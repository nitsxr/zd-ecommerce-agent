"""API request/response schemas."""

from typing import Any

from pydantic import BaseModel, Field

from schemas.agent import ToolCall


class ChatRequest(BaseModel):
    """Request payload for POST /chat endpoint."""

    session_id: str = Field(description="Session identifier for conversation continuity")
    message: str = Field(description="User's message")


class ChatResponse(BaseModel):
    """Response payload from POST /chat endpoint."""

    session_id: str = Field(description="Session identifier")
    response: str = Field(description="Assistant's response message")
    agent: str = Field(description="Name of the agent that handled this request")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tools called during processing")
    handover: str | None = Field(
        default=None, description="Handover chain (e.g., 'OrchestratorAgent → OrderTrackingAgent')"
    )
    confidence: float | None = Field(default=None, description="Confidence score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HealthResponse(BaseModel):
    """Response payload for GET /health endpoint."""

    status: str = Field(description="Overall health status")
    redis: str = Field(description="Redis connection status")
    version: str = Field(default="1.0.0", description="API version")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(description="Error message")
    detail: str | None = Field(default=None, description="Additional error details")
    correlation_id: str | None = Field(default=None, description="Request correlation ID for debugging")
