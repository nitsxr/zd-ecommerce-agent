"""Base agent interface."""

import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable

from pydantic import ValidationError

from observability.logger import get_logger
from schemas.agent import AgentResponse, ToolCall
from schemas.session import SessionState

logger = get_logger(__name__)


class AgentError(Exception):
    """Base exception for agent errors."""

    def __init__(self, message: str, agent: str, recoverable: bool = True):
        self.message = message
        self.agent = agent
        self.recoverable = recoverable
        super().__init__(message)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    name: str = "BaseAgent"

    @abstractmethod
    async def process(self, session: SessionState, message: str) -> AgentResponse:
        """
        Process a user message and return a response.

        Args:
            session: Current session state with conversation history
            message: The user's message to process

        Returns:
            AgentResponse with the response and metadata
        """
        ...

    def _create_response(
        self,
        response: str,
        tool_calls: list[ToolCall] | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Helper to create a standardized agent response."""
        return AgentResponse(
            response=response,
            agent=self.name,
            tool_calls=tool_calls or [],
            handover=None,
            confidence=confidence,
            metadata=metadata or {},
        )

    def _create_error_response(self, error_message: str) -> AgentResponse:
        """Helper to create an error response."""
        return AgentResponse(
            response=error_message,
            agent=self.name,
            tool_calls=[],
            handover=None,
            confidence=None,
            metadata={"error": True},
        )


def validate_response(func: Callable) -> Callable:
    """Decorator to validate agent responses against schema."""

    @wraps(func)
    async def wrapper(self: BaseAgent, *args, **kwargs) -> AgentResponse:
        start_time = time.perf_counter()

        try:
            response = await func(self, *args, **kwargs)

            # Validate response schema
            if not isinstance(response, AgentResponse):
                raise AgentError(
                    f"Agent {self.name} returned invalid response type: {type(response)}",
                    agent=self.name,
                )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "Agent processing complete",
                agent=self.name,
                duration_ms=duration_ms,
            )

            return response

        except ValidationError as e:
            logger.error("Agent response validation failed", agent=self.name, error=str(e))
            raise AgentError(f"Response validation failed: {e}", agent=self.name)

        except AgentError:
            raise

        except Exception as e:
            logger.exception("Agent processing failed", agent=self.name, error=str(e))
            raise AgentError(f"Processing failed: {e}", agent=self.name)

    return wrapper
