"""Aggregate statistics for the stats dashboard."""

import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from observability.logger import get_logger

logger = get_logger(__name__)


class StatsCollector:
    """Collects and serves aggregate stats from Redis."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: redis.Redis | None = None
        self._key_counters = "stats:counters"
        self._key_latencies = "stats:latencies"
        self._key_agents = "stats:agents"
        self._key_sentiment = "stats:sentiment"
        self._max_latencies = 10000  # Keep last N for percentiles

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def record_request(
        self,
        duration_ms: int,
        success: bool,
        agent: str | None,
        tokens_used: int = 0,
        sentiment_label: str | None = None,
    ) -> None:
        """Record one chat request for stats."""
        try:
            client = await self._get_client()
            pipe = client.pipeline()

            pipe.hincrby(self._key_counters, "total_messages", 1)
            if success:
                pipe.hincrby(self._key_counters, "successful_messages", 1)
            pipe.hincrby(self._key_counters, "total_tokens", tokens_used)

            pipe.lpush(self._key_latencies, duration_ms)
            pipe.ltrim(self._key_latencies, 0, self._max_latencies - 1)

            if agent:
                pipe.hincrby(self._key_agents, agent, 1)

            if sentiment_label:
                pipe.hincrby(self._key_sentiment, sentiment_label, 1)

            await pipe.execute()
        except RedisError as e:
            logger.warning("Stats record failed", error=str(e))

    async def record_session_created(self) -> None:
        """Increment total sessions count."""
        try:
            client = await self._get_client()
            await client.hincrby(self._key_counters, "total_sessions", 1)
        except RedisError as e:
            logger.warning("Stats record failed", error=str(e))

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate stats for the dashboard."""
        try:
            client = await self._get_client()
            counters = await client.hgetall(self._key_counters)
            agents = await client.hgetall(self._key_agents)
            sentiment = await client.hgetall(self._key_sentiment)
            raw_latencies = await client.lrange(self._key_latencies, 0, -1)

            total_messages = int(counters.get("total_messages", 0))
            successful = int(counters.get("successful_messages", 0))
            total_tokens = int(counters.get("total_tokens", 0))
            total_sessions = int(counters.get("total_sessions", 0))

            success_rate = (successful / total_messages) if total_messages else 0

            latencies = [int(x) for x in raw_latencies if x]
            latencies.sort()
            n = len(latencies)
            if n == 0:
                avg_latency_ms = 0
                p50 = p95 = p99 = 0
            else:
                avg_latency_ms = sum(latencies) // n
                p50 = latencies[int(n * 0.5)] if n else 0
                p95 = latencies[int(n * 0.95)] if n > 1 else (latencies[0] if latencies else 0)
                p99 = latencies[int(n * 0.99)] if n > 1 else (latencies[0] if latencies else 0)

            agent_distribution = {k: int(v) for k, v in (agents or {}).items()}
            sentiment_distribution = {k: int(v) for k, v in (sentiment or {}).items()}

            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "success_rate": round(success_rate, 4),
                "avg_latency_ms": avg_latency_ms,
                "p50_latency_ms": p50,
                "p95_latency_ms": p95,
                "p99_latency_ms": p99,
                "tokens_used": total_tokens,
                "agent_distribution": agent_distribution,
                "sentiment_distribution": sentiment_distribution,
            }
        except RedisError as e:
            logger.error("Stats get failed", error=str(e))
            return {
                "total_sessions": 0,
                "total_messages": 0,
                "success_rate": 0,
                "avg_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "tokens_used": 0,
                "agent_distribution": {},
                "sentiment_distribution": {},
            }
