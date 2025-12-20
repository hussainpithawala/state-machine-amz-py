# pkg/repository/models.py
"""SQLAlchemy models for executions and state history."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ExecutionModel(Base):
    """SQLAlchemy model for executions table."""

    __tablename__ = "executions"

    execution_id: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=False)
    state_machine_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    input: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    start_time: Mapped[datetime] = mapped_column(index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    current_state: Mapped[str] = mapped_column(String(255))
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to state history
    state_history: Mapped[List["StateHistoryModel"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Composite indexes and constraints
    __table_args__ = (
        Index("idx_executions_sm_status_time", "state_machine_id", "status", "start_time"),
        Index(
            "idx_executions_running",
            "state_machine_id",
            "start_time",
            postgresql_where=text("status = 'RUNNING'"),
        ),
        CheckConstraint(
            "status IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'TIMED_OUT', 'ABORTED')",
            name="check_execution_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<ExecutionModel(id={self.execution_id}, status={self.status})>"


class StateHistoryModel(Base):
    """SQLAlchemy model for state_history table."""

    __tablename__ = "state_history"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions.execution_id", ondelete="CASCADE"),
        index=True,
    )
    execution_start_time: Mapped[datetime] = mapped_column()
    state_name: Mapped[str] = mapped_column(String(255), index=True)
    state_type: Mapped[str] = mapped_column(String(50))
    input: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    start_time: Mapped[datetime] = mapped_column(index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    sequence_number: Mapped[int] = mapped_column(index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationship to execution
    execution: Mapped["ExecutionModel"] = relationship(back_populates="state_history")

    # Composite indexes and constraints
    __table_args__ = (
        Index("idx_state_history_exec_seq", "execution_id", "sequence_number"),
        CheckConstraint(
            "status IN ('SUCCEEDED', 'FAILED', 'RUNNING', 'CANCELLED', 'TIMED_OUT', 'RETRYING')",
            name="check_state_history_status",
        ),
        CheckConstraint("sequence_number >= 0", name="check_sequence_number"),
    )

    def __repr__(self) -> str:
        return f"<StateHistoryModel(id={self.id}, state={self.state_name})>"


class ExecutionStatisticsModel(Base):
    """SQLAlchemy model for execution statistics."""

    __tablename__ = "execution_statistics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    state_machine_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50))
    execution_count: Mapped[int] = mapped_column(default=0)
    avg_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    first_execution: Mapped[datetime] = mapped_column()
    last_execution: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("state_machine_id", "status", name="idx_stats_unique"),
        Index("idx_stats_sm_status", "state_machine_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<ExecutionStatisticsModel(sm={self.state_machine_id}, status={self.status})>"
