"""Agent response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Record of a tool invocation by an agent."""

    tool: str = Field(description="Name of the tool called")
    input: dict[str, Any] = Field(description="Input parameters passed to the tool")
    result: dict[str, Any] | None = Field(default=None, description="Result returned by the tool")
    duration_ms: int | None = Field(default=None, description="Time taken in milliseconds")
    success: bool = Field(default=True, description="Whether the tool call succeeded")
    error: str | None = Field(default=None, description="Error message if failed")


class AgentResponse(BaseModel):
    """Standardized response from any agent."""

    response: str = Field(description="The response message to send to the user")
    agent: str = Field(description="Name of the agent that handled this request")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tools called during processing")
    handover: str | None = Field(
        default=None, description="Handover chain (e.g., 'OrchestratorAgent → OrderTrackingAgent')"
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Confidence score for the response"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")
