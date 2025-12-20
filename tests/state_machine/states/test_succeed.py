"""
Tests for the SucceedState implementation.
"""

import json
from unittest.mock import Mock

import pytest

from src.states.base import StateError, get_path_processor, set_path_processor
from src.states.succeed import SucceedState


class TestSucceedState:
    """Test suite for SucceedState."""

    @pytest.fixture
    def mock_path_processor(self):
        """Create a mock path processor."""
        processor = Mock()
        processor.apply_input_path = Mock(return_value="processed_input")
        processor.apply_output_path = Mock(return_value="final_output")
        return processor

    @pytest.fixture
    def sample_input_data(self):
        """Sample input data for testing."""
        return {"data": "input data", "metadata": {"source": "test", "timestamp": "2024-01-15"}}

    # Test initialization and basic properties

    def test_succeed_state_creation(self):
        """Test basic SucceedState creation."""
        state = SucceedState(
            name="TestSucceedState", input_path="$.data", output_path="$.result", comment="Test comment", end=True
        )

        assert state.name == "TestSucceedState"
        assert state.type == "Succeed"
        assert state.input_path == "$.data"
        assert state.output_path == "$.result"
        assert state.comment == "Test comment"
        assert state.next_state is None
        assert state.end is False  # Not explicitly set
        assert state.result_path is None

    def test_succeed_state_defaults(self):
        """Test SucceedState with default values."""
        state = SucceedState(name="SimpleSucceed")

        assert state.name == "SimpleSucceed"
        assert state.type == "Succeed"
        assert state.input_path is None
        assert state.output_path is None
        assert state.comment is None
        assert state.next_state is None
        assert state.result_path is None

    def test_succeed_state_type_fixed(self):
        """Test that SucceedState always has Type 'Succeed'."""
        state = SucceedState(name="TestSucceed", end=True)
        # Even if we try to change it, __post_init__ sets it back
        state.type = "WrongType"
        # Reinitialize to trigger __post_init__
        state.__post_init__()
        assert state.type == "Succeed"

    # Test validation

    def test_succeed_state_validation_valid(self):
        """Test validation of valid SucceedState."""
        test_cases = [
            # Simple succeed state
            {"name": "ValidSucceed", "type": "Succeed"},
            # With input path
            {"name": "ValidSucceed", "type": "Succeed", "input_path": "$.data"},
            # With output path
            {"name": "ValidSucceed", "type": "Succeed", "output_path": "$.result"},
            # With both paths
            {"name": "ValidSucceed", "type": "Succeed", "input_path": "$.input", "output_path": "$.output"},
            # With comment
            {"name": "ValidSucceed", "type": "Succeed", "comment": "Successful completion"},
        ]

        for test_case in test_cases:
            # Create state with test case parameters
            kwargs = {k: v for k, v in test_case.items() if k != "type"}
            state = SucceedState(**kwargs)

            # Should not raise any error
            state.validate()

    def test_succeed_state_validation_no_name(self):
        """Test validation with empty name."""

        class InvalidState(SucceedState):
            def __init__(self):
                self.name = ""
                self.type = "Succeed"

        state = InvalidState()
        with pytest.raises(ValueError, match="State name cannot be empty"):
            state.validate()

    def test_succeed_state_validation_wrong_type(self):
        """Test validation with wrong type (should be prevented by __post_init__)."""
        # This shouldn't happen in practice due to __post_init__
        state = SucceedState(name="WrongType")
        state.type = "Pass"  # Manually set wrong type

        with pytest.raises(ValueError, match="must have Type 'Succeed'"):
            state.validate()

    def test_succeed_state_validation_has_next(self):
        """Test validation with Next field."""

        class InvalidState(SucceedState):
            def __init__(self):
                self.name = "InvalidSucceed"
                self.type = "Succeed"
                self.next_state = "NextState"

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have Next field"):
            state.validate()

    def test_succeed_state_validation_has_end(self):
        """Test validation with End field."""

        class InvalidState(SucceedState):
            def __init__(self):
                self.name = "InvalidSucceed"
                self.type = "Succeed"
                self.end = True

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have End field"):
            state.validate()

    def test_succeed_state_validation_has_result_path(self):
        """Test validation with ResultPath."""

        class InvalidState(SucceedState):
            def __init__(self):
                self.name = "InvalidSucceed"
                self.type = "Succeed"
                self.result_path = "$.result"

        state = InvalidState()
        with pytest.raises(ValueError, match="cannot have ResultPath"):
            state.validate()

    # Test execute method

    @pytest.mark.asyncio
    async def test_succeed_state_execute_simple(self, mock_path_processor, sample_input_data):
        """Test simple SucceedState execution."""
        state = SucceedState(name="SimpleSucceed")
        state.set_path_processor(mock_path_processor)

        output, next_state = await state.execute(sample_input_data)

        # Verify processor calls
        mock_path_processor.apply_input_path.assert_called_once_with(sample_input_data, None)
        mock_path_processor.apply_output_path.assert_called_once_with("processed_input", None)

        # Verify results
        assert output == "final_output"
        assert next_state is None  # Succeed states have no next state

    @pytest.mark.asyncio
    async def test_succeed_state_execute_with_input_path(self, mock_path_processor, sample_input_data):
        """Test SucceedState execution with input path."""
        state = SucceedState(name="SucceedWithInput", input_path="$.data")
        state.set_path_processor(mock_path_processor)

        await state.execute(sample_input_data)

        mock_path_processor.apply_input_path.assert_called_once_with(sample_input_data, "$.data")
        mock_path_processor.apply_output_path.assert_called_once_with("processed_input", None)

    @pytest.mark.asyncio
    async def test_succeed_state_execute_with_output_path(self, mock_path_processor, sample_input_data):
        """Test SucceedState execution with output path."""
        state = SucceedState(name="SucceedWithOutput", output_path="$.result")
        state.set_path_processor(mock_path_processor)

        await state.execute(sample_input_data)

        mock_path_processor.apply_input_path.assert_called_once_with(sample_input_data, None)
        mock_path_processor.apply_output_path.assert_called_once_with("processed_input", "$.result")

    @pytest.mark.asyncio
    async def test_succeed_state_execute_with_both_paths(self, mock_path_processor, sample_input_data):
        """Test SucceedState execution with both input and output paths."""
        state = SucceedState(name="CompleteSucceed", input_path="$.data", output_path="$.output")
        state.set_path_processor(mock_path_processor)

        await state.execute(sample_input_data)

        mock_path_processor.apply_input_path.assert_called_once_with(sample_input_data, "$.data")
        mock_path_processor.apply_output_path.assert_called_once_with("processed_input", "$.output")

    @pytest.mark.asyncio
    async def test_succeed_state_execute_with_context(self, mock_path_processor, sample_input_data):
        """Test SucceedState execution with context."""
        state = SucceedState(name="SucceedWithContext")
        state.set_path_processor(mock_path_processor)

        context = {"execution_id": "test-123", "timestamp": "2024-01-15"}

        output, next_state = await state.execute(sample_input_data, context)

        # Context should be ignored by SucceedState
        assert output == "final_output"
        assert next_state is None

    @pytest.mark.asyncio
    async def test_succeed_state_execute_path_processing_error(self, sample_input_data):
        """Test SucceedState execution when path processing fails."""
        # Create a mock processor that raises an exception
        mock_processor = Mock()
        mock_processor.apply_input_path.side_effect = ValueError("Path not found")

        state = SucceedState(name="ErrorSucceed")
        state.set_path_processor(mock_processor)

        with pytest.raises(StateError, match="Failed to execute succeed state"):
            await state.execute(sample_input_data)

    @pytest.mark.asyncio
    async def test_succeed_state_execute_nil_input(self, mock_path_processor):
        """Test SucceedState execution with None input."""
        state = SucceedState(name="SucceedWithNil")
        state.set_path_processor(mock_path_processor)

        output, next_state = await state.execute(None)

        mock_path_processor.apply_input_path.assert_called_once_with(None, None)
        assert output == "final_output"
        assert next_state is None

    @pytest.mark.asyncio
    async def test_succeed_state_execute_uses_default_processor(self, sample_input_data):
        """Test that SucceedState uses default path processor when none is set."""
        # Store original processor
        original_processor = get_path_processor()

        try:
            # Create a mock default processor
            mock_default = Mock()
            mock_default.apply_input_path = Mock(return_value="default_processed")
            mock_default.apply_output_path = Mock(return_value="default_output")

            # Set it as default
            set_path_processor(mock_default)

            # Create state without setting processor
            state = SucceedState(name="DefaultProcessorSucceed")

            output, next_state = await state.execute(sample_input_data)

            # Should use default processor
            mock_default.apply_input_path.assert_called_once_with(sample_input_data, None)
            assert output == "default_output"

        finally:
            # Restore original processor
            set_path_processor(original_processor)

    # Test to_dict method

    def test_succeed_state_to_dict_simple(self):
        """Test to_dict with simple SucceedState."""
        state = SucceedState(name="SimpleSucceed")

        result = state.to_dict()

        assert result == {"Type": "Succeed"}
        assert "InputPath" not in result
        assert "OutputPath" not in result
        assert "Comment" not in result
        assert "Next" not in result
        assert "End" not in result
        assert "ResultPath" not in result

    def test_succeed_state_to_dict_with_input_path(self):
        """Test to_dict with input path."""
        state = SucceedState(name="SucceedWithInput", input_path="$.data")

        result = state.to_dict()

        assert result == {"Type": "Succeed", "InputPath": "$.data"}
        assert "OutputPath" not in result
        assert "Comment" not in result

    def test_succeed_state_to_dict_with_output_path(self):
        """Test to_dict with output path."""
        state = SucceedState(name="SucceedWithOutput", output_path="$.result")

        result = state.to_dict()

        assert result == {"Type": "Succeed", "OutputPath": "$.result"}
        assert "InputPath" not in result
        assert "Comment" not in result

    def test_succeed_state_to_dict_with_comment(self):
        """Test to_dict with comment."""
        state = SucceedState(name="SucceedWithComment", comment="Successful completion")

        result = state.to_dict()

        assert result == {"Type": "Succeed", "Comment": "Successful completion"}
        assert "InputPath" not in result
        assert "OutputPath" not in result

    def test_succeed_state_to_dict_complete(self):
        """Test to_dict with all allowed fields."""
        state = SucceedState(
            name="CompleteSucceed", input_path="$.input", output_path="$.output", comment="Complete succeed state"
        )

        result = state.to_dict()

        assert result == {
            "Type": "Succeed",
            "InputPath": "$.input",
            "OutputPath": "$.output",
            "Comment": "Complete succeed state",
        }
        # Verify disallowed fields are not present
        assert "Next" not in result
        assert "End" not in result
        assert "ResultPath" not in result

    # Test to_json method (inherited from BaseState)

    def test_succeed_state_to_json(self):
        """Test to_json method."""
        state = SucceedState(name="JsonSucceed", input_path="$.data", comment="JSON test")

        json_str = state.to_json()
        result = json.loads(json_str)

        assert result == {"Type": "Succeed", "InputPath": "$.data", "Comment": "JSON test"}

    def test_succeed_state_to_json_indented(self):
        """Test to_json with indentation."""
        state = SucceedState(name="IndentedSucceed", comment="Indented")

        json_str = state.to_json(indent=2)
        assert "\n  " in json_str  # Check for indentation

    # Test get_next_states method

    def test_succeed_state_get_next_states(self):
        """Test get_next_states method."""
        state = SucceedState(name="SucceedNoNext")

        next_states = state.get_next_states()

        # Succeed states have no next states
        assert next_states == []

    # Test string representations

    def test_succeed_state_str(self):
        """Test string representation."""
        state = SucceedState(name="TestSucceed")

        assert str(state) == "SucceedState(name=TestSucceed)"

    def test_succeed_state_repr(self):
        """Test detailed representation."""
        state = SucceedState(name="TestSucceed", input_path="$.input", output_path="$.output", comment="Test state")

        repr_str = repr(state)
        assert "SucceedState" in repr_str
        assert "name='TestSucceed'" in repr_str
        assert "input_path='$.input'" in repr_str
        assert "output_path='$.output'" in repr_str
        assert "comment='Test state'" in repr_str

    # Test edge cases and special scenarios

    @pytest.mark.asyncio
    async def test_succeed_state_execute_empty_input(self, mock_path_processor):
        """Test SucceedState execution with empty input."""
        state = SucceedState(name="SucceedEmpty")
        state.set_path_processor(mock_path_processor)

        empty_input = {}
        output, next_state = await state.execute(empty_input)

        mock_path_processor.apply_input_path.assert_called_once_with(empty_input, None)
        assert output == "final_output"
        assert next_state is None

    @pytest.mark.asyncio
    async def test_succeed_state_execute_different_input_types(self, mock_path_processor):
        """Test SucceedState execution with different input types."""
        state = SucceedState(name="TypeTestSucceed")
        state.set_path_processor(mock_path_processor)

        test_cases = [
            # (input, description)
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

            output, next_state = await state.execute(input_data)

            mock_path_processor.apply_input_path.assert_called_once_with(input_data, None)
            assert output == "final_output", f"Failed for {description}"
            assert next_state is None, f"Failed for {description}"

    @pytest.mark.asyncio
    async def test_succeed_state_execute_complex_transformation(self, mock_path_processor):
        """Test complex data transformation scenario."""

        # Setup mock to simulate actual path processing
        def apply_input_path(input_data, path):
            if path == "$.transaction":
                return input_data.get("transaction", {})
            return input_data

        def apply_output_path(processed_input, path):
            if path == "$.summary":
                return {"summary": processed_input}
            return processed_input

        mock_processor = Mock()
        mock_processor.apply_input_path = Mock(side_effect=apply_input_path)
        mock_processor.apply_output_path = Mock(side_effect=apply_output_path)

        # Create state with paths
        state = SucceedState(name="TransactionSummary", input_path="$.transaction", output_path="$.summary")
        state.set_path_processor(mock_processor)

        # Complex input data
        input_data = {
            "transaction": {"id": "txn_12345", "amount": 100.50, "currency": "USD", "status": "completed"},
            "user": {"id": "user_67890", "email": "test@example.com"},
            "metadata": {"processed": True, "version": "1.0"},
        }

        output, next_state = await state.execute(input_data)

        # Verify calls
        mock_processor.apply_input_path.assert_called_once_with(input_data, "$.transaction")
        mock_processor.apply_output_path.assert_called_once_with(input_data["transaction"], "$.summary")

        # Verify output structure
        assert output == {"summary": input_data["transaction"]}
        assert next_state is None

    # Test integration with actual JsonPathNgProcessor

    @pytest.mark.asyncio
    async def test_succeed_state_integration_real_processor(self):
        """Test SucceedState integration with real JsonPathNgProcessor."""
        from src.states.json_path import JSONPathProcessor

        processor = JSONPathProcessor()
        state = SucceedState(name="IntegrationTest")
        state.set_path_processor(processor)

        input_data = {"user": {"name": "John", "age": 30}, "metadata": {"source": "test"}}

        output, next_state = await state.execute(input_data)

        # With no paths, output should be same as input
        assert output == input_data
        assert next_state is None

    @pytest.mark.asyncio
    async def test_succeed_state_integration_with_paths(self):
        """Test SucceedState integration with real processor and paths."""
        from src.states.json_path import JSONPathProcessor

        processor = JSONPathProcessor()
        state = SucceedState(name="PathIntegration", input_path="$.user.name", output_path="$.username")
        state.set_path_processor(processor)

        input_data = {"user": {"name": "Alice", "age": 25}, "other": "data"}

        output, next_state = await state.execute(input_data)

        # Should extract name and wrap in "username" field
        assert output == {"username": "Alice"}
        assert next_state is None

    # Test that SucceedState inherits from BaseState correctly

    def test_succeed_state_inheritance(self):
        """Test that SucceedState properly inherits from BaseState."""
        state = SucceedState(name="InheritanceTest")

        # Check inherited methods
        assert hasattr(state, "execute")
        assert hasattr(state, "validate")
        assert hasattr(state, "to_dict")
        assert hasattr(state, "to_json")
        assert hasattr(state, "get_next_states")
        assert hasattr(state, "set_path_processor")

        # Check inherited properties
        assert state.state_name == "InheritanceTest"
        assert state.state_type == "Succeed"
        assert state.get_next() is None
        assert state.is_end() is False  # Not explicitly set as end state

    # Test concurrency safety

    @pytest.mark.asyncio
    async def test_succeed_state_concurrent_execution(self):
        """Test concurrent execution of SucceedState."""
        import asyncio
        from unittest.mock import Mock

        state = SucceedState(name="ConcurrentSucceed")

        # Create synchronous mock processor (matching real JsonPathNgProcessor)
        mock_processor = Mock()
        mock_processor.apply_input_path = Mock(side_effect=lambda data, path: data)
        mock_processor.apply_output_path = Mock(side_effect=lambda data, path: data)

        state.set_path_processor(mock_processor)

        # Run concurrent executions
        num_tasks = 10
        tasks = []

        for i in range(num_tasks):
            input_data = {"id": i, "data": f"task_{i}"}
            task = asyncio.create_task(state.execute(input_data))
            tasks.append(task)

        # Wait for all tasks
        results = await asyncio.gather(*tasks)

        # Verify all completed successfully
        assert len(results) == num_tasks
        for i, (output, next_state) in enumerate(results):
            assert output["id"] == i
            assert output["data"] == f"task_{i}"
            assert next_state is None

        # Verify processor was called correct number of times
        assert mock_processor.apply_input_path.call_count == num_tasks
        assert mock_processor.apply_output_path.call_count == num_tasks


# Test helper functions

# Benchmark tests (optional - run with pytest -m benchmark)


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_succeed_state_benchmark(benchmark):
    """Benchmark SucceedState execution."""
    from src.states.json_path import JSONPathProcessor

    processor = JSONPathProcessor()
    state = SucceedState(name="BenchmarkSucceed")
    state.set_path_processor(processor)

    input_data = {"test": "data", "nested": {"level1": {"level2": "value"}, "array": [1, 2, 3, 4, 5]}}

    # Run benchmark
    async def run_execute():
        return await state.execute(input_data)

    # Use pytest-benchmark if available
    benchmark(run_execute)
    output, next_state = await run_execute()

    assert output == input_data
    assert next_state is None
