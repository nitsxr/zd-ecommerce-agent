"""Test scenario and run result schemas."""

from pydantic import BaseModel, Field


class TestTurn(BaseModel):
    """A single turn in a test scenario."""

    message: str = Field(description="User message to send")
    expect_agent: str | None = Field(default=None, description="Expected agent name")
    expect_contains: str | None = Field(default=None, description="Response must contain this string")
    expect_not_contains: str | None = Field(default=None, description="Response must not contain this string")


class TestScenario(BaseModel):
    """A multi-turn test scenario."""

    id: str = Field(description="Unique test ID")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="", description="Optional description")
    turns: list[TestTurn] = Field(default_factory=list, description="Conversation turns")


class TurnResult(BaseModel):
    """Result of one turn execution."""

    turn_index: int = Field(description="0-based turn index")
    passed: bool = Field(description="Whether assertions passed")
    message: str = Field(description="User message sent")
    actual_response: str = Field(default="", description="Actual assistant response")
    actual_agent: str | None = Field(default=None, description="Actual agent that handled")
    reason: str | None = Field(default=None, description="Failure reason if not passed")


class TestRunResult(BaseModel):
    """Result of running a test scenario."""

    test_id: str = Field(description="Test scenario ID")
    passed: bool = Field(description="Whether all turns passed")
    session_id: str = Field(description="Session ID used for the run")
    turns: list[TurnResult] = Field(default_factory=list, description="Per-turn results")
    error: str | None = Field(default=None, description="Error message if run failed")
