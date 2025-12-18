"""Tests for embedding job and storage methods."""

import os
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
import sqlite_vec

from app.core.embeddings import serialize_f32
from app.core.storage import DB


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    sqlite_vec.load(conn)
    database = DB(conn=conn)
    database.init()
    return database


def test_get_documents_without_embedding_empty(db):
    """Test with no documents in DB."""
    docs = db.get_documents_without_embedding()
    assert docs == []


def test_get_documents_without_embedding(db):
    """Test getting documents that need embeddings."""
    # Insert test documents
    db.save_article(
        source="test",
        provider_id="doc1",
        url_original="https://example.com/1",
        title="Test Document 1",
        author="Author 1",
        summary="Summary 1",
        fulltext="Fulltext content 1",
    )
    db.save_article(
        source="test",
        provider_id="doc2",
        url_original="https://example.com/2",
        title="Test Document 2",
        author=None,
        summary=None,
        fulltext="Fulltext content 2",
    )

    docs = db.get_documents_without_embedding()
    assert len(docs) == 2
    assert docs[0]["title"] == "Test Document 1"
    assert "Author 1" in docs[0]["text"]
    assert "Summary 1" in docs[0]["text"]
    assert docs[1]["title"] == "Test Document 2"


def test_save_embedding(db):
    """Test saving an embedding for a document."""
    # Insert a document
    doc_id = db.save_article(
        source="test",
        provider_id="doc1",
        url_original="https://example.com/1",
        title="Test Document",
    )

    # Save embedding
    embedding = [0.1] * 1536
    embedding_bytes = serialize_f32(embedding)
    db.save_embedding(doc_id, embedding_bytes)

    # Verify it was saved
    cur = db.conn.execute(
        "SELECT document_id FROM doc_embeddings WHERE document_id = ?",
        (doc_id,),
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] == doc_id


def test_save_embedding_replaces_existing(db):
    """Test that saving embedding replaces existing one."""
    doc_id = db.save_article(
        source="test",
        provider_id="doc1",
        url_original="https://example.com/1",
        title="Test Document",
    )

    # Save first embedding
    embedding1 = [0.1] * 1536
    db.save_embedding(doc_id, serialize_f32(embedding1))

    # Save second embedding (should replace)
    embedding2 = [0.2] * 1536
    db.save_embedding(doc_id, serialize_f32(embedding2))

    # Verify only one exists
    cur = db.conn.execute(
        "SELECT COUNT(*) FROM doc_embeddings WHERE document_id = ?",
        (doc_id,),
    )
    count = cur.fetchone()[0]
    assert count == 1


def test_get_documents_without_embedding_excludes_embedded(db):
    """Test that documents with embeddings are excluded."""
    # Insert two documents
    doc_id1 = db.save_article(
        source="test",
        provider_id="doc1",
        url_original="https://example.com/1",
        title="Doc with embedding",
    )
    db.save_article(
        source="test",
        provider_id="doc2",
        url_original="https://example.com/2",
        title="Doc without embedding",
    )

    # Add embedding to first doc
    embedding = [0.1] * 1536
    db.save_embedding(doc_id1, serialize_f32(embedding))

    # Get docs without embeddings
    docs = db.get_documents_without_embedding()
    assert len(docs) == 1
    assert docs[0]["title"] == "Doc without embedding"


def test_get_embedding_stats(db):
    """Test embedding statistics."""
    # Empty DB
    stats = db.get_embedding_stats()
    assert stats["total_documents"] == 0
    assert stats["embedded_documents"] == 0
    assert stats["pending"] == 0

    # Add documents
    doc_id = db.save_article(
        source="test",
        provider_id="doc1",
        url_original="https://example.com/1",
        title="Doc 1",
    )
    db.save_article(
        source="test",
        provider_id="doc2",
        url_original="https://example.com/2",
        title="Doc 2",
    )

    stats = db.get_embedding_stats()
    assert stats["total_documents"] == 2
    assert stats["embedded_documents"] == 0
    assert stats["pending"] == 2

    # Add embedding to one doc
    db.save_embedding(doc_id, serialize_f32([0.1] * 1536))

    stats = db.get_embedding_stats()
    assert stats["total_documents"] == 2
    assert stats["embedded_documents"] == 1
    assert stats["pending"] == 1


@pytest.mark.asyncio
async def test_generate_embeddings_batch():
    """Test batch embedding generation with mocked API."""
    from app.core.embed_job import generate_embeddings_batch

    # Create in-memory DB
    conn = sqlite3.connect(":memory:")
    sqlite_vec.load(conn)
    db = DB(conn=conn)
    db.init()

    # Insert test documents
    db.save_article(
        source="test",
        provider_id="doc1",
        url_original="https://example.com/1",
        title="Test Doc 1",
        fulltext="Content 1",
    )
    db.save_article(
        source="test",
        provider_id="doc2",
        url_original="https://example.com/2",
        title="Test Doc 2",
        fulltext="Content 2",
    )

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

    with patch("app.core.storage._db", db):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("httpx.AsyncClient.post", side_effect=mock_post):
                result = await generate_embeddings_batch(limit=10)

    assert result["processed"] == 2
    assert result["failed"] == 0
    assert result["remaining"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
