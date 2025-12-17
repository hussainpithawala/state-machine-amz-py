"""
Tests for the PassState implementation.
"""

import json
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from src.state_machine.__internal__.states.base import (
    StateError,
    get_path_processor,
    set_path_processor,
)
from src.state_machine.__internal__.states.pass_state import PassState


class TestPassState:
    """Test suite for PassState."""

    @pytest.fixture
    def mock_path_processor(self):
        """Create a mock path processor."""
        processor = Mock()
        processor.apply_input_path = Mock(return_value="processed_input")
        processor.apply_result_path = Mock(return_value="combined_data")
        processor.apply_output_path = Mock(return_value="final_output")
        return processor

    @pytest.fixture
    def sample_input_data(self):
        """Sample input data for testing."""
        return {
            "data": "input data",
            "metadata": {"source": "test", "timestamp": "2024-01-15"},
            "count": 42
        }

    # Test initialization and basic properties

    def test_pass_state_creation(self):
        """Test basic PassState creation."""
        state = PassState(
            name="TestPassState",
            next_state="NextState",
            input_path="$.data",
            output_path="$.result",
            comment="Test comment"
        )

        assert state.name == "TestPassState"
        assert state.type == "Pass"
        assert state.next_state == "NextState"
        assert state.input_path == "$.data"
        assert state.output_path == "$.result"
        assert state.comment == "Test comment"
        assert state.end is False
        assert state.result is None
        assert state.parameters is None

    def test_pass_state_with_end(self):
        """Test PassState with end=True."""
        state = PassState(name="EndPass", end=True)

        assert state.name == "EndPass"
        assert state.type == "Pass"
        assert state.end is True
        assert state.next_state is None

    def test_pass_state_with_result(self):
        """Test PassState with static result."""
        result_data = {"status": "success", "value": 100}
        state = PassState(
            name="ResultPass",
            next_state="NextState",
            result=result_data
        )

        assert state.result == result_data
        assert state.parameters is None

    def test_pass_state_with_parameters(self):
        """Test PassState with parameters."""
        params = {"key.$": "$.data", "static": "value"}
        state = PassState(
            name="ParamsPass",
            next_state="NextState",
            parameters=params
        )

        assert state.parameters == params
        assert state.result is None

    def test_pass_state_defaults(self):
        """Test PassState with default values."""
        state = PassState(name="SimplePass", next_state="Next")

        assert state.name == "SimplePass"
        assert state.type == "Pass"
        assert state.next_state == "Next"
        assert state.end is False
        assert state.input_path is None
        assert state.output_path is None
        assert state.result_path is None
        assert state.result is None
        assert state.parameters is None
        assert state.comment is None

    def test_pass_state_type_fixed(self):
        """Test that PassState always has Type 'Pass'."""
        state = PassState(name="TestPass", next_state="Next")
        state.type = "WrongType"
        state.__post_init__()
        assert state.type == "Pass"

    # Test validation

    def test_pass_state_validation_valid(self):
        """Test validation of valid PassState configurations."""
        test_cases = [
            # Simple pass with next
            {"name": "ValidPass", "next_state": "NextState"},
            # Pass with end
            {"name": "ValidPass", "end": True},
            # With input/output paths
            {"name": "ValidPass", "next_state": "Next", "input_path": "$.data", "output_path": "$.out"},
            # With result
            {"name": "ValidPass", "next_state": "Next", "result": {"key": "value"}},
            # With parameters
            {"name": "ValidPass", "next_state": "Next", "parameters": {"key": "value"}},
            # With result_path
            {"name": "ValidPass", "next_state": "Next", "result_path": "$.result"},
        ]

        for test_case in test_cases:
            state = PassState(**test_case)
            state.validate()  # Should not raise

    def test_pass_state_validation_no_name(self):
        """Test validation with empty name."""

        class InvalidState(PassState):
            def __init__(self):
                self.name = ""
                self.type = "Pass"
                self.next_state = "Next"

        state = InvalidState()
        with pytest.raises(ValueError, match="State name cannot be empty"):
            state.validate()

    def test_pass_state_validation_wrong_type(self):
        """Test validation with wrong type."""
        state = PassState(name="WrongType", next_state="Next")
        state.type = "Succeed"

        with pytest.raises(ValueError, match="must have Type 'Pass'"):
            state.validate()

    def test_pass_state_validation_no_next_or_end(self):
        """Test validation without Next or End."""

        class InvalidState(PassState):
            def __init__(self):
                self.name = "InvalidPass"
                self.type = "Pass"
                self.next_state = None
                self.end = False

        state = InvalidState()
        with pytest.raises(ValueError, match="must have either Next or End"):
            state.validate()

    def test_pass_state_validation_both_next_and_end(self):
        """Test validation with both Next and End."""

        class InvalidState(PassState):
            def __init__(self):
                self.name = "InvalidPass"
                self.type = "Pass"
                self.next_state = "NextState"
                self.end = True

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have both Next and End"):
            state.validate()

    def test_pass_state_validation_both_result_and_parameters(self):
        """Test validation with both Result and Parameters."""
        with pytest.raises(ValueError, match="cannot have both Result and Parameters"):
            pass_state = PassState(
                name="InvalidPass",
                next_state="Next",
                result={"key": "value"},
                parameters={"param": "value"}
            )
            pass_state.validate()

    # Test execute method

    @pytest.mark.asyncio
    async def test_pass_state_execute_simple(self, mock_path_processor, sample_input_data):
        """Test simple PassState execution without result."""
        state = PassState(name="SimplePass", next_state="NextState")
        state.set_path_processor(mock_path_processor)

        # Mock to simulate pass-through
        mock_path_processor.apply_input_path.return_value = sample_input_data
        mock_path_processor.apply_output_path.return_value = sample_input_data

        output, next_state = await state.execute(sample_input_data)

        # Verify processor calls
        mock_path_processor.apply_input_path.assert_called_once_with(sample_input_data, None)
        mock_path_processor.apply_output_path.assert_called_once_with(sample_input_data, None)

        # Verify results
        assert output == sample_input_data
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_pass_state_execute_with_result(self, mock_path_processor, sample_input_data):
        """Test PassState execution with static result."""
        result_data = {"status": "processed", "value": 123}
        state = PassState(
            name="ResultPass",
            next_state="NextState",
            result=result_data
        )
        state.set_path_processor(mock_path_processor)

        output, next_state = await state.execute(sample_input_data)

        # Verify processor calls
        mock_path_processor.apply_input_path.assert_called_once_with(sample_input_data, None)
        mock_path_processor.apply_result_path.assert_called_once_with(
            "processed_input", result_data, None
        )
        mock_path_processor.apply_output_path.assert_called_once_with("combined_data", None)

        # Verify results
        assert output == "final_output"
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_pass_state_execute_with_parameters(self, mock_path_processor, sample_input_data):
        """Test PassState execution with parameters."""
        params = {"key": "value", "number": 42}
        state = PassState(
            name="ParamsPass",
            next_state="NextState",
            parameters=params
        )
        state.set_path_processor(mock_path_processor)

        output, next_state = await state.execute(sample_input_data)

        # Verify processor calls
        mock_path_processor.apply_input_path.assert_called_once()
        mock_path_processor.apply_result_path.assert_called_once_with(
            "processed_input", params, None
        )
        mock_path_processor.apply_output_path.assert_called_once()

        assert output == "final_output"
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_pass_state_execute_with_input_path(self, mock_path_processor, sample_input_data):
        """Test PassState execution with input path."""
        state = PassState(
            name="InputPathPass",
            next_state="NextState",
            input_path="$.data"
        )
        state.set_path_processor(mock_path_processor)

        await state.execute(sample_input_data)

        mock_path_processor.apply_input_path.assert_called_once_with(sample_input_data, "$.data")

    @pytest.mark.asyncio
    async def test_pass_state_execute_with_output_path(self, mock_path_processor, sample_input_data):
        """Test PassState execution with output path."""
        state = PassState(
            name="OutputPathPass",
            next_state="NextState",
            output_path="$.result"
        )
        state.set_path_processor(mock_path_processor)

        await state.execute(sample_input_data)

        mock_path_processor.apply_output_path.assert_called_once_with("processed_input", "$.result")

    @pytest.mark.asyncio
    async def test_pass_state_execute_with_result_path(self, mock_path_processor, sample_input_data):
        """Test PassState execution with result path."""
        result_data = {"new": "data"}
        state = PassState(
            name="ResultPathPass",
            next_state="NextState",
            result=result_data,
            result_path="$.output"
        )
        state.set_path_processor(mock_path_processor)

        await state.execute(sample_input_data)

        mock_path_processor.apply_result_path.assert_called_once_with(
            "processed_input", result_data, "$.output"
        )

    @pytest.mark.asyncio
    async def test_pass_state_execute_with_all_paths(self, mock_path_processor, sample_input_data):
        """Test PassState execution with all paths."""
        result_data = {"injected": "value"}
        state = PassState(
            name="CompletePass",
            next_state="NextState",
            input_path="$.data",
            result_path="$.result",
            output_path="$.final",
            result=result_data
        )
        state.set_path_processor(mock_path_processor)

        await state.execute(sample_input_data)

        mock_path_processor.apply_input_path.assert_called_once_with(sample_input_data, "$.data")
        mock_path_processor.apply_result_path.assert_called_once_with(
            "processed_input", result_data, "$.result"
        )
        mock_path_processor.apply_output_path.assert_called_once_with("combined_data", "$.final")

    @pytest.mark.asyncio
    async def test_pass_state_execute_with_context(self, mock_path_processor, sample_input_data):
        """Test PassState execution with context."""
        state = PassState(name="ContextPass", next_state="NextState")
        state.set_path_processor(mock_path_processor)

        context = {"execution_id": "test-123", "timestamp": "2024-01-15"}

        output, next_state =  await state.execute(sample_input_data, context)

        assert output == "final_output"
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_pass_state_execute_end_state(self, mock_path_processor, sample_input_data):
        """Test PassState execution as end state."""
        state = PassState(name="EndPass", end=True)
        state.set_path_processor(mock_path_processor)

        output, next_state = await state.execute(sample_input_data)

        assert output == "final_output"
        assert next_state is None  # End state has no next


    @pytest.mark.asyncio
    async def test_pass_state_execute_path_processing_error(self, sample_input_data):
        """Test PassState execution when path processing fails."""
        mock_processor = Mock()
        mock_processor.apply_input_path.side_effect = ValueError("Invalid path")

        state = PassState(name="ErrorPass", next_state="NextState")
        state.set_path_processor(mock_processor)

        with pytest.raises(StateError, match="Failed to execute pass state"):
            await state.execute(sample_input_data)

    @pytest.mark.asyncio
    async def test_pass_state_execute_nil_input(self, mock_path_processor):
        """Test PassState execution with None input."""
        state = PassState(name="NilPass", next_state="NextState")
        state.set_path_processor(mock_path_processor)

        output, next_state =  await state.execute(None)

        mock_path_processor.apply_input_path.assert_called_once_with(None, None)
        assert output == "final_output"
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_pass_state_execute_uses_default_processor(self, sample_input_data):
        """Test that PassState uses default path processor when none is set."""
        original_processor = get_path_processor()

        try:
            mock_default = Mock()
            mock_default.apply_input_path = Mock(return_value=sample_input_data)
            mock_default.apply_output_path = Mock(return_value=sample_input_data)

            set_path_processor(mock_default)

            state = PassState(name="DefaultPass", next_state="NextState")

            output, next_state = await state.execute(sample_input_data)

            mock_default.apply_input_path.assert_called_once()
            assert output == sample_input_data
            assert next_state == "NextState"

        finally:
            set_path_processor(original_processor)

    # Test to_dict method

    def test_pass_state_to_dict_simple(self):
        """Test to_dict with simple PassState."""
        state = PassState(name="SimplePass", next_state="NextState")

        result = state.to_dict()

        assert result == {
            "Type": "Pass",
            "Next": "NextState"
        }

    def test_pass_state_to_dict_with_end(self):
        """Test to_dict with end state."""
        state = PassState(name="EndPass", end=True)

        result = state.to_dict()

        assert result == {
            "Type": "Pass",
            "End": True
        }

    def test_pass_state_to_dict_with_result(self):
        """Test to_dict with result."""
        result_data = {"status": "success", "value": 100}
        state = PassState(
            name="ResultPass",
            next_state="NextState",
            result=result_data
        )

        result = state.to_dict()

        assert result == {
            "Type": "Pass",
            "Next": "NextState",
            "Result": result_data
        }

    def test_pass_state_to_dict_with_parameters(self):
        """Test to_dict with parameters."""
        params = {"key.$": "$.data", "static": "value"}
        state = PassState(
            name="ParamsPass",
            next_state="NextState",
            parameters=params
        )

        result = state.to_dict()

        assert result == {
            "Type": "Pass",
            "Next": "NextState",
            "Parameters": params
        }

    def test_pass_state_to_dict_complete(self):
        """Test to_dict with all allowed fields."""
        state = PassState(
            name="CompletePass",
            next_state="NextState",
            input_path="$.input",
            result_path="$.result",
            output_path="$.output",
            result={"key": "value"},
            comment="Complete pass state"
        )

        result = state.to_dict()

        assert result == {
            "Type": "Pass",
            "Next": "NextState",
            "InputPath": "$.input",
            "ResultPath": "$.result",
            "OutputPath": "$.output",
            "Result": {"key": "value"},
            "Comment": "Complete pass state"
        }

    # Test to_json method

    def test_pass_state_to_json(self):
        """Test to_json method."""
        state = PassState(
            name="JsonPass",
            next_state="NextState",
            result={"status": "ok"}
        )

        json_str = state.to_json()
        result = json.loads(json_str)

        assert result == {
            "Type": "Pass",
            "Next": "NextState",
            "Result": {"status": "ok"}
        }

    def test_pass_state_to_json_indented(self):
        """Test to_json with indentation."""
        state = PassState(name="IndentedPass", next_state="Next")

        json_str = state.to_json(indent=2)
        assert "\n  " in json_str

    # Test get_next_states method

    def test_pass_state_get_next_states(self):
        """Test get_next_states method."""
        state = PassState(name="TestPass", next_state="NextState")

        next_states = state.get_next_states()

        assert next_states == ["NextState"]

    def test_pass_state_get_next_states_end(self):
        """Test get_next_states for end state."""
        state = PassState(name="EndPass", end=True)

        next_states = state.get_next_states()

        assert next_states == []

    # Test string representations

    def test_pass_state_str(self):
        """Test string representation."""
        state = PassState(name="TestPass", next_state="NextState")

        assert str(state) == "PassState(name=TestPass)"

    def test_pass_state_repr(self):
        """Test detailed representation."""
        state = PassState(
            name="TestPass",
            next_state="NextState",
            end=False,
            result={"key": "value"}
        )

        repr_str = repr(state)
        assert "PassState" in repr_str
        assert "name='TestPass'" in repr_str
        assert "next_state='NextState'" in repr_str

    # Test edge cases

    @pytest.mark.asyncio
    async def test_pass_state_execute_empty_input(self, mock_path_processor):
        """Test PassState execution with empty input."""
        state = PassState(name="EmptyPass", next_state="NextState")
        state.set_path_processor(mock_path_processor)

        empty_input = {}
        output, next_state =  await state.execute(empty_input)

        assert output == "final_output"
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_pass_state_execute_different_input_types(self, mock_path_processor):
        """Test PassState execution with different input types."""
        state = PassState(name="TypeTestPass", next_state="NextState")
        state.set_path_processor(mock_path_processor)

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
            mock_path_processor.reset_mock()

            output, next_state =  await state.execute(input_data)

            assert output == "final_output", f"Failed for {description}"
            assert next_state == "NextState", f"Failed for {description}"

    # Test integration with real processor

    @pytest.mark.asyncio
    async def test_pass_state_integration_real_processor(self):
        """Test PassState integration with real processor."""
        from src.state_machine.__internal__.states.jsonpath_ng_processor import (
            JsonPathNgProcessor,
        )

        processor = JsonPathNgProcessor()
        state = PassState(name="IntegrationPass", next_state="NextState")
        state.set_path_processor(processor)

        input_data = {
            "user": {"name": "John", "age": 30},
            "metadata": {"source": "test"}
        }

        output, next_state =  await state.execute(input_data)

        assert output == input_data
        assert next_state == "NextState"


    @pytest.mark.asyncio
    async def test_pass_state_integration_with_result(self):
        """Test PassState integration with result injection."""
        from src.state_machine.__internal__.states.json_path import JSONPathProcessor

        processor = JSONPathProcessor()
        result_data = {"injected": "value", "count": 42}
        state = PassState(
            name="ResultIntegration",
            next_state="NextState",
            result=result_data,
            result_path="$.result"
        )
        state.set_path_processor(processor)

        input_data = {"original": "data"}

        output, next_state =  await state.execute(input_data)

        # Result should be injected at result_path
        assert "result" in output
        assert output["result"] == result_data
        assert next_state == "NextState"


    # Test inheritance

    def test_pass_state_inheritance(self):
        """Test that PassState properly inherits from BaseState."""
        state = PassState(name="InheritanceTest", next_state="NextState")

        assert hasattr(state, "execute")
        assert hasattr(state, "validate")
        assert hasattr(state, "to_dict")
        assert hasattr(state, "to_json")
        assert hasattr(state, "get_next_states")
        assert hasattr(state, "set_path_processor")

        assert state.state_name == "InheritanceTest"
        assert state.state_type == "Pass"
        assert state.get_next() == "NextState"
        assert state.is_end() is False

    # Test concurrency

    @pytest.mark.asyncio
    async def test_pass_state_concurrent_execution(self):
        """Test concurrent execution of PassState."""
        import asyncio

        state = PassState(name="ConcurrentPass", next_state="NextState")

        mock_processor = Mock()
        mock_processor.apply_input_path = Mock(side_effect=lambda data, path: data)
        mock_processor.apply_output_path = Mock(side_effect=lambda data, path: data)

        state.set_path_processor(mock_processor)

        num_tasks = 10
        tasks = []

        for i in range(num_tasks):
            input_data = {"id": i, "data": f"task_{i}"}
            task = asyncio.create_task(state.execute(input_data))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        assert len(results) == num_tasks
        for i, (output, next_state) in enumerate(results):
            assert output["id"] == i
            assert output["data"] == f"task_{i}"
            assert next_state == "NextState"
