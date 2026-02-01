"""
LLM router: get intent, order_id, clarification from LLM (or mock).
Validates output and returns structured result for decision_engine.
"""
from __future__ import annotations

import re
from typing import Any

from orchestrator.llm_client import call_orchestrator_llm
from orchestrator.prompts import build_orchestrator_messages

ORDER_ID_RE = re.compile(r"^ORD-\d+$", re.IGNORECASE)


def _validate_order_id(value: str | None) -> bool:
    return value is not None and bool(ORDER_ID_RE.match(value.strip()))


def llm_orchestrate(state: Any, current_message: str) -> dict[str, Any]:
    """
    Run LLM (or mock) for orchestrator decision. Returns intent, order_id,
    clarification_message, proceed. Validates output; invalid -> unclear, no proceed.
    """
    messages = build_orchestrator_messages(state, current_message)
    get_last = getattr(state, "get_last_order_id", lambda: None)
    context = {"last_order_id": get_last()}
    raw = call_orchestrator_llm(messages, context=context)

    intent = (raw.get("intent") or "unclear").lower()
    if intent not in ("cancel", "track", "product", "unclear"):
        intent = "unclear"

    order_id = raw.get("order_id")
    if order_id and isinstance(order_id, str):
        order_id = order_id.strip().upper()
        if not ORDER_ID_RE.match(order_id):
            order_id = None
    else:
        order_id = None

    clarification_message = raw.get("clarification_message")
    if clarification_message and not isinstance(clarification_message, str):
        clarification_message = None

    proceed = bool(raw.get("proceed", False))

    # If proceed but cancel/track need order_id and we don't have it, force clarification
    needs_id = proceed and intent in ("cancel", "track")
    if needs_id and not _validate_order_id(order_id):
        proceed = False
        clarification_message = (
            "I can help with that. Please provide your order ID in the format "
            "ORD-XXXX (e.g. ORD-1234)."
        )

    return {
        "intent": intent,
        "order_id": order_id,
        "clarification_message": clarification_message or None,
        "proceed": proceed,
    }
