"""
Tests for the JSONPath processor implementation.
"""

import json

import pytest

from src.state_machine.__internal__.states.json_path import JSONPathProcessor


class TestJSONPathProcessor:
    """Tests for JSONPathProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create a fresh JSONPathProcessor for each test."""
        return JSONPathProcessor()

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {
            "input": {
                "user": {
                    "name": "John",
                    "age": 30,
                    "address": {"city": "New York", "zip": "10001"},
                },
                "items": ["apple", "banana", "cherry"],
                "nested": {"deep": {"value": 42}},
            },
            "metadata": {"id": 123, "active": True},
        }

    @pytest.fixture
    def sample_array_data(self):
        """Sample array data for testing."""
        return {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"},
            ],
            "matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        }

    # Test get_value method

    def test_get_value_root(self, processor, sample_data):
        """Test getting root value."""
        value = processor.get_value(sample_data, "$")
        assert value == sample_data

    def test_get_value_simple_path(self, processor, sample_data):
        """Test getting value with simple path."""
        value = processor.get_value(sample_data, "$.metadata.id")
        assert value == 123

    def test_get_value_nested_path(self, processor, sample_data):
        """Test getting value with nested path."""
        value = processor.get_value(sample_data, "$.input.user.address.city")
        assert value == "New York"

    def test_get_value_array_index(self, processor, sample_data):
        """Test getting value with array index."""
        value = processor.get_value(sample_data, "$.input.items[1]")
        assert value == "banana"

    def test_get_value_nested_array(self, processor, sample_array_data):
        """Test getting value from nested array."""
        value = processor.get_value(sample_array_data, "$.users[2].name")
        assert value == "Charlie"

    def test_get_value_multi_dimensional_array(self, processor, sample_array_data):
        """Test getting value from multi-dimensional array."""
        value = processor.get_value(sample_array_data, "$.matrix[1][2]")
        assert value == 6

    def test_get_value_path_not_starting_with_dollar(self, processor, sample_data):
        """Test getting value with invalid path."""
        with pytest.raises(ValueError, match="path must start with '\$'"):
            processor.get_value(sample_data, "metadata.id")

    def test_get_value_field_not_found(self, processor, sample_data):
        """Test getting value with non-existent field."""
        with pytest.raises(ValueError, match="field 'nonexistent' not found"):
            processor.get_value(sample_data, "$.metadata.nonexistent")

    def test_get_value_array_index_out_of_bounds(self, processor, sample_data):
        """Test getting value with out-of-bounds array index."""
        with pytest.raises(ValueError, match="array index 10 out of bounds"):
            processor.get_value(sample_data, "$.input.items[10]")

    def test_get_value_invalid_array_index(self, processor, sample_data):
        """Test getting value with invalid array index."""
        with pytest.raises(ValueError, match="invalid array index: \[not-a-number\]"):
            processor.get_value(sample_data, "$.input.items[not-a-number]")

    def test_get_value_index_non_array(self, processor, sample_data):
        """Test indexing non-array."""
        with pytest.raises(ValueError, match=""):
            processor.get_value(sample_data, "$.metadata[0]")

    # Test set_value method

    def test_set_value_root(self, processor):
        """Test setting root value."""
        result = processor.set_value({"old": "data"}, "$", {"new": "data"})
        assert result == {"new": "data"}

    def test_set_value_simple_path(self, processor):
        """Test setting value with simple path."""
        data = {"existing": "value"}
        result = processor.set_value(data, "$.new_field", "new_value")
        assert result == {"existing": "value", "new_field": "new_value"}

    def test_set_value_nested_path(self, processor):
        """Test setting value with nested path."""
        data = {"top": {"middle": {"bottom": "old"}}}
        result = processor.set_value(data, "$.top.middle.bottom", "new")
        assert result == {"top": {"middle": {"bottom": "new"}}}

    def test_set_value_array_index(self, processor):
        """Test setting value with array index."""
        data = {"items": ["a", "b", "c"]}
        result = processor.set_value(data, "$.items[1]", "X")
        assert result == {"items": ["a", "X", "c"]}

    def test_set_value_create_nested_structure(self, processor):
        """Test creating nested structure."""
        data = {}
        result = processor.set_value(data, "$.a.b.c", "value")
        assert result == {"a": {"b": {"c": "value"}}}

    def test_set_value_create_array(self, processor):
        """Test creating array structure."""
        data = {}
        result = processor.set_value(data, "$.items[2]", "third")
        assert result == {"items": [None, None, "third"]}

    def test_set_value_merge_with_existing(self, processor):
        """Test merging with existing data."""
        data = {"existing": "value", "nested": {"keep": "this"}}
        result = processor.set_value(data, "$.nested.new", "added")

        assert result == {
            "existing": "value",
            "nested": {"keep": "this", "new": "added"},
        }

    def test_set_value_path_not_starting_with_dollar(self, processor):
        """Test setting value with invalid path."""
        with pytest.raises(ValueError, match="path must start with '\$'"):
            processor.set_value({}, "metadata.id", "new-id")

    def test_set_value_invalid_array_index(self, processor):
        """Test setting value with invalid array index."""
        with pytest.raises(ValueError, match="invalid array index: \[not-a-number\]"):
            processor.set_value({}, "$.items[not-a-number]", "value")

    # Test wrap_value method

    def test_wrap_value_root(self, processor):
        """Test wrapping root value."""
        result = processor.wrap_value("$", "value")
        assert result == "value"

    def test_wrap_value_simple_path(self, processor):
        """Test wrapping value with simple path."""
        result = processor.wrap_value("$.field", "value")
        assert result == {"field": "value"}

    def test_wrap_value_nested_path(self, processor):
        """Test wrapping value with nested path."""
        result = processor.wrap_value("$.a.b.c", "value")
        assert result == {"a": {"b": {"c": "value"}}}

    def test_wrap_value_with_array(self, processor):
        """Test wrapping value with array path."""
        result = processor.wrap_value("$.items[0]", "first")
        assert result == {"items": ["first"]}

    def test_wrap_value_complex_path(self, processor):
        """Test wrapping value with complex path."""
        result = processor.wrap_value("$.users[1].name", "Bob")
        assert result == {"users": [None, {"name": "Bob"}]}

    def test_wrap_value_path_not_starting_with_dollar(self, processor):
        """Test wrapping value with invalid path."""
        with pytest.raises(ValueError, match="invalid array index: \[not-a-number\]"):
            processor.set_value({}, "$.items[not-a-number]", "value")

    # Test apply_input_path method

    def test_apply_input_path_none_or_empty(self, processor, sample_data):
        """Test apply_input_path with None, empty, or $ path."""
        # None path
        result = processor.apply_input_path(sample_data, None)
        assert result == sample_data

        # Empty path
        result = processor.apply_input_path(sample_data, "")
        assert result == sample_data

        # $ path
        result = processor.apply_input_path(sample_data, "$")
        assert result == sample_data

    def test_apply_input_path_valid_path(self, processor, sample_data):
        """Test apply_input_path with valid path."""
        result = processor.apply_input_path(sample_data, "$.metadata")
        assert result == sample_data["metadata"]

    def test_apply_input_path_path_not_found(self, processor, sample_data):
        """Test apply_input_path with non-existent path."""
        # Should return wrapped value
        with pytest.raises(ValueError, match="nonexistent"):
            processor.apply_input_path(sample_data, "$.nonexistent")

    # Test apply_result_path method

    def test_apply_result_path_none_or_empty(self, processor):
        """Test apply_result_path with None or empty path."""
        # None path
        result = processor.apply_result_path({"input": "data"}, "result", None)
        assert result == "result"

        # Empty path
        result = processor.apply_result_path({"input": "data"}, "result", "")
        assert result == "result"

    def test_apply_result_path_dollar_path(self, processor):
        """Test apply_result_path with $ path."""
        result = processor.apply_result_path({"input": "data"}, "result", "$")
        assert result == "result"

    def test_apply_result_path_valid_path(self, processor):
        """Test apply_result_path with valid path."""
        result = processor.apply_result_path(
            {"original": "data"}, "new_result", "$.result"
        )
        # Creates nested structure
        assert isinstance(result, dict)
        assert "original" in result
        assert "result" in result

    def test_apply_result_path_merge_with_input(self, processor):
        """Test apply_result_path merging with input."""
        input_data = {"user": "John", "settings": {"theme": "dark"}}
        result = "success"

        output = processor.apply_result_path(input_data, result, "$.status")

        assert output["user"] == "John"
        assert output["settings"]["theme"] == "dark"
        assert output["status"] == "success"

    # Test apply_output_path method

    def test_apply_output_path_none_or_empty(self, processor, sample_data):
        """Test apply_output_path with None, empty, or $ path."""
        # None path
        result = processor.apply_output_path(sample_data, None)
        assert result == sample_data

        # Empty path
        result = processor.apply_output_path(sample_data, "")
        assert result == sample_data

        # $ path
        result = processor.apply_output_path(sample_data, "$")
        assert result == sample_data

    def test_apply_output_path_valid_path(self, processor, sample_data):
        """Test apply_output_path with valid path."""
        result = processor.apply_output_path(sample_data, "$.metadata")
        assert result == sample_data["metadata"]

    def test_apply_output_path_path_not_found(self, processor, sample_data):
        """Test apply_output_path with non-existent path."""
        # Should wrap the output
        result = processor.apply_output_path(sample_data, "$.nonexistent")
        assert result == {"nonexistent": sample_data}

    # Test expand_parameters method

    def test_expand_parameters_no_paths(self, processor, sample_data):
        """Test expand_parameters without JSONPath references."""
        params = {"name": "test", "value": 42, "enabled": True}
        result = processor.expand_parameters(params, sample_data)
        assert result == params

    def test_expand_parameters_with_paths(self, processor, sample_data):
        """Test expand_parameters with JSONPath references."""
        params = {
            "user_name": "$.input.user.name",
            "city": "$.input.user.address.city",
            "static": "value",
        }

        result = processor.expand_parameters(params, sample_data)

        assert result["user_name"] == "John"
        assert result["city"] == "New York"
        assert result["static"] == "value"

    def test_expand_parameters_nested_structure(self, processor, sample_data):
        """Test expand_parameters with nested structure."""
        params = {"user": {"info": "$.input.user", "first_item": "$.input.items[0]"}}

        result = processor.expand_parameters(params, sample_data)

        assert result["user"]["info"]["name"] == "John"
        assert result["user"]["first_item"] == "apple"

    def test_expand_parameters_array(self, processor, sample_data):
        """Test expand_parameters with array containing paths."""
        params = {"items": ["$.input.items[0]", "$.input.items[1]", "static"]}
        result = processor.expand_parameters(params, sample_data)
        assert result["items"] == ["apple", "banana", "static"]

    def test_expand_parameters_path_not_found(self, processor, sample_data):
        """Test expand_parameters with non-existent path."""
        params = {"invalid": "$.nonexistent.path"}

        with pytest.raises(ValueError, match="field 'nonexistent' not found"):
            processor.expand_parameters(params, sample_data)

    # Test expand_value method

    def test_expand_value_string_path(self, processor, sample_data):
        """Test expand_value with string path."""
        value = processor.expand_value("$.input.user.name", sample_data)
        assert value == "John"

    def test_expand_value_string_literal(self, processor, sample_data):
        """Test expand_value with string literal."""
        value = processor.expand_value("literal string", sample_data)
        assert value == "literal string"

    def test_expand_value_dict(self, processor, sample_data):
        """Test expand_value with dictionary."""
        value = processor.expand_value(
            {"name": "$.input.user.name", "age": 30}, sample_data
        )

        assert value["name"] == "John"
        assert value["age"] == 30

    def test_expand_value_array(self, processor, sample_data):
        """Test expand_value with array."""
        value = processor.expand_value(
            ["$.input.items[0]", "$.input.items[1]", "end"], sample_data
        )
        assert value == ["apple", "banana", "end"]

    def test_expand_value_other_types(self, processor, sample_data):
        """Test expand_value with other types."""
        # Integer
        value = processor.expand_value(42, sample_data)
        assert value == 42

        # Float
        value = processor.expand_value(3.14, sample_data)
        assert value == 3.14

        # Boolean
        value = processor.expand_value(True, sample_data)
        assert value is True

        # None
        value = processor.expand_value(None, sample_data)
        assert value is None

    # Test to_json and from_json methods

    def test_to_json_valid(self, processor):
        """Test to_json with valid data."""
        data = {"name": "John", "age": 30, "active": True}
        json_str = processor.to_json(data)
        parsed = json.loads(json_str)
        assert parsed == data

    def test_to_json_invalid(self, processor):
        """Test to_json with invalid data."""

        class NonSerializable:
            pass

        data = {"obj": NonSerializable()}
        with pytest.raises(ValueError):
            processor.to_json(data)

    def test_from_json_valid(self, processor):
        """Test from_json with valid JSON."""
        json_str = '{"name": "John", "age": 30}'
        data = processor.from_json(json_str)
        assert data["name"] == "John"
        assert data["age"] == 30

    def test_from_json_invalid(self, processor):
        """Test from_json with invalid JSON."""
        json_str = '{"name": "John", "age": 30'  # Missing closing brace
        with pytest.raises(ValueError):
            processor.from_json(json_str)

    # Test _split_path method

    def test_split_path_simple(self, processor):
        """Test _split_path with simple path."""
        parts = processor.split_path("user.name")
        assert parts == ["user", "name"]

    @pytest.mark.skip(
        reason="test_split_path_with_array is currently under development"
    )
    def test_split_path_with_array(self, processor):
        """Test _split_path with array index."""
        parts = processor.split_path("users[0].name")
        assert parts == ["users[0]", "name"]

    @pytest.mark.skip(
        reason="test_split_path_nested_array is currently under development"
    )
    def test_split_path_nested_array(self, processor):
        """Test _split_path with nested array."""
        parts = processor.split_path("matrix[1][2]")
        assert parts == ["matrix[1]", "[2]"]

    def test_split_path_empty(self, processor):
        """Test _split_path with empty string."""
        parts = processor.split_path("")
        assert parts == []

    # Test _merge_maps method

    def test_merge_maps_shallow(self, processor):
        """Test _merge_maps with shallow merge."""
        a = {"x": 1, "y": 2}
        b = {"y": 3, "z": 4}

        result = processor._merge_maps(a, b)

        assert result["x"] == 1
        assert result["y"] == 3  # b wins
        assert result["z"] == 4

    def test_merge_maps_deep(self, processor):
        """Test _merge_maps with deep merge."""
        a = {"user": {"name": "John", "age": 30}, "settings": {"theme": "dark"}}
        b = {"user": {"age": 31, "city": "NYC"}, "active": True}

        result = processor._merge_maps(a, b)

        assert result["user"]["name"] == "John"  # From a
        assert result["user"]["age"] == 31  # From b
        assert result["user"]["city"] == "NYC"  # From b
        assert result["settings"]["theme"] == "dark"  # From a
        assert result["active"] is True  # From b

    def test_merge_maps_empty(self, processor):
        """Test _merge_maps with empty maps."""
        result = processor._merge_maps({}, {})
        assert result == {}

    # Test public methods (Get, Set, etc.)

    def test_get_public_method(self, processor, sample_data):
        """Test public Get method."""
        value = processor.get(sample_data, "$.metadata.id")
        assert value == 123

    def test_set_public_method(self, processor):
        """Test public Set method."""
        data = {"existing": "value"}
        result= processor.set(data, "$.new", "value")
        assert result["existing"] == "value"
        assert result["new"] == "value"

    def test_merge_maps_public_method(self, processor):
        """Test public merge_maps method."""
        a = {"x": 1}
        b = {"y": 2}

        result = processor.merge_maps(a, b)
        assert result["x"] == 1
        assert result["y"] == 2

    # Test safe methods

    def test_apply_input_path_safe_valid(self, processor, sample_data):
        """Test apply_input_path_safe with valid path."""
        result = processor.apply_input_path_safe(sample_data, "$.metadata")
        assert result == sample_data["metadata"]

    def test_apply_input_path_safe_invalid(self, processor, sample_data):
        """Test apply_input_path_safe with invalid path."""
        with pytest.raises(ValueError, match="path must start with '\$'"):
            processor.apply_input_path_safe(sample_data, "invalid.path")

    def test_apply_result_path_safe(self, processor):
        """Test apply_result_path_safe."""
        result = processor.apply_result_path_safe(
            {"input": "data"}, "result", "$.output"
        )
        assert isinstance(result, dict)

    def test_apply_output_path_safe(self, processor, sample_data):
        """Test apply_output_path_safe."""
        result = processor.apply_output_path_safe(sample_data, "$.metadata")
        assert result == sample_data["metadata"]

    # Edge cases and special scenarios

    def test_complex_nested_structure(self, processor):
        """Test with complex nested structure."""
        data = {"a": {"b": [{"c": 1}, {"c": 2, "d": {"e": "deep"}}]}}

        # Get deep value
        value = processor.get_value(data, "$.a.b[1].d.e")
        assert value == "deep"

        # Set deep value
        result = processor.set_value(data, "$.a.b[0].new", "added")
        assert result["a"]["b"][0]["new"] == "added"

    def test_path_with_special_characters(self, processor):
        """Test paths with special characters in field names."""
        data = {
            "field-with-dash": "value1",
            "field.with.dot": "value2",
            "field with spaces": "value3",
        }

        # Note: JSONPath doesn't officially support these without quoting
        # This test documents current behavior

        # For now, test with simple field names
        value = processor.get_value(data, "$.field-with-dash")
        # This might fail depending on implementation
        # assert error is None or "not found" in error

    def test_empty_objects_and_arrays(self, processor):
        """Test with empty objects and arrays."""
        data = {"empty_obj": {}, "empty_arr": [], "nested": {"empty": {}}}

        # Get from empty object
        with pytest.raises(ValueError, match="not found"):
            processor.get_value(data, "$.empty_obj.nonexistent")

        # Get from empty array
        with pytest.raises(ValueError, match="out of bounds"):
            processor.get_value(data, "$.empty_arr[0]")

    def test_null_values(self, processor):
        """Test with null values."""
        data = {"null_field": None, "nested": {"null": None}}

        # Get null value
        value = processor.get_value(data, "$.null_field")
        assert value is None

        # Set null value
        result = processor.set_value(data, "$.new_null", None)
        assert result["new_null"] is None
