"""Product information agent."""

import time

from agents.base import BaseAgent, validate_response
from observability.logger import get_logger
from schemas.agent import AgentResponse, ToolCall
from schemas.session import SessionState
from tools.knowledge_base import KnowledgeBase

logger = get_logger(__name__)


class ProductInfoAgent(BaseAgent):
    """Agent for answering product and policy questions from knowledge base."""

    name = "ProductInfoAgent"

    def __init__(self, knowledge_base: KnowledgeBase | None = None):
        """Initialize with optional KnowledgeBase instance."""
        self.knowledge_base = knowledge_base or KnowledgeBase()

    @validate_response
    async def process(self, session: SessionState, message: str) -> AgentResponse:
        """
        Process a product information request.

        Searches the knowledge base for relevant FAQs and returns
        the best matching answer(s).
        """
        logger.info("Processing product info request", user_message=message[:100])

        # Search knowledge base
        start_time = time.perf_counter()
        results = await self.knowledge_base.search(message, limit=2)
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        tool_call = ToolCall(
            tool="KnowledgeBase.search",
            input={"query": message, "limit": 2},
            result={
                "count": len(results),
                "faq_ids": [r.id for r in results],
            },
            duration_ms=duration_ms,
            success=True,
        )

        # No results found
        if not results:
            return self._create_response(
                response=(
                    "I couldn't find specific information about that in our knowledge base. "
                    "Here's what I can help you with:\n\n"
                    "• Return and refund policies\n"
                    "• Shipping and delivery times\n"
                    "• Order tracking and cancellation\n"
                    "• Product specifications\n"
                    "• Warranty information\n\n"
                    "Could you rephrase your question or ask about one of these topics?"
                ),
                tool_calls=[tool_call],
                metadata={"reason": "no_results", "query": message},
            )

        # Single result - return full answer
        if len(results) == 1:
            faq = results[0]

            # Track product mention in session
            if faq.category == "products":
                for keyword in faq.keywords:
                    if keyword.lower() not in [p.lower() for p in session.extracted_entities.products]:
                        session.extracted_entities.products.insert(0, keyword)
                        break

            return self._create_response(
                response=faq.answer,
                tool_calls=[tool_call],
                confidence=0.9,
                metadata={
                    "faq_id": faq.id,
                    "faq_question": faq.question,
                    "category": faq.category,
                },
            )

        # Multiple results - combine top answers
        primary_faq = results[0]
        secondary_faq = results[1]

        # Build combined response
        response_parts = [primary_faq.answer]

        # Add secondary info if relevant and different category
        if secondary_faq.category != primary_faq.category:
            response_parts.append(
                f"\n\n**Related: {secondary_faq.question}**\n{secondary_faq.answer}"
            )

        response_text = "\n".join(response_parts)

        # Track product mentions
        for faq in results:
            if faq.category == "products":
                for keyword in faq.keywords:
                    if keyword.lower() not in [p.lower() for p in session.extracted_entities.products]:
                        session.extracted_entities.products.insert(0, keyword)
                        break

        return self._create_response(
            response=response_text,
            tool_calls=[tool_call],
            confidence=0.85,
            metadata={
                "faq_ids": [r.id for r in results],
                "primary_category": primary_faq.category,
            },
        )
