"""
Task state implementation for Amazon States Language.

Based on the Go implementation with Python-specific enhancements.
"""

from __future__ import annotations

import asyncio
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from .base import BaseState, CatchRule, RetryRule, StateError

# Context key for execution context
EXECUTION_CONTEXT_KEY = "execution_context"


@runtime_checkable
class TaskHandler(Protocol):
    """Protocol for task execution handlers."""

    async def execute(
        self,
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute the task and return the result."""
        ...

    async def execute_with_timeout(
        self,
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute the task with a specific timeout."""
        ...

    def can_handle(self, resource: str) -> bool:
        """Check if this handler can handle the resource."""
        ...


@runtime_checkable
class ExecutionContext(Protocol):
    """Protocol for execution context that provides task handlers."""

    # def get_task_handler(self, resource: str) -> Optional[Callable[[Any], Any]]:
    #     """Get a task handler for the given resource."""
    #     ...
    def get_task_handler(self, resource: str) -> TaskHandler | Optional[Callable]:
        """Get a task handler for the given resource."""
        ...


class AbstractTaskHandler(ABC):
    async def execute(
        self,
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        raise NotImplementedError("Implement me..")

    async def execute_with_timeout(
        self,
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        raise NotImplementedError("Implement me..")


class DefaultTaskHandler:
    """Default task handler that delegates to execution context."""

    async def execute(
        self,
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute task by delegating to execution context handler."""
        if context is None:
            context = {}

        # Try to get execution context
        exec_ctx = context.get(EXECUTION_CONTEXT_KEY)
        if exec_ctx is not None and isinstance(exec_ctx, ExecutionContext):
            # Get handler from execution context
            handler: TaskHandler | Optional[Callable] = exec_ctx.get_task_handler(resource)
            if handler is not None:
                # Apply parameters if provided
                if parameters is not None:
                    from .json_path import JSONPathProcessor

                    processor = JSONPathProcessor()
                    processor.expand_value(parameters, {"$": input_data})
                if callable(handler):
                    if asyncio.iscoroutinefunction(handler):
                        return await handler(resource, input_data, parameters)
                    else:
                        return handler(resource, input_data, parameters)
                else:
                    # Execute the registered handler
                    if asyncio.iscoroutinefunction(handler.execute):
                        return await handler.execute(resource, input_data, parameters)
                    else:
                        return handler.execute(resource, input_data, parameters)

        # Fallback: return input as-is
        return input_data

    async def execute_with_timeout(
        self,
        resource: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute task with timeout."""
        if timeout_seconds is None or timeout_seconds <= 0:
            return await self.execute(resource, input_data, parameters, context)

        try:
            return await asyncio.wait_for(
                self.execute(resource, input_data, parameters, context),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise StateError(
                f"Task execution timed out after {timeout_seconds} seconds",
                error_type="States.Timeout",
            )

    def can_handle(self, resource: str) -> bool:
        """Default handler can handle any resource."""
        return True


@dataclass
class TaskState(BaseState):
    """
    Task state for executing work in state machines.

    Task states execute work by calling a task handler with the input data.
    """

    name: str = field(default="", repr=False)
    resource: str = field(default="", repr=False)
    parameters: Optional[Dict[str, Any]] = field(default=None, repr=False)
    timeout_seconds: Optional[int] = field(default=None, repr=False)
    heartbeat_seconds: Optional[int] = field(default=None, repr=False)
    retry: List[RetryRule] = field(default_factory=list, repr=False)
    catch: List[CatchRule] = field(default_factory=list, repr=False)
    result_selector: Optional[Dict[str, Any]] = field(default=None, repr=False)
    task_handler: Optional[TaskHandler] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Initialize task state."""
        self.type = "Task"
        self.validate(skip_type=True, skip_next_state=False)

    def validate(self, skip_name=False, skip_type=False, skip_next_state=False) -> None:
        """Validate task state configuration."""
        super().validate(skip_type, skip_next_state)

        self._validate_resource()
        self._validate_timeout_seconds()
        self._validate_heartbeat_seconds()
        self._validate_heartbeat_less_than_timeout()
        self._validate_retry_policies()
        self._validate_catch_policies()

    def _validate_resource(self) -> None:
        if not self.resource:
            raise ValueError(f"Task state '{self.name}' Resource is required")

    def _validate_timeout_seconds(self) -> None:
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError(f"Task state '{self.name}' TimeoutSeconds must be positive")

    def _validate_heartbeat_seconds(self) -> None:
        if self.heartbeat_seconds is not None and self.heartbeat_seconds <= 0:
            raise ValueError(f"Task state '{self.name}' HeartbeatSeconds must be positive")

    def _validate_heartbeat_less_than_timeout(self) -> None:
        if (
            self.heartbeat_seconds is not None
            and self.timeout_seconds is not None
            and self.heartbeat_seconds >= self.timeout_seconds
        ):
            raise ValueError(f"Task state '{self.name}' HeartbeatSeconds must be less than TimeoutSeconds")

    def _validate_retry_policies(self) -> None:
        for i, retry_policy in enumerate(self.retry):
            if not retry_policy.error_equals:
                raise ValueError(f"Task state '{self.name}' Retry policy {i}: ErrorEquals is required")
            if retry_policy.backoff_rate < 1.0:
                raise ValueError(f"Task state '{self.name}' Retry policy {i}: BackoffRate must be >= 1.0")

    def _validate_catch_policies(self) -> None:
        for i, catch_policy in enumerate(self.catch):
            if not catch_policy.error_equals:
                raise ValueError(f"Task state '{self.name}' Catch policy {i}: ErrorEquals is required")
            if not catch_policy.next_state:
                raise ValueError(f"Task state '{self.name}' Catch policy {i}: Next is required")

    async def execute(
        self, input_data: Optional[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> tuple[Any, Optional[str]]:
        """Execute the task state."""
        if context is None:
            context = {}

        try:
            # Prepare input and parameters
            processor, task_input, processed_input = self._prepare_input(input_data)

            # Get ExecutionContext from context or fallback to default handler
            _exec_context: Any = context.get(EXECUTION_CONTEXT_KEY)
            # Need to double check to avoid type-casting issues reported by mypy
            if _exec_context and _exec_context.__class__.__name__ == "ExecutionContext":
                handler = _exec_context.get_task_handler(self.resource)
                if handler is None:
                    handler = self._get_task_handler()
            else:
                handler = self._get_task_handler()

            # Execute task with retry logic
            result, task_error = await self._execute_with_retry(handler, task_input, context)

            # Handle task result
            return await self._handle_task_result(processor, processed_input, result, task_error, context)

        except Exception as e:
            if isinstance(e, StateError):
                raise
            raise StateError(f"Task execution failed: {str(e)}", self.name, "States.TaskFailed")

    def _prepare_input(self, input_data: Any) -> tuple[Any, Any, Any]:
        """Prepare input by applying input path and parameters."""
        from .json_path import JSONPathProcessor

        processor = JSONPathProcessor()

        # Apply input path
        processed_input = processor.apply_input_path(input_data, self.input_path)

        # Prepare parameters if provided
        task_input = processed_input
        if self.parameters is not None:
            task_input = processor.expand_value(self.parameters, {"$": processed_input})

        return processor, task_input, processed_input

    def _get_task_handler(self) -> TaskHandler:
        """Get the appropriate task handler."""
        if self.task_handler is not None:
            return self.task_handler
        return DefaultTaskHandler()

    async def _execute_with_retry(
        self, handler: TaskHandler, task_input: Any, context: Dict[str, Any]
    ) -> tuple[Any, Optional[Exception]]:
        """Execute task with retry logic."""
        result = None
        max_attempts = self._calculate_max_attempts()
        backoff_duration = 1.0  # seconds

        for attempt in range(max_attempts + 1):
            try:
                # Execute task
                if hasattr(handler, "execute_with_timeout"):
                    result = await handler.execute_with_timeout(
                        self.resource,
                        task_input,
                        self.parameters,
                        self.timeout_seconds,
                        context,
                    )
                elif hasattr(handler, "execute"):
                    result = await handler.execute(self.resource, task_input, self.parameters)
                elif callable(handler):
                    result = await handler(self.resource, task_input, self.parameters)
                else:
                    raise ValueError("Invalid task handler")

                return result, None

            except Exception as task_error:
                # Check if we should retry
                should_retry = self._should_retry(task_error, attempt, max_attempts)
                if not should_retry:
                    return None, task_error

                # Calculate backoff duration
                backoff_duration = self._calculate_backoff_duration(task_error, backoff_duration)

                # Wait before retrying
                await asyncio.sleep(backoff_duration)

        return None, StateError("Max retry attempts exceeded", self.name)

    def _calculate_max_attempts(self) -> int:
        """Calculate maximum retry attempts."""
        max_attempts = 0
        for retry_policy in self.retry:
            if retry_policy.max_attempts is not None and retry_policy.max_attempts > 0:
                max_attempts = retry_policy.max_attempts
                break
        return max_attempts

    def _should_retry(self, task_error: Exception, attempt: int, max_attempts: int) -> bool:
        """Determine if task should be retried."""
        if attempt >= max_attempts:
            return False

        # Check if error matches any retry policy
        for retry_policy in self.retry:
            if self._error_matches(task_error, retry_policy.error_equals):
                return True

        return False

    def _calculate_backoff_duration(self, task_error: Exception, current_duration: float) -> float:
        """Calculate backoff duration for retries."""
        duration = current_duration

        for retry_policy in self.retry:
            if self._error_matches(task_error, retry_policy.error_equals):
                # Apply interval seconds if this is the first retry
                if current_duration == 1.0:
                    duration = float(retry_policy.interval_seconds)

                # Apply backoff rate
                if retry_policy.backoff_rate > 1.0:
                    duration = duration * retry_policy.backoff_rate

                # Apply max delay limit
                if retry_policy.max_delay_seconds is not None:
                    max_duration = float(retry_policy.max_delay_seconds)
                    if duration > max_duration:
                        duration = max_duration
                break

        return duration

    async def _handle_task_result(
        self,
        processor: Any,
        processed_input: Any,
        result: Any,
        task_error: Optional[Exception],
        context: Dict[str, Any],
    ) -> tuple[Any, Optional[str]]:
        """Handle task result or error."""
        if task_error is not None:
            return self._handle_task_failure(processor, processed_input, task_error, context)

        return self._process_successful_result(processor, processed_input, result)

    def _handle_task_failure(
        self,
        processor: Any,
        processed_input: Any,
        task_error: Exception,
        context: Dict[str, Any],
    ) -> tuple[Any, Optional[str]]:
        """Handle task failure with catch policies."""
        # Check catch policies
        for catch_policy in self.catch:
            if self._error_matches(task_error, catch_policy.error_equals):
                return self._handle_caught_error(processor, processed_input, task_error, catch_policy)

        # No catch policy matched, raise error
        raise task_error

    def _handle_caught_error(
        self,
        processor: Any,
        processed_input: Any,
        task_error: Exception,
        catch_policy: CatchRule,
    ) -> tuple[Any, Optional[str]]:
        """Handle error caught by catch policy."""
        # Create error result
        error_result = {
            "Error": str(task_error),
            "Cause": str(task_error),
        }

        # Apply result path
        output = processor.apply_result_path(processed_input, error_result, catch_policy.result_path)

        return output, catch_policy.next_state

    def _process_successful_result(
        self, processor: Any, processed_input: Any, result: Any
    ) -> tuple[Any, Optional[str]]:
        """Process successful task result."""
        output = result

        # Apply result selector if provided
        if self.result_selector is not None:
            output = processor.expand_value(self.result_selector, {"$": result})

        # Apply result path
        output = processor.apply_result_path(processed_input, output, self.result_path)

        # Apply output path
        output = processor.apply_output_path(output, self.output_path)

        return output, self.next_state

    def _error_matches(self, error: Exception, error_patterns: List[str]) -> bool:
        """Check if error matches any of the error patterns."""
        error_msg = str(error)
        error_type = getattr(error, "error_type", None) or type(error).__name__

        for pattern in error_patterns:
            if pattern == "States.ALL":
                return True
            if pattern == error_msg or pattern == error_type:
                return True
            # Check if error message contains pattern
            if pattern in error_msg:
                return True

        return False

    def get_next_states(self) -> List[str]:
        """Get all possible next states."""
        next_states = []

        if self.next_state is not None:
            next_states.append(self.next_state)

        # Add all catch destinations
        for catch_policy in self.catch:
            next_states.append(catch_policy.next_state)

        return next_states

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = super().to_dict()

        result["Resource"] = self.resource

        if self.parameters is not None:
            result["Parameters"] = self.parameters

        if self.timeout_seconds is not None:
            result["TimeoutSeconds"] = self.timeout_seconds

        if self.heartbeat_seconds is not None:
            result["HeartbeatSeconds"] = self.heartbeat_seconds

        if self.retry:
            result["Retry"] = [r.to_dict() for r in self.retry]

        if self.catch:
            result["Catch"] = [c.to_dict() for c in self.catch]

        if self.result_selector is not None:
            result["ResultSelector"] = self.result_selector

        return result


def with_execution_context(context: Dict[str, Any], exec_ctx: ExecutionContext) -> Dict[str, Any]:
    """Add execution context to context dictionary."""
    context[EXECUTION_CONTEXT_KEY] = exec_ctx
    return context
