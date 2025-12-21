"""
State Machine implementation for Amazon States Language.

Main state machine class that loads, validates, and executes state machines.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import yaml

from src.execution import Execution
from src.factory import StateFactory
from src.validator import StateMachineValidator


@dataclass
class StateMachine:
    """
    Amazon States Language state machine.

    Represents a complete state machine definition that can be executed
    with various inputs.
    """

    comment: Optional[str] = None
    start_at: str = ""
    states: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: Optional[int] = None
    version: str = "1.0"

    # Internal fields
    _validator: Optional[StateMachineValidator] = field(default=None, init=False, repr=False)
    _created_at: datetime = field(default_factory=datetime.now, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize validator."""
        self._validator = StateMachineValidator()

    @classmethod
    def from_json(cls, definition: str) -> StateMachine:
        """
        Create a state machine from JSON definition.

        Args:
            definition: JSON string defining the state machine

        Returns:
            StateMachine instance

        Raises:
            ValueError: If definition is invalid
        """
        try:
            data = json.loads(definition)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON definition: {e}") from e

        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, definition: str) -> StateMachine:
        """
        Create a state machine from YAML definition.

        Args:
            definition: YAML string defining the state machine

        Returns:
            StateMachine instance

        Raises:
            ValueError: If definition is invalid
        """
        try:
            data = yaml.safe_load(definition)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML definition: {e}") from e

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StateMachine:
        """
        Create state machine from dictionary.

        Args:
            data: Dictionary representation of state machine

        Returns:
            StateMachine instance
        """
        # Extract basic fields
        comment = data.get("Comment")
        start_at = data.get("StartAt", "")
        timeout_seconds = data.get("TimeoutSeconds")
        version = data.get("Version", "1.0")

        # Validate that States exists
        if "States" not in data or not data["States"]:
            raise ValueError("Failed to unmarshal state machine definition: " "States is required and cannot be empty")

        # Parse states using factory
        state_factory = StateFactory()
        states = {}

        for state_name, state_data in data["States"].items():
            try:
                state = state_factory.create_state(state_name, state_data)
                states[state_name] = state
            except Exception as e:
                raise ValueError(f"Failed to create state '{state_name}': {e}") from e

        # Create state machine
        sm = cls(
            comment=comment,
            start_at=start_at,
            states=states,
            timeout_seconds=timeout_seconds,
            version=version,
        )

        # Validate
        try:
            sm.validate()
        except Exception as e:
            raise ValueError(f"State machine validation failed: {e}") from e

        return sm

    def validate(self) -> None:
        """
        Validate the state machine definition.

        Raises:
            ValueError: If validation fails
        """
        if self._validator is None:
            self._validator = StateMachineValidator()

        self._validator.validate(self.start_at, self.states, self.timeout_seconds)

    def get_start_at(self) -> str:
        """Get the start state name."""
        return self.start_at

    def get_state(self, name: str) -> Any:
        """
        Get a state by name.

        Args:
            name: State name

        Returns:
            State object

        Raises:
            ValueError: If state not found
        """
        if name not in self.states:
            raise ValueError(f"State '{name}' not found")
        return self.states[name]

    async def execute(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
        execution_name: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> Execution:
        """
        Execute the state machine with given input.

        Args:
            input_data: Input data for execution
            context: Optional execution context
            execution_name: Optional name for execution

        Returns:
            Execution object with results
            :param input_data:
            :param context:
            :param execution_name:
            :param execution_id:
        """
        if context is None:
            context = {}

        # Create execution context
        if execution_name is None:
            execution_name = f"execution-{int(time.time())}"

        exec_ctx = Execution.new_context(execution_name, self.start_at, input_data)

        return await self.run_execution(exec_ctx, context)

    async def run_execution(self, exec_ctx: Execution, context: Optional[Dict[str, Any]] = None) -> Execution:
        """
        Run an execution with the given context.

        Args:
            exec_ctx: Execution context
            context: Optional additional context

        Returns:
            Completed execution context
        """
        if context is None:
            context = {}

        current_state_name = self.start_at
        current_input = exec_ctx.input

        while True:
            # Check for timeout
            if self.timeout_seconds is not None:
                elapsed = (datetime.now() - exec_ctx.start_time).total_seconds()
                if elapsed > self.timeout_seconds:
                    exec_ctx.status = "TIMED_OUT"
                    exec_ctx.end_time = datetime.now()
                    exec_ctx.error = TimeoutError(f"State machine timed out after {self.timeout_seconds} seconds")
                    return exec_ctx

            # Get current state
            try:
                state = self.get_state(current_state_name)
            except ValueError as e:
                exec_ctx.status = "FAILED"
                exec_ctx.end_time = datetime.now()
                exec_ctx.error = e
                return exec_ctx

            # Update execution context
            exec_ctx.current_state = current_state_name

            # Execute the state
            try:
                output, next_state = await state.execute(current_input, context)
            except Exception as e:
                # State execution failed
                exec_ctx.status = "FAILED"
                exec_ctx.end_time = datetime.now()
                exec_ctx.error = e
                exec_ctx.output = None
                # Record failed state in history
                exec_ctx.add_state_history(current_state_name, current_input, None)
                return exec_ctx

            # Record state history
            exec_ctx.add_state_history(current_state_name, current_input, output)

            # Check if this is an end state
            if state.is_end() or next_state is None:
                # Execution completed successfully
                exec_ctx.status = "SUCCEEDED"
                exec_ctx.end_time = datetime.now()
                exec_ctx.output = output
                break

            # Move to next state
            current_state_name = next_state
            current_input = output

        return exec_ctx

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the state machine.

        Returns:
            Dictionary with state machine summary
        """
        summary: Dict[str, Any] = {
            "startAt": self.start_at,
            "statesCount": len(self.states),
            "version": self.version,
            "createdAt": self._created_at.isoformat(),
        }

        if self.timeout_seconds is not None:
            summary["timeoutSeconds"] = self.timeout_seconds

        if self.comment:
            summary["comment"] = self.comment

        # Count state types
        state_types: Dict[str, int] = {}
        for state in self.states.values():
            state_type = state.state_type
            state_types[state_type] = state_types.get(state_type, 0) + 1

        summary["stateTypes"] = state_types

        return summary

    def is_timeout(self, start_time: datetime) -> bool:
        """
        Check if execution has timed out.

        Args:
            start_time: Execution start time

        Returns:
            True if timed out
        """
        if self.timeout_seconds is None:
            return False

        elapsed = (datetime.now() - start_time).total_seconds()
        return elapsed > self.timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state machine to dictionary.

        Returns:
            Dictionary representation
        """
        result: Dict[str, Any] = {
            "StartAt": self.start_at,
            "States": {name: state.to_dict() for name, state in self.states.items()},
        }

        if self.comment:
            result["Comment"] = self.comment

        if self.timeout_seconds is not None:
            result["TimeoutSeconds"] = self.timeout_seconds

        if self.version != "1.0":
            result["Version"] = self.version

        return result

    def to_json(self, indent: Optional[int] = 2) -> str:
        """
        Convert state machine to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_yaml(self) -> str:
        """
        Convert state machine to YAML string.

        Returns:
            YAML string
        """
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)


# Execution options
class ExecutionOptions:
    """Options for state machine execution."""

    def __init__(self, name: Optional[str] = None):
        """
        Initialize execution options.

        Args:
            name: Execution name
        """
        self.name = name


def with_execution_name(name: str) -> Callable[[ExecutionOptions], None]:
    """
    Create an option setter for execution name.

    Args:
        name: Execution name

    Returns:
        Option setter function
    """

    def setter(opts: ExecutionOptions) -> None:
        opts.name = name

    return setter
