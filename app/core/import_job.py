"""ImportJob model and store with DB persistence for streaming imports."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.storage import DB


class ImportStatus(str, Enum):
    """Status of an import job."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ImportJob:
    """Tracks state of a streaming import from Readwise APIs."""

    id: str
    status: ImportStatus
    reader_cursor: str | None = None
    export_cursor: str | None = None
    reader_done: bool = False
    export_done: bool = False
    items_imported: int = 0
    items_merged: int = 0
    items_failed: int = 0  # Count of items that failed to process
    items_total: int | None = None  # Total from API count (Reader + Export)
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None

    def touch(self) -> None:
        """Update last_activity timestamp."""
        self.last_activity = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "reader_cursor": self.reader_cursor,
            "export_cursor": self.export_cursor,
            "reader_done": self.reader_done,
            "export_done": self.export_done,
            "items_imported": self.items_imported,
            "items_merged": self.items_merged,
            "items_failed": self.items_failed,
            "items_total": self.items_total,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "error": self.error,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ImportJob:
        """Create ImportJob from database row."""
        return cls(
            id=row["id"],
            status=ImportStatus(row["status"]),
            reader_cursor=row["reader_cursor"],
            export_cursor=row["export_cursor"],
            reader_done=bool(row["reader_done"]),
            export_done=bool(row["export_done"]),
            items_imported=row["items_imported"],
            items_merged=row["items_merged"],
            items_failed=row["items_failed"],
            items_total=row["items_total"],
            started_at=datetime.fromisoformat(row["started_at"]),
            last_activity=datetime.fromisoformat(row["last_activity"]),
            error=row["error"],
        )


class ImportJobStore:
    """Store for ImportJobs with DB persistence. Thread-safe."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._jobs: dict[str, ImportJob] = {}
        self._lock = threading.Lock()
        # Load incomplete jobs from DB on init
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load all non-completed jobs from DB into memory."""
        cur = self._conn.execute(
            """
            SELECT id, status, reader_cursor, export_cursor, reader_done, export_done,
                   items_imported, items_merged, items_failed, items_total, started_at, last_activity, error
            FROM import_jobs
            WHERE status NOT IN ('completed')
            ORDER BY started_at DESC
            """
        )
        for row in cur.fetchall():
            job = ImportJob.from_row(row)
            self._jobs[job.id] = job

    def create(self) -> ImportJob:
        """Create a new pending ImportJob and persist to DB."""
        job = ImportJob(
            id=str(uuid.uuid4()),
            status=ImportStatus.PENDING,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._persist(job)
        return job

    def _persist(self, job: ImportJob) -> None:
        """Save or update job in DB. Must be called within lock."""
        self._conn.execute(
            """
            INSERT INTO import_jobs (
                id, status, reader_cursor, export_cursor, reader_done, export_done,
                items_imported, items_merged, items_failed, items_total, started_at, last_activity, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                reader_cursor = excluded.reader_cursor,
                export_cursor = excluded.export_cursor,
                reader_done = excluded.reader_done,
                export_done = excluded.export_done,
                items_imported = excluded.items_imported,
                items_merged = excluded.items_merged,
                items_failed = excluded.items_failed,
                items_total = excluded.items_total,
                last_activity = excluded.last_activity,
                error = excluded.error
            """,
            (
                job.id,
                job.status.value,
                job.reader_cursor,
                job.export_cursor,
                int(job.reader_done),
                int(job.export_done),
                job.items_imported,
                job.items_merged,
                job.items_failed,
                job.items_total,
                job.started_at.isoformat(),
                job.last_activity.isoformat(),
                job.error,
            ),
        )
        self._conn.commit()

    def get(self, job_id: str) -> ImportJob | None:
        """Get job by ID, or None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: ImportJob) -> None:
        """Update job in store and persist to DB."""
        job.touch()
        with self._lock:
            self._jobs[job.id] = job
            self._persist(job)

    def list_all(self) -> list[ImportJob]:
        """List all jobs in memory, newest first."""
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.started_at,
                reverse=True,
            )

    def list_recent(self, limit: int = 10) -> list[ImportJob]:
        """List recent jobs from DB (including completed), newest first."""
        cur = self._conn.execute(
            """
            SELECT id, status, reader_cursor, export_cursor, reader_done, export_done,
                   items_imported, items_merged, items_failed, items_total, started_at, last_activity, error
            FROM import_jobs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [ImportJob.from_row(row) for row in cur.fetchall()]

    def get_resumable(self) -> ImportJob | None:
        """Get the most recent failed or paused job that can be resumed."""
        with self._lock:
            for job in sorted(
                self._jobs.values(),
                key=lambda j: j.last_activity,
                reverse=True,
            ):
                if job.status in (ImportStatus.FAILED, ImportStatus.PAUSED):
                    return job
            return None

    def delete(self, job_id: str) -> bool:
        """Delete job by ID from memory and DB. Returns True if deleted."""
        with self._lock:
            # Remove from memory if present
            if job_id in self._jobs:
                del self._jobs[job_id]
            # Always try to delete from DB (completed jobs are not in memory)
            cur = self._conn.execute("DELETE FROM import_jobs WHERE id = ?", (job_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def cancel(self, job_id: str) -> ImportJob | None:
        """Cancel a running or pending job. Returns the job if cancelled, None otherwise."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if job.status not in (ImportStatus.RUNNING, ImportStatus.PENDING):
                return None
            job.status = ImportStatus.CANCELLED
            job.touch()
            self._persist(job)
            return job


# Global store instance
_store: ImportJobStore | None = None


def init_import_store(conn: sqlite3.Connection) -> None:
    """Initialize the global ImportJobStore with DB connection."""
    global _store
    _store = ImportJobStore(conn)


def get_import_store() -> ImportJobStore:
    """Get the global ImportJobStore. Must call init_import_store first."""
    if _store is None:
        raise RuntimeError("ImportJobStore not initialized. Call init_import_store first.")
    return _store
