# pkg/repository/test_sqlalchemy_postgres_integration.py
"""Integration tests for SQLAlchemy PostgreSQL repository."""

import os
from datetime import datetime, timedelta
from typing import Optional

import pytest
from sqlalchemy import text

from src.repository.sqlalchemy_postgres import SQLAlchemyPostgresRepository
from src.repository.types import ExecutionFilter, ExecutionRecord, RepositoryConfig, StateHistoryRecord


class TestSQLAlchemyPostgresIntegration:
    """Integration tests for SQLAlchemy PostgreSQL repository."""

    repository: Optional[SQLAlchemyPostgresRepository] = None

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
            cls.repository = SQLAlchemyPostgresRepository(config)
            cls.repository.initialize()
        except Exception as e:
            raise pytest.skip(f"PostgreSQL not available: {e}")

    def teardown_class(cls):
        """Clean up database connection."""
        if cls.repository:
            cls.repository.close()

    def setup_method(cls):
        cls.cleanup_data()

    def teardown_method(cls):
        cls.cleanup_data()

    def cleanup_data(cls):
        """Remove all test data."""
        if cls.repository:
            with cls.repository.get_session() as session:
                # Truncate in FK-safe order
                session.execute(text("TRUNCATE TABLE state_history CASCADE"))
                session.execute(text("TRUNCATE TABLE executions CASCADE"))
                session.execute(text("TRUNCATE TABLE execution_statistics CASCADE"))


    def test_save_and_get_execution(self):
        """Test basic save and retrieve operations."""
        now = datetime.utcnow()
        record = ExecutionRecord(
            execution_id="exec-sa-001",
            state_machine_id="sm-test-001",
            name="test-execution",
            input={"orderId": "12345", "amount": 100.50},
            status="RUNNING",
            start_time=now,
            current_state="ProcessOrder",
            metadata={"version": "1.0", "source": "api"},
        )

        self.repository.save_execution(record)

        retrieved = self.repository.get_execution("exec-sa-001")
        assert record.execution_id == retrieved.execution_id
        assert record.status == retrieved.status
        assert record.state_machine_id == retrieved.state_machine_id
        assert retrieved.input is not None
        assert "12345" == retrieved.input["orderId"]

    def test_update_execution(self):
        """Test updating an existing execution."""
        now = datetime.utcnow()
        record = ExecutionRecord(
            execution_id="exec-sa-002",
            state_machine_id="sm-test-001",
            name="update-test",
            input={"test": "data"},
            status="RUNNING",
            start_time=now,
            current_state="State1",
        )

        self.repository.save_execution(record)

        # Update the record
        record.status = "SUCCEEDED"
        record.current_state = "State2"
        record.end_time = now + timedelta(minutes=1)
        record.output = {"result": "success"}

        self.repository.save_execution(record)

        retrieved = self.repository.get_execution("exec-sa-002")
        assert "SUCCEEDED" == retrieved.status
        assert "State2" == retrieved.current_state
        assert retrieved.end_time is not None
        assert retrieved.output is not None

    def test_save_state_history(self):
        """Test saving state execution history."""
        now = datetime.utcnow()

        exec_record = ExecutionRecord(
            execution_id="exec-sa-003",
            state_machine_id="sm-test-001",
            name="history-test",
            input={},
            status="RUNNING",
            start_time=now,
            current_state="State1",
        )
        self.repository.save_execution(exec_record)

        for i in range(3):
            start_time = now + timedelta(seconds=i)
            end_time = start_time + timedelta(milliseconds=500)

            hist_record = StateHistoryRecord(
                id=f"hist-sa-{i}",
                execution_id=exec_record.execution_id,
                execution_start_time=exec_record.start_time,
                state_name=f"State{i + 1}",
                state_type="Task",
                input={"step": i, "value": i * 10},
                output={"result": "processed"},
                status="SUCCEEDED",
                start_time=start_time,
                end_time=end_time,
                sequence_number=i,
                retry_count=0,
            )

            self.repository.save_state_history(hist_record)

        history = self.repository.get_state_history(exec_record.execution_id)
        assert 3 == len(history)

        for i, h in enumerate(history):
            assert i == h.sequence_number
            assert f"State{i + 1}" == h.state_name
            assert "SUCCEEDED" == h.status
            assert h.end_time is not None

    def test_state_history_with_retries(self):
        """Test retry tracking."""
        now = datetime.utcnow()

        exec_record = ExecutionRecord(
            execution_id="exec-sa-004",
            state_machine_id="sm-test-001",
            name="retry-test",
            input={},
            status="RUNNING",
            start_time=now,
            current_state="FlakyState",
        )
        self.repository.save_execution(exec_record)

        for retry in range(3):
            start_time = now + timedelta(seconds=retry)
            end_time = start_time + timedelta(milliseconds=100)

            status = "FAILED" if retry < 2 else "SUCCEEDED"
            error_str = "Transient error" if retry < 2 else None

            hist_record = StateHistoryRecord(
                id=f"hist-sa-retry-{retry}",
                execution_id=exec_record.execution_id,
                execution_start_time=exec_record.start_time,
                state_name="FlakyState",
                state_type="Task",
                input={},
                status=status,
                start_time=start_time,
                end_time=end_time,
                error=error_str,
                retry_count=retry,
                sequence_number=0,
            )

            self.repository.save_state_history(hist_record)

        history = self.repository.get_state_history(exec_record.execution_id)
        assert 3 == len(history)

        assert 0 == history[0].retry_count
        assert "FAILED" == history[0].status
        assert 2 == history[2].retry_count
        assert "SUCCEEDED" == history[2].status

    def test_list_executions(self):
        """Test listing with various filters."""
        base_time = datetime.utcnow() - timedelta(hours=1)

        test_cases = [
            ("exec-sa-list-001", "sm-order", "SUCCEEDED", timedelta(0)),
            ("exec-sa-list-002", "sm-order", "RUNNING", timedelta(minutes=10)),
            ("exec-sa-list-003", "sm-payment", "SUCCEEDED", timedelta(minutes=20)),
            ("exec-sa-list-004", "sm-order", "FAILED", timedelta(minutes=30)),
            ("exec-sa-list-005", "sm-payment", "SUCCEEDED", timedelta(minutes=40)),
        ]

        for exec_id, sm_id, status, offset in test_cases:
            start_time = base_time + offset
            record = ExecutionRecord(
                execution_id=exec_id,
                state_machine_id=sm_id,
                name="list-test",
                input={},
                status=status,
                start_time=start_time,
                current_state="SomeState",
            )
            self.repository.save_execution(record)

        # List all
        executions = self.repository.list_executions(ExecutionFilter(limit=100, offset=0))
        assert len(executions) >= 5

        # Filter by status
        executions = self.repository.list_executions(ExecutionFilter(limit=100, offset=0, status="SUCCEEDED"))
        assert 3 == len(executions)

        # Filter by state machine ID
        executions = self.repository.list_executions(ExecutionFilter(state_machine_id="sm-order", limit=100, offset=0))
        assert 3 == len(executions)

        # Combined filters
        executions = self.repository.list_executions(
            ExecutionFilter(state_machine_id="sm-order", status="SUCCEEDED", limit=100, offset=0)
        )
        assert 1 == len(executions)

        # Pagination
        executions = self.repository.list_executions(ExecutionFilter(limit=2, offset=0))
        assert 2 == len(executions)

        # Time range filter
        time_lapse = base_time + timedelta(minutes=15)
        executions = self.repository.list_executions(ExecutionFilter(limit=100, offset=0, start_after=time_lapse))
        assert 3 == len(executions)

    def test_delete_execution(self):
        """Test cascade deletion."""
        start_time = datetime.utcnow()
        exec_record = ExecutionRecord(
            execution_id="exec-sa-delete",
            state_machine_id="sm-test-001",
            name="delete-test",
            input={},
            status="SUCCEEDED",
            start_time=start_time,
            current_state="Final",
        )
        self.repository.save_execution(exec_record)

        start_time_history = datetime.utcnow()
        hist_record = StateHistoryRecord(
            id="hist-sa-delete",
            execution_id=exec_record.execution_id,
            execution_start_time=exec_record.start_time,
            state_name="State1",
            state_type="Task",
            input={},
            status="SUCCEEDED",
            start_time=start_time_history,
            sequence_number=0,
        )
        self.repository.save_state_history(hist_record)

        self.repository.delete_execution(exec_record.execution_id)

        with pytest.raises(ValueError):
            self.repository.get_execution(exec_record.execution_id)

        history = self.repository.get_state_history(exec_record.execution_id)
        assert 0 == len(history)

    def test_health_check(self):
        """Test database health check."""
        # Should not raise
        self.repository.health_check()

    def test_get_statistics(self):
        """Test statistics generation."""
        statuses = ["SUCCEEDED", "SUCCEEDED", "FAILED", "RUNNING"]

        for i, status in enumerate(statuses):
            start_time = datetime.utcnow() - timedelta(minutes=i)
            end_time = start_time + timedelta(seconds=30)

            record = ExecutionRecord(
                execution_id=f"exec-sa-stats-{i}",
                state_machine_id="sm-stats-test",
                name="stats-test",
                input={},
                status=status,
                start_time=start_time,
                current_state="Final",
            )
            if status != "RUNNING":
                record.end_time = end_time

            self.repository.save_execution(record)

        stats = self.repository.get_statistics("sm-stats-test")
        assert stats is not None
        assert stats.by_status is not None

        succeeded_stats = stats.by_status.get("SUCCEEDED")
        assert succeeded_stats is not None
        assert 2 == succeeded_stats.count
        assert succeeded_stats.avg_duration_seconds >= 0.0

        failed_stats = stats.by_status.get("FAILED")
        assert failed_stats is not None
        assert 1 == failed_stats.count

    def test_error_handling(self):
        """Test various error scenarios."""
        # Save with empty execution ID (should fail)
        with pytest.raises(Exception):
            self.repository.save_execution(
                ExecutionRecord(
                    execution_id=None,
                    name="test",
                    status="RUNNING",
                    start_time=datetime.utcnow(),
                    current_state="State1",
                )
            )

        # Get non-existent execution
        with pytest.raises(ValueError):
            self.repository.get_execution("non-existent")

        # Delete non-existent execution
        with pytest.raises(ValueError):
            self.repository.delete_execution("non-existent")

        # Save state history without execution (should fail due to FK)
        now = datetime.utcnow()
        with pytest.raises(Exception):
            self.repository.save_state_history(
                StateHistoryRecord(
                    id="orphan-hist-sa",
                    execution_id="non-existent-exec",
                    state_name="State1",
                    state_type="Task",
                    status="SUCCEEDED",
                    start_time=now,
                    sequence_number=0,
                )
            )
