"""
Execution context for state machine executions.

Tracks execution state, history, and metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StateHistory:
    """
    History record for a single state execution.

    Tracks input, output, and metadata for each state execution.
    """

    state_name: str
    state_type: str = ""
    status: str = "SUCCEEDED"
    input: Any = None
    output: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    sequence_number: int = 0
    error: Optional[Exception] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: Dict[str, Any] = {
            "stateName": self.state_name,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.state_type:
            result["stateType"] = self.state_type

        if self.input is not None:
            result["input"] = self.input

        if self.output is not None:
            result["output"] = self.output

        if self.retry_count > 0:
            result["retryCount"] = self.retry_count

        if self.error is not None:
            result["error"] = str(self.error)

        return result


@dataclass
class Execution:
    """
    State machine execution context.

    Tracks the complete lifecycle of a state machine execution including
    status, input/output, history, and timing information.
    """

    id: str
    name: str
    status: str = "RUNNING"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    input: Any = None
    output: Any = None
    error: Optional[Exception] = None
    current_state: str = ""
    history: List[StateHistory] = field(default_factory=list)
    state_machine_id: Optional[str] = None

    @classmethod
    def new_context(cls, name: str, start_at: str, input_data: Any) -> Execution:
        """
        Create a new execution context.

        Args:
            name: Execution name
            start_at: Starting state name
            input_data: Input data

        Returns:
            New Execution instance
        """
        return cls(
            id=_generate_execution_id(),
            name=name,
            status="RUNNING",
            start_time=datetime.now(),
            input=input_data,
            current_state=start_at,
            history=[],
        )

    @classmethod
    def new(
        cls,
        id: Optional[str] = None,
        name: str = "",
        input_data: Any = None,
    ) -> Execution:
        """
        Create a new execution with custom ID.

        Args:
            id: Optional custom execution ID
            name: Execution name
            input_data: Input data

        Returns:
            New Execution instance
        """
        if not id:
            id = _generate_execution_id()

        return cls(
            id=id,
            name=name,
            status="RUNNING",
            start_time=datetime.now(),
            input=input_data,
            history=[],
        )

    def add_state_history(self, state_name: str, input_data: Any, output: Any) -> None:
        """
        Add a state execution to history.

        Args:
            state_name: Name of executed state
            input_data: Input to the state
            output: Output from the state
        """
        self.history.append(
            StateHistory(
                state_name=state_name,
                status="SUCCEEDED",
                input=input_data,
                output=output,
                timestamp=datetime.now(),
                sequence_number=len(self.history),
            )
        )

    def get_last_state(self) -> StateHistory:
        """
        Get the last executed state.

        Returns:
            Last StateHistory entry

        Raises:
            ValueError: If no history available
        """
        if not self.history:
            raise ValueError("No history available")
        return self.history[-1]

    def get_state_history(self, state_name: str) -> List[StateHistory]:
        """
        Get history for a specific state.

        Args:
            state_name: State name to filter by

        Returns:
            List of StateHistory entries for the state
        """
        return [h for h in self.history if h.state_name == state_name]

    def get_duration(self) -> float:
        """
        Get execution duration in seconds.

        Returns:
            Duration in seconds
        """
        end = self.end_time if self.end_time else datetime.now()
        return (end - self.start_time).total_seconds()

    def is_complete(self) -> bool:
        """
        Check if execution is complete.

        Returns:
            True if execution is in a terminal state
        """
        return self.status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert execution to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        result: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "startTime": self.start_time.isoformat(),
            "currentState": self.current_state,
            "duration": f"{self.get_duration(): .2f}s",
        }

        if self.state_machine_id:
            result["stateMachineId"] = self.state_machine_id

        if self.end_time:
            result["endTime"] = self.end_time.isoformat()

        if self.input is not None:
            result["input"] = self.input

        if self.output is not None:
            result["output"] = self.output

        if self.error is not None:
            result["error"] = str(self.error)

        # Add history summary
        if self.history:
            result["history"] = [h.to_dict() for h in self.history]

        return result

    def __str__(self) -> str:
        """String representation of execution."""
        return f"Execution(id={self.id}, name={self.name}, status={self.status}, " f"states={len(self.history)})"


def _generate_execution_id() -> str:
    """
    Generate a unique execution ID.

    Returns:
        Unique execution ID
    """
    return f"exec-{uuid.uuid4().hex[:8]}"
