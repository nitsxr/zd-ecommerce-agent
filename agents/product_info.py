"""
ProductInfoAgent: queries knowledge base (JSON Q&A), returns answer.
Stateless; no Redis or orchestrator logic.
"""
from __future__ import annotations

from typing import Any

from tools.knowledge_base import search


def run(query: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Look up product/FAQ answer. Query is free-form from user message.
    Returns (response_message, tool_calls).
    """
    query = (query or "").strip() or "general help"
    result = search(query)
    answer = result.get("answer", "I couldn't find specific information for that. Try asking about returns, warranty, or product details.")
    tool_call = {
        "tool": "KnowledgeBase",
        "input": {"query": query},
        "result": {"answer": answer, "matched_question": result.get("matched_question")},
    }
    return answer, [tool_call]
