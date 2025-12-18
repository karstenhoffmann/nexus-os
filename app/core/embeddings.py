"""Embedding functions using OpenAI API."""

from __future__ import annotations

import asyncio
import logging
import os
import struct

import httpx

logger = logging.getLogger(__name__)

# Retry settings for rate limits
MAX_RETRIES = 5
INITIAL_DELAY = 2.0  # seconds
MAX_DELAY = 60.0  # seconds


def serialize_f32(vector: list[float]) -> bytes:
    """Serialize a list of floats into bytes for sqlite-vec."""
    return struct.pack(f"{len(vector)}f", *vector)


async def get_embedding(text: str) -> list[float]:
    """Get embedding for a single text using OpenAI API.

    Uses text-embedding-3-small model (1536 dimensions).

    Args:
        text: The text to embed. Will be truncated if too long.

    Returns:
        List of 1536 floats representing the embedding.

    Raises:
        ValueError: If OPENAI_API_KEY is not set.
        httpx.HTTPStatusError: If API call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Truncate text if too long (max ~8000 tokens, rough estimate)
    max_chars = 30000
    if len(text) > max_chars:
        text = text[:max_chars]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": text,
            },
        )
        response.raise_for_status()
        data = response.json()

    return data["data"][0]["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts in a single API call.

    More efficient than calling get_embedding() multiple times.
    OpenAI supports up to 2048 texts per batch.

    Args:
        texts: List of texts to embed. Each will be truncated if too long.

    Returns:
        List of embeddings in the same order as input texts.

    Raises:
        ValueError: If OPENAI_API_KEY is not set or texts is empty.
        httpx.HTTPStatusError: If API call fails.
    """
    if not texts:
        raise ValueError("texts list cannot be empty")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Truncate texts if too long
    max_chars = 30000
    truncated = [t[:max_chars] if len(t) > max_chars else t for t in texts]

    async with httpx.AsyncClient(timeout=60.0) as client:
        delay = INITIAL_DELAY
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "input": truncated,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # API returns embeddings in order, but let's be safe
                embeddings = [None] * len(texts)
                for item in data["data"]:
                    embeddings[item["index"]] = item["embedding"]

                return embeddings

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # Rate limit - retry with backoff
                    logger.warning(
                        f"Rate limit hit, attempt {attempt + 1}/{MAX_RETRIES}. "
                        f"Waiting {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, MAX_DELAY)
                else:
                    # Other HTTP error - don't retry
                    raise

        # All retries exhausted
        raise last_error
