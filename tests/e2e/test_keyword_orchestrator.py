"""
E2E tests for keyword orchestrator (USE_LLM_ORCHESTRATOR=false).
Same scenarios as LLM path; validates keyword path works.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def use_keyword_orchestrator():
    """Use keyword orchestrator (no LLM)."""
    os.environ["USE_LLM_ORCHESTRATOR"] = "false"


def test_keyword_cancel_order(client):
    """Keyword: cancel order ORD-4567 -> OrderCancellationAgent."""
    r = client.post(
        "/chat",
        json={"session_id": "kw-1", "message": "I want to cancel my order ORD-4567"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["agent"] == "OrderCancellationAgent"
    assert "ORD-4567" in data["response"] or "cancelled" in data["response"].lower()


def test_keyword_track_order(client):
    """Keyword: track order -> OrderTrackingAgent."""
    r = client.post(
        "/chat",
        json={"session_id": "kw-2", "message": "Track order ORD-1001"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["agent"] == "OrderTrackingAgent"


def test_keyword_product_question(client):
    """Keyword: product question -> ProductInfoAgent."""
    r = client.post(
        "/chat",
        json={"session_id": "kw-3", "message": "Can I return my Bluetooth headphones?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["agent"] == "ProductInfoAgent"


def test_keyword_multi_turn_cancel_that(client):
    """Keyword: Turn 1 cancel ORD-4567, Turn 2 'cancel that' -> same order from context."""
    client.post(
        "/chat",
        json={"session_id": "kw-multi", "message": "I want to cancel my order ORD-4567"},
    )
    r2 = client.post(
        "/chat",
        json={"session_id": "kw-multi", "message": "cancel that"},
    )
    assert r2.status_code == 200
    assert r2.json()["agent"] == "OrderCancellationAgent"
    assert "ORD-4567" in r2.json()["response"] or "cancelled" in r2.json()["response"].lower()


def test_keyword_missing_order_id(client):
    """Keyword: cancel without order_id -> clarification."""
    r = client.post(
        "/chat",
        json={"session_id": "kw-4", "message": "I want to cancel my order"},
    )
    assert r.status_code == 200
    assert r.json()["agent"] == "OrchestratorAgent"
    assert "order ID" in r.json()["response"] or "ORD-" in r.json()["response"]
