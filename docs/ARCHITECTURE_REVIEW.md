# Architecture Review vs Challenge Requirements

Checklist mapping [challenge.md](../Challenge.md) requirements to implementation.

## Core system

| Requirement | Implementation | Location |
|-------------|-----------------|----------|
| Order cancellation: ask for order ID, validate ORD-XXXX | Orchestrator validates slot; agents re-validate. Clarification when missing. | orchestrator/decision_engine, agents/order_cancellation, schemas/validation_rules.md |
| Order cancellation: only if placed &lt; 24h ago | Mock order API enforces 24h rule; returns rejected with reason. | tools/order_api.cancel_order |
| Order cancellation: mock API, inform user of result | OrderCancellationAgent calls cancel_order, returns structured response + tool_calls. | agents/order_cancellation, tools/order_api |
| Order tracking: ask for order ID, validate ORD-XXXX | Same slot validation; OrderTrackingAgent. | orchestrator, agents/order_tracking |
| Order tracking: mock API, status and estimated delivery | get_order_status returns status, estimated_delivery. | tools/tracking_api, agents/order_tracking |
| Product info: FAQ / product queries from knowledge base | ProductInfoAgent, JSON Q&A string search. | agents/product_info, tools/knowledge_base |

## Architecture and state

| Requirement | Implementation | Location |
|-------------|-----------------|----------|
| Multi-component, orchestrator delegates to specialized components | Orchestrator → Router → OrderCancellationAgent, OrderTrackingAgent, ProductInfoAgent. | orchestrator/, agents/ |
| Multi-turn: recall context (e.g. "that" → previous order/product) | Session state: extracted_entities, last_order_id; LLM or keyword resolves "that". | orchestrator/state_machine, orchestrator/llm_router, docs/MULTI_TURN_AND_LLM.md |
| Structured, predictable agent outputs | agent_response schema; tool_calls in response. | schemas/agent_response.json, POST /chat response |
| Documentation: multi-turn and state management | README, docs/LLM_ORCHESTRATOR_DESIGN.md, docs/MULTI_TURN_AND_LLM.md | docs/, README |

## Observability

| Requirement | Implementation | Location |
|-------------|-----------------|----------|
| Logging for key events | Structured JSON logging (chat_turn, errors). | observability/logger |
| Trace / observability | Trace event per turn; trace store; GET /sessions/{id}/traces. | observability/tracer, src/main.py |

## API and interface

| Requirement | Implementation | Location |
|-------------|-----------------|----------|
| Single HTTP endpoint POST /chat | Request: session_id, message. Response: response, agent, tool_calls, handover. | src/main.py |
| session_id for conversational context | Session state keyed by session_id; Redis or in-memory. | memory/session_store, memory/redis_store |

## Evaluation criteria

| Criterion | Notes |
|-----------|------|
| Scenario fitness | E2E tests (keyword, LLM, failure modes); reviewable scenarios in Chat UI. |
| Modularity | Orchestrator, agents, tools separate; new agent = new module + router entry. |
| Code readability | Comments, schemas, README, docs/. |
| Robustness | Validation (order_id, intent); fallback (LLM → keyword); 404/422 handling; 24h rule. |
| Bonus | Dockerfile, docker-compose, Swagger (/docs), trace inspector, E2E scenarios in UI. |

## Submission checklist

- [x] Source code: multi-agent + mock APIs, no third-party agent libraries
- [x] README: architecture diagram, design choices, build/run, schemas, Docker
- [x] Dockerfile and docker-compose.yml
- [ ] Share repo with specified reviewers; email link to magdalena.korzecmaro@zendesk.com
