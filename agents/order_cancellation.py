"""Order cancellation agent."""

import re
import time

from agents.base import BaseAgent, validate_response
from observability.logger import get_logger
from schemas.agent import AgentResponse, ToolCall
from schemas.session import SessionState
from tools.order_api import OrderAPI, OrderStatus

logger = get_logger(__name__)

# Regex pattern for order ID validation
ORDER_ID_PATTERN = re.compile(r"ORD-\d+", re.IGNORECASE)


class OrderCancellationAgent(BaseAgent):
    """Agent for cancelling orders with 24-hour policy enforcement."""

    name = "OrderCancellationAgent"

    def __init__(self, order_api: OrderAPI | None = None):
        """Initialize with optional OrderAPI instance."""
        self.order_api = order_api or OrderAPI()

    def _extract_order_ids(self, message: str) -> list[str]:
        """Extract all order IDs from a message."""
        matches = ORDER_ID_PATTERN.findall(message)
        return [match.upper() for match in matches]

    @validate_response
    async def process(self, session: SessionState, message: str) -> AgentResponse:
        """
        Process a cancellation request.

        Handles:
        - Valid order ID within 24hr window → cancel and confirm
        - Order too old → explain 24hr policy
        - Already shipped → cannot cancel, offer tracking
        - Already cancelled → inform user
        - No order ID → ask for order ID
        - Order not found → helpful error
        """
        logger.info("Processing cancellation request", user_message=message[:100])

        # Extract order IDs from message
        order_ids = self._extract_order_ids(message)

        # Check session for previously mentioned order IDs if none in current message
        if not order_ids and session.extracted_entities.order_ids:
            # Use most recent order from session context
            order_ids = [session.extracted_entities.order_ids[0]]
            logger.info("Using order ID from session context", order_id=order_ids[0])

        # No order ID found
        if not order_ids:
            return self._create_response(
                response=(
                    "I'd be happy to help cancel your order. Could you please provide your "
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
                    f"Which order would you like me to cancel?"
                ),
                metadata={"reason": "multiple_order_ids", "order_ids": order_ids},
            )

        # Single order ID - attempt cancellation
        order_id = order_ids[0]
        logger.info("Attempting to cancel order", order_id=order_id)

        # First, fetch the order to check its status
        start_time = time.perf_counter()
        order = await self.order_api.get_order(order_id)
        get_duration_ms = int((time.perf_counter() - start_time) * 1000)

        get_tool_call = ToolCall(
            tool="OrderAPI.get_order",
            input={"order_id": order_id},
            result=order.model_dump() if order else None,
            duration_ms=get_duration_ms,
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
                tool_calls=[get_tool_call],
                metadata={"reason": "order_not_found", "order_id": order_id},
            )

        # Order already cancelled
        if order.status == OrderStatus.CANCELLED:
            return self._create_response(
                response=(
                    f"Order {order_id} has already been cancelled. Your refund should "
                    f"appear within 3-5 business days if it hasn't already. "
                    f"Is there anything else I can help you with?"
                ),
                tool_calls=[get_tool_call],
                metadata={"reason": "already_cancelled", "order_id": order_id},
            )

        # Order already shipped or delivered
        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            status_text = "shipped" if order.status == OrderStatus.SHIPPED else "delivered"
            return self._create_response(
                response=(
                    f"I'm unable to cancel order {order_id} because it has already {status_text}. "
                    f"You can track your package using the order ID, or initiate a return "
                    f"once you receive it.\n\n"
                    f"Would you like me to help you track this order instead?"
                ),
                tool_calls=[get_tool_call],
                metadata={
                    "reason": "already_shipped",
                    "order_id": order_id,
                    "order_status": order.status.value,
                },
            )

        # Attempt cancellation (this checks the 24hr policy)
        start_time = time.perf_counter()
        result = await self.order_api.cancel_order(order_id)
        cancel_duration_ms = int((time.perf_counter() - start_time) * 1000)

        cancel_tool_call = ToolCall(
            tool="OrderAPI.cancel_order",
            input={"order_id": order_id},
            result={
                "success": result.success,
                "status": result.status,
                "refund_amount": result.refund_amount,
            },
            duration_ms=cancel_duration_ms,
            success=result.success,
            error=None if result.success else result.message,
        )

        tool_calls = [get_tool_call, cancel_tool_call]

        # Cancellation failed due to 24hr policy
        if result.status == "ineligible":
            return self._create_response(
                response=(
                    f"I'm sorry, but order {order_id} was placed more than 24 hours ago "
                    f"and is no longer eligible for cancellation. Our policy allows "
                    f"cancellations only within 24 hours of placing an order.\n\n"
                    f"If you'd like to return the item after receiving it, I can provide "
                    f"information about our return policy."
                ),
                tool_calls=tool_calls,
                metadata={
                    "reason": "outside_cancellation_window",
                    "order_id": order_id,
                },
            )

        # Success!
        if result.success:
            # Update session with extracted entity
            if order_id not in session.extracted_entities.order_ids:
                session.extracted_entities.order_ids.insert(0, order_id)

            refund_text = ""
            if result.refund_amount:
                refund_text = f"A refund of ${result.refund_amount:.2f} will be processed within 3-5 business days."

            return self._create_response(
                response=(
                    f"I've successfully cancelled your order {order_id}. {refund_text}\n\n"
                    f"Is there anything else I can help you with?"
                ),
                tool_calls=tool_calls,
                confidence=1.0,
                metadata={
                    "order_id": order_id,
                    "cancelled": True,
                    "refund_amount": result.refund_amount,
                },
            )

        # Unexpected failure
        return self._create_response(
            response=(
                f"I encountered an issue while trying to cancel order {order_id}: "
                f"{result.message}\n\n"
                f"Please try again or contact our support team for assistance."
            ),
            tool_calls=tool_calls,
            metadata={
                "reason": "cancellation_failed",
                "order_id": order_id,
                "error": result.message,
            },
        )
