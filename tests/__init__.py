# Mock TaskHandler for testing
import asyncio
from typing import Any, Dict, Optional


class MockTaskHandler:
    """Mock implementation of TaskHandler for testing."""

    def __init__(
            self,
            execute_func=None,
            execute_with_timeout_func=None,
            can_handle_func=None,
    ):
        self.execute_func = execute_func
        self.execute_with_timeout_func = execute_with_timeout_func
        self.can_handle_func = can_handle_func

    async def execute(
            self,
            resource: str,
            input_data: Any,
            parameters: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute task."""
        if self.execute_func is not None:
            result = self.execute_func(resource, input_data, parameters)
            if asyncio.iscoroutine(result):
                return await result
            return result
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
        if self.execute_with_timeout_func is not None:
            result = self.execute_with_timeout_func(
                resource, input_data, parameters, timeout_seconds, context
            )
            if asyncio.iscoroutine(result):
                return await result
            return result

        # Default implementation - if no timeout specified, execute directly
        if timeout_seconds is None or timeout_seconds <= 0:
            return await self.execute(resource, input_data, parameters)

        try:
            return await asyncio.wait_for(
                self.execute(resource, input_data, parameters), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task timed out after {timeout_seconds} seconds")

    def can_handle(self, resource: str) -> bool:
        """Check if can handle resource."""
        if self.can_handle_func is not None:
            return self.can_handle_func(resource)
        return True
