"""
Trace store abstraction and emit: every /chat turn produces a trace event.
Trace != conversation data; stored separately for observability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from observability.logger import log_turn


class TraceStore(Protocol):
    """Abstract trace store; implement with in-memory list or Redis in production."""

    def append(self, trace: dict[str, Any]) -> None: ...
    def get_by_request(self, request_id: str) -> dict[str, Any] | None: ...
    def get_by_session(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]: ...


class InMemoryTraceStore:
    """In-memory trace store. Append-only; can be replaced with Redis later."""

    def __init__(self) -> None:
        self._traces: list[dict[str, Any]] = []
        self._by_request: dict[str, dict[str, Any]] = {}

    def append(self, trace: dict[str, Any]) -> None:
        request_id = trace.get("request_id")
        if request_id:
            self._by_request[request_id] = trace
        self._traces.append(trace)

    def get_by_request(self, request_id: str) -> dict[str, Any] | None:
        return self._by_request.get(request_id)

    def get_by_session(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        matching = [t for t in reversed(self._traces) if t.get("session_id") == session_id]
        return matching[:limit]


_default_trace_store: TraceStore = InMemoryTraceStore()


def set_trace_store(store: TraceStore) -> None:
    """Inject trace store (e.g. for tests or Redis)."""
    global _default_trace_store
    _default_trace_store = store


def emit_trace(trace: dict[str, Any]) -> None:
    """
    Emit turn-level trace: add ISO8601 timestamp if missing, log, and store.
    Called after every /chat turn. Trace != conversation data.
    """
    if "timestamp" not in trace:
        trace = {**trace, "timestamp": datetime.now(timezone.utc).isoformat()}
    log_turn(
        request_id=trace.get("request_id", ""),
        session_id=trace.get("session_id", ""),
        turn_index=trace.get("turn_index", 0),
        agent=trace.get("selected_agent", ""),
        latency_ms=trace.get("latency_ms", 0),
        errors=trace.get("errors", []),
    )
    _default_trace_store.append(trace)
