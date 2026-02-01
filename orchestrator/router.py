"""
Agent routing: map intent to agent name.
Orchestrator uses this to select which agent handles the turn.
"""
from typing import Literal

from .intent import Intent

AgentName = Literal[
    "OrderCancellationAgent",
    "OrderTrackingAgent",
    "ProductInfoAgent",
    "OrchestratorAgent",
]


def route(intent: Intent) -> AgentName:
    """
    Map intent to agent. For unclear, orchestrator handles (clarification or context resolution).
    """
    if intent == "cancel":
        return "OrderCancellationAgent"
    if intent == "track":
        return "OrderTrackingAgent"
    if intent == "product":
        return "ProductInfoAgent"
    return "OrchestratorAgent"
