"""
Knowledge base for product/FAQ: JSON Q&A with string search.
No RAG/embeddings for M5; can be upgraded later.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Default Q&A pairs (in-code fallback; can override with file)
_DEFAULT_QA: list[dict[str, str]] = [
    {"q": "Can I return my Bluetooth headphones?", "a": "Yes. You can return Bluetooth headphones within 30 days of delivery if they are unused and in original packaging. Start a return from your order page."},
    {"q": "return policy", "a": "Returns are accepted within 30 days of delivery. Items must be unused and in original packaging. Refunds are processed within 5–7 business days."},
    {"q": "warranty", "a": "Most electronics come with a 1-year manufacturer warranty. Extended warranty options are available at checkout."},
    {"q": "Bluetooth headphones", "a": "We offer several Bluetooth headphone models. All support multipoint pairing and have at least 20 hours of battery life. Check the product page for specs."},
    {"q": "shipping time", "a": "Standard shipping is 3–5 business days. Express shipping is 1–2 business days. Delivery estimates are shown at checkout."},
    {"q": "cancel order", "a": "You can cancel an order within 24 hours of placing it. After that, you may need to request a return once the order ships. Use your order ID (e.g. ORD-1234) when contacting support."},
]

_qa_cache: list[dict[str, str]] | None = None


def _load_qa() -> list[dict[str, str]]:
    """Load Q&A from file if present, else default in-code list."""
    global _qa_cache
    if _qa_cache is not None:
        return _qa_cache
    base = Path(__file__).resolve().parent
    for name in ("knowledge_base.json", "knowledge_qa.json"):
        path = base / name
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    _qa_cache = data
                elif isinstance(data, dict) and "qa" in data:
                    _qa_cache = data["qa"]
                else:
                    _qa_cache = _DEFAULT_QA
            except (json.JSONDecodeError, OSError):
                _qa_cache = _DEFAULT_QA
            return _qa_cache
    _qa_cache = _DEFAULT_QA
    return _qa_cache


def search(query: str) -> dict[str, Any]:
    """
    Simple string search: find best-matching Q&A by keyword overlap.
    Returns { "answer": str, "matched_question": str } or { "answer": str, "matched_question": null } if no match.
    """
    query_lower = (query or "").strip().lower()
    if not query_lower:
        return {"answer": "Please ask a specific question about our products or policies.", "matched_question": None}
    qa = _load_qa()
    best_score = 0
    best_a = "I couldn't find a specific answer for that. You can ask about returns, warranty, shipping, or product details. If you need to cancel or track an order, use your order ID (e.g. ORD-1234)."
    best_q: str | None = None
    query_words = set(query_lower.split())
    for pair in qa:
        q = (pair.get("q") or "").lower()
        a = pair.get("a") or ""
        q_words = set(q.split())
        overlap = len(query_words & q_words)
        if overlap > best_score or (overlap > 0 and overlap == best_score and len(q) < len(best_q or "")):
            best_score = overlap
            best_a = a
            best_q = pair.get("q")
    return {"answer": best_a, "matched_question": best_q}
