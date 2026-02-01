# E2E User Flows

All end-to-end user flows the system must support. Each flow includes the user journey, system behavior, and expected outcomes.

---

## Flow Categories

| Category | Flows |
|----------|-------|
| Order Tracking | 1-3 |
| Order Cancellation | 4-8 |
| Product Information | 9-11 |
| Multi-Turn Context | 12-16 |
| Edge Cases & Fallbacks | 17-21 |
| Sentiment & Urgency | 22-24 |

---

## Order Tracking Flows

### Flow 1: Happy Path — Track Order

**Scenario:** User wants to know their order status.

```
User: "What's the status of my order ORD-1234?"
```

**System Behavior:**
1. Memory Agent: Extract order_id=ORD-1234, sentiment=neutral, urgency=low
2. Orchestrator: Route to OrderTrackingAgent (confidence: 0.95)
3. OrderTrackingAgent: Validate format, call Tracking API
4. Response: Order status and estimated delivery

**Expected Response:**
```
Your order ORD-1234 is currently "shipped" and is estimated to arrive on February 5th, 2026.
```

**Trace:**
```
OrchestratorAgent → OrderTrackingAgent
Tool: TrackingAPI.get_order({order_id: "ORD-1234"})
```

---

### Flow 2: Track Order — Invalid Format

**Scenario:** User provides order ID in wrong format.

```
User: "Track order 1234"
```

**System Behavior:**
1. Memory Agent: No valid order_id extracted, detect intent=tracking
2. Orchestrator: Route to OrderTrackingAgent
3. OrderTrackingAgent: Validation fails on format

**Expected Response:**
```
I'd be happy to help track your order. Could you please provide your order ID in the format ORD-XXXX (for example, ORD-1234)?
```

---

### Flow 3: Track Order — Not Found

**Scenario:** User provides valid format but order doesn't exist.

```
User: "Where is my order ORD-9999?"
```

**System Behavior:**
1. Memory Agent: Extract order_id=ORD-9999
2. Orchestrator: Route to OrderTrackingAgent
3. OrderTrackingAgent: API returns not found

**Expected Response:**
```
I couldn't find an order with ID ORD-9999. Please double-check the order ID from your confirmation email. If you believe this is an error, please contact our support team.
```

---

## Order Cancellation Flows

### Flow 4: Happy Path — Cancel Eligible Order

**Scenario:** User cancels an order placed within 24 hours.

```
User: "I want to cancel my order ORD-2345"
```

**System Behavior:**
1. Memory Agent: Extract order_id=ORD-2345, intent=cancellation
2. Orchestrator: Route to OrderCancellationAgent
3. OrderCancellationAgent: Check order timestamp (< 24h), process cancellation

**Expected Response:**
```
I've successfully cancelled your order ORD-2345. A full refund of $89.99 will be processed to your original payment method within 3-5 business days.
```

**Trace:**
```
OrchestratorAgent → OrderCancellationAgent
Tool: OrderAPI.get_order({order_id: "ORD-2345"}) → {created_at: "2026-02-01T10:00:00Z", ...}
Tool: OrderAPI.cancel_order({order_id: "ORD-2345"}) → {status: "cancelled", refunded: true}
```

---

### Flow 5: Cancel Order — Ineligible (Too Old)

**Scenario:** User tries to cancel an order placed more than 24 hours ago.

```
User: "Cancel order ORD-1111"
```

**System Behavior:**
1. Memory Agent: Extract order_id=ORD-1111, intent=cancellation
2. Orchestrator: Route to OrderCancellationAgent
3. OrderCancellationAgent: Check order timestamp (> 24h), reject

**Expected Response:**
```
I'm sorry, but order ORD-1111 was placed more than 24 hours ago and is no longer eligible for cancellation. Our policy allows cancellations only within 24 hours of placing an order.

If you'd like to return the item after receiving it, I can provide information about our return policy.
```

---

### Flow 6: Cancel Order — Already Shipped

**Scenario:** User tries to cancel an order that has already shipped.

```
User: "Please cancel ORD-3333"
```

**System Behavior:**
1. Memory Agent: Extract order_id=ORD-3333
2. OrderCancellationAgent: Order status = shipped

**Expected Response:**
```
I'm unable to cancel order ORD-3333 because it has already shipped. You can track your package using the order ID, or initiate a return once you receive it.

Would you like me to help you track this order instead?
```

---

### Flow 7: Cancel Order — Already Cancelled

**Scenario:** User tries to cancel an order that was already cancelled.

```
User: "Cancel my order ORD-4444"
```

**Expected Response:**
```
Order ORD-4444 has already been cancelled. Your refund should appear within 3-5 business days if it hasn't already. Is there anything else I can help you with?
```

---

### Flow 8: Cancel Order — Invalid Format

**Scenario:** User wants to cancel but provides invalid order ID.

```
User: "Cancel my recent order"
```

**System Behavior:**
1. Memory Agent: No order_id found, intent=cancellation
2. Orchestrator: Route to OrderCancellationAgent
3. OrderCancellationAgent: No order ID to process

**Expected Response:**
```
I'd be happy to help cancel your order. Could you please provide your order ID? You can find it in your confirmation email — it looks like ORD-XXXX.
```

---

## Product Information Flows

### Flow 9: FAQ — Return Policy

**Scenario:** User asks about return policy.

```
User: "What is your return policy?"
```

**System Behavior:**
1. Memory Agent: No entities, intent=product_info
2. Orchestrator: Route to ProductInfoAgent
3. ProductInfoAgent: Search knowledge base for "return policy"

**Expected Response:**
```
Our return policy allows returns within 30 days of delivery for most items. Items must be in original condition with tags attached. 

To start a return:
1. Log into your account
2. Go to Order History
3. Select "Return Item"

Refunds are processed within 5-7 business days after we receive the item.
```

---

### Flow 10: FAQ — Shipping Times

**Scenario:** User asks about delivery times.

```
User: "How long does shipping take?"
```

**Expected Response:**
```
Our shipping times depend on the method selected:

• Standard Shipping: 5-7 business days
• Express Shipping: 2-3 business days  
• Next-Day Shipping: 1 business day (order by 2pm)

Free standard shipping is available on orders over $50.
```

---

### Flow 11: Product-Specific Question

**Scenario:** User asks about a specific product.

```
User: "Are the wireless headphones water resistant?"
```

**System Behavior:**
1. Memory Agent: Extract product="wireless headphones"
2. ProductInfoAgent: Search knowledge base

**Expected Response:**
```
Our Wireless Pro Headphones have an IPX4 water resistance rating, which means they're protected against splashing water from any direction. They're great for workouts and light rain, but shouldn't be submerged in water.
```

---

## Multi-Turn Context Flows

### Flow 12: Track Then Cancel (Same Order)

**Scenario:** User tracks an order, then decides to cancel it.

```
Turn 1:
User: "What's the status of ORD-5555?"
Assistant: "Your order ORD-5555 is currently 'processing' and hasn't shipped yet..."

Turn 2:
User: "Actually, cancel that order"
```

**System Behavior (Turn 2):**
1. Memory Agent: Resolve "that order" → ORD-5555, context_summary="User checked status, now wants to cancel"
2. Orchestrator: Route to OrderCancellationAgent with resolved order_id

**Expected Response (Turn 2):**
```
I've cancelled order ORD-5555. Since it hadn't shipped yet, you'll receive a full refund within 3-5 business days.
```

---

### Flow 13: Product Info Then Order Action

**Scenario:** User asks about a product, then references it for an order.

```
Turn 1:
User: "Tell me about the bluetooth speaker"
Assistant: "Our Bluetooth Speaker Pro features 20-hour battery life..."

Turn 2:
User: "I ordered that last week but haven't received it. Order ORD-6666"
```

**System Behavior (Turn 2):**
1. Memory Agent: Extract order_id=ORD-6666, link to product="bluetooth speaker"
2. Orchestrator: Route to OrderTrackingAgent

**Expected Response (Turn 2):**
```
Let me check on your Bluetooth Speaker Pro order. Order ORD-6666 is currently "in transit" and expected to arrive by February 4th.
```

---

### Flow 14: Multiple Orders in Conversation

**Scenario:** User discusses multiple orders.

```
Turn 1:
User: "Track ORD-7777"
Assistant: "Order ORD-7777 is shipped..."

Turn 2:
User: "What about ORD-8888?"
Assistant: "Order ORD-8888 is processing..."

Turn 3:
User: "Cancel the first one"
```

**System Behavior (Turn 3):**
1. Memory Agent: Resolve "the first one" → ORD-7777 (first mentioned)
2. Process cancellation for ORD-7777

**Expected Response (Turn 3):**
```
I'll cancel order ORD-7777 for you. [processes cancellation]
```

---

### Flow 15: Follow-Up Question

**Scenario:** User asks a follow-up about previous topic.

```
Turn 1:
User: "What's your return policy?"
Assistant: "Our return policy allows returns within 30 days..."

Turn 2:
User: "Does that apply to electronics?"
```

**System Behavior (Turn 2):**
1. Memory Agent: Context = return policy discussion, resolve "that" → return policy
2. ProductInfoAgent: Search for electronics return policy

**Expected Response (Turn 2):**
```
Yes, the 30-day return policy applies to electronics as well. However, electronics must be unopened or defective to qualify for a full refund. Opened electronics may be subject to a 15% restocking fee.
```

---

### Flow 16: Correction Mid-Conversation

**Scenario:** User corrects themselves.

```
Turn 1:
User: "Cancel order ORD-1234"
Assistant: "I've cancelled order ORD-1234..."

Turn 2:
User: "Wait, I meant ORD-1235"
```

**System Behavior (Turn 2):**
1. Memory Agent: Detect correction, extract new order_id=ORD-1235
2. Orchestrator: Route to OrderCancellationAgent

**Expected Response (Turn 2):**
```
No problem! I've now cancelled order ORD-1235 as well. Note that order ORD-1234 remains cancelled from before. Would you like me to reinstate ORD-1234?
```

---

## Edge Cases & Fallbacks

### Flow 17: Out of Scope — Weather

**Scenario:** User asks something completely unrelated.

```
User: "What's the weather like today?"
```

**System Behavior:**
1. Memory Agent: No entities, no relevant intent
2. Orchestrator: Intent=unknown, confidence low

**Expected Response:**
```
I'm your e-commerce assistant and can help with:
• Tracking your orders
• Cancelling orders (within 24 hours)
• Answering questions about products and policies

Is there something I can help you with today?
```

---

### Flow 18: Ambiguous Request

**Scenario:** User request could mean multiple things.

```
User: "I have a problem with my order"
```

**System Behavior:**
1. Memory Agent: No order_id, vague intent
2. Orchestrator: Request clarification

**Expected Response:**
```
I'd be happy to help with your order. Could you tell me:
1. Your order ID (found in your confirmation email, format: ORD-XXXX)
2. What issue you're experiencing (tracking, cancellation, product question)
```

---

### Flow 19: Multiple Intents

**Scenario:** User asks about multiple things at once.

```
User: "Track ORD-1234 and what's your return policy?"
```

**System Behavior:**
1. Memory Agent: Extract order_id=ORD-1234, intents=[tracking, product_info]
2. Orchestrator: Handle primary intent first (tracking), queue secondary

**Expected Response:**
```
Let me help you with both:

**Order ORD-1234 Status:** Your order is "shipped" and arriving February 5th.

**Return Policy:** You can return items within 30 days of delivery. Items must be in original condition with tags attached.

Is there anything else you'd like to know?
```

---

### Flow 20: Empty Message

**Scenario:** User sends empty or whitespace message.

```
User: "   "
```

**Expected Response:**
```
I didn't catch that. How can I help you today? I can assist with tracking orders, cancellations, or product questions.
```

---

### Flow 21: Repeated Failed Attempts

**Scenario:** User keeps trying invalid order IDs.

```
Turn 1: "Track order ABC" → validation error
Turn 2: "Track order 123" → validation error  
Turn 3: "Track ORDER-1234" → validation error
```

**System Behavior (Turn 3):**
1. Memory Agent: Detect pattern of failed attempts, increase urgency

**Expected Response:**
```
I see you're having trouble with the order ID format. The correct format is ORD followed by 4 digits, like ORD-1234. 

You can find your order ID in:
• Your confirmation email subject line
• Your account's order history

Would you like me to help you find your order another way?
```

---

## Sentiment & Urgency Flows

### Flow 22: Frustrated User

**Scenario:** User shows frustration.

```
User: "I've been waiting FOREVER for my order ORD-2222. This is ridiculous!"
```

**System Behavior:**
1. Memory Agent: sentiment=frustrated, urgency=high, extract order_id
2. Orchestrator: Prioritize, include empathy in response

**Expected Response:**
```
I completely understand your frustration, and I apologize for the delay. Let me check on ORD-2222 right away.

Your order is currently "in transit" but appears to be delayed. The new estimated delivery is February 6th.

I've flagged this for priority attention. Is there anything else I can do to help make this right?
```

---

### Flow 23: Escalation Path

**Scenario:** User explicitly asks for human support.

```
User: "I want to speak to a real person"
```

**System Behavior:**
1. Memory Agent: Detect escalation request, urgency=high

**Expected Response:**
```
I understand you'd like to speak with a human agent. Here are your options:

• **Live Chat:** Available Mon-Fri 9am-6pm EST
• **Phone:** 1-800-XXX-XXXX (same hours)
• **Email:** support@example.com (24-48hr response)

Before you go, is there anything I can quickly help you with?
```

---

### Flow 24: Appreciation / Positive

**Scenario:** User expresses thanks.

```
Turn 1: [Order cancelled successfully]
Turn 2: "Thank you so much, that was really helpful!"
```

**System Behavior:**
1. Memory Agent: sentiment=positive, no action needed

**Expected Response:**
```
You're welcome! I'm glad I could help. If you have any other questions in the future, don't hesitate to ask. Have a great day!
```

---

## Test Scenario Matrix

| # | Flow | Agents Involved | Key Validation |
|---|------|-----------------|----------------|
| 1 | Track order (happy) | Memory → Orchestrator → Tracking | Correct status returned |
| 2 | Track order (bad format) | Memory → Orchestrator → Tracking | Format error message |
| 3 | Track order (not found) | Memory → Orchestrator → Tracking | Not found message |
| 4 | Cancel (eligible) | Memory → Orchestrator → Cancellation | Cancelled + refund info |
| 5 | Cancel (too old) | Memory → Orchestrator → Cancellation | Policy explanation |
| 6 | Cancel (shipped) | Memory → Orchestrator → Cancellation | Cannot cancel message |
| 7 | Cancel (already cancelled) | Memory → Orchestrator → Cancellation | Already cancelled message |
| 8 | Cancel (no order ID) | Memory → Orchestrator → Cancellation | Request order ID |
| 9 | FAQ (return policy) | Memory → Orchestrator → Product | Return policy info |
| 10 | FAQ (shipping) | Memory → Orchestrator → Product | Shipping times |
| 11 | Product question | Memory → Orchestrator → Product | Product-specific answer |
| 12 | Multi-turn: track then cancel | Memory (resolve) → Cancel | Context resolution |
| 13 | Multi-turn: product then order | Memory (link) → Tracking | Entity linking |
| 14 | Multi-turn: multiple orders | Memory (resolve "first") | Ordinal resolution |
| 15 | Multi-turn: follow-up | Memory (topic continuity) | Context maintained |
| 16 | Correction | Memory (detect correction) | Handle gracefully |
| 17 | Out of scope | Memory → Orchestrator (fallback) | Capability list |
| 18 | Ambiguous | Memory → Orchestrator (clarify) | Clarification request |
| 19 | Multiple intents | Memory → Orchestrator → Multiple | Both handled |
| 20 | Empty message | Validation | Helpful prompt |
| 21 | Repeated failures | Memory (frustration) | Extra help offered |
| 22 | Frustrated user | Memory (sentiment) | Empathy + priority |
| 23 | Escalation | Memory → Fallback | Human contact options |
| 24 | Positive feedback | Memory | Graceful close |
