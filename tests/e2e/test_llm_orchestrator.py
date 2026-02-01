"""
E2E tests for LLM orchestrator (mock mode): multi-turn, intent, slots, fallback.
Guardrails: LLM output is validated; invalid output is rejected before routing.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def use_llm_mock():
    """Use LLM orchestrator with mock (no API key)."""
    os.environ["USE_LLM_ORCHESTRATOR"] = "true"
    os.environ["MOCK_LLM"] = "true"


def test_chat_cancel_order(client):
    """Single turn: cancel order with ORD-XXXX -> OrderCancellationAgent."""
    r = client.post(
        "/chat",
        json={"session_id": "e2e-1", "message": "I want to cancel my order ORD-4567"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["agent"] == "OrderCancellationAgent"
    assert "ORD-4567" in data["response"] or "cancelled" in data["response"].lower()
    assert len(data["tool_calls"]) >= 1
    assert data["handover"] == "OrchestratorAgent → OrderCancellationAgent"


def test_chat_track_order(client):
    """Single turn: track order -> OrderTrackingAgent."""
    r = client.post(
        "/chat",
        json={"session_id": "e2e-2", "message": "Track order ORD-1001"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["agent"] == "OrderTrackingAgent"
    assert "ORD-1001" in data["response"] or "status" in data["response"].lower()


def test_chat_product_question(client):
    """Single turn: product question -> ProductInfoAgent."""
    r = client.post(
        "/chat",
        json={"session_id": "e2e-3", "message": "Can I return my Bluetooth headphones?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["agent"] == "ProductInfoAgent"
    assert "return" in data["response"].lower() or "Bluetooth" in data["response"]


def test_multi_turn_cancel_that(client):
    """Multi-turn: Turn 1 cancel ORD-4567, Turn 2 'cancel that' -> same order from context."""
    r1 = client.post(
        "/chat",
        json={"session_id": "e2e-multi", "message": "I want to cancel my order ORD-4567"},
    )
    assert r1.status_code == 200
    assert r1.json()["agent"] == "OrderCancellationAgent"

    r2 = client.post(
        "/chat",
        json={"session_id": "e2e-multi", "message": "cancel that"},
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["agent"] == "OrderCancellationAgent"
    assert "ORD-4567" in data2["response"] or "cancelled" in data2["response"].lower()


def test_missing_order_id_clarification(client):
    """Cancel intent without order_id -> clarification, no agent."""
    r = client.post(
        "/chat",
        json={"session_id": "e2e-4", "message": "I want to cancel my order"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["agent"] == "OrchestratorAgent"
    assert "order ID" in data["response"] or "ORD-" in data["response"]


def test_trace_has_orchestrator_type(client):
    """Trace includes orchestrator_type (llm or keyword)."""
    r = client.post(
        "/chat",
        json={"session_id": "e2e-trace", "message": "Track ORD-1001"},
    )
    assert r.status_code == 200
    session = client.get("/sessions/e2e-trace").json()
    assert session["turn_count"] >= 1
    traces = client.get("/sessions/e2e-trace/traces").json()
    assert len(traces["traces"]) >= 1
    assert traces["traces"][0].get("orchestrator_type") in ("llm", "keyword")


def test_session_turns_persisted(client):
    """After two turns, GET /sessions/{id}/turns returns 2 turns."""
    client.post("/chat", json={"session_id": "e2e-persist", "message": "hi"})
    client.post("/chat", json={"session_id": "e2e-persist", "message": "Track ORD-1001"})
    r = client.get("/sessions/e2e-persist/turns")
    assert r.status_code == 200
    data = r.json()
    assert len(data["turns"]) == 2
