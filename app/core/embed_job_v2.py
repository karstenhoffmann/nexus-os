"""Embedding job management with SSE streaming.

Provides:
- EmbedJob and EmbedJobStore for job state management
- run_embed_job() async generator for SSE streaming
- Cursor-based processing for pause/resume

Pattern copied from fetch_job.py (proven to work).
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncIterator

if TYPE_CHECKING:
    from app.core.storage import DB

logger = logging.getLogger(__name__)


class EmbedStatus(str, Enum):
    """Status of an embedding job."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class EmbedEventType(str, Enum):
    """Types of events emitted during embedding."""

    STARTED = "started"
    BATCH_COMPLETE = "batch_complete"
    PAUSED = "paused"
    RESUMED = "resumed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class EmbedEvent:
    """Event emitted during embedding job for SSE streaming."""

    type: EmbedEventType
    job_id: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        import json

        event_data = {
            "type": self.type.value,
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }
        return f"event: {self.type.value}\ndata: {json.dumps(event_data)}\n\n"


@dataclass
class EmbedJob:
    """Tracks state of an embedding job."""

    id: str
    status: EmbedStatus
    cursor_chunk_id: int | None = None  # Resume position
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    items_total: int | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    def touch(self) -> None:
        """Update last_activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if not self.items_total or self.items_total == 0:
            return 0.0
        return (self.items_processed / self.items_total) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "cursor_chunk_id": self.cursor_chunk_id,
            "items_processed": self.items_processed,
            "items_succeeded": self.items_succeeded,
            "items_failed": self.items_failed,
            "items_total": self.items_total,
            "progress_percent": round(self.progress_percent, 1),
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 6),
            "provider": self.provider,
            "model": self.model,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "error": self.error,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> EmbedJob:
        """Create EmbedJob from database row."""
        return cls(
            id=row["id"],
            status=EmbedStatus(row["status"]),
            cursor_chunk_id=row["cursor_chunk_id"],
            items_processed=row["items_processed"],
            items_succeeded=row["items_succeeded"],
            items_failed=row["items_failed"],
            items_total=row["items_total"],
            tokens_used=row["tokens_used"] or 0,
            cost_usd=row["cost_usd"] or 0.0,
            provider=row["provider"] or "openai",
            model=row["model"] or "text-embedding-3-small",
            started_at=datetime.fromisoformat(row["started_at"]),
            last_activity=datetime.fromisoformat(row["last_activity"]),
            error=row["error"],
        )


class EmbedJobStore:
    """Store for EmbedJobs with DB persistence. Thread-safe."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._jobs: dict[str, EmbedJob] = {}
        self._lock = threading.Lock()
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load all non-completed jobs from DB into memory."""
        cur = self._conn.execute(
            """
            SELECT id, status, cursor_chunk_id, items_processed, items_succeeded,
                   items_failed, items_total, tokens_used, cost_usd, provider, model,
                   started_at, last_activity, error
            FROM embed_jobs
            WHERE status NOT IN ('completed')
            ORDER BY started_at DESC
            """
        )
        for row in cur.fetchall():
            job = EmbedJob.from_row(row)
            self._jobs[job.id] = job

    def create(
        self,
        items_total: int | None = None,
        provider: str = "openai",
        model: str = "text-embedding-3-small",
    ) -> EmbedJob:
        """Create a new pending EmbedJob and persist to DB."""
        job = EmbedJob(
            id=str(uuid.uuid4()),
            status=EmbedStatus.PENDING,
            items_total=items_total,
            provider=provider,
            model=model,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._persist(job)
        return job

    def _persist(self, job: EmbedJob) -> None:
        """Save or update job in DB. Must be called within lock."""
        self._conn.execute(
            """
            INSERT INTO embed_jobs (
                id, status, cursor_chunk_id, items_processed, items_succeeded,
                items_failed, items_total, tokens_used, cost_usd, provider, model,
                started_at, last_activity, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                cursor_chunk_id = excluded.cursor_chunk_id,
                items_processed = excluded.items_processed,
                items_succeeded = excluded.items_succeeded,
                items_failed = excluded.items_failed,
                items_total = excluded.items_total,
                tokens_used = excluded.tokens_used,
                cost_usd = excluded.cost_usd,
                last_activity = excluded.last_activity,
                error = excluded.error
            """,
            (
                job.id,
                job.status.value,
                job.cursor_chunk_id,
                job.items_processed,
                job.items_succeeded,
                job.items_failed,
                job.items_total,
                job.tokens_used,
                job.cost_usd,
                job.provider,
                job.model,
                job.started_at.isoformat(),
                job.last_activity.isoformat(),
                job.error,
            ),
        )
        self._conn.commit()

    def get(self, job_id: str) -> EmbedJob | None:
        """Get job by ID, or None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: EmbedJob) -> None:
        """Update job in store and persist to DB."""
        job.touch()
        with self._lock:
            self._jobs[job.id] = job
            self._persist(job)

    def list_all(self) -> list[EmbedJob]:
        """List all jobs in memory, newest first."""
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.started_at,
                reverse=True,
            )

    def list_recent(self, limit: int = 10) -> list[EmbedJob]:
        """List recent jobs from DB (including completed), newest first."""
        cur = self._conn.execute(
            """
            SELECT id, status, cursor_chunk_id, items_processed, items_succeeded,
                   items_failed, items_total, tokens_used, cost_usd, provider, model,
                   started_at, last_activity, error
            FROM embed_jobs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [EmbedJob.from_row(row) for row in cur.fetchall()]

    def get_running(self) -> EmbedJob | None:
        """Get the currently running job, if any."""
        with self._lock:
            for job in self._jobs.values():
                if job.status == EmbedStatus.RUNNING:
                    return job
            return None

    def get_resumable(self) -> EmbedJob | None:
        """Get the most recent paused or failed job that can be resumed."""
        with self._lock:
            for job in sorted(
                self._jobs.values(),
                key=lambda j: j.last_activity,
                reverse=True,
            ):
                if job.status in (EmbedStatus.PAUSED, EmbedStatus.FAILED):
                    return job
            return None

    def pause(self, job_id: str) -> EmbedJob | None:
        """Pause a running job. Returns the job if paused, None otherwise."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != EmbedStatus.RUNNING:
                return None
            job.status = EmbedStatus.PAUSED
            job.touch()
            self._persist(job)
            return job

    def cancel(self, job_id: str) -> EmbedJob | None:
        """Cancel a running or pending job. Returns the job if cancelled."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if job.status not in (
                EmbedStatus.RUNNING,
                EmbedStatus.PENDING,
                EmbedStatus.PAUSED,
            ):
                return None
            job.status = EmbedStatus.CANCELLED
            job.touch()
            self._persist(job)
            return job

    def delete(self, job_id: str) -> bool:
        """Delete job by ID from memory and DB. Returns True if deleted."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
            self._conn.execute("DELETE FROM embed_jobs WHERE id = ?", (job_id,))
            self._conn.commit()
            return True
        return False


# Global store instance (set during init_db)
_embed_store: EmbedJobStore | None = None


def init_embed_store(conn: sqlite3.Connection) -> EmbedJobStore:
    """Initialize the global embed store."""
    global _embed_store
    _embed_store = EmbedJobStore(conn)
    return _embed_store


def get_embed_store() -> EmbedJobStore:
    """Get the global embed store. Must call init_embed_store first."""
    if _embed_store is None:
        raise RuntimeError("EmbedJobStore not initialized. Call init_embed_store first.")
    return _embed_store


async def run_embed_job(
    job: EmbedJob,
    db: "DB",
    store: EmbedJobStore,
    batch_size: int = 200,
) -> AsyncIterator[EmbedEvent]:
    """Run an embedding job, yielding events for SSE streaming.

    Args:
        job: The EmbedJob to run
        db: Database instance
        store: EmbedJobStore for persistence
        batch_size: Chunks to process per batch (default 200)

    Yields:
        EmbedEvent for each significant action
    """
    from app.core.embedding_providers import (
        OpenAIProvider,
        EmbeddingError,
        serialize_f32,
        OPENAI_MODELS,
    )

    # Initialize provider
    try:
        provider = OpenAIProvider(model=job.model)
    except ValueError as e:
        job.status = EmbedStatus.FAILED
        job.error = str(e)
        store.update(job)
        yield EmbedEvent(
            type=EmbedEventType.FAILED,
            job_id=job.id,
            data={"error": str(e), **job.to_dict()},
        )
        return

    # Get model info for cost calculation
    model_info = OPENAI_MODELS.get(job.model)
    cost_per_token = model_info.cost_per_1m_tokens / 1_000_000 if model_info else 0.02 / 1_000_000

    # Update job status
    job.status = EmbedStatus.RUNNING
    store.update(job)

    yield EmbedEvent(
        type=EmbedEventType.STARTED,
        job_id=job.id,
        data={"items_total": job.items_total, "provider": job.provider, "model": job.model},
    )

    try:
        while True:
            # Check if job was paused or cancelled
            current_job = store.get(job.id)
            if not current_job:
                break

            if current_job.status == EmbedStatus.PAUSED:
                yield EmbedEvent(
                    type=EmbedEventType.PAUSED,
                    job_id=job.id,
                    data=job.to_dict(),
                )
                break

            if current_job.status == EmbedStatus.CANCELLED:
                yield EmbedEvent(
                    type=EmbedEventType.CANCELLED,
                    job_id=job.id,
                    data=job.to_dict(),
                )
                break

            # Get next batch of chunks
            chunks = db.get_chunks_for_embedding(
                limit=batch_size,
                cursor_chunk_id=job.cursor_chunk_id,
                provider=job.provider,
                model=job.model,
            )

            if not chunks:
                # No more chunks to process
                job.status = EmbedStatus.COMPLETED
                store.update(job)
                yield EmbedEvent(
                    type=EmbedEventType.COMPLETED,
                    job_id=job.id,
                    data=job.to_dict(),
                )
                break

            # Extract texts for embedding
            texts = [c["chunk_text"] for c in chunks]
            batch_tokens = sum(c["token_count"] for c in chunks)

            try:
                # Call OpenAI API
                embeddings = await provider.embed(texts)

                # Prepare batch data for saving
                embeddings_data = []
                for i, chunk in enumerate(chunks):
                    embeddings_data.append({
                        "embedding": serialize_f32(embeddings[i]),
                        "chunk_id": chunk["id"],
                    })

                # Save all embeddings in single transaction
                saved_count = db.save_embeddings_batch(
                    embeddings_data=embeddings_data,
                    dimensions=provider.dimensions,
                    provider=job.provider,
                    model=job.model,
                )

                # Update job state
                job.cursor_chunk_id = chunks[-1]["id"]
                job.items_processed += len(chunks)
                job.items_succeeded += saved_count
                job.tokens_used += batch_tokens
                job.cost_usd += batch_tokens * cost_per_token
                store.update(job)

                # Yield progress event
                yield EmbedEvent(
                    type=EmbedEventType.BATCH_COMPLETE,
                    job_id=job.id,
                    data={
                        "batch_size": len(chunks),
                        "batch_tokens": batch_tokens,
                        **job.to_dict(),
                    },
                )

            except EmbeddingError as e:
                # Non-retriable error - fail the job
                if not e.retriable:
                    job.status = EmbedStatus.FAILED
                    job.error = str(e)
                    store.update(job)
                    yield EmbedEvent(
                        type=EmbedEventType.FAILED,
                        job_id=job.id,
                        data={"error": str(e), **job.to_dict()},
                    )
                    return

                # Retriable error - log and continue (provider handles retry internally)
                logger.warning(f"Embedding error (retriable): {e}")
                job.items_failed += len(chunks)
                job.items_processed += len(chunks)
                store.update(job)

    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error in embed job {job.id}")
        job.status = EmbedStatus.FAILED
        job.error = f"Unerwarteter Fehler: {e}"
        store.update(job)
        yield EmbedEvent(
            type=EmbedEventType.FAILED,
            job_id=job.id,
            data={"error": str(e), **job.to_dict()},
        )
