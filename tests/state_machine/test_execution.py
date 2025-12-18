"""
Tests for Execution implementation.

Based on execution_test.go
"""

from datetime import datetime, timedelta

import pytest

from state_machine.execution import Execution, StateHistory, _generate_execution_id


class TestExecution:

    def test_new_context(self):
        """Test creating new execution context."""
        exec_ctx = Execution.new_context("test-exec", "StartState", {"key": "value"})

        assert exec_ctx is not None
        assert exec_ctx.name == "test-exec"
        assert exec_ctx.current_state == "StartState"
        assert exec_ctx.input == {"key": "value"}
        assert exec_ctx.status == "RUNNING"
        assert exec_ctx.id.startswith("exec-")
        assert len(exec_ctx.history) == 0

    def test_new_with_custom_id(self):
        """Test creating execution with custom ID."""
        exec_ctx = Execution.new(id="custom-id", name="test", input_data=None)

        assert exec_ctx.id == "custom-id"
        assert exec_ctx.name == "test"

    def test_new_generates_id(self):
        """Test that new() generates ID if not provided."""
        exec_ctx = Execution.new(name="test", input_data=None)

        assert exec_ctx.id is not None
        assert exec_ctx.id.startswith("exec-")

    def test_add_state_history(self):
        """Test adding state history."""
        exec_ctx = Execution.new_context("test", "Start", None)

        exec_ctx.add_state_history("State1", {"in": "data"}, {"out": "result"})
        exec_ctx.add_state_history("State2", {"in2": "data2"}, {"out2": "result2"})

        assert len(exec_ctx.history) == 2
        assert exec_ctx.history[0].state_name == "State1"
        assert exec_ctx.history[0].input == {"in": "data"}
        assert exec_ctx.history[0].output == {"out": "result"}
        assert exec_ctx.history[0].status == "SUCCEEDED"
        assert exec_ctx.history[0].sequence_number == 0

        assert exec_ctx.history[1].state_name == "State2"
        assert exec_ctx.history[1].sequence_number == 1

    def test_get_last_state(self):
        """Test getting last executed state."""
        exec_ctx = Execution.new_context("test", "Start", None)

        exec_ctx.add_state_history("State1", None, "result1")
        exec_ctx.add_state_history("State2", None, "result2")

        last = exec_ctx.get_last_state()

        assert last is not None
        assert last.state_name == "State2"
        assert last.output == "result2"

    def test_get_last_state_no_history(self):
        """Test getting last state when no history exists."""
        exec_ctx = Execution.new_context("test", "Start", None)

        with pytest.raises(ValueError, match="No history available"):
            exec_ctx.get_last_state()

    def test_get_state_history(self):
        """Test getting history for specific state."""
        exec_ctx = Execution.new_context("test", "Start", None)

        exec_ctx.add_state_history("State1", None, "result1")
        exec_ctx.add_state_history("State2", None, "result2")
        exec_ctx.add_state_history("State1", None, "result3")

        history = exec_ctx.get_state_history("State1")

        assert len(history) == 2
        assert history[0].output == "result1"
        assert history[1].output == "result3"

    def test_get_state_history_not_found(self):
        """Test getting history for non-existent state."""
        exec_ctx = Execution.new_context("test", "Start", None)

        exec_ctx.add_state_history("State1", None, "result1")

        history = exec_ctx.get_state_history("NonExistent")

        assert len(history) == 0

    def test_get_duration(self):
        """Test calculating execution duration."""
        exec_ctx = Execution.new_context("test", "Start", None)

        # Execution is still running
        duration = exec_ctx.get_duration()
        assert duration >= 0

        # Complete execution
        exec_ctx.end_time = exec_ctx.start_time + timedelta(seconds=5)
        duration = exec_ctx.get_duration()
        assert duration == pytest.approx(5.0, rel=0.1)

    def test_is_complete(self):
        """Test checking if execution is complete."""
        exec_ctx = Execution.new_context("test", "Start", None)

        # Initially running
        assert not exec_ctx.is_complete()

        # Test each terminal status
        exec_ctx.status = "SUCCEEDED"
        assert exec_ctx.is_complete()

        exec_ctx.status = "FAILED"
        assert exec_ctx.is_complete()

        exec_ctx.status = "TIMED_OUT"
        assert exec_ctx.is_complete()

        exec_ctx.status = "ABORTED"
        assert exec_ctx.is_complete()

        # Back to running
        exec_ctx.status = "RUNNING"
        assert not exec_ctx.is_complete()

    def test_to_dict(self):
        """Test converting execution to dictionary."""
        exec_ctx = Execution.new_context("test-exec", "Start", {"input": "data"})

        exec_ctx.add_state_history("State1", {"input": "data"}, {"output": "result"})
        exec_ctx.status = "SUCCEEDED"
        exec_ctx.end_time = datetime.now()
        exec_ctx.output = {"final": "output"}

        result = exec_ctx.to_dict()

        assert result["id"] == exec_ctx.id
        assert result["name"] == "test-exec"
        assert result["status"] == "SUCCEEDED"
        assert "startTime" in result
        assert "endTime" in result
        assert result["input"] == {"input": "data"}
        assert result["output"] == {"final": "output"}
        assert "history" in result
        assert len(result["history"]) == 1

    def test_to_dict_with_error(self):
        """Test converting execution with error to dictionary."""
        exec_ctx = Execution.new_context("test", "Start", None)
        exec_ctx.error = ValueError("Test error")
        exec_ctx.status = "FAILED"

        result = exec_ctx.to_dict()

        assert "error" in result
        assert "Test error" in result["error"]

    def test_state_history_to_dict(self):
        """Test converting state history to dictionary."""
        history = StateHistory(
            state_name="TestState",
            state_type="Pass",
            status="SUCCEEDED",
            input={"in": "data"},
            output={"out": "result"},
            retry_count=2,
        )

        result = history.to_dict()

        assert result["stateName"] == "TestState"
        assert result["stateType"] == "Pass"
        assert result["status"] == "SUCCEEDED"
        assert result["input"] == {"in": "data"}
        assert result["output"] == {"out": "result"}
        assert result["retryCount"] == 2
        assert "timestamp" in result

    def test_generate_execution_id(self):
        """Test generating unique execution IDs."""
        id1 = _generate_execution_id()
        id2 = _generate_execution_id()

        assert id1.startswith("exec-")
        assert id2.startswith("exec-")
        assert id1 != id2  # Should be unique

    def test_execution_str(self):
        """Test string representation of execution."""
        exec_ctx = Execution.new_context("test-name", "Start", None)
        exec_ctx.add_state_history("State1", None, None)

        str_repr = str(exec_ctx)

        assert "test-name" in str_repr
        assert exec_ctx.id in str_repr
        assert "RUNNING" in str_repr

    def test_state_history_with_error(self):
        """Test state history with error."""
        error = RuntimeError("Task failed")
        history = StateHistory(
            state_name="FailedState",
            status="FAILED",
            error=error,
        )

        result = history.to_dict()

        assert result["status"] == "FAILED"
        assert "error" in result
        assert "Task failed" in result["error"]

    def test_execution_complete_flow(self):
        """Test complete execution flow."""
        # Create execution
        exec_ctx = Execution.new_context("complete-test", "Start", {"initial": "data"})

        assert exec_ctx.status == "RUNNING"
        assert not exec_ctx.is_complete()

        # Execute some states
        exec_ctx.add_state_history("State1", {"initial": "data"}, {"step1": "result"})
        exec_ctx.add_state_history("State2", {"step1": "result"}, {"step2": "result"})
        exec_ctx.add_state_history("State3", {"step2": "result"}, {"final": "output"})

        # Complete execution
        exec_ctx.status = "SUCCEEDED"
        exec_ctx.end_time = datetime.now()
        exec_ctx.output = {"final": "output"}

        assert exec_ctx.is_complete()
        assert len(exec_ctx.history) == 3

        # Verify duration
        duration = exec_ctx.get_duration()
        assert duration >= 0

        # Verify last state
        last = exec_ctx.get_last_state()
        assert last.state_name == "State3"

        # Convert to dict
        result = exec_ctx.to_dict()
        assert result["status"] == "SUCCEEDED"
        assert len(result["history"]) == 3

    def test_execution_metadata(self):
        """Test execution metadata fields."""
        exec_ctx = Execution.new(
            id="test-123",
            name="metadata-test",
            input_data={"test": "data"},
        )

        exec_ctx.state_machine_id = "sm-456"

        result = exec_ctx.to_dict()

        assert result["stateMachineId"] == "sm-456"
        assert result["id"] == "test-123"
        assert result["name"] == "metadata-test"
