"""
Pytest fixtures: app, client, in-memory store.
Tests run with in-memory session store (no Redis).
"""
from __future__ import annotations

import os

import pytest

# Use in-memory store and mock LLM for tests
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("USE_LLM_ORCHESTRATOR", "true")


@pytest.fixture
def app():
    """FastAPI app (import after env is set)."""
    from src.main import app
    return app


@pytest.fixture
def client(app):
    """TestClient for the app."""
    from fastapi.testclient import TestClient
    return TestClient(app)
