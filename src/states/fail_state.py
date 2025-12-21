"""
Fail state implementation for Amazon States Language.

A Fail state stops execution of the state machine and marks it as a failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .base import BaseState, StateError


@dataclass
class FailState(BaseState):
    """
    Fail state implementation.

    A Fail state stops an execution and marks it as a failure. The Fail state
    only allows the use of Type, Comment, Error, and Cause fields.

    Attributes:
        name: The name of the state
        error: Error name/code for the failure
        cause: Human-readable error message
        comment: Human-readable description of the state
    """

    cause: Optional[str] = None

    def __init__(
        self,
        name: str,
        error: str,
        cause: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        self.name = name
        self.type = "Fail"
        self.error = error
        self.cause = cause
        self.comment = comment
        # Fail states cannot have these fields
        self.next_state = None
        self.end = False
        self.input_path = None
        self.result_path = None
        self.output_path = None

    def __post_init__(self) -> None:
        """Initialize FailState with fixed type."""
        self.type = "Fail"
        # Call parent validation
        self.validate()

    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, Optional[str]]:
        """
        Execute the Fail state.

        Args:
            input_data: Input data for the state (ignored)
            context: Optional execution context

        Returns:
            Tuple of (None, None, StateError)

        Note:
            Fail states always return an error and no next state.
        """
        if context is None:
            context = {}

        # Create error with the specified error code and cause
        raise StateError(
            message=self.cause or f"State '{self.name}' failed",
            state_name=self.name,
            error_type=self.error,
        )

    def validate(self, skip_name=False, skip_type=False, skip_next_state=False) -> None:
        """
        Validate the Fail state configuration.

        Raises:
            ValueError: If the state configuration is invalid
        """
        # Fail state specific validations
        if self.type != "Fail":
            raise ValueError(f"Fail state '{self.name}' must have Type 'Fail', " f"got '{self.type}'")

        # Error field is required
        if not self.error:
            raise ValueError(f"Fail state '{self.name}' must have Error field")

        # Fail states cannot have Next field
        if self.next_state is not None:
            raise ValueError(f"Fail state '{self.name}' cannot have Next field")

        # Fail states cannot have End field
        if self.end:
            raise ValueError(f"Fail state '{self.name}' cannot have End field (it's implicit)")

        # Fail states cannot have InputPath
        if self.input_path is not None:
            raise ValueError(f"Fail state '{self.name}' cannot have InputPath")

        # Fail states cannot have OutputPath
        if self.output_path is not None:
            raise ValueError(f"Fail state '{self.name}' cannot have OutputPath")

        # Fail states cannot have ResultPath
        if self.result_path is not None:
            raise ValueError(f"Fail state '{self.name}' cannot have ResultPath")

        # Call parent validation with skip flags
        super().validate(skip_type=True, skip_next_state=True)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the state
        """
        result: Dict[str, Any] = {
            "Type": self.type,
            "Error": self.error,
        }

        if self.cause is not None:
            result["Cause"] = self.cause

        if self.comment is not None:
            result["Comment"] = self.comment

        # Explicitly exclude disallowed fields
        # (Next, End, InputPath, OutputPath, ResultPath should not appear)

        return result

    def get_next_states(self) -> list[str]:
        """
        Get all possible next state names for graph validation.

        Returns:
            Empty list (Fail states have no next states)
        """
        return []

    def __str__(self) -> str:
        """String representation of the state."""
        return f"FailState(name={self.name}, error={self.error})"

    def __repr__(self) -> str:
        """Detailed representation of the state."""
        return (
            f"FailState("
            f"name={self.name!r}, "
            f"error={self.error!r}, "
            f"cause={self.cause!r}, "
            f"comment={self.comment!r}"
            ")"
        )
