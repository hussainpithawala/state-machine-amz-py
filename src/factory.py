"""
Factory for creating state objects from definitions.

Creates appropriate state objects based on type.
"""
import typing
from typing import Any, Dict

from src.states import BaseState


class StateFactory:
    """
    Factory for creating state objects from dictionaries.

    Creates the appropriate state class based on the Type field.
    """

    def __init__(self):
        """Initialize state factory."""
        # State creators will be registered here
        self._creators: Dict[str, Any] = {}
        self._register_default_creators()

    def _register_default_creators(self) -> None:
        """Register default state creators."""
        # Import state classes
        self._creators = {
            "Pass": self._create_pass_state,
            "Fail": self._create_fail_state,
            "Succeed": self._create_succeed_state,
            "Wait": self._create_wait_state,
            "Task": self._create_task_state,
            "Parallel": self._create_parallel_state,
            "Choice": self._create_choice_state,
        }

    def create_state(self, name: str, state_data: Dict[str, Any]) -> Any:
        """
        Create a state from dictionary data.

        Args:
            name: State name
            state_data: Dictionary with state configuration

        Returns:
            State object

        Raises:
            ValueError: If state type is unknown or creation fails
        """
        if "Type" not in state_data:
            raise ValueError(f"State '{name}' missing Type field")

        state_type = state_data["Type"]

        if state_type not in self._creators:
            raise ValueError(f"Unknown state type: {state_type}")

        creator = self._creators[state_type]
        return creator(name, state_data)

    def _create_pass_state(self, name: str, data: Dict[str, Any]) -> Any:
        """Create a Pass state."""
        from src.states.pass_state import PassState

        return PassState(
            name=name,
            next_state=data.get("Next"),
            end=data.get("End", False),
            input_path=data.get("InputPath"),
            result_path=data.get("ResultPath"),
            output_path=data.get("OutputPath"),
            comment=data.get("Comment"),
            result=data.get("Result"),
            parameters=data.get("Parameters"),
        )

    def _create_fail_state(self, name: str, data: Dict[str, Any]) -> Any:
        """Create a Fail state."""
        from src.states.fail_state import FailState

        return FailState(
            name=name,
            error=data.get("Error", "States.Fail"),
            cause=data.get("Cause", "Fail state reached"),
            comment=data.get("Comment"),
        )

    def _create_succeed_state(self, name: str, data: Dict[str, Any]) -> Any:
        """Create a Succeed state."""
        from src.states.succeed import SucceedState

        return SucceedState(
            name=name,
            input_path=data.get("InputPath"),
            output_path=data.get("OutputPath"),
            comment=data.get("Comment"),
        )

    def _create_wait_state(self, name: str, data: Dict[str, Any]) -> Any:
        """Create a Wait state."""
        from src.states.wait_state import WaitState

        return WaitState(
            name=name,
            next_state=data.get("Next"),
            end=data.get("End", False),
            input_path=data.get("InputPath"),
            result_path=data.get("ResultPath"),
            output_path=data.get("OutputPath"),
            comment=data.get("Comment"),
            seconds=data.get("Seconds"),
            timestamp=data.get("Timestamp"),
            seconds_path=data.get("SecondsPath"),
            timestamp_path=data.get("TimestampPath"),
        )

    def _create_task_state(self, name: str, data: Dict[str, Any]) -> Any:
        """Create a Task state."""
        from src.states.task_state import CatchRule, RetryRule, TaskState

        # Parse retry policies
        retry = []
        for retry_data in data.get("Retry", []):
            retry.append(
                RetryRule(
                    error_equals=retry_data.get("ErrorEquals", []),
                    interval_seconds=retry_data.get("IntervalSeconds", 1),
                    max_attempts=retry_data.get("MaxAttempts"),
                    backoff_rate=retry_data.get("BackoffRate", 2.0),
                    max_delay_seconds=retry_data.get("MaxDelaySeconds"),
                    jitter_strategy=retry_data.get("JitterStrategy"),
                )
            )

        # Parse catch policies
        catch = []
        for catch_data in data.get("Catch", []):
            catch.append(
                CatchRule(
                    error_equals=catch_data.get("ErrorEquals", []),
                    next_state=catch_data.get("Next", ""),
                    result_path=catch_data.get("ResultPath"),
                )
            )

        return TaskState(
            name=name,
            next_state=data.get("Next"),
            end=data.get("End", False),
            input_path=data.get("InputPath"),
            result_path=data.get("ResultPath"),
            output_path=data.get("OutputPath"),
            comment=data.get("Comment"),
            resource=data.get("Resource", ""),
            parameters=data.get("Parameters"),
            timeout_seconds=data.get("TimeoutSeconds"),
            heartbeat_seconds=data.get("HeartbeatSeconds"),
            retry=retry,
            catch=catch,
            result_selector=data.get("ResultSelector"),
        )

    def _create_parallel_state(self, name: str, data: Dict[str, Any]) -> Any:
        """Create a Parallel state."""
        from src.states.parallel_state import Branch, ParallelState

        # Parse branches
        branches = []
        for branch_data in data.get("Branches", []):
            # Parse states in branch
            branch_states = {}
            for state_name, state_data in branch_data.get("States", {}).items():
                branch_states[state_name] = self.create_state(state_name, state_data)

            branches.append(
                Branch(
                    start_at=branch_data.get("StartAt", ""),
                    states=branch_states,
                    comment=branch_data.get("Comment"),
                )
            )

        return ParallelState(
            next_state=data.get("Next"),
            end=data.get("End", False),
            input_path=data.get("InputPath"),
            result_path=data.get("ResultPath"),
            output_path=data.get("OutputPath"),
            comment=data.get("Comment"),
            branches=branches,
            result_selector=data.get("ResultSelector"),
        )

    def _create_choice_state(self, name: str, data: Dict[str, Any]) -> Any:
        """Create a Choice state."""
        from src.states.choice_state import ChoiceRule, ChoiceState

        def parse_rule(rule_data: Dict[str, Any]) -> ChoiceRule:
            rule = ChoiceRule(
                variable=rule_data.get("Variable", ""),
                next=rule_data.get("Next", ""),
                string_equals=rule_data.get("StringEquals"),
                string_less_than=rule_data.get("StringLessThan"),
                string_greater_than=rule_data.get("StringGreaterThan"),
                string_less_than_equals=rule_data.get("StringLessThanEquals"),
                string_greater_than_equals=rule_data.get("StringGreaterThanEquals"),
                numeric_equals=rule_data.get("NumericEquals"),
                numeric_less_than=rule_data.get("NumericLessThan"),
                numeric_greater_than=rule_data.get("NumericGreaterThan"),
                numeric_less_than_equals=rule_data.get("NumericLessThanEquals"),
                numeric_greater_than_equals=rule_data.get("NumericGreaterThanEquals"),
                boolean_equals=rule_data.get("BooleanEquals"),
                timestamp_equals=rule_data.get("TimestampEquals"),
                timestamp_less_than=rule_data.get("TimestampLessThan"),
                timestamp_greater_than=rule_data.get("TimestampGreaterThan"),
                timestamp_less_than_equals=rule_data.get("TimestampLessThanEquals"),
                timestamp_greater_than_equals=rule_data.get("TimestampGreaterThanEquals"),
                comment=rule_data.get("Comment"),
            )
            if "And" in rule_data:
                rule.and_rules = [parse_rule(r) for r in rule_data["And"]]
            if "Or" in rule_data:
                rule.or_rules = [parse_rule(r) for r in rule_data["Or"]]
            if "Not" in rule_data:
                rule.not_rule = parse_rule(rule_data["Not"])
            return rule

        choices = [parse_rule(choice_data) for choice_data in data.get("Choices", [])]

        return ChoiceState(
            name=name,
            choices=choices,
            default=data.get("Default"),
            input_path=data.get("InputPath"),
            result_path=data.get("ResultPath"),
            output_path=data.get("OutputPath"),
            comment=data.get("Comment"),
        )

    def register_creator(self, state_type: str, creator: typing.Callable[[str, dict], BaseState]) -> None:
        """
        Register a custom state creator.

        Args:
            state_type: State type name
            creator: Creator function that takes (name, data) and returns state
        """
        self._creators[state_type] = creator
