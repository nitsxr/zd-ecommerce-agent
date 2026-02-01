"""Order tracking agent."""

import re
import time
from datetime import datetime

from agents.base import BaseAgent, validate_response
from observability.logger import get_logger
from schemas.agent import AgentResponse, ToolCall
from schemas.session import SessionState
from tools.order_api import OrderAPI, Order

logger = get_logger(__name__)

# Regex pattern for order ID validation
ORDER_ID_PATTERN = re.compile(r"ORD-\d{4}", re.IGNORECASE)


class OrderTrackingAgent(BaseAgent):
    """Agent for tracking order status."""

    name = "OrderTrackingAgent"

    def __init__(self, order_api: OrderAPI | None = None):
        """Initialize with optional OrderAPI instance."""
        self.order_api = order_api or OrderAPI()

    def _extract_order_ids(self, message: str) -> list[str]:
        """Extract all order IDs from a message."""
        matches = ORDER_ID_PATTERN.findall(message)
        # Normalize to uppercase
        return [match.upper() for match in matches]

    def _format_order_status(self, order: Order) -> str:
        """Format order details into a human-readable response."""
        status_messages = {
            "pending": "is being prepared",
            "processing": "is being processed",
            "shipped": "has been shipped",
            "delivered": "has been delivered",
            "cancelled": "has been cancelled",
        }

        status_text = status_messages.get(order.status.value, f"has status '{order.status.value}'")

        response = f"Your order {order.order_id} {status_text}."

        # Add tracking info if shipped
        if order.tracking_number:
            response += f"\n\nTracking number: {order.tracking_number}"

        # Add estimated delivery if available and not delivered/cancelled
        if order.estimated_delivery and order.status.value not in ("delivered", "cancelled"):
            delivery_date = order.estimated_delivery.strftime("%B %d, %Y")
            response += f"\n\nEstimated delivery: {delivery_date}"

        # Add product info
        response += f"\n\nProduct: {order.product_name}"
        if order.quantity > 1:
            response += f" (x{order.quantity})"

        return response

    @validate_response
    async def process(self, session: SessionState, message: str) -> AgentResponse:
        """
        Process a tracking request.

        Handles:
        - Valid order ID → fetch and return status
        - Invalid format → prompt for correct format
        - Order not found → helpful error message
        - Multiple order IDs → ask for clarification
        """
        logger.info("Processing tracking request", user_message=message[:100])

        # Extract order IDs from message
        order_ids = self._extract_order_ids(message)

        # No order ID found
        if not order_ids:
            return self._create_response(
                response=(
                    "I'd be happy to help track your order. Could you please provide your "
                    "order ID? You can find it in your confirmation email — it looks like "
                    "ORD-XXXX (for example, ORD-1234)."
                ),
                metadata={"reason": "no_order_id"},
            )

        # Multiple order IDs found
        if len(order_ids) > 1:
            order_list = ", ".join(order_ids)
            return self._create_response(
                response=(
                    f"I found multiple order IDs in your message: {order_list}. "
                    f"Which order would you like me to track?"
                ),
                metadata={"reason": "multiple_order_ids", "order_ids": order_ids},
            )

        # Single order ID - fetch status
        order_id = order_ids[0]
        logger.info("Fetching order status", order_id=order_id)

        # Track timing for tool call
        start_time = time.perf_counter()
        order = await self.order_api.get_order(order_id)
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Build tool call record
        tool_call = ToolCall(
            tool="OrderAPI.get_order",
            input={"order_id": order_id},
            result=order.model_dump() if order else None,
            duration_ms=duration_ms,
            success=order is not None,
            error=None if order else "Order not found",
        )

        # Order not found
        if order is None:
            return self._create_response(
                response=(
                    f"I couldn't find an order with ID {order_id}. Please double-check "
                    f"the order ID from your confirmation email. If you believe this is "
                    f"an error, please contact our support team."
                ),
                tool_calls=[tool_call],
                metadata={"reason": "order_not_found", "order_id": order_id},
            )

        # Success - format and return status
        response_text = self._format_order_status(order)

        # Update session with extracted entity
        if order_id not in session.extracted_entities.order_ids:
            session.extracted_entities.order_ids.insert(0, order_id)

        return self._create_response(
            response=response_text,
            tool_calls=[tool_call],
            confidence=1.0,
            metadata={
                "order_id": order_id,
                "order_status": order.status.value,
            },
        )
