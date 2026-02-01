# Project Board: Production-Ready Multi-Agent E-commerce Assistant

## Project Goal

Deliver a **scalable, observable, multi-agent conversational system** with a **traceable chat interface**, meeting all challenge requirements at a production bar.

---

## Milestone 0 — Architecture Lock (FOUNDATIONAL)

**Status:** Blocking
**Owner:** Lead / Architect
**Exit Criteria:** No work proceeds without this completed

### Tasks

* [ ] Define system architecture (logical + physical)
* [ ] Define agent responsibilities and boundaries
* [ ] Define orchestrator control flow
* [ ] Define state model (session, entities, context)
* [ ] Define trace model (turn-level observability)

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

**Status:** Parallelizable after M0
**Owner:** Agent A

### Tasks

* [ ] Agent input/output schema
* [ ] Tool invocation schema
* [ ] Trace event schema
* [ ] Conversation state schema
* [ ] Validation rules (order ID, timestamps, etc.)

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

**Status:** Parallel (depends on M1)
**Owner:** Agent B

### Tasks

* [ ] Intent detection
* [ ] Agent routing logic
* [ ] Multi-turn state machine
* [ ] Missing-information handling
* [ ] Validation before agent execution

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

**Status:** Parallel (depends on M1)
**Owner:** Agent C

### Tasks

* [ ] Redis session store
* [ ] Conversation message store
* [ ] State diffing mechanism
* [ ] TTL and eviction policy

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

**Status:** Parallel (depends on M1)
**Owner:** Agent D

### Tasks

* [ ] OrderCancellationAgent
* [ ] OrderTrackingAgent
* [ ] ProductInfoAgent
* [ ] Schema-validated responses only

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

**Status:** Parallel (depends on M1)
**Owner:** Agent E

### Tasks

* [ ] Mock order database
* [ ] Cancellation API (24-hour rule)
* [ ] Tracking API
* [ ] Deterministic error cases

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

**Status:** Sequential (after M2, M3)
**Owner:** Agent F

### Tasks

* [ ] Structured logging
* [ ] Trace middleware
* [ ] Trace store abstraction
* [ ] Error and latency tracking

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

**Status:** Parallel (after M2, M6)
**Owner:** Agent G

### Tasks

* [ ] Chat UI (send messages)
* [ ] Session browser
* [ ] Conversation timeline
* [ ] Trace inspector (side-by-side)

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

**Status:** Parallel (after M2)
**Owner:** Agent H

### Tasks

* [ ] `/chat` endpoint spec
* [ ] Read-only session APIs
* [ ] OpenAPI / Swagger
* [ ] README run instructions

### Artifacts

* OpenAPI spec
* README.md (complete)

### Acceptance Criteria

* Clean onboarding
* One-command startup
* APIs documented and versioned

---

## Milestone 9 — Dockerization & Packaging

**Status:** Final
**Owner:** Agent H

### Tasks

* [ ] Backend Dockerfile
* [ ] UI Dockerfile
* [ ] docker-compose.yml
* [ ] Environment config

### Acceptance Criteria

* `docker-compose up` works
* Stateless backend containers
* Redis + API + UI wired correctly

---

## Milestone 10 — Validation & Review

**Status:** Final Gate
**Owner:** Lead

### Tasks

* [ ] End-to-end test scenarios
* [ ] Multi-turn conversation tests
* [ ] Failure mode tests
* [ ] Architecture review against requirements

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
