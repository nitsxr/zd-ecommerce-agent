"""Session state schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """A single turn in the conversation."""

    role: Literal["user", "assistant"] = Field(description="Who sent this message")
    content: str = Field(description="The message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent: str | None = Field(default=None, description="Which agent handled this (for assistant turns)")


class ExtractedEntities(BaseModel):
    """Entities extracted from the conversation."""

    order_ids: list[str] = Field(default_factory=list, description="Order IDs mentioned (most recent first)")
    products: list[str] = Field(default_factory=list, description="Products mentioned")
    issues: list[str] = Field(default_factory=list, description="Issues identified (e.g., cancellation_request)")


class SessionState(BaseModel):
    """Complete session state persisted in Redis."""

    session_id: str = Field(description="Unique session identifier")
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list, description="List of conversation turns"
    )
    extracted_entities: ExtractedEntities = Field(
        default_factory=ExtractedEntities, description="Entities extracted from conversation"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = Field(default=1800, description="Session TTL in seconds (default 30 min)")

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history."""
        self.conversation_history.append(
            ConversationTurn(role="user", content=content)
        )
        self.updated_at = datetime.utcnow()

    def add_assistant_message(self, content: str, agent: str) -> None:
        """Add an assistant message to the conversation history."""
        self.conversation_history.append(
            ConversationTurn(role="assistant", content=content, agent=agent)
        )
        self.updated_at = datetime.utcnow()
