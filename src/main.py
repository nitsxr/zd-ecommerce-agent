"""
FastAPI app: POST /chat, read-only session APIs, traces API, and UI static files.
OpenAPI/Swagger at /docs, ReDoc at /redoc. Chat UI at /ui.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from memory.conversation_store import get_session_summary, get_turns
from memory.session_store import default_store
from observability.tracer import emit_trace, get_traces_for_session
from orchestrator.decision_engine import run_turn

app = FastAPI(
    title="Multi-Agent E-commerce Assistant",
    description=(
        "Chat API for order cancellation, tracking, product info. "
        "Read-only session APIs for debug."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Chat", "description": "Send messages and get responses"},
        {"name": "Sessions", "description": "Read-only session state and traces"},
    ],
)


class ChatRequest(BaseModel):
    """Request body for POST /chat."""
    session_id: str = Field(..., description="Session id for context")
    message: str = Field(..., description="User message")


class ToolCallPayload(BaseModel):
    tool: str
    input: dict
    result: dict | None = None


class ChatResponse(BaseModel):
    """Response body for POST /chat (challenge spec)."""
    response: str
    agent: str
    tool_calls: list[ToolCallPayload] = []
    handover: str


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a user message and get the assistant response.
    session_id maintains context; orchestrator routes to the right agent.
    """
    result = run_turn(
        session_id=request.session_id,
        message=request.message,
        store=default_store,
    )
    emit_trace(result.trace)
    tool_calls = [
        ToolCallPayload(tool=tc["tool"], input=tc["input"], result=tc.get("result"))
        for tc in result.tool_calls
    ]
    return ChatResponse(
        response=result.response,
        agent=result.agent,
        tool_calls=tool_calls,
        handover=result.handover,
    )


@app.get("/sessions/{session_id}", tags=["Sessions"])
def get_session(session_id: str):
    """
    Get session summary: turn_count, extracted_entities, slot_state. Read-only.
    Returns 404 if session does not exist.
    """
    summary = get_session_summary(session_id, default_store)
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary


@app.get("/sessions/{session_id}/turns", tags=["Sessions"])
def get_session_turns(session_id: str):
    """
    Get conversation turns for a session. Read-only.
    Returns 404 if session does not exist.
    """
    summary = get_session_summary(session_id, default_store)
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")
    turns = get_turns(session_id, default_store)
    return {"session_id": session_id, "turns": turns}


@app.get("/sessions/{session_id}/traces", tags=["Sessions"])
def get_session_traces(session_id: str):
    """
    Get trace events for a session. Read-only. Aligned by turn_index with /turns.
    Returns list of trace events (oldest first). 200 even if empty (no 404).
    """
    traces = get_traces_for_session(session_id)
    return {"session_id": session_id, "traces": traces}


# UI: serve static files from ui/ (M7)
_ui_dir = Path(__file__).resolve().parent.parent / "ui"
if _ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(_ui_dir), html=True), name="ui")

    @app.get("/")
    def root():
        return RedirectResponse(url="/ui/")
