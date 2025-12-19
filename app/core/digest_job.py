"""Digest generation job state and events.

This module provides job management for LLM-powered digest generation:
1. FETCH: Load chunks from date range
2. CLUSTER: Group chunks into topics (hybrid or pure LLM)
3. SUMMARIZE: Generate summaries per topic + overall
4. COMPILE: Store results in database

The structure mirrors pipeline_job.py for consistency.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DigestPhase(str, Enum):
    """Phases of digest generation."""

    IDLE = "idle"
    FETCH = "fetch"
    CLUSTER = "cluster"
    SUMMARIZE = "summarize"
    COMPILE = "compile"
    DONE = "done"


class DigestStatus(str, Enum):
    """Status of a digest job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DigestEventType(str, Enum):
    """Types of events emitted during digest generation."""

    PHASE_START = "phase_start"
    PHASE_PROGRESS = "phase_progress"
    PHASE_COMPLETE = "phase_complete"
    DIGEST_COMPLETE = "digest_complete"
    DIGEST_FAILED = "digest_failed"


@dataclass
class DigestEvent:
    """Event emitted during digest generation for SSE streaming."""

    type: DigestEventType
    phase: DigestPhase
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
class DigestJob:
    """Tracks state of a digest generation job."""

    id: str
    status: DigestStatus
    phase: DigestPhase = DigestPhase.IDLE

    # Configuration
    strategy: str = "hybrid"  # 'hybrid' or 'pure_llm'
    model: str = "gpt-4.1-mini"
    days: int = 7
    date_from: datetime | None = None
    date_to: datetime | None = None

    # Progress counters
    docs_found: int = 0
    chunks_found: int = 0
    topics_created: int = 0
    summaries_generated: int = 0

    # Token/Cost tracking
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0

    # Result
    digest_id: int | None = None  # ID in generated_digests table

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    def touch(self) -> None:
        """Update last_activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def add_tokens(self, input_tokens: int, output_tokens: int, cost: float) -> None:
        """Add token usage and cost from an LLM call."""
        self.tokens_input += input_tokens
        self.tokens_output += output_tokens
        self.cost_usd += cost

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)."""
        return self.tokens_input + self.tokens_output

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "phase": self.phase.value,
            "strategy": self.strategy,
            "model": self.model,
            "days": self.days,
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
            "docs_found": self.docs_found,
            "chunks_found": self.chunks_found,
            "topics_created": self.topics_created,
            "summaries_generated": self.summaries_generated,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "cost_usd": round(self.cost_usd, 6),
            "digest_id": self.digest_id,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "error": self.error,
        }


class DigestJobStore:
    """In-memory store for digest jobs. Thread-safe."""

    def __init__(self) -> None:
        self._jobs: dict[str, DigestJob] = {}
        self._lock = threading.Lock()

    def create(
        self,
        strategy: str = "hybrid",
        model: str = "gpt-4.1-mini",
        days: int = 7,
    ) -> DigestJob:
        """Create a new pending digest job."""
        job = DigestJob(
            id=str(uuid.uuid4()),
            status=DigestStatus.PENDING,
            strategy=strategy,
            model=model,
            days=days,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> DigestJob | None:
        """Get job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: DigestJob) -> None:
        """Update job in store."""
        job.touch()
        with self._lock:
            self._jobs[job.id] = job

    def delete(self, job_id: str) -> bool:
        """Delete job from memory."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False

    def get_running(self) -> DigestJob | None:
        """Get currently running job if any."""
        with self._lock:
            for job in self._jobs.values():
                if job.status == DigestStatus.RUNNING:
                    return job
            return None

    def list_all(self) -> list[DigestJob]:
        """List all jobs, newest first."""
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.started_at,
                reverse=True,
            )

    def list_completed(self, limit: int = 10) -> list[DigestJob]:
        """List completed jobs, newest first."""
        with self._lock:
            completed = [j for j in self._jobs.values() if j.status == DigestStatus.COMPLETED]
            return sorted(
                completed,
                key=lambda j: j.started_at,
                reverse=True,
            )[:limit]


# Global store instance
_digest_store: DigestJobStore | None = None


def get_digest_store() -> DigestJobStore:
    """Get or create the global digest store."""
    global _digest_store
    if _digest_store is None:
        _digest_store = DigestJobStore()
    return _digest_store
