"""Unified sync pipeline orchestrating import -> chunk -> embed -> index.

This module coordinates the complete data sync workflow:
1. IMPORT: Fetch documents from Readwise (Reader + Export APIs)
2. CHUNK: Split documents with fulltext into chunks for embedding
3. EMBED: Generate embeddings for all chunks via OpenAI
4. INDEX: Rebuild FTS index for keyword search

The pipeline reuses existing job infrastructure and yields SSE events
for real-time UI updates.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncIterator

if TYPE_CHECKING:
    from app.core.storage import DB

logger = logging.getLogger(__name__)


class PipelinePhase(str, Enum):
    """Phases of the sync pipeline."""

    IDLE = "idle"
    IMPORT = "import"
    CHUNK = "chunk"
    EMBED = "embed"
    INDEX = "index"
    DONE = "done"


class PipelineStatus(str, Enum):
    """Status of a pipeline job."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineEventType(str, Enum):
    """Types of events emitted during pipeline execution."""

    PHASE_START = "phase_start"
    PHASE_PROGRESS = "phase_progress"
    PHASE_COMPLETE = "phase_complete"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_PAUSED = "pipeline_paused"
    PIPELINE_CANCELLED = "pipeline_cancelled"
    PIPELINE_FAILED = "pipeline_failed"
    COST_CONFIRM = "cost_confirm"  # Requires user confirmation before embed
    HEARTBEAT = "heartbeat"  # Regular status ping during long operations


@dataclass
class PipelineEvent:
    """Event emitted during pipeline execution for SSE streaming."""

    type: PipelineEventType
    phase: PipelinePhase
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        event_data = {
            "type": self.type.value,
            "phase": self.phase.value,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }
        return f"event: {self.type.value}\ndata: {json.dumps(event_data)}\n\n"


@dataclass
class PipelineJob:
    """Tracks state of a sync pipeline job."""

    id: str
    status: PipelineStatus
    phase: PipelinePhase = PipelinePhase.IDLE

    # Child job references
    import_job_id: str | None = None
    embed_job_id: str | None = None

    # Aggregated counters
    docs_imported: int = 0
    docs_merged: int = 0
    chunks_created: int = 0
    chunks_embedded: int = 0
    chunks_total: int = 0

    # Cost tracking
    tokens_used: int = 0
    cost_usd: float = 0.0

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    def touch(self) -> None:
        """Update last_activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "phase": self.phase.value,
            "import_job_id": self.import_job_id,
            "embed_job_id": self.embed_job_id,
            "docs_imported": self.docs_imported,
            "docs_merged": self.docs_merged,
            "chunks_created": self.chunks_created,
            "chunks_embedded": self.chunks_embedded,
            "chunks_total": self.chunks_total,
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 6),
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "error": self.error,
        }


class PipelineJobStore:
    """In-memory store for pipeline jobs. Thread-safe."""

    def __init__(self) -> None:
        self._jobs: dict[str, PipelineJob] = {}
        self._lock = threading.Lock()

    def create(self) -> PipelineJob:
        """Create a new pending pipeline job."""
        job = PipelineJob(
            id=str(uuid.uuid4()),
            status=PipelineStatus.PENDING,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> PipelineJob | None:
        """Get job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: PipelineJob) -> None:
        """Update job in store."""
        job.touch()
        with self._lock:
            self._jobs[job.id] = job

    def pause(self, job_id: str) -> PipelineJob | None:
        """Pause a running job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != PipelineStatus.RUNNING:
                return None
            job.status = PipelineStatus.PAUSED
            job.touch()
            return job

    def cancel(self, job_id: str) -> PipelineJob | None:
        """Cancel a running or pending job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if job.status not in (PipelineStatus.RUNNING, PipelineStatus.PENDING, PipelineStatus.PAUSED):
                return None
            job.status = PipelineStatus.CANCELLED
            job.touch()
            return job

    def delete(self, job_id: str) -> bool:
        """Delete job from memory."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False

    def get_running(self) -> PipelineJob | None:
        """Get currently running job if any."""
        with self._lock:
            for job in self._jobs.values():
                if job.status == PipelineStatus.RUNNING:
                    return job
            return None

    def list_all(self) -> list[PipelineJob]:
        """List all jobs, newest first."""
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.started_at,
                reverse=True,
            )


# Global store instance
_pipeline_store: PipelineJobStore | None = None


def get_pipeline_store() -> PipelineJobStore:
    """Get or create the global pipeline store."""
    global _pipeline_store
    if _pipeline_store is None:
        _pipeline_store = PipelineJobStore()
    return _pipeline_store


def check_control_status(
    job: PipelineJob,
    store: PipelineJobStore,
    phase: PipelinePhase,
) -> PipelineEvent | None:
    """Check if job should stop due to pause/cancel.

    Returns event to yield if stopping, None to continue.
    Call this BEFORE entering loops to ensure responsiveness even with 0 items.
    """
    current = store.get(job.id)
    if not current:
        return None

    if current.status == PipelineStatus.PAUSED:
        return PipelineEvent(
            type=PipelineEventType.PIPELINE_PAUSED,
            phase=phase,
            data=job.to_dict(),
        )

    if current.status == PipelineStatus.CANCELLED:
        return PipelineEvent(
            type=PipelineEventType.PIPELINE_CANCELLED,
            phase=phase,
            data=job.to_dict(),
        )

    return None


# Constants for heartbeat timing
HEARTBEAT_INTERVAL = 2.0  # seconds


async def run_pipeline(
    job: PipelineJob,
    db: "DB",
    store: PipelineJobStore,
    token: str,
    skip_import: bool = False,
) -> AsyncIterator[PipelineEvent]:
    """Async wrapper that runs the pipeline in a thread for proper SSE streaming.

    The actual pipeline contains blocking I/O (HTTP requests to Readwise API).
    Running it directly in an async generator blocks the event loop and prevents
    SSE events from being sent. This wrapper runs the pipeline in a thread and
    yields events through an asyncio Queue.
    """
    import asyncio
    import queue

    # Queue for events from the pipeline thread
    event_queue: queue.Queue[PipelineEvent | None] = queue.Queue()

    def run_in_thread():
        """Run the sync pipeline and put events on the queue."""
        try:
            for event in _run_pipeline_sync(
                job=job,
                db=db,
                store=store,
                token=token,
                skip_import=skip_import,
            ):
                event_queue.put(event)
        except Exception as e:
            logger.exception("Pipeline error in thread")
            event_queue.put(PipelineEvent(
                type=PipelineEventType.PIPELINE_FAILED,
                phase=job.phase,
                data={"error": str(e)},
            ))
        finally:
            event_queue.put(None)  # Signal end of stream

    # Start pipeline in background thread
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

    # Yield events from queue asynchronously
    loop = asyncio.get_event_loop()
    while True:
        # Use run_in_executor to avoid blocking the event loop
        event = await loop.run_in_executor(None, event_queue.get)
        if event is None:
            break
        yield event


def _run_pipeline_sync(
    job: PipelineJob,
    db: "DB",
    store: PipelineJobStore,
    token: str,
    skip_import: bool = False,
):
    """Run the complete sync pipeline (synchronous generator).

    Phases:
    1. IMPORT - Fetch from Readwise (can be skipped)
    2. CHUNK - Create chunks for documents without chunks
    3. EMBED - Generate embeddings for chunks
    4. INDEX - Rebuild FTS index

    Args:
        job: The PipelineJob to run
        db: Database instance
        store: PipelineJobStore for state management
        token: Readwise API token
        skip_import: Skip import phase (for chunk/embed only)

    Yields:
        PipelineEvent for each significant action
    """
    from app.core.import_job import ImportStatus, get_import_store
    from app.core.embed_job_v2 import EmbedStatus, get_embed_store, run_embed_job
    from app.core.chunking import chunk_document
    from app.providers.readwise import ReadwiseClient, ImportEvent, ImportEventType

    job.status = PipelineStatus.RUNNING
    store.update(job)

    try:
        # ========== PHASE 1: IMPORT ==========
        if not skip_import:
            job.phase = PipelinePhase.IMPORT
            store.update(job)

            yield PipelineEvent(
                type=PipelineEventType.PHASE_START,
                phase=PipelinePhase.IMPORT,
                data={"message": "Verbinde mit Readwise API..."},
            )

            # Check control BEFORE expensive API operation
            stop_event = check_control_status(job, store, PipelinePhase.IMPORT)
            if stop_event:
                yield stop_event
                return

            import_store = get_import_store()
            import_job = import_store.create()
            job.import_job_id = import_job.id
            store.update(job)

            items_processed = 0
            last_heartbeat = time.monotonic()

            # Get last sync timestamp for incremental import
            last_sync_str = db.get_setting("last_sync_at")
            updated_after = None
            if last_sync_str:
                from datetime import datetime
                try:
                    updated_after = datetime.fromisoformat(last_sync_str)
                    logger.info(f"Incremental sync: fetching documents updated after {updated_after}")
                except ValueError:
                    logger.warning(f"Invalid last_sync_at value: {last_sync_str}, doing full sync")

            url_index: dict[str, str] = {}
            with ReadwiseClient(token=token) as client:
                for event in client.stream_import(import_job, url_index=url_index, updated_after=updated_after):
                    # Heartbeat for long-running operations
                    if time.monotonic() - last_heartbeat > HEARTBEAT_INTERVAL:
                        yield PipelineEvent(
                            type=PipelineEventType.HEARTBEAT,
                            phase=PipelinePhase.IMPORT,
                            data={"items_processed": items_processed, "status": "processing"},
                        )
                        last_heartbeat = time.monotonic()

                    # Check for pause/cancel inside loop for responsiveness
                    stop_event = check_control_status(job, store, PipelinePhase.IMPORT)
                    if stop_event:
                        if stop_event.type == PipelineEventType.PIPELINE_PAUSED:
                            import_store.pause(import_job.id)
                        else:
                            import_store.cancel(import_job.id)
                        yield stop_event
                        return

                    # Process import events
                    if event.type == ImportEventType.ITEM:
                        items_processed += 1
                        last_heartbeat = time.monotonic()
                        # Save article and highlights to DB
                        article_data = event.data.get("article", {})
                        if article_data.get("provider_id"):
                            from app.core.content_fetcher import extract_text_from_html

                            html_content = article_data.get("html_content")
                            clean_text = extract_text_from_html(html_content) if html_content else None
                            doc_id = db.save_article(
                                source=article_data.get("provider", "unknown"),
                                provider_id=article_data.get("provider_id", ""),
                                url_original=article_data.get("source_url"),
                                title=article_data.get("title"),
                                author=article_data.get("author"),
                                published_at=article_data.get("published_date"),
                                saved_at=article_data.get("saved_at"),
                                category=article_data.get("category"),
                                word_count=article_data.get("word_count"),
                                fulltext=clean_text,
                                fulltext_html=html_content,
                                fulltext_source="readwise" if clean_text else None,
                                summary=article_data.get("summary"),
                            )
                            # Save highlights if present
                            highlights = event.data.get("highlights", [])
                            for hl in highlights:
                                if hl.get("provider_id") and hl.get("text"):
                                    db.save_highlight(
                                        document_id=doc_id,
                                        provider_highlight_id=hl["provider_id"],
                                        text=hl["text"],
                                        note=hl.get("note"),
                                        highlighted_at=hl.get("highlighted_at"),
                                        provider=hl.get("provider"),
                                    )

                    elif event.type == ImportEventType.PROGRESS:
                        job.docs_imported = import_job.items_imported
                        job.docs_merged = import_job.items_merged
                        store.update(job)
                        last_heartbeat = time.monotonic()

                        yield PipelineEvent(
                            type=PipelineEventType.PHASE_PROGRESS,
                            phase=PipelinePhase.IMPORT,
                            data={
                                "docs_imported": job.docs_imported,
                                "docs_merged": job.docs_merged,
                                "items_total": import_job.items_total,
                            },
                        )

                    elif event.type == ImportEventType.ERROR:
                        logger.warning(f"Import error: {event.data}")

                    elif event.type == ImportEventType.COMPLETED:
                        # Rebuild FTS after import
                        db.rebuild_fts()
                        break

            # Ensure we always send a progress event, even if no items were imported
            if items_processed == 0:
                yield PipelineEvent(
                    type=PipelineEventType.PHASE_PROGRESS,
                    phase=PipelinePhase.IMPORT,
                    data={
                        "docs_imported": 0,
                        "docs_merged": 0,
                        "message": "Keine neuen Dokumente gefunden",
                    },
                )

            yield PipelineEvent(
                type=PipelineEventType.PHASE_COMPLETE,
                phase=PipelinePhase.IMPORT,
                data={
                    "docs_imported": job.docs_imported,
                    "docs_merged": job.docs_merged,
                },
            )

        # ========== PHASE 2: CHUNK ==========
        job.phase = PipelinePhase.CHUNK
        store.update(job)

        # Get total count BEFORE processing for progress percentage
        stats = db.count_documents_for_fetch()
        docs_to_chunk = stats.get("without_chunks", 0)

        yield PipelineEvent(
            type=PipelineEventType.PHASE_START,
            phase=PipelinePhase.CHUNK,
            data={
                "message": "Pruefe Dokumente fuer Chunking...",
                "docs_total": docs_to_chunk,
            },
        )

        # Check control BEFORE processing
        stop_event = check_control_status(job, store, PipelinePhase.CHUNK)
        if stop_event:
            yield stop_event
            return

        # Get documents that need chunking
        chunks_created = 0
        docs_processed = 0
        batch_size = 50

        # First check: Are there any documents to chunk?
        docs = db.get_documents_for_chunking(limit=batch_size)

        if not docs:
            # Nothing to do - send explicit feedback
            yield PipelineEvent(
                type=PipelineEventType.PHASE_PROGRESS,
                phase=PipelinePhase.CHUNK,
                data={
                    "chunks_created": 0,
                    "docs_processed": 0,
                    "docs_total": docs_to_chunk,
                    "message": "Keine Dokumente benoetigen Chunking",
                },
            )
        else:
            while docs:
                # Check for pause/cancel at start of each batch
                stop_event = check_control_status(job, store, PipelinePhase.CHUNK)
                if stop_event:
                    yield stop_event
                    return

                for doc in docs:
                    if doc["fulltext"]:
                        chunks = chunk_document(
                            fulltext=doc["fulltext"],
                            title=doc["title"] or "",
                        )
                        if chunks:
                            db.save_chunks(
                                document_id=doc["id"],
                                chunks=[c.to_dict() for c in chunks],
                            )
                            chunks_created += len(chunks)

                docs_processed += len(docs)
                job.chunks_created = chunks_created
                store.update(job)

                yield PipelineEvent(
                    type=PipelineEventType.PHASE_PROGRESS,
                    phase=PipelinePhase.CHUNK,
                    data={
                        "chunks_created": chunks_created,
                        "docs_processed": docs_processed,
                        "docs_total": docs_to_chunk,
                    },
                )

                # Get next batch
                docs = db.get_documents_for_chunking(limit=batch_size)

        yield PipelineEvent(
            type=PipelineEventType.PHASE_COMPLETE,
            phase=PipelinePhase.CHUNK,
            data={
                "chunks_created": chunks_created,
                "docs_processed": docs_processed,
                "docs_total": docs_to_chunk,
            },
        )

        # ========== PHASE 3: EMBED ==========
        job.phase = PipelinePhase.EMBED
        store.update(job)

        yield PipelineEvent(
            type=PipelineEventType.PHASE_START,
            phase=PipelinePhase.EMBED,
            data={"message": "Pruefe ausstehende Embeddings..."},
        )

        # Check control BEFORE expensive operation
        stop_event = check_control_status(job, store, PipelinePhase.EMBED)
        if stop_event:
            yield stop_event
            return

        # Get stats for embedding
        stats = db.count_chunks_for_embedding()
        pending_chunks = stats["pending_chunks"]

        if pending_chunks == 0:
            yield PipelineEvent(
                type=PipelineEventType.PHASE_PROGRESS,
                phase=PipelinePhase.EMBED,
                data={"chunks_embedded": 0, "message": "Alle Chunks haben bereits Embeddings"},
            )
            yield PipelineEvent(
                type=PipelineEventType.PHASE_COMPLETE,
                phase=PipelinePhase.EMBED,
                data={"chunks_embedded": 0},
            )
        else:
            # Estimate cost
            est_tokens = pending_chunks * 200  # ~200 tokens per chunk
            est_cost = est_tokens * 0.02 / 1_000_000  # text-embedding-3-small price

            yield PipelineEvent(
                type=PipelineEventType.PHASE_PROGRESS,
                phase=PipelinePhase.EMBED,
                data={
                    "message": f"Generiere Embeddings fuer {pending_chunks} Chunks...",
                    "pending_chunks": pending_chunks,
                    "estimated_cost_usd": round(est_cost, 4),
                },
            )

            job.chunks_total = pending_chunks
            store.update(job)

            # Create and run embed job
            embed_store = get_embed_store()
            embed_job = embed_store.create(items_total=pending_chunks)
            job.embed_job_id = embed_job.id
            store.update(job)

            # Run async embed job in a new event loop (we're in a thread)
            import asyncio

            async def collect_embed_events():
                events = []
                async for event in run_embed_job(embed_job, db, embed_store):
                    events.append(event)
                return events

            embed_events = asyncio.run(collect_embed_events())

            for event in embed_events:
                # Check for pause/cancel
                stop_event = check_control_status(job, store, PipelinePhase.EMBED)
                if stop_event:
                    if stop_event.type == PipelineEventType.PIPELINE_PAUSED:
                        embed_store.pause(embed_job.id)
                    else:
                        embed_store.cancel(embed_job.id)
                    yield stop_event
                    return

                # Update pipeline job from embed job
                job.chunks_embedded = embed_job.items_succeeded
                job.tokens_used = embed_job.tokens_used
                job.cost_usd = embed_job.cost_usd
                store.update(job)

                yield PipelineEvent(
                    type=PipelineEventType.PHASE_PROGRESS,
                    phase=PipelinePhase.EMBED,
                    data={
                        "chunks_embedded": job.chunks_embedded,
                        "chunks_total": job.chunks_total,
                        "tokens_used": job.tokens_used,
                        "cost_usd": round(job.cost_usd, 4),
                        "progress_percent": embed_job.progress_percent,
                    },
                )

            yield PipelineEvent(
                type=PipelineEventType.PHASE_COMPLETE,
                phase=PipelinePhase.EMBED,
                data={
                    "chunks_embedded": job.chunks_embedded,
                    "tokens_used": job.tokens_used,
                    "cost_usd": round(job.cost_usd, 4),
                },
            )

        # ========== PHASE 4: INDEX ==========
        job.phase = PipelinePhase.INDEX
        store.update(job)

        yield PipelineEvent(
            type=PipelineEventType.PHASE_START,
            phase=PipelinePhase.INDEX,
            data={"message": "Aktualisiere Suchindex..."},
        )

        indexed_count = db.rebuild_fts()

        yield PipelineEvent(
            type=PipelineEventType.PHASE_COMPLETE,
            phase=PipelinePhase.INDEX,
            data={"indexed_documents": indexed_count},
        )

        # ========== DONE ==========
        job.phase = PipelinePhase.DONE
        job.status = PipelineStatus.COMPLETED
        store.update(job)

        # Save last_sync_at for incremental sync next time
        from datetime import datetime
        db.set_setting("last_sync_at", datetime.utcnow().isoformat())
        logger.info("Saved last_sync_at timestamp for incremental sync")

        yield PipelineEvent(
            type=PipelineEventType.PIPELINE_COMPLETE,
            phase=PipelinePhase.DONE,
            data={
                "summary": {
                    "docs_imported": job.docs_imported,
                    "docs_merged": job.docs_merged,
                    "chunks_created": job.chunks_created,
                    "chunks_embedded": job.chunks_embedded,
                    "tokens_used": job.tokens_used,
                    "cost_usd": round(job.cost_usd, 4),
                },
                **job.to_dict(),
            },
        )

    except Exception as e:
        logger.exception(f"Pipeline error: {e}")
        job.status = PipelineStatus.FAILED
        job.error = str(e)
        store.update(job)

        yield PipelineEvent(
            type=PipelineEventType.PIPELINE_FAILED,
            phase=job.phase,
            data={"error": str(e), **job.to_dict()},
        )
