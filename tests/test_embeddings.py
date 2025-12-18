"""Tests for embedding functions."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.embeddings import get_embedding, get_embeddings_batch, serialize_f32


def test_serialize_f32():
    """Test float serialization for sqlite-vec."""
    vec = [1.0, 2.0, 3.0]
    result = serialize_f32(vec)
    assert isinstance(result, bytes)
    assert len(result) == 12  # 3 floats * 4 bytes


def test_serialize_f32_1536_dimensions():
    """Test serialization with OpenAI embedding dimensions."""
    vec = [0.1] * 1536
    result = serialize_f32(vec)
    assert len(result) == 1536 * 4  # 6144 bytes


@pytest.mark.asyncio
async def test_get_embedding_no_api_key():
    """Test that missing API key raises ValueError."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await get_embedding("test text")


@pytest.mark.asyncio
async def test_get_embedding_mocked():
    """Test get_embedding with mocked API response."""
    mock_embedding = [0.1] * 1536

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": mock_embedding, "index": 0}]
    }
    mock_response.raise_for_status = MagicMock()

    async def mock_post(*args, **kwargs):
        return mock_response

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            result = await get_embedding("test text")

    assert result == mock_embedding
    assert len(result) == 1536


@pytest.mark.asyncio
async def test_get_embeddings_batch_empty():
    """Test that empty batch raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        await get_embeddings_batch([])


@pytest.mark.asyncio
async def test_get_embeddings_batch_mocked():
    """Test batch embedding with mocked API response."""
    mock_embeddings = [[0.1] * 1536, [0.2] * 1536]

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"embedding": mock_embeddings[0], "index": 0},
            {"embedding": mock_embeddings[1], "index": 1},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    async def mock_post(*args, **kwargs):
        return mock_response

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            result = await get_embeddings_batch(["text1", "text2"])

    assert len(result) == 2
    assert result[0] == mock_embeddings[0]
    assert result[1] == mock_embeddings[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
