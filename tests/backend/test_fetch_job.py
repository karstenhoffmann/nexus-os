"""Tests for fetch_job.py"""

import sqlite3
import pytest
import asyncio
from datetime import datetime

from app.core.fetch_job import (
    FetchStatus,
    FetchJob,
    FetchJobStore,
    FetchEvent,
    FetchEventType,
    DomainRateLimiter,
)


@pytest.fixture
def db_conn():
    """Create in-memory SQLite connection with schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Create fetch_jobs table
    conn.execute("""
        CREATE TABLE fetch_jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            cursor_doc_id INTEGER,
            items_processed INTEGER DEFAULT 0,
            items_succeeded INTEGER DEFAULT 0,
            items_failed INTEGER DEFAULT 0,
            items_skipped INTEGER DEFAULT 0,
            items_total INTEGER,
            started_at TEXT DEFAULT (datetime('now')),
            last_activity TEXT DEFAULT (datetime('now')),
            error TEXT
        )
    """)
    conn.commit()
    return conn


class TestFetchJob:
    """Tests for FetchJob dataclass."""

    def test_create_job(self):
        job = FetchJob(
            id="test-123",
            status=FetchStatus.PENDING,
        )
        assert job.id == "test-123"
        assert job.status == FetchStatus.PENDING
        assert job.items_processed == 0

    def test_to_dict(self):
        job = FetchJob(
            id="test-123",
            status=FetchStatus.RUNNING,
            items_total=100,
            items_processed=50,
        )
        d = job.to_dict()
        assert d["id"] == "test-123"
        assert d["status"] == "running"
        assert d["progress_percent"] == 50.0

    def test_progress_percent_zero_total(self):
        job = FetchJob(
            id="test",
            status=FetchStatus.PENDING,
            items_total=0,
        )
        assert job.progress_percent == 0.0

    def test_touch_updates_last_activity(self):
        job = FetchJob(id="test", status=FetchStatus.PENDING)
        old_time = job.last_activity
        import time
        time.sleep(0.01)
        job.touch()
        assert job.last_activity > old_time


class TestFetchJobStore:
    """Tests for FetchJobStore."""

    def test_create_job(self, db_conn):
        store = FetchJobStore(db_conn)
        job = store.create(items_total=100)

        assert job.id is not None
        assert job.status == FetchStatus.PENDING
        assert job.items_total == 100

    def test_get_job(self, db_conn):
        store = FetchJobStore(db_conn)
        job = store.create()

        retrieved = store.get(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id

    def test_get_nonexistent_job(self, db_conn):
        store = FetchJobStore(db_conn)
        assert store.get("nonexistent") is None

    def test_update_job(self, db_conn):
        store = FetchJobStore(db_conn)
        job = store.create()

        job.status = FetchStatus.RUNNING
        job.items_processed = 10
        store.update(job)

        retrieved = store.get(job.id)
        assert retrieved.status == FetchStatus.RUNNING
        assert retrieved.items_processed == 10

    def test_pause_job(self, db_conn):
        store = FetchJobStore(db_conn)
        job = store.create()
        job.status = FetchStatus.RUNNING
        store.update(job)

        paused = store.pause(job.id)
        assert paused is not None
        assert paused.status == FetchStatus.PAUSED

    def test_pause_nonrunning_job(self, db_conn):
        store = FetchJobStore(db_conn)
        job = store.create()  # PENDING status

        result = store.pause(job.id)
        assert result is None  # Can't pause a pending job

    def test_cancel_job(self, db_conn):
        store = FetchJobStore(db_conn)
        job = store.create()
        job.status = FetchStatus.RUNNING
        store.update(job)

        cancelled = store.cancel(job.id)
        assert cancelled is not None
        assert cancelled.status == FetchStatus.CANCELLED

    def test_get_running(self, db_conn):
        store = FetchJobStore(db_conn)

        # No running jobs
        assert store.get_running() is None

        # Create and start a job
        job = store.create()
        job.status = FetchStatus.RUNNING
        store.update(job)

        running = store.get_running()
        assert running is not None
        assert running.id == job.id

    def test_get_resumable(self, db_conn):
        store = FetchJobStore(db_conn)

        # No resumable jobs
        assert store.get_resumable() is None

        # Create a paused job
        job = store.create()
        job.status = FetchStatus.PAUSED
        store.update(job)

        resumable = store.get_resumable()
        assert resumable is not None
        assert resumable.id == job.id

    def test_list_recent(self, db_conn):
        store = FetchJobStore(db_conn)
        store.create()
        store.create()
        store.create()

        recent = store.list_recent(limit=2)
        assert len(recent) == 2

    def test_delete_job(self, db_conn):
        store = FetchJobStore(db_conn)
        job = store.create()

        assert store.delete(job.id) is True
        assert store.get(job.id) is None

    def test_delete_nonexistent(self, db_conn):
        store = FetchJobStore(db_conn)
        assert store.delete("nonexistent") is False


class TestFetchEvent:
    """Tests for FetchEvent."""

    def test_to_sse(self):
        event = FetchEvent(
            type=FetchEventType.PROGRESS,
            job_id="test-123",
            data={"items_processed": 50},
        )
        sse = event.to_sse()
        assert "event: progress" in sse
        assert "data:" in sse
        assert "test-123" in sse
        assert sse.endswith("\n\n")


class TestDomainRateLimiter:
    """Tests for DomainRateLimiter."""

    def test_get_domain(self):
        limiter = DomainRateLimiter()
        assert limiter._get_domain("https://www.example.com/page") == "example.com"
        assert limiter._get_domain("https://sub.example.com/page") == "sub.example.com"

    def test_record_success_resets_delay(self):
        limiter = DomainRateLimiter()
        url = "https://example.com/page"

        # Increase delay by recording failures
        limiter.record_failure(url)
        limiter.record_failure(url)
        assert limiter._delays["example.com"] > limiter.MIN_DELAY

        # Success resets to minimum
        limiter.record_success(url)
        assert limiter._delays["example.com"] == limiter.MIN_DELAY

    def test_record_failure_increases_delay(self):
        limiter = DomainRateLimiter()
        url = "https://example.com/page"

        initial = limiter._delays["example.com"]
        limiter.record_failure(url)
        assert limiter._delays["example.com"] > initial

    def test_delay_capped_at_max(self):
        limiter = DomainRateLimiter()
        url = "https://example.com/page"

        # Record many failures
        for _ in range(20):
            limiter.record_failure(url)

        assert limiter._delays["example.com"] <= limiter.MAX_DELAY

    @pytest.mark.asyncio
    async def test_wait_for_domain(self):
        limiter = DomainRateLimiter()
        # Set very short delay for testing
        limiter.MIN_DELAY = 0.01
        limiter._delays["example.com"] = 0.01

        url = "https://example.com/page"

        # First request should be immediate
        start = asyncio.get_event_loop().time()
        await limiter.wait_for_domain(url)
        elapsed1 = asyncio.get_event_loop().time() - start
        assert elapsed1 < 0.1  # Should be nearly instant

        # Second request should wait
        start = asyncio.get_event_loop().time()
        await limiter.wait_for_domain(url)
        elapsed2 = asyncio.get_event_loop().time() - start
        # Should have waited some amount
        assert elapsed2 >= 0.005  # At least half the delay

    def test_get_stats(self):
        limiter = DomainRateLimiter()
        limiter.record_failure("https://slow.com/page")
        limiter.record_failure("https://fast.com/page")
        limiter.record_success("https://fast.com/page")

        stats = limiter.get_stats()
        assert "slow.com" in stats
        assert "fast.com" in stats
        assert stats["fast.com"] == limiter.MIN_DELAY
        assert stats["slow.com"] > limiter.MIN_DELAY
