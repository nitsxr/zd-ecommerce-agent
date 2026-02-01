"""FastAPI application entry point."""

import time
from pathlib import Path

from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agents import (
    OrderTrackingAgent,
    OrderCancellationAgent,
    ProductInfoAgent,
    MemoryAgent,
    AgentError,
)
from memory.redis_store import RedisSessionStore
from observability.logger import setup_logging, get_logger
from observability.middleware import CorrelationIdMiddleware
from observability.context import session_id_var
from observability.tracer import Tracer
from observability.stats import StatsCollector
from orchestrator import Orchestrator, LLMClient
from schemas.api import ChatRequest, ChatResponse, HealthResponse, ErrorResponse
from schemas.session import SessionState
from schemas.tests import TestScenario
from src.config import settings
from testing.store import TestScenarioStore
from testing.runner import run_test, run_all_tests

# Setup logging
setup_logging(settings.log_level)
logger = get_logger(__name__)

# Initialize services
session_store = RedisSessionStore(
    redis_url=settings.redis_url,
    default_ttl=settings.session_ttl_seconds,
)

tracer = Tracer(redis_url=settings.redis_url)
stats_collector = StatsCollector(redis_url=settings.redis_url)

# Initialize LLM client
llm_client = LLMClient(
    api_key=settings.openai_api_key,
    model=settings.openai_model,
)

# Initialize agents
tracking_agent = OrderTrackingAgent()
cancellation_agent = OrderCancellationAgent()
product_agent = ProductInfoAgent()
memory_agent = MemoryAgent(llm_client=llm_client)

# Initialize orchestrator and register agents
orchestrator = Orchestrator(llm_client=llm_client)
orchestrator.register_agent("order_tracking", tracking_agent)
orchestrator.register_agent("order_cancellation", cancellation_agent)
orchestrator.register_agent("product_info", product_agent)

# Test scenario store (loads golden tests on init)
test_store = TestScenarioStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Application starting", env=settings.app_env)
    yield
    logger.info("Application shutting down")
    await session_store.close()
    await tracer.close()
    await stats_collector.close()


# Create FastAPI app
app = FastAPI(
    title="E-commerce Assistant API",
    description="Multi-agent customer service system",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve UI
UI_DIR = Path(__file__).resolve().parent.parent / "ui"
if UI_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")

    @app.get("/", include_in_schema=False)
    def serve_ui():
        """Serve the chat UI at root."""
        index_path = UI_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="UI not found")
        return FileResponse(index_path)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    redis_healthy = await session_store.health_check()

    return HealthResponse(
        status="healthy" if redis_healthy else "degraded",
        redis="connected" if redis_healthy else "disconnected",
        version="1.0.0",
    )


@app.post("/chat", response_model=ChatResponse, responses={500: {"model": ErrorResponse}})
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message.

    Pipeline:
    1. Memory Agent analyzes context, resolves references, detects sentiment
    2. Orchestrator routes to appropriate agent using memory analysis
    3. Specialized agent processes the request

    Sessions are maintained via session_id for multi-turn conversations.
    """
    start_time = time.perf_counter()
    logger.info("Chat request received", session_id=request.session_id)
    session_id_var.set(request.session_id)

    tokens_at_start = getattr(llm_client, "total_prompt_tokens", 0) + getattr(
        llm_client, "total_completion_tokens", 0
    )
    try:
        # Record request received
        await tracer.record(
            session_id=request.session_id,
            event_type="request_received",
            action=f"User message: {request.message[:100]}...",
            metadata={"message_length": len(request.message)},
        )

        # Get or create session
        session = await session_store.get_session(request.session_id)
        if session is None:
            logger.info("Creating new session", session_id=request.session_id)
            session = SessionState(session_id=request.session_id)
            await stats_collector.record_session_created()

        # Add user message to history
        session.add_user_message(request.message)

        # === MEMORY AGENT ANALYSIS ===
        memory_start = time.perf_counter()
        memory_analysis = await memory_agent.analyze(session, request.message)
        memory_duration_ms = int((time.perf_counter() - memory_start) * 1000)

        # Record memory analysis
        await tracer.record(
            session_id=request.session_id,
            event_type="memory_analysis",
            action=f"Context: {memory_analysis.context_summary[:100]}",
            agent="MemoryAgent",
            duration_ms=memory_duration_ms,
            metadata={
                "sentiment": memory_analysis.sentiment.label,
                "sentiment_score": memory_analysis.sentiment.score,
                "urgency": memory_analysis.urgency,
                "references_resolved": [
                    {"ref": r.reference, "to": r.resolved_to}
                    for r in memory_analysis.references_resolved
                ],
                "is_correction": memory_analysis.is_correction,
                "failure_count": memory_analysis.failure_count,
            },
        )

        logger.info(
            "Memory analysis complete",
            session_id=request.session_id,
            sentiment=memory_analysis.sentiment.label,
            urgency=memory_analysis.urgency,
            references=len(memory_analysis.references_resolved),
        )

        # Resolve references in message for downstream processing
        resolved_message = memory_agent.get_resolved_message(
            request.message, memory_analysis, session
        )

        # Update session with extracted entities from memory analysis
        for entity in memory_analysis.extracted_entities.order_ids:
            if entity.value not in session.extracted_entities.order_ids:
                session.extracted_entities.order_ids.insert(0, entity.value)

        for entity in memory_analysis.extracted_entities.products:
            if entity.value not in session.extracted_entities.products:
                session.extracted_entities.products.insert(0, entity.value)

        # === ORCHESTRATOR ROUTING ===
        orchestrator_start = time.perf_counter()

        try:
            # Pass memory context to orchestrator via metadata
            agent_response = await orchestrator.process(
                session,
                resolved_message,
                memory_context=memory_analysis.suggested_context_for_agent,
            )
        except AgentError as e:
            logger.error("Agent error", agent=e.agent, error=e.message)
            agent_response = orchestrator._create_error_response(
                "I'm sorry, I encountered an error processing your request. Please try again."
            )

        orchestrator_duration_ms = int((time.perf_counter() - orchestrator_start) * 1000)

        # Record routing decision
        await tracer.record(
            session_id=request.session_id,
            event_type="routing_decision",
            action=f"Routed: {agent_response.handover or 'direct response'}",
            agent="OrchestratorAgent",
            duration_ms=orchestrator_duration_ms,
            tokens_used=llm_client.total_completion_tokens,
            metadata={
                "handover": agent_response.handover,
                "confidence": agent_response.confidence,
                "memory_urgency": memory_analysis.urgency,
                "memory_sentiment": memory_analysis.sentiment.label,
            },
        )

        # Record tool calls
        for tool_call in agent_response.tool_calls:
            await tracer.record(
                session_id=request.session_id,
                event_type="tool_called",
                action=f"Called {tool_call.tool}",
                agent=agent_response.agent,
                duration_ms=tool_call.duration_ms,
                metadata={
                    "tool": tool_call.tool,
                    "success": tool_call.success,
                    "input": tool_call.input,
                },
            )

        # Add assistant response to history
        session.add_assistant_message(agent_response.response, agent=agent_response.agent)

        # Save session
        await session_store.save_session(session)

        # Calculate total duration
        total_duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Record response sent
        await tracer.record(
            session_id=request.session_id,
            event_type="response_sent",
            action="Response generated",
            agent=agent_response.agent,
            duration_ms=total_duration_ms,
            metadata={
                "response_length": len(agent_response.response),
                "handover": agent_response.handover,
                "pipeline": f"MemoryAgent({memory_duration_ms}ms) → Orchestrator({orchestrator_duration_ms}ms)",
            },
        )

        logger.info(
            "Chat response generated",
            session_id=request.session_id,
            agent=agent_response.agent,
            handover=agent_response.handover,
            duration_ms=total_duration_ms,
            memory_ms=memory_duration_ms,
            orchestrator_ms=orchestrator_duration_ms,
        )

        # Record stats
        tokens_used = (
            getattr(llm_client, "total_prompt_tokens", 0)
            + getattr(llm_client, "total_completion_tokens", 0)
            - tokens_at_start
        )
        await stats_collector.record_request(
            duration_ms=total_duration_ms,
            success=True,
            agent=agent_response.agent,
            tokens_used=tokens_used,
        )

        # Include memory analysis in response metadata
        response_metadata = agent_response.metadata or {}
        response_metadata["memory"] = {
            "sentiment": memory_analysis.sentiment.label,
            "urgency": memory_analysis.urgency,
            "references_resolved": len(memory_analysis.references_resolved),
        }

        return ChatResponse(
            session_id=request.session_id,
            response=agent_response.response,
            agent=agent_response.agent,
            tool_calls=agent_response.tool_calls,
            handover=f"MemoryAgent → {agent_response.handover}" if agent_response.handover else "MemoryAgent → OrchestratorAgent",
            confidence=agent_response.confidence,
            metadata=response_metadata,
        )

    except Exception as e:
        logger.exception("Chat processing failed", session_id=request.session_id, error=str(e))

        # Record error and stats
        await tracer.record(
            session_id=request.session_id,
            event_type="error",
            action=f"Error: {str(e)}",
            metadata={"error_type": type(e).__name__},
        )
        await stats_collector.record_request(
            duration_ms=int((time.perf_counter() - start_time) * 1000),
            success=False,
            agent=None,
            tokens_used=0,
        )

        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions")
async def list_sessions(limit: int = 100):
    """List recent sessions with summary."""
    summaries = await session_store.list_sessions(limit=limit)
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "message_count": s.message_count,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in summaries
        ],
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details and full trace."""
    session = await session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    events = await tracer.get_trace(session_id)
    return {
        "session": session.model_dump(),
        "trace": [e.model_dump() for e in events],
    }


@app.get("/sessions/{session_id}/trace")
async def get_session_trace(session_id: str):
    """Get trace events for a session."""
    events = await tracer.get_trace(session_id)
    return {
        "session_id": session_id,
        "events": [e.model_dump() for e in events],
    }


@app.get("/sessions/{session_id}/trace/summary")
async def get_session_trace_summary(session_id: str):
    """Get trace summary for a session."""
    return await tracer.get_trace_summary(session_id)


@app.get("/stats")
async def get_stats():
    """Get aggregate statistics for the stats dashboard."""
    return await stats_collector.get_stats()


# --- Test scenarios ---


@app.get("/tests")
async def list_tests():
    """List all test scenarios."""
    scenarios = test_store.list_all()
    return {"tests": [s.model_dump() for s in scenarios]}


@app.get("/tests/{test_id}")
async def get_test(test_id: str):
    """Get a test scenario by ID."""
    scenario = test_store.get(test_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Test not found")
    return scenario.model_dump()


@app.post("/tests")
async def create_test(scenario: TestScenario):
    """Create or overwrite a test scenario."""
    test_store.put(scenario)
    return scenario.model_dump()


@app.put("/tests/{test_id}")
async def update_test(test_id: str, scenario: TestScenario):
    """Update a test scenario (id in path must match body)."""
    if scenario.id != test_id:
        raise HTTPException(status_code=400, detail="ID in path does not match body")
    test_store.put(scenario)
    return scenario.model_dump()


@app.delete("/tests/{test_id}")
async def delete_test(test_id: str):
    """Delete a test scenario."""
    if not test_store.delete(test_id):
        raise HTTPException(status_code=404, detail="Test not found")
    return {"deleted": test_id}


@app.post("/tests/{test_id}/run")
async def run_single_test(test_id: str):
    """Run a single test scenario."""
    scenario = test_store.get(test_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Test not found")
    result = await run_test(scenario, app)
    return result.model_dump()


class RunAllRequest(BaseModel):
    """Optional body for POST /tests/run-all."""

    test_ids: list[str] | None = Field(default=None, description="If set, run only these tests")


@app.post("/tests/run-all")
async def run_all_tests_endpoint(body: RunAllRequest | None = None):
    """Run all tests or a subset by ID. Body: optional {"test_ids": ["id1", "id2"]}."""
    test_ids = body.test_ids if body else None
    results = await run_all_tests(test_store, app, test_ids=test_ids)
    return {"results": [r.model_dump() for r in results]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
