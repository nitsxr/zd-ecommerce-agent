"""
Decision engine: orchestrate one chat turn.
Load state -> intent -> route -> validate slots -> clarify or invoke agent -> persist -> build response.
All decisions are deterministic and traceable; no agent controls flow.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from orchestrator.intent import Intent, detect_intent, extract_order_id
from orchestrator.router import route as route_intent
from orchestrator.state_machine import ConversationState, create_empty_state

# Order ID validation per schemas/validation_rules.md
ORDER_ID_RE = re.compile(r"^ORD-\d+$", re.IGNORECASE)


def _validate_order_id(value: str | None) -> bool:
    """Return True if value is a valid order ID (ORD-XXXX)."""
    return value is not None and bool(ORDER_ID_RE.match(value.strip()))


@dataclass
class ChatResult:
    """Result of one chat turn: HTTP response shape + trace info."""
    response: str
    agent: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    handover: str = ""
    trace: dict[str, Any] = field(default_factory=dict)


def _stub_invoke_agent(
    agent_name: str,
    order_id: str | None = None,
    message: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    """
    Stub agent invocation for M2. M4 will replace with real agents and tools.
    Returns (response_text, tool_calls).
    """
    if agent_name == "OrderCancellationAgent":
        return (
            f"I'll process your cancellation request for order {order_id or 'N/A'}. (Cancellation agent not yet implemented.)",
            [{"tool": "OrderCancellationAPI", "input": {"orderId": order_id or ""}, "result": None}],
        )
    if agent_name == "OrderTrackingAgent":
        return (
            f"I'll look up the status for order {order_id or 'N/A'}. (Tracking agent not yet implemented.)",
            [{"tool": "TrackingAPI", "input": {"orderId": order_id or ""}, "result": None}],
        )
    if agent_name == "ProductInfoAgent":
        return (
            f"I'll look up information for: \"{message[:80] or 'your question'}\". (Product info agent not yet implemented.)",
            [{"tool": "KnowledgeBase", "input": {"query": message}, "result": None}],
        )
    return "I'm not sure how to help with that. You can ask to cancel or track an order (use format ORD-1234), or ask a product question.", []


def run_turn(
    session_id: str,
    message: str,
    store: Any,
) -> ChatResult:
    """
    Execute one chat turn: load state, detect intent, route, validate slots,
    clarify or invoke agent, persist state, build response.
    """
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    # 1. Load state (create empty if new)
    state = store.get(session_id) or create_empty_state(session_id)
    intent: Intent = detect_intent(message)
    agent_name = route_intent(intent)

    # 2. Resolve order_id: from message, or from context ("that" -> last order_id)
    order_id_from_message = extract_order_id(message)
    last_order_id = state.get_last_order_id()
    order_id = order_id_from_message or last_order_id

    # 3. Unclear intent -> clarification (no agent invoked)
    if agent_name == "OrchestratorAgent":
        response_text = (
            "Could you please specify whether you want to cancel an order, track an order, or ask a product question? "
            "If canceling or tracking, include your order ID (e.g. ORD-1234)."
        )
        state.append_turn(
            user_message=message,
            agent="OrchestratorAgent",
            response=response_text,
            handover="OrchestratorAgent",
        )
        store.set(session_id, state)
        latency_ms = (time.perf_counter() - start) * 1000
        return ChatResult(
            response=response_text,
            agent="OrchestratorAgent",
            tool_calls=[],
            handover="OrchestratorAgent",
            trace={
                "request_id": request_id,
                "session_id": session_id,
                "turn_index": state.turn_index - 1,
                "intent": intent,
                "selected_agent": "OrchestratorAgent",
                "latency_ms": round(latency_ms, 2),
                "errors": [],
            },
        )

    # 4. Slot validation: cancel/track require order_id
    needs_order_id = agent_name in ("OrderCancellationAgent", "OrderTrackingAgent")
    if needs_order_id and not _validate_order_id(order_id):
        # Missing or invalid order_id -> clarification
        state.set_awaiting_slots(["order_id"])
        state.append_turn(
            user_message=message,
            agent="OrchestratorAgent",
            response="I can help with that. Please provide your order ID in the format ORD-XXXX (e.g. ORD-1234).",
            handover="OrchestratorAgent → (awaiting order_id)",
        )
        store.set(session_id, state)
        latency_ms = (time.perf_counter() - start) * 1000
        return ChatResult(
            response="I can help with that. Please provide your order ID in the format ORD-XXXX (e.g. ORD-1234).",
            agent="OrchestratorAgent",
            tool_calls=[],
            handover="OrchestratorAgent → (awaiting order_id)",
            trace={
                "request_id": request_id,
                "session_id": session_id,
                "turn_index": state.turn_index - 1,
                "intent": intent,
                "selected_agent": "OrchestratorAgent",
                "latency_ms": round(latency_ms, 2),
                "errors": [],
            },
        )

    # 5. Invoke agent (stub for M2)
    if needs_order_id:
        state.clear_slot_state()
    response_text, tool_calls = _stub_invoke_agent(agent_name, order_id=order_id, message=message)
    handover_str = f"OrchestratorAgent → {agent_name}"

    # 6. Persist turn
    state.append_turn(
        user_message=message,
        agent=agent_name,
        response=response_text,
        handover=handover_str,
        tool_calls=tool_calls,
    )
    store.set(session_id, state)

    latency_ms = (time.perf_counter() - start) * 1000
    trace = {
        "request_id": request_id,
        "session_id": session_id,
        "turn_index": state.turn_index - 1,
        "intent": intent,
        "selected_agent": agent_name,
        "tool_calls_summary": [{"tool": tc.get("tool", ""), "success": tc.get("result") is not None} for tc in tool_calls],
        "latency_ms": round(latency_ms, 2),
        "errors": [],
    }

    return ChatResult(
        response=response_text,
        agent=agent_name,
        tool_calls=tool_calls,
        handover=handover_str,
        trace=trace,
    )
