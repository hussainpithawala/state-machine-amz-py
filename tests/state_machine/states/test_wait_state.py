"""
Tests for the WaitState implementation.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from src.states.base import StateError
from src.states.wait_state import WaitState


class TestWaitState:
    """Test suite for WaitState."""

    @pytest.fixture
    def mock_path_processor(self):
        """Create a mock path processor."""
        processor = Mock()
        processor.apply_input_path = Mock(side_effect=lambda data, path: data)
        processor.apply_result_path = Mock(side_effect=lambda input_data, result, path: input_data)
        processor.apply_output_path = Mock(side_effect=lambda data, path: data)
        processor.get = Mock(side_effect=lambda data, path: data.get(path.strip("$."), None))
        return processor

    @pytest.fixture
    def sample_input_data(self):
        """Sample input data for testing."""
        return {"key": "value", "duration": 1, "data": "test"}

    # Test initialization and basic properties

    def test_wait_state_creation_with_seconds(self):
        """Test basic WaitState creation with Seconds."""
        state = WaitState(name="TestWaitState", next_state="NextState", seconds=5, comment="Test wait state")

        assert state.name == "TestWaitState"
        assert state.type == "Wait"
        assert state.next_state == "NextState"
        assert state.seconds == 5
        assert state.seconds_path is None
        assert state.timestamp is None
        assert state.timestamp_path is None
        assert state.comment == "Test wait state"

    def test_wait_state_creation_with_seconds_path(self):
        """Test WaitState creation with SecondsPath."""
        state = WaitState(name="WaitWithPath", next_state="NextState", seconds_path="$.duration")

        assert state.seconds is None
        assert state.seconds_path == "$.duration"
        assert state.timestamp is None
        assert state.timestamp_path is None

    def test_wait_state_creation_with_timestamp(self):
        """Test WaitState creation with Timestamp."""
        timestamp = "2025-12-31T23:59:59Z"
        state = WaitState(name="WaitUntil", end=True, timestamp=timestamp)

        assert state.seconds is None
        assert state.seconds_path is None
        assert state.timestamp == timestamp
        assert state.timestamp_path is None
        assert state.end is True

    def test_wait_state_creation_with_timestamp_path(self):
        """Test WaitState creation with TimestampPath."""
        state = WaitState(name="WaitUntilPath", next_state="NextState", timestamp_path="$.waitUntil")

        assert state.seconds is None
        assert state.seconds_path is None
        assert state.timestamp is None
        assert state.timestamp_path == "$.waitUntil"

    def test_wait_state_type_fixed(self):
        """Test that WaitState always has Type 'Wait'."""
        state = WaitState(name="TestWait", seconds=1, next_state="Next")
        state.type = "WrongType"
        state.__post_init__()
        assert state.type == "Wait"

    # Test validation

    def test_wait_state_validation_valid_seconds(self):
        """Test validation with valid Seconds."""
        state = WaitState(name="ValidWait", next_state="Next", seconds=5)
        state.validate()  # Should not raise

    def test_wait_state_validation_valid_seconds_path(self):
        """Test validation with valid SecondsPath."""
        state = WaitState(name="ValidWait", next_state="Next", seconds_path="$.duration")
        state.validate()  # Should not raise

    def test_wait_state_validation_valid_timestamp(self):
        """Test validation with valid Timestamp."""
        state = WaitState(name="ValidWait", next_state="Next", timestamp="2025-12-31T23:59:59Z")
        state.validate()  # Should not raise

    def test_wait_state_validation_valid_timestamp_path(self):
        """Test validation with valid TimestampPath."""
        state = WaitState(name="ValidWait", next_state="Next", timestamp_path="$.timestamp")
        state.validate()  # Should not raise

    def test_wait_state_validation_no_wait_method(self):
        """Test validation with no wait method specified."""
        with pytest.raises(ValueError, match="must specify one of"):
            WaitState(name="InvalidWait", next_state="Next").validate()

    def test_wait_state_validation_multiple_wait_methods(self):
        """Test validation with multiple wait methods."""
        with pytest.raises(ValueError, match="must specify only one of"):
            WaitState(name="InvalidWait", next_state="Next", seconds=5, seconds_path="$.duration").validate()

    def test_wait_state_validation_negative_seconds(self):
        """Test validation with negative Seconds."""
        with pytest.raises(ValueError, match="must be non-negative"):
            WaitState(name="InvalidWait", next_state="Next", seconds=-1).validate()

    def test_wait_state_validation_wrong_type(self):
        """Test validation with wrong type."""
        state = WaitState(name="WrongType", next_state="Next", seconds=1)
        state.type = "Pass"

        with pytest.raises(ValueError, match="must have Type 'Wait'"):
            state.validate()

    # Test execute method with Seconds

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_seconds(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with Seconds."""
        state = WaitState(name="WaitSeconds", next_state="NextState", seconds=1)
        state.set_path_processor(mock_path_processor)

        start_time = time.time()
        output, next_state = await state.execute(sample_input_data)
        elapsed = time.time() - start_time

        assert output == sample_input_data
        assert next_state == "NextState"

        # Verify we waited approximately 1 second (with tolerance)
        assert elapsed >= 1.0
        assert elapsed < 2.0

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_zero_seconds(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with zero Seconds."""
        state = WaitState(name="WaitZero", next_state="NextState", seconds=0)
        state.set_path_processor(mock_path_processor)

        start_time = time.time()
        output, next_state = await state.execute(sample_input_data)
        elapsed = time.time() - start_time

        assert output == sample_input_data
        assert next_state == "NextState"

        # Should complete immediately
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_fractional_seconds(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with fractional seconds."""
        # Use a small fractional value for faster test
        state = WaitState(name="WaitFractional", next_state="NextState", seconds=0.5)
        state.set_path_processor(mock_path_processor)

        start_time = time.time()
        output, next_state = await state.execute(sample_input_data)
        elapsed = time.time() - start_time

        assert output == sample_input_data
        assert next_state == "NextState"

        assert elapsed >= 0.5
        assert elapsed < 1.0

    # Test execute method with SecondsPath

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_seconds_path(self, mock_path_processor):
        """Test WaitState execution with SecondsPath."""
        state = WaitState(name="WaitSecondsPath", next_state="NextState", seconds_path="$.duration")

        # Configure mock to return duration value
        mock_path_processor.get = Mock(return_value=1)
        state.set_path_processor(mock_path_processor)

        input_data = {"duration": 1, "key": "value"}

        start_time = time.time()
        output, next_state = await state.execute(input_data)
        elapsed = time.time() - start_time

        assert output == input_data
        assert next_state == "NextState"

        assert elapsed >= 1.0
        mock_path_processor.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_state_execute_seconds_path_with_float(self, mock_path_processor):
        """Test WaitState execution with SecondsPath returning float."""
        state = WaitState(name="WaitFloat", next_state="NextState", seconds_path="$.duration")

        mock_path_processor.get = Mock(return_value=0.5)
        state.set_path_processor(mock_path_processor)

        input_data = {"duration": 0.5}

        start_time = time.time()
        output, next_state = await state.execute(input_data)
        elapsed = time.time() - start_time

        assert elapsed >= 0.5
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_wait_state_execute_seconds_path_invalid_value(self, mock_path_processor):
        """Test WaitState execution with SecondsPath returning invalid value."""
        state = WaitState(name="WaitInvalid", next_state="NextState", seconds_path="$.duration")

        mock_path_processor.get = Mock(return_value="not a number")
        state.set_path_processor(mock_path_processor)

        input_data = {"duration": "invalid"}

        with pytest.raises(StateError, match="Failed to extract SecondsPath"):
            await state.execute(input_data)

    @pytest.mark.asyncio
    async def test_wait_state_execute_seconds_path_negative(self, mock_path_processor):
        """Test WaitState execution with SecondsPath returning negative value."""
        state = WaitState(name="WaitNegative", next_state="NextState", seconds_path="$.duration")

        mock_path_processor.get = Mock(return_value=-5)
        state.set_path_processor(mock_path_processor)

        input_data = {"duration": -5}

        with pytest.raises(StateError, match="must be non-negative"):
            await state.execute(input_data)

    # Test execute method with Timestamp

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_timestamp(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with Timestamp."""
        # Set timestamp to 1 second in the future
        future_time = datetime.now(timezone.utc) + timedelta(seconds=2)
        timestamp = future_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        state = WaitState(name="WaitTimestamp", end=True, timestamp=timestamp)
        state.set_path_processor(mock_path_processor)

        start_time = time.time()
        output, next_state = await state.execute(sample_input_data)
        elapsed = time.time() - start_time

        assert output == sample_input_data
        assert next_state is None  # End state

        # Should wait approximately 1 second
        assert elapsed >= 0.9  # Allow slight tolerance

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_past_timestamp(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with past Timestamp."""
        # Set timestamp to 1 second in the past
        past_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        timestamp = past_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        state = WaitState(name="WaitPast", end=True, timestamp=timestamp)
        state.set_path_processor(mock_path_processor)

        start_time = time.time()
        output, next_state = await state.execute(sample_input_data)
        elapsed = time.time() - start_time

        assert output == sample_input_data
        assert next_state is None

        # Should complete immediately without waiting
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_invalid_timestamp(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with invalid Timestamp format."""
        state = WaitState(name="WaitInvalidTimestamp", next_state="Next", timestamp="not-a-timestamp")
        state.set_path_processor(mock_path_processor)

        with pytest.raises(StateError, match="Failed to parse timestamp"):
            await state.execute(sample_input_data)

    @pytest.mark.asyncio
    async def test_wait_state_execute_timestamp_with_microseconds(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with Timestamp including microseconds."""
        future_time = datetime.now(timezone.utc) + timedelta(seconds=0.5)
        timestamp = future_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        state = WaitState(name="WaitMicro", next_state="Next", timestamp=timestamp)
        state.set_path_processor(mock_path_processor)

        start_time = time.time()
        output, next_state = await state.execute(sample_input_data)
        elapsed = time.time() - start_time

        assert elapsed >= 0.4  # Allow tolerance

    # Test execute method with TimestampPath

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_timestamp_path(self, mock_path_processor):
        """Test WaitState execution with TimestampPath."""
        future_time = datetime.now(timezone.utc) + timedelta(seconds=2)
        timestamp = future_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        state = WaitState(name="WaitTimestampPath", next_state="NextState", timestamp_path="$.waitUntil")

        mock_path_processor.get = Mock(return_value=timestamp)
        state.set_path_processor(mock_path_processor)

        input_data = {"waitUntil": timestamp, "data": "test"}

        start_time = time.time()
        output, next_state = await state.execute(input_data)
        elapsed = time.time() - start_time

        assert output == input_data
        assert next_state == "NextState"

        assert elapsed >= 0.9  # Allow tolerance

    @pytest.mark.asyncio
    async def test_wait_state_execute_timestamp_path_not_string(self, mock_path_processor):
        """Test WaitState execution with TimestampPath returning non-string."""
        state = WaitState(name="WaitInvalidPath", next_state="Next", timestamp_path="$.timestamp")

        mock_path_processor.get = Mock(return_value=12345)
        state.set_path_processor(mock_path_processor)

        input_data = {"timestamp": 12345}

        with pytest.raises(StateError, match="must be a string"):
            await state.execute(input_data)

    # Test task cancellation

    @pytest.mark.asyncio
    async def test_wait_state_execute_task_cancellation(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with task cancellation."""
        state = WaitState(name="WaitCancel", next_state="Next", seconds=10)
        state.set_path_processor(mock_path_processor)

        # Create task and cancel it
        task = asyncio.create_task(state.execute(sample_input_data))

        # Give it a moment to start waiting
        await asyncio.sleep(0.1)

        # Cancel the task
        task.cancel()

        with pytest.raises(StateError, match="was cancelled"):
            await task

    # Test with paths

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_input_path(self, mock_path_processor):
        """Test WaitState execution with input path."""
        state = WaitState(name="WaitInputPath", next_state="Next", seconds=0, input_path="$.data")

        mock_path_processor.apply_input_path = Mock(return_value={"filtered": "data"})
        state.set_path_processor(mock_path_processor)

        input_data = {"data": {"filtered": "data"}, "other": "ignored"}

        output, next_state = await state.execute(input_data)

        mock_path_processor.apply_input_path.assert_called_once_with(input_data, "$.data")

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_result_path(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with result path."""
        state = WaitState(name="WaitResultPath", next_state="Next", seconds=0, result_path="$.result")
        state.set_path_processor(mock_path_processor)

        output, next_state = await state.execute(sample_input_data)

        mock_path_processor.apply_result_path.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_output_path(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with output path."""
        state = WaitState(name="WaitOutputPath", next_state="Next", seconds=0, output_path="$.output")
        state.set_path_processor(mock_path_processor)

        output, next_state = await state.execute(sample_input_data)

        mock_path_processor.apply_output_path.assert_called_once()

    # Test to_dict method

    def test_wait_state_to_dict_with_seconds(self):
        """Test to_dict with Seconds."""
        state = WaitState(name="WaitSeconds", next_state="Next", seconds=5)

        result = state.to_dict()

        assert result == {"Type": "Wait", "Next": "Next", "Seconds": 5}

    def test_wait_state_to_dict_with_seconds_path(self):
        """Test to_dict with SecondsPath."""
        state = WaitState(name="WaitPath", next_state="Next", seconds_path="$.duration")

        result = state.to_dict()

        assert result == {"Type": "Wait", "Next": "Next", "SecondsPath": "$.duration"}

    def test_wait_state_to_dict_with_timestamp(self):
        """Test to_dict with Timestamp."""
        timestamp = "2025-12-31T23:59:59Z"
        state = WaitState(name="WaitUntil", end=True, timestamp=timestamp)

        result = state.to_dict()

        assert result == {"Type": "Wait", "End": True, "Timestamp": timestamp}

    def test_wait_state_to_dict_with_timestamp_path(self):
        """Test to_dict with TimestampPath."""
        state = WaitState(name="WaitUntilPath", next_state="Next", timestamp_path="$.waitUntil")

        result = state.to_dict()

        assert result == {"Type": "Wait", "Next": "Next", "TimestampPath": "$.waitUntil"}

    def test_wait_state_to_dict_complete(self):
        """Test to_dict with all allowed fields."""
        state = WaitState(
            name="CompleteWait",
            next_state="Next",
            input_path="$.input",
            result_path="$.result",
            output_path="$.output",
            seconds=10,
            comment="Complete wait state",
        )

        result = state.to_dict()

        assert result == {
            "Type": "Wait",
            "Next": "Next",
            "InputPath": "$.input",
            "ResultPath": "$.result",
            "OutputPath": "$.output",
            "Seconds": 10,
            "Comment": "Complete wait state",
        }

    # Test to_json method

    def test_wait_state_to_json(self):
        """Test to_json method."""
        state = WaitState(name="JsonWait", next_state="Next", seconds=5)

        json_str = state.to_json()
        result = json.loads(json_str)

        assert result == {"Type": "Wait", "Next": "Next", "Seconds": 5}

    def test_wait_state_to_json_indented(self):
        """Test to_json with indentation."""
        state = WaitState(name="IndentedWait", next_state="Next", seconds=5)

        json_str = state.to_json(indent=2)
        assert "\n  " in json_str

    # Test get_next_states method

    def test_wait_state_get_next_states(self):
        """Test get_next_states method."""
        state = WaitState(name="TestWait", next_state="NextState", seconds=1)

        next_states = state.get_next_states()

        assert next_states == ["NextState"]

    def test_wait_state_get_next_states_end(self):
        """Test get_next_states for end state."""
        state = WaitState(name="EndWait", end=True, seconds=1)

        next_states = state.get_next_states()

        assert next_states == []

    # Test string representations

    def test_wait_state_str(self):
        """Test string representation."""
        state = WaitState(name="TestWait", next_state="Next", seconds=5)

        assert str(state) == "WaitState(name=TestWait)"

    def test_wait_state_repr_with_seconds(self):
        """Test detailed representation with Seconds."""
        state = WaitState(name="TestWait", next_state="Next", seconds=5)

        repr_str = repr(state)
        assert "WaitState" in repr_str
        assert "name='TestWait'" in repr_str
        assert "seconds=5" in repr_str

    def test_wait_state_repr_with_timestamp(self):
        """Test detailed representation with Timestamp."""
        timestamp = "2025-12-31T23:59:59Z"
        state = WaitState(name="TestWait", end=True, timestamp=timestamp)

        repr_str = repr(state)
        assert "WaitState" in repr_str
        assert "timestamp=" in repr_str

    # Test edge cases

    @pytest.mark.asyncio
    async def test_wait_state_execute_with_context(self, mock_path_processor, sample_input_data):
        """Test WaitState execution with context."""
        state = WaitState(name="ContextWait", next_state="Next", seconds=0)
        state.set_path_processor(mock_path_processor)

        context = {"execution_id": "test-123"}

        output, next_state = await state.execute(sample_input_data, context)

        assert output == sample_input_data

    @pytest.mark.asyncio
    async def test_wait_state_execute_nil_input(self, mock_path_processor):
        """Test WaitState execution with None input."""
        state = WaitState(name="NilWait", next_state="Next", seconds=0)
        state.set_path_processor(mock_path_processor)

        output, next_state = await state.execute(None)

        assert output is None

    @pytest.mark.asyncio
    async def test_wait_state_integration_real_processor(self):
        """Test WaitState integration with real processor."""
        from src.states.json_path import JSONPathProcessor

        processor = JSONPathProcessor()
        state = WaitState(name="IntegrationWait", next_state="Next", seconds=0)
        state.set_path_processor(processor)

        input_data = {"key": "value"}

        output, next_state = await state.execute(input_data)

        assert output == input_data
        assert next_state == "Next"

    # Test inheritance

    def test_wait_state_inheritance(self):
        """Test that WaitState properly inherits from BaseState."""
        state = WaitState(name="InheritanceTest", next_state="Next", seconds=1)

        assert hasattr(state, "execute")
        assert hasattr(state, "validate")
        assert hasattr(state, "to_dict")
        assert hasattr(state, "to_json")
        assert hasattr(state, "get_next_states")
        assert hasattr(state, "set_path_processor")

        assert state.state_name == "InheritanceTest"
        assert state.state_type == "Wait"
        assert state.get_next() == "Next"
        assert state.is_end() is False

    # Test concurrent execution

    @pytest.mark.asyncio
    async def test_wait_state_concurrent_execution(self):
        """Test concurrent execution of WaitState."""
        state = WaitState(name="ConcurrentWait", next_state="Next", seconds=0)

        mock_processor = Mock()
        mock_processor.apply_input_path = Mock(side_effect=lambda data, path: data)
        mock_processor.apply_result_path = Mock(side_effect=lambda inp, res, path: inp)
        mock_processor.apply_output_path = Mock(side_effect=lambda data, path: data)

        state.set_path_processor(mock_processor)

        num_tasks = 5
        tasks = []

        for i in range(num_tasks):
            input_data = {"id": i, "data": f"task_{i}"}
            task = asyncio.create_task(state.execute(input_data))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        assert len(results) == num_tasks
        for i, (output, next_state) in enumerate(results):
            assert output["id"] == i
            assert next_state == "Next"

    # Test timestamp parsing formats

    @pytest.mark.asyncio
    async def test_wait_state_timestamp_formats(self, mock_path_processor, sample_input_data):
        """Test various ISO-8601 timestamp formats."""
        formats = [
            "2025-12-31T23:59:59Z",
            "2025-12-31T23:59:59+00:00",
            "2025-12-31T23:59:59.123456Z",
        ]

        for timestamp_format in formats:
            # Use past timestamp to avoid waiting
            past_time = datetime.now(timezone.utc) - timedelta(seconds=1)

            if ".%f" in timestamp_format:
                timestamp = past_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            elif "+00:00" in timestamp_format:
                timestamp = past_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            else:
                timestamp = past_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            state = WaitState(name="FormatTest", next_state="Next", timestamp=timestamp)
            state.set_path_processor(mock_path_processor)

            output, next_state = await state.execute(sample_input_data)

    # Test helper methods

    def test_wait_state_to_number_conversion(self):
        """Test _to_number helper method."""
        state = WaitState(name="TestConvert", next_state="Next", seconds=1)

        # Test various numeric types
        assert state._to_number(5) == 5.0
        assert state._to_number(5.5) == 5.5
        assert state._to_number("10") == 10.0
        assert state._to_number("3.14") == 3.14

        # Test invalid conversions
        with pytest.raises(ValueError):
            state._to_number("not a number")

        with pytest.raises(ValueError):
            state._to_number({"key": "value"})

    def test_wait_state_parse_timestamp_invalid(self):
        """Test _parse_timestamp with invalid format."""
        state = WaitState(name="TestParse", next_state="Next", seconds=1)

        with pytest.raises(ValueError, match="Invalid timestamp format"):
            state._parse_timestamp("not-a-timestamp")
