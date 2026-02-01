"""
Session store: get/set conversation state by session_id.
In-memory implementation for M2; M3 will add Redis.
"""
from __future__ import annotations

from typing import Protocol

from orchestrator.state_machine import ConversationState


class SessionStore(Protocol):
    """Abstract session store; implement with in-memory dict or Redis in M3."""

    def get(self, session_id: str) -> ConversationState | None: ...
    def set(self, session_id: str, state: ConversationState) -> None: ...


class InMemorySessionStore:
    """In-memory session store. Stateless API pods would use Redis (M3)."""
    _store: dict[str, dict]

    def __init__(self) -> None:
        self._store = {}

    def get(self, session_id: str) -> ConversationState | None:
        data = self._store.get(session_id)
        if data is None:
            return None
        return ConversationState.from_dict(data)

    def set(self, session_id: str, state: ConversationState) -> None:
        self._store[session_id] = state.to_dict()


# Default store for the app; can be replaced with Redis store in M3
default_store: SessionStore = InMemorySessionStore()
