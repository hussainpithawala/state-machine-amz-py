"""
Tests for Executor implementation.

Based on executor_test.go
"""

from datetime import datetime

import pytest

from pkg.execution import Execution
from pkg.executor import BaseExecutor, ExecutionContextAdapter, StateRegistry


def test_state_registry_register_and_get_task_handler():
    """Test registering and retrieving task handlers."""
    registry = StateRegistry()

    called = False

    def handler(input_data):
        nonlocal called
        called = True
        return input_data

    registry.register_task_handler("resource://x", handler)

    got = registry.get_task_handler("resource://x")
    assert got is not None

    result = got("in")
    assert result == "in"
    assert called

    missing = registry.get_task_handler("resource://missing")
    assert missing is None


def test_new_base_executor_initializes_maps_and_registry():
    """Test that BaseExecutor initializes properly."""
    executor = BaseExecutor()

    assert executor is not None
    assert executor.executions is not None
    assert executor.registry is not None
    assert executor.registry.task_handlers is not None


def test_base_executor_get_status_not_found():
    """Test getting status for non-existent execution."""
    executor = BaseExecutor()

    with pytest.raises(ValueError, match="not found"):
        executor.get_status("does-not-exist")


def test_base_executor_get_status_found():
    """Test getting status for existing execution."""
    executor = BaseExecutor()

    exec_ctx = Execution(
        id="exec-1",
        name="n1",
        status="RUNNING",
        start_time=datetime.now(),
    )
    executor.executions[exec_ctx.id] = exec_ctx

    got = executor.get_status("exec-1")
    assert got is exec_ctx


@pytest.mark.asyncio
async def test_base_executor_stop_nil_execution():
    """Test stopping with None execution."""
    executor = BaseExecutor()

    with pytest.raises(ValueError, match="cannot be None"):
        await executor.stop(None)


@pytest.mark.asyncio
async def test_base_executor_stop_sets_aborted():
    """Test that stop sets execution to ABORTED."""
    executor = BaseExecutor()

    exec_ctx = Execution(
        id="exec-1",
        status="RUNNING",
        name="test",
        start_time=datetime.now(),
    )
    executor.executions[exec_ctx.id] = exec_ctx

    before = datetime.now()
    await executor.stop(exec_ctx)
    after = datetime.now()

    assert exec_ctx.status == "ABORTED"
    assert exec_ctx.end_time is not None
    assert before <= exec_ctx.end_time <= after

    # Should be removed from active executions
    assert "exec-1" not in executor.executions


def test_base_executor_list_executions():
    """Test listing executions."""
    executor = BaseExecutor()

    assert len(executor.list_executions()) == 0

    exec1 = Execution(id="exec-1", name="e1", status="RUNNING")
    exec2 = Execution(id="exec-2", name="e2", status="SUCCEEDED")
    executor.executions[exec1.id] = exec1
    executor.executions[exec2.id] = exec2

    executions = executor.list_executions()
    assert len(executions) == 2

    # Check membership (order not guaranteed)
    ids = {e.id for e in executions}
    assert "exec-1" in ids
    assert "exec-2" in ids


def test_base_executor_register_go_function():
    """Test registering a Python function as task handler."""
    executor = BaseExecutor()

    def handler(input_data):
        return "ok"

    executor.register_go_function("MyFn", handler)

    arn = "arn:aws:states:::lambda:function:MyFn"
    got = executor.registry.get_task_handler(arn)
    assert got is not None

    result = got(None)
    assert result == "ok"


@pytest.mark.asyncio
async def test_base_executor_execute_go_task():
    """Test executing a Go/Python task."""
    executor = BaseExecutor()

    result = await executor.execute_go_task(None, {"k": "v"})
    assert result == {"k": "v"}


def test_execution_context_adapter_get_task_handler():
    """Test ExecutionContextAdapter getting task handlers."""
    executor = BaseExecutor()

    def handler(input_data):
        return "result"

    executor.registry.register_task_handler("resource://test", handler)

    adapter = ExecutionContextAdapter(executor)
    got = adapter.get_task_handler("resource://test")

    assert got is not None
    assert got(None) == "result"


def test_execution_context_adapter_none_executor():
    """Test adapter with None executor."""
    adapter = ExecutionContextAdapter(None)
    got = adapter.get_task_handler("resource://test")

    assert got is None


def test_execution_context_adapter_missing_handler():
    """Test adapter with missing handler."""
    executor = BaseExecutor()
    adapter = ExecutionContextAdapter(executor)

    got = adapter.get_task_handler("resource://missing")
    assert got is None


def test_state_registry_multiple_handlers():
    """Test registering multiple handlers."""
    registry = StateRegistry()

    def handler1(input_data):
        return "handler1"

    def handler2(input_data):
        return "handler2"

    registry.register_task_handler("resource://1", handler1)
    registry.register_task_handler("resource://2", handler2)

    got1 = registry.get_task_handler("resource://1")
    got2 = registry.get_task_handler("resource://2")

    assert got1(None) == "handler1"
    assert got2(None) == "handler2"


def test_state_registry_overwrite_handler():
    """Test overwriting existing handler."""
    registry = StateRegistry()

    def handler1(input_data):
        return "handler1"

    def handler2(input_data):
        return "handler2"

    registry.register_task_handler("resource://test", handler1)
    registry.register_task_handler("resource://test", handler2)

    got = registry.get_task_handler("resource://test")
    assert got(None) == "handler2"


@pytest.mark.asyncio
async def test_base_executor_execute_removes_completed():
    """Test that completed executions are removed."""
    from pkg.machine import StateMachine

    executor = BaseExecutor()

    definition = """{
        "StartAt": "FirstState",
        "States": {
            "FirstState": {
                "Type": "Pass",
                "End": true
            }
        }
    }"""

    sm = StateMachine.from_json(definition)
    exec_ctx = Execution.new_context("test", "FirstState", None)

    # Execute through executor
    result = await executor.execute(sm, exec_ctx)

    # Should be complete and removed from active executions
    assert result.is_complete()
    assert exec_ctx.id not in executor.executions
