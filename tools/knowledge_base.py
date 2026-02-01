"""Knowledge base for FAQ and product information."""

from pydantic import BaseModel, Field

from observability.logger import get_logger

logger = get_logger(__name__)


class FAQ(BaseModel):
    """A single FAQ entry."""

    id: str
    question: str
    answer: str
    keywords: list[str] = Field(default_factory=list)
    category: str = "general"


# Mock FAQ data
_FAQ_DATA: list[FAQ] = [
    FAQ(
        id="faq-1",
        question="What is your return policy?",
        answer=(
            "Our return policy allows returns within 30 days of delivery for most items. "
            "Items must be in original condition with tags attached.\n\n"
            "To start a return:\n"
            "1. Log into your account\n"
            "2. Go to Order History\n"
            "3. Select 'Return Item'\n\n"
            "Refunds are processed within 5-7 business days after we receive the item."
        ),
        keywords=["return", "refund", "send back", "return policy", "30 days"],
        category="returns",
    ),
    FAQ(
        id="faq-2",
        question="How long does shipping take?",
        answer=(
            "Our shipping times depend on the method selected:\n\n"
            "• Standard Shipping: 5-7 business days\n"
            "• Express Shipping: 2-3 business days\n"
            "• Next-Day Shipping: 1 business day (order by 2pm)\n\n"
            "Free standard shipping is available on orders over $50."
        ),
        keywords=["shipping", "delivery", "how long", "shipping time", "arrive"],
        category="shipping",
    ),
    FAQ(
        id="faq-3",
        question="What is your cancellation policy?",
        answer=(
            "Orders can be cancelled within 24 hours of placement, as long as the order "
            "hasn't shipped yet. After 24 hours or once shipped, you'll need to wait for "
            "delivery and then initiate a return.\n\n"
            "To cancel an order, provide your order ID (format: ORD-XXXX) and we'll "
            "process the cancellation immediately if eligible."
        ),
        keywords=["cancel", "cancellation", "cancel order", "stop order"],
        category="orders",
    ),
    FAQ(
        id="faq-4",
        question="Do you ship internationally?",
        answer=(
            "Yes, we ship to over 50 countries worldwide. International shipping typically "
            "takes 7-14 business days depending on the destination.\n\n"
            "Please note:\n"
            "• Import duties and taxes may apply\n"
            "• Some items may have shipping restrictions\n"
            "• Tracking is available for all international orders"
        ),
        keywords=["international", "worldwide", "overseas", "other countries", "abroad"],
        category="shipping",
    ),
    FAQ(
        id="faq-5",
        question="How do I track my order?",
        answer=(
            "You can track your order by:\n\n"
            "1. Providing your order ID (format: ORD-XXXX)\n"
            "2. Checking your email for tracking updates\n"
            "3. Logging into your account and viewing Order History\n\n"
            "Once your order ships, you'll receive a tracking number via email."
        ),
        keywords=["track", "tracking", "where is my order", "order status", "shipment status"],
        category="orders",
    ),
    FAQ(
        id="faq-6",
        question="What payment methods do you accept?",
        answer=(
            "We accept the following payment methods:\n\n"
            "• Credit/Debit Cards (Visa, Mastercard, Amex)\n"
            "• PayPal\n"
            "• Apple Pay\n"
            "• Google Pay\n"
            "• Shop Pay\n\n"
            "All transactions are securely processed and encrypted."
        ),
        keywords=["payment", "pay", "credit card", "paypal", "payment method"],
        category="payment",
    ),
    FAQ(
        id="faq-7",
        question="Are the wireless headphones water resistant?",
        answer=(
            "Our Wireless Pro Headphones have an IPX4 water resistance rating, which means "
            "they're protected against splashing water from any direction. They're great for "
            "workouts and light rain, but shouldn't be submerged in water."
        ),
        keywords=["headphones", "water resistant", "waterproof", "sweat", "workout", "ipx4"],
        category="products",
    ),
    FAQ(
        id="faq-8",
        question="What is the warranty on electronics?",
        answer=(
            "All electronics come with a 1-year manufacturer warranty covering defects in "
            "materials and workmanship.\n\n"
            "The warranty does not cover:\n"
            "• Accidental damage\n"
            "• Water damage (beyond rated resistance)\n"
            "• Normal wear and tear\n\n"
            "Extended warranty options are available at checkout."
        ),
        keywords=["warranty", "guarantee", "defect", "broken", "electronics warranty"],
        category="products",
    ),
    FAQ(
        id="faq-9",
        question="How do I contact customer support?",
        answer=(
            "You can reach our customer support team through:\n\n"
            "• Live Chat: Available Mon-Fri 9am-6pm EST\n"
            "• Phone: 1-800-555-0123 (same hours)\n"
            "• Email: support@example.com (24-48hr response)\n\n"
            "For fastest service, please have your order ID ready."
        ),
        keywords=["contact", "support", "help", "customer service", "phone", "email", "human", "speak to someone"],
        category="support",
    ),
    FAQ(
        id="faq-10",
        question="What is your price match policy?",
        answer=(
            "We offer price matching within 14 days of purchase if you find the same item "
            "at a lower price from an authorized retailer.\n\n"
            "Requirements:\n"
            "• Item must be identical (same model, color, size)\n"
            "• Competitor must be an authorized retailer\n"
            "• Item must be in stock at the competitor\n\n"
            "Contact support with proof of the lower price to request a match."
        ),
        keywords=["price match", "lower price", "cheaper", "price guarantee"],
        category="pricing",
    ),
    FAQ(
        id="faq-11",
        question="Do you offer gift wrapping?",
        answer=(
            "Yes! Gift wrapping is available for $4.99 per item. You can select this option "
            "at checkout.\n\n"
            "Gift wrapping includes:\n"
            "• Premium wrapping paper\n"
            "• Ribbon and bow\n"
            "• Gift message card\n\n"
            "Prices will be hidden on the packing slip for gift orders."
        ),
        keywords=["gift", "gift wrap", "wrapping", "present", "gift message"],
        category="orders",
    ),
    FAQ(
        id="faq-12",
        question="How does the return process work for electronics?",
        answer=(
            "For electronics, the standard 30-day return policy applies with some additional notes:\n\n"
            "• Unopened electronics: Full refund\n"
            "• Opened but defective: Full refund or exchange\n"
            "• Opened and working: May be subject to a 15% restocking fee\n\n"
            "Please include all original accessories, cables, and packaging for a smooth return."
        ),
        keywords=["return electronics", "electronics return", "restocking fee", "return headphones"],
        category="returns",
    ),
]


class KnowledgeBase:
    """Knowledge base for FAQ and product information."""

    def __init__(self, faqs: list[FAQ] | None = None):
        """Initialize with FAQ data."""
        self._faqs = faqs or _FAQ_DATA

    async def search(self, query: str, limit: int = 3) -> list[FAQ]:
        """
        Search the knowledge base for relevant FAQs.

        Uses simple keyword matching. In production, this could be
        replaced with embeddings/vector search.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching FAQs, ordered by relevance
        """
        logger.info("Searching knowledge base", query=query)

        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score each FAQ by keyword matches
        scored_faqs: list[tuple[FAQ, int]] = []

        for faq in self._faqs:
            score = 0

            # Check keyword matches
            for keyword in faq.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in query_lower:
                    score += 3  # Exact keyword match
                elif any(word in keyword_lower for word in query_words):
                    score += 1  # Partial match

            # Check question similarity
            question_words = set(faq.question.lower().split())
            overlap = len(query_words & question_words)
            score += overlap

            if score > 0:
                scored_faqs.append((faq, score))

        # Sort by score (descending) and return top results
        scored_faqs.sort(key=lambda x: x[1], reverse=True)
        results = [faq for faq, _ in scored_faqs[:limit]]

        logger.info("Knowledge base search complete", query=query, results_count=len(results))

        return results

    async def get_by_id(self, faq_id: str) -> FAQ | None:
        """Get a specific FAQ by ID."""
        for faq in self._faqs:
            if faq.id == faq_id:
                return faq
        return None

    async def get_by_category(self, category: str) -> list[FAQ]:
        """Get all FAQs in a category."""
        return [faq for faq in self._faqs if faq.category == category]
