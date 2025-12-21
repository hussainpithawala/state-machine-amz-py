"""
JSON Path processor for Amazon States Language.

Based on the Go implementation with simplified but correct JSONPath handling.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from .base import PathProcessor


class JSONPathProcessor(PathProcessor):
    """
    JSON Path processor implementation based on Go version.

    Handles JSON path operations as specified in the
    Amazon States Language specification.
    """

    def __init__(self) -> None:
        """Initialize the JSON path processor."""
        pass

    def to_json(self, value: Any) -> Optional[str]:
        """
        Convert value to JSON string.

        Args:
            value: Value to convert

        Returns:
            Tuple of (json_string, error_message)
        """
        try:
            return json.dumps(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to convert value to JSON: {str(e)}", e)

    def from_json(self, json_str: str) -> Tuple[Any, Optional[str]]:
        """
        Parse JSON string to value.

        Args:
            json_str: JSON string to parse

        Returns:
            Tuple of (value, error_message)
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {str(e)}", e)

    def split_path(self, path: str) -> List[str]:
        """
        Split a JSONPath into parts.

        Args:
            path: JSON path string

        Returns:
            List of path parts
        """
        parts = []
        current: List[str] = []
        in_brackets = False

        for ch in path:
            if ch == "." and not in_brackets:
                if current:
                    parts.append("".join(current))
                    current = []
            elif ch == "[" and not in_brackets:
                if current:
                    parts.append("".join(current))
                    current = []
                in_brackets = True
                current.append(ch)
            elif ch == "]" and in_brackets:
                current.append(ch)
                parts.append("".join(current))
                current = []
                in_brackets = False
            else:
                current.append(ch)

        if current:
            parts.append("".join(current))

        return parts

    def apply_input_path(self, input_data: Any, path: Optional[str]) -> Any:
        """
        Apply input path to filter input data.

        Args:
            input_data: Original input data
            path: JSON path expression (None means pass through)

        Returns:
            Filtered input data
        """
        if path is None or path == "" or path == "$":
            return input_data
        return self.get_value(input_data, path)

    def apply_result_path(self, input_data: Any, result: Any, path: Optional[str]) -> Any:
        """
        Apply result path to combine input and result.

        Args:
            input_data: Original input data
            result: Result from state execution
            path: JSON path expression (None means replace)

        Returns:
            Combined data according to result path
        """
        if path is None or path == "":
            return result

        if path == "$":
            return result

        return self.set_value(input_data, path, result)

    def apply_output_path(self, output: Any, path: Optional[str]) -> Any:
        """
        Apply output path to filter output data.

        Args:
            output: Original output data
            path: JSON path expression (None means pass through)

        Returns:
            Filtered output data
        """
        if path is None or path == "" or path == "$":
            return output

        try:
            return self.get_value(output, path)
        except ValueError:
            # If any error occurs, wrap the output
            return self.wrap_value(path, output)

    def get_value(self, data: Any, path: str) -> Tuple[Any, Optional[str]]:
        """
        Get a value at a JSONPath.

        Args:
            data: Input data
            path: JSON path string

        Returns:
            Tuple of (value, error_message)
        """
        if path == "$":
            return data

        if not path.startswith("$"):
            raise ValueError("path must start with '$'")

        # Remove $ and optional leading .
        path = path[1:]  # Remove "$"
        if path.startswith("."):
            path = path[1:]  # Remove leading "."

        parts = self.split_path(path)
        current = data

        for part in parts:
            if part == "":
                continue
            current = self._handle_part(current, part)

        return current

    def _handle_part(self, current: Any, part: str) -> Any:
        """Handle a single part of a JSONPath."""
        # Handle array index
        if part.startswith("[") and part.endswith("]"):
            return self._handle_array_index(current, part)

        # Handle object field
        return self._handle_object_field(current, part)

    def _handle_array_index(self, current: Any, part: str) -> Any:
        """Handle array index part."""
        try:
            index_str = part[1:-1]
            index = int(index_str)

            if not isinstance(current, list):
                # Check at the root level if it's an array at '$'
                if isinstance(current, dict):
                    sub_current = current.get("$")
                    if isinstance(sub_current, list):
                        current = sub_current
                    else:
                        raise ValueError("cannot index non-array")
                else:
                    raise ValueError("cannot index non-array")

            if index < 0 or index >= len(current):
                raise ValueError(f"array index {index} out of bounds")

            return current[index]
        except ValueError as ve:
            if "array index" in str(ve) or "cannot index non-array" in str(ve):
                raise ve
            raise ValueError(f"invalid array index: {part}", ve)

    def _handle_object_field(self, current: Any, part: str) -> Any:
        """Handle object field part."""
        if isinstance(current, dict):
            if part in current:
                return current[part]

            # Check for nested structure with "$" key (from Go implementation)
            if "$" in current:
                nested = current["$"]
                if isinstance(nested, dict) and part in nested:
                    return nested[part]

        # Field not found
        raise ValueError(f"field '{part}' not found")

    def set_value(self, data: Any, path: str, value: Any) -> Any:
        """
        Set a value at a JSONPath.

        Args:
            data: Original data
            path: JSON path string
            value: Value to set

        Returns:
            Tuple of (new_data, error_message)
        """
        if path == "$":
            return value

        result = self.wrap_value(path, value)

        # Merge with original data if it's a map
        if isinstance(data, dict) and isinstance(result, dict):
            return self._merge_maps(data, result)

        return result

    def wrap_value(self, path: str, value: Any) -> Any:
        """
        Wrap a value in a nested structure based on path.

        Args:
            path: JSON path string
            value: Value to wrap

        Returns:
            Tuple of (wrapped_value, error_message)
        """
        if path == "$":
            return value

        if not path.startswith("$"):
            raise ValueError("path must start with '$'")

        # Parse the path
        path = path[1:]  # Remove "$"
        if path.startswith("."):
            path = path[1:]  # Remove leading "."

        parts = self.split_path(path)

        # Start with the value and wrap it
        result = value
        for i in range(len(parts) - 1, -1, -1):
            part = parts[i]
            if part == "":
                continue

            result = self._wrap_part(result, part)

        return result

    def _wrap_part(self, current: Any, part: str) -> Any:
        """Wrap a value with a single path part."""
        if part.startswith("[") and part.endswith("]"):
            # Array index - create array
            try:
                index_str = part[1:-1]
                index = int(index_str)

                # Create array with value at index
                arr = [None] * (index + 1)
                arr[index] = current
                return arr
            except ValueError as ve:
                raise ValueError(f"invalid array index: {part}", ve)
        else:
            # Object field
            return {part: current}

    def expand_parameters(self, params: Dict[str, Any], input_data: Any) -> Dict[str, Any]:
        """
        Expand parameters with JSONPath references.

        Args:
            params: Parameters to expand
            input_data: Input data for path references

        Returns:
            Tuple of (expanded_parameters, error_message)
        """
        result = {}
        for key, value in params.items():
            expanded = self.expand_value(value, input_data)
            result[key] = expanded
        return result

    def expand_value(self, value: Any, input_data: Any) -> Optional[Any]:
        """
        Expand a single value with JSONPath references.

        Args:
            value: Value to expand
            input_data: Input data for path references

        Returns:
            Tuple of (expanded_value, error_message)
        """
        if isinstance(value, str):
            if value.startswith("$"):
                return self.get_value(input_data, value)
            return value

        elif isinstance(value, dict):
            dict_result = {}
            for key, val in value.items():
                expanded = self.expand_value(val, input_data)
                dict_result[key] = expanded
            return dict_result

        elif isinstance(value, list):
            list_result = []
            for val in value:
                expanded = self.expand_value(val, input_data)
                list_result.append(expanded)
            return list_result
        else:
            return value

    def _merge_maps(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deeply merge two maps.

        Args:
            a: First map
            b: Second map

        Returns:
            Merged map
        """
        result = a.copy()

        for key, value in b.items():
            try:
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    # Both are maps, merge recursively
                    result[key] = self._merge_maps(result[key], value)
                elif key in result and isinstance(result[key], list) and isinstance(value, list):
                    # Not both maps or different types, b wins
                    for index, current_val in enumerate(result[key]):
                        if (index <= len(value) - 1) and value[index]:
                            result[key][index] = value[index]
                else:
                    result[key] = value
            except IndexError:
                pass

        return result

    # Export methods for testing (matching Go interface)

    def get(self, data: Any, path: str) -> Tuple[Any, Optional[str]]:
        """Get value at path (public method for testing)."""
        return self.get_value(data, path)

    def set(self, data: Any, path: str, value: Any) -> Tuple[Any, Optional[str]]:
        """Set value at path (public method for testing)."""
        return self.set_value(data, path, value)

    def merge_maps(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two maps (public method for testing)."""
        return self._merge_maps(a, b)

    # Convenience methods that match PathProcessor protocol

    def apply_input_path_safe(self, input_data: Any, path: Optional[str]) -> Any:
        """
        Safe version that raises exceptions on error.

        Args:
            input_data: Original input data
            path: JSON path expression

        Returns:
            Filtered input data

        Raises:
            ValueError: If path is invalid or not found
        """
        if path is None or path == "" or path == "$":
            return input_data

        return self.get_value(input_data, path)

    def apply_result_path_safe(self, input_data: Any, result: Any, path: Optional[str]) -> Any:
        """
        Safe version that raises exceptions on error.

        Args:
            input_data: Original input data
            result: Result from state execution
            path: JSON path expression

        Returns:
            Combined data

        Raises:
            ValueError: If path is invalid
        """
        if path is None or path == "":
            return result

        if path == "$":
            return result

        new_data = self.set_value(input_data, path, result)
        return new_data

    def apply_output_path_safe(self, output: Any, path: Optional[str]) -> Any:
        """
        Safe version that raises exceptions on error.

        Args:
            output: Original output data
            path: JSON path expression

        Returns:
            Filtered output data

        Raises:
            ValueError: If path is invalid
        """
        if path is None or path == "" or path == "$":
            return output
        try:
            return self.get_value(output, path)
        except ValueError:
            return self.wrap_value(path, output)
