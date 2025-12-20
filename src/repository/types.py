# pkg/repository/types.py
"""Repository types, interfaces, and domain models."""

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# Status enums
class ExecutionStatus(str, Enum):
    """Execution status constants."""

    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    ABORTED = "ABORTED"


class StateHistoryStatus(str, Enum):
    """State history status constants."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    RETRYING = "RETRYING"


@dataclass
class ExecutionRecord:
    """Represents the execution data to be persisted."""

    execution_id: str
    name: str
    status: str
    start_time: datetime
    current_state: str
    state_machine_id: str = ""
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StateHistoryRecord:
    """Represents a single state execution in history."""

    id: str
    execution_id: str
    state_name: str
    state_type: str
    status: str
    start_time: datetime
    sequence_number: int
    execution_start_time: Optional[datetime] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionFilter:
    """Defines filters for querying executions."""

    status: Optional[str] = None
    state_machine_id: Optional[str] = None
    name: Optional[str] = None
    start_after: Optional[datetime] = None
    start_before: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


@dataclass
class StatusStatistics:
    """Statistics for a specific status."""

    count: int
    avg_duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    p50_duration: float = 0.0
    p95_duration: float = 0.0
    p99_duration: float = 0.0
    first_execution: Optional[datetime] = None
    last_execution: Optional[datetime] = None


@dataclass
class Statistics:
    """Aggregated execution statistics."""

    state_machine_id: str
    by_status: Dict[str, StatusStatistics] = field(default_factory=dict)
    total_count: int = 0
    updated_at: Optional[datetime] = None


@dataclass
class Execution:
    """Domain model for state machine execution."""

    id: str
    state_machine_id: str
    name: str
    status: str
    start_time: datetime
    current_state: str
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    end_time: Optional[datetime] = None
    error: Optional[Exception] = None
    metadata: Optional[Dict[str, Any]] = None

    def is_terminal(self) -> bool:
        """Returns True if the execution status is terminal."""
        return self.status in {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMED_OUT,
            ExecutionStatus.ABORTED,
        }

    def duration(self) -> float:
        """Returns the execution duration in seconds."""
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()

    def mark_succeeded(self, output: Optional[Dict[str, Any]] = None):
        """Marks the execution as succeeded."""
        self.status = ExecutionStatus.SUCCEEDED
        self.output = output
        self.end_time = datetime.utcnow()

    def mark_failed(self, error: Exception):
        """Marks the execution as failed."""
        self.status = ExecutionStatus.FAILED
        self.error = error
        self.end_time = datetime.utcnow()

    def mark_cancelled(self):
        """Marks the execution as cancelled."""
        self.status = ExecutionStatus.CANCELLED
        self.end_time = datetime.utcnow()

    def mark_timed_out(self):
        """Marks the execution as timed out."""
        self.status = ExecutionStatus.TIMED_OUT
        self.end_time = datetime.utcnow()

    def validate(self) -> None:
        """Validates the execution."""
        if not self.id:
            raise ValueError("execution ID is required")
        if not self.state_machine_id:
            raise ValueError("state machine ID is required")
        if not self.name:
            raise ValueError("execution name is required")
        if not self.status:
            raise ValueError("execution status is required")
        if self.status not in ExecutionStatus.__members__.values():
            raise ValueError(f"invalid execution status: {self.status}")
        if not self.start_time:
            raise ValueError("start time is required")


@dataclass
class StateHistory:
    """Domain model for state execution history."""

    id: str
    execution_id: str
    state_name: str
    state_type: str
    status: str
    start_time: datetime
    sequence_number: int
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    end_time: Optional[datetime] = None
    error: Optional[Exception] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

    def is_terminal(self) -> bool:
        """Returns True if the state history status is terminal."""
        return self.status in {
            StateHistoryStatus.SUCCEEDED,
            StateHistoryStatus.FAILED,
            StateHistoryStatus.CANCELLED,
            StateHistoryStatus.TIMED_OUT,
        }

    def duration(self) -> float:
        """Returns the state execution duration in seconds."""
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()

    def mark_succeeded(self, output: Optional[Dict[str, Any]] = None):
        """Marks the state history as succeeded."""
        self.status = StateHistoryStatus.SUCCEEDED
        self.output = output
        self.end_time = datetime.utcnow()

    def mark_failed(self, error: Exception):
        """Marks the state history as failed."""
        self.status = StateHistoryStatus.FAILED
        self.error = error
        self.end_time = datetime.utcnow()

    def increment_retry(self):
        """Increments the retry count."""
        self.retry_count += 1
        self.status = StateHistoryStatus.RETRYING

    def validate(self) -> None:
        """Validates the state history."""
        if not self.id:
            raise ValueError("state history ID is required")
        if not self.execution_id:
            raise ValueError("execution ID is required")
        if not self.state_name:
            raise ValueError("state name is required")
        if not self.state_type:
            raise ValueError("state type is required")
        if not self.status:
            raise ValueError("state history status is required")
        if self.status not in StateHistoryStatus.__members__.values():
            raise ValueError(f"invalid state history status: {self.status}")
        if not self.start_time:
            raise ValueError("start time is required")
        if self.sequence_number < 0:
            raise ValueError("sequence number must be non-negative")


class Repository(ABC):
    """Abstract repository interface for execution persistence."""

    @abstractmethod
    def initialize(self) -> None:
        """Creates necessary database schema."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes the repository connection."""
        pass

    @abstractmethod
    def save_execution(self, execution: ExecutionRecord) -> None:
        """Saves or updates an execution."""
        pass

    @abstractmethod
    def get_execution(self, execution_id: str) -> ExecutionRecord:
        """Retrieves an execution by ID."""
        pass

    @abstractmethod
    def save_state_history(self, history: StateHistoryRecord) -> None:
        """Saves a state history entry."""
        pass

    @abstractmethod
    def get_state_history(self, execution_id: str) -> List[StateHistoryRecord]:
        """Retrieves all state history for an execution."""
        pass

    @abstractmethod
    def list_executions(self, filter: ExecutionFilter) -> List[ExecutionRecord]:
        """Lists executions with filtering and pagination."""
        pass

    @abstractmethod
    def count_executions(self, filter: ExecutionFilter) -> int:
        """Returns the count of executions matching the filter."""
        pass

    @abstractmethod
    def delete_execution(self, execution_id: str) -> None:
        """Removes an execution and its history."""
        pass

    @abstractmethod
    def health_check(self) -> None:
        """Verifies the repository is accessible."""
        pass


class ExtendedRepository(Repository):
    """Extended repository interface with additional capabilities."""

    @abstractmethod
    def get_execution_with_history(self, execution_id: str) -> tuple[ExecutionRecord, List[StateHistoryRecord]]:
        """Retrieves an execution with its full state history."""
        pass

    @abstractmethod
    def get_statistics(self, state_machine_id: str) -> Statistics:
        """Returns aggregated statistics for a state machine."""
        pass

    @abstractmethod
    def update_statistics(self) -> None:
        """Refreshes the execution statistics."""
        pass


@dataclass
class RepositoryConfig:
    """Repository configuration."""

    strategy: str
    connection_url: str
    options: Optional[Dict[str, Any]] = None


# Helper functions
def generate_execution_id() -> str:
    """Generates a unique execution ID."""
    random_bytes = secrets.token_hex(16)
    return f"exec-{random_bytes}"


def generate_state_history_id(execution_id: str, state_name: str, sequence_number: int) -> str:
    """Generates a unique state history ID."""
    random_bytes = secrets.token_hex(4)
    return f"{execution_id}-{state_name}-{sequence_number}-{random_bytes}"


def generate_history_id(execution_id: str, state_name: str, timestamp: datetime) -> str:
    """Generates a unique history ID based on timestamp."""
    timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)
    return f"{execution_id}-{state_name}-{timestamp_ns}"


def new_execution(state_machine_id: str, name: str, input_data: Optional[Dict[str, Any]] = None) -> Execution:
    """Creates a new execution with default values."""
    return Execution(
        id=generate_execution_id(),
        state_machine_id=state_machine_id,
        name=name,
        input=input_data or {},
        status=ExecutionStatus.RUNNING,
        start_time=datetime.utcnow(),
        current_state="",
        metadata={},
    )


def new_state_history(
    execution_id: str,
    state_name: str,
    state_type: str,
    input_data: Optional[Dict[str, Any]],
    sequence_number: int,
) -> StateHistory:
    """Creates a new state history entry."""
    return StateHistory(
        id=generate_state_history_id(execution_id, state_name, sequence_number),
        execution_id=execution_id,
        state_name=state_name,
        state_type=state_type,
        input=input_data or {},
        status=StateHistoryStatus.RUNNING,
        start_time=datetime.utcnow(),
        sequence_number=sequence_number,
        retry_count=0,
        metadata={},
    )
