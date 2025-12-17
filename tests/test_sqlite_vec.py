"""Test sqlite-vec functionality."""

import sqlite3
import struct

import pytest
import sqlite_vec


def serialize_f32(vector: list[float]) -> bytes:
    """Serialize a list of floats into bytes for sqlite-vec."""
    return struct.pack(f"{len(vector)}f", *vector)


def test_sqlite_vec_loads():
    """Test that sqlite-vec extension loads correctly."""
    conn = sqlite3.connect(":memory:")
    sqlite_vec.load(conn)

    # Check version
    cur = conn.execute("SELECT vec_version()")
    version = cur.fetchone()[0]
    assert version is not None
    conn.close()


def test_vec0_insert_and_query():
    """Test basic vec0 insert and similarity search."""
    conn = sqlite3.connect(":memory:")
    sqlite_vec.load(conn)

    # Create table with 4 dimensions (small for testing)
    conn.execute("""
        CREATE VIRTUAL TABLE test_embeddings USING vec0(
            embedding float[4],
            doc_id integer
        )
    """)

    # Insert test vectors
    vectors = [
        ([1.0, 0.0, 0.0, 0.0], 1),  # doc 1
        ([0.0, 1.0, 0.0, 0.0], 2),  # doc 2
        ([0.9, 0.1, 0.0, 0.0], 3),  # doc 3 - similar to doc 1
    ]

    for vec, doc_id in vectors:
        conn.execute(
            "INSERT INTO test_embeddings (embedding, doc_id) VALUES (?, ?)",
            (serialize_f32(vec), doc_id),
        )
    conn.commit()

    # Query for vectors similar to [1.0, 0.0, 0.0, 0.0]
    query_vec = [1.0, 0.0, 0.0, 0.0]
    cur = conn.execute(
        """
        SELECT doc_id, distance
        FROM test_embeddings
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT 3
        """,
        (serialize_f32(query_vec),),
    )

    results = cur.fetchall()
    conn.close()

    # doc 1 should be first (exact match), doc 3 second (similar)
    assert len(results) == 3
    assert results[0][0] == 1  # doc_id 1 first
    assert results[1][0] == 3  # doc_id 3 second (similar)
    assert results[2][0] == 2  # doc_id 2 last (orthogonal)


def test_vec0_with_1536_dimensions():
    """Test vec0 with OpenAI ada-002 dimensions (1536)."""
    conn = sqlite3.connect(":memory:")
    sqlite_vec.load(conn)

    conn.execute("""
        CREATE VIRTUAL TABLE doc_embeddings USING vec0(
            embedding float[1536],
            document_id integer
        )
    """)

    # Create two similar vectors and one different
    vec1 = [0.1] * 1536
    vec2 = [0.1] * 1536
    vec2[0] = 0.15  # slightly different
    vec3 = [-0.1] * 1536  # opposite direction

    conn.execute(
        "INSERT INTO doc_embeddings (embedding, document_id) VALUES (?, ?)",
        (serialize_f32(vec1), 100),
    )
    conn.execute(
        "INSERT INTO doc_embeddings (embedding, document_id) VALUES (?, ?)",
        (serialize_f32(vec2), 200),
    )
    conn.execute(
        "INSERT INTO doc_embeddings (embedding, document_id) VALUES (?, ?)",
        (serialize_f32(vec3), 300),
    )
    conn.commit()

    # Query similar to vec1
    cur = conn.execute(
        """
        SELECT document_id, distance
        FROM doc_embeddings
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT 3
        """,
        (serialize_f32(vec1),),
    )

    results = cur.fetchall()
    conn.close()

    # doc 100 first (exact), doc 200 second (similar), doc 300 last (opposite)
    assert results[0][0] == 100
    assert results[1][0] == 200
    assert results[2][0] == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
