"""LLM Provider Abstraction for Chat/Completion APIs (OpenAI GPT-4.1, etc.)."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Retry settings for rate limits
MAX_RETRIES = 5
INITIAL_DELAY = 2.0  # seconds
MAX_DELAY = 60.0  # seconds


@dataclass(frozen=True)
class ChatModelInfo:
    """Information about a chat/completion model."""

    model_id: str
    cost_per_1m_input: float  # USD per 1M input tokens
    cost_per_1m_output: float  # USD per 1M output tokens
    max_context: int  # Max context window tokens
    description: str


# Available Models (December 2025)
# Source: https://platform.openai.com/docs/models
OPENAI_CHAT_MODELS: dict[str, ChatModelInfo] = {
    "gpt-4.1-nano": ChatModelInfo(
        model_id="gpt-4.1-nano",
        cost_per_1m_input=0.10,
        cost_per_1m_output=0.40,
        max_context=1047576,
        description="Schnellstes und guenstigstes GPT-4.1 Modell. Ideal fuer einfache Tasks.",
    ),
    "gpt-4.1-mini": ChatModelInfo(
        model_id="gpt-4.1-mini",
        cost_per_1m_input=0.40,
        cost_per_1m_output=1.60,
        max_context=1047576,
        description="Gute Balance aus Qualitaet und Kosten. Empfohlen fuer Digest.",
    ),
    "gpt-4o-mini": ChatModelInfo(
        model_id="gpt-4o-mini",
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
        max_context=128000,
        description="Guenstige Alternative. Gute Qualitaet bei einfachen Tasks.",
    ),
    "gpt-4o": ChatModelInfo(
        model_id="gpt-4o",
        cost_per_1m_input=2.50,
        cost_per_1m_output=10.00,
        max_context=128000,
        description="Hohe Qualitaet. Fuer komplexe Analysen und beste Ergebnisse.",
    ),
}

# Default model for digest generation
DEFAULT_DIGEST_MODEL = "gpt-4.1-mini"


@dataclass
class ChatResponse:
    """Response from a chat completion."""

    content: str
    model: str
    tokens_input: int
    tokens_output: int
    finish_reason: str
    latency_ms: int


@dataclass
class HealthCheckResult:
    """Result of a provider health check."""

    healthy: bool
    provider: str
    model: str
    message: str
    latency_ms: int | None = None
    details: dict[str, Any] | None = None


class LLMError(Exception):
    """Error during LLM API call."""

    def __init__(self, message: str, provider: str, retriable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """The model identifier being used."""
        ...

    @property
    @abstractmethod
    def cost_per_1m_input(self) -> float:
        """Cost in USD per 1M input tokens."""
        ...

    @property
    @abstractmethod
    def cost_per_1m_output(self) -> float:
        """Cost in USD per 1M output tokens."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature (0-2).
            max_tokens: Max tokens to generate (None = model default).

        Returns:
            ChatResponse with content and usage info.

        Raises:
            LLMError: If the API call fails.
        """
        ...

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """Check if the provider is available and configured correctly."""
        ...

    def estimate_cost(self, tokens_input: int, tokens_output: int) -> float:
        """Estimate cost in USD for given token counts."""
        input_cost = (tokens_input / 1_000_000) * self.cost_per_1m_input
        output_cost = (tokens_output / 1_000_000) * self.cost_per_1m_output
        return input_cost + output_cost


class OpenAIChatProvider(LLMProvider):
    """OpenAI Chat/Completion provider using the API."""

    def __init__(self, model: str = DEFAULT_DIGEST_MODEL, api_key: str | None = None):
        """Initialize OpenAI provider.

        Args:
            model: Model ID (gpt-4.1-nano, gpt-4.1-mini, gpt-4o-mini, gpt-4o).
            api_key: Optional API key. Falls back to OPENAI_API_KEY env var.
        """
        if model not in OPENAI_CHAT_MODELS:
            raise ValueError(
                f"Unknown OpenAI model: {model}. Available: {list(OPENAI_CHAT_MODELS.keys())}"
            )

        self._model = model
        self._model_info = OPENAI_CHAT_MODELS[model]
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def cost_per_1m_input(self) -> float:
        return self._model_info.cost_per_1m_input

    @property
    def cost_per_1m_output(self) -> float:
        return self._model_info.cost_per_1m_output

    @property
    def max_context(self) -> int:
        return self._model_info.max_context

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """Send a chat completion request."""
        if not self._api_key:
            raise LLMError(
                "OPENAI_API_KEY nicht gesetzt. Bitte in .env konfigurieren.",
                provider=self.name,
                retriable=False,
            )

        async with httpx.AsyncClient(timeout=120.0) as client:
            delay = INITIAL_DELAY
            last_error: Exception | None = None

            for attempt in range(MAX_RETRIES):
                start_time = time.monotonic()
                try:
                    request_body: dict[str, Any] = {
                        "model": self._model,
                        "messages": messages,
                        "temperature": temperature,
                    }
                    if max_tokens:
                        request_body["max_tokens"] = max_tokens

                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json=request_body,
                    )
                    response.raise_for_status()
                    data = response.json()

                    latency_ms = int((time.monotonic() - start_time) * 1000)

                    choice = data["choices"][0]
                    usage = data["usage"]

                    return ChatResponse(
                        content=choice["message"]["content"],
                        model=data["model"],
                        tokens_input=usage["prompt_tokens"],
                        tokens_output=usage["completion_tokens"],
                        finish_reason=choice["finish_reason"],
                        latency_ms=latency_ms,
                    )

                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code == 429:
                        error_body = e.response.text
                        if "quota" in error_body.lower():
                            raise LLMError(
                                "OpenAI Guthaben aufgebraucht. Bitte Credits kaufen auf platform.openai.com",
                                provider=self.name,
                                retriable=False,
                            ) from e

                        # Rate limit - retry with backoff
                        logger.warning(
                            f"Rate limit hit, attempt {attempt + 1}/{MAX_RETRIES}. "
                            f"Waiting {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, MAX_DELAY)

                    elif e.response.status_code == 401:
                        raise LLMError(
                            "OpenAI API-Key ungueltig. Bitte in .env pruefen.",
                            provider=self.name,
                            retriable=False,
                        ) from e

                    elif e.response.status_code == 404:
                        raise LLMError(
                            f"Modell '{self._model}' nicht verfuegbar. "
                            f"Bitte anderes Modell waehlen.",
                            provider=self.name,
                            retriable=False,
                        ) from e

                    else:
                        raise LLMError(
                            f"OpenAI API Fehler: {e.response.status_code} - {e.response.text}",
                            provider=self.name,
                            retriable=False,
                        ) from e

            # All retries exhausted
            raise LLMError(
                f"Rate limit nach {MAX_RETRIES} Versuchen nicht ueberwunden.",
                provider=self.name,
                retriable=True,
            ) from last_error

    async def health_check(self) -> HealthCheckResult:
        """Check OpenAI API connectivity and authentication."""
        if not self._api_key:
            return HealthCheckResult(
                healthy=False,
                provider=self.name,
                model=self._model,
                message="API-Key nicht gesetzt",
                details={"error": "OPENAI_API_KEY environment variable not set"},
            )

        start = time.monotonic()
        try:
            # Simple completion request to test connectivity
            response = await self.chat(
                messages=[{"role": "user", "content": "Say 'OK'"}],
                temperature=0,
                max_tokens=5,
            )
            latency_ms = int((time.monotonic() - start) * 1000)

            return HealthCheckResult(
                healthy=True,
                provider=self.name,
                model=self._model,
                message="Verbunden",
                latency_ms=latency_ms,
                details={
                    "max_context": self.max_context,
                    "cost_input_1m": self.cost_per_1m_input,
                    "cost_output_1m": self.cost_per_1m_output,
                },
            )

        except LLMError as e:
            return HealthCheckResult(
                healthy=False,
                provider=self.name,
                model=self._model,
                message=str(e),
                details={"retriable": e.retriable},
            )

        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                provider=self.name,
                model=self._model,
                message=f"Verbindungsfehler: {e}",
            )


def get_chat_provider(
    provider_name: str = "openai",
    model: str | None = None,
) -> LLMProvider:
    """Factory function to get an LLM provider.

    Args:
        provider_name: 'openai' (more providers can be added later)
        model: Optional model ID. Uses default if not specified.

    Returns:
        Configured LLMProvider instance.

    Raises:
        ValueError: If provider or model is unknown.
    """
    provider_name = provider_name.lower()

    if provider_name == "openai":
        model = model or os.getenv("DIGEST_MODEL", DEFAULT_DIGEST_MODEL)
        return OpenAIChatProvider(model=model)

    else:
        raise ValueError(f"Unknown provider: {provider_name}. Available: openai")


def get_all_chat_models() -> dict[str, dict[str, ChatModelInfo]]:
    """Get all available chat models grouped by provider."""
    return {
        "openai": OPENAI_CHAT_MODELS,
    }


def estimate_digest_cost(
    chunks_count: int,
    avg_tokens_per_chunk: int = 200,
    model: str = DEFAULT_DIGEST_MODEL,
) -> dict[str, Any]:
    """Estimate cost for digest generation.

    Args:
        chunks_count: Number of chunks to analyze
        avg_tokens_per_chunk: Average tokens per chunk (default 200)
        model: Model to use for estimation

    Returns:
        Dict with estimated costs and token counts
    """
    if model not in OPENAI_CHAT_MODELS:
        model = DEFAULT_DIGEST_MODEL

    model_info = OPENAI_CHAT_MODELS[model]

    # Estimate input tokens
    # - Chunks content: chunks_count * avg_tokens_per_chunk
    # - System prompts and formatting: ~2000 tokens
    # - Multiple calls (clustering, summaries): multiply by 2
    estimated_input = (chunks_count * avg_tokens_per_chunk + 2000) * 2

    # Estimate output tokens
    # - Clustering: ~500 tokens
    # - Topic summaries (7 topics * 300 tokens): ~2100 tokens
    # - Overall summary: ~500 tokens
    # - Highlights: ~400 tokens
    estimated_output = 3500

    input_cost = (estimated_input / 1_000_000) * model_info.cost_per_1m_input
    output_cost = (estimated_output / 1_000_000) * model_info.cost_per_1m_output
    total_cost = input_cost + output_cost

    return {
        "model": model,
        "chunks_count": chunks_count,
        "estimated_input_tokens": estimated_input,
        "estimated_output_tokens": estimated_output,
        "input_cost_usd": round(input_cost, 4),
        "output_cost_usd": round(output_cost, 4),
        "total_cost_usd": round(total_cost, 4),
    }
