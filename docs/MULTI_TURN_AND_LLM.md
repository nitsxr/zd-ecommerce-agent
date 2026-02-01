# Multi-Turn Conversation and LLM Orchestrator

## How multi-turn works

- **Session state** is keyed by `session_id`. Each request loads state (turns, extracted_entities, slot_state), processes the new message, then persists state.
- **Conversation history** is stored as turns: each turn has user_message, agent, response, handover, tool_calls. The orchestrator (LLM or keyword) uses the last N turns plus the current message to decide intent and slots.
- **Reference resolution:** When the user says "that", "it", or "the order", the orchestrator resolves it from context:
  - **Keyword path:** `state.get_last_order_id()` returns the last mentioned order_id; if the current message doesn’t contain an order ID, that value is used for cancel/track.
  - **LLM path:** The prompt includes "Known context: order_id='ORD-1234', ..." and the last N turns, so the LLM can resolve "that" to the previous order_id (or product). The mock uses `context["last_order_id"]` the same way.
- **Entity update:** After a turn, extracted_entities are updated from the user message (e.g. `extract_order_id(user_message)`) or from the LLM output (when the LLM resolved order_id, we set `state.extracted_entities["order_id"]` before persisting). So the next turn has the correct context.

## State management with LLM

- **Input to LLM:** System prompt + last K turns (user/assistant) + "Known context: order_id=..., product=..." + current user message. Built in `orchestrator/prompts.build_orchestrator_messages(state, current_message)`.
- **Context for mock:** `context["last_order_id"]` from `state.get_last_order_id()` so the mock can return order_id for "cancel that" without calling the API.
- **After LLM returns:** We validate output (intent enum, order_id format). If proceed and we have order_id, we set `state.extracted_entities["order_id"] = order_id` so the next turn’s context includes it. Then we route to the agent and append the turn (which also runs extract_order_id on the user message for keyword-based entity update).
- **Agents and tools** do not see conversation history; they only receive the current slot values (order_id, message) and return a response. All multi-turn behavior is in the orchestrator.

## Enabling the LLM orchestrator

1. Set **USE_LLM_ORCHESTRATOR=true** so the decision engine uses the LLM path.
2. **Mock (no API key):** Set **MOCK_LLM=true** (default). The LLM path uses a keyword-based mock that returns the same structured output.
3. **Real OpenAI:** Set **MOCK_LLM=false** and **OPENAI_API_KEY=sk-...**. Optionally set **OPENAI_MODEL** (default gpt-3.5-turbo).
4. Run the API; each trace will include **orchestrator_type: "llm"** or **"keyword"** (keyword is used when USE_LLM_ORCHESTRATOR=false or when the LLM path fails and we fall back).

See [README](README.md) "LLM-based orchestrator" and [LLM_ORCHESTRATOR_DESIGN.md](LLM_ORCHESTRATOR_DESIGN.md) for scope, fallback, and guardrails.
