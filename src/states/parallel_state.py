"""
Parallel state implementation for Amazon States Language.

Executes multiple branches concurrently and collects their results.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.states.base import BaseState, StateError


@dataclass
class Branch:
    """
    Represents a single branch in a Parallel state.

    Each branch is essentially a mini state machine with its own
    StartAt and States configuration.
    """

    start_at: str
    states: Dict[str, BaseState]  # Dict[str, State] but avoiding circular import
    comment: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate branch configuration."""
        if not self.start_at:
            raise ValueError("Branch StartAt is required")
        if not self.states:
            raise ValueError("Branch must have at least one state")

    def to_dict(self) -> Dict[str, Any]:
        """Convert branch to dictionary for JSON serialization."""
        result: Dict[str, Any] = {
            "StartAt": self.start_at,
            "States": {
                name: state.to_dict() if hasattr(state, "to_dict") else state for name, state in self.states.items()
            },
        }

        if self.comment is not None:
            result["Comment"] = self.comment

        return result


@dataclass
class ParallelState(BaseState):
    """
    Parallel state for executing multiple branches concurrently.

    The Parallel state executes all branches simultaneously and waits for
    all to complete. Results from all branches are collected into an array.
    """

    branches: List[Branch] = field(default_factory=list)
    result_selector: Optional[Dict[str, Any]] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize parallel state."""
        self.type = "Parallel"
        super().__post_init__()

    def validate(self, skip_name=True, skip_type=False, skip_next_state=True) -> None:
        """Validate parallel state configuration."""
        super().validate(skip_name, skip_type, skip_next_state)

        if not self.branches:
            raise ValueError(f"Parallel state '{self.type}' must have at least one branch")

        # Validate each branch
        for i, branch in enumerate(self.branches):
            if not branch.start_at:
                raise ValueError(f"Parallel state '{self.type}' branch {i}: StartAt is required")

            if not branch.states:
                raise ValueError(f"Parallel state '{self.type}' branch {i}: States must not be empty")

            # Validate that StartAt state exists
            if branch.start_at not in branch.states:
                raise ValueError(
                    f"Parallel state '{self.type}' branch {i}: " f"StartAt state '{branch.start_at}' not found"
                )

            # Validate that all states in branch have proper End or Next configuration
            for state_name, state in branch.states.items():
                state.validate()

    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> tuple[Any, Optional[str]]:
        """Execute the parallel state by running all branches concurrently."""
        if context is None:
            context = {}

        try:
            from .json_path import JSONPathProcessor

            processor = JSONPathProcessor()

            # Apply input path
            processed_input = processor.apply_input_path(input_data, self.input_path)

            # Execute all branches concurrently
            tasks = [self._execute_branch(branch, processed_input, context) for branch in self.branches]

            # Wait for all branches to complete
            results = await asyncio.gather(*tasks)

            # Combine results into an array
            output: Any = list(results)

            # Apply result selector if provided
            if self.result_selector is not None:
                output = processor.expand_value(self.result_selector, {"$": results})

            # Apply result path
            output = processor.apply_result_path(processed_input, output, self.result_path)

            # Apply output path
            output = processor.apply_output_path(output, self.output_path)

            return output, self.next_state

        except Exception as e:
            if isinstance(e, StateError):
                raise
            raise StateError(
                f"Parallel state execution failed: {str(e)}",
                "States.Runtime",
            )

    async def _execute_branch(self, branch: Branch, input_data: Any, context: Dict[str, Any]) -> Any:
        """
        Execute a single branch as a mini state machine.

        Args:
            branch: Branch to execute
            input_data: Input data for the branch
            context: Execution context

        Returns:
            Final output from the branch
        """
        current_state_name = branch.start_at
        current_input = input_data

        while True:
            # Get current state from branch
            try:
                state = branch.states[current_state_name]
            except KeyError:
                raise StateError(f'State "{current_state_name}" not found in branch States.Runtime')

            # Execute the state
            output, next_state = await state.execute(current_input, context)

            # Check if this is an end state
            if state.is_end() or next_state is None:
                # Branch execution completed
                return output

            # Move to next state
            current_state_name = next_state
            current_input = output

    def get_next_states(self) -> List[str]:
        """
        Get all possible next states.

        Note: Branch states are not included here as they're internal
        to the Parallel state.
        """
        if self.next_state is not None:
            return [self.next_state]
        return []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = super().to_dict()

        result["Branches"] = [branch.to_dict() for branch in self.branches]

        if self.result_selector is not None:
            result["ResultSelector"] = self.result_selector

        return result

    @classmethod
    def from_dict(cls, state_dict: Dict[str, Any], state_factory=None) -> ParallelState:
        """
        Create ParallelState from dictionary.

        Args:
            name: State name
            state_dict: Dictionary representation
            state_factory: Optional factory for creating states in branches

        Returns:
            ParallelState instance
        """
        # Extract base fields
        next_state = state_dict.get("Next")
        end = state_dict.get("End", False)
        input_path = state_dict.get("InputPath")
        result_path = state_dict.get("ResultPath")
        output_path = state_dict.get("OutputPath")
        comment = state_dict.get("Comment")
        result_selector = state_dict.get("ResultSelector")

        # Parse branches
        branches = []
        for branch_dict in state_dict.get("Branches", []):
            branch = cls._parse_branch(branch_dict, state_factory)
            branches.append(branch)

        return cls(
            next_state=next_state,
            end=end,
            input_path=input_path,
            result_path=result_path,
            output_path=output_path,
            comment=comment,
            branches=branches,
            result_selector=result_selector,
        )

    @staticmethod
    def _parse_branch(branch_dict: Dict[str, Any], state_factory=None) -> Branch:
        """
        Parse a branch from dictionary.

        Args:
            branch_dict: Branch dictionary
            state_factory: Optional factory for creating states

        Returns:
            Branch instance
        """
        start_at = branch_dict.get("StartAt", "")
        comment = branch_dict.get("Comment")
        states_dict = branch_dict.get("States", {})

        # Parse states in the branch
        states = {}
        if state_factory is not None:
            for state_name, state_data in states_dict.items():
                state = state_factory.create_state(state_name, state_data)
                states[state_name] = state
        else:
            # If no factory, just store the raw dict (for testing)
            states = states_dict

        return Branch(start_at=start_at, states=states, comment=comment)


def create_branch(start_at: str, states: Dict[str, Any], comment: Optional[str] = None) -> Branch:
    """
    Helper function to create a Branch.

    Args:
        start_at: Starting state name
        states: Dictionary of state objects
        comment: Optional comment

    Returns:
        Branch instance
    """
    return Branch(start_at=start_at, states=states, comment=comment)
