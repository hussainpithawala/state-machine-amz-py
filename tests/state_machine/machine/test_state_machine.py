"""
Tests for StateMachine implementation.

Based on statemachine_test.go
"""

import json
from datetime import datetime, timedelta

import pytest

from state_machine.execution import Execution
from state_machine.machine.state_machine import StateMachine


class TestStateMachine():

    @pytest.mark.asyncio
    async def test_new_valid_definition(self):
        """Test creating state machine from valid JSON definition."""
        definition = """{
            "Comment": "A simple state machine",
            "StartAt": "FirstState",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "Result": "Hello World",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)

        assert sm is not None
        assert sm.comment == "A simple state machine"
        assert sm.start_at == "FirstState"
        assert len(sm.states) == 1

    def test_new_invalid_json(self):
        """Test creating state machine from invalid JSON."""
        definition = "{invalid json}"

        with pytest.raises(ValueError, match="Failed to parse JSON"):
            StateMachine.from_json(definition)

    def test_new_missing_start_at(self):
        """Test creating state machine without StartAt."""
        definition = """{
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        with pytest.raises(ValueError, match="StartAt is required"):
            StateMachine.from_json(definition)

    def test_new_missing_states(self):
        """Test creating state machine without States."""
        definition = """{
            "StartAt": "FirstState"
        }"""

        with pytest.raises(ValueError, match="States is required"):
            StateMachine.from_json(definition)

    def test_new_default_version(self):
        """Test that default version is set."""
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

        assert sm.version == "1.0"

    def test_new_custom_version(self):
        """Test creating state machine with custom version."""
        definition = """{
            "Version": "2.0",
            "StartAt": "FirstState",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)

        assert sm.version == "2.0"

    def test_get_start_at(self):
        """Test getting start state name."""
        definition = """{
            "StartAt": "MyStartState",
            "States": {
                "MyStartState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)
        start_at = sm.get_start_at()

        assert start_at == "MyStartState"

    def test_get_state_exists(self):
        """Test getting an existing state."""
        definition = """{
            "StartAt": "FirstState",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "End": true
                },
                "SecondState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)
        state = sm.get_state("FirstState")

        assert state is not None
        assert state.state_name == "FirstState"

    def test_get_state_not_found(self):
        """Test getting a non-existent state."""
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

        with pytest.raises(ValueError, match="not found"):
            sm.get_state("NonExistentState")

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

        sm = StateMachine.from_json(definition)
        input_data = {"key": "value"}

        exec_ctx = await sm.execute(input_data)

        assert exec_ctx is not None
        assert exec_ctx.status == "SUCCEEDED"
        assert exec_ctx.current_state == "FirstState"
        assert exec_ctx.output is not None

    @pytest.mark.asyncio
    async def test_execute_with_result(self):
        """Test executing state machine with result."""
        definition = """{
            "StartAt": "FirstState",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "Result": "Hello World",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)
        input_data = "ignored"

        exec_ctx = await sm.execute(input_data)

        assert exec_ctx.status == "SUCCEEDED"
        assert exec_ctx.output == "Hello World"

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

        sm = StateMachine.from_json(definition)
        input_data = "initial"

        exec_ctx = await sm.execute(input_data)

        assert exec_ctx.status == "SUCCEEDED"
        assert exec_ctx.output == "step2"
        assert len(exec_ctx.history) == 2

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

        sm = StateMachine.from_json(definition)
        input_data = "test"

        exec_ctx = await sm.execute(input_data)

        assert exec_ctx is not None
        assert exec_ctx.status == "FAILED"
        assert exec_ctx.error is not None

    @pytest.mark.asyncio
    async def test_execute_with_execution_name(self):
        """Test executing with custom execution name."""
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
        input_data = "test"

        exec_ctx = await sm.execute(input_data, execution_name="custom-execution")

        assert exec_ctx.name == "custom-execution"

    def test_get_execution_summary(self):
        """Test getting execution summary."""
        definition = """{
            "Comment": "Test state machine",
            "Version": "1.0",
            "TimeoutSeconds": 300,
            "StartAt": "FirstState",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "Next": "SecondState"
                },
                "SecondState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)
        summary = sm.get_execution_summary()

        assert summary is not None
        assert summary["startAt"] == "FirstState"
        assert summary["statesCount"] == 2
        assert summary["version"] == "1.0"

        state_types = summary["stateTypes"]
        assert state_types["Pass"] == 2

    def test_is_timeout(self):
        """Test timeout checking."""
        definition = """{
            "TimeoutSeconds": 1,
            "StartAt": "FirstState",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)

        # Test within timeout
        start_time = datetime.now()
        is_timeout = sm.is_timeout(start_time)
        assert not is_timeout

        # Test past timeout
        past_time = datetime.now() - timedelta(seconds=2)
        is_timeout = sm.is_timeout(past_time)
        assert is_timeout

    def test_is_timeout_no_timeout(self):
        """Test that no timeout is set."""
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

        # Should never timeout if TimeoutSeconds is not set
        past_time = datetime.now() - timedelta(seconds=10)
        is_timeout = sm.is_timeout(past_time)
        assert not is_timeout

    def test_to_json(self):
        """Test converting state machine to JSON."""
        definition = """{
            "Comment": "Test machine",
            "Version": "1.0",
            "StartAt": "FirstState",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)
        json_str = sm.to_json()

        assert json_str is not None

        result = json.loads(json_str)

        # Verify exported fields are included
        assert result["Comment"] == "Test machine"
        assert result["StartAt"] == "FirstState"
        assert "States" in result

    def test_validate(self):
        """Test state machine validation."""
        # Valid definition
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
        # Should not raise

    def test_validate_missing_start_at(self):
        """Test validation with missing StartAt."""
        definition = """{
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        with pytest.raises(ValueError):
            StateMachine.from_json(definition)

    def test_validate_invalid_start_at_reference(self):
        """Test validation with invalid StartAt reference."""
        definition = """{
            "StartAt": "NonExistent",
            "States": {
                "FirstState": {
                    "Type": "Pass",
                    "End": true
                }
            }
        }"""

        with pytest.raises(ValueError, match="not found"):
            StateMachine.from_json(definition)

    @pytest.mark.asyncio
    async def test_execute_state_history(self):
        """Test that state history is recorded."""
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
                    "Next": "ThirdState"
                },
                "ThirdState": {
                    "Type": "Pass",
                    "Result": "step3",
                    "End": true
                }
            }
        }"""

        sm = StateMachine.from_json(definition)
        input_data = "initial"

        exec_ctx = await sm.execute(input_data)

        assert len(exec_ctx.history) == 3
        assert exec_ctx.history[0].state_name == "FirstState"
        assert exec_ctx.history[1].state_name == "SecondState"
        assert exec_ctx.history[2].state_name == "ThirdState"

    @pytest.mark.asyncio
    async def test_execute_execution_metadata(self):
        """Test that execution metadata is captured."""
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
        input_data = "test"

        exec_ctx = await sm.execute(input_data)

        assert exec_ctx.start_time is not None
        assert exec_ctx.end_time is not None
        assert exec_ctx.end_time > exec_ctx.start_time
        assert exec_ctx.current_state == "FirstState"

    def test_from_yaml(self):
        """Test creating state machine from YAML."""
        definition = """
    Comment: A simple state machine
    StartAt: FirstState
    States:
      FirstState:
        Type: Pass
        Result: Hello World
        End: true
    """

        sm = StateMachine.from_yaml(definition)

        assert sm is not None
        assert sm.comment == "A simple state machine"
        assert sm.start_at == "FirstState"
        assert len(sm.states) == 1

    def test_to_yaml(self):
        """Test converting state machine to YAML."""
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
        yaml_str = sm.to_yaml()

        assert yaml_str is not None
        assert "StartAt: FirstState" in yaml_str
        assert "States:" in yaml_str
