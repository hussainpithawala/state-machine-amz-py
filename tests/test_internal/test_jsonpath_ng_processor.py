"""
Test suite for JsonPathNgProcessor using jsonpath-ng library.
"""
import copy

import pytest

from src.state_machine.__internal__.states.jsonpath_ng_processor import (
    JsonPathNgProcessor,
)


@pytest.mark.skip("Unsupported processor for testing")
class TestJsonPathNgProcessor:
    """Test suite for JsonPathNgProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a fresh JsonPathNgProcessor for each test."""
        return JsonPathNgProcessor()

    @pytest.fixture
    def sample_data(self):
        """Sample JSON data for testing."""
        return {
            "store": {
                "book": [
                    {
                        "category": "reference",
                        "author": "Nigel Rees",
                        "title": "Sayings of the Century",
                        "price": 8.95,
                    },
                    {
                        "category": "fiction",
                        "author": "Evelyn Waugh",
                        "title": "Sword of Honour",
                        "price": 12.99,
                    },
                    {
                        "category": "fiction",
                        "author": "Herman Melville",
                        "title": "Moby Dick",
                        "isbn": "0-553-21311-3",
                        "price": 8.99,
                    },
                    {
                        "category": "fiction",
                        "author": "J. R. R. Tolkien",
                        "title": "The Lord of the Rings",
                        "isbn": "0-395-19395-8",
                        "price": 22.99,
                    },
                ],
                "bicycle": {"color": "red", "price": 19.95},
            },
            "expensive": 10,
        }

    @pytest.fixture
    def amazon_state_example(self):
        """Example data similar to AWS Step Functions state machine input."""
        return {
            "input": {
                "comment": "Example input",
                "data": {"value": 42, "nested": {"array": [1, 2, 3], "flag": True}},
                "metadata": {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "source": "api-gateway",
                },
            },
            "execution": {
                "id": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:abc123",
                "startTime": "2024-01-15T10:29:55Z",
            },
        }

    # Test apply_input_path method

    def test_apply_input_path_none(self, processor, sample_data):
        """Test apply_input_path with None path."""
        result = processor.apply_input_path(sample_data, None)
        assert result == sample_data

    def test_apply_input_path_empty(self, processor, sample_data):
        """Test apply_input_path with empty path."""
        result = processor.apply_input_path(sample_data, "")
        assert result == sample_data

    def test_apply_input_path_root(self, processor, sample_data):
        """Test apply_input_path with root path $."""
        result = processor.apply_input_path(sample_data, "$")
        assert result == sample_data

    def test_apply_input_path_simple_field(self, processor, sample_data):
        """Test apply_input_path with simple field access."""
        result = processor.apply_input_path(sample_data, "$.expensive")
        assert result == 10

    def test_apply_input_path_nested_field(self, processor, sample_data):
        """Test apply_input_path with nested field access."""
        result = processor.apply_input_path(sample_data, "$.store.bicycle.color")
        assert result == "red"

    def test_apply_input_path_array_index(self, processor, sample_data):
        """Test apply_input_path with array index."""
        result = processor.apply_input_path(sample_data, "$.store.book[0].title")
        assert result == "Sayings of the Century"

    def test_apply_input_path_wildcard(self, processor, sample_data):
        """Test apply_input_path with wildcard."""
        result = processor.apply_input_path(sample_data, "$.store.book[*].author")
        assert isinstance(result, list)
        assert len(result) == 4
        assert "Nigel Rees" in result
        assert "Evelyn Waugh" in result
        assert "Herman Melville" in result
        assert "J. R. R. Tolkien" in result

    def test_apply_input_path_filter_expression(self, processor, sample_data):
        """Test apply_input_path with filter expression."""
        result = processor.apply_input_path(
            sample_data, "$.store.book[?(@.price < 10)].title"
        )
        assert isinstance(result, list)
        assert len(result) == 2
        assert "Sayings of the Century" in result
        assert "Moby Dick" in result

    def test_apply_input_path_slice(self, processor, sample_data):
        """Test apply_input_path with slice."""
        result = processor.apply_input_path(sample_data, "$.store.book[0:2].title")
        assert isinstance(result, list)
        assert len(result) == 2
        assert "Sayings of the Century" in result[0]
        assert "Sword of Honour" in result[1]

    def test_apply_input_path_nonexistent_path(self, processor, sample_data):
        """Test apply_input_path with non-existent path (should return original data)."""
        original = copy.deepcopy(sample_data)
        result = processor.apply_input_path(sample_data, "$.nonexistent.path")
        # According to our implementation, should return original data
        assert result == original

    # Test apply_result_path method

    def test_apply_result_path_none(self, processor):
        """Test apply_result_path with None path."""
        input_data = {"original": "data"}
        result_data = "new_result"

        result = processor.apply_result_path(input_data, result_data, None)
        assert result == result_data

    def test_apply_result_path_empty(self, processor):
        """Test apply_result_path with empty path."""
        input_data = {"original": "data"}
        result_data = "new_result"

        result = processor.apply_result_path(input_data, result_data, "")
        assert result == result_data

    def test_apply_result_path_root(self, processor):
        """Test apply_result_path with root path $."""
        input_data = {"original": "data"}
        result_data = "new_result"

        result = processor.apply_result_path(input_data, result_data, "$")
        assert result == result_data

    def test_apply_result_path_set_simple_field(self, processor):
        """Test apply_result_path setting a simple field."""
        input_data = {"existing": "value"}
        result_data = "new_value"

        result = processor.apply_result_path(input_data, result_data, "$.result")
        assert result["existing"] == "value"
        assert result["result"] == "new_value"

    def test_apply_result_path_set_nested_field(self, processor):
        """Test apply_result_path setting a nested field."""
        input_data = {"top": {"middle": "old"}}
        result_data = "new"

        result = processor.apply_result_path(input_data, result_data, "$.top.middle")
        assert result["top"]["middle"] == "new"

    def test_apply_result_path_set_new_nested_structure(self, processor):
        """Test apply_result_path creating new nested structure."""
        input_data = {}
        result_data = "deep_value"

        result = processor.apply_result_path(input_data, result_data, "$.a.b.c")
        assert result["a"]["b"]["c"] == "deep_value"

    @pytest.mark.skip(
        reason="test_apply_result_path_set_array_element is currently under development"
    )
    def test_apply_result_path_set_array_element(self, processor):
        """Test apply_result_path setting array element."""
        input_data = {"items": ["a", "b", "c"]}
        result_data = "X"

        result = processor.apply_result_path(input_data, result_data, "$.items[1]")
        assert result["items"][1] == "X"
        assert result["items"][0] == "a"
        assert result["items"][2] == "c"

    @pytest.mark.skip(
        reason="test_apply_result_path_set_with_wildcard is currently under development"
    )
    def test_apply_result_path_set_with_wildcard(self, processor):
        """Test apply_result_path with wildcard (should update all matches)."""
        input_data = {
            "books": [
                {"title": "Book1", "read": False},
                {"title": "Book2", "read": False},
                {"title": "Book3", "read": False},
            ]
        }
        result_data = True

        result = processor.apply_result_path(input_data, result_data, "$.books[*].read")
        assert all(book["read"] == True for book in result["books"])

    # Test apply_output_path method

    def test_apply_output_path_none(self, processor, sample_data):
        """Test apply_output_path with None path."""
        result = processor.apply_output_path(sample_data, None)
        assert result == sample_data

    def test_apply_output_path_empty(self, processor, sample_data):
        """Test apply_output_path with empty path."""
        result = processor.apply_output_path(sample_data, "")
        assert result == sample_data

    def test_apply_output_path_root(self, processor, sample_data):
        """Test apply_output_path with root path $."""
        result = processor.apply_output_path(sample_data, "$")
        assert result == sample_data

    def test_apply_output_path_simple_field(self, processor, sample_data):
        """Test apply_output_path with simple field."""
        result = processor.apply_output_path(sample_data, "$.expensive")
        assert result == 10

    def test_apply_output_path_nested_field(self, processor, sample_data):
        """Test apply_output_path with nested field."""
        result = processor.apply_output_path(sample_data, "$.store.bicycle")
        assert result == {"color": "red", "price": 19.95}

    def test_apply_output_path_array_slice(self, processor, sample_data):
        """Test apply_output_path with array slice."""
        result = processor.apply_output_path(sample_data, "$.store.book[0:2]")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["title"] == "Sayings of the Century"
        assert result[1]["title"] == "Sword of Honour"

    @pytest.mark.skip(
        reason="test_apply_output_path_with_filter is currently under development"
    )
    def test_apply_output_path_with_filter(self, processor, sample_data):
        """Test apply_output_path with filter."""
        result = processor.apply_output_path(
            sample_data, "$.store.book[?(@.price > 20)]"
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "The Lord of the Rings"

    def test_apply_output_path_nonexistent(self, processor, sample_data):
        """Test apply_output_path with non-existent path."""
        original = copy.deepcopy(sample_data)
        result = processor.apply_output_path(sample_data, "$.does.not.exist")
        # Should return original data according to implementation
        assert result == original

    # Test _get_value method

    def test_get_value_single_match(self, processor, sample_data):
        """Test _get_value with single match."""
        result = processor._get_value(sample_data, "$.expensive")
        assert result == 10

    def test_get_value_multiple_matches(self, processor, sample_data):
        """Test _get_value with multiple matches."""
        result = processor._get_value(sample_data, "$.store.book[*].price")
        assert isinstance(result, list)
        assert len(result) == 4
        assert 8.95 in result
        assert 12.99 in result
        assert 8.99 in result
        assert 22.99 in result

    def test_get_value_no_match(self, processor, sample_data):
        """Test _get_value with no matches."""
        original = copy.deepcopy(sample_data)
        result = processor._get_value(sample_data, "$.nonexistent.path")
        assert result == original

    @pytest.mark.skip(
        reason="test_get_value_complex_expression is currently under development"
    )
    def test_get_value_complex_expression(self, processor, sample_data):
        """Test _get_value with complex JSONPath expression."""
        result = processor._get_value(
            sample_data, "$.store.book[?(@.category == 'fiction' && @.price < 10)]"
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Moby Dick"

    # Test _set_value method

    def test_set_value_simple_path(self, processor):
        """Test _set_value with simple path."""
        data = {"existing": "value"}
        result = processor._set_value(data, "$.new_field", "new_value")
        assert result["existing"] == "value"
        assert result["new_field"] == "new_value"

    def test_set_value_update_existing(self, processor):
        """Test _set_value updating existing field."""
        data = {"field": "old_value"}
        result = processor._set_value(data, "$.field", "new_value")
        assert result["field"] == "new_value"

    def test_set_value_nested_path(self, processor):
        """Test _set_value with nested path."""
        data = {"top": {"middle": {"bottom": "old"}}}
        result = processor._set_value(data, "$.top.middle.bottom", "new")
        assert result["top"]["middle"]["bottom"] == "new"

    def test_set_value_create_nested(self, processor):
        """Test _set_value creating nested structure."""
        data = {}
        result = processor._set_value(data, "$.a.b.c", "deep_value")
        assert result["a"]["b"]["c"] == "deep_value"

    @pytest.mark.skip(reason="test_set_value_array_index")
    def test_set_value_array_index(self, processor):
        """Test _set_value with array index."""
        data = {"items": ["a", "b", "c"]}
        result = processor._set_value(data, "$.items[1]", "X")
        assert result["items"][1] == "X"
        assert result["items"][0] == "a"
        assert result["items"][2] == "c"

    @pytest.mark.skip(
        reason="test_set_value_multiple_matches is currently under development"
    )
    def test_set_value_multiple_matches(self, processor):
        """Test _set_value updating multiple matches."""
        data = {
            "books": [
                {"read": False, "title": "Book1"},
                {"read": False, "title": "Book2"},
            ]
        }
        result = processor._set_value(data, "$.books[*].read", True)
        assert result["books"][0]["read"] == True
        assert result["books"][1]["read"] == True

    # Test expand_parameters method

    def test_expand_parameters_no_paths(self, processor, amazon_state_example):
        """Test expand_parameters without JSONPath references."""
        params = {"static_string": "hello", "static_number": 42, "static_bool": True}

        result = processor.expand_parameters(params, amazon_state_example)
        assert result == params

    def test_expand_parameters_with_paths(self, processor, amazon_state_example):
        """Test expand_parameters with JSONPath references."""
        params = {
            "value": "$.input.data.value",
            "source": "$.input.metadata.source",
            "execution_id": "$.execution.id",
        }

        result = processor.expand_parameters(params, amazon_state_example)
        assert result["value"] == 42
        assert result["source"] == "api-gateway"
        assert (
                result["execution_id"]
                == "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:abc123"
        )

    def test_expand_parameters_mixed(self, processor, amazon_state_example):
        """Test expand_parameters with mixed static and path values."""
        params = {
            "static": "fixed_value",
            "dynamic": "$.input.data.nested.flag",
            "nested": {"value": "$.input.data.value", "static": "nested_static"},
        }

        result = processor.expand_parameters(params, amazon_state_example)
        assert result["static"] == "fixed_value"
        assert result["dynamic"] == True
        assert result["nested"]["value"] == 42
        assert result["nested"]["static"] == "nested_static"

    def test_expand_parameters_array(self, processor, amazon_state_example):
        """Test expand_parameters with array containing paths."""
        params = {
            "values": [
                "$.input.data.nested.array[0]",
                "$.input.data.nested.array[1]",
                "static_value",
            ]
        }

        result = processor.expand_parameters(params, amazon_state_example)
        assert result["values"] == [1, 2, "static_value"]

    # Test expand_value method

    def test_expand_value_string_path(self, processor, amazon_state_example):
        """Test expand_value with string JSONPath."""
        result = processor.expand_value("$.input.data.value", amazon_state_example)
        assert result == 42

    def test_expand_value_string_literal(self, processor, amazon_state_example):
        """Test expand_value with string literal."""
        result = processor.expand_value("literal string", amazon_state_example)
        assert result == "literal string"

    def test_expand_value_dict(self, processor, amazon_state_example):
        """Test expand_value with dictionary."""
        value = {
            "path_value": "$.input.data.value",
            "static_value": "static",
            "nested": {"flag": "$.input.data.nested.flag"},
        }

        result = processor.expand_value(value, amazon_state_example)
        assert result["path_value"] == 42
        assert result["static_value"] == "static"
        assert result["nested"]["flag"] == True

    def test_expand_value_list(self, processor, amazon_state_example):
        """Test expand_value with list."""
        value = ["$.input.data.value", "static", {"nested": "$.input.data.nested.flag"}]

        result = processor.expand_value(value, amazon_state_example)
        assert result[0] == 42
        assert result[1] == "static"
        assert result[2]["nested"] == True

    def test_expand_value_primitive_types(self, processor, amazon_state_example):
        """Test expand_value with primitive types (no expansion)."""
        assert processor.expand_value(42, amazon_state_example) == 42
        assert processor.expand_value(3.14, amazon_state_example) == 3.14
        assert processor.expand_value(True, amazon_state_example) == True
        assert processor.expand_value(None, amazon_state_example) == None

    # Test Amazon States Language specific scenarios

    @pytest.mark.skip(
        reason="test_amazon_input_path_scenarios is currently under development"
    )
    def test_amazon_input_path_scenarios(self, processor, amazon_state_example):
        """Test Amazon States Language input path scenarios."""
        # InputPath to select subset of input
        result = processor.apply_input_path(amazon_state_example, "$.input.data")
        assert result["value"] == 42
        assert "nested" in result
        assert "metadata" not in result

        # InputPath to select specific value
        result = processor.apply_input_path(amazon_state_example, "$.input.data.value")
        assert result == 42

        # InputPath with wildcard
        result = processor.apply_input_path(amazon_state_example, "$.input.*.timestamp")
        # Should find timestamp in metadata
        assert isinstance(result, list)
        assert "2024-01-15T10:30:00Z" in result

    def test_amazon_result_path_scenarios(self, processor, amazon_state_example):
        """Test Amazon States Language result path scenarios."""
        # ResultPath to combine input and result
        input_data = amazon_state_example["input"]["data"]
        task_result = {"status": "success", "processed": True}

        result = processor.apply_result_path(input_data, task_result, "$.task_result")

        assert result["value"] == 42
        assert result["task_result"]["status"] == "success"
        assert result["task_result"]["processed"] == True

        # ResultPath to replace entire input
        result = processor.apply_result_path({"old": "data"}, {"new": "data"}, None)
        assert result == {"new": "data"}

    def test_amazon_output_path_scenarios(self, processor):
        """Test Amazon States Language output path scenarios."""
        # OutputPath to select subset of output
        output_data = {
            "statusCode": 200,
            "body": {"message": "Success", "data": [1, 2, 3]},
            "headers": {"Content-Type": "application/json"},
        }

        result = processor.apply_output_path(output_data, "$.body")
        assert result["message"] == "Success"
        assert result["data"] == [1, 2, 3]

        # OutputPath to select specific field
        result = processor.apply_output_path(output_data, "$.statusCode")
        assert result == 200

    # Test edge cases and error scenarios

    def test_empty_data(self, processor):
        """Test with empty data structures."""
        empty_dict = {}
        result = processor.apply_input_path(empty_dict, "$.any.path")
        assert result == empty_dict

        empty_list = []
        result = processor.apply_input_path(empty_list, "$[0]")
        assert result == empty_list

    def test_null_values(self, processor):
        """Test with null/None values."""
        data = {"field": None, "nested": {"null_field": None}}

        result = processor.apply_input_path(data, "$.field")
        assert result is None

        result = processor.apply_input_path(data, "$.nested.null_field")
        assert result is None

        # Setting null value
        result = processor.apply_result_path({}, None, "$.null_field")
        assert result["null_field"] is None

    def test_special_characters_in_field_names(self, processor):
        """Test with special characters in field names."""
        # Note: jsonpath-ng handles special characters with bracket notation
        data = {
            "field-with-dash": "value1",
            "field.with.dot": "value2",
            "field with spaces": "value3",
        }

        # Test with bracket notation (standard JSONPath for special chars)
        result = processor.apply_input_path(data, "$['field-with-dash']")
        assert result == "value1"

        result = processor.apply_input_path(data, "$['field.with.dot']")
        assert result == "value2"

    def test_complex_nested_structures(self, processor):
        """Test with complex nested structures."""
        data = {"a": {"b": [{"c": {"d": 1}}, {"c": {"d": 2, "e": {"f": "deep"}}}]}}

        # Deep nested access
        result = processor.apply_input_path(data, "$.a.b[1].c.e.f")
        assert result == "deep"

        # Multiple levels of array access
        result = processor.apply_input_path(data, "$.a.b[*].c.d")
        assert result == [1, 2]

    @pytest.mark.skip(
        reason="test_jsonpath_ng_specific_features is currently under development"
    )
    def test_jsonpath_ng_specific_features(self, processor, sample_data):
        """Test jsonpath-ng specific features."""
        # Parent selector
        result = processor._get_value(sample_data, "$.store.book[0].category~")
        # The ~ operator returns the parent of the matched node
        # Implementation may vary

        # Length operator
        result = processor._get_value(sample_data, "$.store.book.length()")
        # Should return 4

        # Union operator
        result = processor._get_value(sample_data, "$.store.book[0,2].title")
        assert isinstance(result, list)
        assert len(result) == 2
        assert "Sayings of the Century" in result
        assert "Moby Dick" in result

    # Test PathProcessor protocol compliance

    def test_implements_path_processor_protocol(self, processor):
        """Test that JsonPathNgProcessor implements PathProcessor protocol."""
        from src.state_machine.__internal__.states.base import PathProcessor

        assert isinstance(processor, PathProcessor)
        assert hasattr(processor, "apply_input_path")
        assert hasattr(processor, "apply_result_path")
        assert hasattr(processor, "apply_output_path")

        # Verify method signatures
        import inspect

        input_path_sig = inspect.signature(processor.apply_input_path)
        assert len(input_path_sig.parameters) == 2

        result_path_sig = inspect.signature(processor.apply_result_path)
        assert len(result_path_sig.parameters) == 3

        output_path_sig = inspect.signature(processor.apply_output_path)
        assert len(output_path_sig.parameters) == 2

    @pytest.mark.skip(
        reason="test_integration_with_base_state is currently under development"
    )
    def test_integration_with_base_state(self, processor, amazon_state_example):
        """Test integration with BaseState's _apply_paths method."""
        from tests.test_internal.test_base import ConcreteState

        # Create a test state with various paths
        class TestState(ConcreteState):
            def __init__(self):
                self.name = "TestTask"
                self.type = "Task"
                self.next_state = "NextState"
                self.input_path = "$.input.data"
                self.result_path = "$.task_result"
                self.output_path = "$.task_result"
                self._path_processor = processor
                super().__init__(self.name, self.type)

            async def execute(self, input_data, context=None):
                # Simulate task execution
                return (
                    {"status": "processed", "value": input_data.get("value", 0) * 2},
                    self.next_state,
                    None,
                )

        state = TestState()

        # Simulate _apply_paths logic
        input_data = amazon_state_example
        result = {"status": "success", "processed_value": 84}

        # Apply input path
        filtered_input = processor.apply_input_path(input_data, state.input_path)
        assert filtered_input["value"] == 42

        # Apply result path
        combined = processor.apply_result_path(
            filtered_input, result, state.result_path
        )
        assert combined["value"] == 42
        assert combined["task_result"]["status"] == "success"

        # Apply output path
        output = processor.apply_output_path(combined, state.output_path)
        assert output["status"] == "success"
        assert output["processed_value"] == 84
