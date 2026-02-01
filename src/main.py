"""
Minimal FastAPI app exposing POST /chat.
Stub implementation: returns 501 and reads session_id + message.
Orchestrator and agents will be wired in later milestones.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Multi-Agent E-commerce Assistant",
    description="Chat API for order cancellation, tracking, and product information.",
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ToolCallPayload(BaseModel):
    tool: str
    input: dict
    result: dict | None = None


class ChatResponse(BaseModel):
    response: str
    agent: str
    tool_calls: list[ToolCallPayload] = []
    handover: str


@app.post("/chat")
def chat(request: ChatRequest):
    """
    Accept user message and session_id; return system response.
    Stub: returns 501 Not Implemented until orchestrator is wired.
    """
    # Stub: read session_id and message, return 501 with challenge-shaped body
    payload = {
        "response": "Chat endpoint is not yet implemented. Orchestrator will be wired in a later milestone.",
        "agent": "OrchestratorAgent",
        "tool_calls": [],
        "handover": "OrchestratorAgent",
    }
    return JSONResponse(status_code=501, content=payload)
