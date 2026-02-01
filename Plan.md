# Project Board: Production-Ready Multi-Agent E-commerce Assistant

## Project Goal

Deliver a **scalable, observable, multi-agent conversational system** with a **traceable chat interface**, meeting all challenge requirements at a production bar.

---

## Milestone 0 — Architecture Lock (FOUNDATIONAL)

**Status:** Done
**Owner:** Lead / Architect
**Exit Criteria:** No work proceeds without this completed

### Tasks

* [x] Define system architecture (logical + physical)
* [x] Define agent responsibilities and boundaries
* [x] Define orchestrator control flow
* [x] Define state model (session, entities, context)
* [x] Define trace model (turn-level observability)

### Artifacts

* Architecture diagram
* `/schemas/*.json`
* README: “Architecture & Design Decisions”

### Acceptance Criteria

* All contracts versioned
* Schemas reviewed and frozen
* Clear separation of concerns documented

---

## Milestone 1 — Core Contracts & Schemas

**Status:** Done
**Owner:** Agent A

### Tasks

* [x] Agent input/output schema
* [x] Tool invocation schema
* [x] Trace event schema
* [x] Conversation state schema
* [x] Validation rules (order ID, timestamps, etc.)

### Artifacts

```
/schemas
  agent_response.json
  tool_call.json
  trace_event.json
  conversation_state.json
```

### Acceptance Criteria

* Schemas are deterministic
* Schemas enforce all business rules
* No agent relies on free-text outputs

---

## Milestone 2 — Orchestrator & State Machine

**Status:** Done
**Owner:** Agent B

### Tasks

* [x] Intent detection
* [x] Agent routing logic
* [x] Multi-turn state machine
* [x] Missing-information handling
* [x] Validation before agent execution

### Artifacts

```
/orchestrator
  router.py
  decision_engine.py
  state_machine.py
```

### Acceptance Criteria

* Orchestrator is deterministic
* No agent controls conversation flow
* All decisions are traceable

---

## Milestone 3 — Memory & Persistence Layer

**Status:** Done
**Owner:** Agent C

### Tasks

* [x] Redis session store
* [x] Conversation message store
* [x] State diffing mechanism
* [x] TTL and eviction policy

### Artifacts

```
/memory
  redis_store.py
  conversation_store.py
  state_diff.py
```

### Acceptance Criteria

* Stateless API pods
* Session recovery works
* State diffs are human-readable

---

## Milestone 4 — Business Agents Implementation

**Status:** Done
**Owner:** Agent D

### Tasks

* [x] OrderCancellationAgent
* [x] OrderTrackingAgent
* [x] ProductInfoAgent
* [x] Schema-validated responses only

### Artifacts

```
/agents
  order_cancellation.py
  order_tracking.py
  product_info.py
```

### Acceptance Criteria

* Agents are stateless
* No Redis or orchestrator logic inside agents
* Agents fail loudly on invalid input

---

## Milestone 5 — Mock APIs & Tooling

**Status:** Done
**Owner:** Agent E

### Tasks

* [x] Mock order database
* [x] Cancellation API (24-hour rule)
* [x] Tracking API
* [x] Deterministic error cases

### Artifacts

```
/tools
  order_api.py
  tracking_api.py
```

### Acceptance Criteria

* Business rules enforced in code
* Time-based logic testable
* APIs usable without LLMs

---

## Milestone 6 — Observability & Tracing

**Status:** Done
**Owner:** Agent F

### Tasks

* [x] Structured logging
* [x] Trace middleware
* [x] Trace store abstraction
* [x] Error and latency tracking

### Artifacts

```
/observability
  tracer.py
  logger.py
```

### Acceptance Criteria

* Every `/chat` call emits a trace
* Partial failures are visible
* Trace ≠ conversation data

---

## Milestone 7 — Chat Interface & Debug Console

**Status:** Done
**Owner:** Agent G

### Tasks

* [x] Chat UI (send messages)
* [x] Session browser
* [x] Conversation timeline
* [x] Trace inspector (side-by-side)

### Artifacts

```
/ui
  /pages
  /components
  /services
```

### Acceptance Criteria

* Conversation and trace views aligned by turn
* UI is read-only for traces
* Debuggable without backend logs

---

## Milestone 8 — API Surface & Documentation

**Status:** Done
**Owner:** Agent H

### Tasks

* [x] `/chat` endpoint spec
* [x] Read-only session APIs
* [x] OpenAPI / Swagger
* [x] README run instructions

### Artifacts

* OpenAPI spec
* README.md (complete)

### Acceptance Criteria

* Clean onboarding
* One-command startup
* APIs documented and versioned

---

## Milestone 9 — Dockerization & Packaging

**Status:** Done (UI Dockerfile deferred until M7)
**Owner:** Agent H

### Tasks

* [x] Backend Dockerfile
* [ ] UI Dockerfile (deferred until M7 Chat UI)
* [x] docker-compose.yml
* [x] Environment config

### Acceptance Criteria

* `docker-compose up` works
* Stateless backend containers
* Redis + API + UI wired correctly

---

## Milestone 10 — Validation & Review

**Status:** Done
**Owner:** Lead

### Tasks

* [x] End-to-end test scenarios (keyword + LLM paths; reviewable E2E in Chat UI)
* [x] Multi-turn conversation tests
* [x] Failure mode tests (404, 422, 24h rule)
* [x] Architecture review against requirements (docs/ARCHITECTURE_REVIEW.md)

### Acceptance Criteria

* All challenge criteria satisfied
* System explainable via UI
* Architecture change-tolerant

---

## Critical Path Summary

**Blocking:**
Milestone 0 → Milestone 1 → Milestone 2 → Milestone 6 → Milestone 10

Everything else can be parallelized safely.

---
