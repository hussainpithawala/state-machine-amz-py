"""
Wait state implementation for Amazon States Language.

A Wait state delays execution for a specified time period or until a
specified timestamp.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from .base import BaseState, StateError, get_path_processor


@dataclass
class WaitState(BaseState):
    """
    Wait state implementation.

    A Wait state causes the interpreter to delay the machine from continuing for
    a specified time. The time can be specified as a wait duration, specified in
    seconds, or an absolute expiry time, specified as an ISO-8601 extended offset
    date-time format string.

    Attributes:
        name: The name of the state
        next_state: The name of the next state to transition to
        end: Whether this is a terminal state
        input_path: JSONPath to select portion of input to pass to the state
        result_path: JSONPath to specify where to place the result
        output_path: JSONPath to select portion of state output to pass to next state
        seconds: Number of seconds to wait (non-negative integer)
        seconds_path: JSONPath to extract seconds from input
        timestamp: ISO-8601 timestamp string to wait until
        timestamp_path: JSONPath to extract timestamp from input
        comment: Human-readable description of the state
    """

    seconds: Optional[int] = None
    seconds_path: Optional[str] = None
    timestamp: Optional[str] = None
    timestamp_path: Optional[str] = None

    def __init__(
        self,
        name: str,
        next_state: Optional[str] = None,
        end: bool = False,
        input_path: Optional[str] = None,
        result_path: Optional[str] = None,
        output_path: Optional[str] = None,
        seconds: Optional[int] = None,
        seconds_path: Optional[str] = None,
        timestamp: Optional[str] = None,
        timestamp_path: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        self.name = name
        self.type = "Wait"
        self.next_state = next_state
        self.end = end
        self.input_path = input_path
        self.result_path = result_path
        self.output_path = output_path
        self.seconds = seconds
        self.seconds_path = seconds_path
        self.timestamp = timestamp
        self.timestamp_path = timestamp_path
        self.comment = comment

    def __post_init__(self) -> None:
        """Initialize WaitState with fixed type."""
        self.type = "Wait"
        # Call parent validation
        self.validate()

    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, Optional[str]]:
        """
        Execute the Wait state.

        Args:
            input_data: Input data for the state
            context: Optional execution context

        Returns:
            Tuple of (output, next_state, error)

        Raises:
            StateError: If wait calculation or execution fails
        """
        if context is None:
            context = {}

        try:
            # Get path processor
            processor = self._path_processor or get_path_processor()

            # Process input path
            processed_input = processor.apply_input_path(input_data, self.input_path)

            # Calculate wait duration
            wait_duration = self._calculate_wait_duration(processor, processed_input)

            # Perform the wait
            if wait_duration > 0:
                try:
                    await asyncio.sleep(wait_duration)
                except asyncio.CancelledError:
                    # If the task is cancelled during wait, propagate the error
                    raise StateError(
                        f"Wait state '{self.name}' was cancelled",
                        state_name=self.name,
                        error_type="States.Timeout",
                    )

            # Apply result path (Wait state passes through input)
            output = processor.apply_result_path(processed_input, processed_input, self.result_path)

            # Process output path
            final_output = processor.apply_output_path(output, self.output_path)

            # Return output and next state
            return final_output, self.next_state

        except StateError:
            # Re-raise StateError as-is
            raise
        except Exception as e:
            # Wrap any other error in StateError
            raise StateError(
                f"Failed to execute wait state '{self.name}': {str(e)}",
                state_name=self.name,
                error_type="States.Runtime",
            ) from e

    def _calculate_wait_duration(self, processor: Any, processed_input: Any) -> float:
        """
        Calculate wait duration in seconds based on state configuration.

        Args:
            processor: Path processor for extracting values
            processed_input: Input data after input path processing

        Returns:
            Wait duration in seconds (non-negative float)

        Raises:
            StateError: If wait calculation fails
        """
        try:
            if self.seconds is not None:
                return float(self.seconds)

            elif self.seconds_path is not None:
                return self._calculate_seconds_path_wait(processor, processed_input)

            elif self.timestamp is not None:
                return self._calculate_timestamp_wait(self.timestamp)

            elif self.timestamp_path is not None:
                return self._calculate_timestamp_path_wait(processor, processed_input)

            else:
                # Should not reach here due to validation
                return 0.0

        except StateError:
            raise
        except Exception as e:
            raise StateError(
                f"Failed to calculate wait duration in state '{self.name}': {str(e)}",
                state_name=self.name,
                error_type="States.Runtime",
            ) from e

    def _calculate_seconds_path_wait(self, processor: Any, processed_input: Any) -> float:
        """Calculate wait duration from seconds_path."""
        try:
            # Extract value from path
            seconds_value = processor.get(processed_input, self.seconds_path)

            # Convert to float
            seconds = self._to_number(seconds_value)

            if seconds < 0:
                raise ValueError("SecondsPath value must be non-negative")

            return seconds

        except Exception as e:
            raise StateError(
                f"Failed to extract SecondsPath " f"'{self.seconds_path}' in state '{self.name}': {str(e)}",
                state_name=self.name,
                error_type="States.Runtime",
            ) from e

    def _calculate_timestamp_wait(self, timestamp: str) -> float:
        """Calculate wait duration until a timestamp."""
        try:
            # Parse timestamp (ISO-8601 format)
            target_time = self._parse_timestamp(timestamp)

            # Calculate duration until target time
            now = datetime.now(timezone.utc)
            wait_duration = (target_time - now).total_seconds()

            # Don't wait if timestamp is in the past
            return max(0.0, wait_duration)

        except Exception as e:
            raise StateError(
                f"Failed to parse timestamp '{timestamp}' " f"in state '{self.name}': {str(e)}",
                state_name=self.name,
                error_type="States.Runtime",
            ) from e

    def _calculate_timestamp_path_wait(self, processor: Any, processed_input: Any) -> float:
        """Calculate wait duration from timestamp_path."""
        try:
            # Extract timestamp string from path
            timestamp_value = processor.get(processed_input, self.timestamp_path)

            if not isinstance(timestamp_value, str):
                raise ValueError("TimestampPath value must be a string")

            return self._calculate_timestamp_wait(timestamp_value)

        except StateError:
            raise
        except Exception as e:
            raise StateError(
                f"Failed to extract TimestampPath '{self.timestamp_path}' " f"in state '{self.name}': {str(e)}",
                state_name=self.name,
                error_type="States.Runtime",
            ) from e

    def _parse_timestamp(self, timestamp: str) -> datetime:
        """
        Parse ISO-8601 timestamp string.

        Args:
            timestamp: ISO-8601 formatted timestamp string

        Returns:
            Parsed datetime object with timezone

        Raises:
            ValueError: If timestamp format is invalid
        """
        # Try parsing with different ISO-8601 formats
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",  # RFC3339 with Z
            "%Y-%m-%dT%H:%M:%S%z",  # RFC3339 with timezone
            "%Y-%m-%dT%H:%M:%S.%fZ",  # RFC3339 with microseconds and Z
            "%Y-%m-%dT%H:%M:%S.%f%z",  # RFC3339 with microseconds and timezone
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp, fmt)
                # Ensure timezone-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        # If none of the formats work, raise error
        raise ValueError(f"Invalid timestamp format: {timestamp}. Expected ISO-8601 format.")

    def _to_number(self, value: Any) -> float:
        """
        Convert value to float.

        Args:
            value: Value to convert

        Returns:
            Converted float value

        Raises:
            ValueError: If value cannot be converted to number
        """
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Cannot convert string '{value}' to number")
        else:
            raise ValueError(f"Cannot convert {type(value).__name__} to number")

    def validate(self, skip_name=False, skip_type=False, skip_next_state=False) -> None:
        """
        Validate the Wait state configuration.

        Raises:
            ValueError: If the state configuration is invalid
        """
        # Wait state specific validations
        if self.type != "Wait":
            raise ValueError(f"Wait state '{self.name}' must have Type 'Wait', " f"got '{self.type}'")

        # Count how many wait methods are specified
        wait_methods_count = sum(
            [
                self.seconds is not None,
                self.seconds_path is not None,
                self.timestamp is not None,
                self.timestamp_path is not None,
            ]
        )

        if wait_methods_count == 0:
            raise ValueError(
                f"Wait state '{self.name}' must specify one of: " "Seconds, SecondsPath, Timestamp, or TimestampPath"
            )

        if wait_methods_count > 1:
            raise ValueError(
                f"Wait state '{self.name}' must specify only one of: "
                "Seconds, SecondsPath, Timestamp, or TimestampPath"
            )

        # Validate Seconds value if present
        if self.seconds is not None and self.seconds < 0:
            raise ValueError(f"Wait state '{self.name}' Seconds must be non-negative")

        # Call parent validation
        super().validate(skip_type=True, skip_next_state=False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the state
        """
        result = super().to_dict()

        # Add wait-specific fields
        wait_fields = {
            "Seconds": self.seconds,
            "SecondsPath": self.seconds_path,
            "Timestamp": self.timestamp,
            "TimestampPath": self.timestamp_path,
        }

        for key, value in wait_fields.items():
            if value is not None:
                result[key] = value

        return result

    def __str__(self) -> str:
        """String representation of the state."""
        return f"WaitState(name={self.name})"

    def __repr__(self) -> str:
        """Detailed representation of the state."""
        wait_method = None
        if self.seconds is not None:
            wait_method = f"seconds={self.seconds}"
        elif self.seconds_path is not None:
            wait_method = f"seconds_path={self.seconds_path!r}"
        elif self.timestamp is not None:
            wait_method = f"timestamp={self.timestamp!r}"
        elif self.timestamp_path is not None:
            wait_method = f"timestamp_path={self.timestamp_path!r}"

        return (
            f"WaitState("
            f"name={self.name!r}, "
            f"next_state={self.next_state!r}, "
            f"end={self.end!r}, "
            f"{wait_method}"
            ")"
        )
