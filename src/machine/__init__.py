"""State machine package with persistent execution support."""

from .persistent_statemachine import PersistentContext, PersistentStateMachine, StateHistoryEntry, StateMachine

__all__ = [
    # Core classes
    "PersistentStateMachine",
    "PersistentContext",
    "StateHistoryEntry",
    "StateMachine"
    # State types
    # Factory function
]

__version__ = "1.0.0"
