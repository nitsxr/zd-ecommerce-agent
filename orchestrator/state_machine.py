"""
Multi-turn state machine: ConversationState type and transitions.
Session state is keyed by session_id; holds turns, extracted_entities, slot_state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orchestrator.intent import extract_order_id


@dataclass
class Turn:
    """Single turn: user message + assistant response."""
    user_message: str
    agent: str
    response: str
    handover: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConversationState:
    """Session state: turns, extracted_entities, slot_state."""
    session_id: str
    turns: list[Turn] = field(default_factory=list)
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    slot_state: dict[str, Any] = field(default_factory=dict)

    @property
    def turn_index(self) -> int:
        """Zero-based index of the next turn (current length)."""
        return len(self.turns)

    def append_turn(
        self,
        user_message: str,
        agent: str,
        response: str,
        handover: str,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        """Append one turn and optionally update entities from message."""
        self.turns.append(
            Turn(
                user_message=user_message,
                agent=agent,
                response=response,
                handover=handover,
                tool_calls=tool_calls or [],
            )
        )
        # Update extracted entities from this message
        order_id = extract_order_id(user_message)
        if order_id:
            self.extracted_entities["order_id"] = order_id

    def set_awaiting_slots(self, slots: list[str]) -> None:
        """Set slot_state.awaiting to list of slot names (e.g. ['order_id'])."""
        self.slot_state["awaiting"] = slots

    def clear_slot_state(self) -> None:
        """Clear slot_state after slots are filled."""
        self.slot_state = {}

    def get_last_order_id(self) -> str | None:
        """Last mentioned order_id for multi-turn resolution ('that' -> order_id)."""
        return self.extracted_entities.get("order_id")

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage (e.g. Redis in M3)."""
        return {
            "session_id": self.session_id,
            "turns": [
                {
                    "user_message": t.user_message,
                    "agent": t.agent,
                    "response": t.response,
                    "handover": t.handover,
                    "tool_calls": t.tool_calls,
                }
                for t in self.turns
            ],
            "extracted_entities": self.extracted_entities,
            "slot_state": self.slot_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationState":
        """Deserialize from storage."""
        turns = [
            Turn(
                user_message=t["user_message"],
                agent=t["agent"],
                response=t["response"],
                handover=t["handover"],
                tool_calls=t.get("tool_calls", []),
            )
            for t in data.get("turns", [])
        ]
        return cls(
            session_id=data["session_id"],
            turns=turns,
            extracted_entities=data.get("extracted_entities", {}),
            slot_state=data.get("slot_state", {}),
        )


def create_empty_state(session_id: str) -> ConversationState:
    """Create new session state."""
    return ConversationState(session_id=session_id)
