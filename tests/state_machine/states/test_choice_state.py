"""
Tests for the Choice state implementation.
"""

import json

import pytest

from src.states.base import StateError
from src.states.choice_state import ChoiceRule, ChoiceState


class TestChoiceRule:
    """Tests for ChoiceRule class."""

    def test_choice_rule_creation(self):
        """Test basic ChoiceRule creation."""
        rule = ChoiceRule(
            variable="$.value",
            numeric_equals=10,
            next="Path1",
        )

        assert rule.variable == "$.value"
        assert rule.numeric_equals == 10
        assert rule.next == "Path1"

    def test_choice_rule_to_dict(self):
        """Test ChoiceRule to_dict method."""
        rule = ChoiceRule(
            variable="$.status",
            string_equals="active",
            next="ActivePath",
            comment="Check if active",
        )

        result = rule.to_dict()

        assert result["Variable"] == "$.status"
        assert result["StringEquals"] == "active"
        assert result["Next"] == "ActivePath"
        assert result["Comment"] == "Check if active"

    def test_choice_rule_to_dict_with_and(self):
        """Test ChoiceRule to_dict with AND operator."""
        rule = ChoiceRule(
            variable="$.user",
            and_rules=[
                ChoiceRule(
                    variable="$.age",
                    numeric_greater_than=18,
                    next="",
                ),
                ChoiceRule(
                    variable="$.country",
                    string_equals="US",
                    next="",
                ),
            ],
            next="AdultInUS",
        )

        result = rule.to_dict()

        assert result["Variable"] == "$.user"
        assert result["Next"] == "AdultInUS"
        assert "And" in result
        assert len(result["And"]) == 2


class TestChoiceState:
    """Tests for ChoiceState class."""

    def test_choice_state_creation(self):
        """Test basic ChoiceState creation."""
        state = ChoiceState(
            name="TestChoice",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="Path1",
                )
            ],
            default="DefaultPath",
        )

        assert state.name == "TestChoice"
        assert state.type == "Choice"
        assert len(state.choices) == 1
        assert state.default == "DefaultPath"
        assert state.get_next() is None
        assert not state.is_end()

    def test_choice_state_validation_valid(self):
        """Test ChoiceState validation with valid configuration."""
        state = ChoiceState(
            name="ValidChoice",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="NextState",
                )
            ],
        )

        # Should not raise
        state.validate()

    def test_choice_state_validation_with_default_only(self):
        """Test ChoiceState validation with default only."""
        state = ChoiceState(
            name="ValidChoice",
            default="DefaultState",
        )

        # Should not raise
        state.validate()

    def test_choice_state_validation_no_choices_no_default(self):
        """Test ChoiceState validation without choices or default."""
        state_name = "InvalidChoice"
        with pytest.raises(ValueError, match=f"Choice state '{state_name}' must have either Choices or Default") as exec:
            ChoiceState(name=state_name)

    def test_choice_state_validation_empty_name(self):
        """Test ChoiceState validation with empty name."""
        with pytest.raises(ValueError, match="State name cannot be empty"):
            ChoiceState(
                name="",
                choices=[
                    ChoiceRule(
                        variable="$.value",
                        numeric_equals=10,
                        next="NextState",
                    )
                ],
            )

    def test_choice_state_validation_no_variable(self):
        """Test ChoiceState validation with missing variable."""
        with pytest.raises(ValueError, match="Variable is required"):
            ChoiceState(
                name="InvalidChoice",
                choices=[
                    ChoiceRule(
                        variable="",
                        numeric_equals=10,
                        next="NextState",
                    )
                ],
            )

    def test_choice_state_validation_no_operator(self):
        """Test ChoiceState validation with no comparison operator."""
        with pytest.raises(ValueError, match="must have at least one comparison operator"):
            ChoiceState(
                name="InvalidChoice",
                choices=[
                    ChoiceRule(
                        variable="$.value",
                        next="NextState",
                    )
                ],
            )

    def test_choice_state_validation_no_next(self):
        """Test ChoiceState validation with missing Next."""
        with pytest.raises(ValueError, match="Next is required"):
            ChoiceState(
                name="InvalidChoice",
                choices=[
                    ChoiceRule(
                        variable="$.value",
                        numeric_equals=10,
                        next="",
                    )
                ],
            ).validate()


class TestChoiceStateExecution:
    """Tests for ChoiceState execution."""

    @pytest.mark.asyncio
    async def test_execute_string_equals_match(self):
        """Test execution with StringEquals match."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.status",
                    string_equals="active",
                    next="ActivePath",
                )
            ],
        )

        input_data = {"status": "active"}
        output, next_state = await state.execute(input_data)

        assert next_state == "ActivePath"
        assert output == input_data

    @pytest.mark.asyncio
    async def test_execute_string_equals_no_match(self):
        """Test execution with StringEquals no match."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.status",
                    string_equals="active",
                    next="ActivePath",
                )
            ],
            default="DefaultPath",
        )

        input_data = {"status": "inactive"}
        output, next_state = await state.execute(input_data)

        assert next_state == "DefaultPath"
        assert output == input_data

    @pytest.mark.asyncio
    async def test_execute_string_less_than(self):
        """Test execution with StringLessThan."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.name",
                    string_less_than="M",
                    next="BeforeM",
                )
            ],
        )

        input_data = {"name": "Alice"}
        output, next_state = await state.execute(input_data)

        assert next_state == "BeforeM"

    @pytest.mark.asyncio
    async def test_execute_string_greater_than(self):
        """Test execution with StringGreaterThan."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.name",
                    string_greater_than="M",
                    next="AfterM",
                )
            ],
        )

        input_data = {"name": "Zoe"}
        output, next_state = await state.execute(input_data)

        assert next_state == "AfterM"

    @pytest.mark.asyncio
    async def test_execute_numeric_equals_int(self):
        """Test execution with NumericEquals for integer."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.count",
                    numeric_equals=10,
                    next="Equals10",
                )
            ],
        )

        input_data = {"count": 10}
        output, next_state = await state.execute(input_data)

        assert next_state == "Equals10"

    @pytest.mark.asyncio
    async def test_execute_numeric_equals_float(self):
        """Test execution with NumericEquals for float."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.price",
                    numeric_equals=99.99,
                    next="PriceMatch",
                )
            ],
        )

        input_data = {"price": 99.99}
        output, next_state = await state.execute(input_data)

        assert next_state == "PriceMatch"

    @pytest.mark.asyncio
    async def test_execute_numeric_less_than(self):
        """Test execution with NumericLessThan."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.age",
                    numeric_less_than=18,
                    next="Minor",
                )
            ],
        )

        input_data = {"age": 16}
        output, next_state = await state.execute(input_data)

        assert next_state == "Minor"

    @pytest.mark.asyncio
    async def test_execute_numeric_greater_than(self):
        """Test execution with NumericGreaterThan."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.score",
                    numeric_greater_than=90,
                    next="Excellent",
                )
            ],
        )

        input_data = {"score": 95}
        output, next_state = await state.execute(input_data)

        assert next_state == "Excellent"

    @pytest.mark.asyncio
    async def test_execute_numeric_string_conversion(self):
        """Test execution with string to number conversion."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=42,
                    next="Answer",
                )
            ],
        )

        input_data = {"value": "42"}
        output, next_state = await state.execute(input_data)

        assert next_state == "Answer"

    @pytest.mark.asyncio
    async def test_execute_boolean_equals_true(self):
        """Test execution with BooleanEquals true."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.enabled",
                    boolean_equals=True,
                    next="Enabled",
                )
            ],
        )

        input_data = {"enabled": True}
        output, next_state = await state.execute(input_data)

        assert next_state == "Enabled"

    @pytest.mark.asyncio
    async def test_execute_boolean_equals_false(self):
        """Test execution with BooleanEquals false."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.active",
                    boolean_equals=False,
                    next="Inactive",
                )
            ],
        )

        input_data = {"active": False}
        output, next_state = await state.execute(input_data)

        assert next_state == "Inactive"

    @pytest.mark.asyncio
    async def test_execute_boolean_string_true(self):
        """Test execution with BooleanEquals for string 'true'."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.status",
                    boolean_equals=True,
                    next="TrueStatus",
                )
            ],
        )

        input_data = {"status": "true"}
        output, next_state = await state.execute(input_data)

        assert next_state == "TrueStatus"

    @pytest.mark.asyncio
    async def test_execute_timestamp_equals(self):
        """Test execution with TimestampEquals."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.eventTime",
                    timestamp_equals="2024-01-15T10:30:00Z",
                    next="ExactTime",
                )
            ],
        )

        input_data = {"eventTime": "2024-01-15T10:30:00Z"}
        output, next_state = await state.execute(input_data)

        assert next_state == "ExactTime"

    @pytest.mark.asyncio
    async def test_execute_timestamp_less_than(self):
        """Test execution with TimestampLessThan."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.deadline",
                    timestamp_less_than="2024-12-31T23:59:59Z",
                    next="BeforeDeadline",
                )
            ],
        )

        input_data = {"deadline": "2024-06-15T12:00:00Z"}
        output, next_state = await state.execute(input_data)

        assert next_state == "BeforeDeadline"

    @pytest.mark.asyncio
    async def test_execute_timestamp_unix(self):
        """Test execution with Unix timestamp."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.timestamp",
                    timestamp_equals="2024-01-01T00:00:00Z",
                    next="NewYear",
                )
            ],
        )

        # Unix timestamp for 2024-01-01T00:00:00Z
        input_data = {"timestamp": 1704067200}
        output, next_state = await state.execute(input_data)

        assert next_state == "NewYear"

    @pytest.mark.asyncio
    async def test_execute_and_operator_both_true(self):
        """Test execution with AND operator - both conditions true."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.user",
                    and_rules=[
                        ChoiceRule(
                            variable="$.age",
                            numeric_greater_than=18,
                            next="",
                        ),
                        ChoiceRule(
                            variable="$.country",
                            string_equals="US",
                            next="",
                        ),
                    ],
                    next="AdultInUS",
                )
            ],
        )

        input_data = {"user": {"age": 25, "country": "US"}}
        output, next_state = await state.execute(input_data)

        assert next_state == "AdultInUS"

    @pytest.mark.asyncio
    async def test_execute_and_operator_one_false(self):
        """Test execution with AND operator - one condition false."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.user",
                    and_rules=[
                        ChoiceRule(
                            variable="$.age",
                            numeric_greater_than=18,
                            next="",
                        ),
                        ChoiceRule(
                            variable="$.country",
                            string_equals="US",
                            next="",
                        ),
                    ],
                    next="AdultInUS",
                )
            ],
            default="DefaultPath",
        )

        input_data = {"user": {"age": 16, "country": "US"}}
        output, next_state = await state.execute(input_data)

        assert next_state == "DefaultPath"

    @pytest.mark.asyncio
    async def test_execute_or_operator_first_true(self):
        """Test execution with OR operator - first condition true."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.status",
                    or_rules=[
                        ChoiceRule(
                            variable="$.code",
                            string_equals="200",
                            next="",
                        ),
                        ChoiceRule(
                            variable="$.code",
                            string_equals="201",
                            next="",
                        ),
                    ],
                    next="Success",
                )
            ],
        )

        input_data = {"status": {"code": "200"}}
        output, next_state = await state.execute(input_data)

        assert next_state == "Success"

    @pytest.mark.asyncio
    async def test_execute_or_operator_second_true(self):
        """Test execution with OR operator - second condition true."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.status",
                    or_rules=[
                        ChoiceRule(
                            variable="$.code",
                            string_equals="200",
                            next="",
                        ),
                        ChoiceRule(
                            variable="$.code",
                            string_equals="201",
                            next="",
                        ),
                    ],
                    next="Success",
                )
            ],
        )

        input_data = {"status": {"code": "201"}}
        output, next_state = await state.execute(input_data)

        assert next_state == "Success"

    @pytest.mark.asyncio
    async def test_execute_or_operator_none_true(self):
        """Test execution with OR operator - no conditions true."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.status",
                    or_rules=[
                        ChoiceRule(
                            variable="$.code",
                            string_equals="200",
                            next="",
                        ),
                        ChoiceRule(
                            variable="$.code",
                            string_equals="201",
                            next="",
                        ),
                    ],
                    next="Success",
                )
            ],
            default="DefaultPath",
        )

        input_data = {"status": {"code": "404"}}
        output, next_state = await state.execute(input_data)

        assert next_state == "DefaultPath"

    @pytest.mark.asyncio
    async def test_execute_not_operator_true(self):
        """Test execution with NOT operator - negation results in true."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.user",
                    not_rule=ChoiceRule(
                        variable="$.status",
                        string_equals="inactive",
                        next="",
                    ),
                    next="ActiveUser",
                )
            ],
        )

        input_data = {"user": {"status": "active"}}
        output, next_state = await state.execute(input_data)

        assert next_state == "ActiveUser"

    @pytest.mark.asyncio
    async def test_execute_not_operator_false(self):
        """Test execution with NOT operator - negation results in false."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.user",
                    not_rule=ChoiceRule(
                        variable="$.status",
                        string_equals="inactive",
                        next="",
                    ),
                    next="ActiveUser",
                )
            ],
            default="DefaultPath",
        )

        input_data = {"user": {"status": "inactive"}}
        output, next_state = await state.execute(input_data)

        assert next_state == "DefaultPath"

    @pytest.mark.asyncio
    async def test_execute_multiple_choices_first_match(self):
        """Test execution with multiple choices - first matches."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_less_than=0,
                    next="Negative",
                ),
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=0,
                    next="Zero",
                ),
                ChoiceRule(
                    variable="$.value",
                    numeric_greater_than=0,
                    next="Positive",
                ),
            ],
        )

        input_data = {"value": -5}
        output, next_state = await state.execute(input_data)

        assert next_state == "Negative"

    @pytest.mark.asyncio
    async def test_execute_multiple_choices_second_match(self):
        """Test execution with multiple choices - second matches."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_less_than=0,
                    next="Negative",
                ),
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=0,
                    next="Zero",
                ),
                ChoiceRule(
                    variable="$.value",
                    numeric_greater_than=0,
                    next="Positive",
                ),
            ],
        )

        input_data = {"value": 0}
        output, next_state = await state.execute(input_data)

        assert next_state == "Zero"

    @pytest.mark.asyncio
    async def test_execute_with_paths(self):
        """Test execution with input, result, and output paths."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="Path1",
                )
            ],
            input_path="$.data",
            result_path="$.result",
            output_path="$.output",
        )

        input_data = {"data": {"value": 10}, "other": "data"}
        output, next_state = await state.execute(input_data)

        assert next_state == "Path1"
        # Check that paths were applied correctly
        assert "output" in output

    @pytest.mark.asyncio
    async def test_execute_no_match_no_default(self):
        """Test execution with no match and no default."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="Path1",
                )
            ],
        )

        input_data = {"value": 20}

        with pytest.raises(StateError, match="no choice rule matched and no default"):
            await state.execute(input_data)

    @pytest.mark.asyncio
    async def test_execute_missing_variable(self):
        """Test execution with missing variable."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.missing",
                    string_equals="test",
                    next="Match",
                )
            ],
            default="DefaultPath",
        )

        input_data = {"value": "test"}
        output, next_state = await state.execute(input_data)

        assert next_state == "DefaultPath"

    @pytest.mark.asyncio
    async def test_execute_deeply_nested_variable(self):
        """Test execution with deeply nested variable."""
        state = ChoiceState(
            name="ChoiceState",
            choices=[
                ChoiceRule(
                    variable="$.user.profile.settings.notifications",
                    boolean_equals=True,
                    next="NotificationsOn",
                )
            ],
        )

        input_data = {
            "user": {
                "profile": {
                    "settings": {
                        "notifications": True
                    }
                }
            }
        }
        output, next_state = await state.execute(input_data)

        assert next_state == "NotificationsOn"


class TestChoiceStateSerialization:
    """Tests for ChoiceState serialization."""

    def test_to_dict_simple(self):
        """Test to_dict with simple choice state."""
        state = ChoiceState(
            name="SimpleChoice",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="NextState",
                )
            ],
        )

        result = state.to_dict()

        assert result["Type"] == "Choice"
        assert "Choices" in result
        assert len(result["Choices"]) == 1
        assert result["Choices"][0]["Variable"] == "$.value"
        assert result["Choices"][0]["NumericEquals"] == 10
        assert result["Choices"][0]["Next"] == "NextState"

    def test_to_dict_with_default(self):
        """Test to_dict with default."""
        state = ChoiceState(
            name="ChoiceWithDefault",
            choices=[
                ChoiceRule(
                    variable="$.status",
                    string_equals="active",
                    next="ActivePath",
                )
            ],
            default="DefaultPath",
        )

        result = state.to_dict()

        assert result["Type"] == "Choice"
        assert result["Default"] == "DefaultPath"

    def test_to_dict_with_all_fields(self):
        """Test to_dict with all optional fields."""
        state = ChoiceState(
            name="CompleteChoice",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="Path1",
                    comment="Value equals 10",
                )
            ],
            default="DefaultPath",
            input_path="$.input",
            result_path="$.result",
            output_path="$.output",
            comment="Choice state example",
        )

        result = state.to_dict()

        assert result["Type"] == "Choice"
        assert result["Default"] == "DefaultPath"
        assert result["InputPath"] == "$.input"
        assert result["ResultPath"] == "$.result"
        assert result["OutputPath"] == "$.output"
        assert result["Comment"] == "Choice state example"

    def test_to_json(self):
        """Test to_json method."""
        state = ChoiceState(
            name="TestChoice",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="NextState",
                )
            ],
        )

        json_str = state.to_json()
        result = json.loads(json_str)

        assert result["Type"] == "Choice"
        assert len(result["Choices"]) == 1


class TestChoiceStateHelpers:
    """Tests for ChoiceState helper methods."""

    def test_get_next_states(self):
        """Test get_next_states method."""
        state = ChoiceState(
            name="TestChoice",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_less_than=10,
                    next="LessThan10",
                ),
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="Equals10",
                ),
                ChoiceRule(
                    variable="$.value",
                    numeric_greater_than=10,
                    next="GreaterThan10",
                ),
            ],
            default="DefaultPath",
        )

        next_states = state.get_next_states()

        assert len(next_states) == 4
        assert "LessThan10" in next_states
        assert "Equals10" in next_states
        assert "GreaterThan10" in next_states
        assert "DefaultPath" in next_states

    def test_get_next_states_no_default(self):
        """Test get_next_states without default."""
        state = ChoiceState(
            name="TestChoice",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="Path1",
                )
            ],
        )

        next_states = state.get_next_states()

        assert len(next_states) == 1
        assert "Path1" in next_states

    def test_string_representation(self):
        """Test string representation."""
        state = ChoiceState(
            name="TestChoice",
            choices=[
                ChoiceRule(
                    variable="$.value",
                    numeric_equals=10,
                    next="NextState",
                )
            ],
        )

        assert "ChoiceState" in str(state)
        assert "TestChoice" in str(state)
