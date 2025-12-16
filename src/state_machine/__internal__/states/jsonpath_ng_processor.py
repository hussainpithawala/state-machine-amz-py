"""
Adapter for jsonpath-ng library to implement the PathProcessor protocol.
"""
from typing import Any, Optional

from jsonpath_ng import parse
from jsonpath_ng.ext import parse as parse_ext  # For extended features like filters
from ramda import assoc_path

from .base import PathProcessor


def jsonpath_to_ramda_path(expr: str) -> list:
    # Remove leading $.
    if expr.startswith("$."):
        expr = expr[2:]
    # Split on .
    return expr.split(".")


class JsonPathNgProcessor(PathProcessor):
    """
    Path processor implementation using the jsonpath-ng library.
    """

    def apply_input_path(self, input_data: Any, path: Optional[str]) -> Any:
        """
        Apply input path to filter input data.
        """
        if path is None or path == "" or path == "$":
            return input_data
        return self._get_value(input_data, path)

    def apply_result_path(
        self, input_data: Any, result: Any, path: Optional[str]
    ) -> Any:
        """
        Apply result path to combine input and result.
        """
        if path is None or path == "":
            return result
        if path == "$":
            return result
        # For result path, we need to set the value at the specified path
        # jsonpath-ng has an 'update' capability we can use
        return self._set_value(input_data, path, result)

    def apply_output_path(self, output: Any, path: Optional[str]) -> Any:
        """
        Apply output path to filter output data.
        """
        if path is None or path == "" or path == "$":
            return output
        return self._get_value(output, path)

    def _get_value(self, data: Any, path: str) -> Any:
        """
        Get value(s) at the specified JSONPath.

        Returns:
            - A single value if one match is found
            - A list of values if multiple matches are found
            - None if no matches are found
        """
        # try:
        #     jsonpath_expr = parse(path)
        # except Exception:
        jsonpath_expr = parse_ext(path)

        matches = jsonpath_expr.find(data)

        if not matches:
            # Amazon States Language spec: if path doesn't exist,
            # the output is wrapped in a structure based on the path
            # For simplicity, we return the original data here
            # A more complete implementation would create the structure
            return data

        if len(matches) == 1:
            return matches[0].value
        else:
            return [match.value for match in matches]

    def _set_value(self, data: Any, path: str, value: Any) -> Any:
        """
        Set a value at the specified JSONPath.
        jsonpath-ng provides an update method for this.
        """
        try:
            jsonpath_expr = parse(path)
            return jsonpath_expr.update(data, value)
        except:
            try:
                jsonpath_expr_ext = parse_ext(path)
                return jsonpath_expr_ext.update(data, value)
            except:
                # Create a copy to avoid modifying the original
                import copy

                result = copy.deepcopy(data)
                ramda_path = jsonpath_to_ramda_path(path)

                result = assoc_path(ramda_path, value, result)
                return result

    # Additional useful methods from the Go implementation
    def expand_parameters(self, params: dict, input_data: Any) -> dict:
        """
        Expand parameters with JSONPath references.
        Similar to the Go implementation's ExpandParameters method.
        """
        result = {}
        for key, param_value in params.items():
            result[key] = self.expand_value(param_value, input_data)
        return result

    def expand_value(self, value: Any, input_data: Any) -> Any:
        """
        Expand a single value with JSONPath references.
        """
        if isinstance(value, str) and value.startswith("$"):
            return self._get_value(input_data, value)
        elif isinstance(value, dict):
            return {k: self.expand_value(v, input_data) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.expand_value(item, input_data) for item in value]
        else:
            return value
