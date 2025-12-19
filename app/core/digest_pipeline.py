"""Digest Pipeline - Orchestrates the full digest generation flow.

Pipeline Phases:
1. FETCH: Load chunks from date range
2. CLUSTER: Group chunks into topics (hybrid or pure_llm)
3. SUMMARIZE: Generate overall summary and highlights
4. COMPILE: Store results in database

Usage:
    job = digest_store.create(strategy="hybrid", model="gpt-4.1-mini", days=7)
    async for event in run_digest_pipeline(job, db):
        # Handle SSE events
        pass
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator

from app.core.digest_clustering import ClusteringResult, cluster_chunks
from app.core.digest_job import (
    DigestEvent,
    DigestEventType,
    DigestJob,
    DigestPhase,
    DigestStatus,
    get_digest_store,
)
from app.core.llm_providers import LLMProvider, get_chat_provider
from app.core.storage import DB

logger = logging.getLogger(__name__)


async def run_digest_pipeline(
    job: DigestJob,
    db: DB,
) -> AsyncGenerator[DigestEvent, None]:
    """Run the full digest generation pipeline.

    Args:
        job: DigestJob with configuration (strategy, model, days)
        db: DB instance for database access

    Yields:
        DigestEvent for SSE streaming to client

    Updates:
        job state is updated throughout and saved to the store
    """
    store = get_digest_store()
    llm = get_chat_provider(provider_name="openai", model=job.model)

    # Calculate date range
    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=job.days)
    job.date_from = date_from
    job.date_to = date_to
    job.status = DigestStatus.RUNNING
    store.update(job)

    try:
        # Phase 1: FETCH
        chunks, docs_count = await _fetch_phase(job, db, store)
        yield DigestEvent(
            type=DigestEventType.PHASE_COMPLETE,
            phase=DigestPhase.FETCH,
            data={
                "chunks_found": len(chunks),
                "docs_found": docs_count,
            },
        )

        if not chunks:
            job.status = DigestStatus.COMPLETED
            job.phase = DigestPhase.DONE
            job.error = "Keine Chunks im Zeitraum gefunden"
            store.update(job)
            yield DigestEvent(
                type=DigestEventType.DIGEST_COMPLETE,
                phase=DigestPhase.DONE,
                data={"message": "Keine Inhalte zum Analysieren"},
            )
            return

        # Phase 2: CLUSTER
        clustering_result = await _cluster_phase(job, chunks, llm, store)
        yield DigestEvent(
            type=DigestEventType.PHASE_COMPLETE,
            phase=DigestPhase.CLUSTER,
            data={
                "topics_created": len(clustering_result.clusters),
                "strategy": clustering_result.strategy,
            },
        )

        # Phase 3: SUMMARIZE
        overall_summary, highlights = await _summarize_phase(
            job, clustering_result, llm, store
        )
        yield DigestEvent(
            type=DigestEventType.PHASE_COMPLETE,
            phase=DigestPhase.SUMMARIZE,
            data={
                "summary_length": len(overall_summary),
                "highlights_count": len(highlights),
            },
        )

        # Phase 4: COMPILE
        digest_id = await _compile_phase(
            job, db, clustering_result, overall_summary, highlights, store
        )
        yield DigestEvent(
            type=DigestEventType.PHASE_COMPLETE,
            phase=DigestPhase.COMPILE,
            data={"digest_id": digest_id},
        )

        # Done
        job.status = DigestStatus.COMPLETED
        job.phase = DigestPhase.DONE
        job.digest_id = digest_id
        store.update(job)

        yield DigestEvent(
            type=DigestEventType.DIGEST_COMPLETE,
            phase=DigestPhase.DONE,
            data={
                "digest_id": digest_id,
                "topics_count": len(clustering_result.clusters),
                "total_cost_usd": round(job.cost_usd, 6),
                "total_tokens": job.total_tokens,
            },
        )

    except Exception as e:
        logger.exception(f"Digest pipeline failed: {e}")
        job.status = DigestStatus.FAILED
        job.error = str(e)
        store.update(job)
        yield DigestEvent(
            type=DigestEventType.DIGEST_FAILED,
            phase=job.phase,
            data={"error": str(e)},
        )


async def _fetch_phase(
    job: DigestJob,
    db: DB,
    store: Any,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch chunks from database for the date range.

    Returns:
        Tuple of (chunks list, unique document count)
    """
    job.phase = DigestPhase.FETCH
    store.update(job)

    date_from_str = job.date_from.strftime("%Y-%m-%d") if job.date_from else ""
    date_to_str = job.date_to.strftime("%Y-%m-%d") if job.date_to else ""

    logger.info(f"Fetching chunks from {date_from_str} to {date_to_str}")

    # For hybrid strategy, we need embeddings
    if job.strategy == "hybrid":
        chunks = db.get_chunk_embeddings_in_date_range(
            date_from=date_from_str,
            date_to=date_to_str,
            limit=2000,
        )
    else:
        # Pure LLM doesn't need embeddings
        chunks = db.get_chunks_in_date_range(
            date_from=date_from_str,
            date_to=date_to_str,
            limit=2000,
        )

    # Count unique documents
    doc_ids = set(c["document_id"] for c in chunks)

    job.chunks_found = len(chunks)
    job.docs_found = len(doc_ids)
    store.update(job)

    logger.info(f"Fetched {len(chunks)} chunks from {len(doc_ids)} documents")

    return chunks, len(doc_ids)


async def _cluster_phase(
    job: DigestJob,
    chunks: list[dict[str, Any]],
    llm: LLMProvider,
    store: Any,
) -> ClusteringResult:
    """Cluster chunks into topics using the configured strategy."""
    job.phase = DigestPhase.CLUSTER
    store.update(job)

    logger.info(f"Clustering {len(chunks)} chunks with strategy '{job.strategy}'")

    result = await cluster_chunks(
        chunks=chunks,
        llm=llm,
        strategy=job.strategy,
        num_clusters=7,  # Default number of topics
    )

    # Track token usage
    job.add_tokens(result.tokens_input, result.tokens_output, result.cost_usd)
    job.topics_created = len(result.clusters)
    store.update(job)

    logger.info(
        f"Created {len(result.clusters)} clusters, "
        f"tokens: {result.tokens_input}+{result.tokens_output}, "
        f"cost: ${result.cost_usd:.4f}"
    )

    return result


async def _summarize_phase(
    job: DigestJob,
    clustering_result: ClusteringResult,
    llm: LLMProvider,
    store: Any,
) -> tuple[str, list[str]]:
    """Generate overall summary and highlights from clustered topics."""
    job.phase = DigestPhase.SUMMARIZE
    store.update(job)

    # Build topics summary for the LLM
    topics_text = []
    for cluster in clustering_result.clusters:
        topic_info = f"**{cluster.topic_name}** ({cluster.chunk_count} Chunks)"
        if cluster.summary:
            topic_info += f"\n{cluster.summary}"
        if cluster.key_points:
            topic_info += "\n- " + "\n- ".join(cluster.key_points)
        topics_text.append(topic_info)

    topics_joined = "\n\n".join(topics_text)

    # Generate overall summary
    prompt = f"""Du bist ein persoenlicher Wissensassistent. Der Nutzer hat diese Woche folgende Themen gelesen:

{topics_joined}

Erstelle:
1. Eine Zusammenfassung (3-5 Saetze): Was hat den Nutzer diese Woche beschaeftigt?
2. 3-5 Highlights: Die wichtigsten Erkenntnisse oder interessantesten Punkte

Antworte im JSON-Format:
{{
  "summary": "...",
  "highlights": ["...", "...", "..."]
}}"""

    response = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=800,
    )

    # Track token usage
    cost = llm.estimate_cost(response.tokens_input, response.tokens_output)
    job.add_tokens(response.tokens_input, response.tokens_output, cost)
    job.summaries_generated = 1
    store.update(job)

    # Parse response
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    try:
        data = json.loads(content)
        summary = data.get("summary", "")
        highlights = data.get("highlights", [])
    except json.JSONDecodeError:
        logger.warning("Failed to parse summary response, using raw content")
        summary = content[:500]
        highlights = []

    logger.info(
        f"Generated summary ({len(summary)} chars) and {len(highlights)} highlights"
    )

    return summary, highlights


async def _compile_phase(
    job: DigestJob,
    db: DB,
    clustering_result: ClusteringResult,
    overall_summary: str,
    highlights: list[str],
    store: Any,
) -> int:
    """Store the generated digest in the database."""
    job.phase = DigestPhase.COMPILE
    store.update(job)

    # Prepare topics JSON
    topics_json = json.dumps(
        [c.to_dict() for c in clustering_result.clusters],
        ensure_ascii=False,
    )

    # Prepare highlights JSON
    highlights_json = json.dumps(highlights, ensure_ascii=False) if highlights else None

    # Generate digest name
    date_from_str = job.date_from.strftime("%Y-%m-%d") if job.date_from else ""
    date_to_str = job.date_to.strftime("%Y-%m-%d") if job.date_to else ""
    name = f"Digest {date_from_str} bis {date_to_str}"

    # Save to database
    digest_id = db.save_generated_digest(
        name=name,
        time_range_days=job.days,
        date_from=date_from_str,
        date_to=date_to_str,
        strategy=job.strategy,
        model_id=job.model,
        summary_text=overall_summary,
        topics_json=topics_json,
        highlights_json=highlights_json,
        docs_analyzed=job.docs_found,
        chunks_analyzed=job.chunks_found,
        tokens_input=job.tokens_input,
        tokens_output=job.tokens_output,
        cost_usd=job.cost_usd,
    )

    logger.info(
        f"Saved digest {digest_id}: {name}, "
        f"{job.docs_found} docs, {job.chunks_found} chunks, "
        f"cost: ${job.cost_usd:.4f}"
    )

    return digest_id


async def estimate_digest(
    days: int,
    db: DB,
    model: str = "gpt-4.1-mini",
) -> dict[str, Any]:
    """Estimate cost and scope for a digest without generating it.

    Args:
        days: Number of days to include
        db: DB instance
        model: Model to use for estimation

    Returns:
        Dict with chunk/doc counts and cost estimate
    """
    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=days)

    date_from_str = date_from.strftime("%Y-%m-%d")
    date_to_str = date_to.strftime("%Y-%m-%d")

    chunks = db.get_chunks_in_date_range(
        date_from=date_from_str,
        date_to=date_to_str,
        limit=2000,
    )

    doc_ids = set(c["document_id"] for c in chunks)

    # Import here to avoid circular import
    from app.core.llm_providers import estimate_digest_cost

    cost_estimate = estimate_digest_cost(chunks_count=len(chunks), model=model)

    return {
        "days": days,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "docs_count": len(doc_ids),
        "chunks_count": len(chunks),
        **cost_estimate,
    }
