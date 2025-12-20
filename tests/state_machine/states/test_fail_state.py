"""
Tests for the FailState implementation.
"""

import json

import pytest

from src.states.base import StateError
from src.states.fail_state import FailState


class TestFailState:
    """Test suite for FailState."""

    @pytest.fixture
    def sample_input_data(self):
        """Sample input data for testing."""
        return {"data": "input data", "metadata": {"source": "test", "timestamp": "2024-01-15"}, "count": 42}

    # Test initialization and basic properties

    def test_fail_state_creation(self):
        """Test basic FailState creation."""
        state = FailState(
            name="TestFailState",
            error="States.Timeout",
            cause="Request timed out after 30 seconds",
            comment="Test fail state",
        )

        assert state.name == "TestFailState"
        assert state.type == "Fail"
        assert state.error == "States.Timeout"
        assert state.cause == "Request timed out after 30 seconds"
        assert state.comment == "Test fail state"
        assert state.next_state is None
        assert state.end is False
        assert state.input_path is None
        assert state.output_path is None
        assert state.result_path is None

    def test_fail_state_minimal(self):
        """Test FailState with minimal fields."""
        state = FailState(name="MinimalFail", error="States.TaskFailed")

        assert state.name == "MinimalFail"
        assert state.type == "Fail"
        assert state.error == "States.TaskFailed"
        assert state.cause is None
        assert state.comment is None

    def test_fail_state_with_cause(self):
        """Test FailState with cause."""
        state = FailState(name="CauseFail", error="CustomError", cause="Something went wrong in the process")

        assert state.error == "CustomError"
        assert state.cause == "Something went wrong in the process"

    def test_fail_state_defaults(self):
        """Test FailState enforces terminal state properties."""
        state = FailState(name="DefaultFail", error="States.Failed")

        # These should all be None/False for terminal state
        assert state.next_state is None
        assert state.end is False
        assert state.input_path is None
        assert state.output_path is None
        assert state.result_path is None

    def test_fail_state_type_fixed(self):
        """Test that FailState always has Type 'Fail'."""
        state = FailState(name="TestFail", error="TestError")
        state.type = "WrongType"
        state.__post_init__()
        assert state.type == "Fail"

    # Test validation

    def test_fail_state_validation_valid(self):
        """Test validation of valid FailState configurations."""
        test_cases = [
            # Minimal
            {"name": "ValidFail", "error": "States.Failed"},
            # With cause
            {"name": "ValidFail", "error": "States.Timeout", "cause": "Timed out"},
            # With comment
            {"name": "ValidFail", "error": "CustomError", "comment": "Test comment"},
            # Complete
            {"name": "ValidFail", "error": "States.TaskFailed", "cause": "Task error", "comment": "Complete"},
        ]

        for test_case in test_cases:
            state = FailState(**test_case)
            state.validate()  # Should not raise

    def test_fail_state_validation_no_name(self):
        """Test validation with empty name."""

        class InvalidState(FailState):
            def __init__(self):
                self.name = ""
                self.type = "Fail"
                self.error = "TestError"

        state = InvalidState()
        with pytest.raises(ValueError, match="State name cannot be empty"):
            state.validate()

    def test_fail_state_validation_wrong_type(self):
        """Test validation with wrong type."""
        state = FailState(name="WrongType", error="TestError")
        state.type = "Pass"

        with pytest.raises(ValueError, match="must have Type 'Fail'"):
            state.validate()

    def test_fail_state_validation_no_error(self):
        """Test validation without Error field."""

        class InvalidState(FailState):
            def __init__(self):
                self.name = "InvalidFail"
                self.type = "Fail"
                self.error = ""

        state = InvalidState()
        with pytest.raises(ValueError, match="must have Error field"):
            state.validate()

    def test_fail_state_validation_has_next(self):
        """Test validation with Next field."""

        class InvalidState(FailState):
            def __init__(self):
                self.name = "InvalidFail"
                self.type = "Fail"
                self.error = "TestError"
                self.next_state = "NextState"

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have Next field"):
            state.validate()

    def test_fail_state_validation_has_end(self):
        """Test validation with End field."""

        class InvalidState(FailState):
            def __init__(self):
                self.name = "InvalidFail"
                self.type = "Fail"
                self.error = "TestError"
                self.end = True

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have End field"):
            state.validate()

    def test_fail_state_validation_has_input_path(self):
        """Test validation with InputPath."""

        class InvalidState(FailState):
            def __init__(self):
                self.name = "InvalidFail"
                self.type = "Fail"
                self.error = "TestError"
                self.input_path = "$.data"

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have InputPath"):
            state.validate()

    def test_fail_state_validation_has_output_path(self):
        """Test validation with OutputPath."""

        class InvalidState(FailState):
            def __init__(self):
                self.name = "InvalidFail"
                self.type = "Fail"
                self.error = "TestError"
                self.output_path = "$.output"

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have OutputPath"):
            state.validate()

    def test_fail_state_validation_has_result_path(self):
        """Test validation with ResultPath."""

        class InvalidState(FailState):
            def __init__(self):
                self.name = "InvalidFail"
                self.type = "Fail"
                self.error = "TestError"
                self.result_path = "$.result"

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have ResultPath"):
            state.validate()

    # Test execute method

    @pytest.mark.asyncio
    async def test_fail_state_execute_simple(self, sample_input_data):
        """Test simple FailState execution."""
        with pytest.raises(StateError) as exc_info:
            state = FailState(name="SimpleFail", error="States.TaskFailed", cause="Task execution failed")
            output, next_state = await state.execute(sample_input_data)

        # Verify results
        # assert output is None  # Fail states produce no output
        # assert next_state is None  # Fail states have no next state
        # assert error is not None  # Must have an error
        # assert isinstance(error, StateError)
        # assert error.error_type == "States.TaskFailed"
        # assert "Task execution failed" in str(error) or error.message == "Task execution failed"
        # assert error.state_name == "SimpleFail"

    @pytest.mark.asyncio
    async def test_fail_state_execute_without_cause(self, sample_input_data):
        """Test FailState execution without cause."""
        with pytest.raises(StateError) as exc_info:
            await FailState(name="NoCauseFail", error="CustomError").execute(sample_input_data)

    @pytest.mark.asyncio
    async def test_fail_state_execute_with_context(self, sample_input_data):
        """Test FailState execution with context."""
        with pytest.raises(StateError) as exc_info:
            await FailState(name="ContextFail", error="States.Timeout", cause="Operation timed out").execute(
                sample_input_data, {"execution_id": "test-123", "timestamp": "2024-01-15"}
            )

    @pytest.mark.asyncio
    async def test_fail_state_execute_nil_input(self):
        """Test FailState execution with None input."""
        with pytest.raises(StateError) as exc_info:
            await FailState(name="NilFail", error="States.Failed").execute(None)

    @pytest.mark.asyncio
    async def test_fail_state_execute_ignores_input(self, sample_input_data):
        """Test that FailState ignores input data."""
        test_inputs = [sample_input_data, {"different": "data"}, None, "string", 42, []]

        for input_data in test_inputs:
            with pytest.raises(StateError) as exec:
                # Execute with different inputs - should always fail the same way
                await FailState(
                    name="IgnoreInputFail", error="States.Failed", cause="Failed regardless of input"
                ).execute(input_data)


@pytest.mark.asyncio
async def test_fail_state_execute_different_error_types():
    """Test FailState with different error types."""
    error_types = [
        "States.Timeout",
        "States.TaskFailed",
        "States.Permissions",
        "CustomError",
        "ServiceException",
        "ValidationError",
    ]

    for error_type in error_types:
        with pytest.raises(StateError, match=f"Failed with {error_type}"):
            await FailState(name=f"Fail_{error_type}", error=error_type, cause=f"Failed with {error_type}").execute({})


# Test to_dict method


def test_fail_state_to_dict_minimal():
    """Test to_dict with minimal FailState."""
    state = FailState(name="MinimalFail", error="States.Failed")

    result = state.to_dict()

    assert result == {"Type": "Fail", "Error": "States.Failed"}
    assert "Cause" not in result
    assert "Comment" not in result
    assert "Next" not in result
    assert "End" not in result
    assert "InputPath" not in result
    assert "OutputPath" not in result
    assert "ResultPath" not in result


def test_fail_state_to_dict_with_cause():
    """Test to_dict with cause."""
    state = FailState(name="CauseFail", error="States.Timeout", cause="Request timed out")

    result = state.to_dict()

    assert result == {"Type": "Fail", "Error": "States.Timeout", "Cause": "Request timed out"}


def test_fail_state_to_dict_with_comment():
    """Test to_dict with comment."""
    state = FailState(name="CommentFail", error="CustomError", comment="This is a test failure")

    result = state.to_dict()

    assert result == {"Type": "Fail", "Error": "CustomError", "Comment": "This is a test failure"}


def test_fail_state_to_dict_complete():
    """Test to_dict with all allowed fields."""
    state = FailState(
        name="CompleteFail", error="States.TaskFailed", cause="Task execution failed", comment="Complete fail state"
    )

    result = state.to_dict()

    assert result == {
        "Type": "Fail",
        "Error": "States.TaskFailed",
        "Cause": "Task execution failed",
        "Comment": "Complete fail state",
    }
    # Verify disallowed fields are not present
    assert "Next" not in result
    assert "End" not in result
    assert "InputPath" not in result
    assert "OutputPath" not in result
    assert "ResultPath" not in result


# Test to_json method


def test_fail_state_to_json():
    """Test to_json method."""
    state = FailState(name="JsonFail", error="States.Failed", cause="JSON test")

    json_str = state.to_json()
    result = json.loads(json_str)

    assert result == {"Type": "Fail", "Error": "States.Failed", "Cause": "JSON test"}


def test_fail_state_to_json_indented():
    """Test to_json with indentation."""
    state = FailState(name="IndentedFail", error="TestError", comment="Indented")

    json_str = state.to_json(indent=2)
    assert "\n  " in json_str


# Test get_next_states method


def test_fail_state_get_next_states():
    """Test get_next_states method."""
    state = FailState(name="NoNextFail", error="States.Failed")

    next_states = state.get_next_states()

    # Fail states have no next states
    assert next_states == []


# Test string representations


def test_fail_state_str():
    """Test string representation."""
    state = FailState(name="TestFail", error="States.Failed")

    str_repr = str(state)
    assert "FailState" in str_repr
    assert "TestFail" in str_repr
    assert "States.Failed" in str_repr


def test_fail_state_repr():
    """Test detailed representation."""
    state = FailState(name="TestFail", error="States.TaskFailed", cause="Task error", comment="Test state")

    repr_str = repr(state)
    assert "FailState" in repr_str
    assert "name='TestFail'" in repr_str
    assert "error='States.TaskFailed'" in repr_str
    assert "cause='Task error'" in repr_str
    assert "comment='Test state'" in repr_str


# Test edge cases


@pytest.mark.asyncio
async def test_fail_state_execute_empty_input():
    """Test FailState execution with empty input."""
    with pytest.raises(StateError, match="State: EmptyFail | Error: State 'EmptyFail' failed | Type: States.Failed"):
        await FailState(name="EmptyFail", error="States.Failed").execute({})


@pytest.mark.asyncio
async def test_fail_state_execute_different_input_types():
    """Test FailState execution with different input types."""
    test_cases = [
        ("string input", "string"),
        (42, "integer"),
        (3.14, "float"),
        (True, "boolean"),
        ([1, 2, 3], "list"),
        ({"key": "value"}, "dict"),
        (None, "None"),
    ]

    for input_data, description in test_cases:
        with pytest.raises(
            StateError, match="State: TypeTestFail | Error: State 'TypeTestFail' failed | Type: States.Failed"
        ) as exec:
            await FailState(name="TypeTestFail", error="States.Failed").execute(input_data=input_data)


@pytest.mark.asyncio
async def test_fail_state_error_details():
    """Test that error contains correct details."""
    with pytest.raises(StateError, match="CustomError.SubType") as exc:
        await FailState(
            name="DetailedFail", error="CustomError.SubType", cause="Detailed error message with context"
        ).execute({"test": "data"})
    # Check error message contains cause
    assert exc is not None
    assert exc.value.state_name == "DetailedFail"
    assert exc.value.error_type == "CustomError.SubType"
    assert "Detailed error message with context" in exc.value.message


@pytest.mark.asyncio
async def test_fail_state_error_string_representation():
    """Test error string representation."""
    with pytest.raises(StateError) as exec:
        await FailState(name="StringFail", error="States.Timeout", cause="Operation exceeded timeout limit").execute({})

    assert "StringFail" in exec.value.state_name
    assert "States.Timeout" in exec.value.error_type


# Test inheritance


def test_fail_state_inheritance():
    """Test that FailState properly inherits from BaseState."""
    state = FailState(name="InheritanceTest", error="TestError")

    # Check inherited methods
    assert hasattr(state, "execute")
    assert hasattr(state, "validate")
    assert hasattr(state, "to_dict")
    assert hasattr(state, "to_json")
    assert hasattr(state, "get_next_states")

    # Check inherited properties
    assert state.state_name == "InheritanceTest"
    assert state.state_type == "Fail"
    assert state.get_next() is None
    assert state.is_end() is False


# Test concurrency


@pytest.mark.asyncio
async def test_fail_state_concurrent_execution():
    """Test concurrent execution of FailState."""
    import asyncio

    state = FailState(name="ConcurrentFail", error="States.Failed", cause="Concurrent test failure")

    # Run concurrent executions
    num_tasks = 10
    tasks = []

    for i in range(num_tasks):
        input_data = {"id": i, "data": f"task_{i}"}
        task = asyncio.create_task(state.execute(input_data))
        tasks.append(task)

    # Wait for all tasks
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all completed with errors
    assert len(results) == num_tasks
    for error in results:
        assert error is not None
        assert error.error_type == "States.Failed"


# Test AWS standard error codes


@pytest.mark.asyncio
async def test_fail_state_aws_standard_errors():
    """Test FailState with AWS standard error codes."""
    aws_errors = [
        ("States.ALL", "Wildcard error"),
        ("States.Timeout", "Execution timeout"),
        ("States.TaskFailed", "Task execution failed"),
        ("States.Permissions", "Permission denied"),
        ("States.ResultPathMatchFailure", "Result path match failed"),
        ("States.ParameterPathFailure", "Parameter path failed"),
        ("States.BranchFailed", "Parallel branch failed"),
        ("States.NoChoiceMatched", "No choice matched"),
    ]

    for error_code, cause in aws_errors:
        with pytest.raises(StateError, match=error_code) as error:
            await FailState(name=f"Fail_{error_code}", error=error_code, cause=cause).execute({})


# Test multiple executions


@pytest.mark.asyncio
async def test_fail_state_multiple_executions():
    """Test that FailState can be executed multiple times."""
    state = FailState(name="MultiExecFail", error="States.Failed", cause="Multiple execution test")

    # Execute multiple times with different inputs
    for i in range(5):
        with pytest.raises(StateError, match="States.Failed") as exec:
            await state.execute({"iteration": i})


# Test error immutability


@pytest.mark.asyncio
async def test_fail_state_error_consistency():
    """Test that error details remain consistent across executions."""
    for index in [0, 1]:
        with pytest.raises(StateError) as exec:
            fail_state = FailState(name="ConsistentFail", error="CustomError", cause="Consistent error message")
            await fail_state.execute({"test": index + 1})
        assert exec.value.error_type == fail_state.error
        assert exec.value.state_name == fail_state.name
        assert exec.value.message == fail_state.cause
