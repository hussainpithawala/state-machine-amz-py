# pkg/repository/test_repository.py
"""Unit tests for repository manager."""
from datetime import datetime, timezone
from typing import List, Optional
from unittest.mock import patch

import pytest

from src.repository import PersistenceManager
from src.repository.types import (
    Execution,
    ExecutionFilter,
    ExecutionRecord,
    ExecutionStatus,
    Repository,
    RepositoryConfig,
    StateHistory,
    StateHistoryRecord,
    StateHistoryStatus,
    generate_history_id,
)


class FakeRepository(Repository):
    """Fake repository for testing."""

    def __init__(self):
        self.initialize_calls = 0
        self.close_calls = 0
        self.save_execution_calls = 0
        self.save_state_history_calls = 0
        self.last_saved_execution: Optional[ExecutionRecord] = None
        self.last_saved_state_history: Optional[StateHistoryRecord] = None
        self.get_execution_id: Optional[str] = None
        self.get_history_id: Optional[str] = None
        self.list_limit = 0
        self.list_offset = 0

    def initialize(self) -> None:
        self.initialize_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def health_check(self) -> None:
        pass

    def delete_execution(self, execution_id: str) -> None:
        pass

    def save_execution(self, execution: ExecutionRecord) -> None:
        self.save_execution_calls += 1
        self.last_saved_execution = execution

    def get_execution(self, execution_id: str) -> ExecutionRecord:
        self.get_execution_id = execution_id
        return ExecutionRecord(
            execution_id=execution_id,
            name="test",
            status="RUNNING",
            start_time=datetime.utcnow(),
            current_state="State1",
        )

    def save_state_history(self, history: StateHistoryRecord) -> None:
        self.save_state_history_calls += 1
        self.last_saved_state_history = history

    def get_state_history(self, execution_id: str) -> List[StateHistoryRecord]:
        self.get_history_id = execution_id
        return [
            StateHistoryRecord(
                id="hist-1",
                execution_id=execution_id,
                state_name="Any",
                state_type="Task",
                status="SUCCEEDED",
                start_time=datetime.utcnow(),
                sequence_number=0,
            )
        ]

    def list_executions(self, filter: ExecutionFilter) -> List[ExecutionRecord]:
        self.list_limit = filter.limit
        self.list_offset = filter.offset
        return [
            ExecutionRecord(
                execution_id="exec-1",
                name="test",
                status="RUNNING",
                start_time=datetime.utcnow(),
                current_state="State1",
            )
        ]

    def count_executions(self, filter: ExecutionFilter) -> int:
        return 1


class TestPersistenceManager:
    """Test cases for PersistenceManager."""

    def test_unsupported_strategy(self):
        """Test that unsupported strategy raises error."""
        config = RepositoryConfig(strategy="nope", connection_url="fake")
        with pytest.raises(ValueError) as ce:
            PersistenceManager(config)
        assert ce.value.args[0] == "unsupported persistence repository: nope"

    @pytest.mark.parametrize(
        "strategy, msg",
        [
            ("dynamodb", "DynamoDB repository not yet implemented"),
            ("redis", "Redis repository not yet implemented"),
            ("memory", "InMemory repository not yet implemented"),
        ],
    )
    def test_not_implemented_strategies(self, strategy, msg):
        """Test that not-yet-implemented strategies raise NotImplementedError."""
        config = RepositoryConfig(strategy=strategy, connection_url="fake")
        with pytest.raises(NotImplementedError) as ce:
            PersistenceManager(config)
        assert ce.value.args[0] == msg

    @patch("src.repository.repository.SQLAlchemyPostgresRepository")
    def test_initialize_and_close_delegates(self, mock_repo_class):
        """Test that initialize and close delegate to repository."""
        fake_repo = FakeRepository()
        mock_repo_class.return_value = fake_repo

        config = RepositoryConfig(strategy="postgres", connection_url="fake")
        pm = PersistenceManager(config)

        pm.initialize()
        pm.close()

        assert 1 == fake_repo.initialize_calls
        assert 1 == fake_repo.close_calls

    @patch("src.repository.repository.SQLAlchemyPostgresRepository")
    def test_save_execution_maps_fields_with_end_time_and_error(self, mock_repo_class):
        """Test that save_execution correctly maps fields including EndTime and Error."""
        fake_repo = FakeRepository()
        mock_repo_class.return_value = fake_repo

        config = RepositoryConfig(strategy="postgres", connection_url="fake")
        pm = PersistenceManager(config)

        start_time = datetime(2025, 1, 2, 3, 4, 5)
        end_time = datetime(2025, 1, 2, 3, 5, 0)

        exec = Execution(
            id="exec-123",
            state_machine_id="sm-1",
            name="my-exec",
            input={"k": "v"},
            output="out",
            status=ExecutionStatus.FAILED,
            start_time=start_time,
            end_time=end_time,
            current_state="SomeState",
            error=Exception("boom"),
        )

        pm.save_execution(exec)
        assert 1 == fake_repo.save_execution_calls

        rec = fake_repo.last_saved_execution
        assert "exec-123" == rec.execution_id
        assert exec.input == rec.input
        assert exec.output == rec.output
        assert "FAILED" == rec.status
        assert start_time == rec.start_time
        assert end_time == rec.end_time
        assert "SomeState" == rec.current_state
        assert rec.end_time is not None
        assert "boom" == rec.error

    @patch("src.repository.repository.SQLAlchemyPostgresRepository")
    def test_save_execution_does_not_set_end_time_or_error_when_missing(self, mock_repo_class):
        """Test that save_execution doesn't set EndTime or Error when they're missing."""
        fake_repo = FakeRepository()
        mock_repo_class.return_value = fake_repo

        config = RepositoryConfig(strategy="postgres", connection_url="fake")
        pm = PersistenceManager(config)

        exec = Execution(
            id="exec-1",
            state_machine_id="sm-1",
            name="n",
            status=ExecutionStatus.RUNNING,
            start_time=datetime(2025, 2, 3, 4, 5, 6),
            current_state="S1",
            # EndTime and Error are not set
        )

        pm.save_execution(exec)

        assert fake_repo.last_saved_execution is not None
        assert fake_repo.last_saved_execution.end_time is None
        assert fake_repo.last_saved_execution.error is None

    @patch("src.repository.repository.SQLAlchemyPostgresRepository")
    def test_save_state_history_maps_fields_with_end_time_and_error(self, mock_repo_class):
        """Test that save_state_history correctly maps fields including EndTime and Error."""
        fake_repo = FakeRepository()
        mock_repo_class.return_value = fake_repo

        config = RepositoryConfig(strategy="postgres", connection_url="fake")
        pm = PersistenceManager(config)

        exec_start = datetime(2025, 3, 4, 5, 6, 7)

        exec = Execution(
            id="exec-9",
            state_machine_id="sm-1",
            name="test",
            status=ExecutionStatus.RUNNING,
            start_time=exec_start,
            current_state="A",
        )

        hist_start = datetime(2025, 3, 4, 5, 6, 8)
        hist_end = datetime(2025, 3, 4, 5, 6, 9)

        h = StateHistory(
            id="hist-1",
            execution_id="exec-9",
            state_name="A",
            state_type="Pass",
            status=StateHistoryStatus.FAILED,
            input="in",
            output="out",
            start_time=hist_start,
            end_time=hist_end,
            retry_count=2,
            sequence_number=7,
            error=Exception("state failed"),
        )

        pm.save_state_history(exec, h)

        assert 1 == fake_repo.save_state_history_calls
        assert fake_repo.last_saved_state_history is not None

        rec = fake_repo.last_saved_state_history
        assert "exec-9" == rec.execution_id
        assert exec_start == rec.execution_start_time
        assert "A" == rec.state_name
        assert "Pass" == rec.state_type
        assert "in" == rec.input
        assert "out" == rec.output
        assert "FAILED" == rec.status
        assert hist_start == rec.start_time
        assert hist_end == rec.end_time
        assert 2 == rec.retry_count
        assert 7 == rec.sequence_number
        assert rec.end_time is not None
        assert "state failed" == rec.error
        assert rec.id is not None
        assert rec.id.startswith("exec-9-A-") is True

    @patch("src.repository.repository.SQLAlchemyPostgresRepository")
    def test_get_execution_get_state_history_list_executions_delegates(self, mock_repo_class):
        """Test that get methods delegate to repository."""
        fake_repo = FakeRepository()
        mock_repo_class.return_value = fake_repo

        config = RepositoryConfig(strategy="postgres", connection_url="fake")
        pm = PersistenceManager(config)

        pm.get_execution("exec-abc")
        assert "exec-abc" == fake_repo.get_execution_id
        pm.get_state_history("exec-hist")
        assert "exec-hist" == fake_repo.get_history_id
        pm.list_executions(ExecutionFilter(offset=20, limit=10))
        assert 10 == fake_repo.list_limit
        assert 20 == fake_repo.list_offset

    def test_generate_history_id_unique_for_different_timestamps(self):
        """Test that generateHistoryID produces unique IDs for different timestamps."""
        t1 = datetime.fromtimestamp(100.000000001)
        t2 = datetime.fromtimestamp(100.000000002)

        id1 = generate_history_id("exec-x", "StateY", t1)
        id2 = generate_history_id("exec-x", "StateY", t2)

        assert id1 == id2
        assert id1.startswith("exec-x-StateY-") is True
        assert id2.startswith("exec-x-StateY-") is True
