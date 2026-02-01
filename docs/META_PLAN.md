# E-commerce Multi-Agent System — Design Plan

## Overview

A production-ready multi-agent system for handling customer service inquiries. The system uses LLM-based orchestration to route requests to specialized agents, maintains conversational context across turns, and provides full observability through a dedicated UI.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web UI                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   Chat   │ │  Trace   │ │  Stats   │ │  Tests   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      POST /chat Endpoint                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Memory Agent (LLM)                         │
│    (Context Analysis + Entity Extraction + Insight Surfacing)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LLM Orchestrator                              │
│         (Intent Classification + Routing + Context)             │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Order Tracking   │ │ Order Cancel     │ │ Product Info     │
│ Agent            │ │ Agent            │ │ Agent            │
└──────────────────┘ └──────────────────┘ └──────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Tracking API     │ │ Cancellation API │ │ Knowledge Base   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Redis                                   │
│            (Session State + Traces + Metrics)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| State store | In-memory, Redis | **Redis** | Production-ready, horizontal scaling, TTL for session expiry |
| Routing | Keyword match, ML classifier, LLM | **LLM with structured output** | Handles ambiguity, context-aware, demonstrates capability |
| Memory | Rule-based extraction, LLM-enhanced | **LLM-enhanced Memory Agent** | Deeper context understanding, sentiment analysis, proactive insights |
| Knowledge base | Embeddings + RAG, JSON + search | **JSON + simple search** | Sufficient for scope; RAG is a documented extension point |
| Frontend | React, HTMX, Vanilla JS | **Vanilla JS + HTML/CSS** | Zero dependencies, no build step, maximum simplicity |
| Observability | Logs only, Full tracing | **Full tracing with UI** | Visual debugging, enables replay, production mindset |
| Metrics storage | Time-series DB, In-memory | **Redis** | Sufficient for demo; Prometheus/InfluxDB for production |

---

## Core Capabilities

### 1. LLM-Based Orchestration
- Intent classification using structured LLM output
- Confidence scores on routing decisions
- Handoff protocol between orchestrator and specialized agents
- Fallback handling for out-of-scope requests

### 2. LLM-Enhanced Memory Agent

A dedicated agent that analyzes conversation context and surfaces relevant information before routing.

**Responsibilities:**
- Analyze conversation history for patterns and context
- Extract and track entities (order IDs, products, dates, issues)
- Detect user sentiment and urgency level
- Surface relevant insights to inform orchestrator decisions
- Identify unresolved issues from prior turns
- Generate concise context summaries for specialized agents

**When it activates:**
| Trigger | Action |
|---------|--------|
| New message arrives | Analyze against conversation history |
| Entity mentioned | Extract and link to known entities |
| Frustration detected | Flag urgency, suggest escalation path |
| Reference to prior turn | Resolve reference, surface original context |
| Complex multi-issue conversation | Summarize open threads |

**Output schema:**
```json
{
  "context_summary": "User has been tracking ORD-1234 (shipped). Now wants to cancel.",
  "extracted_entities": {
    "order_ids": [{"id": "ORD-1234", "status": "shipped", "mentioned_turn": 1}],
    "products": [],
    "issues": ["cancellation_request"]
  },
  "sentiment": {"score": -0.3, "label": "slightly_frustrated"},
  "urgency": "medium",
  "unresolved_issues": [],
  "suggested_context_for_agent": "User previously tracked this order. Order is shipped, may not be eligible for cancellation."
}
```

### 3. Specialized Agents

| Agent | Responsibility | Business Logic |
|-------|---------------|----------------|
| Order Tracking | Retrieve order status | Validate ORD-XXXX format, call tracking API |
| Order Cancellation | Process cancellations | 24-hour policy enforcement, validate eligibility |
| Product Info | Answer product questions | Search knowledge base, return relevant FAQs |

### 4. Multi-Turn Context
- Session state persisted in Redis with TTL (30 min idle timeout)
- Memory Agent maintains entity tracking across turns
- Supports references like "cancel the order for that" using prior context
- Context summaries generated for each agent call

### 5. Structured Outputs
All agents return validated responses conforming to defined schemas:
- `SessionState` — conversation context across turns
- `AgentResponse` — standardized agent output
- `ToolCall` — structured tool invocation record
- `TraceEvent` — observability data

---

## User Interface

Built with vanilla JavaScript — no framework, no build step.

| View | Purpose |
|------|---------|
| **Chat Panel** | Customer-facing conversation interface |
| **Trace Inspector** | View agent handoffs, tool calls, decision points |
| **Stats Dashboard** | Session counts, failure rates, latency percentiles, token costs |
| **Replay View** | Step through conversations turn-by-turn |
| **Test Runner** | Define scenarios, run tests, view results |

---

## Observability

Every request includes:
- **Correlation ID** for end-to-end tracing
- **Structured logs** (JSON): timestamp, session_id, agent, action, duration
- **Decision logging**: "Routed to OrderCancellationAgent (confidence: 0.94)"
- **Token usage** per request and per agent
- **Latency breakdown**: LLM call time, tool call time, total time

All trace data stored in Redis for UI visualization and replay.

---

## Error Handling

| Failure Mode | Handling Strategy |
|--------------|-------------------|
| Invalid order ID format | Validation error, prompt user for correct format |
| Order not found | Graceful message, suggest checking order ID |
| LLM malformed output | Schema validation, retry with fallback prompt |
| Out-of-scope request | Polite redirect, offer available capabilities |
| Session expired | Create new session, inform user |
| Redis unavailable | Graceful degradation, return error with retry guidance |

---

## Implementation Phases

### Phase 1: Foundation
- Define Pydantic schemas for all contracts
- Redis session store with TTL
- Structured logging with correlation IDs
- Mock order APIs (Flask)
- Docker Compose (app + Redis)

### Phase 2: Core Agents
- OrderTrackingAgent with API integration
- OrderCancellationAgent with 24hr policy logic
- ProductInfoAgent with knowledge base search
- Schema enforcement on all outputs

### Phase 3: Orchestrator
- LLM-based intent classification
- Handoff protocol to specialized agents
- Confidence scoring on routing
- Fallback handling

### Phase 4: Memory Agent
- LLM-enhanced context analysis
- Entity extraction with relationship tracking
- Sentiment and urgency detection
- Context summary generation for agents
- Reference resolution across turns

### Phase 5: Web UI
- Chat panel with session management
- Trace inspector with timeline view
- Stats dashboard with key metrics
- Test runner with scenario editor

### Phase 6: Polish
- Dockerfile + docker-compose (full stack)
- Architecture diagram
- API documentation (OpenAPI)
- README with design rationale

---

## Production Considerations

Beyond the scope of this implementation, but documented for completeness:

| Concern | Production Approach |
|---------|---------------------|
| Scaling | Kubernetes deployment, Redis cluster, rate limiting |
| Monitoring | Prometheus + Grafana, PagerDuty alerting |
| Cost control | Token budgets per session, model tiering |
| Security | Input sanitization, PII redaction in logs |
| Compliance | Conversation audit logs, data retention policies |

---

## Extension Points

**Adding a new agent:**
1. Create agent class implementing `BaseAgent` interface
2. Define input/output schemas
3. Register with orchestrator's intent classifier
4. Add routing case to LLM prompt

**Upgrading knowledge base to RAG:**
1. Replace JSON search with embedding-based retrieval
2. Add vector store (Pinecone, pgvector)
3. No changes to agent interface required

**Adding new tools:**
1. Implement tool with standardized `ToolCall` output
2. Register in agent's available tools
3. Traces automatically captured
