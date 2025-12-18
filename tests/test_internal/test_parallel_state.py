"""
Tests for ParallelState implementation.

Based on parallel_test.go
"""

import asyncio

import pytest

from src.state_machine.__internal__.states.base import StateError
from src.state_machine.__internal__.states.choice_state import ChoiceState
from src.state_machine.__internal__.states.fail_state import FailState
from src.state_machine.__internal__.states.parallel_state import (
    Branch,
    ParallelState,
    create_branch,
)
from src.state_machine.__internal__.states.pass_state import PassState


@pytest.mark.asyncio
async def test_parallel_state_execute_multiple_branches():
    """Test parallel state execution with multiple branches."""
    # Create two simple branches with Pass states
    state = ParallelState(

        next_state="NextState",
        branches=[
            Branch(
                start_at="Pass1",
                states={
                    "Pass1": PassState(name="Pass1", result="branch1-result", end=True)
                },
            ),
            Branch(
                start_at="Pass2",
                states={
                    "Pass2": PassState(name="Pass2", result="branch2-result", end=True)
                },
            ),
        ],
    )

    input_data = {"original": "data"}

    output, next_state = await state.execute(input_data)

    assert output is not None
    assert next_state == "NextState"

    # Verify output is an array of results
    assert isinstance(output, list)
    assert len(output) == 2
    assert output[0] == "branch1-result"
    assert output[1] == "branch2-result"


@pytest.mark.asyncio
async def test_parallel_state_execute_with_input_path():
    """Test parallel state execution with input path."""
    state = ParallelState(

        end=True,
        input_path="$.data",
        branches=[
            Branch(start_at="Pass1", states={"Pass1": PassState(name="Pass1", end=True)}),
            Branch(start_at="Pass2", states={"Pass2": PassState(name="Pass2", end=True)}),
        ],
    )

    input_data = {"data": {"value": "test"}, "other": "ignored"}

    output, _ = await state.execute(input_data)

    assert isinstance(output, list)
    assert len(output) == 2

    # Each branch should receive the extracted input
    assert output[0] == {"value": "test"}
    assert output[1] == {"value": "test"}


@pytest.mark.asyncio
async def test_parallel_state_execute_multi_state_branch():
    """Test parallel state with branch containing multiple states."""
    state = ParallelState(

        end=True,
        branches=[
            Branch(
                start_at="Pass1",
                states={
                    "Pass1": PassState(
                        name="Pass1", result="step1", next_state="Pass2"
                    ),
                    "Pass2": PassState(name="Pass2", result="final", end=True),
                },
            )
        ],
    )

    input_data = "initial"

    output, _ = await state.execute(input_data)

    assert isinstance(output, list)
    assert len(output) == 1
    assert output[0] == "final"


@pytest.mark.asyncio
async def test_parallel_state_execute_with_result_path():
    """Test parallel state execution with result path."""
    state = ParallelState(

        next_state="NextState",
        result_path="$.results",
        branches=[
            Branch(
                start_at="Pass1",
                states={"Pass1": PassState(name="Pass1", result="value1", end=True)},
            ),
            Branch(
                start_at="Pass2",
                states={"Pass2": PassState(name="Pass2", result="value2", end=True)},
            ),
        ],
    )

    input_data = {"original": "data"}

    output, _ = await state.execute(input_data)

    assert isinstance(output, dict)
    assert output["original"] == "data"

    results = output["results"]
    assert isinstance(results, list)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_parallel_state_execute_with_output_path():
    """Test parallel state execution with output path."""
    state = ParallelState(

        end=True,
        output_path="$[0]",
        branches=[
            Branch(
                start_at="Pass1",
                states={"Pass1": PassState(name="Pass1", result="extracted", end=True)},
            ),
            Branch(
                start_at="Pass2",
                states={"Pass2": PassState(name="Pass2", result="ignored", end=True)},
            ),
        ],
    )

    input_data = "initial"

    output, _ = await state.execute(input_data)

    assert output == "extracted"


@pytest.mark.asyncio
async def test_parallel_state_execute_branch_error():
    """Test parallel state when one branch fails."""
    state = ParallelState(

        end=True,
        branches=[
            Branch(
                start_at="Pass1",
                states={"Pass1": PassState(name="Pass1", result="success", end=True)},
            ),
            Branch(
                start_at="Fail1",
                states={
                    "Fail1": FailState(
                        name="Fail1",
                        error="BranchError",
                        cause="Branch failed intentionally",
                    )
                },
            ),
        ],
    )

    input_data = "initial"

    with pytest.raises(StateError):
        await state.execute(input_data)


@pytest.mark.asyncio
async def test_parallel_state_execute_with_result_selector():
    """Test parallel state with result selector."""
    state = ParallelState(
        end=True,
        result_selector={"first": "$[0]", "second": "$[1]", "count": 2},
        branches=[
            Branch(
                start_at="Pass1",
                states={"Pass1": PassState(name="Pass1", result="value1", end=True)},
            ),
            Branch(
                start_at="Pass2",
                states={"Pass2": PassState(name="Pass2", result="value2", end=True)},
            ),
        ],
    )

    input_data = "initial"

    output, _ = await state.execute(input_data)

    assert isinstance(output, dict)
    assert output["first"] == "value1"
    assert output["second"] == "value2"
    assert output["count"] == 2


@pytest.mark.asyncio
async def test_parallel_state_concurrent_execution():
    """Test that branches actually execute concurrently."""
    execution_log = []

    class LoggingPassState(PassState):
        """Pass state that logs execution."""

        def __init__(self, name: str, delay: float = 0, **kwargs):
            super().__init__(name, **kwargs)
            self.delay = delay

        async def execute(self, input_data, context=None):
            execution_log.append(f"{self.name}_start")
            await asyncio.sleep(self.delay)
            execution_log.append(f"{self.name}_end")
            return await super().execute(input_data, context)

    state = ParallelState(

        end=True,
        branches=[
            Branch(
                start_at="Pass1",
                states={
                    "Pass1": LoggingPassState(
                        name="Pass1", delay=0.1, result="result1", end=True
                    )
                },
            ),
            Branch(
                start_at="Pass2",
                states={
                    "Pass2": LoggingPassState(
                        name="Pass2", delay=0.1, result="result2", end=True
                    )
                },
            ),
        ],
    )

    await state.execute("test")

    # Both should start before either ends (concurrent execution)
    assert "Pass1_start" in execution_log
    assert "Pass2_start" in execution_log
    assert execution_log.index("Pass1_start") < len(execution_log)
    assert execution_log.index("Pass2_start") < len(execution_log)


def test_parallel_state_validate():
    """Test parallel state validation."""

    # Valid parallel state
    state = ParallelState(

        branches=[
            Branch(start_at="Pass1", states={"Pass1": PassState(name="Pass1", end=True)})
        ],
    )
    state.validate()  # Should not raise

    # No branches
    with pytest.raises(ValueError, match="must have at least one branch") as exec:
        ParallelState(branches=[])
    assert exec is not None

    # Branch missing StartAt
    with pytest.raises(ValueError, match="StartAt is required"):
        Branch(start_at="", states={"Pass1": PassState(name="Pass1", end=True)})

    # StartAt state not found
    with pytest.raises(ValueError, match="StartAt state"):
        ParallelState(
            branches=[
                Branch(
                    start_at="NonExistent",
                    states={"Pass1": PassState(name="Pass1", end=True)},
                )
            ],
        )

    # State without End or Next
    with pytest.raises(ValueError, match="must have either Next or End"):
        ParallelState(
            branches=[
                Branch(
                    start_at="Pass1",
                    states={"Pass1": PassState(name="Pass1", end=False, next_state=None)},
                )
            ],
        )

    # Multiple valid branches
    try:
        ParallelState(
            branches=[
                Branch(start_at="Pass1", states={"Pass1": PassState(name="Pass1", end=True)}),
                Branch(start_at="Pass2", states={"Pass2": PassState(name="Pass2", end=True)}),
            ],
        )
    except StateError:
        pytest.fail("StateError Exception shouldn't have occurred")


def test_parallel_state_getters():
    """Test parallel state getters."""
    state = ParallelState(
        end=True,
        next_state="NextState",
        branches=[
            Branch(start_at="Pass1", states={"Pass1": PassState(name="Pass1", end=True)})
        ],
    )

    assert state.state_type == "Parallel"
    assert state.is_end() is True
    assert state.get_next() == "NextState"


def test_parallel_state_get_next_states():
    """Test getting next states from parallel state."""
    state = ParallelState(

        next_state="NextState",
        branches=[
            Branch(start_at="Pass1", states={"Pass1": PassState(name="Pass1", end=True)})
        ],
    )

    next_states = state.get_next_states()
    assert next_states == ["NextState"]

    # Test with end state
    state = ParallelState(

        end=True,
        branches=[
            Branch(start_at="Pass1", states={"Pass1": PassState(name="Pass1", end=True)})
        ],
    )

    next_states = state.get_next_states()
    assert next_states == []


def test_parallel_state_to_dict():
    """Test parallel state serialization to dict."""
    state = ParallelState(

        next_state="NextState",
        result_path="$.results",
        branches=[
            Branch(
                start_at="Pass1",
                states={"Pass1": PassState(name="Pass1", result="value1", end=True)},
                comment="First branch",
            ),
            Branch(
                start_at="Pass2",
                states={"Pass2": PassState(name="Pass2", result="value2", end=True)},
            ),
        ],
    )

    state_dict = state.to_dict()

    assert state_dict["Type"] == "Parallel"
    assert state_dict["Next"] == "NextState"
    assert state_dict["ResultPath"] == "$.results"
    assert len(state_dict["Branches"]) == 2
    assert state_dict["Branches"][0]["StartAt"] == "Pass1"
    assert state_dict["Branches"][0]["Comment"] == "First branch"


def test_branch_creation():
    """Test branch creation helper function."""
    branch = create_branch(
        start_at="Pass1",
        states={"Pass1": PassState(name="Pass1", end=True)},
        comment="Test branch",
    )

    assert branch.start_at == "Pass1"
    assert "Pass1" in branch.states
    assert branch.comment == "Test branch"


def test_branch_validation():
    """Test branch validation."""
    # Valid branch
    branch = Branch(
        start_at="Pass1", states={"Pass1": PassState(name="Pass1", end=True)}
    )
    assert branch.start_at == "Pass1"

    # Empty StartAt
    with pytest.raises(ValueError, match="StartAt is required"):
        Branch(start_at="", states={"Pass1": PassState(name="Pass1", end=True)})

    # Empty states
    with pytest.raises(ValueError, match="must have at least one state"):
        Branch(start_at="Pass1", states={})


@pytest.mark.asyncio
async def test_parallel_state_branch_with_choice():
    """Test parallel state with branches containing different state types."""

    # class ChoiceState:
    #     """Mock Choice state."""
    #
    #     def __init__(self, name: str, default: str):
    #         self.name = name
    #         self.type = "Choice"
    #         self.default = default
    #         self.end = False
    #
    #     def get_next(self) -> Optional[str]:
    #         return None
    #
    #     def is_end(self) -> bool:
    #         return False
    #
    #     async def execute(self, input_data, context=None):
    #         # Simple choice logic - go to default
    #         return input_data, self.default

    state = ParallelState(
        end=True,
        branches=[
            Branch(
                start_at="Choice1",
                states={
                    "Choice1": ChoiceState(name="Choice1", default="Pass1"),
                    "Pass1": PassState(name="Pass1", result="choice-result", end=True),
                },
            ),
            Branch(
                start_at="Pass2",
                states={"Pass2": PassState(name="Pass2", result="direct-result", end=True)},
            ),
        ],
    )

    output, _ = await state.execute({"test": "data"})

    assert isinstance(output, list)
    assert len(output) == 2
    assert output[0] == "choice-result"
    assert output[1] == "direct-result"


@pytest.mark.asyncio
async def test_parallel_state_error_in_branch():
    """Test that errors in branches are propagated correctly."""

    state = ParallelState(

        end=True,
        branches=[
            Branch(start_at="Error1", states={"Error1": FailState(name="Error1", error="Error1")}),
            Branch(
                start_at="Pass1",
                states={"Pass1": PassState(name="Pass1", result="success", end=True)},
            ),
        ],
    )

    with pytest.raises(StateError):
        await state.execute("test")


@pytest.mark.asyncio
async def test_parallel_state_empty_result():
    """Test parallel state with branches that return None."""
    state = ParallelState(

        end=True,
        branches=[
            Branch(
                start_at="Pass1",
                states={"Pass1": PassState(name="Pass1", result=None, end=True)},
            ),
            Branch(
                start_at="Pass2",
                states={"Pass2": PassState(name="Pass2", result=None, end=True)},
            ),
        ],
    )

    output, _ = await state.execute("test")

    assert isinstance(output, list)
    assert len(output) == 2
    assert output[0] is not None
    assert output[1] is not None


@pytest.mark.asyncio
async def test_parallel_state_complex_data_flow():
    """Test parallel state with complex data transformations."""
    state = ParallelState(

        end=True,
        input_path="$.payload",
        result_path="$.parallel_results",
        output_path="$.parallel_results",
        branches=[
            Branch(
                start_at="Pass1",
                states={
                    "Pass1": PassState(
                        name="Pass1",
                        result={"branch": "first", "status": "complete"},
                        end=True,
                    )
                },
            ),
            Branch(
                start_at="Pass2",
                states={
                    "Pass2": PassState(
                        name="Pass2",
                        result={"branch": "second", "status": "complete"},
                        end=True,
                    )
                },
            ),
        ],
    )

    input_data = {"payload": {"data": "test"}, "metadata": "ignored"}

    output, _ = await state.execute(input_data)

    assert isinstance(output, list)
    assert len(output) == 2
    assert output[0]["branch"] == "first"
    assert output[1]["branch"] == "second"
