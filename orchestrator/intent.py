"""
Intent detection: classify user message into cancel / track / product / unclear.
Deterministic, keyword-based for M2; can be replaced with a classifier later.
"""
from __future__ import annotations

import re
from typing import Literal

Intent = Literal["cancel", "track", "product", "unclear"]

# Order ID pattern per validation_rules.md
ORDER_ID_PATTERN = re.compile(r"ORD-\d+", re.IGNORECASE)

# Keywords per intent (lowercased)
CANCEL_KEYWORDS = frozenset(
    {"cancel", "cancellation", "cancel my order", "cancel order", "refund", "undo order"}
)
TRACK_KEYWORDS = frozenset(
    {"track", "tracking", "status", "where is my order", "delivery", "shipped", "when will it arrive"}
)
PRODUCT_KEYWORDS = frozenset(
    {"return", "return policy", "warranty", "product", "faq", "how to", "can i", "do you", "bluetooth", "headphones", "information", "info"}
)


def extract_order_id(text: str) -> str | None:
    """Extract first ORD-XXXX from text. Returns None if none found."""
    if not text or not text.strip():
        return None
    m = ORDER_ID_PATTERN.search(text)
    return m.group(0).upper() if m else None


def detect_intent(message: str) -> Intent:
    """
    Classify user message into cancel, track, product, or unclear.
    Prefer cancel/track when order ID is present and message hints at it.
    """
    if not message or not message.strip():
        return "unclear"
    lower = message.lower().strip()
    has_order_id = ORDER_ID_PATTERN.search(message) is not None

    # Explicit order ID + cancel/track-like phrasing
    if has_order_id:
        if any(k in lower for k in CANCEL_KEYWORDS):
            return "cancel"
        if any(k in lower for k in TRACK_KEYWORDS):
            return "track"

    # Strong cancel/track phrasing even without order ID (we may ask for it)
    if any(k in lower for k in CANCEL_KEYWORDS):
        return "cancel"
    if any(k in lower for k in TRACK_KEYWORDS):
        return "track"

    # Product/FAQ
    if any(k in lower for k in PRODUCT_KEYWORDS):
        return "product"

    # Short follow-ups: "that", "it", "yes" -> keep previous intent via state (handled in decision_engine)
    if lower in ("that", "it", "yes", "ok", "okay", "sure", "please", "go ahead"):
        return "unclear"  # Resolved from context in decision_engine

    return "unclear"
