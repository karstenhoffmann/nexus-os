"""ImportJob model and in-memory store for streaming imports."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ImportStatus(str, Enum):
    """Status of an import job."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
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
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "error": self.error,
        }


class ImportJobStore:
    """In-memory store for ImportJobs. Thread-safe."""

    def __init__(self) -> None:
        self._jobs: dict[str, ImportJob] = {}
        self._lock = threading.Lock()

    def create(self) -> ImportJob:
        """Create a new pending ImportJob."""
        job = ImportJob(
            id=str(uuid.uuid4()),
            status=ImportStatus.PENDING,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> ImportJob | None:
        """Get job by ID, or None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: ImportJob) -> None:
        """Update job in store."""
        job.touch()
        with self._lock:
            self._jobs[job.id] = job

    def list_all(self) -> list[ImportJob]:
        """List all jobs, newest first."""
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.started_at,
                reverse=True,
            )

    def delete(self, job_id: str) -> bool:
        """Delete job by ID. Returns True if deleted."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False


# Global store instance
_store: ImportJobStore | None = None


def get_import_store() -> ImportJobStore:
    """Get or create the global ImportJobStore."""
    global _store
    if _store is None:
        _store = ImportJobStore()
    return _store
