"""LLM client wrapper with retry logic and structured output support."""

import asyncio
import time
from typing import Any, Type, TypeVar

from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
from pydantic import BaseModel

from observability.logger import get_logger
from src.config import settings

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """OpenAI API client with retry logic and structured output support."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        """
        Initialize the LLM client.

        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model to use (defaults to settings)
            max_retries: Maximum number of retries on failure
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.max_retries = max_retries
        self.timeout = timeout

        self._client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=timeout,
        )

        # Token tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> tuple[str, dict[str, int]]:
        """
        Generate a completion from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (response_text, token_usage)
        """
        start_time = time.perf_counter()

        for attempt in range(self.max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Extract response
                content = response.choices[0].message.content or ""

                # Track tokens
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
                self.total_prompt_tokens += usage["prompt_tokens"]
                self.total_completion_tokens += usage["completion_tokens"]

                duration_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info(
                    "LLM completion successful",
                    model=self.model,
                    duration_ms=duration_ms,
                    tokens=usage["total_tokens"],
                )

                return content, usage

            except RateLimitError as e:
                wait_time = 2 ** attempt
                logger.warning(
                    "Rate limited, retrying",
                    attempt=attempt + 1,
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)

            except APITimeoutError as e:
                logger.warning("Request timed out, retrying", attempt=attempt + 1)
                await asyncio.sleep(1)

            except APIError as e:
                logger.error("API error", error=str(e), attempt=attempt + 1)
                if attempt == self.max_retries - 1:
                    raise

        raise Exception(f"Failed after {self.max_retries} retries")

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> tuple[T, dict[str, int]]:
        """
        Generate a structured completion using JSON mode.

        Args:
            messages: List of message dicts
            response_model: Pydantic model for response validation
            temperature: Sampling temperature (lower for structured)
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (parsed_response, token_usage)
        """
        import json

        # Add JSON instruction to system message
        json_instruction = (
            f"\n\nRespond with valid JSON matching this schema:\n"
            f"{response_model.model_json_schema()}"
        )

        # Append instruction to last message or system message
        augmented_messages = messages.copy()
        if augmented_messages and augmented_messages[0]["role"] == "system":
            augmented_messages[0] = {
                "role": "system",
                "content": augmented_messages[0]["content"] + json_instruction,
            }
        else:
            augmented_messages.insert(0, {
                "role": "system",
                "content": f"You are a helpful assistant. {json_instruction}",
            })

        start_time = time.perf_counter()

        for attempt in range(self.max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=augmented_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content or "{}"

                # Parse and validate JSON
                try:
                    data = json.loads(content)
                    result = response_model.model_validate(data)
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(
                        "Failed to parse structured response, retrying",
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt < self.max_retries - 1:
                        continue
                    raise

                # Track tokens
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
                self.total_prompt_tokens += usage["prompt_tokens"]
                self.total_completion_tokens += usage["completion_tokens"]

                duration_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info(
                    "Structured LLM completion successful",
                    model=self.model,
                    duration_ms=duration_ms,
                    tokens=usage["total_tokens"],
                )

                return result, usage

            except RateLimitError:
                wait_time = 2 ** attempt
                logger.warning("Rate limited, retrying", attempt=attempt + 1, wait_seconds=wait_time)
                await asyncio.sleep(wait_time)

            except APITimeoutError:
                logger.warning("Request timed out, retrying", attempt=attempt + 1)
                await asyncio.sleep(1)

            except APIError as e:
                logger.error("API error", error=str(e), attempt=attempt + 1)
                if attempt == self.max_retries - 1:
                    raise

        raise Exception(f"Failed after {self.max_retries} retries")

    def get_token_usage(self) -> dict[str, int]:
        """Get cumulative token usage."""
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }
