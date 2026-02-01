"""
Redis session store: persist ConversationState by session_id.
TTL and eviction: keys expire after session_ttl_seconds (default 24h).
Stateless API pods use this for session recovery.
"""
from __future__ import annotations

import json
import os
from typing import Any

from orchestrator.state_machine import ConversationState

# Key prefix for session keys
SESSION_KEY_PREFIX = "session:"
# Default TTL: 24 hours. Set REDIS_SESSION_TTL_SECONDS to override.
DEFAULT_SESSION_TTL_SECONDS = 24 * 3600


class RedisSessionStore:
    """
    Session store backed by Redis. Same interface as InMemorySessionStore.
    Keys: session:{session_id}. Value: JSON ConversationState.to_dict().
    TTL on every SET for eviction.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        session_ttl_seconds: int | None = None,
        key_prefix: str = SESSION_KEY_PREFIX,
    ) -> None:
        """
        redis_url: e.g. redis://localhost:6379/0. If None, reads REDIS_URL.
        session_ttl_seconds: TTL for keys. If None, reads REDIS_SESSION_TTL_SECONDS or 24h.
        """
        default_url = "redis://localhost:6379/0"
        self._redis_url = redis_url or os.environ.get("REDIS_URL", default_url)
        ttl_env = os.environ.get("REDIS_SESSION_TTL_SECONDS", str(DEFAULT_SESSION_TTL_SECONDS))
        self._ttl = session_ttl_seconds or int(ttl_env)
        self._key_prefix = key_prefix
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy connection to Redis."""
        if self._client is None:
            import redis
            self._client = redis.from_url(
                self._redis_url, decode_responses=True
            )
        return self._client

    def _key(self, session_id: str) -> str:
        return f"{self._key_prefix}{session_id}"

    def get(self, session_id: str) -> ConversationState | None:
        """Load session by session_id. None if not found or expired."""
        try:
            client = self._get_client()
            raw = client.get(self._key(session_id))
        except Exception:
            return None
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return ConversationState.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def set(self, session_id: str, state: ConversationState) -> None:
        """Save session state and set TTL for eviction."""
        key = self._key(session_id)
        value = json.dumps(state.to_dict())
        try:
            client = self._get_client()
            client.set(key, value, ex=self._ttl)
        except Exception:
            raise

    def delete(self, session_id: str) -> bool:
        """Remove session (e.g. testing). True if key was deleted."""
        try:
            client = self._get_client()
            return client.delete(self._key(session_id)) > 0
        except Exception:
            return False
