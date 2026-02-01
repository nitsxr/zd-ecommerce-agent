"""
OrderCancellationAgent: validates order ID, calls cancellation tool (24h rule in tool).
Stateless; no Redis or orchestrator logic. Fails loudly on invalid input.
"""
from __future__ import annotations

import re
from typing import Any

from tools.order_api import cancel_order

ORDER_ID_RE = re.compile(r"^ORD-\d+$", re.IGNORECASE)


def validate_order_id(order_id: str | None) -> str:
    """Raise ValueError if order_id is invalid; return normalized order_id."""
    if not order_id or not isinstance(order_id, str):
        raise ValueError("order_id is required and must be a non-empty string")
    order_id = order_id.strip().upper()
    if not ORDER_ID_RE.match(order_id):
        raise ValueError(f"Invalid order ID format: expected ORD-XXXX, got {order_id!r}")
    return order_id


def run(order_id: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Cancel order. Orchestrator passes validated order_id; we re-validate.
    Returns (response_message, tool_calls).
    """
    order_id = validate_order_id(order_id)
    result = cancel_order(order_id)
    tool_call = {
        "tool": "OrderCancellationAPI",
        "input": {"orderId": order_id},
        "result": result,
    }
    status = result.get("status", "unknown")
    refunded = result.get("refunded", False)
    reason = result.get("reason", "")
    if status == "cancelled":
        message = f"Your order {order_id} has been cancelled. {reason}"
        if refunded:
            message += " Refund processed within 5–7 business days."
    else:
        message = f"We couldn't cancel order {order_id}. {reason}"
    return message, [tool_call]
