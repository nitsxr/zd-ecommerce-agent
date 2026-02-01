"""
Mock order database and cancellation API.
Enforces 24-hour cancellation rule; time-based logic uses configurable now for testability.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

# Default: use real time. Tests can inject a fixed now.
_get_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


def set_now_provider(provider: Callable[[], datetime]) -> None:
    """Inject a custom 'now' (e.g. fixed time for tests)."""
    global _get_now
    _get_now = provider


def get_now() -> datetime:
    """Current time in UTC (configurable for tests)."""
    return _get_now()


# Mock order DB: order_id -> { order_placed_at (ISO8601), status }
_orders: dict[str, dict[str, Any]] = {}


def _ensure_orders() -> None:
    """Seed a few mock orders if empty."""
    global _orders
    if _orders:
        return
    now = get_now()
    # ORD-1001 placed 12h ago (cancelable), ORD-1002 placed 36h ago (not cancelable), ORD-4567 2h ago
    _orders["ORD-1001"] = {
        "order_placed_at": (now - timedelta(hours=12)).isoformat(),
        "status": "confirmed",
    }
    _orders["ORD-1002"] = {
        "order_placed_at": (now - timedelta(hours=36)).isoformat(),
        "status": "confirmed",
    }
    _orders["ORD-4567"] = {
        "order_placed_at": (now - timedelta(hours=2)).isoformat(),
        "status": "confirmed",
    }


def get_order(order_id: str) -> dict[str, Any] | None:
    """Return order record or None if not found. Ensures mock data is seeded."""
    _ensure_orders()
    return _orders.get(order_id.upper())


def cancel_order(order_id: str) -> dict[str, Any]:
    """
    Attempt to cancel order. Enforces 24h rule.
    Returns { "status": "cancelled"|"rejected", "refunded": bool, "reason": str }.
    """
    order_id = order_id.upper()
    order = get_order(order_id)
    if not order:
        return {
            "status": "rejected",
            "refunded": False,
            "reason": "Order not found",
        }
    placed_at_str = order.get("order_placed_at")
    if not placed_at_str:
        return {
            "status": "rejected",
            "refunded": False,
            "reason": "Invalid order record",
        }
    try:
        placed_at = datetime.fromisoformat(placed_at_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return {
            "status": "rejected",
            "refunded": False,
            "reason": "Invalid order timestamp",
        }
    now = get_now()
    if now - placed_at > timedelta(hours=24):
        return {
            "status": "rejected",
            "refunded": False,
            "reason": "Order is older than 24 hours; cancellation not allowed.",
        }
    # Mark as cancelled in mock DB
    order["status"] = "cancelled"
    return {
        "status": "cancelled",
        "refunded": True,
        "reason": "Order cancelled successfully.",
    }
