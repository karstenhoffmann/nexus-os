"""Embedding generation job for documents."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from app.core.embeddings import get_embeddings_batch, serialize_f32
from app.core.embedding_providers import get_provider, EmbeddingError
from app.core.chunking import chunk_document, chunk_for_embedding
from app.core.storage import get_db
from app.core.settings import Settings

logger = logging.getLogger(__name__)

# OpenAI Embeddings Rate Limits (Dec 2025): 1M TPM, 3000 RPM, max 2048 inputs/request
# With ~200 tokens/chunk, batch of 200 = ~40k tokens, well under 1M TPM limit
# Increased from 10->50->200 based on actual API limits research
BATCH_SIZE = 200
MAX_EMBED_CHARS = 20000  # ~5000 tokens, safety limit per single input


def truncate_for_embedding(text: str, max_chars: int = MAX_EMBED_CHARS) -> str:
    """Truncate text to fit within embedding model token limits."""
    if len(text) <= max_chars:
        return text
    # Log truncation
    logger.warning(f"Truncating text from {len(text)} to {max_chars} chars")
    # Truncate at word boundary
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        return truncated[:last_space] + "..."
    return truncated + "..."


async def generate_embeddings_batch(limit: int = 100) -> dict[str, int]:
    """Generate embeddings for documents that don't have them yet.

    Uses the legacy doc_embeddings table for backward compatibility.

    Args:
        limit: Maximum number of documents to process in this run.

    Returns:
        Dict with counts: processed, failed, remaining
    """
    db = get_db()
    docs = db.get_documents_without_embedding(limit=limit)

    if not docs:
        stats = db.get_embedding_stats()
        return {"processed": 0, "failed": 0, "remaining": stats["pending"]}

    processed = 0
    failed = 0

    # Process in batches
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        texts = [doc["text"] for doc in batch]
        doc_ids = [doc["id"] for doc in batch]

        try:
            embeddings = await get_embeddings_batch(texts)

            for doc_id, embedding in zip(doc_ids, embeddings):
                try:
                    embedding_bytes = serialize_f32(embedding)
                    db.save_embedding(doc_id, embedding_bytes)
                    processed += 1
                    logger.info(f"Embedded document {doc_id}")
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to save embedding for doc {doc_id}: {e}")

        except Exception as e:
            failed += len(batch)
            logger.error(f"Batch embedding failed: {e}")

    stats = db.get_embedding_stats()
    return {"processed": processed, "failed": failed, "remaining": stats["pending"]}


async def generate_all_embeddings(
    batch_size: int = 100,
    delay_between_batches: float = 1.0,
) -> dict[str, int]:
    """Generate embeddings for ALL documents without embeddings.

    Processes in batches with delay to avoid rate limits.

    Args:
        batch_size: Documents per batch
        delay_between_batches: Seconds to wait between API calls

    Returns:
        Total counts: processed, failed
    """
    total_processed = 0
    total_failed = 0

    while True:
        result = await generate_embeddings_batch(limit=batch_size)
        total_processed += result["processed"]
        total_failed += result["failed"]

        logger.info(
            f"Batch complete: {result['processed']} processed, "
            f"{result['failed']} failed, {result['remaining']} remaining"
        )

        if result["remaining"] == 0 or result["processed"] == 0:
            break

        # Delay to avoid rate limits
        await asyncio.sleep(delay_between_batches)

    return {"processed": total_processed, "failed": total_failed}


# ==================== V2 Functions with Provider Abstraction ====================


async def generate_embeddings_v2(
    provider_name: str | None = None,
    model: str | None = None,
    limit: int = 100,
    include_chunks: bool = False,
    track_usage: bool = True,
) -> dict[str, int]:
    """Generate embeddings using the new provider abstraction.

    Args:
        provider_name: 'openai' or 'ollama'. Uses settings default if not specified.
        model: Model ID. Uses provider default if not specified.
        limit: Maximum documents to process
        include_chunks: If True, also generate chunk-level embeddings
        track_usage: If True, log API usage for cost tracking

    Returns:
        Dict with processed, failed, remaining counts and cost info
    """
    db = get_db()
    settings = Settings.from_env()

    # Get provider
    provider_name = provider_name or settings.embedding_provider
    provider = get_provider(provider_name, model)

    # Get documents without embeddings for this provider/model
    docs = db.get_documents_without_embedding_v2(
        provider=provider.name.lower(),
        model=provider.model_id,
        limit=limit,
    )

    if not docs:
        stats = db.get_embedding_stats_v2()
        return {
            "processed": 0,
            "failed": 0,
            "remaining": 0,
            "cost_usd": 0.0,
            "provider": provider.name,
            "model": provider.model_id,
        }

    processed = 0
    failed = 0
    total_tokens = 0
    total_cost = 0.0

    # Process in batches
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        texts = [chunk_for_embedding(doc["text"], doc.get("title", "")) for doc in batch]
        doc_ids = [doc["id"] for doc in batch]

        start_time = time.monotonic()
        try:
            embeddings = await provider.embed(texts)
            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Estimate tokens (rough)
            batch_tokens = sum(len(t) // 4 for t in texts)
            total_tokens += batch_tokens
            batch_cost = provider.estimate_cost(batch_tokens)
            total_cost += batch_cost

            # Prepare batch data for single-transaction save (fixes SQLite concurrency)
            embeddings_data = []
            for doc_id, embedding in zip(doc_ids, embeddings):
                try:
                    embedding_bytes = serialize_f32(embedding)
                    embeddings_data.append({
                        "embedding": embedding_bytes,
                        "document_id": doc_id,
                    })
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to serialize embedding for doc {doc_id}: {e}")

            # Save all embeddings in single transaction
            if embeddings_data:
                try:
                    saved = db.save_embeddings_batch(
                        embeddings_data=embeddings_data,
                        dimensions=provider.dimensions,
                        provider=provider.name.lower(),
                        model=provider.model_id,
                    )
                    processed += saved
                    for doc_id in doc_ids[:saved]:
                        logger.info(f"Embedded document {doc_id} with {provider.name}/{provider.model_id}")
                except Exception as e:
                    failed += len(embeddings_data)
                    logger.error(f"Failed to save embedding batch: {e}")

            # Track usage
            if track_usage:
                db.log_api_usage(
                    provider=provider.name.lower(),
                    model=provider.model_id,
                    operation="embed_batch",
                    tokens_input=batch_tokens,
                    cost_usd=batch_cost,
                    latency_ms=latency_ms,
                    success=True,
                    metadata=json.dumps({"doc_ids": doc_ids, "batch_size": len(batch)}),
                )

        except EmbeddingError as e:
            failed += len(batch)
            logger.error(f"Batch embedding failed: {e}")

            if track_usage:
                db.log_api_usage(
                    provider=provider.name.lower(),
                    model=provider.model_id,
                    operation="embed_batch",
                    tokens_input=0,
                    cost_usd=0,
                    success=False,
                    error_message=str(e),
                )

            if not e.retriable:
                break  # Don't continue if error is not retriable

        except Exception as e:
            failed += len(batch)
            logger.error(f"Batch embedding failed: {e}")

    # Optionally generate chunk embeddings
    chunks_processed = 0
    if include_chunks and processed > 0:
        chunks_result = await generate_chunk_embeddings_v2(
            provider_name=provider_name,
            model=model,
            limit=limit * 3,  # Roughly 3 chunks per doc on average
            track_usage=track_usage,
        )
        chunks_processed = chunks_result.get("processed", 0)
        total_cost += chunks_result.get("cost_usd", 0)

    return {
        "processed": processed,
        "failed": failed,
        "chunks_processed": chunks_processed,
        "cost_usd": round(total_cost, 6),
        "tokens": total_tokens,
        "provider": provider.name,
        "model": provider.model_id,
    }


async def generate_chunk_embeddings_v2(
    provider_name: str | None = None,
    model: str | None = None,
    limit: int = 100,
    track_usage: bool = True,
) -> dict[str, int]:
    """Generate embeddings for document chunks.

    First chunks documents that don't have chunks yet,
    then generates embeddings for chunks without embeddings.

    Args:
        provider_name: 'openai' or 'ollama'
        model: Model ID
        limit: Maximum chunks to process
        track_usage: If True, log API usage

    Returns:
        Dict with processed, failed counts and cost info
    """
    db = get_db()
    settings = Settings.from_env()

    provider_name = provider_name or settings.embedding_provider
    provider = get_provider(provider_name, model)

    # First, chunk documents that don't have chunks yet
    cur = db.conn.execute(
        """
        SELECT d.id, d.title, d.fulltext
        FROM documents d
        LEFT JOIN document_chunks c ON c.document_id = d.id
        WHERE c.id IS NULL AND d.fulltext IS NOT NULL AND d.fulltext != ''
        LIMIT ?
        """,
        (limit,),
    )
    docs_to_chunk = cur.fetchall()

    chunks_created = 0
    for doc_id, title, fulltext in docs_to_chunk:
        if not fulltext:
            continue
        chunks = chunk_document(fulltext, title or "")
        if chunks:
            db.save_chunks(doc_id, [c.to_dict() for c in chunks])
            chunks_created += len(chunks)
            logger.info(f"Created {len(chunks)} chunks for document {doc_id}")

    # Now get chunks without embeddings for this provider/model
    cur = db.conn.execute(
        """
        SELECT c.id, c.chunk_text, c.document_id
        FROM document_chunks c
        LEFT JOIN embeddings e ON e.chunk_id = c.id
            AND e.provider = ? AND e.model = ?
        WHERE e.id IS NULL
        LIMIT ?
        """,
        (provider.name.lower(), provider.model_id, limit),
    )
    chunks_to_embed = cur.fetchall()

    if not chunks_to_embed:
        return {
            "processed": 0,
            "failed": 0,
            "chunks_created": chunks_created,
            "cost_usd": 0.0,
            "provider": provider.name,
            "model": provider.model_id,
        }

    processed = 0
    failed = 0
    total_tokens = 0
    total_cost = 0.0

    # Process chunks in batches
    for i in range(0, len(chunks_to_embed), BATCH_SIZE):
        batch = chunks_to_embed[i : i + BATCH_SIZE]
        # Truncate texts that exceed embedding model limits
        texts = [truncate_for_embedding(row[1]) for row in batch]
        chunk_ids = [row[0] for row in batch]

        start_time = time.monotonic()
        try:
            embeddings = await provider.embed(texts)
            latency_ms = int((time.monotonic() - start_time) * 1000)

            batch_tokens = sum(len(t) // 4 for t in texts)
            total_tokens += batch_tokens
            batch_cost = provider.estimate_cost(batch_tokens)
            total_cost += batch_cost

            # Prepare batch data for single-transaction save (fixes SQLite concurrency)
            embeddings_data = []
            for chunk_id, embedding in zip(chunk_ids, embeddings):
                try:
                    embedding_bytes = serialize_f32(embedding)
                    embeddings_data.append({
                        "embedding": embedding_bytes,
                        "chunk_id": chunk_id,
                    })
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to serialize embedding for chunk {chunk_id}: {e}")

            # Save all embeddings in single transaction
            if embeddings_data:
                try:
                    saved = db.save_embeddings_batch(
                        embeddings_data=embeddings_data,
                        dimensions=provider.dimensions,
                        provider=provider.name.lower(),
                        model=provider.model_id,
                    )
                    processed += saved
                except Exception as e:
                    failed += len(embeddings_data)
                    logger.error(f"Failed to save embedding batch: {e}")

            if track_usage:
                db.log_api_usage(
                    provider=provider.name.lower(),
                    model=provider.model_id,
                    operation="embed_chunks",
                    tokens_input=batch_tokens,
                    cost_usd=batch_cost,
                    latency_ms=latency_ms,
                    success=True,
                    metadata=json.dumps({"chunk_ids": chunk_ids, "batch_size": len(batch)}),
                )

        except EmbeddingError as e:
            failed += len(batch)
            logger.error(f"Chunk embedding batch failed: {e}")
            if not e.retriable:
                break

        except Exception as e:
            failed += len(batch)
            logger.error(f"Chunk embedding batch failed: {e}")

    return {
        "processed": processed,
        "failed": failed,
        "chunks_created": chunks_created,
        "cost_usd": round(total_cost, 6),
        "tokens": total_tokens,
        "provider": provider.name,
        "model": provider.model_id,
    }
