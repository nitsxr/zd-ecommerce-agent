"""
LLM client: OpenAI wrapper with mock mode.
When MOCK_LLM=true or OPENAI_API_KEY is unset, API calls are mocked (keyword-based).
"""
from __future__ import annotations

import json
import os
from typing import Any

# Structured output shape for orchestrator
LLM_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["cancel", "track", "product", "unclear"]},
        "order_id": {"type": ["string", "null"]},
        "clarification_message": {"type": ["string", "null"]},
        "proceed": {"type": "boolean"},
    },
    "required": ["intent", "proceed"],
    "additionalProperties": False,
}


def _use_mock() -> bool:
    """True if we should mock OpenAI (no key or MOCK_LLM=true)."""
    if os.environ.get("MOCK_LLM", "").lower() in ("true", "1", "yes"):
        return True
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        return True
    return False


def call_orchestrator_llm(
    messages: list[dict[str, str]],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Call LLM for orchestrator decision. Returns structured output:
    { "intent": str, "order_id": str|None, "clarification_message": str|None, "proceed": bool }.
    Uses mock when MOCK_LLM=true or OPENAI_API_KEY unset.
    context: optional { "last_order_id": str } for multi-turn resolution.
    """
    if _use_mock():
        return _mock_orchestrator_response(messages, context or {})
    return _openai_orchestrator_response(messages)


def _mock_orchestrator_response(
    messages: list[dict[str, str]],
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Mock: derive intent, order_id, clarification, proceed from last user message
    and context (last_order_id) using keyword logic (no API call).
    """
    from orchestrator.intent import detect_intent, extract_order_id

    # Last user message
    user_text = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_text = m.get("content", "")
            break

    intent = detect_intent(user_text)
    order_id_from_message = extract_order_id(user_text)
    last_order_id = context.get("last_order_id")
    order_id = order_id_from_message or last_order_id

    # Resolve proceed and clarification
    needs_order_id = intent in ("cancel", "track")
    if intent == "unclear":
        return {
            "intent": "unclear",
            "order_id": None,
            "clarification_message": (
                "Could you please specify whether you want to cancel an order, "
                "track an order, or ask a product question? "
                "If canceling or tracking, include your order ID (e.g. ORD-1234)."
            ),
            "proceed": False,
        }
    if needs_order_id and not order_id:
        return {
            "intent": intent,
            "order_id": None,
            "clarification_message": (
                "I can help with that. Please provide your order ID in the format "
                "ORD-XXXX (e.g. ORD-1234)."
            ),
            "proceed": False,
        }
    if needs_order_id and order_id:
        return {
            "intent": intent,
            "order_id": order_id,
            "clarification_message": None,
            "proceed": True,
        }
    # product or other
    return {
        "intent": intent,
        "order_id": None,
        "clarification_message": None,
        "proceed": True,
    }


def _openai_orchestrator_response(messages: list[dict[str, str]]) -> dict[str, Any]:
    """Call OpenAI with JSON mode; parse and return structured output."""
    try:
        from openai import OpenAI
    except ImportError:
        return _mock_orchestrator_response(messages)

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=256,
    )
    raw = response.choices[0].message.content
    if not raw:
        return _mock_orchestrator_response(messages)
    data = json.loads(raw)
    # Normalize
    intent = (data.get("intent") or "unclear").lower()
    if intent not in ("cancel", "track", "product", "unclear"):
        intent = "unclear"
    return {
        "intent": intent,
        "order_id": data.get("order_id") or None,
        "clarification_message": data.get("clarification_message") or None,
        "proceed": bool(data.get("proceed", False)),
    }
