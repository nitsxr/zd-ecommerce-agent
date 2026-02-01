"""Memory Agent schemas for context analysis."""

from typing import Literal

from pydantic import BaseModel, Field


class EntityMention(BaseModel):
    """A mention of an entity in conversation."""

    value: str = Field(description="The entity value (e.g., 'ORD-1234')")
    turn: int = Field(description="Which conversation turn this was mentioned in")
    status: str | None = Field(default=None, description="Current known status if applicable")


class ReferenceResolution(BaseModel):
    """Resolution of a pronoun or reference to a concrete entity."""

    reference: str = Field(description="The original reference text (e.g., 'that order')")
    resolved_to: str = Field(description="What it resolved to (e.g., 'ORD-1234')")
    entity_type: Literal["order_id", "product", "topic", "turn"] = Field(
        description="Type of entity this resolved to"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this resolution")


class SentimentAnalysis(BaseModel):
    """Analysis of user sentiment."""

    score: float = Field(
        ge=-1.0, le=1.0, description="Sentiment score from -1 (negative) to 1 (positive)"
    )
    label: Literal["positive", "neutral", "slightly_frustrated", "frustrated", "angry"] = Field(
        description="Human-readable sentiment label"
    )
    indicators: list[str] = Field(
        default_factory=list,
        description="Indicators that led to this sentiment assessment",
    )


class ExtractedEntities(BaseModel):
    """Entities extracted from the current message and context."""

    order_ids: list[EntityMention] = Field(
        default_factory=list, description="Order IDs mentioned"
    )
    products: list[EntityMention] = Field(
        default_factory=list, description="Products mentioned"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Issues or intents detected (e.g., 'cancellation_request')",
    )
    dates: list[str] = Field(default_factory=list, description="Dates mentioned")


class MemoryAnalysis(BaseModel):
    """Complete analysis from the Memory Agent."""

    context_summary: str = Field(
        description="Brief summary of conversation context for the orchestrator"
    )
    extracted_entities: ExtractedEntities = Field(
        default_factory=ExtractedEntities, description="Entities extracted from this turn"
    )
    sentiment: SentimentAnalysis = Field(
        description="Current sentiment analysis"
    )
    urgency: Literal["low", "medium", "high", "critical"] = Field(
        default="low", description="Urgency level of the request"
    )
    unresolved_issues: list[str] = Field(
        default_factory=list,
        description="Issues from previous turns that remain unresolved",
    )
    suggested_context_for_agent: str = Field(
        default="",
        description="Tailored context to pass to the handling agent",
    )
    references_resolved: list[ReferenceResolution] = Field(
        default_factory=list,
        description="References resolved in this turn",
    )
    is_correction: bool = Field(
        default=False,
        description="Whether this message is correcting a previous statement",
    )
    failure_count: int = Field(
        default=0,
        description="Number of consecutive failures/errors in conversation",
    )
