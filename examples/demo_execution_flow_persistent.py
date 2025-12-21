"""
Demo execution flow for State Machine.

Demonstrates real-world usage patterns with task handlers, retry logic,
parallel execution, and error handling.

Based on execution_test.go demo
"""

import asyncio
import os
from datetime import datetime
from pprint import pprint
from typing import Any, Dict, Optional

from examples import ExampleTaskHandler
from sqlalchemy import text

from src.machine import PersistentStateMachine
from src.repository import PersistenceManager, RepositoryConfig, new_persistence_manager
from src.states import with_execution_context
from tests.state_machine.machine.test_persistent_statemachine import TaskContext


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


async def demo_1_simple_greeting(persistence_manager: PersistenceManager):
    """Demo 1: Simple greeting handler."""
    print("\n" + "=" * 60)
    print("Demo 1: Simple Greeting")
    print("=" * 60)

    # Create Task context
    task_context = TaskContext()

    # Register greeting handler
    async def greet_handler(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("👋 Greeting handler called")
        if isinstance(input_data, dict):
            input_data["greeting"] = f"Hello, {input_data.get('name', 'World')}!"
            input_data["timestamp"] = datetime.now().isoformat()
            input_data["processed"] = True
        return input_data

    task_context.register_handler("greet", greet_handler)

    # Create state machine
    definition = """
    {
      "StartAt": "GreetUser",
      "States": {
        "GreetUser": {
          "Type": "Task",
          "Resource": "greet",
          "End": "true"
        }
      }
    }
    """
    input_data = {"name": "Python User", "type": "demo"}
    # Create task execution context
    task_exec_context = with_execution_context({}, task_context)

    psm = PersistentStateMachine.create_from_json(
        definition,
        persistence_manager=persistence_manager,
        state_machine_id="test-sm-4",
    )

    execution = await psm.execute(
        input_data,
        task_exec_context=task_exec_context,
        execution_name="GreetUser-exec-name-1",
        execution_id="GreetUser-exec-id-1",
    )

    # Execute
    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")
    history = await psm.get_execution_history(execution_id=execution.id)
    pprint(history)


async def demo_2_processing_with_parameters(persistence_manager: PersistenceManager):
    """Demo 2: Processing with parameters."""
    print("\n" + "=" * 60)
    print("Demo 2: Processing with Parameters")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register processor
    async def process_handler(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("⚙️  Processing handler called")
        if isinstance(input_data, dict):
            input_data["processed"] = True
            input_data["stage"] = "completed"
            input_data["processing_time"] = datetime.now().isoformat()
        return input_data

    exec_ctx.register_handler("process", process_handler)

    # Create state machine with parameters
    definition = """
    {
  "StartAt": "ProcessData",
  "States": {
    "ProcessData": {
      "Type": "Task",
      "Resource": "process",
      "Parameters": {
        "values.$": "$.data.values",
        "source.$": "$.data.source",
        "extra": "parameter"
      },
      "End": "true"
    }
  }
}
    """
    # Execute
    input_data = {
        "data": {"values": [1, 2, 3], "source": "demo"},
        "metadata": "ignored",
    }
    task_exec_context = with_execution_context({}, exec_ctx)

    psm = PersistentStateMachine.create_from_json(
        definition,
        persistence_manager=persistence_manager,
        state_machine_id="test-sm-4",
    )

    execution = await psm.execute(
        input_data,
        task_exec_context=task_exec_context,
        execution_name="GreetUser-exec-name-1",
        execution_id="GreetUser-exec-id-1",
    )

    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")
    history = await psm.get_execution_history(execution_id=execution.id)
    pprint(history)


async def demo_3_validation_success(persistence_manager: PersistenceManager):
    """Demo 3: Validation success case."""
    print("\n" + "=" * 60)
    print("Demo 3: Validation Success")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register validator
    async def validate_handler(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("✅ Validation handler called")
        if not isinstance(input_data, dict):
            raise ValueError("validation failed: invalid input type")

        if not input_data.get("required"):
            raise ValueError("validation failed: required field missing")

        input_data["valid"] = True
        return input_data

    exec_ctx.register_handler("validate", validate_handler)

    # Create state machine
    definition = """
    {
  "StartAt": "ValidateInput",
  "States": {
    "ValidateInput": {
      "Type": "Task",
      "Resource": "validate",
      "End": "true"
    }
  }
}
    """
    # input data
    input_data = {"required": True, "optional": "value"}

    # task context
    task_exec_context = with_execution_context({}, exec_ctx)

    # Execute
    psm = PersistentStateMachine.create_from_json(
        definition,
        persistence_manager=persistence_manager,
        state_machine_id="test-sm-3",
    )

    execution = await psm.execute(
        input_data,
        task_exec_context=task_exec_context,
        execution_name="Validate-exec-name-1",
        execution_id="Validate-exec-id-1",
    )

    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")
    history = await psm.get_execution_history(execution_id=execution.id)
    pprint(history)


async def demo_4_validation_failure(persistence_manager: PersistenceManager):
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
    ):
        print("✅ Validation handler called")
        print(f"resource {resource}")
        print(f"input_data {input_data}")
        print(f"parameters {parameters}")

        if not input_data.get("required"):
            raise ValueError("validation failed: required field missing")
        return input_data

    exec_ctx.register_handler(
        "validate",
        ExampleTaskHandler(execute_func=validate_handler, execute_with_timeout_func=validate_handler),
    )

    # Create state machine with error handling

    definition = """
    {
  "StartAt": "ValidateInput",
  "States": {
    "ValidateInput": {
      "Type": "Task",
      "Resource": "validate",
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ],
      "End": "true"
    },
    "HandleError": {
      "Type": "Pass",
      "Result": "Error handled gracefully",
      "End": "true"
    }
  }
}
    """

    try:
        task_exec_context = with_execution_context({}, exec_ctx)
        # Execute with missing required field
        input_data = {"optional": "value"}
        psm = PersistentStateMachine.create_from_json(
            definition,
            persistence_manager=persistence_manager,
            state_machine_id="test-demo-4",
        )

        execution = await psm.execute(
            input_data,
            task_exec_context=task_exec_context,
            execution_name="Validate-fail-exec-name-1",
            execution_id="Validate-fail-exec-id-1",
        )

        print(f"Status: {execution.status}")
        print(f"Output: {execution.output}")
        history = await psm.get_execution_history(execution_id=execution.id)
        pprint(history)
    except ValueError as ve:
        print(f"ValueError as {ve}")


def setup_persistent_manager() -> PersistenceManager:
    """Set up test database connection."""
    # Get connection string from environment or use default
    conn_url = os.getenv(
        "POSTGRES_TEST_URL",
        "postgresql://postgres:postgres@localhost:5432/statemachine_demo",
    )

    config = RepositoryConfig(
        strategy="postgres",
        connection_url=conn_url,
        options={
            "max_open_conns": 10,
            "max_overflow": 5,
            "pool_timeout": 30,
            "conn_max_lifetime": 300,
            "echo": False,
        },
    )

    try:
        persistence_manager = new_persistence_manager(config=config)
        return persistence_manager
    except Exception as e:
        raise EnvironmentError(f"PostgreSQL not available: {e}")


async def demo_7_complex_workflow(persistence_manager):
    """Demo 7: Complex workflow with multiple patterns."""
    print("\n" + "=" * 60)
    print("Demo 7: Complex Workflow")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register handlers
    async def fetch_data(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("📥 Fetching data...")
        await asyncio.sleep(0.2)
        return {"data": [1, 2, 3, 4, 5], "source": "database"}

    async def transform_data(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("🔄 Transforming data...")
        await asyncio.sleep(0.3)
        data = input_data.get("data", [])
        return {"transformed": [x * 2 for x in data], "count": len(data)}

    async def validate_result(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("✅ Validating result...")
        if input_data.get("count", 0) > 0:
            return {"valid": True, "data": input_data}
        raise ValueError("No data to process")

    async def save_result(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("💾 Saving result...")
        await asyncio.sleep(0.2)
        return {"saved": True, "id": "result-123"}

    exec_ctx.register_handler("fetch", fetch_data)
    exec_ctx.register_handler("transform", transform_data)
    exec_ctx.register_handler("validate", validate_result)
    exec_ctx.register_handler("save", save_result)

    # Create complex workflow
    definition = """
    {
  "StartAt": "FetchData",
  "States": {
    "FetchData": {
      "Type": "Task",
      "Resource": "fetch",
      "Next": "TransformData"
    },
    "TransformData": {
      "Type": "Task",
      "Resource": "transform",
      "Next": "ValidateResult"
    },
    "ValidateResult": {
      "Type": "Task",
      "Resource": "validate",
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ],
      "Next": "SaveResult"
    },
    "SaveResult": {
      "Type": "Task",
      "Resource": "save",
      "End": "true"
    },
    "HandleError": {
      "Type": "Pass",
      "Result": "Error in validation",
      "End": "true"
    }
  }
}
    """

    task_exec_context = with_execution_context({}, exec_ctx)

    psm = PersistentStateMachine.create_from_json(
        definition,
        persistence_manager=persistence_manager,
        state_machine_id="test-demo-4",
    )
    # Execute
    start = datetime.now()
    execution = await psm.execute(
        input_data={},
        task_exec_context=task_exec_context,
        execution_name="Validate-fail-exec-name-1",
        execution_id="Validate-fail-exec-id-1",
    )
    elapsed = datetime.now() - start

    print(f"\nStatus: {execution.status}")
    print(f"Total time: {elapsed.microseconds/1000: .2f} milli-seconds")
    print(f"States executed: {len(execution.history)}")
    print(f"Final output: {execution.output}")

    # Show execution history
    history = await psm.get_execution_history(execution_id=execution.id)
    pprint(history)


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("AWS State Machine - Execution Flow Demo")
    print("=" * 60)

    persistence_manager = setup_persistent_manager()
    persistence_manager.initialize()

    try:
        await demo_1_simple_greeting(persistence_manager)
        await demo_2_processing_with_parameters(persistence_manager)
        await demo_3_validation_success(persistence_manager)
        await demo_4_validation_failure(persistence_manager)
        await demo_5_task_with_retry(persistence_manager)
        await demo_6_parallel_execution(persistence_manager)
        await demo_7_complex_workflow(persistence_manager)

        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        cleanup_data(persistence_manager)
        persistence_manager.close()


async def demo_5_task_with_retry(persistence_manager: PersistenceManager):
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
    ):
        print(f"🎲 Flaky handler called (attempt {call_count['count']})")

        print(f"resource {resource}")
        print(f"input_data {input_data}")
        print(f"parameters {parameters}")

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
    definition = """
    {
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
                        "BackoffRate": 1.5
                    }
                ],
                "End": "true"
            }
        }
    }
    """

    task_exec_context = with_execution_context({}, exec_ctx)

    # Execute

    psm = PersistentStateMachine.create_from_json(
        json_str=definition,
        persistence_manager=persistence_manager,
        state_machine_id="test-sm-5",
    )

    start = datetime.now()
    execution = await psm.execute(
        {},
        task_exec_context=task_exec_context,
        execution_name="Validate-exec-name-1",
        execution_id="Validate-exec-id-1",
    )
    elapsed = datetime.now() - start

    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")
    print(f"Total attempts: {call_count['count']}")
    print(f"Time taken: {elapsed.seconds: .2f} seconds (including retry delays)")

    history = await psm.get_execution_history(execution_id=execution.id)
    pprint(history)


async def demo_6_parallel_execution(persistence_manager: PersistenceManager):
    """Demo 6: Parallel execution."""
    print("\n" + "=" * 60)
    print("Demo 6: Parallel Execution")
    print("=" * 60)

    exec_ctx = DemoExecutionContext()

    # Register parallel handlers
    async def task_a(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("🔵 Task A starting...")
        await asyncio.sleep(0.5)
        print("🔵 Task A completed")
        return {"task": "A", "result": "success"}

    async def task_b(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("🟢 Task B starting...")
        await asyncio.sleep(0.3)
        print("🟢 Task B completed")
        return {"task": "B", "result": "success"}

    async def task_c(
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        print("🟡 Task C starting...")
        await asyncio.sleep(0.4)
        print("🟡 Task C completed")
        return {"task": "C", "result": "success"}

    exec_ctx.register_handler("taskA", task_a)
    exec_ctx.register_handler("taskB", task_b)
    exec_ctx.register_handler("taskC", task_c)

    # Create parallel state machine
    definition = """
    {
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
                                "End": "true"
                            }
                        }
                    },
                    {
                        "StartAt": "BranchB",
                        "States": {
                            "BranchB": {
                                "Type": "Task",
                                "Resource": "taskB",
                                "End": "true"
                            }
                        }
                    },
                    {
                        "StartAt": "BranchC",
                        "States": {
                            "BranchC": {
                                "Type": "Task",
                                "Resource": "taskC",
                                "End": "true"
                            }
                        }
                    }
                ],
                "End": "true"
            }
        }
    }
    """

    try:
        task_context = with_execution_context({}, exec_ctx)
        psm = PersistentStateMachine.create_from_json(
            definition,
            persistence_manager=persistence_manager,
            state_machine_id="test-demo-6",
        )
        # Execute
        start = datetime.now()
        execution = await psm.execute(
            {},
            task_exec_context=task_context,
            execution_name="parallel-success-exec-name-1",
            execution_id="parallel-success-exec-id-1",
        )
        elapsed = datetime.now() - start

        print(f"\nStatus: {execution.status}")
        print(f"Parallel execution time: {elapsed.microseconds/1000: .2f} milli-seconds")
        print(f"Results: {execution.output}")
        history = await psm.get_execution_history(execution_id=execution.id)
        pprint(history)

    except ValueError as ve:
        print(f"ValueError as {ve}")


def cleanup_data(persistence_manager):
    with persistence_manager.repository.get_session() as session:
        # Truncate in FK-safe order
        session.execute(text("TRUNCATE TABLE state_history CASCADE"))
        session.execute(text("TRUNCATE TABLE executions CASCADE"))
        # session.execute(text("TRUNCATE TABLE execution_statistics CASCADE"))


if __name__ == "__main__":
    asyncio.run(main())
