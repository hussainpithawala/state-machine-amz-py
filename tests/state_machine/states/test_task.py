"""
Tests for TaskState implementation.

Based on task_test.go
"""

import asyncio
from typing import Any, Dict, Optional

import pytest

from src.states.base import CatchRule, RetryRule
from src.states.task_state import TaskState


# Mock TaskHandler for testing
class MockTaskHandler:
    """Mock implementation of TaskHandler for testing."""

    def __init__(
            self,
            execute_func=None,
            execute_with_timeout_func=None,
            can_handle_func=None,
    ):
        self.execute_func = execute_func
        self.execute_with_timeout_func = execute_with_timeout_func
        self.can_handle_func = can_handle_func

    async def execute(
            self,
            resource: str,
            input_data: Any,
            parameters: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute task."""
        if self.execute_func is not None:
            result = self.execute_func(resource, input_data, parameters)
            if asyncio.iscoroutine(result):
                return await result
            return result
        return input_data

    async def execute_with_timeout(
            self,
            resource: str,
            input_data: Any,
            parameters: Optional[Dict[str, Any]] = None,
            timeout_seconds: Optional[int] = None,
            context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute task with timeout."""
        if self.execute_with_timeout_func is not None:
            result = self.execute_with_timeout_func(
                resource, input_data, parameters, timeout_seconds, context
            )
            if asyncio.iscoroutine(result):
                return await result
            return result

        # Default implementation - if no timeout specified, execute directly
        if timeout_seconds is None or timeout_seconds <= 0:
            return await self.execute(resource, input_data, parameters)

        try:
            return await asyncio.wait_for(
                self.execute(resource, input_data, parameters), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task timed out after {timeout_seconds} seconds")

    def can_handle(self, resource: str) -> bool:
        """Check if can handle resource."""
        if self.can_handle_func is not None:
            return self.can_handle_func(resource)
        return True


@pytest.mark.asyncio
async def test_task_state_execute_basic():
    """Test basic task state execution."""

    def execute_func(resource, input_data, parameters):
        return {"result": "success", "input": input_data}

    handler = MockTaskHandler(execute_func=execute_func)
    resource_key = "arn:aws:lambda:us-east-1:123456789012:function:MyFunction"
    state = TaskState(
        name="TaskState",
        resource=resource_key,
        next_state="NextState",
        task_handler=handler,
    )

    input_data = {"key": "value"}

    # Create execution context
    output, next_state = await state.execute(input_data)

    assert output is not None
    assert next_state == "NextState"
    assert output["result"] == "success"


@pytest.mark.asyncio
async def test_task_state_execute_with_parameters():
    """Test task state execution with parameters."""

    def execute_func(resource, input_data, parameters):
        return {"params": parameters}

    handler = MockTaskHandler(execute_func=execute_func)
    _resource_key = "arn:aws:lambda:us-east-1:123456789012:function:MyFunction"
    state = TaskState(
        name="TaskState",
        resource=_resource_key,
        end=True,
        parameters={"param1": "value1", "param2": 42},
        task_handler=handler,
    )

    input_data = "initial"

    output, _ = await state.execute(input_data)

    assert output is not None


@pytest.mark.asyncio
async def test_task_state_execute_with_input_path():
    """Test task state execution with input path."""

    def execute_func(resource, input_data, parameters):
        return input_data

    _resource_key = "arn:aws:lambda:us-east-1:123456789012:function:MyFunction"
    state = TaskState(
        name="TaskState",
        resource=_resource_key,
        end=True,
        input_path="$.data",
        task_handler=MockTaskHandler(execute_func=execute_func)
    )

    input_data = {"data": {"value": "test"}, "other": "ignored"}

    output, _ = await state.execute(input_data)

    assert output is not None
    assert output["value"] == "test"


@pytest.mark.asyncio
async def test_task_state_execute_with_result_path():
    """Test task state execution with result path."""

    def execute_func(resource, input_data, parameters):
        return "task-result"

    handler = MockTaskHandler(execute_func=execute_func)

    _resource_key = "arn:aws:lambda:us-east-1:123456789012:function:MyFunction"
    state = TaskState(
        name="TaskState",
        resource=_resource_key,
        end=True,
        result_path="$.taskResult",
        task_handler=handler,
    )

    input_data = {"original": "data"}

    output, _ = await state.execute(input_data)

    assert output is not None
    assert output["original"] == "data"
    assert output["taskResult"] == "task-result"


@pytest.mark.asyncio
async def test_task_state_execute_with_output_path():
    """Test task state execution with output path."""

    def execute_func(resource, input_data, parameters):
        return {"result": "success", "extra": "data"}

    handler = MockTaskHandler(execute_func=execute_func)
    _resource_key = "arn:aws:lambda:us-east-1:123456789012:function:MyFunction"
    state = TaskState(
        name="TaskState",
        resource=_resource_key,
        end=True,
        output_path="$.result",
        task_handler=handler,
    )

    input_data = "initial"

    output, _ = await state.execute(input_data)

    assert output == "success"


@pytest.mark.asyncio
async def test_task_state_execute_with_timeout():
    """Test task state execution with timeout."""

    async def execute_func(resource, input_data, parameters):
        # Simulate a long-running task
        await asyncio.sleep(3)
        return input_data

    handler = MockTaskHandler(execute_func=execute_func)

    state = TaskState(
        name="TaskState",
        resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
        end=True,
        timeout_seconds=1,
        task_handler=handler,
    )

    input_data = "test"

    with pytest.raises(Exception):
        await state.execute(input_data)


@pytest.mark.asyncio
async def test_task_state_execute_with_retry_success():
    """Test task state execution with retry that eventually succeeds."""
    call_count = {"count": 0}

    def execute_func(resource, input_data, parameters):
        call_count["count"] += 1
        # Fail on first attempt, succeed on second
        if call_count["count"] == 1:
            raise Exception("TemporaryError")
        return "success"

    _resource_key = "arn:aws:lambda:us-east-1:123456789012:function:MyFunction"
    state = TaskState(
        name="TaskState",
        resource=_resource_key,
        end=True,
        retry=[
            RetryRule(
                error_equals=["TemporaryError"],
                interval_seconds=0,
                max_attempts=2,
                backoff_rate=1.0,
            )
        ],
        task_handler=MockTaskHandler(execute_func=execute_func),
    )

    input_data = "test"

    output, _ = await state.execute(input_data)

    assert output == "success"
    assert call_count["count"] == 2


@pytest.mark.asyncio
async def test_task_state_execute_with_retry_exhausted_attempts():
    """Test task state execution with retry that exhausts attempts."""
    call_count = {"count": 0}

    def execute_func(resource, input_data, parameters):
        call_count["count"] += 1
        raise Exception("PersistentError")

    handler = MockTaskHandler(execute_func=execute_func)
    _resource_key = "arn:aws:lambda:us-east-1:123456789012:function:MyFunction"
    state = TaskState(
        name="TaskState",
        resource=_resource_key,
        end=True,
        retry=[
            RetryRule(
                error_equals=["PersistentError"],
                interval_seconds=0,
                max_attempts=2,
                backoff_rate=1.0,
            )
        ],
        task_handler=handler,
    )

    input_data = "test"

    with pytest.raises(Exception):
        await state.execute(input_data)

    assert call_count["count"] == 3  # Initial + 2 retries


@pytest.mark.asyncio
async def test_task_state_execute_with_catch():
    """Test task state execution with catch policy."""

    def execute_func(resource, input_data, parameters):
        raise Exception("CustomError")

    handler = MockTaskHandler(execute_func=execute_func)

    state = TaskState(
        name="TaskState",
        resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
        catch=[
            CatchRule(
                error_equals=["CustomError"],
                next_state="ErrorHandler",
                result_path="$.error",
            )
        ],
        task_handler=handler,
        end=True
    )

    input_data = {"original": "data"}

    output, next_state = await state.execute(input_data)

    assert next_state == "ErrorHandler"
    assert output["original"] == "data"
    assert "error" in output


@pytest.mark.asyncio
async def test_task_state_execute_with_result_selector():
    """Test task state execution with result selector."""

    def execute_func(resource, input_data, parameters):
        return {"statusCode": 200, "body": "success"}

    handler = MockTaskHandler(execute_func=execute_func)

    state = TaskState(
        name="TaskState",
        resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
        end=True,
        result_selector={"message": "$.body", "code": "$.statusCode"},
        task_handler=handler,
    )

    input_data = "test"

    output, _ = await state.execute(input_data)

    assert output is not None
    assert output["message"] == "success"
    assert output["code"] == 200


def test_task_state_validate():
    """Test task state validation."""

    # Valid task state
    try:
        TaskState(
            name="TaskState",
            resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
            end=True
        )
    except ValueError:
        pytest.fail("ValueError should not be raised")

    # Missing resource
    with pytest.raises(ValueError, match="Resource is required"):
        TaskState(name="TaskState", resource="", end=True).validate()

    # Invalid timeout
    with pytest.raises(ValueError, match="TimeoutSeconds must be positive"):
        TaskState(
            name="TaskState2",
            resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
            timeout_seconds=0,
            end=True
        )

    # Invalid heartbeat
    with pytest.raises(ValueError, match="HeartbeatSeconds must be positive"):
        TaskState(
            name="TaskState",
            resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
            heartbeat_seconds=-1,
            end=True
        )

    # Heartbeat >= timeout
    with pytest.raises(
            ValueError, match="HeartbeatSeconds must be less than TimeoutSeconds"
    ):
        TaskState(
            name="TaskState",
            resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
            timeout_seconds=10,
            heartbeat_seconds=10,
            end=True
        )

    # Invalid retry - no error equals
    with pytest.raises(ValueError, match="ErrorEquals"):
        TaskState(
            name="TaskState",
            resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
            retry=[RetryRule(error_equals=[])],
            end=True
        )

    # Invalid backoff rate
    with pytest.raises(ValueError, match="BackoffRate"):
        RetryRule(error_equals=["Error"], backoff_rate=0.5)

    # Invalid catch - no next
    with pytest.raises(ValueError, match="Next"):
        TaskState(
            name="TaskState",
            resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
            catch=[CatchRule(error_equals=["Error"], next_state="")],
        ).validate()


def test_task_state_getters():
    """Test task state getters."""
    with pytest.raises(ValueError, match="State cannot have both Next and End") as exec:
        TaskState(
            name="MyTaskState",
            resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
            end=True,
            next_state="NextState",
        )


def test_task_state_error_matching():
    """Test error matching logic."""
    state = TaskState(
        name="TaskState",
        resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
        end=True
    )

    # Exact match
    error = Exception("CustomError")
    assert state._error_matches(error, ["CustomError"]) is True

    # States.ALL wildcard
    error = Exception("AnyError")
    assert state._error_matches(error, ["States.ALL"]) is True

    # No match
    error = Exception("UnhandledError")
    assert state._error_matches(error, ["CustomError"]) is False


def test_task_state_get_next_states():
    """Test getting all possible next states."""
    state = TaskState(
        name="TaskState",
        resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
        next_state="NextState",
        catch=[
            CatchRule(error_equals=["Error1"], next_state="ErrorHandler1"),
            CatchRule(error_equals=["Error2"], next_state="ErrorHandler2"),
        ],
    )

    next_states = state.get_next_states()
    assert "NextState" in next_states
    assert "ErrorHandler1" in next_states
    assert "ErrorHandler2" in next_states


def test_task_state_to_dict():
    """Test task state serialization to dict."""
    state = TaskState(
        name="TaskState",
        resource="arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
        next_state="NextState",
        parameters={"param1": "value1"},
        timeout_seconds=30,
        retry=[RetryRule(error_equals=["Error"], max_attempts=3)],
        catch=[CatchRule(error_equals=["Error"], next_state="ErrorHandler")],
    )

    state_dict = state.to_dict()

    assert state_dict["Type"] == "Task"
    assert state_dict["Resource"] == "arn:aws:lambda:us-east-1:123456789012:function:MyFunction"
    assert state_dict["Next"] == "NextState"
    assert state_dict["Parameters"] == {"param1": "value1"}
    assert state_dict["TimeoutSeconds"] == 30
    assert len(state_dict["Retry"]) == 1
    assert len(state_dict["Catch"]) == 1
