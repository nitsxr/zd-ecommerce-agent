"""
Session store: get/set conversation state by session_id.
In-memory (M2) or Redis (M3) via get_store(). Use REDIS_URL to enable Redis.
"""
from __future__ import annotations

import os
from typing import Protocol

from orchestrator.state_machine import ConversationState


class SessionStore(Protocol):
    """Abstract session store; implement with in-memory dict or Redis."""

    def get(self, session_id: str) -> ConversationState | None: ...
    def set(self, session_id: str, state: ConversationState) -> None: ...


class InMemorySessionStore:
    """In-memory session store. Used when REDIS_URL is not set."""
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


def get_store() -> SessionStore:
    """
    Return session store: Redis if REDIS_URL is set, else in-memory.
    Stateless API pods set REDIS_URL for session recovery across instances.
    """
    if os.environ.get("REDIS_URL"):
        from memory.redis_store import RedisSessionStore
        return RedisSessionStore()
    return InMemorySessionStore()


# Default store: Redis when REDIS_URL set, else in-memory
default_store: SessionStore = get_store()
