# pkg/statemachine/test_persistent_statemachine.py
"""Tests for persistent state machine implementation."""
import datetime
import os
from typing import Any, Dict, Optional

import pytest
from sqlalchemy import text

from src.machine import PersistentStateMachine
from src.repository import (
    ExecutionFilter,
    PersistenceManager,
    RepositoryConfig,
    new_persistence_manager,
)
from src.states import with_execution_context


# Mock execution context
class TaskContext:
    """Demo execution context for testing handlers."""

    def __init__(self):
        self.handlers = {}

    def register_handler(self, name, handler):
        """Register a task handler."""
        self.handlers[name] = handler

    def get_task_handler(self, resource):
        """Get a task handler by resource."""
        return self.handlers.get(resource)


class TestPersistentStateMachine():
    persistenceManager: Optional[PersistenceManager] = None

    def setup_class(cls):
        """Set up test database connection."""
        # Get connection string from environment or use default
        conn_url = os.getenv(
            "POSTGRES_TEST_URL",
            "postgresql://postgres:postgres@localhost:5432/statemachine_test_py_sql",
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
            cls.persistenceManager = new_persistence_manager(config=config)
            cls.persistenceManager.initialize()
        except Exception as e:
            raise pytest.skip(f"PostgreSQL not available: {e}")

    def teardown_class(cls):
        """Clean up database connection."""
        if cls.persistenceManager:
            cls.persistenceManager.close()

    def setup_method(cls):
        cls.cleanup_data()

    def teardown_method(cls):
        cls.cleanup_data()

    def cleanup_data(cls):
        """Remove all test data."""
        if cls.persistenceManager:
            with cls.persistenceManager.repository.get_session() as session:
                # Truncate in FK-safe order
                session.execute(text("TRUNCATE TABLE state_history CASCADE"))
                session.execute(text("TRUNCATE TABLE executions CASCADE"))
                session.execute(text("TRUNCATE TABLE execution_statistics CASCADE"))

    @pytest.mark.asyncio
    async def test_execute_simple_passthrough(self):
        """Test executing simple pass-through state machine."""
        definition = """{
            "StartAt": "FirstState",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""
        psm = PersistentStateMachine.create_from_json(json_str=definition,
                                                      persistence_manager=self.persistenceManager,
                                                      state_machine_id="test-sm-1")

        input_data = {"key": "value"}

        exec_ctx = await psm.execute(input_data)

        execution_record = psm.get_persistence_manager().get_execution(exec_ctx.id)

        assert exec_ctx is not None
        assert exec_ctx.status == "SUCCEEDED"
        assert execution_record.execution_id == exec_ctx.id
        assert exec_ctx.current_state == "FirstState"
        assert execution_record.current_state == "FirstState"
        assert exec_ctx.output is not None

        executions = self.persistenceManager.repository.list_executions(ExecutionFilter(limit=100, offset=0))
        assert len(executions) >= 1

    @pytest.mark.asyncio
    async def test_execute_multiple_states(self):
        """Test executing state machine with multiple states."""
        definition = """{
                "StartAt": "FirstState",
                "States": {
                    "FirstState": {
                        "Type": "Pass",
                        "Result": "step1",
                        "Next": "SecondState"
                    },
                    "SecondState": {
                        "Type": "Pass",
                        "Result": "step2",
                        "End": true
                    }
                }
            }"""

        sm = PersistentStateMachine.create_from_json(definition, persistence_manager=self.persistenceManager,
                                                     state_machine_id="test-sm-2")
        input_data = "initial"

        exec_ctx = await sm.execute(input_data)

        assert exec_ctx.status == "SUCCEEDED"
        assert exec_ctx.output == "step2"
        assert len(exec_ctx.history) == 2

        executions = self.persistenceManager.repository.list_executions(ExecutionFilter(limit=100, offset=0))
        assert len(executions) >= 1

        state_history = self.persistenceManager.repository.get_state_history(executions[0].execution_id)
        assert len(state_history) == 2

    @pytest.mark.asyncio
    async def test_execute_with_fail(self):
        """Test executing state machine that fails."""
        definition = """{
                "StartAt": "FailState",
                "States": {
                    "FailState": {
                        "Type": "Fail",
                        "Error": "CustomError",
                        "Cause": "Test failure"
                    }
                }
            }"""

        sm = PersistentStateMachine.create_from_json(definition, persistence_manager=self.persistenceManager,
                                                     state_machine_id="test-sm-3")
        input_data = "test"

        exec_ctx = await sm.execute(input_data)

        assert exec_ctx is not None
        assert exec_ctx.status == "FAILED"
        assert exec_ctx.error is not None

        executions = self.persistenceManager.repository.list_executions(ExecutionFilter(limit=100, offset=0))
        assert len(executions) >= 1

        execution = executions[0]
        assert execution.current_state == "FailState"

    @pytest.mark.asyncio
    async def test_with_task_handler_success(self):
        # Create Task context
        task_context = TaskContext()

        # Register greeting handler
        async def test_greet_handler(resource: str,
                                     input_data: Any,
                                     parameters: Optional[Dict[str, Any]] = None,
                                     ):
            print("Test Greeting handler called")
            if isinstance(input_data, dict):
                input_data["greeting"] = f"Hello, {input_data.get('name', 'World')}!"
                input_data["timestamp"] = datetime.now().isoformat()
                input_data["processed"] = True
            return input_data

        task_context.register_handler("greet", test_greet_handler)

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

        psm = PersistentStateMachine.create_from_json(definition, persistence_manager=self.persistenceManager,
                                                      state_machine_id="test-sm-4")
        input_data = "test"

        # Create context
        task_exec_context = with_execution_context({}, task_context)

        exec_ctx = await psm.execute(input_data, task_exec_context=task_exec_context,
                                     execution_name="GreetUser-exec-name-1",
                                     execution_id="GreetUser-exec-id-1")

        assert exec_ctx is not None

        assert exec_ctx is not None
        assert exec_ctx.status == "SUCCEEDED"
        assert exec_ctx.error is None

        executions = self.persistenceManager.repository.list_executions(ExecutionFilter(limit=100, offset=0))
        assert len(executions) >= 1

        execution = executions[0]
        assert execution.current_state == "GreetUser"
