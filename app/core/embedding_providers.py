"""Embedding Provider Abstraction for multiple backends (OpenAI, Ollama)."""

from __future__ import annotations

import asyncio
import logging
import os
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Retry settings for rate limits
MAX_RETRIES = 5
INITIAL_DELAY = 2.0  # seconds
MAX_DELAY = 60.0  # seconds


def serialize_f32(vector: list[float]) -> bytes:
    """Serialize a list of floats into bytes for sqlite-vec."""
    return struct.pack(f"{len(vector)}f", *vector)


@dataclass(frozen=True)
class ModelInfo:
    """Information about an embedding model."""

    model_id: str
    dimensions: int
    cost_per_1m_tokens: float  # USD, 0 for local models
    max_tokens: int  # Max input tokens
    description: str


# Available Models (December 2025)
OPENAI_MODELS: dict[str, ModelInfo] = {
    "text-embedding-3-small": ModelInfo(
        model_id="text-embedding-3-small",
        dimensions=1536,
        cost_per_1m_tokens=0.02,
        max_tokens=8191,
        description="Beste Balance aus Qualitaet und Kosten. Empfohlen fuer die meisten Anwendungen.",
    ),
    "text-embedding-3-large": ModelInfo(
        model_id="text-embedding-3-large",
        dimensions=3072,
        cost_per_1m_tokens=0.13,
        max_tokens=8191,
        description="Hoechste Praezision. Fuer komplexe Themen und maximale Suchqualitaet.",
    ),
}

OLLAMA_MODELS: dict[str, ModelInfo] = {
    "nomic-embed-text": ModelInfo(
        model_id="nomic-embed-text",
        dimensions=768,
        cost_per_1m_tokens=0.0,
        max_tokens=8192,
        description="Gute Qualitaet, kompakt (275MB). Laeuft lokal, kostenlos.",
    ),
    "mxbai-embed-large": ModelInfo(
        model_id="mxbai-embed-large",
        dimensions=1024,
        cost_per_1m_tokens=0.0,
        max_tokens=512,
        description="Sehr gute Qualitaet, groesser (~670MB). Lokal und kostenlos.",
    ),
}


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g., 'OpenAI', 'Ollama')."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """The model identifier being used."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding vector dimensions."""
        ...

    @property
    @abstractmethod
    def cost_per_1m_tokens(self) -> float:
        """Cost in USD per 1 million tokens. 0 for local models."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors in the same order as input.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        ...

    @abstractmethod
    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        ...

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """Check if the provider is available and configured correctly.

        Returns:
            HealthCheckResult with status and details.
        """
        ...

    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost in USD for a given number of tokens."""
        return (token_count / 1_000_000) * self.cost_per_1m_tokens


@dataclass
class HealthCheckResult:
    """Result of a provider health check."""

    healthy: bool
    provider: str
    model: str
    message: str
    latency_ms: int | None = None
    details: dict[str, Any] | None = None


class EmbeddingError(Exception):
    """Error during embedding generation."""

    def __init__(self, message: str, provider: str, retriable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable


class OpenAIProvider(EmbeddingProvider):
    """OpenAI embedding provider using the API."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None):
        """Initialize OpenAI provider.

        Args:
            model: Model ID (text-embedding-3-small or text-embedding-3-large).
            api_key: Optional API key. Falls back to OPENAI_API_KEY env var.
        """
        if model not in OPENAI_MODELS:
            raise ValueError(f"Unknown OpenAI model: {model}. Available: {list(OPENAI_MODELS.keys())}")

        self._model = model
        self._model_info = OPENAI_MODELS[model]
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        self._max_chars = 20000  # ~5000 tokens, safe for 8192 limit with variable tokenization

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._model_info.dimensions

    @property
    def cost_per_1m_tokens(self) -> float:
        return self._model_info.cost_per_1m_tokens

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts in a single API call."""
        if not texts:
            return []

        if not self._api_key:
            raise EmbeddingError(
                "OPENAI_API_KEY nicht gesetzt. Bitte in .env konfigurieren.",
                provider=self.name,
                retriable=False,
            )

        # Truncate texts if too long
        truncated = [t[: self._max_chars] if len(t) > self._max_chars else t for t in texts]

        async with httpx.AsyncClient(timeout=60.0) as client:
            delay = INITIAL_DELAY
            last_error: Exception | None = None

            for attempt in range(MAX_RETRIES):
                try:
                    response = await client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self._model,
                            "input": truncated,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    # API returns embeddings in order, but let's be safe
                    embeddings: list[list[float] | None] = [None] * len(texts)
                    for item in data["data"]:
                        embeddings[item["index"]] = item["embedding"]

                    return embeddings  # type: ignore

                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code == 429:
                        # Check if it's rate limit or quota exceeded
                        error_body = e.response.text
                        if "quota" in error_body.lower():
                            raise EmbeddingError(
                                "OpenAI Guthaben aufgebraucht. Bitte Credits kaufen auf platform.openai.com",
                                provider=self.name,
                                retriable=False,
                            ) from e

                        # Rate limit - retry with backoff
                        logger.warning(
                            f"Rate limit hit, attempt {attempt + 1}/{MAX_RETRIES}. " f"Waiting {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, MAX_DELAY)
                    elif e.response.status_code == 401:
                        raise EmbeddingError(
                            "OpenAI API-Key ungueltig. Bitte in .env pruefen.",
                            provider=self.name,
                            retriable=False,
                        ) from e
                    else:
                        raise EmbeddingError(
                            f"OpenAI API Fehler: {e.response.status_code} - {e.response.text}",
                            provider=self.name,
                            retriable=False,
                        ) from e

            # All retries exhausted
            raise EmbeddingError(
                f"Rate limit nach {MAX_RETRIES} Versuchen nicht ueberwunden.",
                provider=self.name,
                retriable=True,
            ) from last_error

    async def embed_single(self, text: str) -> list[float]:
        """Get embedding for a single text."""
        result = await self.embed([text])
        return result[0]

    async def health_check(self) -> HealthCheckResult:
        """Check OpenAI API connectivity and authentication."""
        import time

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
            # Simple embedding request to test connectivity
            await self.embed_single("test")
            latency_ms = int((time.monotonic() - start) * 1000)

            return HealthCheckResult(
                healthy=True,
                provider=self.name,
                model=self._model,
                message="Verbunden",
                latency_ms=latency_ms,
                details={"dimensions": self.dimensions},
            )

        except EmbeddingError as e:
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


class OllamaProvider(EmbeddingProvider):
    """Ollama embedding provider for local models."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str | None = None,
    ):
        """Initialize Ollama provider.

        Args:
            model: Model ID (nomic-embed-text or mxbai-embed-large).
            base_url: Ollama server URL. Falls back to OLLAMA_BASE_URL env var or localhost.
        """
        if model not in OLLAMA_MODELS:
            raise ValueError(f"Unknown Ollama model: {model}. Available: {list(OLLAMA_MODELS.keys())}")

        self._model = model
        self._model_info = OLLAMA_MODELS[model]
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")).rstrip("/")

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._model_info.dimensions

    @property
    def cost_per_1m_tokens(self) -> float:
        return 0.0  # Local = free

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts.

        Note: Ollama doesn't support batch embedding, so we call one by one.
        This is still fast because it's local.
        """
        if not texts:
            return []

        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for text in texts:
                try:
                    response = await client.post(
                        f"{self._base_url}/api/embeddings",
                        json={
                            "model": self._model,
                            "prompt": text,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    results.append(data["embedding"])

                except httpx.ConnectError as e:
                    raise EmbeddingError(
                        f"Ollama nicht erreichbar unter {self._base_url}. Laeuft Ollama?",
                        provider=self.name,
                        retriable=True,
                    ) from e

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        raise EmbeddingError(
                            f"Modell '{self._model}' nicht gefunden. "
                            f"Bitte 'ollama pull {self._model}' ausfuehren.",
                            provider=self.name,
                            retriable=False,
                        ) from e
                    raise EmbeddingError(
                        f"Ollama Fehler: {e.response.status_code} - {e.response.text}",
                        provider=self.name,
                        retriable=False,
                    ) from e

        return results

    async def embed_single(self, text: str) -> list[float]:
        """Get embedding for a single text."""
        result = await self.embed([text])
        return result[0]

    async def health_check(self) -> HealthCheckResult:
        """Check Ollama connectivity and model availability."""
        import time

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # First check if Ollama is running
                try:
                    version_response = await client.get(f"{self._base_url}/api/version")
                    version_response.raise_for_status()
                    version = version_response.json().get("version", "unknown")
                except httpx.ConnectError:
                    return HealthCheckResult(
                        healthy=False,
                        provider=self.name,
                        model=self._model,
                        message="Ollama nicht erreichbar",
                        details={
                            "url": self._base_url,
                            "hint": "Starte Ollama mit 'ollama serve' oder pruefe ob es laeuft",
                        },
                    )

                # Check if the model is available
                try:
                    tags_response = await client.get(f"{self._base_url}/api/tags")
                    tags_response.raise_for_status()
                    models = [m["name"].split(":")[0] for m in tags_response.json().get("models", [])]

                    if self._model not in models:
                        return HealthCheckResult(
                            healthy=False,
                            provider=self.name,
                            model=self._model,
                            message=f"Modell '{self._model}' nicht installiert",
                            details={
                                "available_models": models,
                                "hint": f"Fuehre 'ollama pull {self._model}' aus",
                            },
                        )
                except Exception:
                    pass  # Model check is optional

                # Test actual embedding
                await self.embed_single("test")
                latency_ms = int((time.monotonic() - start) * 1000)

                return HealthCheckResult(
                    healthy=True,
                    provider=self.name,
                    model=self._model,
                    message=f"Verbunden (v{version})",
                    latency_ms=latency_ms,
                    details={
                        "dimensions": self.dimensions,
                        "version": version,
                        "url": self._base_url,
                    },
                )

        except EmbeddingError as e:
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
                message=f"Unbekannter Fehler: {e}",
            )


def get_provider(
    provider_name: str = "openai",
    model: str | None = None,
) -> EmbeddingProvider:
    """Factory function to get an embedding provider.

    Args:
        provider_name: 'openai' or 'ollama'
        model: Optional model ID. Uses default if not specified.

    Returns:
        Configured EmbeddingProvider instance.

    Raises:
        ValueError: If provider or model is unknown.
    """
    provider_name = provider_name.lower()

    if provider_name == "openai":
        model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAIProvider(model=model)

    elif provider_name == "ollama":
        model = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        return OllamaProvider(model=model)

    else:
        raise ValueError(f"Unknown provider: {provider_name}. Available: openai, ollama")


def get_all_models() -> dict[str, dict[str, ModelInfo]]:
    """Get all available models grouped by provider."""
    return {
        "openai": OPENAI_MODELS,
        "ollama": OLLAMA_MODELS,
    }
