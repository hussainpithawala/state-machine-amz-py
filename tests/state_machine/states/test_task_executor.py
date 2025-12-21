"""
Integration tests for TaskState with ExecutionContext.

Based on task_with_executor_test.go
"""

import asyncio
import time
from typing import Any, Callable, Dict, Optional

import pytest

from src.states.base import CatchRule, RetryRule, StateError
from src.states.json_path import JSONPathProcessor
from src.states.task_state import AbstractTaskHandler, DefaultTaskHandler, TaskState, with_execution_context


# Mock ExecutionContext implementation
class MockExecutionContext:
    """Mock implementation of ExecutionContext for testing."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, resource: str, handler: Callable[[Any], Any]) -> None:
        """Register a task handler for a resource."""
        self.handlers[resource] = handler

    def get_task_handler(self, resource: str) -> Optional[Callable]:
        """Get a task handler for a resource."""
        return self.handlers.get(resource)


@pytest.mark.asyncio
async def test_task_executor_basic():
    """Test basic task execution with registered handler."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    # Register a simple handler
    async def hello_world_handler(resource, input_data, parameters):
        print(f"Executing HelloWorld with input: {input_data}")
        if isinstance(input_data, dict):
            input_data["message"] = "Hello, World!"
            input_data["processed"] = True
            input_data["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return input_data

    mock_exec_ctx.register_handler(
        "arn:aws:lambda:us-east-1:123456789012:function:HelloWorld",
        hello_world_handler,
    )

    # Create context with execution context
    context = with_execution_context({}, mock_exec_ctx)

    # Create default task handler
    handler = DefaultTaskHandler()

    # Test input
    input_data = {"name": "Test User", "age": 30}

    # Execute task
    result = await handler.execute(
        "arn:aws:lambda:us-east-1:123456789012:function:HelloWorld",
        input_data,
        None,
        context,
    )

    assert result is not None
    assert result["message"] == "Hello, World!"
    assert result["processed"] is True
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_task_executor_with_parameters():
    """Test task execution with parameters."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    # Register payment processor
    async def payment_processor(resource, input_data, parameters):
        print(f"Processing payment with input: {input_data}")

        if not isinstance(input_data, dict):
            raise ValueError("invalid payment input")

        # Validate required fields
        json_path_processor = JSONPathProcessor()
        amount = json_path_processor.get_value(input_data, parameters['amount'])
        if amount is None:
            raise ValueError("invalid amount")

        currency = json_path_processor.get_value(input_data, parameters['currency'])
        if currency is None:
            raise ValueError("invalid currency")

        # Process payment
        input_data["amount"] = amount
        input_data["currency"] = currency
        input_data["status"] = "COMPLETED"
        input_data["transaction_id"] = f"TXN-{int(time.time() * 1000000)}"
        input_data["processed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        return input_data

    mock_exec_ctx.register_handler("arn:aws:states:::payment:process", payment_processor)

    # Create context
    context = with_execution_context({}, mock_exec_ctx)

    # Create handler
    handler = DefaultTaskHandler()

    # Test input
    input_data = {
        "payment": {"amount": 100.50, "currency": "USD"},
        "customer": {"id": "cust_123", "name": "John Doe"},
    }

    parameters = {
        "amount": "$.payment.amount",
        "currency": "$.payment.currency",
        "customer": "$.customer",
        "reference": "test-123",
    }

    # Execute task
    result = await handler.execute("arn:aws:states:::payment:process", input_data, parameters, context)

    assert result is not None
    assert result["amount"] == 100.50
    assert result["currency"] == "USD"
    assert result["status"] == "COMPLETED"
    assert "transaction_id" in result


@pytest.mark.asyncio
async def test_task_executor_with_timeout():
    """Test task execution with timeout."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    # Register slow operation
    async def slow_operation(resource, input_data, parameters):
        print("Starting slow operation")
        await asyncio.sleep(2)
        print("Slow operation completed")
        return {"status": "slow_success"}

    mock_exec_ctx.register_handler("arn:aws:lambda:::slow:operation", slow_operation)

    # Create context
    context = with_execution_context({}, mock_exec_ctx)

    # Create handler
    handler = DefaultTaskHandler()

    # Execute with timeout
    timeout = 1
    start = time.time()

    with pytest.raises(Exception) as exc_info:
        await handler.execute_with_timeout("arn:aws:lambda:::slow:operation", None, None, timeout, context)

    elapsed = time.time() - start

    assert "timeout" in str(exc_info.value).lower() or "Timeout" in str(exc_info.value)
    assert elapsed < 1.5  # Should timeout before 1.5s
    assert elapsed > 0.9  # But after 0.9s


@pytest.mark.asyncio
async def test_task_executor_fallback():
    """Test fallback behavior when no handler is registered."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    # Create context
    context = with_execution_context({}, mock_exec_ctx)

    # Create handler
    handler = DefaultTaskHandler()

    # Test input
    input_data = {"test": "data"}

    # Execute - should fall back to returning input as-is
    result = await handler.execute("arn:aws:lambda:::unknown:function", input_data, None, context)

    assert result == input_data


@pytest.mark.asyncio
async def test_task_executor_error_handling():
    """Test error handling in task execution."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    # Register error generator
    async def error_generator(resource, input_data, parameters):
        if isinstance(input_data, dict) and input_data.get("should_fail") is True:
            raise StateError("Task execution failed", error_type="States.TaskFailed")
        return {"status": "success"}

    mock_exec_ctx.register_handler("arn:aws:lambda:::error:generator", error_generator)

    # Create context
    context = with_execution_context({}, mock_exec_ctx)

    # Create handler
    handler = DefaultTaskHandler()

    # Test error case
    input_data = {"should_fail": True}

    with pytest.raises(Exception) as exc_info:
        await handler.execute("arn:aws:lambda:::error:generator", input_data, None, context)

    assert "Task execution failed" in str(exc_info.value)

    # Test success case
    input_data = {"should_fail": False}

    result = await handler.execute("arn:aws:lambda:::error:generator", input_data, None, context)

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_task_executor_no_execution_context():
    """Test task execution without execution context."""
    # Create handler
    handler = DefaultTaskHandler()

    # Test input
    input_data = {"test": "data"}

    # Execute without execution context - should fall back
    result = await handler.execute("arn:aws:lambda:::any:function", input_data, None, {})

    assert result == input_data


@pytest.mark.asyncio
async def test_task_state_integration():
    """Test full TaskState integration with execution context."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    # Prepare handler as a sub-class of AbstractTaskHandler

    class TransformDataHandler(AbstractTaskHandler):
        async def execute(
            self,
            resource: str,
            input_data: Optional[Dict[str, Any]],
            parameters: Optional[Dict[str, Any]] = None,
            context: Optional[Dict[str, Any]] = None,
        ) -> Any:
            return self.transform_data(input_data)

        async def execute_with_timeout(
            self,
            resource: str,
            input_data: Optional[Dict[str, Any]],
            parameters: Optional[Dict[str, Any]] = None,
            timeout_seconds: Optional[int] = None,
            context: Optional[Dict[str, Any]] = None,
        ) -> Any:
            return self.transform_data(input_data)

        def transform_data(self, input_data: Optional[Dict[str, Any]]) -> Any:
            if not isinstance(input_data, dict):
                raise ValueError("invalid input")

            input_data["transformed"] = True
            input_data["processed_at"] = int(time.time())
            return input_data

    # Register handler

    mock_exec_ctx.register_handler("arn:aws:lambda:function:TransformData", TransformDataHandler())

    resource_key = "arn:aws:lambda:function:TransformData"

    # Create task state
    task_state = TaskState(
        name="ProcessData",
        resource=resource_key,
        next_state="NextState",
        result_path="$.result",
        output_path="$.result",
        parameters={"data": "$", "id": "$.id"},
    )

    # Create context
    context = with_execution_context({}, mock_exec_ctx)

    # Test input
    input_data = {"id": "test-123", "data": [1, 2, 3]}

    # Execute task state
    result, next_state = await task_state.execute(input_data, context)

    assert result is not None
    assert next_state == "NextState"
    assert result["transformed"] is True
    assert "processed_at" in result
    assert "id" in result
    assert "data" in result


@pytest.mark.asyncio
async def test_task_retry_logic():
    """Test retry and catch functionality."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    call_count = {"count": 0}

    class FlakyServiceHandler(AbstractTaskHandler):
        async def execute(
            self,
            resource: str,
            input_data: Any,
            parameters: Optional[Dict[str, Any]] = None,
            context: Optional[Dict[str, Any]] = None,
        ) -> Any:
            return self.__flaky_service__(input_data)

        async def execute_with_timeout(
            self,
            resource: str,
            input_data: Any,
            parameters: Optional[Dict[str, Any]] = None,
            timeout_seconds: Optional[int] = None,
            context: Optional[Dict[str, Any]] = None,
        ) -> Any:
            return self.__flaky_service__(input_data)

        def __flaky_service__(self, input_data):
            call_count["count"] += 1
            print(f"FlakyService called {call_count['count']} times")

            if call_count["count"] < 3:
                raise StateError("Task failed", error_type="States.TaskFailed")

            return {
                "status": "success",
                "attempts": call_count["count"],
                "finalized": True,
            }

    mock_exec_ctx.register_handler("arn:aws:lambda:function:FlakyService", FlakyServiceHandler())

    # Create task state with retry policy
    task_state = TaskState(
        name="FlakyTask",
        resource="arn:aws:lambda:function:FlakyService",
        retry=[
            RetryRule(
                error_equals=["States.TaskFailed"],
                interval_seconds=1,
                max_attempts=3,
                backoff_rate=2.0,
            )
        ],
        catch=[CatchRule(error_equals=["States.TaskFailed"], next_state="HandleFailure")],
        end=True,
    )

    # Create context
    context = with_execution_context({}, mock_exec_ctx)

    # Execute task state
    start = time.time()
    result, next_state = await task_state.execute(None, context)
    elapsed = time.time() - start

    assert result is not None
    assert next_state is None  # Should succeed after retries

    # Should have retried 3 times
    assert call_count["count"] == 3

    # Should have taken around 1s + 2s = 3s for retries with backoff
    assert elapsed > 2.5
    assert elapsed < 7.0

    # Verify result
    assert result["status"] == "success"
    assert result["attempts"] == 3


@pytest.mark.asyncio
async def test_task_catch_logic():
    """Test catch functionality."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    call_count = {"count": 0}

    class AlwaysFailsHandler(DefaultTaskHandler):
        async def execute(
            self,
            resource: str,
            input_data: Any,
            parameters: Optional[Dict[str, Any]] = None,
            context: Optional[Dict[str, Any]] = None,
        ) -> Any:
            return self.always_fails(input_data)

        def can_handle(self, resource: str) -> bool:
            return super().can_handle(resource)

        def always_fails(self, input_data):
            call_count["count"] += 1
            raise StateError("Task failed", error_type="States.TaskFailed")

    mock_exec_ctx.register_handler("arn:aws:lambda:function:AlwaysFails", AlwaysFailsHandler())

    # Create task state with catch policy
    task_state = TaskState(
        name="FailingTask",
        resource="arn:aws:lambda:function:AlwaysFails",
        retry=[RetryRule(error_equals=["States.TaskFailed"], max_attempts=2)],
        catch=[
            CatchRule(
                error_equals=["States.TaskFailed"],
                result_path="$.error",
                next_state="ErrorHandler",
            )
        ],
        end=True,
    )

    # Create context
    context = with_execution_context({}, mock_exec_ctx)

    # Test input
    input_data = {"original": "data"}

    # Execute task state
    result, next_state = await task_state.execute(input_data, context)

    # Should not raise error because catch handled it
    assert result is not None
    assert next_state == "ErrorHandler"

    # Should have been called 3 times (initial + 2 retries)
    assert call_count["count"] == 3

    # Verify result contains error info
    assert "original" in result
    assert "error" in result

    error_info = result["error"]
    assert "Error" in error_info
    assert "Cause" in error_info


@pytest.mark.asyncio
async def test_example_task_executor():
    """Demonstration of real-world usage."""
    # 1. Create execution context and register handlers
    mock_exec_ctx = MockExecutionContext()

    # Register payment processor
    async def process_payment(resource, input_data, parameters):
        payment = input_data
        payment["status"] = "processed"
        payment["transaction_id"] = f"TXN-{int(time.time() * 1000000)}"
        return payment

    mock_exec_ctx.register_handler("arn:aws:states:::payment:process", process_payment)

    # Register email sender
    async def send_email(resource, input_data, parameters):
        email = input_data
        print(f"Sending email to: {email.get('to')}")
        email["sent"] = True
        email["sent_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return email

    mock_exec_ctx.register_handler("arn:aws:states:::email:send", send_email)

    # 2. Create context
    context = with_execution_context({}, mock_exec_ctx)

    # 3. Create task handler
    handler = DefaultTaskHandler()

    # 4. Execute tasks
    payment_input = {
        "amount": 99.99,
        "currency": "USD",
        "customer": "john@example.com",
    }

    result = await handler.execute("arn:aws:states:::payment:process", payment_input, None, context)

    print(f"Payment result: {result}")
    assert result["status"] == "processed"
    assert "transaction_id" in result

    # 5. Chain another task
    email_input = {
        "to": "john@example.com",
        "subject": "Payment Confirmation",
        "body": "Your payment was successful!",
    }

    email_result = await handler.execute("arn:aws:states:::email:send", email_input, None, context)

    print(f"Email result: {email_result}")
    assert email_result["sent"] is True
    assert "sent_at" in email_result


@pytest.mark.asyncio
async def test_synchronous_handler():
    """Test that synchronous handlers work correctly."""
    # Create mock execution context
    mock_exec_ctx = MockExecutionContext()

    # Register synchronous handler
    def sync_handler(resource, input_data, parameters):
        return {"result": "sync", "input": input_data}

    mock_exec_ctx.register_handler("arn:aws:lambda:::sync:function", sync_handler)

    # Create context
    context = with_execution_context({}, mock_exec_ctx)

    # Create handler
    handler = DefaultTaskHandler()

    # Execute
    result = await handler.execute("arn:aws:lambda:::sync:function", {"test": "data"}, None, context)

    assert result["result"] == "sync"
    assert result["input"]["test"] == "data"
