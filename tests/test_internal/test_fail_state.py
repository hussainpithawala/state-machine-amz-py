"""
Tests for the FailState implementation.
"""

import json
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from src.state_machine.__internal__.states.base import StateError
from src.state_machine.__internal__.states.fail_state import FailState


class TestFailState:
    """Test suite for FailState."""

    @pytest.fixture
    def sample_input_data(self):
        """Sample input data for testing."""
        return {
            "data": "input data",
            "metadata": {"source": "test", "timestamp": "2024-01-15"},
            "count": 42
        }

    # Test initialization and basic properties

    def test_fail_state_creation(self):
        """Test basic FailState creation."""
        state = FailState(
            name="TestFailState",
            error="States.Timeout",
            cause="Request timed out after 30 seconds",
            comment="Test fail state"
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
        state = FailState(
            name="MinimalFail",
            error="States.TaskFailed"
        )

        assert state.name == "MinimalFail"
        assert state.type == "Fail"
        assert state.error == "States.TaskFailed"
        assert state.cause is None
        assert state.comment is None

    def test_fail_state_with_cause(self):
        """Test FailState with cause."""
        state = FailState(
            name="CauseFail",
            error="CustomError",
            cause="Something went wrong in the process"
        )

        assert state.error == "CustomError"
        assert state.cause == "Something went wrong in the process"

    def test_fail_state_defaults(self):
        """Test FailState enforces terminal state properties."""
        state = FailState(
            name="DefaultFail",
            error="States.Failed"
        )

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
        state = FailState(
            name="SimpleFail",
            error="States.TaskFailed",
            cause="Task execution failed"
        )

        output, next_state, error = await state.execute(sample_input_data)

        # Verify results
        assert output is None  # Fail states produce no output
        assert next_state is None  # Fail states have no next state
        assert error is not None  # Must have an error
        assert isinstance(error, StateError)
        assert error.error_type == "States.TaskFailed"
        assert "Task execution failed" in str(error) or error.message == "Task execution failed"
        assert error.state_name == "SimpleFail"

    @pytest.mark.asyncio
    async def test_fail_state_execute_without_cause(self, sample_input_data):
        """Test FailState execution without cause."""
        state = FailState(
            name="NoCauseFail",
            error="CustomError"
        )

        output, next_state, error = await state.execute(sample_input_data)

        assert output is None
        assert next_state is None
        assert error is not None
        assert isinstance(error, StateError)
        assert error.error_type == "CustomError"
        assert error.state_name == "NoCauseFail"

    @pytest.mark.asyncio
    async def test_fail_state_execute_with_context(self, sample_input_data):
        """Test FailState execution with context."""
        state = FailState(
            name="ContextFail",
            error="States.Timeout",
            cause="Operation timed out"
        )

        context = {"execution_id": "test-123", "timestamp": "2024-01-15"}

        output, next_state, error = await state.execute(sample_input_data, context)

        assert output is None
        assert next_state is None
        assert error is not None
        assert error.error_type == "States.Timeout"

    @pytest.mark.asyncio
    async def test_fail_state_execute_nil_input(self):
        """Test FailState execution with None input."""
        state = FailState(
            name="NilFail",
            error="States.Failed"
        )

        output, next_state, error = await state.execute(None)

        assert output is None
        assert next_state is None
        assert error is not None

    @pytest.mark.asyncio
    async def test_fail_state_execute_ignores_input(self, sample_input_data):
        """Test that FailState ignores input data."""
        state = FailState(
            name="IgnoreInputFail",
            error="States.Failed",
            cause="Failed regardless of input"
        )

        # Execute with different inputs - should always fail the same way
        test_inputs = [
            sample_input_data,
            {"different": "data"},
            None,
            "string",
            42,
            []
        ]

        for input_data in test_inputs:
            output, next_state, error = await state.execute(input_data)

            assert output is None
            assert next_state is None
            assert error is not None
            assert error.error_type == "States.Failed"

    @pytest.mark.asyncio
    async def test_fail_state_execute_different_error_types(self):
        """Test FailState with different error types."""
        error_types = [
            "States.Timeout",
            "States.TaskFailed",
            "States.Permissions",
            "CustomError",
            "ServiceException",
            "ValidationError"
        ]

        for error_type in error_types:
            state = FailState(
                name=f"Fail_{error_type}",
                error=error_type,
                cause=f"Failed with {error_type}"
            )

            output, next_state, error = await state.execute({})

            assert output is None
            assert next_state is None
            assert error is not None
            assert error.error_type == error_type

    # Test to_dict method

    def test_fail_state_to_dict_minimal(self):
        """Test to_dict with minimal FailState."""
        state = FailState(
            name="MinimalFail",
            error="States.Failed"
        )

        result = state.to_dict()

        assert result == {
            "Type": "Fail",
            "Error": "States.Failed"
        }
        assert "Cause" not in result
        assert "Comment" not in result
        assert "Next" not in result
        assert "End" not in result
        assert "InputPath" not in result
        assert "OutputPath" not in result
        assert "ResultPath" not in result

    def test_fail_state_to_dict_with_cause(self):
        """Test to_dict with cause."""
        state = FailState(
            name="CauseFail",
            error="States.Timeout",
            cause="Request timed out"
        )

        result = state.to_dict()

        assert result == {
            "Type": "Fail",
            "Error": "States.Timeout",
            "Cause": "Request timed out"
        }

    def test_fail_state_to_dict_with_comment(self):
        """Test to_dict with comment."""
        state = FailState(
            name="CommentFail",
            error="CustomError",
            comment="This is a test failure"
        )

        result = state.to_dict()

        assert result == {
            "Type": "Fail",
            "Error": "CustomError",
            "Comment": "This is a test failure"
        }

    def test_fail_state_to_dict_complete(self):
        """Test to_dict with all allowed fields."""
        state = FailState(
            name="CompleteFail",
            error="States.TaskFailed",
            cause="Task execution failed",
            comment="Complete fail state"
        )

        result = state.to_dict()

        assert result == {
            "Type": "Fail",
            "Error": "States.TaskFailed",
            "Cause": "Task execution failed",
            "Comment": "Complete fail state"
        }
        # Verify disallowed fields are not present
        assert "Next" not in result
        assert "End" not in result
        assert "InputPath" not in result
        assert "OutputPath" not in result
        assert "ResultPath" not in result

    # Test to_json method

    def test_fail_state_to_json(self):
        """Test to_json method."""
        state = FailState(
            name="JsonFail",
            error="States.Failed",
            cause="JSON test"
        )

        json_str = state.to_json()
        result = json.loads(json_str)

        assert result == {
            "Type": "Fail",
            "Error": "States.Failed",
            "Cause": "JSON test"
        }

    def test_fail_state_to_json_indented(self):
        """Test to_json with indentation."""
        state = FailState(
            name="IndentedFail",
            error="TestError",
            comment="Indented"
        )

        json_str = state.to_json(indent=2)
        assert "\n  " in json_str

    # Test get_next_states method

    def test_fail_state_get_next_states(self):
        """Test get_next_states method."""
        state = FailState(
            name="NoNextFail",
            error="States.Failed"
        )

        next_states = state.get_next_states()

        # Fail states have no next states
        assert next_states == []

    # Test string representations

    def test_fail_state_str(self):
        """Test string representation."""
        state = FailState(
            name="TestFail",
            error="States.Failed"
        )

        str_repr = str(state)
        assert "FailState" in str_repr
        assert "TestFail" in str_repr
        assert "States.Failed" in str_repr

    def test_fail_state_repr(self):
        """Test detailed representation."""
        state = FailState(
            name="TestFail",
            error="States.TaskFailed",
            cause="Task error",
            comment="Test state"
        )

        repr_str = repr(state)
        assert "FailState" in repr_str
        assert "name='TestFail'" in repr_str
        assert "error='States.TaskFailed'" in repr_str
        assert "cause='Task error'" in repr_str
        assert "comment='Test state'" in repr_str

    # Test edge cases

    @pytest.mark.asyncio
    async def test_fail_state_execute_empty_input(self):
        """Test FailState execution with empty input."""
        state = FailState(
            name="EmptyFail",
            error="States.Failed"
        )

        empty_input = {}
        output, next_state, error = await state.execute(empty_input)

        assert output is None
        assert next_state is None
        assert error is not None

    @pytest.mark.asyncio
    async def test_fail_state_execute_different_input_types(self):
        """Test FailState execution with different input types."""
        state = FailState(
            name="TypeTestFail",
            error="States.Failed"
        )

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
            output, next_state, error = await state.execute(input_data)

            assert output is None, f"Failed for {description}"
            assert next_state is None, f"Failed for {description}"
            assert error is not None, f"Failed for {description}"
            assert isinstance(error, StateError), f"Failed for {description}"

    @pytest.mark.asyncio
    async def test_fail_state_error_details(self):
        """Test that error contains correct details."""
        state = FailState(
            name="DetailedFail",
            error="CustomError.SubType",
            cause="Detailed error message with context"
        )

        output, next_state, error = await state.execute({"test": "data"})

        assert error is not None
        assert error.state_name == "DetailedFail"
        assert error.error_type == "CustomError.SubType"
        # Check error message contains cause
        assert "Detailed error message with context" in error.message

    @pytest.mark.asyncio
    async def test_fail_state_error_string_representation(self):
        """Test error string representation."""
        state = FailState(
            name="StringFail",
            error="States.Timeout",
            cause="Operation exceeded timeout limit"
        )

        output, next_state, error = await state.execute({})

        error_str = str(error)
        assert "StringFail" in error_str
        assert "States.Timeout" in error_str

    # Test inheritance

    def test_fail_state_inheritance(self):
        """Test that FailState properly inherits from BaseState."""
        state = FailState(
            name="InheritanceTest",
            error="TestError"
        )

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
    async def test_fail_state_concurrent_execution(self):
        """Test concurrent execution of FailState."""
        import asyncio

        state = FailState(
            name="ConcurrentFail",
            error="States.Failed",
            cause="Concurrent test failure"
        )

        # Run concurrent executions
        num_tasks = 10
        tasks = []

        for i in range(num_tasks):
            input_data = {"id": i, "data": f"task_{i}"}
            task = asyncio.create_task(state.execute(input_data))
            tasks.append(task)

        # Wait for all tasks
        results = await asyncio.gather(*tasks)

        # Verify all completed with errors
        assert len(results) == num_tasks
        for output, next_state, error in results:
            assert output is None
            assert next_state is None
            assert error is not None
            assert error.error_type == "States.Failed"

    # Test AWS standard error codes

    @pytest.mark.asyncio
    async def test_fail_state_aws_standard_errors(self):
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
            state = FailState(
                name=f"Fail_{error_code}",
                error=error_code,
                cause=cause
            )

            output, next_state, error = await state.execute({})

            assert error is not None
            assert error.error_type == error_code

    # Test multiple executions

    @pytest.mark.asyncio
    async def test_fail_state_multiple_executions(self):
        """Test that FailState can be executed multiple times."""
        state = FailState(
            name="MultiExecFail",
            error="States.Failed",
            cause="Multiple execution test"
        )

        # Execute multiple times with different inputs
        for i in range(5):
            output, next_state, error = await state.execute({"iteration": i})

            assert output is None
            assert next_state is None
            assert error is not None
            assert error.error_type == "States.Failed"

    # Test error immutability

    @pytest.mark.asyncio
    async def test_fail_state_error_consistency(self):
        """Test that error details remain consistent across executions."""
        state = FailState(
            name="ConsistentFail",
            error="CustomError",
            cause="Consistent error message"
        )

        # Execute twice
        output1, next1, error1 = await state.execute({"test": 1})
        output2, next2, error2 = await state.execute({"test": 2})

        # Both should produce equivalent errors
        assert error1.error_type == error2.error_type
        assert error1.state_name == error2.state_name
        assert error1.message == error2.message
