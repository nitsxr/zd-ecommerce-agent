"""Redis implementation of session store."""

import json
import logging
from datetime import datetime

import redis.asyncio as redis
from redis.exceptions import RedisError

from memory.session_store import SessionSummary
from schemas.session import SessionState

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """Redis-backed session store with TTL support."""

    def __init__(self, redis_url: str, default_ttl: int = 1800):
        """
        Initialize Redis session store.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
            default_ttl: Default TTL in seconds (default 30 minutes)
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._client: redis.Redis | None = None
        self._session_prefix = "session:"
        self._session_index = "sessions:index"

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for a session."""
        return f"{self._session_prefix}{session_id}"

    async def get_session(self, session_id: str) -> SessionState | None:
        """Retrieve a session by ID."""
        try:
            client = await self._get_client()
            data = await client.get(self._session_key(session_id))

            if data is None:
                logger.debug(f"Session not found: {session_id}")
                return None

            session_dict = json.loads(data)
            session = SessionState.model_validate(session_dict)
            logger.debug(f"Session retrieved: {session_id}")
            return session

        except RedisError as e:
            logger.error(f"Redis error getting session {session_id}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid session data for {session_id}: {e}")
            return None

    async def save_session(self, session: SessionState) -> None:
        """Save or update a session with TTL."""
        try:
            client = await self._get_client()
            key = self._session_key(session.session_id)
            ttl = session.ttl_seconds or self.default_ttl

            # Update timestamp
            session.updated_at = datetime.utcnow()

            # Serialize and save with TTL
            data = session.model_dump_json()
            await client.setex(key, ttl, data)

            # Update session index (sorted set by updated_at)
            await client.zadd(
                self._session_index,
                {session.session_id: session.updated_at.timestamp()},
            )

            logger.debug(f"Session saved: {session.session_id} (TTL: {ttl}s)")

        except RedisError as e:
            logger.error(f"Redis error saving session {session.session_id}: {e}")
            raise

    async def delete_session(self, session_id: str) -> None:
        """Delete a session by ID."""
        try:
            client = await self._get_client()
            key = self._session_key(session_id)

            await client.delete(key)
            await client.zrem(self._session_index, session_id)

            logger.debug(f"Session deleted: {session_id}")

        except RedisError as e:
            logger.error(f"Redis error deleting session {session_id}: {e}")
            raise

    async def list_sessions(self, limit: int = 100) -> list[SessionSummary]:
        """List recent sessions, ordered by last update (newest first)."""
        try:
            client = await self._get_client()

            # Get session IDs from sorted set (newest first)
            session_ids = await client.zrevrange(self._session_index, 0, limit - 1)

            summaries = []
            for session_id in session_ids:
                session = await self.get_session(session_id)
                if session:
                    summaries.append(
                        SessionSummary(
                            session_id=session.session_id,
                            message_count=len(session.conversation_history),
                            created_at=session.created_at.isoformat(),
                            updated_at=session.updated_at.isoformat(),
                        )
                    )

            return summaries

        except RedisError as e:
            logger.error(f"Redis error listing sessions: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Redis is healthy and connected."""
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False
