"""
Decision engine: orchestrate one chat turn.
Load state -> intent -> route -> validate slots -> clarify or invoke agent -> persist -> build response.
Supports LLM orchestrator (USE_LLM_ORCHESTRATOR=true) with mock or OpenAI; fallback to keyword.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agents import order_cancellation, order_tracking, product_info
from orchestrator.intent import Intent, detect_intent, extract_order_id
from orchestrator.router import route as route_intent
from orchestrator.state_machine import ConversationState, create_empty_state


def _use_llm_orchestrator() -> bool:
    """Read at request time so tests can override per test."""
    return os.environ.get("USE_LLM_ORCHESTRATOR", "").lower() in ("true", "1", "yes")

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


def _invoke_agent(
    agent_name: str,
    order_id: str | None = None,
    message: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    """
    Invoke real agent (M4). Agents are stateless; they call tools and return (response_text, tool_calls).
    On validation error, return error message and tool_calls with error result (fail loudly but gracefully).
    """
    try:
        if agent_name == "OrderCancellationAgent":
            return order_cancellation.run(order_id or "")
        if agent_name == "OrderTrackingAgent":
            return order_tracking.run(order_id or "")
        if agent_name == "ProductInfoAgent":
            return product_info.run(message or "")
    except ValueError as e:
        err_msg = str(e)
        tool_calls = [
            {
                "tool": "OrchestratorAgent",
                "input": {"order_id": order_id, "message": message},
                "result": {"error": err_msg},
            }
        ]
        return f"Sorry, I couldn't process that: {err_msg}", tool_calls
    return (
        "I'm not sure how to help with that. You can ask to cancel or track an order (use format ORD-1234), or ask a product question.",
        [],
    )


def _run_turn_keyword(
    state: ConversationState,
    session_id: str,
    message: str,
    store: Any,
    request_id: str,
    start: float,
) -> ChatResult:
    """Keyword-based path: intent from keywords, order_id from message or context."""
    intent: Intent = detect_intent(message)
    agent_name = route_intent(intent)
    order_id_from_message = extract_order_id(message)
    last_order_id = state.get_last_order_id()
    order_id = order_id_from_message or last_order_id
    return _run_turn_with_intent(
        state=state,
        session_id=session_id,
        message=message,
        store=store,
        request_id=request_id,
        start=start,
        intent=intent,
        agent_name=agent_name,
        order_id=order_id,
        orchestrator_type="keyword",
    )


def _run_turn_with_intent(
    state: ConversationState,
    session_id: str,
    message: str,
    store: Any,
    request_id: str,
    start: float,
    intent: Intent,
    agent_name: str,
    order_id: str | None,
    orchestrator_type: str,
) -> ChatResult:
    """Shared logic: use intent, agent_name, order_id to clarify or invoke agent."""
    # Unclear intent -> clarification
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
        trace = {
            "request_id": request_id,
            "session_id": session_id,
            "turn_index": state.turn_index - 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": intent,
            "selected_agent": "OrchestratorAgent",
            "latency_ms": round(latency_ms, 2),
            "errors": [],
            "orchestrator_type": orchestrator_type,
        }
        return ChatResult(
            response=response_text,
            agent="OrchestratorAgent",
            tool_calls=[],
            handover="OrchestratorAgent",
            trace=trace,
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
        trace = {
            "request_id": request_id,
            "session_id": session_id,
            "turn_index": state.turn_index - 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": intent,
            "selected_agent": "OrchestratorAgent",
            "latency_ms": round(latency_ms, 2),
            "errors": [],
            "orchestrator_type": orchestrator_type,
        }
        return ChatResult(
            response="I can help with that. Please provide your order ID in the format ORD-XXXX (e.g. ORD-1234).",
            agent="OrchestratorAgent",
            tool_calls=[],
            handover="OrchestratorAgent → (awaiting order_id)",
            trace=trace,
        )

    # 5. Invoke agent (M4: real agents and tools)
    if needs_order_id:
        state.clear_slot_state()
    response_text, tool_calls = _invoke_agent(agent_name, order_id=order_id, message=message)
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": intent,
        "selected_agent": agent_name,
        "tool_calls_summary": [{"tool": tc.get("tool", ""), "success": tc.get("result") is not None} for tc in tool_calls],
        "latency_ms": round(latency_ms, 2),
        "errors": [],
        "orchestrator_type": orchestrator_type,
    }

    return ChatResult(
        response=response_text,
        agent=agent_name,
        tool_calls=tool_calls,
        handover=handover_str,
        trace=trace,
    )


def run_turn(
    session_id: str,
    message: str,
    store: Any,
) -> ChatResult:
    """
    Execute one chat turn. When USE_LLM_ORCHESTRATOR=true, use LLM (or mock)
    for intent/slots/clarification; otherwise use keyword orchestrator.
    On LLM failure, fall back to keyword. Trace includes orchestrator_type.
    """
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    state = store.get(session_id) or create_empty_state(session_id)

    if _use_llm_orchestrator():
        try:
            from orchestrator.llm_router import llm_orchestrate
            llm_out = llm_orchestrate(state, message)
        except Exception:
            return _run_turn_keyword(state, session_id, message, store, request_id, start)

        intent = llm_out["intent"]
        order_id = llm_out.get("order_id")
        clarification_message = llm_out.get("clarification_message")
        proceed = llm_out.get("proceed", False)

        if not proceed and clarification_message:
            state.append_turn(
                user_message=message,
                agent="OrchestratorAgent",
                response=clarification_message,
                handover="OrchestratorAgent",
            )
            store.set(session_id, state)
            latency_ms = (time.perf_counter() - start) * 1000
            return ChatResult(
                response=clarification_message,
                agent="OrchestratorAgent",
                tool_calls=[],
                handover="OrchestratorAgent",
                trace={
                    "request_id": request_id,
                    "session_id": session_id,
                    "turn_index": state.turn_index - 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "intent": intent,
                    "selected_agent": "OrchestratorAgent",
                    "latency_ms": round(latency_ms, 2),
                    "errors": [],
                    "orchestrator_type": "llm",
                },
            )

        agent_name = route_intent(intent)
        if order_id:
            state.extracted_entities["order_id"] = order_id
        return _run_turn_with_intent(
            state=state,
            session_id=session_id,
            message=message,
            store=store,
            request_id=request_id,
            start=start,
            intent=intent,
            agent_name=agent_name,
            order_id=order_id,
            orchestrator_type="llm",
        )

    return _run_turn_keyword(state, session_id, message, store, request_id, start)
