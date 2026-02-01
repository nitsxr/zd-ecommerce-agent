"""
FastAPI app exposing POST /chat.
Orchestrator (M2) handles intent detection, routing, slot validation, and stub agent invocation.
"""
from fastapi import FastAPI
from pydantic import BaseModel

from memory.session_store import default_store
from orchestrator.decision_engine import run_turn

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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Accept user message and session_id; return system response.
    Orchestrator: intent -> route -> validate slots -> clarify or invoke agent -> persist state.
    """
    result = run_turn(
        session_id=request.session_id,
        message=request.message,
        store=default_store,
    )
    return ChatResponse(
        response=result.response,
        agent=result.agent,
        tool_calls=[ToolCallPayload(tool=tc["tool"], input=tc["input"], result=tc.get("result")) for tc in result.tool_calls],
        handover=result.handover,
    )
