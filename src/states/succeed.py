"""
Succeed state implementation for Amazon States Language.

A Succeed state is a terminal state that stops execution successfully.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .base import BaseState, StateError, get_path_processor


@dataclass
class SucceedState(BaseState):
    """
    Succeed state implementation.

    A Succeed state stops an execution successfully. The Succeed state is a
    useful target for Choice state branches that don't do anything but
    stop the execution.

    Attributes:
        name: The name of the state
        input_path: JSONPath to select portion of input to pass to the state
        output_path: JSONPath to select portion of state output to pass to next state
        comment: Human-readable description of the state
    """

    def __init__(
        self,
        name: str,
        next_state: Optional[str] = None,
        end: bool = False,
        input_path: Optional[str] = None,
        result_path: Optional[str] = None,
        output_path: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        self.name = name
        self.type = "Succeed"
        self.input_path = input_path
        self.next_state = next_state
        self.result_path = result_path
        self.output_path = output_path
        self.comment = comment

    def __post_init__(self) -> None:
        """Initialize SucceedState with fixed type."""
        self.type = "Succeed"
        # Call parent validation
        self.validate()

    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, Optional[str]]:
        """
        Execute the Succeed state.

        Args:
            input_data: Input data for the state
            context: Optional execution context

        Returns:
            Tuple of (output, next_state, error)

        Raises:
            StateError: If path processing fails
        """
        if context is None:
            context = {}

        try:
            # Get path processor
            processor = self._path_processor or get_path_processor()

            # Process input path
            processed_input = processor.apply_input_path(input_data, self.input_path)

            # Process output path
            final_output = processor.apply_output_path(processed_input, self.output_path)

            # Succeed states always end execution (no next state, no error)
            return final_output, None

        except Exception as e:
            # Wrap any processing error in StateError
            raise StateError(
                f"Failed to execute succeed state '{self.name}': {str(e)}",
                state_name=self.name,
                error_type="States.Runtime",
            ) from e

    def validate(self, skip_name=False, skip_type=False, skip_next_state=False) -> None:
        """
        Validate the Succeed state configuration.

        Raises:
            ValueError: If the state configuration is invalid
            :param skip_name:
            :param skip_type:
            :param skip_next_state:
        """
        # Call parent validation first

        # Succeed state specific validations
        if self.type != "Succeed":
            raise ValueError(f"Succeed state '{self.name}' must have Type 'Succeed', " f"got '{self.type}'")

        # Succeed states cannot have Next field (they're implicitly end states)
        if self.next_state is not None:
            raise ValueError(f"Succeed state '{self.name}' cannot have Next field")

        # Succeed states cannot have End field (it's implicit)
        if self.end:
            raise ValueError(f"Succeed state '{self.name}' cannot have End field (it's implicit)")

        # Succeed states cannot have ResultPath
        if self.result_path is not None:
            raise ValueError(f"Succeed state '{self.name}' cannot have ResultPath")

        super().validate(skip_type=True, skip_next_state=True)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the state
        """
        result: Dict[str, Any] = {
            "Type": self.type,
        }

        # Only include allowed fields for Succeed state
        if self.input_path is not None:
            result["InputPath"] = self.input_path

        if self.output_path is not None:
            result["OutputPath"] = self.output_path

        if self.comment is not None:
            result["Comment"] = self.comment

        # Explicitly exclude disallowed fields
        # (Next, End, ResultPath should not appear)

        return result

    def get_next_states(self) -> list[str]:
        """
        Get all possible next state names for graph validation.

        Returns:
            Empty list (Succeed states have no next states)
        """
        return []

    def __str__(self) -> str:
        """String representation of the state."""
        return f"SucceedState(name={self.name})"

    def __repr__(self) -> str:
        """Detailed representation of the state."""
        return (
            f"SucceedState("
            f"name={self.name!r}, "
            f"input_path={self.input_path!r}, "
            f"output_path={self.output_path!r}, "
            f"comment={self.comment!r}"
            ")"
        )
