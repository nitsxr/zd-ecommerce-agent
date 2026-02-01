# LLM Orchestrator Design

## Scope and boundary

- **LLM decides:** intent (cancel / track / product / unclear), order_id (if present or resolvable from context), clarification_message (when to ask user), proceed (route to agent or return clarification).
- **LLM does not:** call tools, interpret business rules (e.g. 24h cancellation), or control conversation flow beyond one turn. Agents and tools are unchanged.
- **Structured output only:** JSON with `intent`, `order_id`, `clarification_message`, `proceed`. No free-form routing.

## LLM input

- **Conversation history:** Last N turns (user_message, assistant response) from `ConversationState.turns`, serialized as user/assistant messages.
- **Current message:** The new user message for this turn.
- **Context (for mock / multi-turn):** `extracted_entities` (e.g. last_order_id, product) so the LLM (or mock) can resolve "that" / "the order" from context.

See `orchestrator/prompts.build_orchestrator_messages(state, current_message)` and `orchestrator/llm_client.call_orchestrator_llm(messages, context)`.

## LLM output schema

Defined in `schemas/llm_orchestrator_output.json` and enforced in `orchestrator/llm_router.llm_orchestrate()`:

- **intent:** one of `cancel`, `track`, `product`, `unclear`
- **order_id:** string or null (ORD-XXXX when cancel/track and known)
- **clarification_message:** string or null (when proceed is false)
- **proceed:** boolean (true → route to agent; false → return clarification)

## Fallback strategy

- **When:** LLM call raises (timeout, network, parse error) or output is invalid (intent not in enum, order_id wrong format).
- **Action:** Fall back to keyword-based orchestrator (`orchestrator/intent.detect_intent`, `orchestrator/router.route`). No silent failure; trace includes `orchestrator_type: "llm"` or `"keyword"`.
- **Config:** `USE_LLM_ORCHESTRATOR=true` to use LLM path; `MOCK_LLM=true` to mock API (no key). Fallback is automatic on exception in decision_engine.

## Multi-turn context flow

1. **Load state** by session_id (turns, extracted_entities).
2. **Build messages** for LLM: system prompt + last K turns (user/assistant) + current user message. Context dict includes `last_order_id` from state.
3. **Call LLM** (or mock) with messages and context; get intent, order_id, clarification_message, proceed.
4. **Validate** output (intent enum, order_id ORD-\d+); if invalid, treat as unclear or fallback.
5. **If not proceed:** return clarification_message, append turn, persist state.
6. **If proceed:** route to agent (router), validate slots (e.g. order_id for cancel/track), invoke agent, append turn, persist state. Update extracted_entities from current turn (e.g. order_id from message or LLM).
7. **Emit trace** with orchestrator_type, intent, selected_agent.

Agents and tools remain stateless; they do not see conversation history. Only the orchestrator (LLM or keyword) uses state for intent and slot resolution.

## Guardrails and validation

- **LLM output is never trusted blindly.** All output is validated before routing:
  - **intent:** must be one of `cancel`, `track`, `product`, `unclear`; otherwise treated as `unclear`.
  - **order_id:** if present, must match `ORD-\d+`; otherwise cleared to null.
  - **proceed:** if true but cancel/track and order_id missing or invalid, we force clarification (proceed=false, clarification_message asking for order ID).
- Validation is implemented in `orchestrator/llm_router.llm_orchestrate()`. Invalid or malformed LLM response leads to fallback (unclear + no proceed) or exception fallback to keyword path.
- **When to use LLM vs keyword:** LLM improves natural language and multi-turn reference resolution; keyword is cheaper, faster, and deterministic. Use `USE_LLM_ORCHESTRATOR=true` for richer conversation; use `false` for cost/latency-sensitive or fully deterministic flows.
