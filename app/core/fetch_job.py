"""Fetch job management for fulltext extraction.

Provides:
- FetchJob and FetchJobStore for job state management
- DomainRateLimiter for polite crawling
- run_fetch_job() async generator for SSE streaming
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncIterator

from app.core.content_fetcher import ContentFetcher, FetchResult, FetchErrorType

# Optional trafilatura cache reset for memory optimization
try:
    from trafilatura.meta import reset_caches as reset_trafilatura_caches
except ImportError:
    reset_trafilatura_caches = None  # type: ignore

if TYPE_CHECKING:
    from app.core.storage import DB

logger = logging.getLogger(__name__)


class FetchStatus(str, Enum):
    """Status of a fetch job."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class FetchEventType(str, Enum):
    """Types of events emitted during fetch."""

    STARTED = "started"
    PROGRESS = "progress"
    ITEM_SUCCESS = "item_success"
    ITEM_FAILED = "item_failed"
    ITEM_SKIPPED = "item_skipped"
    PAUSED = "paused"
    RESUMED = "resumed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FetchEvent:
    """Event emitted during fetch job for SSE streaming."""

    type: FetchEventType
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
class FetchJob:
    """Tracks state of a fulltext fetch job."""

    id: str
    status: FetchStatus
    cursor_doc_id: int | None = None  # Resume position
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    items_skipped: int = 0
    items_total: int | None = None
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
            "cursor_doc_id": self.cursor_doc_id,
            "items_processed": self.items_processed,
            "items_succeeded": self.items_succeeded,
            "items_failed": self.items_failed,
            "items_skipped": self.items_skipped,
            "items_total": self.items_total,
            "progress_percent": round(self.progress_percent, 1),
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "error": self.error,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> FetchJob:
        """Create FetchJob from database row."""
        return cls(
            id=row["id"],
            status=FetchStatus(row["status"]),
            cursor_doc_id=row["cursor_doc_id"],
            items_processed=row["items_processed"],
            items_succeeded=row["items_succeeded"],
            items_failed=row["items_failed"],
            items_skipped=row["items_skipped"],
            items_total=row["items_total"],
            started_at=datetime.fromisoformat(row["started_at"]),
            last_activity=datetime.fromisoformat(row["last_activity"]),
            error=row["error"],
        )


class FetchJobStore:
    """Store for FetchJobs with DB persistence. Thread-safe."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._jobs: dict[str, FetchJob] = {}
        self._lock = threading.Lock()
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load all non-completed jobs from DB into memory."""
        cur = self._conn.execute(
            """
            SELECT id, status, cursor_doc_id, items_processed, items_succeeded,
                   items_failed, items_skipped, items_total, started_at, last_activity, error
            FROM fetch_jobs
            WHERE status NOT IN ('completed')
            ORDER BY started_at DESC
            """
        )
        for row in cur.fetchall():
            job = FetchJob.from_row(row)
            self._jobs[job.id] = job

    def create(self, items_total: int | None = None) -> FetchJob:
        """Create a new pending FetchJob and persist to DB."""
        job = FetchJob(
            id=str(uuid.uuid4()),
            status=FetchStatus.PENDING,
            items_total=items_total,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._persist(job)
        return job

    def _persist(self, job: FetchJob) -> None:
        """Save or update job in DB. Must be called within lock."""
        self._conn.execute(
            """
            INSERT INTO fetch_jobs (
                id, status, cursor_doc_id, items_processed, items_succeeded,
                items_failed, items_skipped, items_total, started_at, last_activity, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                cursor_doc_id = excluded.cursor_doc_id,
                items_processed = excluded.items_processed,
                items_succeeded = excluded.items_succeeded,
                items_failed = excluded.items_failed,
                items_skipped = excluded.items_skipped,
                items_total = excluded.items_total,
                last_activity = excluded.last_activity,
                error = excluded.error
            """,
            (
                job.id,
                job.status.value,
                job.cursor_doc_id,
                job.items_processed,
                job.items_succeeded,
                job.items_failed,
                job.items_skipped,
                job.items_total,
                job.started_at.isoformat(),
                job.last_activity.isoformat(),
                job.error,
            ),
        )
        self._conn.commit()

    def get(self, job_id: str) -> FetchJob | None:
        """Get job by ID, or None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: FetchJob) -> None:
        """Update job in store and persist to DB."""
        job.touch()
        with self._lock:
            self._jobs[job.id] = job
            self._persist(job)

    def list_all(self) -> list[FetchJob]:
        """List all jobs in memory, newest first."""
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.started_at,
                reverse=True,
            )

    def list_recent(self, limit: int = 10) -> list[FetchJob]:
        """List recent jobs from DB (including completed), newest first."""
        cur = self._conn.execute(
            """
            SELECT id, status, cursor_doc_id, items_processed, items_succeeded,
                   items_failed, items_skipped, items_total, started_at, last_activity, error
            FROM fetch_jobs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [FetchJob.from_row(row) for row in cur.fetchall()]

    def get_running(self) -> FetchJob | None:
        """Get the currently running job, if any."""
        with self._lock:
            for job in self._jobs.values():
                if job.status == FetchStatus.RUNNING:
                    return job
            return None

    def get_resumable(self) -> FetchJob | None:
        """Get the most recent paused or failed job that can be resumed."""
        with self._lock:
            for job in sorted(
                self._jobs.values(),
                key=lambda j: j.last_activity,
                reverse=True,
            ):
                if job.status in (FetchStatus.PAUSED, FetchStatus.FAILED):
                    return job
            return None

    def pause(self, job_id: str) -> FetchJob | None:
        """Pause a running job. Returns the job if paused, None otherwise."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != FetchStatus.RUNNING:
                return None
            job.status = FetchStatus.PAUSED
            job.touch()
            self._persist(job)
            return job

    def cancel(self, job_id: str) -> FetchJob | None:
        """Cancel a running or pending job. Returns the job if cancelled."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if job.status not in (FetchStatus.RUNNING, FetchStatus.PENDING, FetchStatus.PAUSED):
                return None
            job.status = FetchStatus.CANCELLED
            job.touch()
            self._persist(job)
            return job

    def delete(self, job_id: str) -> bool:
        """Delete job by ID from memory and DB. Returns True if deleted."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
            cur = self._conn.execute("DELETE FROM fetch_jobs WHERE id = ?", (job_id,))
            self._conn.commit()
            return cur.rowcount > 0


class DomainRateLimiter:
    """Per-domain rate limiting with adaptive delays.

    - MIN_DELAY: Base delay between requests to same domain
    - MAX_DELAY: Maximum delay after repeated failures
    - Delays increase on failures, reset on success
    """

    MIN_DELAY = 2.0  # Seconds between requests to same domain
    MAX_DELAY = 10.0  # Maximum delay after failures
    FAILURE_MULTIPLIER = 1.5  # How much to increase delay on failure

    def __init__(self) -> None:
        self._last_request: dict[str, float] = defaultdict(float)
        self._delays: dict[str, float] = defaultdict(lambda: self.MIN_DELAY)
        self._lock = threading.Lock()

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    async def wait_for_domain(self, url: str) -> None:
        """Wait if needed before making request to this domain."""
        domain = self._get_domain(url)

        with self._lock:
            last = self._last_request[domain]
            delay = self._delays[domain]

        now = time.monotonic()
        elapsed = now - last
        wait_time = delay - elapsed

        if wait_time > 0:
            logger.debug(f"Rate limit: waiting {wait_time:.1f}s for {domain}")
            await asyncio.sleep(wait_time)

        with self._lock:
            self._last_request[domain] = time.monotonic()

    def record_success(self, url: str) -> None:
        """Record successful request - reset delay to minimum."""
        domain = self._get_domain(url)
        with self._lock:
            self._delays[domain] = self.MIN_DELAY

    def record_failure(self, url: str) -> None:
        """Record failed request - increase delay."""
        domain = self._get_domain(url)
        with self._lock:
            current = self._delays[domain]
            new_delay = min(current * self.FAILURE_MULTIPLIER, self.MAX_DELAY)
            self._delays[domain] = new_delay
            logger.debug(f"Rate limit: increased delay for {domain} to {new_delay:.1f}s")

    def get_stats(self) -> dict[str, float]:
        """Get current delay stats by domain."""
        with self._lock:
            return dict(self._delays)


async def run_fetch_job(
    job: FetchJob,
    db: "DB",
    store: FetchJobStore,
    batch_size: int = 10,
) -> AsyncIterator[FetchEvent]:
    """Run a fetch job, yielding events for SSE streaming.

    Args:
        job: The FetchJob to run
        db: Database instance
        store: FetchJobStore for persistence
        batch_size: Documents to process per batch

    Yields:
        FetchEvent for each significant action
    """
    fetcher = ContentFetcher()
    rate_limiter = DomainRateLimiter()

    # Update job status
    job.status = FetchStatus.RUNNING
    store.update(job)

    yield FetchEvent(
        type=FetchEventType.STARTED,
        job_id=job.id,
        data={"items_total": job.items_total},
    )

    try:
        while True:
            # Check if job was paused or cancelled
            current_job = store.get(job.id)
            if not current_job:
                break

            if current_job.status == FetchStatus.PAUSED:
                yield FetchEvent(
                    type=FetchEventType.PAUSED,
                    job_id=job.id,
                    data=job.to_dict(),
                )
                break

            if current_job.status == FetchStatus.CANCELLED:
                yield FetchEvent(
                    type=FetchEventType.CANCELLED,
                    job_id=job.id,
                    data=job.to_dict(),
                )
                break

            # Get next batch of documents
            docs = db.get_documents_for_fetch(
                limit=batch_size,
                cursor_doc_id=job.cursor_doc_id,
            )

            if not docs:
                # No more documents to process
                job.status = FetchStatus.COMPLETED
                store.update(job)
                yield FetchEvent(
                    type=FetchEventType.COMPLETED,
                    job_id=job.id,
                    data=job.to_dict(),
                )
                break

            # Process each document
            for doc in docs:
                doc_id = doc["id"]
                url = doc.get("url")
                title = doc.get("title", f"Document {doc_id}")

                # Update cursor
                job.cursor_doc_id = doc_id

                if not url:
                    job.items_skipped += 1
                    job.items_processed += 1
                    store.update(job)
                    yield FetchEvent(
                        type=FetchEventType.ITEM_SKIPPED,
                        job_id=job.id,
                        data={
                            "doc_id": doc_id,
                            "title": title[:50],
                            "reason": "no_url",
                            **job.to_dict(),
                        },
                    )
                    continue

                # Rate limit
                await rate_limiter.wait_for_domain(url)

                # Fetch content
                result = await fetcher.fetch(url)

                if result.success:
                    # Save fulltext
                    db.save_fulltext(doc_id, result.fulltext, source="trafilatura")
                    rate_limiter.record_success(url)

                    job.items_succeeded += 1
                    job.items_processed += 1
                    store.update(job)

                    yield FetchEvent(
                        type=FetchEventType.ITEM_SUCCESS,
                        job_id=job.id,
                        data={
                            "doc_id": doc_id,
                            "title": title[:50],
                            "char_count": result.char_count,
                            **job.to_dict(),
                        },
                    )
                else:
                    # Save failure
                    db.save_fetch_failure(
                        document_id=doc_id,
                        url=url,
                        error_type=result.error_type.value if result.error_type else "unknown",
                        error_message=result.error_message,
                        http_status=result.http_status,
                        job_id=job.id,
                    )

                    if result.retriable:
                        rate_limiter.record_failure(url)

                    job.items_failed += 1
                    job.items_processed += 1
                    store.update(job)

                    yield FetchEvent(
                        type=FetchEventType.ITEM_FAILED,
                        job_id=job.id,
                        data={
                            "doc_id": doc_id,
                            "title": title[:50],
                            "error_type": result.error_type.value if result.error_type else "unknown",
                            "error_message": result.error_message,
                            "retriable": result.retriable,
                            **job.to_dict(),
                        },
                    )

                # Yield progress event every few items
                if job.items_processed % 5 == 0:
                    yield FetchEvent(
                        type=FetchEventType.PROGRESS,
                        job_id=job.id,
                        data=job.to_dict(),
                    )

            # Clear trafilatura caches after each batch to prevent memory buildup
            if reset_trafilatura_caches is not None:
                reset_trafilatura_caches()

    except Exception as e:
        logger.exception(f"Fetch job {job.id} failed")
        job.status = FetchStatus.FAILED
        job.error = str(e)
        store.update(job)
        yield FetchEvent(
            type=FetchEventType.FAILED,
            job_id=job.id,
            data={"error": str(e), **job.to_dict()},
        )

    finally:
        await fetcher.close()


# Global store instance
_store: FetchJobStore | None = None


def init_fetch_store(conn: sqlite3.Connection) -> None:
    """Initialize the global FetchJobStore with DB connection."""
    global _store
    _store = FetchJobStore(conn)


def get_fetch_store() -> FetchJobStore:
    """Get the global FetchJobStore. Must call init_fetch_store first."""
    if _store is None:
        raise RuntimeError("FetchJobStore not initialized. Call init_fetch_store first.")
    return _store
