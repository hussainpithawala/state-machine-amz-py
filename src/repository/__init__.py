# pkg/repository/__init__.py
"""Repository package for state machine execution persistence."""

from .models import Base, ExecutionModel, ExecutionStatisticsModel, StateHistoryModel
from .repository import PersistenceManager, new_persistence_manager
from .sqlalchemy_postgres import SQLAlchemyPostgresRepository
from .types import (
    Execution,
    ExecutionFilter,
    ExecutionRecord,
    ExecutionStatus,
    ExtendedRepository,
    Repository,
    RepositoryConfig,
    StateHistory,
    StateHistoryRecord,
    StateHistoryStatus,
    Statistics,
    StatusStatistics,
    generate_execution_id,
    generate_history_id,
    generate_state_history_id,
    new_execution,
    new_state_history,
)

__all__ = [
    # Models
    "Base",
    "ExecutionModel",
    "StateHistoryModel",
    "ExecutionStatisticsModel",
    # Repository Manager
    "PersistenceManager",
    "new_persistence_manager",
    # Repository Implementation
    "SQLAlchemyPostgresRepository",
    # Types and Interfaces
    "Repository",
    "ExtendedRepository",
    "RepositoryConfig",
    "ExecutionRecord",
    "StateHistoryRecord",
    "ExecutionFilter",
    "Statistics",
    "StatusStatistics",
    "Execution",
    "StateHistory",
    "ExecutionStatus",
    "StateHistoryStatus",
    # Helper Functions
    "generate_execution_id",
    "generate_state_history_id",
    "generate_history_id",
    "new_execution",
    "new_state_history",
]

__version__ = "1.0.0"
