"""
Conversation store: read-only view of conversation (turns/messages) for a session.
Uses the session store as source of truth; no separate persistence.
"""
from __future__ import annotations

from typing import Any

from orchestrator.state_machine import ConversationState

from memory.session_store import SessionStore


def get_turns(session_id: str, store: SessionStore) -> list[dict[str, Any]]:
    """
    Return conversation turns for session_id. Each turn: user_message, agent, response, handover, tool_calls.
    Returns [] if session not found.
    """
    state = store.get(session_id)
    if state is None:
        return []
    return [
        {
            "user_message": t.user_message,
            "agent": t.agent,
            "response": t.response,
            "handover": t.handover,
            "tool_calls": t.tool_calls,
        }
        for t in state.turns
    ]


def get_messages(session_id: str, store: SessionStore) -> list[dict[str, str]]:
    """
    Return flat message list for UI: alternating user/assistant with role and content.
    Returns [] if session not found.
    """
    turns = get_turns(session_id, store)
    out: list[dict[str, str]] = []
    for t in turns:
        out.append({"role": "user", "content": t["user_message"]})
        out.append({"role": "assistant", "content": t["response"]})
    return out


def get_session_summary(session_id: str, store: SessionStore) -> dict[str, Any] | None:
    """
    Return session summary: session_id, turn_count, extracted_entities, slot_state.
    Returns None if session not found.
    """
    state = store.get(session_id)
    if state is None:
        return None
    return {
        "session_id": state.session_id,
        "turn_count": len(state.turns),
        "extracted_entities": state.extracted_entities,
        "slot_state": state.slot_state,
    }
