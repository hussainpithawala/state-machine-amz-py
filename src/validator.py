"""
Validator for state machine definitions.

Validates state machine structure and state configurations.
"""

from typing import Any, Dict, Optional, Set


class StateMachineValidator:
    """
    Validator for Amazon States Language state machines.

    Validates state machine structure, state transitions, and configurations.
    """

    def validate(
        self,
        start_at: str,
        states: Dict[str, Any],
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """
        Validate a state machine definition.

        Args:
            start_at: Starting state name
            states: Dictionary of states
            timeout_seconds: Optional timeout in seconds

        Raises:
            ValueError: If validation fails
        """
        # Validate basic requirements
        if not start_at:
            raise ValueError("StartAt is required")

        if not states:
            raise ValueError("States cannot be empty")

        # Validate StartAt references existing state
        if start_at not in states:
            raise ValueError(f"StartAt state '{start_at}' not found in States")

        # Validate timeout
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("TimeoutSeconds must be positive")

        # Validate each state
        for state_name, state in states.items():
            self._validate_state(state_name, state, states)

        # Validate state machine has at least one terminal state
        self._validate_terminal_states(states)

        # Validate all referenced states exist
        self._validate_state_references(states)

        # Check for unreachable states
        self._validate_reachability(start_at, states)

    def _validate_state(self, state_name: str, state: Any, all_states: Dict[str, Any]) -> None:
        """
        Validate a single state.

        Args:
            state_name: Name of the state
            state: State object
            all_states: All states in the machine
        """
        # State must have either End or Next (unless it's a terminal state type)
        state_type = state.state_type

        # Terminal state types
        terminal_types = {"Fail", "Succeed"}

        if state_type not in terminal_types:
            if not state.is_end() and state.get_next() is None:
                raise ValueError(f"State '{state_name}' must have either Next or End set")

            # Cannot have both End and Next
            if state.is_end() and state.get_next() is not None:
                raise ValueError(f"State '{state_name}' cannot have both Next and End set")

    def _validate_terminal_states(self, states: Dict[str, Any]) -> None:
        """
        Validate that state machine has at least one terminal state.

        Args:
            states: Dictionary of states

        Raises:
            ValueError: If no terminal states found
        """
        has_terminal = False
        for state in states.values():
            if state.is_end() or state.state_type in {"Fail", "Succeed"}:
                has_terminal = True
                break

        if not has_terminal:
            raise ValueError("State machine must have at least one terminal state")

    def _validate_state_references(self, states: Dict[str, Any]) -> None:
        """
        Validate all state references point to existing states.

        Args:
            states: Dictionary of states

        Raises:
            ValueError: If invalid references found
        """
        for state_name, state in states.items():
            # Check Next reference
            next_state = state.get_next()
            if next_state is not None and next_state not in states:
                raise ValueError(f"State '{state_name}' references non-existent state '{next_state}'")

            # Check state-specific references
            self._validate_state_specific_references(state_name, state, states)

    def _validate_state_specific_references(self, state_name: str, state: Any, all_states: Dict[str, Any]) -> None:
        """
        Validate state-specific references (e.g., Choice, Parallel).

        Args:
            state_name: Name of the state
            state: State object
            all_states: All states in the machine
        """
        state_type = state.state_type

        # Validate Choice state
        if state_type == "Choice":
            if hasattr(state, "default") and state.default:
                if state.default not in all_states:
                    raise ValueError(f"Choice state '{state_name}' default '{state.default}' " "not found")

            if hasattr(state, "choices"):
                for i, choice in enumerate(state.choices):
                    if hasattr(choice, "next") and choice.next not in all_states:
                        raise ValueError(
                            f"Choice state '{state_name}' choice {i} " f"references non-existent state '{choice.next}'"
                        )

        # Validate Task state Catch
        if state_type == "Task" and hasattr(state, "catch"):
            for i, catch in enumerate(state.catch):
                if catch.next_state not in all_states:
                    raise ValueError(
                        f"Task state '{state_name}' catch {i} " f"references non-existent state '{catch.next_state}'"
                    )

    def _validate_reachability(self, start_at: str, states: Dict[str, Any]) -> None:
        """
        Validate all states are reachable from StartAt.

        Args:
            start_at: Starting state name
            states: Dictionary of states

        Note:
            This is a warning validation - unreachable states are allowed
            but may indicate a configuration error.
        """
        reachable: Set[str] = set()
        to_visit = [start_at]

        while to_visit:
            current = to_visit.pop()
            if current in reachable:
                continue

            reachable.add(current)

            if current not in states:
                continue

            state = states[current]

            # Add next states
            next_states = self._get_next_states(state)
            to_visit.extend(next_states)

        # Check for unreachable states
        unreachable = set(states.keys()) - reachable
        if unreachable:
            # This is informational - not an error
            # In production, you might want to log this as a warning
            pass

    def _get_next_states(self, state: Any) -> list[str]:
        """
        Get all possible next states from a state.

        Args:
            state: State object

        Returns:
            List of next state names
        """
        next_states = []

        # Get primary next state
        if hasattr(state, "get_next_states"):
            next_states.extend(state.get_next_states())
        elif state.get_next() is not None:
            next_states.append(state.get_next())

        return next_states
