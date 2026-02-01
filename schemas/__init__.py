"""Pydantic schemas for the e-commerce assistant."""

from schemas.session import SessionState, ConversationTurn, ExtractedEntities
from schemas.agent import AgentResponse, ToolCall
from schemas.api import ChatRequest, ChatResponse
from schemas.trace import TraceEvent
from schemas.memory import (
    MemoryAnalysis,
    SentimentAnalysis,
    EntityMention,
    ReferenceResolution,
    ExtractedEntities as MemoryExtractedEntities,
)

__all__ = [
    "SessionState",
    "ConversationTurn",
    "ExtractedEntities",
    "AgentResponse",
    "ToolCall",
    "ChatRequest",
    "ChatResponse",
    "TraceEvent",
    "MemoryAnalysis",
    "SentimentAnalysis",
    "EntityMention",
    "ReferenceResolution",
    "MemoryExtractedEntities",
]
