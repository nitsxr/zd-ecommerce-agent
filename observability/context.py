"""Context variables for request tracking."""

import uuid
from contextvars import ContextVar

# Context variables for request tracking
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id_var.set(cid)
    return cid


def get_session_id() -> str:
    """Get current session ID."""
    return session_id_var.get()
