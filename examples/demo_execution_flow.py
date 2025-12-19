"""
Demo execution flow for State Machine.

Demonstrates real-world usage patterns with task handlers, retry logic,
parallel execution, and error handling.

Based on execution_test.go demo
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, Optional

from examples import ExampleTaskHandler
from pkg.machine import StateMachine
from pkg.states import with_execution_context


# Mock execution context
class DemoExecutionContext:
    """Demo execution context for testing handlers."""

    def __init__(self):
        self.handlers = {}

    def register_handler(self, name, handler):
        """Register a task handler."""
        self.handlers[name] = handler

    def get_task_handler(self, resource):
        """Get a task handler by resource."""
        return self.handlers.get(resource)


async def demo_1_simple_greeting():
    """Demo 1: Simple greeting handler."""
    print("\n" + "=" * 60)
    print("Demo 1: Simple Greeting")
    print("=" * 60)

    # Create execution context
    exec_ctx = DemoExecutionContext()

    # Register greeting handler
    async def greet_handler(input_data):
        print("👋 Greeting handler called")
        if isinstance(input_data, dict):
            input_data["greeting"] = f"Hello, {input_data.get('name', 'World')}!"
            input_data["timestamp"] = datetime.now().isoformat()
            input_data["processed"] = True
        return input_data

    exec_ctx.register_handler("greet", greet_handler)

    # Create state machine
    definition = {
        "StartAt": "GreetUser",
        "States": {
            "GreetUser": {
                "Type": "Task",
                "Resource": "greet",
                "End": True,
            }
        },
    }

    sm = StateMachine.from_dict(definition)

    # Create context
    context = with_execution_context({}, exec_ctx)

    # Execute
    input_data = {"name": "Python User", "type": "demo"}
    execution = await sm.execute(input_data, context=context)

    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")


async def demo_2_processing_with_parameters():
    """Demo 2: Processing with parameters."""
    print("\n" + "=" * 60)
    print("Demo 2: Processing with Parameters")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register processor
    async def process_handler(input_data):
        print("⚙️  Processing handler called")
        if isinstance(input_data, dict):
            input_data["processed"] = True
            input_data["stage"] = "completed"
            input_data["processing_time"] = time.time()
        return input_data

    exec_ctx.register_handler("process", process_handler)

    # Create state machine with parameters
    definition = {
        "StartAt": "ProcessData",
        "States": {
            "ProcessData": {
                "Type": "Task",
                "Resource": "process",
                "Parameters": {
                    "values.$": "$.data.values",
                    "source.$": "$.data.source",
                    "extra": "parameter",
                },
                "End": True,
            }
        },
    }

    sm = StateMachine.from_dict(definition)
    context = with_execution_context({}, exec_ctx)

    # Execute
    input_data = {
        "data": {"values": [1, 2, 3], "source": "demo"},
        "metadata": "ignored",
    }

    execution = await sm.execute(input_data, context=context)

    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")


async def demo_3_validation_success():
    """Demo 3: Validation success case."""
    print("\n" + "=" * 60)
    print("Demo 3: Validation Success")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register validator
    async def validate_handler(input_data):
        print("✅ Validation handler called")
        if not isinstance(input_data, dict):
            raise ValueError("validation failed: invalid input type")

        if not input_data.get("required"):
            raise ValueError("validation failed: required field missing")

        input_data["valid"] = True
        return input_data

    exec_ctx.register_handler("validate", validate_handler)

    # Create state machine
    definition = {
        "StartAt": "ValidateInput",
        "States": {
            "ValidateInput": {
                "Type": "Task",
                "Resource": "validate",
                "End": True,
            }
        },
    }

    sm = StateMachine.from_dict(definition)
    context = with_execution_context({}, exec_ctx)

    # Execute
    input_data = {"required": True, "optional": "value"}

    execution = await sm.execute(input_data, context=context)

    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")


async def demo_4_validation_failure():
    """Demo 4: Validation failure case."""
    print("\n" + "=" * 60)
    print("Demo 4: Validation Failure")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register validator
    async def validate_handler(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        print("✅ Validation handler called")
        print(f"resource {resource}")
        print(f"input_data {input_data}")
        print(f"parameters {parameters}")
        print(f"timeout_seconds {timeout_seconds}")
        print(f"context {context}")

        if not input_data.get("required"):
            raise ValueError("validation failed: required field missing")
        return input_data

    exec_ctx.register_handler(
        "validate",
        ExampleTaskHandler(
            execute_func=validate_handler, execute_with_timeout_func=validate_handler
        ),
    )

    # Create state machine with error handling
    definition = {
        "StartAt": "ValidateInput",
        "States": {
            "ValidateInput": {
                "Type": "Task",
                "Resource": "validate",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleError",
                    }
                ],
                "End": True,
            },
            "HandleError": {
                "Type": "Pass",
                "Result": "Error handled gracefully",
                "End": True,
            },
        },
    }

    try:
        sm = StateMachine.from_dict(definition)
        context = with_execution_context({}, exec_ctx)
        # Execute with missing required field
        input_data = {"optional": "value"}
        await sm.execute(input_data, context=context)
    except ValueError as ve:
        print(f"ValueError as {ve}")


async def demo_5_task_with_retry():
    """Demo 5: Task with retry logic."""
    print("\n" + "=" * 60)
    print("Demo 5: Task with Retry")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    call_count = {"count": 0}

    # Register flaky handler
    async def flaky_handler(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        print(f"🎲 Flaky handler called (attempt {call_count['count']})")

        print(f"resource {resource}")
        print(f"input_data {input_data}")
        print(f"parameters {parameters}")
        print(f"timeout_seconds {timeout_seconds}")
        print(f"context {context}")

        call_count["count"] += 1

        if call_count["count"] < 3:
            raise Exception("States.TaskFailed: Temporary failure")

        return {
            "status": "success",
            "attempts": call_count["count"],
            "message": "Succeeded after retries",
        }

    exec_ctx.register_handler("flaky", flaky_handler)

    # Create state machine with retry
    definition = {
        "StartAt": "FlakyTask",
        "States": {
            "FlakyTask": {
                "Type": "Task",
                "Resource": "flaky",
                "Retry": [
                    {
                        "ErrorEquals": ["States.TaskFailed"],
                        "IntervalSeconds": 1,
                        "MaxAttempts": 3,
                        "BackoffRate": 1.5,
                    }
                ],
                "End": True,
            }
        },
    }

    sm = StateMachine.from_dict(definition)
    context = with_execution_context({}, exec_ctx)

    # Execute
    start = time.time()
    execution = await sm.execute({}, context=context)
    elapsed = time.time() - start

    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")
    print(f"Total attempts: {call_count['count']}")
    print(f"Time taken: {elapsed:.2f}s (including retry delays)")


async def demo_6_parallel_execution():
    """Demo 6: Parallel execution."""
    print("\n" + "=" * 60)
    print("Demo 6: Parallel Execution")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register parallel handlers
    async def task_a(input_data):
        print("🔵 Task A starting...")
        await asyncio.sleep(0.5)
        print("🔵 Task A completed")
        return {"task": "A", "result": "success"}

    async def task_b(input_data):
        print("🟢 Task B starting...")
        await asyncio.sleep(0.3)
        print("🟢 Task B completed")
        return {"task": "B", "result": "success"}

    async def task_c(input_data):
        print("🟡 Task C starting...")
        await asyncio.sleep(0.4)
        print("🟡 Task C completed")
        return {"task": "C", "result": "success"}

    exec_ctx.register_handler("taskA", task_a)
    exec_ctx.register_handler("taskB", task_b)
    exec_ctx.register_handler("taskC", task_c)

    # Create parallel state machine
    definition = {
        "StartAt": "ParallelProcessing",
        "States": {
            "ParallelProcessing": {
                "Type": "Parallel",
                "Branches": [
                    {
                        "StartAt": "BranchA",
                        "States": {
                            "BranchA": {
                                "Type": "Task",
                                "Resource": "taskA",
                                "End": True,
                            }
                        },
                    },
                    {
                        "StartAt": "BranchB",
                        "States": {
                            "BranchB": {
                                "Type": "Task",
                                "Resource": "taskB",
                                "End": True,
                            }
                        },
                    },
                    {
                        "StartAt": "BranchC",
                        "States": {
                            "BranchC": {
                                "Type": "Task",
                                "Resource": "taskC",
                                "End": True,
                            }
                        },
                    },
                ],
                "End": True,
            }
        },
    }

    try:
        sm = StateMachine.from_dict(definition)
        context = with_execution_context({}, exec_ctx)

        # Execute
        start = time.time()
        execution = await sm.execute({}, context=context)
        elapsed = time.time() - start

        print(f"\nStatus: {execution.status}")
        print(f"Parallel execution time: {elapsed: .2f}s")
        print(f"Results: {execution.output}")
    except ValueError as ve:
        print(f"ValueError as {ve}")


async def demo_7_complex_workflow():
    """Demo 7: Complex workflow with multiple patterns."""
    print("\n" + "=" * 60)
    print("Demo 7: Complex Workflow")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register handlers
    async def fetch_data(input_data):
        print("📥 Fetching data...")
        await asyncio.sleep(0.2)
        return {"data": [1, 2, 3, 4, 5], "source": "database"}

    async def transform_data(input_data):
        print("🔄 Transforming data...")
        await asyncio.sleep(0.3)
        data = input_data.get("data", [])
        return {"transformed": [x * 2 for x in data], "count": len(data)}

    async def validate_result(input_data):
        print("✅ Validating result...")
        if input_data.get("count", 0) > 0:
            return {"valid": True, "data": input_data}
        raise ValueError("No data to process")

    async def save_result(input_data):
        print("💾 Saving result...")
        await asyncio.sleep(0.2)
        return {"saved": True, "id": "result-123"}

    exec_ctx.register_handler("fetch", fetch_data)
    exec_ctx.register_handler("transform", transform_data)
    exec_ctx.register_handler("validate", validate_result)
    exec_ctx.register_handler("save", save_result)

    # Create complex workflow
    definition = {
        "StartAt": "FetchData",
        "States": {
            "FetchData": {
                "Type": "Task",
                "Resource": "fetch",
                "Next": "TransformData",
            },
            "TransformData": {
                "Type": "Task",
                "Resource": "transform",
                "Next": "ValidateResult",
            },
            "ValidateResult": {
                "Type": "Task",
                "Resource": "validate",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleError",
                    }
                ],
                "Next": "SaveResult",
            },
            "SaveResult": {
                "Type": "Task",
                "Resource": "save",
                "End": True,
            },
            "HandleError": {
                "Type": "Pass",
                "Result": "Error in validation",
                "End": True,
            },
        },
    }

    sm = StateMachine.from_dict(definition)
    context = with_execution_context({}, exec_ctx)

    # Execute
    start = time.time()
    execution = await sm.execute({}, context=context)
    elapsed = time.time() - start

    print(f"\nStatus: {execution.status}")
    print(f"Total time: {elapsed: .2f}s")
    print(f"States executed: {len(execution.history)}")
    print(f"Final output: {execution.output}")

    # Show execution history
    print("\nExecution History:")
    for i, state in enumerate(execution.history, 1):
        print(f"  {i}. {state.state_name}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("AWS State Machine - Execution Flow Demo")
    print("=" * 60)

    try:
        await demo_1_simple_greeting()
        await demo_2_processing_with_parameters()
        await demo_3_validation_success()
        await demo_4_validation_failure()
        await demo_5_task_with_retry()
        await demo_6_parallel_execution()
        await demo_7_complex_workflow()

        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
