"""LLM-Enhanced Memory Agent for context analysis."""

import re
import time
from typing import Literal

from pydantic import BaseModel, Field

from observability.logger import get_logger
from orchestrator.llm_client import LLMClient
from schemas.memory import (
    MemoryAnalysis,
    SentimentAnalysis,
    ExtractedEntities,
    EntityMention,
    ReferenceResolution,
)
from schemas.session import SessionState

logger = get_logger(__name__)

# Regex for order IDs
ORDER_ID_PATTERN = re.compile(r"ORD-\d+", re.IGNORECASE)


class LLMMemoryOutput(BaseModel):
    """Structured output from the Memory Agent LLM."""

    context_summary: str = Field(
        description="Brief 1-2 sentence summary of conversation context"
    )

    sentiment_score: float = Field(
        ge=-1.0, le=1.0, description="Sentiment from -1 (angry) to 1 (positive)"
    )

    sentiment_label: Literal[
        "positive", "neutral", "slightly_frustrated", "frustrated", "angry"
    ] = Field(description="Human-readable sentiment label")

    sentiment_indicators: list[str] = Field(
        default_factory=list, description="What indicates this sentiment"
    )

    urgency: Literal["low", "medium", "high", "critical"] = Field(
        description="Request urgency level"
    )

    issues_detected: list[str] = Field(
        default_factory=list, description="Issues: cancellation_request, tracking_inquiry, etc."
    )

    unresolved_from_history: list[str] = Field(
        default_factory=list, description="Unresolved issues from prior turns"
    )

    references: list[dict] = Field(
        default_factory=list,
        description="References to resolve: [{reference, resolved_to, entity_type, confidence}]",
    )

    is_correction: bool = Field(
        default=False, description="Is user correcting a previous statement?"
    )

    suggested_context: str = Field(
        default="", description="Context to pass to the handling agent"
    )

    products_mentioned: list[str] = Field(
        default_factory=list, description="Products referenced in this message"
    )


MEMORY_SYSTEM_PROMPT = """You are a Memory Agent analyzing customer service conversations.

Your job is to:
1. Summarize the conversation context
2. Detect sentiment and urgency
3. Resolve references (pronouns, "that order", "the product", ordinals)
4. Track issues and entities across turns

REFERENCE RESOLUTION RULES:
- "that order" / "the order" / "it" (when about orders) → most recently mentioned order_id
- "those" / "the product" / "them" (when about products) → most recently mentioned product
- "the first one" / "the second order" → use ordinal position from history
- "my previous question" → reference to prior turn topic

SENTIMENT SCORING:
- Polite, patient → 0.5 to 1.0 (positive/neutral)
- Normal tone → 0.0 to 0.3 (neutral)
- Slight frustration, repeated questions → -0.2 to -0.5 (slightly_frustrated)
- Clear frustration, caps, exclamation → -0.5 to -0.8 (frustrated)
- Angry, demanding, threats → -0.8 to -1.0 (angry)

URGENCY RULES:
- Baseline: low
- +1 level for: repeated failures, frustrated sentiment, time-sensitive ("urgent", "ASAP")
- +0.5 level for: caps usage, multiple exclamation marks
- Critical: angry customer + unresolved issue

Output valid JSON matching the schema."""

MEMORY_EXAMPLES = """
Example 1 - First message with order:
History: (none)
Message: "What's the status of order ORD-1234?"
Output: {"context_summary": "User asking about order ORD-1234 status", "sentiment_score": 0.1, "sentiment_label": "neutral", "sentiment_indicators": [], "urgency": "low", "issues_detected": ["tracking_inquiry"], "unresolved_from_history": [], "references": [], "is_correction": false, "suggested_context": "User wants to track order ORD-1234", "products_mentioned": []}

Example 2 - Reference resolution:
History: [User: "Track ORD-1234", Assistant: "Your order is shipped"]
Message: "Cancel that order"
Output: {"context_summary": "User wants to cancel previously discussed order ORD-1234", "sentiment_score": 0.0, "sentiment_label": "neutral", "sentiment_indicators": [], "urgency": "low", "issues_detected": ["cancellation_request"], "unresolved_from_history": [], "references": [{"reference": "that order", "resolved_to": "ORD-1234", "entity_type": "order_id", "confidence": 0.95}], "is_correction": false, "suggested_context": "User wants to cancel ORD-1234 which was just tracked (shipped status)", "products_mentioned": []}

Example 3 - Frustrated user:
History: [User: "Cancel ORD-1234", Assistant: "Cannot cancel, already shipped"]
Message: "WHY?! This is ridiculous!"
Output: {"context_summary": "User frustrated that order cannot be cancelled", "sentiment_score": -0.7, "sentiment_label": "frustrated", "sentiment_indicators": ["caps usage", "exclamation marks", "negative reaction to policy"], "urgency": "high", "issues_detected": ["complaint"], "unresolved_from_history": ["cancellation_request"], "references": [], "is_correction": false, "suggested_context": "User is frustrated about ORD-1234 cancellation denial. Handle with empathy.", "products_mentioned": []}

Example 4 - Correction:
History: [User: "Cancel ORD-1234"]
Message: "Wait, I meant ORD-1235"
Output: {"context_summary": "User correcting previous order ID from ORD-1234 to ORD-1235", "sentiment_score": 0.0, "sentiment_label": "neutral", "sentiment_indicators": [], "urgency": "low", "issues_detected": ["cancellation_request"], "unresolved_from_history": [], "references": [], "is_correction": true, "suggested_context": "User corrected order ID to ORD-1235. Process cancellation for ORD-1235, not ORD-1234.", "products_mentioned": []}

Example 5 - Product reference:
History: [User: "Tell me about wireless headphones", Assistant: "Our wireless headphones have 20hr battery..."]
Message: "What's the return policy for those?"
Output: {"context_summary": "User asking about return policy for previously discussed wireless headphones", "sentiment_score": 0.1, "sentiment_label": "neutral", "sentiment_indicators": [], "urgency": "low", "issues_detected": ["policy_inquiry"], "unresolved_from_history": [], "references": [{"reference": "those", "resolved_to": "wireless headphones", "entity_type": "product", "confidence": 0.9}], "is_correction": false, "suggested_context": "User wants return policy info specifically for wireless headphones", "products_mentioned": ["wireless headphones"]}

Example 6 - Ordinal reference:
History: [User: "Track ORD-1111", Assistant: "ORD-1111 shipped", User: "Also track ORD-2222", Assistant: "ORD-2222 pending"]
Message: "Cancel the first one"
Output: {"context_summary": "User wants to cancel ORD-1111 (the first order mentioned)", "sentiment_score": 0.0, "sentiment_label": "neutral", "sentiment_indicators": [], "urgency": "low", "issues_detected": ["cancellation_request"], "unresolved_from_history": [], "references": [{"reference": "the first one", "resolved_to": "ORD-1111", "entity_type": "order_id", "confidence": 0.9}], "is_correction": false, "suggested_context": "User wants to cancel ORD-1111 (first of two orders discussed)", "products_mentioned": []}
"""


class MemoryAgent:
    """LLM-enhanced agent for analyzing conversation context."""

    name = "MemoryAgent"

    def __init__(self, llm_client: LLMClient | None = None):
        """Initialize with LLM client."""
        self.llm_client = llm_client

    def _format_history(self, session: SessionState) -> str:
        """Format conversation history for the prompt."""
        if not session.conversation_history:
            return "(no prior conversation)"

        lines = []
        for i, turn in enumerate(session.conversation_history[-8:]):  # Last 4 exchanges
            role = "User" if turn.role == "user" else "Assistant"
            content = turn.content[:300] + "..." if len(turn.content) > 300 else turn.content
            lines.append(f"Turn {i + 1} - {role}: {content}")

        return "\n".join(lines)

    def _extract_order_ids_regex(self, text: str) -> list[str]:
        """Extract order IDs using regex."""
        matches = ORDER_ID_PATTERN.findall(text)
        return [m.upper() for m in matches]

    def _count_failures(self, session: SessionState) -> int:
        """Count consecutive failures in recent history."""
        failures = 0
        for turn in reversed(session.conversation_history):
            if turn.role == "assistant":
                content_lower = turn.content.lower()
                if any(
                    phrase in content_lower
                    for phrase in ["couldn't find", "not found", "unable to", "error"]
                ):
                    failures += 1
                else:
                    break
        return failures

    async def analyze(self, session: SessionState, message: str) -> MemoryAnalysis:
        """
        Analyze the current message in context of the conversation.

        Returns MemoryAnalysis with:
        - Context summary
        - Extracted entities
        - Sentiment analysis
        - Reference resolutions
        - Urgency assessment
        """
        start_time = time.perf_counter()
        logger.info("Memory analysis starting", message_preview=message[:50])

        # Get conversation history
        history_text = self._format_history(session)

        # Count prior failures
        failure_count = self._count_failures(session)

        # Extract order IDs via regex (fast path)
        order_ids_in_message = self._extract_order_ids_regex(message)

        # Get known entities from session
        known_order_ids = session.extracted_entities.order_ids
        known_products = session.extracted_entities.products

        # Build context for LLM
        entity_context = ""
        if known_order_ids:
            entity_context += f"Known order IDs: {', '.join(known_order_ids)}\n"
        if known_products:
            entity_context += f"Known products: {', '.join(known_products)}\n"

        messages = [
            {"role": "system", "content": MEMORY_SYSTEM_PROMPT + "\n\n" + MEMORY_EXAMPLES},
            {
                "role": "user",
                "content": f"""Conversation History:
{history_text}

{entity_context}
Current Message:
{message}

Analyze this message and output JSON:""",
            },
        ]

        try:
            llm_output, usage = await self.llm_client.complete_structured(
                messages=messages,
                response_model=LLMMemoryOutput,
                temperature=0.1,
                max_tokens=512,
            )
        except Exception as e:
            logger.error("Memory analysis LLM failed", error=str(e))
            # Return minimal analysis on failure
            return MemoryAnalysis(
                context_summary=f"User message: {message[:100]}",
                sentiment=SentimentAnalysis(
                    score=0.0, label="neutral", indicators=[]
                ),
                urgency="low",
                suggested_context_for_agent=message,
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Build extracted entities
        extracted = ExtractedEntities(
            order_ids=[
                EntityMention(
                    value=oid, turn=len(session.conversation_history), status=None
                )
                for oid in order_ids_in_message
            ],
            products=[
                EntityMention(
                    value=p, turn=len(session.conversation_history), status=None
                )
                for p in llm_output.products_mentioned
            ],
            issues=llm_output.issues_detected,
            dates=[],
        )

        # Build reference resolutions
        references = []
        for ref in llm_output.references:
            try:
                references.append(
                    ReferenceResolution(
                        reference=ref.get("reference", ""),
                        resolved_to=ref.get("resolved_to", ""),
                        entity_type=ref.get("entity_type", "order_id"),
                        confidence=ref.get("confidence", 0.8),
                    )
                )
            except Exception:
                pass

        # Adjust urgency based on failure count
        urgency = llm_output.urgency
        if failure_count >= 3:
            urgency = "high" if urgency in ("low", "medium") else urgency
        elif failure_count >= 2:
            urgency = "medium" if urgency == "low" else urgency

        analysis = MemoryAnalysis(
            context_summary=llm_output.context_summary,
            extracted_entities=extracted,
            sentiment=SentimentAnalysis(
                score=llm_output.sentiment_score,
                label=llm_output.sentiment_label,
                indicators=llm_output.sentiment_indicators,
            ),
            urgency=urgency,
            unresolved_issues=llm_output.unresolved_from_history,
            suggested_context_for_agent=llm_output.suggested_context,
            references_resolved=references,
            is_correction=llm_output.is_correction,
            failure_count=failure_count,
        )

        logger.info(
            "Memory analysis complete",
            duration_ms=duration_ms,
            sentiment=analysis.sentiment.label,
            urgency=analysis.urgency,
            references_resolved=len(references),
            tokens=usage.get("total_tokens", 0),
        )

        return analysis

    def get_resolved_message(
        self, message: str, analysis: MemoryAnalysis, session: SessionState
    ) -> str:
        """
        Get the message with references resolved to concrete values.

        E.g., "Cancel that order" → "Cancel order ORD-1234"
        """
        resolved = message

        for ref in analysis.references_resolved:
            if ref.entity_type == "order_id" and ref.confidence >= 0.7:
                # Replace references like "that order", "it", etc. with the order ID
                patterns = [
                    r"\bthat order\b",
                    r"\bthe order\b",
                    r"\bthis order\b",
                    r"\bthe first one\b",
                    r"\bthe second one\b",
                    r"\bit\b(?=.*(?:cancel|track|status))",
                ]
                for pattern in patterns:
                    if re.search(pattern, resolved, re.IGNORECASE):
                        resolved = re.sub(
                            pattern,
                            f"order {ref.resolved_to}",
                            resolved,
                            flags=re.IGNORECASE,
                        )
                        break

                # Also inject order ID if message implies an order but has none
                if not ORDER_ID_PATTERN.search(resolved) and ref.resolved_to:
                    resolved = f"{resolved} (referring to {ref.resolved_to})"

        return resolved
