"""
Pass state implementation for Amazon States Language.

A Pass state passes its input to its output, performing no work. Pass states
are useful when constructing and debugging state machines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .base import BaseState, StateError, get_path_processor


@dataclass
class PassState(BaseState):
    """
    Pass state implementation.

    A Pass state simply passes its input to its output, performing no work.
    Pass states are useful when constructing and debugging state machines.
    They can inject fixed data into the state machine or transform data using
    paths.

    Attributes:
        name: The name of the state
        next_state: The name of the next state to transition to
        end: Whether this is a terminal state
        input_path: JSONPath to select portion of input to pass to the state
        result_path: JSONPath to specify where to place the result
        output_path: JSONPath to select portion of state output to pass to next state
        result: Static result data to inject
        parameters: Parameters to pass (for data transformation)
        comment: Human-readable description of the state
    """

    result: Optional[Any] = None
    parameters: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        name: str,
        next_state: Optional[str] = None,
        end: bool = False,
        input_path: Optional[str] = None,
        result_path: Optional[str] = None,
        output_path: Optional[str] = None,
        result: Optional[Any] = None,
        parameters: Optional[Dict[str, Any]] = None,
        comment: Optional[str] = None,
    ):
        self.name = name
        self.type = "Pass"
        self.next_state = next_state
        self.end = end
        self.input_path = input_path
        self.result_path = result_path
        self.output_path = output_path
        self.result = result
        self.parameters = parameters
        self.comment = comment

    def __post_init__(self) -> None:
        """Initialize PassState with fixed type."""
        self.type = "Pass"
        # Call parent validation
        self.validate()

    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, Optional[str]]:
        """
        Execute the Pass state.

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

            # Determine the result to use
            if self.result is not None:
                state_result = self.result
            elif self.parameters is not None:
                # Parameters would be processed here (simplified for now)
                state_result = self.parameters
            else:
                state_result = None

            # Apply result path
            if state_result is not None:
                combined_data = processor.apply_result_path(processed_input, state_result, self.result_path)
            else:
                combined_data = processed_input

            # Process output path
            final_output = processor.apply_output_path(combined_data, self.output_path)

            # Return output and next state
            return final_output, self.next_state

        except Exception as e:
            # Wrap any processing error in StateError
            raise StateError(
                f"Failed to execute pass state '{self.name}': {str(e)}",
                state_name=self.name,
                error_type="States.Runtime",
            ) from e

    def validate(self, skip_name=False, skip_type=False, skip_next_state=False) -> None:
        """
        Validate the Pass state configuration.

        Raises:
            ValueError: If the state configuration is invalid
        """
        # Pass state specific validations
        if self.type != "Pass":
            raise ValueError(f"Pass state '{self.name}' must have Type 'Pass', " f"got '{self.type}'")

        # Cannot have both Result and Parameters
        if self.result is not None and self.parameters is not None:
            raise ValueError(f"Pass state '{self.name}' cannot have both Result and Parameters")

        # Call parent validation
        super().validate(skip_type=True, skip_next_state=False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the state
        """
        result: Dict[str, Any] = {
            "Type": self.type,
        }

        if self.next_state is not None:
            result["Next"] = self.next_state

        if self.end:
            result["End"] = self.end

        if self.input_path is not None:
            result["InputPath"] = self.input_path

        if self.result_path is not None:
            result["ResultPath"] = self.result_path

        if self.output_path is not None:
            result["OutputPath"] = self.output_path

        if self.result is not None:
            result["Result"] = self.result

        if self.parameters is not None:
            result["Parameters"] = self.parameters

        if self.comment is not None:
            result["Comment"] = self.comment

        return result

    def __str__(self) -> str:
        """String representation of the state."""
        return f"PassState(name={self.name})"

    def __repr__(self) -> str:
        """Detailed representation of the state."""
        return (
            f"PassState("
            f"name={self.name!r}, "
            f"next_state={self.next_state!r}, "
            f"end={self.end!r}, "
            f"result={self.result!r}, "
            f"parameters={self.parameters!r}"
            ")"
        )
