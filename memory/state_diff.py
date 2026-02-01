"""
State diffing: human-readable diff between two conversation states.
Used for debugging and observability (what changed after a turn).
"""
from __future__ import annotations

from typing import Any


def diff_state(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """
    Produce a list of human-readable diff lines between two state dicts
    (e.g. ConversationState.to_dict() before and after a turn).
    """
    lines: list[str] = []
    # Turns: count change
    before_turns = len(before.get("turns", []))
    after_turns = len(after.get("turns", []))
    if after_turns != before_turns:
        lines.append(f"turns: {before_turns} -> {after_turns} (+{after_turns - before_turns})")
    # extracted_entities
    before_ent = before.get("extracted_entities") or {}
    after_ent = after.get("extracted_entities") or {}
    for key in sorted(set(before_ent) | set(after_ent)):
        b = before_ent.get(key)
        a = after_ent.get(key)
        if b != a:
            lines.append(f"extracted_entities.{key}: {_repr(b)} -> {_repr(a)}")
    # slot_state
    before_slot = before.get("slot_state") or {}
    after_slot = after.get("slot_state") or {}
    for key in sorted(set(before_slot) | set(after_slot)):
        b = before_slot.get(key)
        a = after_slot.get(key)
        if b != a:
            lines.append(f"slot_state.{key}: {_repr(b)} -> {_repr(a)}")
    return lines


def _repr(v: Any) -> str:
    """Short string repr for diff output."""
    if v is None:
        return "None"
    if isinstance(v, list):
        return "[" + ", ".join(_repr(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_repr(x)}" for k, x in v.items()) + "}"
    return repr(v)


def format_diff(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Single string with one diff line per line."""
    return "\n".join(diff_state(before, after)) if (before or after) else "(no diff)"
