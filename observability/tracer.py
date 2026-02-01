"""Trace event storage and retrieval."""

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from observability.context import get_correlation_id
from observability.logger import get_logger
from schemas.trace import TraceEvent

logger = get_logger(__name__)


class Tracer:
    """Stores and retrieves trace events in Redis."""

    def __init__(self, redis_url: str):
        """Initialize tracer with Redis connection."""
        self.redis_url = redis_url
        self._client: redis.Redis | None = None
        self._trace_prefix = "trace:"
        self._trace_ttl = 86400  # 24 hours

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
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    def _trace_key(self, session_id: str) -> str:
        """Generate Redis key for session traces."""
        return f"{self._trace_prefix}{session_id}"

    async def record(
        self,
        session_id: str,
        event_type: str,
        action: str,
        agent: str | None = None,
        duration_ms: int | None = None,
        tokens_used: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceEvent:
        """
        Record a trace event.

        Args:
            session_id: Session ID
            event_type: Type of event (request_received, agent_called, etc.)
            action: Description of the action
            agent: Agent name if applicable
            duration_ms: Duration in milliseconds
            tokens_used: LLM tokens used
            metadata: Additional event data

        Returns:
            The created TraceEvent
        """
        event = TraceEvent(
            timestamp=datetime.utcnow(),
            session_id=session_id,
            correlation_id=get_correlation_id(),
            event_type=event_type,
            agent=agent,
            action=action,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            metadata=metadata or {},
        )

        try:
            client = await self._get_client()
            key = self._trace_key(session_id)

            # Append to list
            await client.rpush(key, event.model_dump_json())

            # Set TTL on first event
            await client.expire(key, self._trace_ttl)

            logger.debug(
                "Trace event recorded",
                session_id=session_id,
                event_type=event_type,
                action=action,
            )

        except RedisError as e:
            logger.error("Failed to record trace event", error=str(e))
            # Don't raise - tracing failures shouldn't break the flow

        return event

    async def get_trace(self, session_id: str) -> list[TraceEvent]:
        """
        Get all trace events for a session.

        Args:
            session_id: Session ID

        Returns:
            List of TraceEvents in chronological order
        """
        try:
            client = await self._get_client()
            key = self._trace_key(session_id)

            raw_events = await client.lrange(key, 0, -1)

            events = []
            for raw in raw_events:
                try:
                    data = json.loads(raw)
                    events.append(TraceEvent.model_validate(data))
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning("Failed to parse trace event", error=str(e))

            return events

        except RedisError as e:
            logger.error("Failed to get trace", session_id=session_id, error=str(e))
            return []

    async def get_trace_summary(self, session_id: str) -> dict[str, Any]:
        """
        Get a summary of trace events for a session.

        Returns:
            Summary with counts, total duration, total tokens, etc.
        """
        events = await self.get_trace(session_id)

        if not events:
            return {"session_id": session_id, "event_count": 0}

        total_duration = sum(e.duration_ms or 0 for e in events)
        total_tokens = sum(e.tokens_used or 0 for e in events)
        agents_used = list(set(e.agent for e in events if e.agent))

        return {
            "session_id": session_id,
            "event_count": len(events),
            "total_duration_ms": total_duration,
            "total_tokens": total_tokens,
            "agents_used": agents_used,
            "first_event": events[0].timestamp.isoformat() if events else None,
            "last_event": events[-1].timestamp.isoformat() if events else None,
        }
