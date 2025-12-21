# pkg/statemachine/persistent_statemachine.py
"""Persistent state machine implementation with repository integration."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.machine.state_machine import StateMachine
from src.repository import (
    Execution,
    ExecutionFilter,
    ExecutionRecord,
    PersistenceManager,
    StateHistory,
    StateHistoryRecord,
    generate_history_id,
)
from src.states.base import StateError


class PersistentContext:
    """Represents the execution context of a state machine."""

    def __init__(
        self,
        name: str,
        start_state: str,
        input_data: Any,
        execution_id: Optional[str] = None,
        state_machine_id: Optional[str] = None,
    ):
        self.id = execution_id or f"exec-{int(time.time() * 1000)}"
        self.state_machine_id = state_machine_id or ""
        self.name = name
        self.input = input_data
        self.output: Any = None
        self.status = "RUNNING"
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.current_state = start_state
        self.error: Optional[Exception] = None
        self.history: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def mark_succeeded(self, output: Any) -> None:
        """Mark execution as succeeded."""
        self.status = "SUCCEEDED"
        self.output = output
        self.end_time = datetime.utcnow()

    def mark_failed(self, error: Exception) -> None:
        """Mark execution as failed."""
        self.status = "FAILED"
        self.error = error
        self.end_time = datetime.utcnow()

    def mark_cancelled(self, error: Exception) -> None:
        """Mark execution as cancelled."""
        self.status = "CANCELLED"
        self.error = error
        self.end_time = datetime.utcnow()


class StateHistoryEntry:
    """Represents a state execution history entry."""

    def __init__(
        self,
        state_name: str,
        state_type: str,
        input_data: Any,
        sequence_number: int,
    ):
        self.state_name = state_name
        self.state_type = state_type
        self.input = input_data
        self.output: Any = None
        self.status = "RUNNING"
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.error: Optional[Exception] = None
        self.retry_count = 0
        self.sequence_number = sequence_number

    def mark_succeeded(self, output: Any) -> None:
        """Mark state execution as succeeded."""
        self.status = "SUCCEEDED"
        self.output = output
        self.end_time = datetime.utcnow()

    def mark_failed(self, error: Exception) -> None:
        """Mark state execution as failed."""
        self.status = "FAILED"
        self.error = error
        self.end_time = datetime.utcnow()


@dataclass
class PersistentStateMachine:
    """State machine with persistence capabilities."""

    state_machine: StateMachine
    persistence_manager: PersistenceManager
    state_machine_id: str

    def __post_init__(self):
        if self.state_machine is None:
            raise ValueError("state_machine cannot be None")
        if self.persistence_manager is None:
            raise ValueError("persistence_manager cannot be None")
        if self.state_machine_id is None:
            self.state_machine_id = f"sm-{int(time.time())}"

    @classmethod
    def create_from_json(
        cls,
        json_str: str,
        persistence_manager: PersistenceManager,
        state_machine_id: str,
    ) -> PersistentStateMachine:
        """Factory function to create a persistent state machine.

        Args:
            json_str: str definition for the state machine
            persistence_manager: Repository manager for persistence
            state_machine_id: Optional state machine ID

        Returns:
            PersistentStateMachine instance
        """
        psm: PersistentStateMachine = PersistentStateMachine(
            state_machine=StateMachine.from_json(definition=json_str),
            persistence_manager=persistence_manager,
            state_machine_id=state_machine_id,
        )
        return psm

    @classmethod
    def create_from_yaml(
        cls,
        yaml_str: str,
        persistence_manager: PersistenceManager,
        state_machine_id: str,
    ) -> PersistentStateMachine:
        """Factory function to create a persistent state machine.

            Args:
                persistence_manager: Repository manager for persistence
                state_machine_id: Optional state machine ID

        Returns:
            PersistentStateMachine instance
        """
        if state_machine_id is None:
            raise ValueError("Cannot prepare a persistent-state-machine without an Id")

        if persistence_manager is None:
            raise ValueError("Cannot prepare a persistent-state-machine without a persistent manager")

        psm: PersistentStateMachine = PersistentStateMachine(
            state_machine=StateMachine.from_yaml(definition=yaml_str),
            persistence_manager=persistence_manager,
            state_machine_id=state_machine_id,
        )
        return psm

    async def execute(
        self,
        input_data: Any,
        task_exec_context: Optional[Dict[str, Any]] = None,
        execution_name: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> PersistentContext:
        """Execute the state machine with persistence.

        Args:
            input_data: Input data for the execution
            execution_name: Optional custom execution name
            execution_id: Optional custom execution ID

        Returns:
            ExecutionContext with execution results

        Raises:
            Exception: If execution fails
            :param task_exec_context:
            :param execution_id:
            :param execution_name:
            :param input_data:
            :param persistent_context:
        """
        # Create execution context
        exec_name = execution_name or f"execution-{int(time.time())}"
        execution_id = execution_id or f"{exec_name}-id-{random.randint(1, 10)}"

        persistent_exec_context: PersistentContext = PersistentContext(
            name=exec_name,
            start_state=self.state_machine.start_at,
            input_data=input_data,
            execution_id=execution_id,
            state_machine_id=self.state_machine_id,
        )

        # Set state machine ID
        persistent_exec_context.id = self.state_machine_id
        persistent_exec_context.state_machine_id = self.state_machine_id

        # Save initial execution state
        await self._persist_execution(persistent_exec_context)

        # Run execution
        return await self._run_execution(persistent_exec_context, task_exec_context)

    def get_persistence_manager(self) -> PersistenceManager:
        return self.persistence_manager

    async def _run_execution(
        self, exec_ctx: PersistentContext, task_exec_ctx: Optional[Dict[str, Any]]
    ) -> PersistentContext:
        """Run the execution with persistence hooks.

        Args:
            exec_ctx: Execution context

        Returns:
            Updated execution context

        Raises:
            Exception: If execution fails
        """
        current_state_name = exec_ctx.current_state

        while True:
            # Get current state
            state = self.state_machine.states.get(current_state_name)
            if not state:
                error = Exception(f"state not found: {current_state_name}")
                exec_ctx.mark_failed(error)
                await self._persist_execution(exec_ctx)
                raise error

            # Create history entry
            history = StateHistoryEntry(
                state_name=current_state_name,
                state_type=state.type,
                input_data=exec_ctx.input,
                sequence_number=len(exec_ctx.history),
            )

            # Execute the state
            try:
                output, next_state = await state.execute(exec_ctx.input, context=task_exec_ctx)

                # Update history
                history.end_time = datetime.utcnow()
                history.output = output

                history.mark_succeeded(output)
                exec_ctx.input = output  # Next state's input

                # Append to history
                exec_ctx.history.append(history.__dict__)

                # Persist state history immediately
                await self._save_state_history(exec_ctx, history)

                # Update execution record
                exec_ctx.current_state = current_state_name
                await self._persist_execution(exec_ctx)

                # Check if this is a terminal state
                if state.is_end():
                    exec_ctx.mark_succeeded(output)
                    await self._persist_execution(exec_ctx)
                    return exec_ctx

                # Move to next state
                if not next_state:
                    error = Exception(f"non-terminal state {current_state_name} did not provide next state")
                    exec_ctx.mark_failed(error)
                    await self._persist_execution(exec_ctx)
                    raise error

                current_state_name = next_state
                exec_ctx.current_state = current_state_name

            except StateError as error:
                history.mark_failed(error)
                exec_ctx.mark_failed(error)
                exec_ctx.history.append(history.__dict__)

                # Persist state history and execution
                await self._save_state_history(exec_ctx, history)
                await self._persist_execution(exec_ctx)
                return exec_ctx
            except KeyboardInterrupt:
                key_exception = Exception("execution cancelled by user")
                exec_ctx.mark_cancelled(key_exception)
                await self._persist_execution(exec_ctx)
                raise key_exception

    async def _persist_execution(self, exec_ctx: PersistentContext) -> None:
        """Persist execution state to repository.

        Args:
            exec_ctx: Execution context to persist
        """
        try:
            # Create a mock Execution object for the manager

            exec = Execution(
                id=exec_ctx.id,
                state_machine_id=exec_ctx.state_machine_id,
                name=exec_ctx.name,
                input=exec_ctx.input,
                output=exec_ctx.output,
                status=exec_ctx.status,
                start_time=exec_ctx.start_time,
                end_time=exec_ctx.end_time,
                current_state=exec_ctx.current_state,
                error=exec_ctx.error,
                metadata=exec_ctx.metadata,
            )

            self.persistence_manager.save_execution(exec)
        except Exception as e:
            print(f"Warning: failed to persist execution state: {e}")

    async def _save_state_history(self, exec_ctx: PersistentContext, history: StateHistoryEntry) -> None:
        """Save state history to repository.

        Args:
            exec_ctx: Execution context
            history: State history entry
        """
        try:
            # Create mock objects for the manager
            exec = Execution(
                id=exec_ctx.id,
                state_machine_id=exec_ctx.state_machine_id,
                name=exec_ctx.name,
                input=exec_ctx.input,
                output=exec_ctx.output,
                status=exec_ctx.status,
                start_time=exec_ctx.start_time,
                end_time=exec_ctx.end_time,
                current_state=exec_ctx.current_state,
                error=exec_ctx.error,
            )

            hist = StateHistory(
                id=generate_history_id(exec_ctx.id, history.state_name, history.start_time),
                execution_id=exec_ctx.id,
                state_name=history.state_name,
                state_type=history.state_type,
                input=history.input,
                output=history.output,
                status=history.status,
                start_time=history.start_time,
                end_time=history.end_time,
                error=history.error,
                retry_count=history.retry_count,
                sequence_number=history.sequence_number,
            )

            self.persistence_manager.save_state_history(exec, hist)
        except Exception as e:
            print(f"Warning: failed to persist state history: {e}")

    async def get_execution(self, execution_id: str) -> ExecutionRecord:
        """Retrieve an execution from repository.

        Args:
            execution_id: ID of the execution to retrieve

        Returns:
            ExecutionRecord from repository
        """
        return self.persistence_manager.get_execution(execution_id)

    async def get_execution_history(self, execution_id: str) -> List[StateHistoryRecord]:
        """Retrieve execution history from repository.

        Args:
            execution_id: ID of the execution

        Returns:
            List of state history records
        """
        return self.persistence_manager.get_state_history(execution_id)

    def list_executions(self, filter: Optional[ExecutionFilter] = None) -> List[ExecutionRecord]:
        """List executions from repository.

        Args:
            filter: Optional filter for executions

        Returns:
            List of execution records
        """
        if filter is None:
            filter = ExecutionFilter()

        # Always filter by this state machine's ID
        filter.state_machine_id = self.state_machine_id

        return self.persistence_manager.list_executions(filter)

    async def count_executions(self, filter: Optional[ExecutionFilter] = None) -> int:
        """Count executions matching filter.

        Args:
            filter: Optional filter for executions

        Returns:
            Count of matching executions
        """
        if filter is None:
            filter = ExecutionFilter()

        # Always filter by this state machine's ID
        filter.state_machine_id = self.state_machine_id

        return self.persistence_manager.count_executions(filter)
