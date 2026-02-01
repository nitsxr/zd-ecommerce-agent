# Implementation Milestones

## Overview

8 milestones from foundation to polished submission. Each milestone has a clear deliverable and acceptance criteria.

```
M1 Foundation ──► M2 First Agent ──► M3 Orchestrator ──► M4 Memory Agent
                                            │
                                            ▼
                  M8 Polish ◄── M7 Testing ◄── M6 Tracing ◄── M5 Chat UI
```

**Note:** M4 (Memory Agent) is an LLM-enhanced component that analyzes conversation context, extracts entities, detects sentiment, and surfaces relevant insights before routing.

---

## Milestone 1: Foundation

**Goal:** Infrastructure and contracts in place. System runs but does nothing yet.

**Deliverable:** `docker-compose up` starts app + Redis, health check returns 200, structured logging works.

### TODOs

#### Project Structure
- [ ] Create directory structure:
  ```
  ├── agents/
  ├── orchestrator/
  ├── tools/
  ├── memory/
  ├── observability/
  ├── schemas/
  ├── ui/
  ├── tests/
  └── src/
  ```
- [ ] Create `requirements.txt` with pinned versions
- [ ] Create `.env.example` with required environment variables

#### Schemas (Pydantic Models)
- [ ] `SessionState`: session_id, conversation_history, extracted_entities, created_at, updated_at, ttl
- [ ] `AgentResponse`: response, agent, tool_calls, handover, confidence, metadata
- [ ] `ToolCall`: tool, input, result, duration_ms, success
- [ ] `TraceEvent`: timestamp, session_id, event_type, agent, action, duration_ms, tokens_used, metadata
- [ ] `ChatRequest`: session_id, message
- [ ] `ChatResponse`: extends AgentResponse with session_id
- [ ] Export JSON schemas for documentation

#### Redis Session Store
- [ ] Define `SessionStore` protocol/interface
- [ ] Implement `RedisSessionStore`:
  - `get_session(session_id) -> SessionState | None`
  - `save_session(session: SessionState) -> None`
  - `delete_session(session_id) -> None`
  - `list_sessions(limit=100) -> List[SessionSummary]`
- [ ] Configure TTL (default 30 minutes)
- [ ] Handle Redis connection errors gracefully

#### Structured Logging
- [ ] Create `Logger` class with JSON output
- [ ] Include fields: timestamp, level, correlation_id, session_id, agent, action, duration_ms
- [ ] Implement correlation ID middleware for FastAPI
- [ ] Log at appropriate levels (debug, info, warn, error)

#### Mock APIs
- [ ] `OrderAPI`:
  - `get_order(order_id) -> Order | None`
  - `cancel_order(order_id) -> CancellationResult`
  - Sample data: 5-10 orders with varied timestamps
- [ ] `KnowledgeBase`:
  - JSON file with 10-15 FAQ entries
  - `search(query) -> List[FAQ]`

#### Docker Setup
- [ ] `Dockerfile`:
  - Python 3.11+ base
  - Install dependencies
  - Copy source
  - Run with uvicorn
- [ ] `docker-compose.yml`:
  - App service (port 8000)
  - Redis service (port 6379)
  - Volume for Redis persistence
  - Environment variables from .env
- [ ] `.dockerignore` for build optimization

#### FastAPI App Shell
- [ ] `GET /health` - returns `{"status": "healthy", "redis": "connected"}`
- [ ] `POST /chat` - stub returning `{"error": "not implemented"}`
- [ ] CORS middleware configured
- [ ] Static file serving for UI (placeholder)

### Acceptance Criteria
- [ ] `docker-compose up` succeeds without errors
- [ ] `curl localhost:8000/health` returns 200 with Redis connected
- [ ] Logs appear in JSON format with correlation IDs
- [ ] Redis CLI can connect and read/write test keys

---

## Milestone 2: First Agent E2E

**Goal:** Prove the agent architecture with one fully working agent.

**Deliverable:** POST `/chat` with "What's the status of ORD-1234?" returns structured response with tracking info.

### TODOs

#### Base Agent Interface
- [ ] Define `BaseAgent` abstract class:
  ```python
  async def process(self, session: SessionState, message: str) -> AgentResponse
  ```
- [ ] Schema validation decorator for agent outputs
- [ ] Standard error response format

#### Order Tracking Agent
- [ ] Implement `OrderTrackingAgent(BaseAgent)`:
  - Extract order ID from message (regex: `ORD-\d{4}`)
  - Validate order ID format
  - Call `OrderAPI.get_order()`
  - Format response with status and estimated delivery
- [ ] Handle edge cases:
  - Invalid order ID format → prompt for correct format
  - Order not found → helpful error message
  - Multiple order IDs in message → ask for clarification

#### LLM Client
- [ ] Create `LLMClient` wrapper:
  - OpenAI SDK initialization
  - `complete(messages, response_format) -> StructuredOutput`
  - Token counting (prompt + completion)
  - Retry logic with exponential backoff
- [ ] Handle errors:
  - Rate limits → retry with backoff
  - Timeout → return error response
  - Invalid response → retry once, then fail gracefully
- [ ] Configuration:
  - Model selection (env var)
  - Temperature, max_tokens
  - Timeout settings

#### Wire Up /chat Endpoint
- [ ] Parse `ChatRequest` (session_id, message)
- [ ] Load or create session from Redis
- [ ] Call `OrderTrackingAgent.process()`
- [ ] Save updated session to Redis
- [ ] Return `ChatResponse`

#### Basic Tracing
- [ ] Create `TraceEvent` on each request
- [ ] Store trace events in Redis (list per session)
- [ ] Include: timestamp, agent, action, duration_ms, tokens_used

### Acceptance Criteria
- [ ] `POST /chat {"session_id": "test", "message": "Track order ORD-1234"}` returns:
  ```json
  {
    "response": "Your order ORD-1234 is currently 'shipped' and estimated to arrive on ...",
    "agent": "OrderTrackingAgent",
    "tool_calls": [{"tool": "OrderAPI", "input": {"order_id": "ORD-1234"}, ...}]
  }
  ```
- [ ] Invalid order ID returns validation error message
- [ ] Session state persists across requests (same session_id)
- [ ] Trace events stored in Redis

---

## Milestone 3: Orchestrator + All Agents

**Goal:** LLM-based routing to multiple specialized agents.

**Deliverable:** Different messages route to correct agents with handover field populated.

### TODOs

#### Order Cancellation Agent
- [ ] Implement `OrderCancellationAgent(BaseAgent)`:
  - Extract and validate order ID
  - Fetch order to check timestamp
  - Enforce 24-hour policy (order.created_at > now - 24h)
  - Call `OrderAPI.cancel_order()` if eligible
  - Return cancellation result or ineligibility reason
- [ ] Handle edge cases:
  - Order too old → explain 24-hour policy (Flow 5)
  - Order already shipped → cannot cancel, offer tracking (Flow 6)
  - Order already cancelled → inform user, mention refund (Flow 7)
  - No order ID provided → ask for order ID (Flow 8)
  - Order not found → helpful error (Flow 3 pattern)

#### Product Info Agent
- [ ] Implement `ProductInfoAgent(BaseAgent)`:
  - Parse user query for keywords
  - Search knowledge base
  - Return top matching FAQ(s)
  - Handle no results gracefully
- [ ] Knowledge base structure:
  ```json
  {
    "faqs": [
      {"id": "1", "question": "...", "answer": "...", "keywords": ["..."]}
    ]
  }
  ```

#### LLM Orchestrator
- [ ] Design orchestrator prompt:
  - System message with available agents and their capabilities
  - Few-shot examples of routing decisions
  - Instruction to output structured JSON
- [ ] Define routing output schema:
  ```json
  {
    "intent": "order_tracking | order_cancellation | product_info | unknown",
    "confidence": 0.95,
    "reasoning": "User asked about order status",
    "extracted_entities": {"order_id": "ORD-1234"}
  }
  ```
- [ ] Implement `OrchestratorAgent`:
  - Call LLM with routing prompt
  - Parse structured output
  - Route to appropriate agent
  - Handle low confidence (< 0.7) → ask for clarification
- [ ] Implement fallback handling:
  - Unknown intent → polite message listing capabilities (Flow 17)
  - Ambiguous request → ask clarifying question (Flow 18)
  - Multiple intents → handle both in single response (Flow 19)
  - Empty/whitespace message → helpful prompt (Flow 20)
  - Escalation request ("speak to human") → provide contact options (Flow 23)
  - Positive feedback → graceful acknowledgment (Flow 24)

#### Update /chat Endpoint
- [ ] Route all requests through orchestrator first
- [ ] Orchestrator decides which agent handles request
- [ ] Include `handover` field in response: `"OrchestratorAgent → OrderTrackingAgent"`
- [ ] Log routing decision with confidence

### Acceptance Criteria
- [ ] "Track my order ORD-1234" → routes to OrderTrackingAgent (Flow 1)
- [ ] "Cancel order ORD-5678" → routes to OrderCancellationAgent (Flow 4)
- [ ] "What's your return policy?" → routes to ProductInfoAgent (Flow 9)
- [ ] "What's the weather?" → returns fallback response (Flow 17)
- [ ] "I have a problem with my order" → asks for clarification (Flow 18)
- [ ] "Track ORD-1234 and what's your return policy?" → handles both intents (Flow 19)
- [ ] Empty message → returns helpful prompt (Flow 20)
- [ ] "I want to speak to a real person" → provides contact options (Flow 23)
- [ ] "Thank you!" → graceful acknowledgment (Flow 24)
- [ ] All responses include `handover` field
- [ ] Routing decisions logged with confidence scores

---

## Milestone 4: LLM-Enhanced Memory Agent

**Goal:** Intelligent context analysis that surfaces relevant information before routing.

**Deliverable:** Memory Agent analyzes each message, extracts entities, detects sentiment, and provides context summaries to the orchestrator and agents.

### TODOs

#### Memory Agent Schema
- [ ] Define `MemoryAnalysis` output schema:
  ```python
  class MemoryAnalysis(BaseModel):
      context_summary: str  # Brief summary for orchestrator
      extracted_entities: ExtractedEntities
      sentiment: SentimentAnalysis
      urgency: Literal["low", "medium", "high", "critical"]
      unresolved_issues: List[str]
      suggested_context_for_agent: str  # Tailored context for the handling agent
      references_resolved: List[ReferenceResolution]
  ```
- [ ] Define `ExtractedEntities`:
  ```python
  class ExtractedEntities(BaseModel):
      order_ids: List[EntityMention]  # id, status, mentioned_turn
      products: List[EntityMention]
      issues: List[str]  # e.g., ["cancellation_request", "delivery_concern"]
      dates: List[str]
  ```
- [ ] Define `SentimentAnalysis`:
  ```python
  class SentimentAnalysis(BaseModel):
      score: float  # -1.0 to 1.0
      label: Literal["positive", "neutral", "slightly_frustrated", "frustrated", "angry"]
      indicators: List[str]  # e.g., ["repeated question", "caps usage"]
  ```

#### Memory Agent Implementation
- [ ] Create `MemoryAgent(BaseAgent)`:
  - Input: current message + session state (full history)
  - Output: `MemoryAnalysis`
- [ ] Design memory analysis prompt:
  - System message explaining role
  - Conversation history formatting
  - Few-shot examples of analysis
  - Structured output enforcement
- [ ] Implement entity extraction:
  - Order IDs (regex + LLM validation)
  - Products (LLM extraction from context)
  - Issues/intents mentioned
- [ ] Implement sentiment detection:
  - Analyze tone indicators
  - Track frustration escalation across turns
  - Flag urgent situations

#### Reference Resolution
- [ ] Resolve pronouns and references:
  - "that order" → most recent order_id (Flow 12)
  - "the product" / "those headphones" → most recent product (Flow 13)
  - "it" → context-dependent resolution
  - "the first one" / "the second order" → ordinal resolution (Flow 14)
  - "my previous question" → reference to prior turn
- [ ] Handle follow-up questions:
  - "Does that apply to electronics?" → link to prior topic (Flow 15)
  - Maintain topic continuity across turns
- [ ] Handle corrections:
  - "Wait, I meant ORD-1235" → detect correction, process new ID (Flow 16)
  - Acknowledge the correction gracefully
- [ ] Log all resolutions for tracing:
  ```json
  {"reference": "that order", "resolved_to": "ORD-1234", "confidence": 0.95}
  ```

#### Context Surfacing
- [ ] Generate context summary for orchestrator:
  - What has happened so far
  - What the user likely wants now
  - Any relevant history
- [ ] Generate agent-specific context:
  - Tailored to the agent that will handle the request
  - Include relevant entity details
  - Include sentiment/urgency if relevant

#### Urgency Detection
- [ ] Implement urgency scoring:
  | Signal | Urgency Impact |
  |--------|---------------|
  | Multiple failed attempts | +1 level (Flow 21) |
  | Frustrated sentiment | +1 level (Flow 22) |
  | Time-sensitive issue | +1 level |
  | Caps/exclamation marks | +0.5 level |
  | Polite tone | baseline |
- [ ] Surface urgency in analysis output
- [ ] Log urgency decisions
- [ ] Detect repeated failures pattern:
  - Track validation errors across turns
  - After 2-3 failures, offer extra help (Flow 21)
  - Provide alternative ways to find order ID

#### Integration with Pipeline
- [ ] Call Memory Agent before Orchestrator
- [ ] Pass `MemoryAnalysis` to Orchestrator for routing decision
- [ ] Pass `suggested_context_for_agent` to handling agent
- [ ] Store analysis in session state
- [ ] Include memory analysis in trace events

#### Update Session State
- [ ] Add `memory_analyses: List[MemoryAnalysis]`
- [ ] Add `conversation_history: List[ConversationTurn]`
- [ ] Add `entity_registry`: persistent entity tracking
- [ ] Limit history (last 10 turns, summarize older)

### Acceptance Criteria
- [ ] Turn 1: "What's the status of ORD-1234?" → Memory extracts order_id, neutral sentiment
- [ ] Turn 2: "Cancel that order" → Memory resolves "that order" to ORD-1234 (Flow 12)
- [ ] Turn 3: "Why isn't this working?!" → Memory detects frustration, increases urgency (Flow 22)
- [ ] Memory analysis appears in trace for each turn
- [ ] Context summary passed to orchestrator is accurate
- [ ] Sentiment tracking works across conversation
- [ ] Multi-turn: "Tell me about headphones" then "Cancel the order for those" → resolved correctly (Flow 13)
- [ ] Multiple orders: Track ORD-1111, track ORD-2222, "cancel the first one" → cancels ORD-1111 (Flow 14)
- [ ] Follow-up: "What's return policy?" then "Does that apply to electronics?" → context maintained (Flow 15)
- [ ] Correction: "Cancel ORD-1234" then "Wait, I meant ORD-1235" → handles gracefully (Flow 16)
- [ ] Repeated failures: 3 invalid order IDs → offers extra help finding order ID (Flow 21)

---

## Milestone 5: Chat UI

**Goal:** Web interface for chatting with the system.

**Deliverable:** Browser-based chat that persists across page refreshes.

### TODOs

#### HTML Structure
- [ ] Create `ui/index.html`:
  - Header with title
  - Main area with panels (chat, trace, stats)
  - Clean, professional layout
- [ ] Create `ui/styles.css`:
  - Modern, minimal design
  - Responsive layout
  - Message bubbles (user vs assistant)
  - Loading states

#### Chat Panel Component
- [ ] Create `ui/components/chat-panel.js`:
  - Message input field
  - Send button (Enter key support)
  - Message history display
  - User messages (right-aligned)
  - Assistant messages (left-aligned, show agent name)
  - Loading indicator while waiting
- [ ] Session management:
  - Generate UUID for new session
  - Store session_id in localStorage
  - "New Conversation" button
  - Display current session_id

#### API Integration
- [ ] Create `ui/services/api.js`:
  - `sendMessage(sessionId, message) -> ChatResponse`
  - Error handling with user-friendly messages
  - Loading state management

#### FastAPI Static Serving
- [ ] Serve UI files from `/` path
- [ ] Configure proper MIME types
- [ ] Enable CORS for development

#### Error Handling
- [ ] Display API errors gracefully
- [ ] Retry button on failure
- [ ] Connection lost indicator

### Acceptance Criteria
- [ ] Navigate to `localhost:8000` → see chat interface
- [ ] Type message, press Enter → see response
- [ ] Response shows agent name
- [ ] Refresh page → conversation history preserved (same session)
- [ ] Click "New Conversation" → fresh session
- [ ] API error → user-friendly error message

---

## Milestone 6: Tracing & Stats UI

**Goal:** Visualize conversation traces and system metrics.

**Deliverable:** Can see trace timeline and stats dashboard.

### TODOs

#### Backend Endpoints
- [ ] `GET /sessions` → list recent sessions with summary
- [ ] `GET /sessions/{id}` → session details with full trace
- [ ] `GET /sessions/{id}/trace` → trace events only
- [ ] `GET /stats` → aggregate statistics:
  ```json
  {
    "total_sessions": 150,
    "total_messages": 423,
    "success_rate": 0.94,
    "avg_latency_ms": 850,
    "tokens_used": 125000,
    "agent_distribution": {"OrderTracking": 45, ...}
  }
  ```

#### Session Browser
- [ ] Create `ui/components/session-list.js`:
  - List recent sessions
  - Show: session_id (truncated), message count, last active, status
  - Click to select → load trace
  - Search/filter by session_id

#### Trace Timeline Component
- [ ] Create `ui/components/conversation-timeline.js`:
  - Vertical timeline of events
  - Each turn: user message → orchestrator → agent → response
  - Visual indicators: agent type (color coded), success/failure
  - Expandable details per event

#### Trace Inspector Component
- [ ] Create `ui/components/trace-inspector.js`:
  - Click event in timeline → show details
  - Display: timestamp, duration, tokens used
  - Show tool calls with inputs/outputs
  - Show state diff (what changed in session)
  - Show LLM prompt/response (collapsible)

#### Stats Dashboard Component
- [ ] Create `ui/components/stats-dashboard.js`:
  - Total sessions / messages
  - Success rate (pie chart or percentage)
  - Latency: avg, p50, p95, p99
  - Token usage total and per-session average
  - Agent distribution (bar chart)
- [ ] Auto-refresh every 30 seconds

### Acceptance Criteria
- [ ] Session list shows recent conversations
- [ ] Click session → trace timeline appears
- [ ] Timeline shows orchestrator → agent flow visually
- [ ] Click event → detailed inspector view
- [ ] Stats dashboard shows meaningful metrics
- [ ] Stats update when new conversations happen

---

## Milestone 7: Testing UI

**Goal:** Define and run test scenarios from the UI.

**Deliverable:** Can create multi-turn test scenarios and see pass/fail results.

### TODOs

#### Test Scenario Schema
- [ ] Define `TestScenario`:
  ```json
  {
    "id": "test-1",
    "name": "Track then cancel",
    "description": "User tracks order then cancels it",
    "turns": [
      {"message": "Track ORD-1234", "expect_agent": "OrderTrackingAgent"},
      {"message": "Cancel that", "expect_agent": "OrderCancellationAgent", "expect_contains": "cancelled"}
    ]
  }
  ```
- [ ] Support assertion types:
  - `expect_agent`: which agent should handle
  - `expect_contains`: response should contain string
  - `expect_not_contains`: response should not contain
  - `semantic_match`: LLM judges similarity (optional)

#### Backend Endpoints
- [ ] `GET /tests` → list test scenarios
- [ ] `POST /tests` → create test scenario
- [ ] `PUT /tests/{id}` → update test scenario
- [ ] `DELETE /tests/{id}` → delete test scenario
- [ ] `POST /tests/{id}/run` → run test, return results:
  ```json
  {
    "test_id": "test-1",
    "passed": false,
    "turns": [
      {"passed": true, "actual_agent": "OrderTrackingAgent"},
      {"passed": false, "reason": "Expected OrderCancellationAgent, got OrderTrackingAgent"}
    ],
    "session_id": "test-session-xyz"
  }
  ```
- [ ] `POST /tests/run-all` → run all tests

#### Golden Test Suite
- [ ] Create pre-built scenarios covering all E2E flows:
  
  **Order Tracking (Flows 1-3):**
  - Happy path: track order with valid ID
  - Edge case: invalid order ID format
  - Edge case: order not found
  
  **Order Cancellation (Flows 4-8):**
  - Happy path: cancel eligible order
  - Edge case: order too old (24hr policy)
  - Edge case: order already shipped
  - Edge case: order already cancelled
  - Edge case: no order ID provided
  
  **Product Info (Flows 9-11):**
  - FAQ: return policy
  - FAQ: shipping times
  - Product-specific question
  
  **Multi-Turn Context (Flows 12-16):**
  - Track then cancel same order
  - Product info then order action
  - Multiple orders, ordinal reference
  - Follow-up question
  - User correction mid-conversation
  
  **Edge Cases (Flows 17-21):**
  - Out of scope (weather question)
  - Ambiguous request
  - Multiple intents in one message
  - Empty message
  - Repeated validation failures
  
  **Sentiment (Flows 22-24):**
  - Frustrated user (caps, exclamation)
  - Escalation request
  - Positive feedback
  
- [ ] Store in `tests/golden/` as JSON files
- [ ] Load on startup
- [ ] Total: 24 golden tests matching E2E flows

#### Test Editor UI
- [ ] Create `ui/components/test-editor.js`:
  - List existing tests
  - Create new test form
  - Add/remove turns
  - Set assertions per turn
  - Save/delete tests

#### Test Runner UI
- [ ] Create `ui/components/test-runner.js`:
  - "Run All" button
  - "Run Selected" button
  - Progress indicator
  - Results summary: X passed, Y failed
  - Per-test results with expandable details
  - Click failed test → link to session trace

### Acceptance Criteria
- [ ] Can view list of test scenarios
- [ ] Can create new test with multiple turns
- [ ] Can run single test and see pass/fail
- [ ] Can run all tests and see summary
- [ ] Failed tests show clear reason
- [ ] Can click through to trace of test session
- [ ] Golden tests all pass

---

## Milestone 8: Polish & Documentation

**Goal:** Production-ready submission with full documentation.

**Deliverable:** Complete, documented system ready for review.

### TODOs

#### README.md
- [ ] Project overview (2-3 paragraphs)
- [ ] Architecture diagram (Mermaid):
  ```mermaid
  graph TD
    UI[Web UI] --> API[FastAPI]
    API --> Memory[Memory Agent]
    Memory --> Orch[Orchestrator]
    Orch --> Track[Tracking Agent]
    Orch --> Cancel[Cancellation Agent]
    Orch --> Product[Product Agent]
    Track --> OrderAPI
    Cancel --> OrderAPI
    Product --> KB[Knowledge Base]
    Memory --> Redis
    API --> Redis
  ```
- [ ] Design decisions section:
  - Why Redis for state
  - Why LLM routing vs keyword matching
  - Why vanilla JS for UI
- [ ] Setup instructions:
  - Prerequisites (Docker, API key)
  - Environment variables
  - `docker-compose up` command
  - Verify with health check
- [ ] API documentation:
  - All endpoints with examples
  - Request/response schemas
- [ ] UI screenshots:
  - Chat interface
  - Trace timeline
  - Stats dashboard
  - Test runner
- [ ] How to extend:
  - Adding a new agent (step by step)
  - Adding a new tool
  - Modifying routing logic
- [ ] Production considerations section

#### API Documentation
- [ ] OpenAPI/Swagger spec
- [ ] Serve Swagger UI at `/docs`
- [ ] Example requests with curl

#### Docker Polish
- [ ] Multi-stage Dockerfile (smaller image)
- [ ] Non-root user in container
- [ ] Health checks in docker-compose
- [ ] Production vs development configs

#### Code Quality
- [ ] Type hints on all functions
- [ ] Docstrings on public classes/methods
- [ ] Remove debug code and TODOs
- [ ] Consistent error handling throughout
- [ ] Run linter, fix issues

#### Demo Preparation
- [ ] Seed sample data (orders, FAQs)
- [ ] Demo script with interesting scenarios:
  1. Happy path order tracking
  2. Cancellation success
  3. Cancellation policy violation
  4. Multi-turn context
  5. Fallback handling
- [ ] curl command examples in README
- [ ] Record GIF/video of demo (optional)

### Acceptance Criteria
- [ ] Fresh clone + `docker-compose up` works first try
- [ ] README explains all design decisions
- [ ] All endpoints documented with examples
- [ ] Screenshots show all UI features
- [ ] Code passes linter with no errors
- [ ] Demo script runs successfully
- [ ] Another engineer could add a new agent following docs

---

## Milestone Summary

| # | Milestone | Key Deliverable | Dependencies |
|---|-----------|-----------------|--------------|
| 1 | Foundation | `docker-compose up` works | None |
| 2 | First Agent | Tracking agent E2E | M1 |
| 3 | Orchestrator | LLM routing to all agents | M2 |
| 4 | Memory Agent | LLM-enhanced context analysis, entity tracking, sentiment | M3 |
| 5 | Chat UI | Browser chat works | M2 |
| 6 | Tracing UI | Trace visualization | M5 |
| 7 | Testing UI | Test runner works | M6 |
| 8 | Polish | Submission ready | All |

## Critical Path

```
M1 → M2 → M3 → M4 → M8
           ↓
          M5 → M6 → M7 → M8
```

M5 (Chat UI) can start after M2 is complete, allowing some parallelization.

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM structured output issues | Tackle in M2, iterate before adding complexity |
| Memory Agent complexity | Dedicated milestone (M4) with clear schema definitions |
| Sentiment detection accuracy | Use simple heuristics + LLM, don't over-engineer |
| Time constraints | M7 (Testing UI) is descope-able; core value is M1-M6 |
| UI complexity | Vanilla JS keeps it simple, no build issues |

## Differentiators

The **Memory Agent** is a key differentiator for this submission:

| Feature | Why It Stands Out |
|---------|------------------|
| LLM-enhanced analysis | Goes beyond regex extraction to true understanding |
| Sentiment tracking | Shows awareness of customer experience |
| Urgency detection | Demonstrates production thinking (escalation paths) |
| Context summaries | Each agent gets tailored, relevant context |
| Reference resolution | Handles natural conversation flow gracefully |

This positions the system as more than a routing layer — it's an intelligent conversation manager.
