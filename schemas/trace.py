"""Trace event schemas for observability."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    """A single trace event for observability."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str = Field(description="Session this event belongs to")
    correlation_id: str = Field(description="Request correlation ID")
    event_type: Literal[
        "request_received",
        "memory_analysis",
        "routing_decision",
        "agent_called",
        "tool_called",
        "response_sent",
        "error",
    ] = Field(description="Type of event")
    agent: str | None = Field(default=None, description="Agent involved in this event")
    action: str = Field(description="Description of the action")
    duration_ms: int | None = Field(default=None, description="Duration in milliseconds")
    tokens_used: int | None = Field(default=None, description="LLM tokens used (if applicable)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional event data")
