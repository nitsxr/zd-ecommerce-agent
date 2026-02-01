"""LLM-based orchestrator for routing requests to agents."""

import time
from typing import Literal

from pydantic import BaseModel, Field

from agents.base import BaseAgent, AgentError
from observability.logger import get_logger
from orchestrator.llm_client import LLMClient
from schemas.agent import AgentResponse, ToolCall
from schemas.session import SessionState

logger = get_logger(__name__)


class RoutingDecision(BaseModel):
    """Structured output from the routing LLM."""

    intent: Literal[
        "order_tracking",
        "order_cancellation",
        "product_info",
        "escalation",
        "greeting",
        "thanks",
        "unknown",
    ] = Field(description="The detected user intent")

    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for the routing decision"
    )

    reasoning: str = Field(description="Brief explanation of why this intent was chosen")

    extracted_entities: dict = Field(
        default_factory=dict,
        description="Entities extracted from the message (order_id, product, etc.)",
    )

    requires_clarification: bool = Field(
        default=False, description="Whether the request needs clarification"
    )

    clarification_question: str | None = Field(
        default=None, description="Question to ask if clarification needed"
    )


ROUTING_SYSTEM_PROMPT = """You are a routing assistant for an e-commerce customer service system.

Your job is to analyze user messages and determine which specialized agent should handle the request.

Available agents:
1. **order_tracking** - For questions about order status, delivery dates, tracking numbers
2. **order_cancellation** - For requests to cancel orders (note: 24-hour cancellation policy)
3. **product_info** - For questions about products, policies (returns, shipping, warranty), FAQs

Special intents:
- **escalation** - User wants to speak to a human agent
- **greeting** - User is saying hello or starting conversation
- **thanks** - User is expressing gratitude
- **unknown** - Cannot determine intent or request is out of scope

Guidelines:
- Look for order IDs in format ORD-XXXX
- If user mentions both tracking AND cancellation, prioritize the action (cancellation)
- If message is ambiguous, set requires_clarification=true
- Be conservative with confidence - only use >0.9 for very clear intents
- For greetings/thanks, respond directly without routing to an agent

Output valid JSON matching the schema."""

ROUTING_EXAMPLES = """
Example 1:
User: "Where is my order ORD-1234?"
Response: {"intent": "order_tracking", "confidence": 0.95, "reasoning": "User asking about order location/status", "extracted_entities": {"order_id": "ORD-1234"}, "requires_clarification": false}

Example 2:
User: "I want to cancel my order"
Response: {"intent": "order_cancellation", "confidence": 0.85, "reasoning": "User wants to cancel but no order ID provided", "extracted_entities": {}, "requires_clarification": false}

Example 3:
User: "What's your return policy?"
Response: {"intent": "product_info", "confidence": 0.95, "reasoning": "User asking about store policy", "extracted_entities": {}, "requires_clarification": false}

Example 4:
User: "I have a problem with my order"
Response: {"intent": "unknown", "confidence": 0.4, "reasoning": "Vague request - could be tracking, cancellation, or complaint", "extracted_entities": {}, "requires_clarification": true, "clarification_question": "I'd be happy to help! Could you tell me more about the problem? Are you looking to track your order, cancel it, or something else?"}

Example 5:
User: "I want to speak to a real person"
Response: {"intent": "escalation", "confidence": 0.95, "reasoning": "User explicitly requesting human support", "extracted_entities": {}, "requires_clarification": false}

Example 6:
User: "Thanks for your help!"
Response: {"intent": "thanks", "confidence": 0.95, "reasoning": "User expressing gratitude", "extracted_entities": {}, "requires_clarification": false}
"""


class Orchestrator(BaseAgent):
    """LLM-based orchestrator that routes requests to specialized agents."""

    name = "OrchestratorAgent"

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        agents: dict[str, BaseAgent] | None = None,
    ):
        """
        Initialize orchestrator.

        Args:
            llm_client: LLM client for routing decisions
            agents: Dict mapping intent names to agent instances
        """
        self.llm_client = llm_client
        self.agents = agents or {}

    def register_agent(self, intent: str, agent: BaseAgent) -> None:
        """Register an agent for handling a specific intent."""
        self.agents[intent] = agent
        logger.info("Registered agent", intent=intent, agent=agent.name)

    async def _get_routing_decision(
        self, message: str, session: SessionState
    ) -> tuple[RoutingDecision, dict]:
        """
        Get routing decision from LLM.

        Returns:
            Tuple of (RoutingDecision, token_usage)
        """
        # Build context from session
        context_parts = []
        if session.conversation_history:
            recent = session.conversation_history[-4:]  # Last 2 turns
            for turn in recent:
                role = "User" if turn.role == "user" else "Assistant"
                context_parts.append(f"{role}: {turn.content[:200]}")

        context = "\n".join(context_parts) if context_parts else "No prior context"

        messages = [
            {"role": "system", "content": ROUTING_SYSTEM_PROMPT + "\n\n" + ROUTING_EXAMPLES},
            {
                "role": "user",
                "content": f"Conversation context:\n{context}\n\nCurrent message:\n{message}\n\nProvide your routing decision as JSON:",
            },
        ]

        decision, usage = await self.llm_client.complete_structured(
            messages=messages,
            response_model=RoutingDecision,
            temperature=0.1,
            max_tokens=256,
        )

        return decision, usage

    def _handle_special_intent(self, intent: str, decision: RoutingDecision) -> AgentResponse:
        """Handle special intents that don't need agent routing."""

        if intent == "escalation":
            return self._create_response(
                response=(
                    "I understand you'd like to speak with a human agent. "
                    "Here are your options:\n\n"
                    "• **Live Chat:** Available Mon-Fri 9am-6pm EST\n"
                    "• **Phone:** 1-800-555-0123 (same hours)\n"
                    "• **Email:** support@example.com (24-48hr response)\n\n"
                    "Before you go, is there anything I can quickly help you with?"
                ),
                confidence=decision.confidence,
                metadata={"intent": "escalation", "routing": "special"},
            )

        if intent == "greeting":
            return self._create_response(
                response=(
                    "Hello! I'm your e-commerce assistant. I can help you with:\n\n"
                    "• **Tracking orders** - Check status and delivery dates\n"
                    "• **Cancelling orders** - Within 24 hours of purchase\n"
                    "• **Product questions** - Policies, specs, and FAQs\n\n"
                    "How can I assist you today?"
                ),
                confidence=decision.confidence,
                metadata={"intent": "greeting", "routing": "special"},
            )

        if intent == "thanks":
            return self._create_response(
                response=(
                    "You're welcome! I'm glad I could help. "
                    "If you have any other questions in the future, don't hesitate to ask. "
                    "Have a great day!"
                ),
                confidence=decision.confidence,
                metadata={"intent": "thanks", "routing": "special"},
            )

        if intent == "unknown":
            if decision.requires_clarification and decision.clarification_question:
                return self._create_response(
                    response=decision.clarification_question,
                    confidence=decision.confidence,
                    metadata={"intent": "unknown", "needs_clarification": True},
                )

            return self._create_response(
                response=(
                    "I'm your e-commerce assistant and can help with:\n\n"
                    "• Tracking your orders\n"
                    "• Cancelling orders (within 24 hours)\n"
                    "• Answering questions about products and policies\n\n"
                    "Is there something specific I can help you with?"
                ),
                confidence=decision.confidence,
                metadata={"intent": "unknown", "routing": "fallback"},
            )

        return None

    async def process(
        self, session: SessionState, message: str, memory_context: str | None = None
    ) -> AgentResponse:
        """
        Process a message by routing to the appropriate agent.

        1. Check for empty message
        2. Get routing decision from LLM
        3. Handle special intents (escalation, greeting, thanks, unknown)
        4. Route to specialized agent
        5. Return response with handover chain

        Args:
            session: Current session state
            message: User message (may have references resolved)
            memory_context: Optional context from Memory Agent
        """
        start_time = time.perf_counter()
        self._memory_context = memory_context  # Store for potential use by agents

        # Handle empty message
        if not message or not message.strip():
            return self._create_response(
                response=(
                    "I didn't catch that. How can I help you today? "
                    "I can assist with tracking orders, cancellations, or product questions."
                ),
                metadata={"reason": "empty_message"},
            )

        # Get routing decision
        try:
            decision, token_usage = await self._get_routing_decision(message, session)
        except Exception as e:
            logger.exception("Routing decision failed", error=str(e))
            # Fallback to product_info as default
            decision = RoutingDecision(
                intent="unknown",
                confidence=0.5,
                reasoning=f"LLM routing failed: {e}",
                requires_clarification=True,
                clarification_question=(
                    "I'm having trouble understanding your request. "
                    "Could you please rephrase or tell me if you want to:\n"
                    "• Track an order\n"
                    "• Cancel an order\n"
                    "• Ask about products or policies"
                ),
            )
            token_usage = {"total_tokens": 0}

        routing_duration_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "Routing decision made",
            intent=decision.intent,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            duration_ms=routing_duration_ms,
            tokens=token_usage.get("total_tokens", 0),
        )

        # Handle special intents
        special_response = self._handle_special_intent(decision.intent, decision)
        if special_response:
            special_response.handover = f"{self.name} → (direct response)"
            return special_response

        # Handle clarification needed
        if decision.requires_clarification and decision.clarification_question:
            return self._create_response(
                response=decision.clarification_question,
                confidence=decision.confidence,
                metadata={
                    "intent": decision.intent,
                    "needs_clarification": True,
                    "routing": "clarification",
                },
            )

        # Route to specialized agent
        agent = self.agents.get(decision.intent)
        if not agent:
            logger.warning("No agent registered for intent", intent=decision.intent)
            return self._create_response(
                response=(
                    "I apologize, but I'm unable to handle that request right now. "
                    "Please try asking about order tracking, cancellation, or product information."
                ),
                metadata={"intent": decision.intent, "error": "no_agent_registered"},
            )

        # Process with the selected agent
        try:
            agent_start = time.perf_counter()
            agent_response = await agent.process(session, message)
            agent_duration_ms = int((time.perf_counter() - agent_start) * 1000)

            # Set handover chain
            agent_response.handover = f"{self.name} → {agent.name}"

            logger.info(
                "Agent processing complete",
                orchestrator_duration_ms=routing_duration_ms,
                agent=agent.name,
                agent_duration_ms=agent_duration_ms,
            )

            return agent_response

        except AgentError as e:
            logger.error("Agent error during routing", agent=e.agent, error=e.message)
            return self._create_response(
                response=(
                    f"I encountered an issue while processing your request. "
                    f"Please try again or contact support."
                ),
                metadata={"error": e.message, "agent": e.agent},
            )
