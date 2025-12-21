# pkg/repository/sqlalchemy_postgres.py
"""SQLAlchemy PostgreSQL repository implementation."""

from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, ExecutionModel, ExecutionStatisticsModel, StateHistoryModel
from .types import (
    ExecutionFilter,
    ExecutionRecord,
    ExtendedRepository,
    RepositoryConfig,
    StateHistoryRecord,
    Statistics,
    StatusStatistics,
)


class SQLAlchemyPostgresRepository(ExtendedRepository):
    """PostgreSQL repository implementation using SQLAlchemy."""

    def __init__(self, config: RepositoryConfig):
        """Initializes the repository with configuration."""
        if not config.connection_url:
            raise ValueError("connection URL is required")

        self.config = config
        self.options = config.options or {}

        # Parse configuration
        pool_size = self.options.get("max_open_conns", 25)
        max_overflow = self.options.get("max_overflow", 10)
        pool_timeout = self.options.get("pool_timeout", 30)
        pool_recycle = self.options.get("conn_max_lifetime", 300)  # seconds
        echo = self.options.get("echo", False)

        # Create engine
        self.engine = create_engine(
            config.connection_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Verify connections before using them
            echo=echo,
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    @contextmanager
    def get_session(self):
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def initialize(self) -> None:
        """Creates tables and indexes."""
        # Create all tables
        Base.metadata.create_all(bind=self.engine)

        # Create additional GIN indexes for JSONB columns
        with self.get_session() as session:
            self._create_additional_indexes(session)

    def _create_additional_indexes(self, session: Session) -> None:
        """Creates GIN indexes for JSONB columns."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_executions_metadata_gin ON executions USING GIN (metadata)",
            "CREATE INDEX IF NOT EXISTS idx_state_history_metadata_gin ON state_history USING GIN (metadata)",
            "CREATE INDEX IF NOT EXISTS idx_executions_input_gin ON executions USING GIN (input)",
            "CREATE INDEX IF NOT EXISTS idx_state_history_input_gin ON state_history USING GIN (input)",
        ]

        for index_sql in indexes:
            try:
                session.execute(text(index_sql))
            except SQLAlchemyError as e:
                print(f"Warning: Could not create index: {e}")

    def close(self) -> None:
        """Closes the database connection."""
        if self.engine:
            self.engine.dispose()

    def save_execution(self, execution: ExecutionRecord) -> None:
        """Saves or updates an execution."""
        with self.get_session() as session:
            model = self._to_execution_model(execution)

            # Check if execution exists
            existing = (
                session.query(ExecutionModel).filter(ExecutionModel.execution_id == execution.execution_id).first()
            )

            if existing:
                # Update existing
                for key, value in model.__dict__.items():
                    if not key.startswith("_"):
                        setattr(existing, key, value)
            else:
                # Insert new
                session.add(model)

    def get_execution(self, execution_id: str) -> ExecutionRecord:
        """Retrieves an execution by ID."""
        with self.get_session() as session:
            model = session.query(ExecutionModel).filter(ExecutionModel.execution_id == execution_id).first()

            if not model:
                raise ValueError(f"execution not found: {execution_id}")

            return self._from_execution_model(model)

    def save_state_history(self, history: StateHistoryRecord) -> None:
        """Saves a state history entry."""
        with self.get_session() as session:
            model = self._to_state_history_model(history)

            # Check if history entry exists
            existing = session.query(StateHistoryModel).filter(StateHistoryModel.id == history.id).first()

            if existing:
                # Update existing
                for key, value in model.__dict__.items():
                    if not key.startswith("_"):
                        setattr(existing, key, value)
            else:
                # Insert new
                session.add(model)

    def get_state_history(self, execution_id: str) -> List[StateHistoryRecord]:
        """Retrieves all state history for an execution."""
        with self.get_session() as session:
            models = (
                session.query(StateHistoryModel)
                .filter(StateHistoryModel.execution_id == execution_id)
                .order_by(
                    StateHistoryModel.sequence_number.asc(),
                    StateHistoryModel.start_time.asc(),
                )
                .all()
            )

            return [self._from_state_history_model(model) for model in models]

    def list_executions(self, list_filter: Optional[ExecutionFilter]) -> List[ExecutionRecord]:
        """Lists executions with filtering and pagination."""
        with self.get_session() as session:
            query = session.query(ExecutionModel)

            # Apply filters
            query = self._apply_filters(query, list_filter)

            # Order by start time descending
            query = query.order_by(ExecutionModel.start_time.desc())

            if list_filter:
                # Apply pagination
                if list_filter.limit > 0:
                    query = query.limit(list_filter.limit)
                if list_filter.offset > 0:
                    query = query.offset(list_filter.offset)

            models = query.all()
            return [self._from_execution_model(model) for model in models]

    def count_executions(self, filter: ExecutionFilter) -> int:
        """Returns the count of executions matching the filter."""
        with self.get_session() as session:
            query = session.query(func.count(ExecutionModel.execution_id))

            # Apply same filters
            query = self._apply_filters(query, filter)

            return query.scalar()

    def delete_execution(self, execution_id: str) -> None:
        """Removes an execution and its history (cascade handled by FK)."""
        with self.get_session() as session:
            result = session.query(ExecutionModel).filter(ExecutionModel.execution_id == execution_id).delete()

            if result == 0:
                raise ValueError(f"execution not found: {execution_id}")

    def health_check(self) -> None:
        """Verifies database connectivity."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
        except Exception as e:
            raise RuntimeError(f"database health check failed: {e}")

    def get_execution_with_history(self, execution_id: str) -> tuple[ExecutionRecord, List[StateHistoryRecord]]:
        """Retrieves an execution with its full state history."""
        with self.get_session() as session:
            # Get execution
            exec_model = session.query(ExecutionModel).filter(ExecutionModel.execution_id == execution_id).first()

            if not exec_model:
                raise ValueError(f"execution not found: {execution_id}")

            # Get state history
            history_models = (
                session.query(StateHistoryModel)
                .filter(StateHistoryModel.execution_id == execution_id)
                .order_by(StateHistoryModel.sequence_number.asc())
                .all()
            )

            execution = self._from_execution_model(exec_model)
            histories = [self._from_state_history_model(h) for h in history_models]

            return execution, histories

    def get_statistics(self, state_machine_id: str) -> Statistics:
        """Returns aggregated statistics for a state machine."""
        with self.get_session() as session:
            # Query for statistics
            results = session.execute(
                text(
                    """
                     SELECT status,
                            COUNT(*) as count,
                        AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration_seconds,
                        PERCENTILE_CONT(0.5) WITHIN
                     GROUP (ORDER BY EXTRACT (EPOCH FROM (end_time - start_time))) as p50_duration,
                         PERCENTILE_CONT(0.95) WITHIN
                     GROUP (ORDER BY EXTRACT (EPOCH FROM (end_time - start_time))) as p95_duration,
                         PERCENTILE_CONT(0.99) WITHIN
                     GROUP (ORDER BY EXTRACT (EPOCH FROM (end_time - start_time))) as p99_duration,
                         MIN (start_time) as first_execution,
                         MAX (start_time) as last_execution
                     FROM executions
                     WHERE state_machine_id = :state_machine_id
                       AND end_time IS NOT NULL
                     GROUP BY status
                     """
                ),
                {"state_machine_id": state_machine_id},
            )

            stats = Statistics(state_machine_id=state_machine_id)

            for row in results:
                stats.by_status[row.status] = StatusStatistics(
                    count=row.count,
                    avg_duration_seconds=row.avg_duration_seconds or 0.0,
                    p50_duration=row.p50_duration or 0.0,
                    p95_duration=row.p95_duration or 0.0,
                    p99_duration=row.p99_duration or 0.0,
                    first_execution=row.first_execution,
                    last_execution=row.last_execution,
                )

            stats.total_count = sum(s.count for s in stats.by_status.values())
            stats.updated_at = datetime.utcnow()

            return stats

    def update_statistics(self) -> None:
        """Refreshes the execution statistics table."""
        with self.get_session() as session:
            # Delete old statistics
            session.query(ExecutionStatisticsModel).delete()

            # Insert new statistics
            session.execute(
                text(
                    """
                     INSERT INTO execution_statistics (state_machine_id, status, execution_count,
                                                       avg_duration_seconds, min_duration_seconds, max_duration_seconds,
                                                       first_execution, last_execution)
                     SELECT state_machine_id,
                            status,
                            COUNT(*)                                         as execution_count,
                            AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration_seconds,
                            MIN(EXTRACT(EPOCH FROM (end_time - start_time))) as min_duration_seconds,
                            MAX(EXTRACT(EPOCH FROM (end_time - start_time))) as max_duration_seconds,
                            MIN(start_time)                                  as first_execution,
                            MAX(start_time)                                  as last_execution
                     FROM executions
                     WHERE end_time IS NOT NULL
                     GROUP BY state_machine_id, status
                     """
                )
            )

    def _apply_filters(self, query, list_filter: Optional[ExecutionFilter]):
        if list_filter:
            """Applies filters to a query."""
            if list_filter.status:
                query = query.filter(ExecutionModel.status == list_filter.status)

            if list_filter.state_machine_id:
                query = query.filter(ExecutionModel.state_machine_id == list_filter.state_machine_id)

            if list_filter.name:
                query = query.filter(ExecutionModel.name.ilike(f"%{list_filter.name}%"))

            if list_filter.start_after:
                query = query.filter(ExecutionModel.start_time >= list_filter.start_after)

            if list_filter.start_before:
                query = query.filter(ExecutionModel.start_time <= list_filter.start_before)
        return query

    # Conversion helpers
    @staticmethod
    def _to_execution_model(record: ExecutionRecord) -> ExecutionModel:
        """Converts ExecutionRecord to ExecutionModel."""
        return ExecutionModel(
            execution_id=record.execution_id,
            state_machine_id=record.state_machine_id,
            name=record.name,
            input=record.input,
            output=record.output,
            status=record.status,
            start_time=record.start_time,
            end_time=record.end_time,
            current_state=record.current_state,
            error=record.error,
            metadata=record.metadata or {},
        )

    @staticmethod
    def _from_execution_model(model: ExecutionModel) -> ExecutionRecord:
        """Converts ExecutionModel to ExecutionRecord."""
        return ExecutionRecord(
            execution_id=model.execution_id,
            state_machine_id=model.state_machine_id,
            name=model.name,
            input=model.input,
            output=model.output,
            status=model.status,
            start_time=model.start_time,
            end_time=model.end_time,
            current_state=model.current_state,
            error=model.error,
            metadata=model.metadata.__dict__,
        )

    @staticmethod
    def _to_state_history_model(record: StateHistoryRecord) -> StateHistoryModel:
        """Converts StateHistoryRecord to StateHistoryModel."""
        return StateHistoryModel(
            id=record.id,
            execution_id=record.execution_id,
            execution_start_time=record.execution_start_time,
            state_name=record.state_name,
            state_type=record.state_type,
            input=record.input,
            output=record.output,
            status=record.status,
            start_time=record.start_time,
            end_time=record.end_time,
            error=record.error,
            retry_count=record.retry_count,
            sequence_number=record.sequence_number,
            metadata=record.metadata or {},
        )

    @staticmethod
    def _from_state_history_model(model: StateHistoryModel) -> StateHistoryRecord:
        """Converts StateHistoryModel to StateHistoryRecord."""
        return StateHistoryRecord(
            id=model.id,
            execution_id=model.execution_id,
            execution_start_time=model.execution_start_time,
            state_name=model.state_name,
            state_type=model.state_type,
            input=model.input,
            output=model.output,
            status=model.status,
            start_time=model.start_time,
            end_time=model.end_time,
            error=model.error,
            retry_count=model.retry_count,
            sequence_number=model.sequence_number,
            metadata=model.metadata.__dict__,
        )
