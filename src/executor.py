"""
Executor for state machine execution management.

Manages state machine executions, task handlers, and execution lifecycle.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Protocol

from .execution import Execution


class StateMachineInterface(Protocol):
    """Protocol for state machine interface."""

    def get_start_at(self) -> str:
        """Get start state name."""
        ...

    def get_state(self, name: str) -> Any:
        """Get state by name."""
        ...

    def is_timeout(self, start_time: datetime) -> bool:
        """Check if execution has timed out."""
        ...

    async def run_execution(self, exec_ctx: Execution, context: Optional[Dict[str, Any]] = None) -> Execution:
        """Run execution."""
        ...


class Executor(ABC):
    """Abstract base class for state machine executors."""

    @abstractmethod
    async def execute(
        self,
        sm: StateMachineInterface,
        exec_ctx: Execution,
        context: Optional[Dict[str, Any]] = None,
    ) -> Execution:
        """
        Execute a state machine with the given context.

        Args:
            sm: State machine to execute
            exec_ctx: Execution context
            context: Optional additional context

        Returns:
            Completed execution context
        """
        pass

    @abstractmethod
    def get_status(self, execution_id: str) -> Execution:
        """
        Get the status of an execution.

        Args:
            execution_id: Execution ID

        Returns:
            Execution context

        Raises:
            ValueError: If execution not found
        """
        pass

    @abstractmethod
    async def stop(self, exec_ctx: Execution) -> None:
        """
        Stop an execution.

        Args:
            exec_ctx: Execution to stop
        """
        pass

    @abstractmethod
    def list_executions(self) -> list[Execution]:
        """
        List all executions.

        Returns:
            List of execution contexts
        """
        pass


class StateRegistry:
    """Registry for managing state task handlers."""

    def __init__(self):
        """Initialize state registry."""
        self.task_handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_task_handler(
        self,
        resource_uri: str,
        handler: Callable[[Any], Any],
    ) -> None:
        """
        Register a handler for a task state.

        Args:
            resource_uri: Resource URI (ARN)
            handler: Handler function
        """
        self.task_handlers[resource_uri] = handler

    def get_task_handler(self, resource_uri: str) -> Optional[Callable[[Any], Any]]:
        """
        Get a task handler by resource URI.

        Args:
            resource_uri: Resource URI

        Returns:
            Handler function if found, None otherwise
        """
        return self.task_handlers.get(resource_uri)


class BaseExecutor(Executor):
    """
    Base implementation of state machine executor.

    Provides common functionality for managing executions and task handlers.
    """

    def __init__(self):
        """Initialize base executor."""
        self.executions: Dict[str, Execution] = {}
        self.registry = StateRegistry()

    async def execute(
        self,
        sm: StateMachineInterface,
        exec_ctx: Execution,
        context: Optional[Dict[str, Any]] = None,
    ) -> Execution:
        """
        Execute a state machine.

        Args:
            sm: State machine to execute
            exec_ctx: Execution context
            context: Optional additional context

        Returns:
            Completed execution context
        """
        if context is None:
            context = {}

        # Store execution
        self.executions[exec_ctx.id] = exec_ctx

        # Execute the state machine
        result = await sm.run_execution(exec_ctx, context)

        # Remove from active executions if complete
        if result.is_complete():
            self.executions.pop(exec_ctx.id, None)

        return result

    def get_status(self, execution_id: str) -> Execution:
        """
        Get execution status.

        Args:
            execution_id: Execution ID

        Returns:
            Execution context

        Raises:
            ValueError: If execution not found
        """
        if execution_id not in self.executions:
            raise ValueError(f"Execution '{execution_id}' not found")
        return self.executions[execution_id]

    async def stop(self, exec_ctx: Execution) -> None:
        """
        Stop an execution.

        Args:
            exec_ctx: Execution to stop

        Raises:
            ValueError: If execution is None
        """
        if exec_ctx is None:
            raise ValueError("Execution context cannot be None")

        exec_ctx.status = "ABORTED"
        exec_ctx.end_time = datetime.now()

        # Remove from active executions
        self.executions.pop(exec_ctx.id, None)

    def list_executions(self) -> list[Execution]:
        """
        List all active executions.

        Returns:
            List of execution contexts
        """
        return list(self.executions.values())

    def register_go_function(self, name: str, fn: Callable[[Any], Any]) -> None:
        """
        Register a Python function as a task handler.

        Args:
            name: Function name
            fn: Handler function
        """
        resource_uri = f"arn:aws:states:::lambda:function:{name}"
        self.registry.register_task_handler(resource_uri, fn)

    async def execute_go_task(self, task_state: Any, input_data: Any) -> Any:
        """
        Execute a task using registered handler.

        Args:
            task_state: Task state
            input_data: Input data

        Returns:
            Task output
        """
        # Placeholder - actual implementation would use task_state.resource
        return input_data


class ExecutionContextAdapter:
    """
    Adapter to provide ExecutionContext interface for states.

    Bridges the BaseExecutor with the state execution context.
    """

    def __init__(self, executor: BaseExecutor):
        """
        Initialize adapter.

        Args:
            executor: Base executor instance
        """
        self.executor = executor

    def get_task_handler(self, resource: str) -> Optional[Callable[[Any], Any]]:
        """
        Get task handler for resource.

        Args:
            resource: Resource URI

        Returns:
            Handler function if found
        """
        if self.executor is None or self.executor.registry is None:
            return None
        return self.executor.registry.get_task_handler(resource)
