"""
Orchestrator prompts: system and user message builder for LLM.
Multi-turn: last N turns + current message + extracted_entities.
"""
from __future__ import annotations

from typing import Any

# Last N turns to include in context (token-bound in production)
MAX_TURNS_IN_CONTEXT = 10

SYSTEM_PROMPT = """You are an orchestrator for an e-commerce assistant. Given the conversation history and the latest user message, output a JSON object with:
- intent: one of "cancel", "track", "product", "unclear"
- order_id: the order ID (format ORD-XXXX) if the user wants to cancel or track an order and it was mentioned or can be resolved from context (e.g. "that" = last mentioned order). Otherwise null.
- clarification_message: if you need more info (e.g. missing order ID), a short message to ask the user. Otherwise null.
- proceed: true if you have enough info to route to an agent (cancel/track/product); false if you need to ask for clarification.

Rules: Cancel and track require order_id. Resolve "that", "it", "the order" from context. Output only valid JSON."""


def _format_context(state: Any) -> str:
    """Format extracted_entities for the prompt so LLM can resolve 'that' / 'the order'."""
    entities = getattr(state, "extracted_entities", None) or {}
    if not entities:
        return ""
    parts = [f"{k}={v!r}" for k, v in sorted(entities.items()) if v]
    if not parts:
        return ""
    return "Known context: " + ", ".join(parts) + ".\n\n"


def build_orchestrator_messages(
    state: Any,
    current_message: str,
) -> list[dict[str, str]]:
    """
    Build messages for the LLM: system + conversation history (last N turns)
    + context (extracted_entities) + current user message.
    state: ConversationState with .turns, .extracted_entities.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    turns = getattr(state, "turns", []) or []
    start = max(0, len(turns) - MAX_TURNS_IN_CONTEXT)
    for t in turns[start:]:
        user_msg = getattr(t, "user_message", None) or (t.get("user_message") if isinstance(t, dict) else "")
        if user_msg:
            messages.append({"role": "user", "content": user_msg})
        resp = getattr(t, "response", None) or (t.get("response") if isinstance(t, dict) else "")
        if resp:
            messages.append({"role": "assistant", "content": resp})

    context_prefix = _format_context(state)
    last_user = current_message if not context_prefix else context_prefix + "User: " + current_message
    messages.append({"role": "user", "content": last_user})
    return messages
