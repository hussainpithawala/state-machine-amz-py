import pytest

from src.factory import StateFactory
from src.states.choice_state import ChoiceState
from src.states.fail_state import FailState
from src.states.parallel_state import ParallelState
from src.states.pass_state import PassState
from src.states.succeed import SucceedState
from src.states.task_state import TaskState
from src.states.wait_state import WaitState


def test_state_factory_init():
    factory = StateFactory()
    assert factory._creators is not None
    assert "Pass" in factory._creators
    assert "Fail" in factory._creators
    assert "Succeed" in factory._creators
    assert "Wait" in factory._creators
    assert "Task" in factory._creators
    assert "Parallel" in factory._creators
    assert "Choice" in factory._creators


def test_create_pass_state():
    factory = StateFactory()
    data = {"Type": "Pass", "Result": {"foo": "bar"}, "Next": "NextState", "Comment": "Test comment"}
    state = factory.create_state("MyPass", data)
    assert isinstance(state, PassState)
    assert state.name == "MyPass"
    assert state.result == {"foo": "bar"}
    assert state.next_state == "NextState"
    assert state.comment == "Test comment"


def test_create_fail_state():
    factory = StateFactory()
    data = {"Type": "Fail", "Error": "CustomError", "Cause": "Something went wrong"}
    state = factory.create_state("MyFail", data)
    assert isinstance(state, FailState)
    assert state.name == "MyFail"
    assert state.error == "CustomError"
    assert state.cause == "Something went wrong"


def test_create_succeed_state():
    factory = StateFactory()
    data = {"Type": "Succeed", "Comment": "I succeeded"}
    state = factory.create_state("MySucceed", data)
    assert isinstance(state, SucceedState)
    assert state.name == "MySucceed"
    assert state.comment == "I succeeded"


def test_create_wait_state():
    factory = StateFactory()
    data = {"Type": "Wait", "Seconds": 10, "Next": "AfterWait"}
    state = factory.create_state("MyWait", data)
    assert isinstance(state, WaitState)
    assert state.name == "MyWait"
    assert state.seconds == 10
    assert state.next_state == "AfterWait"


def test_create_task_state():
    factory = StateFactory()
    data = {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:123456789012:function:HelloWorld",
        "Next": "FinalState",
        "Retry": [{"ErrorEquals": ["States.Timeout"], "IntervalSeconds": 3, "MaxAttempts": 2}],
        "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}],
    }
    state = factory.create_state("MyTask", data)
    assert isinstance(state, TaskState)
    assert state.name == "MyTask"
    assert state.resource == "arn:aws:lambda:us-east-1:123456789012:function:HelloWorld"
    assert len(state.retry) == 1
    assert state.retry[0].error_equals == ["States.Timeout"]
    assert state.retry[0].interval_seconds == 3
    assert len(state.catch) == 1
    assert state.catch[0].error_equals == ["States.ALL"]
    assert state.catch[0].next_state == "ErrorHandler"


def test_create_parallel_state():
    factory = StateFactory()
    data = {
        "Type": "Parallel",
        "Branches": [{"StartAt": "State1", "States": {"State1": {"Type": "Pass", "End": True}}}],
        "Next": "JoinState",
    }
    state = factory.create_state("MyParallel", data)
    assert isinstance(state, ParallelState)
    assert len(state.branches) == 1
    assert state.branches[0].start_at == "State1"
    assert "State1" in state.branches[0].states
    assert isinstance(state.branches[0].states["State1"], PassState)


def test_create_choice_state():
    factory = StateFactory()
    data = {
        "Type": "Choice",
        "Choices": [
            {"Variable": "$.value", "NumericEquals": 1, "Next": "One"},
            {
                "And": [
                    {"Variable": "$.value", "NumericGreaterThan": 1},
                    {"Variable": "$.value", "NumericLessThan": 10},
                ],
                "Next": "Middle",
            },
            {"Not": {"Variable": "$.flag", "BooleanEquals": True}, "Next": "FlagFalse"},
        ],
        "Default": "DefaultState",
    }
    state = factory.create_state("MyChoice", data)
    assert isinstance(state, ChoiceState)
    assert state.name == "MyChoice"
    assert len(state.choices) == 3
    assert state.choices[0].variable == "$.value"
    assert state.choices[0].numeric_equals == 1
    assert state.choices[0].next == "One"
    assert len(state.choices[1].and_rules) == 2
    assert state.choices[2].not_rule is not None
    assert state.choices[2].not_rule.variable == "$.flag"
    assert state.choices[2].not_rule.boolean_equals is True
    assert state.default == "DefaultState"


def test_create_state_missing_type():
    factory = StateFactory()
    with pytest.raises(ValueError, match="missing Type field"):
        factory.create_state("NoType", {})


def test_create_state_unknown_type():
    factory = StateFactory()
    with pytest.raises(ValueError, match="Unknown state type: Unknown"):
        factory.create_state("Unknown", {"Type": "Unknown"})


def test_register_creator():
    factory = StateFactory()

    def custom_creator(name, data):
        return f"Custom {name}"

    factory.register_creator("Custom", custom_creator)
    assert "Custom" in factory._creators

    state = factory.create_state("MyCustom", {"Type": "Custom"})
    assert state == "Custom MyCustom"
