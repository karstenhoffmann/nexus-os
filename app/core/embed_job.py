"""Embedding generation job for documents."""

from __future__ import annotations

import asyncio
import logging

from app.core.embeddings import get_embeddings_batch, serialize_f32
from app.core.storage import get_db

logger = logging.getLogger(__name__)

BATCH_SIZE = 50  # OpenAI supports up to 2048, but 50 is safer for memory


async def generate_embeddings_batch(limit: int = 100) -> dict[str, int]:
    """Generate embeddings for documents that don't have them yet.

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
