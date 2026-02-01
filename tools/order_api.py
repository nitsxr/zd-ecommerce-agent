"""Mock Order API for tracking and cancellation."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from observability.logger import get_logger

logger = get_logger(__name__)


class OrderStatus(str, Enum):
    """Possible order statuses."""

    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(BaseModel):
    """Order details."""

    order_id: str
    status: OrderStatus
    product_name: str
    product_id: str
    quantity: int = 1
    total_amount: float
    created_at: datetime
    updated_at: datetime
    estimated_delivery: datetime | None = None
    tracking_number: str | None = None


class CancellationResult(BaseModel):
    """Result of a cancellation attempt."""

    success: bool
    order_id: str
    status: Literal["cancelled", "ineligible", "already_cancelled", "already_shipped", "not_found"]
    message: str
    refund_amount: float | None = None


# Mock data: orders with varied timestamps and statuses
_MOCK_ORDERS: dict[str, Order] = {}


def _init_mock_orders() -> None:
    """Initialize mock order data."""
    now = datetime.utcnow()

    orders = [
        # Recent order - can be cancelled
        Order(
            order_id="ORD-1234",
            status=OrderStatus.PROCESSING,
            product_name="Wireless Bluetooth Headphones",
            product_id="PROD-001",
            total_amount=89.99,
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
            estimated_delivery=now + timedelta(days=5),
        ),
        # Order placed yesterday - cannot be cancelled
        Order(
            order_id="ORD-2345",
            status=OrderStatus.PROCESSING,
            product_name="USB-C Charging Cable",
            product_id="PROD-002",
            quantity=2,
            total_amount=24.99,
            created_at=now - timedelta(hours=30),
            updated_at=now - timedelta(hours=28),
            estimated_delivery=now + timedelta(days=4),
        ),
        # Shipped order
        Order(
            order_id="ORD-3456",
            status=OrderStatus.SHIPPED,
            product_name="Portable Bluetooth Speaker",
            product_id="PROD-003",
            total_amount=149.99,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=1),
            estimated_delivery=now + timedelta(days=2),
            tracking_number="1Z999AA10123456784",
        ),
        # Already cancelled order
        Order(
            order_id="ORD-4567",
            status=OrderStatus.CANCELLED,
            product_name="Phone Case",
            product_id="PROD-004",
            total_amount=19.99,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1),
        ),
        # Delivered order
        Order(
            order_id="ORD-5678",
            status=OrderStatus.DELIVERED,
            product_name="Wireless Mouse",
            product_id="PROD-005",
            total_amount=39.99,
            created_at=now - timedelta(days=7),
            updated_at=now - timedelta(days=1),
        ),
        # Very recent order - can be cancelled
        Order(
            order_id="ORD-6789",
            status=OrderStatus.PENDING,
            product_name="Laptop Stand",
            product_id="PROD-006",
            total_amount=59.99,
            created_at=now - timedelta(minutes=30),
            updated_at=now - timedelta(minutes=30),
            estimated_delivery=now + timedelta(days=6),
        ),
        # Another shipped order
        Order(
            order_id="ORD-7890",
            status=OrderStatus.SHIPPED,
            product_name="Mechanical Keyboard",
            product_id="PROD-007",
            total_amount=129.99,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(hours=12),
            estimated_delivery=now + timedelta(days=1),
            tracking_number="1Z999AA10123456785",
        ),
    ]

    for order in orders:
        _MOCK_ORDERS[order.order_id] = order


# Initialize on module load
_init_mock_orders()


class OrderAPI:
    """Mock Order API for e-commerce operations."""

    CANCELLATION_WINDOW_HOURS = 24

    async def get_order(self, order_id: str) -> Order | None:
        """
        Retrieve order details by ID.

        Args:
            order_id: Order ID in format ORD-XXXX

        Returns:
            Order if found, None otherwise
        """
        logger.info("Fetching order", order_id=order_id)

        order = _MOCK_ORDERS.get(order_id)

        if order:
            logger.info("Order found", order_id=order_id, status=order.status.value)
        else:
            logger.info("Order not found", order_id=order_id)

        return order

    async def cancel_order(self, order_id: str) -> CancellationResult:
        """
        Attempt to cancel an order.

        Business rules:
        - Order must exist
        - Order must not already be cancelled
        - Order must not be shipped/delivered
        - Order must be placed within the last 24 hours

        Args:
            order_id: Order ID to cancel

        Returns:
            CancellationResult with status and message
        """
        logger.info("Attempting to cancel order", order_id=order_id)

        order = _MOCK_ORDERS.get(order_id)

        # Order not found
        if order is None:
            logger.info("Cancel failed: order not found", order_id=order_id)
            return CancellationResult(
                success=False,
                order_id=order_id,
                status="not_found",
                message=f"Order {order_id} was not found.",
            )

        # Already cancelled
        if order.status == OrderStatus.CANCELLED:
            logger.info("Cancel failed: already cancelled", order_id=order_id)
            return CancellationResult(
                success=False,
                order_id=order_id,
                status="already_cancelled",
                message=f"Order {order_id} has already been cancelled.",
            )

        # Already shipped or delivered
        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            logger.info("Cancel failed: already shipped", order_id=order_id, status=order.status.value)
            return CancellationResult(
                success=False,
                order_id=order_id,
                status="already_shipped",
                message=f"Order {order_id} has already been shipped and cannot be cancelled.",
            )

        # Check 24-hour window
        hours_since_order = (datetime.utcnow() - order.created_at).total_seconds() / 3600
        if hours_since_order > self.CANCELLATION_WINDOW_HOURS:
            logger.info(
                "Cancel failed: outside window",
                order_id=order_id,
                hours_since_order=round(hours_since_order, 1),
            )
            return CancellationResult(
                success=False,
                order_id=order_id,
                status="ineligible",
                message=(
                    f"Order {order_id} was placed more than 24 hours ago and is no longer "
                    f"eligible for cancellation. Our policy allows cancellations only within "
                    f"24 hours of placing an order."
                ),
            )

        # Success - cancel the order
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()

        logger.info("Order cancelled successfully", order_id=order_id, refund=order.total_amount)

        return CancellationResult(
            success=True,
            order_id=order_id,
            status="cancelled",
            message=(
                f"Order {order_id} has been successfully cancelled. "
                f"A refund of ${order.total_amount:.2f} will be processed within 3-5 business days."
            ),
            refund_amount=order.total_amount,
        )
