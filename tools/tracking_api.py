"""
Mock tracking API: order status and estimated delivery.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from tools.order_api import get_order


def get_order_status(order_id: str) -> dict[str, Any] | None:
    """
    Return { "status": str, "estimated_delivery": str (ISO8601) } or None if not found.
    """
    order = get_order(order_id)
    if not order:
        return None
    status = order.get("status", "unknown")
    # Mock: delivery 3 days from order date
    placed_at_str = order.get("order_placed_at")
    if placed_at_str:
        try:
            placed_at = datetime.fromisoformat(placed_at_str.replace("Z", "+00:00"))
            est_delivery = (placed_at + timedelta(days=3)).isoformat()
        except (ValueError, TypeError):
            est_delivery = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    else:
        est_delivery = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    return {
        "status": status,
        "estimated_delivery": est_delivery,
    }
