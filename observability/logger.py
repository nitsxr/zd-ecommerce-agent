"""
Structured logging for key events.
Log format: JSON or key-value for easy parsing. No PII in trace logs.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Default: stdout, JSON lines
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
_log = logging.getLogger("ecommerce_assistant")
_log.setLevel(logging.INFO)
_log.addHandler(_handler)
_log.propagate = False


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(event: str, **kwargs: Any) -> None:
    """Emit a structured log line (JSON)."""
    payload = {"ts": _iso_now(), "event": event, **kwargs}
    _log.info(json.dumps(payload))


def log_turn(request_id: str, session_id: str, turn_index: int, agent: str, latency_ms: float, errors: list[str]) -> None:
    """Log a chat turn completion (trace summary, no conversation content)."""
    log_event(
        "chat_turn",
        request_id=request_id,
        session_id=session_id,
        turn_index=turn_index,
        agent=agent,
        latency_ms=round(latency_ms, 2),
        errors=errors,
    )


def log_error(event: str, error: str, **kwargs: Any) -> None:
    """Log an error event."""
    log_event(event, error=error, **kwargs)
