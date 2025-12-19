"""
Tests for the base state classes and related functionality.
"""
import json
from typing import Any, Dict, Optional

import pytest

from src.states.base import (
    BaseState,
    CatchRule,
    PathProcessor,
    RetryRule,
    StateError,
    StateExecutionError,
    StateTaskFailedError,
    StateTimeoutError,
    StateValidationError,
    get_path_processor,
    set_path_processor,
    temporary_path_processor,
)


# Test PathProcessor Protocol Implementation
class MockPathProcessor:
    """Mock PathProcessor for testing."""

    def apply_input_path(self, input_data: Any, path: Optional[str]) -> Any:
        if path == "$.test":
            return {"test": "value"}
        return input_data

    def apply_result_path(
        self, input_data: Any, result: Any, path: Optional[str]
    ) -> Any:
        if path == "$.result":
            return {"original": input_data, "result": result}
        return result

    def apply_output_path(self, output: Any, path: Optional[str]) -> Any:
        if path == "$.output":
            return {"output": output}
        return output


# Test Concrete BaseState Implementation for Testing
class ConcreteState(BaseState):
    """Concrete implementation of BaseState for testing."""

    def __init__(
        self,
        name: str,
        type: str = "Test",
        next_state: Optional[str] = None,
        end: bool = False,
        input_path: Optional[str] = None,
        result_path: Optional[str] = None,
        output_path: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        self.name = name
        self.type = type
        self.next_state = next_state
        self.end = end
        self.input_path = input_path
        self.result_path = result_path
        self.output_path = output_path
        self.comment = comment
        # don't call super().__init__() and expect it to work fine
        # super class is an abstract class and it will spoil the show
        # since all optional parameters passed will be ignored and only strict
        # parameters will work.
        super().__post_init__()

    async def execute(
        self, input_data: Any, context: Optional[Dict[str, Any]] = None
    ) -> tuple[Any, Optional[str]]:
        """Test execution that returns input + 1."""
        if context and context.get("fail"):
            raise StateExecutionError("Test failure")

        result = input_data + 1 if isinstance(input_data, (int, float)) else input_data
        return result, self.next_state


# Test Classes
class TestRetryRule:
    """Tests for RetryRule class."""

    def test_retry_rule_creation(self):
        """Test basic RetryRule creation."""
        rule = RetryRule(
            error_equals=["States.Timeout", "States.TaskFailed"],
            interval_seconds=5,
            max_attempts=3,
            backoff_rate=2.0,
        )

        assert rule.error_equals == ["States.Timeout", "States.TaskFailed"]
        assert rule.interval_seconds == 5
        assert rule.max_attempts == 3
        assert rule.backoff_rate == 2.0
        assert rule.max_delay_seconds is None
        assert rule.jitter_strategy is None

    def test_retry_rule_defaults(self):
        """Test RetryRule with default values."""
        rule = RetryRule(error_equals=["States.Timeout"])

        assert rule.error_equals == ["States.Timeout"]
        assert rule.interval_seconds == 1
        assert rule.max_attempts is None
        assert rule.backoff_rate == 2.0
        assert rule.max_delay_seconds is None
        assert rule.jitter_strategy is None

    def test_retry_rule_validation_empty_errors(self):
        """Test RetryRule validation with empty error_equals."""
        with pytest.raises(ValueError, match="ErrorEquals cannot be empty"):
            RetryRule(error_equals=[])

    def test_retry_rule_validation_negative_interval(self):
        """Test RetryRule validation with negative interval."""
        with pytest.raises(ValueError, match="IntervalSeconds must be >= 0"):
            RetryRule(error_equals=["States.Timeout"], interval_seconds=-1)

    def test_retry_rule_validation_negative_max_attempts(self):
        """Test RetryRule validation with negative max_attempts."""
        with pytest.raises(ValueError, match="MaxAttempts must be >= 0"):
            RetryRule(error_equals=["States.Timeout"], max_attempts=-1)

    def test_retry_rule_validation_invalid_backoff_rate(self):
        """Test RetryRule validation with invalid backoff_rate."""
        with pytest.raises(ValueError, match="BackoffRate must be >= 1.0"):
            RetryRule(error_equals=["States.Timeout"], backoff_rate=0.5)

    def test_retry_rule_to_dict(self):
        """Test RetryRule to_dict method."""
        rule = RetryRule(
            error_equals=["States.Timeout", "States.TaskFailed"],
            interval_seconds=5,
            max_attempts=3,
            backoff_rate=2.5,
            max_delay_seconds=60,
            jitter_strategy="FULL",
        )

        result = rule.to_dict()

        assert result["ErrorEquals"] == ["States.Timeout", "States.TaskFailed"]
        assert result["IntervalSeconds"] == 5
        assert result["MaxAttempts"] == 3
        assert result["BackoffRate"] == 2.5
        assert result["MaxDelaySeconds"] == 60
        assert result["JitterStrategy"] == "FULL"

    def test_retry_rule_to_dict_defaults(self):
        """Test RetryRule to_dict with default values."""
        rule = RetryRule(error_equals=["States.Timeout"])

        result = rule.to_dict()

        assert result["ErrorEquals"] == ["States.Timeout"]
        assert "IntervalSeconds" not in result  # Default value omitted
        assert "MaxAttempts" not in result
        assert "BackoffRate" not in result
        assert "MaxDelaySeconds" not in result
        assert "JitterStrategy" not in result


class TestCatchRule:
    """Tests for CatchRule class."""

    def test_catch_rule_creation(self):
        """Test basic CatchRule creation."""
        rule = CatchRule(
            error_equals=["States.Timeout"],
            next_state="ErrorState",
            result_path="$.error",
        )

        assert rule.error_equals == ["States.Timeout"]
        assert rule.next_state == "ErrorState"
        assert rule.result_path == "$.error"

    def test_catch_rule_validation_empty_errors(self):
        """Test CatchRule validation with empty error_equals."""
        with pytest.raises(ValueError, match="ErrorEquals cannot be empty"):
            CatchRule(error_equals=[], next_state="ErrorState")

    def test_catch_rule_validation_empty_next(self):
        """Test CatchRule validation with empty next."""
        with pytest.raises(ValueError, match="Next cannot be empty"):
            CatchRule(error_equals=["States.Timeout"], next_state="")

    def test_catch_rule_to_dict(self):
        """Test CatchRule to_dict method."""
        rule = CatchRule(
            error_equals=["States.Timeout", "States.TaskFailed"],
            next_state="ErrorHandler",
            result_path="$.error",
        )

        result = rule.to_dict()

        assert result["ErrorEquals"] == ["States.Timeout", "States.TaskFailed"]
        assert result["Next"] == "ErrorHandler"
        assert result["ResultPath"] == "$.error"

    def test_catch_rule_to_dict_no_result_path(self):
        """Test CatchRule to_dict without result_path."""
        rule = CatchRule(
            error_equals=["States.Timeout"],
            next_state="ErrorHandler",
        )

        result = rule.to_dict()

        assert result["ErrorEquals"] == ["States.Timeout"]
        assert result["Next"] == "ErrorHandler"
        assert "ResultPath" not in result


class TestBaseState:
    """Tests for BaseState abstract class via ConcreteState."""

    def test_base_state_creation(self):
        """Test basic BaseState creation."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
            input_path="$.input",
            result_path="$.result",
            output_path="$.output",
            comment="Test comment",
        )

        assert state.name == "TestState"
        assert state.type == "Task"
        assert state.next_state == "NextState"
        assert state.input_path == "$.input"
        assert state.result_path == "$.result"
        assert state.output_path == "$.output"
        assert state.comment == "Test comment"
        assert not state.end

    def test_base_state_end_state(self):
        """Test BaseState as end state."""
        state = ConcreteState(
            name="EndState",
            type="Succeed",
            end=True,
        )

        assert state.name == "EndState"
        assert state.type == "Succeed"
        assert state.end is True
        assert state.next_state is None

    def test_base_state_validation_empty_name(self):
        """Test BaseState validation with empty name."""

        class InvalidState(ConcreteState):
            def __init__(self, name: str):
                self.name = ""
                self.type = "Task"
                self.next_state = "Next"
                super().__init__(None)

        with pytest.raises(ValueError, match="State name cannot be empty"):
            InvalidState(None)

    def test_base_state_validation_empty_type(self):
        """Test BaseState validation with empty type."""

        class InvalidState(ConcreteState):
            def __init__(self, name: Optional[str] = None):
                self.name = "Test"
                self.type = ""
                self.next_state = "Next"
                super().__init__(self.name, self.type)

        with pytest.raises(ValueError, match="State type cannot be empty"):
            InvalidState("Test")

    def test_base_state_validation_no_next_or_end(self):
        """Test BaseState validation without Next or End."""

        class InvalidState(ConcreteState):
            def __init__(self, name: str, type: str):
                super().__init__(name, type)
                self.name = name
                self.type = type
                self.next_state = None
                self.end = False

        with pytest.raises(ValueError, match="State must have either Next or End"):
            InvalidState("Test", "Task")

    def test_base_state_validation_both_next_and_end(self):
        """Test BaseState validation with both Next and End."""

        class InvalidState(ConcreteState):
            def __init__(
                self,
                name: Optional[str] = "Test",
                type: Optional[str] = "Task",
                next_state: Optional[str] = "Next",
                end: Optional[bool] = True,
            ):
                super().__init__(name, type, next_state, end)
                self.name = name
                self.type = type
                self.next_state = next_state
                self.end = end

        with pytest.raises(ValueError, match="State cannot have both Next and End"):
            InvalidState()

    def test_base_state_properties(self):
        """Test BaseState property getters."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
        )

        assert state.state_name == "TestState"
        assert state.state_type == "Task"
        assert state.get_next() == "NextState"
        assert state.is_end() is False

    def test_base_state_end_state_properties(self):
        """Test BaseState properties for end state."""
        state = ConcreteState(
            name="EndState",
            type="Succeed",
            end=True,
        )

        assert state.get_next() is None
        assert state.is_end() is True

    def test_base_state_get_next_states(self):
        """Test BaseState get_next_states method."""
        # State with next
        state1 = ConcreteState(
            name="State1",
            type="Task",
            next_state="State2",
        )
        assert state1.get_next_states() == ["State2"]

        # End state
        state2 = ConcreteState(
            name="EndState",
            type="Succeed",
            end=True,
        )
        assert state2.get_next_states() == []

    def test_base_state_to_dict(self):
        """Test BaseState to_dict method."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
            input_path="$.input",
            result_path="$.result",
            output_path="$.output",
            comment="Test state",
        )

        result = state.to_dict()

        assert result["Type"] == "Task"
        assert result["Next"] == "NextState"
        assert result["InputPath"] == "$.input"
        assert result["ResultPath"] == "$.result"
        assert result["OutputPath"] == "$.output"
        assert result["Comment"] == "Test state"
        assert "End" not in result

    def test_base_state_to_dict_end_state(self):
        """Test BaseState to_dict for end state."""
        state = ConcreteState(
            name="EndState",
            type="Succeed",
            end=True,
        )

        result = state.to_dict()

        assert result["Type"] == "Succeed"
        assert result["End"] is True
        assert "Next" not in result
        assert "InputPath" not in result
        assert "ResultPath" not in result
        assert "OutputPath" not in result
        assert "Comment" not in result

    def test_base_state_to_json(self):
        """Test BaseState to_json method."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
        )

        json_str = state.to_json()
        result = json.loads(json_str)

        assert result["Type"] == "Task"
        assert result["Next"] == "NextState"

    def test_base_state_to_json_indented(self):
        """Test BaseState to_json with indentation."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
        )

        json_str = state.to_json(indent=2)
        assert "\n  " in json_str  # Check for indentation

    def test_base_state_string_representations(self):
        """Test BaseState string representations."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
        )

        assert str(state) == "TaskState(name=TestState)"
        assert "ConcreteState" in repr(state)
        assert "TestState" in repr(state)
        assert "Task" in repr(state)

    @pytest.mark.asyncio
    async def test_base_state_execute(self):
        """Test BaseState execute method."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
        )

        output, next_state =  await state.execute(42)

        assert output == 43  # input + 1
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_base_state_execute_with_context(self):
        """Test BaseState execute with context."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
        )

        # Test with context but no failure
        output, next_state =  await state.execute(42, {"test": "value"})

        assert output == 43
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_base_state_execute_failure(self):
        """Test BaseState execute with failure context."""
        state = ConcreteState(
            name="TestState",
            type="Task",
            next_state="NextState",
        )

        # Test with failure context
        with pytest.raises(StateExecutionError, match="Test failure"):
            await state.execute(42, {"fail": True})

    def test_base_state_set_path_processor(self):
        """Test BaseState set_path_processor method."""
        state = ConcreteState(name="TestState", type="Task", end=True)

        processor = MockPathProcessor()
        state.set_path_processor(processor)

        assert state._path_processor is processor


class TestPathProcessorFunctions:
    """Tests for path processor module functions."""

    def test_get_path_processor(self):
        """Test get_path_processor function."""
        processor = get_path_processor()
        assert processor is not None
        assert hasattr(processor, "apply_input_path")
        assert hasattr(processor, "apply_result_path")
        assert hasattr(processor, "apply_output_path")

    def test_set_path_processor(self):
        """Test set_path_processor function."""
        original = get_path_processor()
        new_processor = MockPathProcessor()

        set_path_processor(new_processor)
        assert get_path_processor() is new_processor

        # Restore original
        set_path_processor(original)

    def test_temporary_path_processor(self):
        """Test temporary_path_processor context manager."""
        original = get_path_processor()
        temp_processor = MockPathProcessor()

        with temporary_path_processor(temp_processor):
            assert get_path_processor() is temp_processor

        assert get_path_processor() is original


class TestStateErrors:
    """Tests for state error classes."""

    def test_state_error_basic(self):
        """Test basic StateError."""
        error = StateError("Something went wrong")

        assert str(error) == "Error: Something went wrong | Type: States.Runtime"
        assert error.message == "Something went wrong"
        assert error.state_name is None
        assert error.error_type == "States.Runtime"

    def test_state_error_with_state_name(self):
        """Test StateError with state name."""
        error = StateError("Execution failed", state_name="MyState")

        assert "State: MyState" in str(error)
        assert error.state_name == "MyState"

    def test_state_error_with_custom_type(self):
        """Test StateError with custom error type."""
        error = StateError("Custom error", error_type="Custom.Error")

        assert error.error_type == "Custom.Error"
        assert "Type: Custom.Error" in str(error)

    def test_state_validation_error(self):
        """Test StateValidationError."""
        error = StateValidationError("Invalid configuration", "MyState")

        assert error.error_type == "States.Validation"
        assert "State: MyState" in str(error)
        assert "Error: Invalid configuration" in str(error)

    def test_state_execution_error(self):
        """Test StateExecutionError."""
        error = StateExecutionError("Execution failed", "TaskState")

        assert error.error_type == "States.Runtime"
        assert "State: TaskState" in str(error)

    def test_state_timeout_error(self):
        """Test StateTimeoutError."""
        error = StateTimeoutError("Operation timed out", "TimeoutState")

        assert error.error_type == "States.Timeout"
        assert "State: TimeoutState" in str(error)

    def test_state_task_failed_error(self):
        """Test StateTaskFailedError."""
        error = StateTaskFailedError("Task failed to complete", "TaskState")

        assert error.error_type == "States.TaskFailed"
        assert "State: TaskState" in str(error)


# Test PathProcessor Protocol
class TestPathProcessorProtocol:
    """Tests for PathProcessor protocol."""

    def test_mock_processor_implements_protocol(self):
        """Test that MockPathProcessor implements PathProcessor protocol."""
        processor = MockPathProcessor()
        assert isinstance(processor, PathProcessor)

    def test_mock_processor_methods(self):
        """Test MockPathProcessor methods."""
        processor = MockPathProcessor()

        # Test apply_input_path
        result = processor.apply_input_path({"key": "value"}, "$.test")
        assert result == {"test": "value"}

        result = processor.apply_input_path({"key": "value"}, None)
        assert result == {"key": "value"}

        # Test apply_result_path
        result = processor.apply_result_path(
            {"input": "data"}, "result_data", "$.result"
        )
        assert result == {"original": {"input": "data"}, "result": "result_data"}

        result = processor.apply_result_path({"input": "data"}, "result_data", None)
        assert result == "result_data"

        # Test apply_output_path
        result = processor.apply_output_path("output_data", "$.output")
        assert result == {"output": "output_data"}

        result = processor.apply_output_path("output_data", None)
        assert result == "output_data"
