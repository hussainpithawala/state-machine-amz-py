"""
Choice state implementation for Amazon States Language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseState, StateError, get_path_processor


@dataclass
class ChoiceRule:
    """Represents a single choice rule for conditional branching."""

    variable: str
    next: str
    # String comparison operators
    string_equals: Optional[str] = None
    string_less_than: Optional[str] = None
    string_greater_than: Optional[str] = None
    string_less_than_equals: Optional[str] = None
    string_greater_than_equals: Optional[str] = None
    # Numeric comparison operators
    numeric_equals: Optional[float] = None
    numeric_less_than: Optional[float] = None
    numeric_greater_than: Optional[float] = None
    numeric_less_than_equals: Optional[float] = None
    numeric_greater_than_equals: Optional[float] = None
    # Boolean comparison operator
    boolean_equals: Optional[bool] = None
    # Timestamp comparison operators
    timestamp_equals: Optional[str] = None
    timestamp_less_than: Optional[str] = None
    timestamp_greater_than: Optional[str] = None
    timestamp_less_than_equals: Optional[str] = None
    timestamp_greater_than_equals: Optional[str] = None
    # Compound operators
    and_rules: List[ChoiceRule] = field(default_factory=list)
    or_rules: List[ChoiceRule] = field(default_factory=list)
    not_rule: Optional[ChoiceRule] = None
    # Optional comment
    comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: Dict[str, Any] = {
            "Variable": self.variable,
            "Next": self.next,
        }

        # Mapping of attribute names to their JSON keys for comparison operators
        comparison_ops = {
            "string_equals": "StringEquals",
            "string_less_than": "StringLessThan",
            "string_greater_than": "StringGreaterThan",
            "string_less_than_equals": "StringLessThanEquals",
            "string_greater_than_equals": "StringGreaterThanEquals",
            "numeric_equals": "NumericEquals",
            "numeric_less_than": "NumericLessThan",
            "numeric_greater_than": "NumericGreaterThan",
            "numeric_less_than_equals": "NumericLessThanEquals",
            "numeric_greater_than_equals": "NumericGreaterThanEquals",
            "boolean_equals": "BooleanEquals",
            "timestamp_equals": "TimestampEquals",
            "timestamp_less_than": "TimestampLessThan",
            "timestamp_greater_than": "TimestampGreaterThan",
            "timestamp_less_than_equals": "TimestampLessThanEquals",
            "timestamp_greater_than_equals": "TimestampGreaterThanEquals",
        }

        for attr, key in comparison_ops.items():
            value = getattr(self, attr)
            if value is not None:
                result[key] = value

        # Add compound operators if present
        if self.and_rules:
            result["And"] = [rule.to_dict() for rule in self.and_rules]
        if self.or_rules:
            result["Or"] = [rule.to_dict() for rule in self.or_rules]
        if self.not_rule is not None:
            result["Not"] = self.not_rule.to_dict()

        if self.comment:
            result["Comment"] = self.comment

        return result


@dataclass
class ChoiceState(BaseState):
    """
    Choice state for conditional branching in state machines.

    Choice states allow branching logic based on input data.
    """

    choices: List[ChoiceRule] = field(default_factory=list)
    default: Optional[str] = None

    def __init__(
        self,
        name: str,
        choices: Optional[List[ChoiceRule]] = None,
        default: Optional[str] = None,
        input_path: Optional[str] = None,
        result_path: Optional[str] = None,
        output_path: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        self.name = name
        self.type = "Choice"
        self.choices = choices or []
        self.default = default
        self.next_state = None  # Choice states don't have Next
        self.end = False  # Choice states don't have End
        self.input_path = input_path
        self.result_path = result_path
        self.output_path = output_path
        self.comment = comment
        super().__post_init__()

    def validate(self, skip_name=False, skip_type: bool = False, skip_next_state: bool = False) -> None:
        """Validate the Choice state configuration."""
        # Validate basic fields
        if not self.name:
            raise ValueError("State name cannot be empty")

        if self.type != "Choice":
            raise ValueError("Choice state must have Type 'Choice'")

        # Choice states cannot have Next
        if self.next_state is not None:
            raise ValueError(f"Choice state '{self.name}' cannot have Next field")

        # Choice states cannot have End
        if self.end:
            raise ValueError(f"Choice state '{self.name}' cannot have End field")

        # Must have at least one choice or a default
        if not self.choices and self.default is None:
            raise ValueError(f"Choice state '{self.name}' must have either Choices or Default")

        # Validate each choice
        for i, choice in enumerate(self.choices):
            self._validate_choice(choice, i, next_required=True)

    def _validate_choice(self, choice: ChoiceRule, index: int, next_required: bool) -> None:
        """Validate a single choice rule."""
        # Count operators
        comparison_count = self._count_comparison_operators(choice)
        compound_count = self._count_compound_operators(choice)

        # For rules with comparison operators, Variable is required
        if comparison_count > 0 and not choice.variable:
            raise ValueError(f"Choice {index}: Variable is required for comparison operators")

        # Must have at least one operator
        if comparison_count == 0 and compound_count == 0:
            raise ValueError(f"Choice {index}: must have at least one comparison operator " f"or compound operator")

        # Validate Next field if required
        if next_required and not choice.next:
            raise ValueError(f"Choice {index}: Next is required")

        # Validate nested compound operators recursively
        for i, and_rule in enumerate(choice.and_rules):
            self._validate_choice(and_rule, i, next_required=False)

        for i, or_rule in enumerate(choice.or_rules):
            self._validate_choice(or_rule, i, next_required=False)

        if choice.not_rule is not None:
            self._validate_choice(choice.not_rule, 0, next_required=False)

    def _count_comparison_operators(self, choice: ChoiceRule) -> int:
        """Count the number of comparison operators in a choice."""
        count = 0
        operators = [
            choice.string_equals,
            choice.string_less_than,
            choice.string_greater_than,
            choice.string_less_than_equals,
            choice.string_greater_than_equals,
            choice.numeric_equals,
            choice.numeric_less_than,
            choice.numeric_greater_than,
            choice.numeric_less_than_equals,
            choice.numeric_greater_than_equals,
            choice.boolean_equals,
            choice.timestamp_equals,
            choice.timestamp_less_than,
            choice.timestamp_greater_than,
            choice.timestamp_less_than_equals,
            choice.timestamp_greater_than_equals,
        ]
        for op in operators:
            if op is not None:
                count += 1
        return count

    def _count_compound_operators(self, choice: ChoiceRule) -> int:
        """Count the number of compound operators in a choice."""
        count = 0
        if choice.and_rules:
            count += 1
        if choice.or_rules:
            count += 1
        if choice.not_rule is not None:
            count += 1
        return count

    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> tuple[Any, Optional[str]]:
        """Execute the Choice state."""
        # Get path processor
        processor = self._path_processor or get_path_processor()

        # Apply input path
        processed_input = processor.apply_input_path(input_data, self.input_path)

        # Evaluate each choice in order
        for choice in self.choices:
            if self._evaluate_choice(choice, processed_input):
                # Apply result path and output path
                processed_result = processor.apply_result_path(processed_input, processed_input, self.result_path)
                final_output = processor.apply_output_path(processed_result, self.output_path)
                return final_output, choice.next

        # No choice matched, use default if specified
        if self.default is not None:
            processed_result = processor.apply_result_path(processed_input, processed_input, self.result_path)
            final_output = processor.apply_output_path(processed_result, self.output_path)
            return final_output, self.default

        # No choice matched and no default - this is an error
        raise StateError(
            "no choice rule matched and no default specified",
            state_name=self.name,
        )

    def _evaluate_choice(self, rule: ChoiceRule, input_data: Any) -> bool:
        """Evaluate a single choice rule."""
        # Determine the context for this rule
        context = input_data
        if rule.variable:
            context = self._get_variable_value(rule.variable, input_data)
            # If the variable doesn't exist, the choice evaluates to false
            if context is None:
                return False

        # Handle compound operators
        if rule.and_rules:
            return self._evaluate_and(rule.and_rules, context)

        if rule.or_rules:
            return self._evaluate_or(rule.or_rules, context)

        if rule.not_rule is not None:
            return not self._evaluate_choice(rule.not_rule, context)

        # Evaluate comparison operators
        return self._evaluate_comparison(rule, context)

    def _evaluate_and(self, rules: List[ChoiceRule], context: Any) -> bool:
        """Evaluate AND conditions."""
        for rule in rules:
            if not self._evaluate_choice(rule, context):
                return False
        return True

    def _evaluate_or(self, rules: List[ChoiceRule], context: Any) -> bool:
        """Evaluate OR conditions."""
        for rule in rules:
            if self._evaluate_choice(rule, context):
                return True
        return False

    def _evaluate_comparison(self, rule: ChoiceRule, variable_value: Any) -> bool:
        """Evaluate comparison operators."""
        # Define comparison configurations: (attribute_name, handler_method, comparison_lambda)
        comparisons: List[Tuple[str, Callable, Optional[Callable]]] = [
            ("string_equals", self._compare_string, lambda a, b: a == b),
            ("string_less_than", self._compare_string, lambda a, b: a < b),
            ("string_greater_than", self._compare_string, lambda a, b: a > b),
            ("string_less_than_equals", self._compare_string, lambda a, b: a <= b),
            ("string_greater_than_equals", self._compare_string, lambda a, b: a >= b),
            ("numeric_equals", self._compare_numeric, lambda a, b: a == b),
            ("numeric_less_than", self._compare_numeric, lambda a, b: a < b),
            ("numeric_greater_than", self._compare_numeric, lambda a, b: a > b),
            ("numeric_less_than_equals", self._compare_numeric, lambda a, b: a <= b),
            ("numeric_greater_than_equals", self._compare_numeric, lambda a, b: a >= b),
            ("boolean_equals", lambda v, e, _: self._compare_boolean(v, e), None),
            ("timestamp_equals", self._compare_timestamp, lambda a, b: a == b),
            ("timestamp_less_than", self._compare_timestamp, lambda a, b: a < b),
            ("timestamp_greater_than", self._compare_timestamp, lambda a, b: a > b),
            ("timestamp_less_than_equals", self._compare_timestamp, lambda a, b: a <= b),
            ("timestamp_greater_than_equals", self._compare_timestamp, lambda a, b: a >= b),
        ]

        for attr, handler, op in comparisons:
            expected = getattr(rule, attr)
            if expected is not None:
                return handler(variable_value, expected, op)

        raise StateError("no comparison operator specified in choice rule")

    def _compare_string(self, variable_value: Any, expected: str, compare_func: Callable) -> bool:
        """Compare string values."""
        if isinstance(variable_value, str):
            str_value = variable_value
        else:
            str_value = str(variable_value)
        return compare_func(str_value, expected)

    def _compare_numeric(self, variable_value: Any, expected: float, compare_func: Callable) -> bool:
        """Compare numeric values."""
        try:
            if isinstance(variable_value, (int, float)):
                float_value = float(variable_value)
            elif isinstance(variable_value, str):
                float_value = float(variable_value)
            else:
                raise ValueError(f"Cannot convert {type(variable_value)} to number")
            return compare_func(float_value, expected)
        except (ValueError, TypeError):
            return False

    def _compare_boolean(self, variable_value: Any, expected: bool) -> bool:
        """Compare boolean values."""
        if isinstance(variable_value, bool):
            return variable_value == expected
        elif isinstance(variable_value, str):
            lower_str = variable_value.lower()
            if lower_str == "true":
                return expected is True
            elif lower_str == "false":
                return expected is False
        return False

    def _compare_timestamp(self, variable_value: Any, expected_str: str, compare_func: Callable) -> bool:
        """Compare timestamp values."""
        try:
            # Parse expected timestamp
            expected_time = self._parse_timestamp(expected_str)

            # Get variable timestamp
            if isinstance(variable_value, datetime):
                variable_time = variable_value
            elif isinstance(variable_value, str):
                variable_time = self._parse_timestamp(variable_value)
            elif isinstance(variable_value, (int, float)):
                # Assume Unix timestamp
                variable_time = datetime.fromtimestamp(variable_value)
            else:
                return False

            return compare_func(variable_time.astimezone(expected_time.tzinfo), expected_time)
        except (ValueError, TypeError):
            return False

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse a timestamp string in various formats."""
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
        ]

        # Try ISO format first
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Try other formats
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Invalid timestamp format: {timestamp_str}")

    def _get_variable_value(self, path: str, input_data: Any) -> Any:
        """Get a value from input at a JSONPath."""
        try:
            processor = self._path_processor or get_path_processor()
            return processor.apply_input_path(input_data, path)
        except Exception:
            # Any error accessing the variable means it doesn't exist
            return None

    def get_next_states(self) -> List[str]:
        """Get all possible next state names."""
        next_states = []

        # Add all choice destinations
        for choice in self.choices:
            next_states.append(choice.next)

        # Add default if present
        if self.default is not None:
            next_states.append(self.default)

        return next_states

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for JSON serialization."""
        result: Dict[str, Any] = {
            "Type": self.type,
            "Choices": [choice.to_dict() for choice in self.choices],
        }

        if self.default is not None:
            result["Default"] = self.default

        if self.input_path is not None:
            result["InputPath"] = self.input_path

        if self.result_path is not None:
            result["ResultPath"] = self.result_path

        if self.output_path is not None:
            result["OutputPath"] = self.output_path

        if self.comment is not None:
            result["Comment"] = self.comment

        return result
