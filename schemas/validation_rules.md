# Validation Rules

Deterministic rules used by the orchestrator and agents. Enforced in code and documented here.

## Order ID

- **Pattern**: `ORD-\d+` (e.g. ORD-1234, ORD-4567).
- **Where enforced**: Orchestrator (before calling cancel/track agents); agents may re-validate and fail loudly on invalid input.
- **Schema**: Can be expressed as JSON Schema pattern `^ORD-\d+$` for any field that represents an order ID.

## 24-Hour Cancellation Rule

- **Rule**: An order can only be canceled if it was placed less than 24 hours ago.
- **Where enforced**: In the **mock Order / Cancellation API** (tool). The orchestrator and OrderCancellationAgent do not interpret this rule; they call the tool, which returns success/failure and optionally a reason. The tool is the single source of truth for the 24h check.
- **Testability**: Use fixed or configurable "now" in tests so that time-based logic is deterministic.

## Timestamps

- **Format**: ISO8601 (e.g. `2025-02-01T12:00:00Z`).
- **Where used**: Trace events (`timestamp`), any order/tracking payloads that include dates (e.g. order_placed_at, estimated_delivery).

## Slots (Required Inputs)

- **Cancel / Track**: Require `order_id` (valid ORD-XXXX). If missing, orchestrator responds with clarification and sets slot_state (e.g. "awaiting order_id"); no agent is invoked until the slot is filled or resolved from context.
- **Product**: No required slot; query is free-form from the user message.
