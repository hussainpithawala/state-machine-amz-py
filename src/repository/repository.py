# pkg/repository/repository.py
"""Repository manager for persistence operations."""

from datetime import datetime
from typing import List

from .sqlalchemy_postgres import SQLAlchemyPostgresRepository
from .types import (
    Execution,
    ExecutionFilter,
    ExecutionRecord,
    Repository,
    RepositoryConfig,
    StateHistory,
    StateHistoryRecord,
    generate_history_id,
)


class PersistenceManager:
    """Manages the persistence repository."""

    def __init__(self, config: RepositoryConfig):
        """Initializes the persistence manager."""
        self.config = config
        self.repository: Repository = self._create_repository(config)

    def _create_repository(self, config: RepositoryConfig) -> Repository:
        """Creates a repository based on the strategy."""
        strategy = config.strategy.lower()

        if strategy in ["postgres", "sqlalchemy", "sqlalchemy-postgres"]:
            return SQLAlchemyPostgresRepository(config)
        elif strategy == "dynamodb":
            raise NotImplementedError("DynamoDB repository not yet implemented")
        elif strategy == "redis":
            raise NotImplementedError("Redis repository not yet implemented")
        elif strategy == "memory":
            raise NotImplementedError("InMemory repository not yet implemented")
        else:
            raise ValueError(f"unsupported persistence repository: {strategy}")

    def initialize(self) -> None:
        """Initializes the persistence layer."""
        self.repository.initialize()

    def close(self) -> None:
        """Closes the persistence layer."""
        self.repository.close()

    def save_execution(self, exec: Execution) -> None:
        """Saves an execution record."""
        record = ExecutionRecord(
            execution_id=exec.id,
            name=exec.name,
            input=exec.input,
            output=exec.output,
            status=exec.status,
            start_time=exec.start_time,
            current_state=exec.current_state,
            state_machine_id=exec.state_machine_id,
        )

        # Only set end_time if it's not None/zero
        if exec.end_time:
            record.end_time = exec.end_time

        # Convert error to string if present
        if exec.error:
            record.error = str(exec.error)

        self.repository.save_execution(record)

    def save_state_history(self, execution_instance: Execution, history: StateHistory) -> None:
        """Saves a state history entry."""
        record = StateHistoryRecord(
            id=generate_history_id(execution_instance.id, history.state_name, datetime.utcnow()),
            execution_id=execution_instance.id,
            execution_start_time=execution_instance.start_time,
            state_name=history.state_name,
            state_type=history.state_type,
            input=history.input,
            output=history.output,
            status=history.status,
            start_time=history.start_time,
            retry_count=history.retry_count,
            sequence_number=history.sequence_number,
        )

        # Only set end_time if it's not None/zero
        if history.end_time:
            record.end_time = history.end_time

        # Convert error to string if present
        if history.error:
            record.error = str(history.error)

        self.repository.save_state_history(record)

    def get_execution(self, execution_id: str) -> ExecutionRecord:
        """Retrieves an execution."""
        return self.repository.get_execution(execution_id)

    def get_state_history(self, execution_id: str) -> List[StateHistoryRecord]:
        """Retrieves state history."""
        return self.repository.get_state_history(execution_id)

    def list_executions(self, filter: ExecutionFilter) -> List[ExecutionRecord]:
        """Lists executions."""
        return self.repository.list_executions(filter)

    def count_executions(self, filter: ExecutionFilter) -> int:
        """Counts executions matching the filter."""
        return self.repository.count_executions(filter)

    def delete_execution(self, execution_id: str) -> None:
        """Deletes an execution."""
        self.repository.delete_execution(execution_id)

    def health_check(self) -> None:
        """Checks repository health."""
        self.repository.health_check()


def new_persistence_manager(config: RepositoryConfig) -> PersistenceManager:
    """Creates a new persistence manager."""
    return PersistenceManager(config)
