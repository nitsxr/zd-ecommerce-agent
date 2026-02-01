"""
OrderTrackingAgent: validates order ID, calls tracking tool, returns status and estimated delivery.
Stateless; no Redis or orchestrator logic. Fails loudly on invalid input.
"""
from __future__ import annotations

import re
from typing import Any

from tools.tracking_api import get_order_status

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
    Get order status and estimated delivery. Orchestrator must pass validated order_id; we re-validate.
    Returns (response_message, tool_calls).
    """
    order_id = validate_order_id(order_id)
    result = get_order_status(order_id)
    tool_call = {
        "tool": "TrackingAPI",
        "input": {"orderId": order_id},
        "result": result,
    }
    if not result:
        return f"We couldn't find order {order_id}. Please check the order ID and try again.", [tool_call]
    status = result.get("status", "unknown")
    est = result.get("estimated_delivery", "")
    if est:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(est.replace("Z", "+00:00"))
            est_readable = dt.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            est_readable = est
    else:
        est_readable = "N/A"
    message = f"Order {order_id} status: **{status}**. Estimated delivery: {est_readable}."
    return message, [tool_call]
