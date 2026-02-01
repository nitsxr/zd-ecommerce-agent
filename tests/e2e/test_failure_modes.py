"""
E2E failure-mode tests: 404, invalid input, 24h rule.
"""
from __future__ import annotations

import pytest


def test_get_session_404(client):
    """GET /sessions/nonexistent -> 404."""
    r = client.get("/sessions/nonexistent-id-12345")
    assert r.status_code == 404
    assert "not found" in r.json().get("detail", "").lower()


def test_get_session_turns_404(client):
    """GET /sessions/nonexistent/turns -> 404."""
    r = client.get("/sessions/nonexistent-id-12345/turns")
    assert r.status_code == 404


def test_chat_missing_body(client):
    """POST /chat with missing session_id or message -> 422."""
    r = client.post("/chat", json={})
    assert r.status_code == 422

    r2 = client.post("/chat", json={"session_id": "x"})
    assert r2.status_code == 422

    r3 = client.post("/chat", json={"message": "hi"})
    assert r3.status_code == 422


def test_24h_rule_old_order_rejected(client):
    """Cancel order older than 24h (ORD-1002 in mock) -> rejected message."""
    r = client.post(
        "/chat",
        json={"session_id": "fail-24h", "message": "Cancel order ORD-1002"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["agent"] == "OrderCancellationAgent"
    assert "couldn't" in data["response"].lower() or "24" in data["response"] or "older" in data["response"].lower()


def test_traces_empty_session_200(client):
    """GET /sessions/{id}/traces for new session -> 200, empty list."""
    r = client.get("/sessions/new-session-no-turns/traces")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "new-session-no-turns"
    assert data["traces"] == []
