"""
Base state classes for Amazon States Language implementation.

Based on the Go implementation structure.
"""

from __future__ import annotations

import contextlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Protocol, TypeVar, runtime_checkable

# Type variable for state input/output
T = TypeVar("T")
R = TypeVar("R")


@runtime_checkable
class PathProcessor(Protocol):
    """Protocol for JSON path processors."""

    def apply_input_path(self, input_data: Any, path: Optional[str]) -> Any:
        """Apply input path to filter input data."""
        ...

    def apply_result_path(self, input_data: Any, result: Any, path: Optional[str]) -> Any:
        """Apply result path to combine input and result."""
        ...

    def apply_output_path(self, output: Any, path: Optional[str]) -> Any:
        """Apply output path to filter output data."""
        ...


@dataclass
class RetryRule:
    """Retry rule configuration for error handling."""

    error_equals: List[str]
    interval_seconds: int = 1
    max_attempts: Optional[int] = None
    backoff_rate: float = 2.0
    max_delay_seconds: Optional[int] = None
    jitter_strategy: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate retry rule configuration."""
        if not self.error_equals:
            raise ValueError("ErrorEquals cannot be empty")
        if self.interval_seconds < 0:
            raise ValueError("IntervalSeconds must be >= 0")
        if self.max_attempts is not None and self.max_attempts < 0:
            raise ValueError("MaxAttempts must be >= 0")
        if self.backoff_rate < 1.0:
            raise ValueError("BackoffRate must be >= 1.0")
        if self.max_delay_seconds is not None and self.max_delay_seconds < 0:
            raise ValueError("MaxDelaySeconds must be >= 0")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: Dict[str, Any] = {
            "ErrorEquals": self.error_equals,
        }

        if self.interval_seconds != 1:
            result["IntervalSeconds"] = self.interval_seconds

        if self.max_attempts is not None:
            result["MaxAttempts"] = self.max_attempts

        if self.backoff_rate != 2.0:
            result["BackoffRate"] = self.backoff_rate

        if self.max_delay_seconds is not None:
            result["MaxDelaySeconds"] = self.max_delay_seconds

        if self.jitter_strategy is not None:
            result["JitterStrategy"] = self.jitter_strategy

        return result


@dataclass
class CatchRule:
    """Catch rule configuration for error handling."""

    error_equals: List[str]
    next_state: str
    result_path: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate catch rule configuration."""
        if not self.error_equals:
            raise ValueError("ErrorEquals cannot be empty")
        if not self.next_state:
            raise ValueError("Next cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: Dict[str, Any] = {
            "ErrorEquals": self.error_equals,
            "Next": self.next_state,
        }

        if self.result_path is not None:
            result["ResultPath"] = self.result_path

        return result


@dataclass
class BaseState(ABC):
    """
    Base class for all Amazon States Language states.

    This is an abstract base class that defines the common interface
    and behavior for all state types.
    """

    name: str = field(init=False)  # Will be set by subclasses
    type: str = field(init=False)  # Will be defined by subclasses
    next_state: Optional[str] = field(default=None, repr=False)
    end: bool = field(default=False, repr=False)
    input_path: Optional[str] = field(default=None, repr=False)
    result_path: Optional[str] = field(default=None, repr=False)
    output_path: Optional[str] = field(default=None, repr=False)
    comment: Optional[str] = field(default=None, repr=False)

    # Path processor instance (injected)
    _path_processor: Optional[PathProcessor] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate state configuration after initialization."""
        self.validate()

    @property
    def state_name(self) -> str:
        """Get the name of the state."""
        return self.name

    @property
    def state_type(self) -> str:
        """Get the type of the state."""
        return self.type

    def get_next(self) -> Optional[str]:
        """Get the next state name if any."""
        return self.next_state

    def is_end(self) -> bool:
        """Check if this is an end state."""
        return self.end

    def validate(self, skip_name=False, skip_type=False, skip_next_state=False) -> None:
        """
        Validate the state configuration.

        Raises:
            ValueError: If the state configuration is invalid
            :param skip_name:
            :param skip_type:
            :param skip_next_state:
        """
        if not skip_name and not self.name:
            raise ValueError("State name cannot be empty")

        if not skip_type and not self.type:
            raise ValueError("State type cannot be empty")

        if not skip_next_state and self.next_state is None and not self.end:
            raise ValueError("State must have either Next or End")

        if not skip_next_state and self.next_state is not None and self.end:
            raise ValueError("State cannot have both Next and End")

    def get_next_states(self) -> List[str]:
        """
        Get all possible next state names for graph validation.

        Returns:
            List of possible next state names
        """
        if self.next_state is not None:
            return [self.next_state]
        return []

    def _apply_paths(self, input_data: Any, result: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Apply input, result, and output paths to data.

        Args:
            input_data: Original input data
            result: Result from state execution
            context: Optional execution context

        Returns:
            Processed output data
        """
        if context is None:
            context = {}

        # Get path processor (use default if not set)
        processor = self._path_processor or get_path_processor()

        # Apply input path
        current_data = processor.apply_input_path(input_data, self.input_path)

        # Apply result path
        if result is not None:
            current_data = processor.apply_result_path(current_data, result, self.result_path)

        # Apply output path
        output = processor.apply_output_path(current_data, self.output_path)

        return output

    @abstractmethod
    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> tuple[Any, Optional[str]]:
        """
        Execute the state with the given input.

        Args:
            input_data: Input data for the state
            context: Optional execution context

        Returns:
            Tuple of (output, next_state, error)
        """
        pass

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

        if self.comment is not None:
            result["Comment"] = self.comment

        return result

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Convert state to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent)

    def set_path_processor(self, processor: PathProcessor) -> None:
        """
        Set a custom path processor for this state.

        Args:
            processor: Path processor instance
        """
        self._path_processor = processor

    def __str__(self) -> str:
        """String representation of the state."""
        return f"{self.type}State(name={self.name})"

    def __repr__(self) -> str:
        """Detailed representation of the state."""
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"type={self.type!r}, "
            f"next_state={self.next_state!r}, "
            f"end={self.end!r}"
            ")"
        )


# Global path processor instance
_default_path_processor: Optional[PathProcessor] = None


def get_path_processor() -> PathProcessor:
    """
    Get the current default path processor.

    Returns:
        Current path processor instance

    Raises:
        RuntimeError: If no path processor is set
    """
    global _default_path_processor
    if _default_path_processor is None:
        from .json_path import JSONPathProcessor

        _default_path_processor = JSONPathProcessor()  # type: ignore[no-untyped-call]
    return _default_path_processor


def set_path_processor(processor: PathProcessor) -> None:
    """
    Set a custom default path processor.

    Args:
        processor: Path processor instance
    """
    global _default_path_processor
    _default_path_processor = processor


@contextlib.contextmanager
def temporary_path_processor(processor: PathProcessor) -> Generator[None, Any, None]:
    """
    Context manager for temporarily using a different path processor.

    Args:
        processor: Temporary path processor to use
    """
    global _default_path_processor
    original = _default_path_processor
    try:
        _default_path_processor = processor
        yield
    finally:
        _default_path_processor = original


class StateError(Exception):
    """Base exception for state execution errors."""

    def __init__(
        self,
        message: str,
        state_name: Optional[str] = None,
        error_type: Optional[str] = None,
    ):
        self.message = message
        self.state_name = state_name
        self.error_type = error_type or "States.Runtime"
        # super().__init__(self.message)

    def __str__(self) -> str:
        parts = []
        if self.state_name:
            parts.append(f"State: {self.state_name}")
        parts.append(f"Error: {self.message}")
        parts.append(f"Type: {self.error_type}")
        return " | ".join(parts)


class StateValidationError(StateError):
    """Exception for state validation errors."""

    def __init__(self, message: str, state_name: Optional[str] = None):
        super().__init__(message, state_name, "States.Validation")


class StateExecutionError(StateError):
    """Exception for state execution errors."""

    def __init__(self, message: str, state_name: Optional[str] = None):
        super().__init__(message, state_name, "States.Runtime")


class StateTimeoutError(StateError):
    """Exception for state timeout errors."""

    def __init__(self, message: str, state_name: Optional[str] = None):
        super().__init__(message, state_name, "States.Timeout")


class StateTaskFailedError(StateError):
    """Exception for task state failures."""

    def __init__(self, message: str, state_name: Optional[str] = None):
        super().__init__(message, state_name, "States.TaskFailed")
