# E-commerce Multi-Agent Assistant

**A multi-agent customer service chatbot** for e-commerce: order tracking, cancellations (24-hour policy), and product/FAQ answers. Requests are routed by an LLM orchestrator to specialist agents; state and traces live in Redis. Built for clarity and interview demos.

**Stack:** FastAPI · Redis · OpenAI (routing + memory) · Vanilla JS UI (no build step)

---

## Try it in 2 minutes

```bash
cp .env.example .env   # set OPENAI_API_KEY
docker-compose up -d
curl -s http://localhost:8000/health | jq .
```

- **Chat UI:** http://localhost:8000/
- **API docs:** http://localhost:8000/docs
- **Run all tests:** `curl -s -X POST http://localhost:8000/tests/run-all -H "Content-Type: application/json" -d '{}' | jq '.results | length, [.results[] | {test_id, passed}]'`

Or use the **Tests** tab in the UI: run all scenarios and open a trace for any run.

---

## What it does

| Capability | Example |
|------------|--------|
| **Order tracking** | "Where is my order ORD-1234?" / "Track ORD-12345" |
| **Order cancellation** | "Cancel order ORD-6789" (24h policy; shipped/cancelled orders rejected) |
| **Product & policies** | "What's your return policy?" / "Shipping times?" |
| **Multi-turn** | "What's the status of ORD-1234?" → "Cancel that order" (resolves "that order") |
| **Out of scope** | "What's the weather?" → gentle guide to supported use cases |

Order IDs: `ORD-` + digits (e.g. `ORD-1234`, `ORD-12345`). Mock order API in `tools/order_api.py`; golden tests in `tests/golden/flows.json`.

---

## Architecture

```
User → Memory Agent (context, refs) → Orchestrator (LLM intent) → Order Tracking | Order Cancellation | Product Info
         ↓                                    ↓
      Redis (sessions)              Low confidence / unknown → gentle "here’s what I can do"
```

- **Memory Agent:** Resolves references ("that order" → last order_id), sentiment, context summary.
- **Orchestrator:** Single LLM call for intent + confidence; routes to agents or handles greeting/thanks/unknown.
- **Specialist agents:** Call Order API or Knowledge Base; return response + tool_calls; update session entities.
- **Redis:** Session state (history, extracted_entities), traces, stats. Stateless API → scale horizontally.

See `orchestrator/router.py` for routing prompt and examples; `agents/` for specialists; `memory/` for session store.

---

## Design decisions (for discussion)

| Decision | Rationale |
|----------|------------|
| **LLM routing** | Handles paraphrasing and ambiguous prompts; low confidence triggers gentle guidance instead of wrong agent. |
| **Redis for state** | Sessions, traces, stats with TTL; single shared store for multiple instances. |
| **Vanilla JS UI** | No build step; Chat, Trace, Stats, Tests tabs; easy to hand off or modify. |
| **Structured routing output** | Pydantic `RoutingDecision` (intent, confidence, reasoning) for observability and testing. |

---

## Project layout

```
agents/          # OrderTrackingAgent, OrderCancellationAgent, ProductInfoAgent, MemoryAgent
orchestrator/    # LLM routing (router.py), OpenAI client (llm_client.py)
memory/          # Redis session store, session state
tools/           # Mock order_api.py, knowledge_base.py
schemas/         # Pydantic models (session, agent, api, tests)
observability/   # Logging, tracer, stats, middleware
testing/         # TestScenarioStore, run_test / run_all_tests
ui/              # Static HTML/JS/CSS (Chat, Trace, Stats, Tests)
tests/golden/    # flows.json – golden E2E scenarios
src/main.py      # FastAPI app, /chat, /sessions, /stats, /tests
```

---

## Setup (detailed)

1. **Environment:** `cp .env.example .env` and set `OPENAI_API_KEY`, optionally `OPENAI_MODEL` (default `gpt-4o-mini`), `REDIS_URL` (default `redis://redis:6379` for Docker).
2. **Run:** `docker-compose up -d` → app on port 8000, Redis in container.
3. **Health:** `curl -s http://localhost:8000/health` → `{"status":"healthy","redis":"connected",...}`.

---

## API (summary)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | `{"session_id","message"}` → response, agent, tool_calls, handover |
| GET | `/sessions`, `/sessions/{id}`, `/sessions/{id}/trace` | List sessions, session + trace |
| GET | `/stats` | Aggregates: sessions, messages, latency, tokens, agents |
| GET | `/tests` | List scenarios |
| POST | `/tests/run-all` | Run all or `{"test_ids":["id1",...]}` |

---

## Running tests

- **UI:** Open the **Tests** tab → Run all (or select scenarios) → see pass/fail and "View trace" per run.
- **CLI:** `curl -s -X POST http://localhost:8000/tests/run-all -H "Content-Type: application/json" -d '{}' | jq .`
- **Demo script:** `./scripts/demo.sh` (health, chat examples, run-all; optional base URL).

Golden scenarios live in `tests/golden/flows.json`; runner in `testing/runner.py` (POSTs each turn to `/chat`, asserts agent and response content).

---

## Extending

- **New agent:** Subclass `BaseAgent` in `agents/`, implement `process(session, message)` → `AgentResponse`; register in `src/main.py` and add intent + examples in `orchestrator/router.py`.
- **New tool:** Add under `tools/`, inject into agent, call from `process()`.
- **Routing changes:** Edit system prompt and few-shot examples in `orchestrator/router.py`; adjust `RoutingDecision` and `_handle_special_intent()` as needed.

---

## Production notes

- Keep `OPENAI_API_KEY` (and Redis auth) in env or a secret manager.
- Use managed Redis with TLS in production; set `REDIS_URL` accordingly.
- App is stateless; scale behind a load balancer with shared Redis.
- Logs are JSON with correlation/session IDs; use `/stats` and `/sessions/{id}/trace` for debugging.
