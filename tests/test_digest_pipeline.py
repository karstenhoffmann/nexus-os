"""Tests for digest_pipeline.py."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.digest_pipeline import (
    run_digest_pipeline,
    estimate_digest,
    _fetch_phase,
    _cluster_phase,
    _summarize_phase,
    _compile_phase,
)
from app.core.digest_job import (
    DigestJob,
    DigestStatus,
    DigestPhase,
    DigestEventType,
    get_digest_store,
)
from app.core.digest_clustering import ClusteringResult, TopicCluster


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = MagicMock()
    db.get_chunk_embeddings_in_date_range.return_value = [
        {
            "id": 1,
            "document_id": 100,
            "chunk_index": 0,
            "chunk_text": "Test content about AI",
            "token_count": 10,
            "title": "AI Article",
            "author": "Author",
            "category": "article",
            "saved_at": "2025-12-15",
            "embedding": [0.1] * 1536,
        },
        {
            "id": 2,
            "document_id": 100,
            "chunk_index": 1,
            "chunk_text": "More content about machine learning",
            "token_count": 12,
            "title": "AI Article",
            "author": "Author",
            "category": "article",
            "saved_at": "2025-12-15",
            "embedding": [0.2] * 1536,
        },
        {
            "id": 3,
            "document_id": 101,
            "chunk_index": 0,
            "chunk_text": "Content about productivity",
            "token_count": 8,
            "title": "Productivity Tips",
            "author": "Writer",
            "category": "article",
            "saved_at": "2025-12-16",
            "embedding": [0.3] * 1536,
        },
    ]
    db.get_chunks_in_date_range.return_value = db.get_chunk_embeddings_in_date_range.return_value
    db.save_generated_digest.return_value = 42
    return db


@pytest.fixture
def mock_llm():
    """Create a mock LLM provider."""
    llm = MagicMock()
    llm.model_id = "gpt-4.1-mini"
    llm.cost_per_1m_input = 0.40
    llm.cost_per_1m_output = 1.60

    async def mock_chat(messages, temperature=0.7, max_tokens=None):
        response = MagicMock()
        response.content = '{"topic_name": "Test Topic", "summary": "Test summary", "key_points": ["Point 1"]}'
        response.tokens_input = 100
        response.tokens_output = 50
        return response

    llm.chat = mock_chat
    llm.estimate_cost.return_value = 0.0001
    return llm


@pytest.fixture
def digest_job():
    """Create a test digest job."""
    store = get_digest_store()
    return store.create(strategy="hybrid", model="gpt-4.1-mini", days=7)


class TestFetchPhase:
    """Tests for the fetch phase."""

    @pytest.mark.asyncio
    async def test_fetch_phase_returns_chunks_and_count(self, mock_db, digest_job):
        """Test that fetch phase returns chunks and document count."""
        store = get_digest_store()
        digest_job.date_from = datetime(2025, 12, 12, tzinfo=timezone.utc)
        digest_job.date_to = datetime(2025, 12, 19, tzinfo=timezone.utc)

        chunks, doc_count = await _fetch_phase(digest_job, mock_db, store)

        assert len(chunks) == 3
        assert doc_count == 2  # 2 unique documents
        assert digest_job.phase == DigestPhase.FETCH
        assert digest_job.chunks_found == 3
        assert digest_job.docs_found == 2

    @pytest.mark.asyncio
    async def test_fetch_phase_uses_embeddings_for_hybrid(self, mock_db, digest_job):
        """Test that hybrid strategy fetches embeddings."""
        store = get_digest_store()
        digest_job.strategy = "hybrid"
        digest_job.date_from = datetime(2025, 12, 12, tzinfo=timezone.utc)
        digest_job.date_to = datetime(2025, 12, 19, tzinfo=timezone.utc)

        await _fetch_phase(digest_job, mock_db, store)

        mock_db.get_chunk_embeddings_in_date_range.assert_called_once()
        mock_db.get_chunks_in_date_range.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_phase_uses_chunks_for_pure_llm(self, mock_db, digest_job):
        """Test that pure_llm strategy fetches chunks without embeddings."""
        store = get_digest_store()
        digest_job.strategy = "pure_llm"
        digest_job.date_from = datetime(2025, 12, 12, tzinfo=timezone.utc)
        digest_job.date_to = datetime(2025, 12, 19, tzinfo=timezone.utc)

        await _fetch_phase(digest_job, mock_db, store)

        mock_db.get_chunks_in_date_range.assert_called_once()


class TestClusterPhase:
    """Tests for the cluster phase."""

    @pytest.mark.asyncio
    async def test_cluster_phase_tracks_tokens(self, mock_llm, digest_job):
        """Test that cluster phase tracks token usage."""
        store = get_digest_store()
        chunks = [
            {"id": i, "chunk_text": f"Text {i}", "title": f"Doc {i}", "embedding": [0.1] * 1536}
            for i in range(10)
        ]

        with patch("app.core.digest_pipeline.cluster_chunks") as mock_cluster:
            mock_cluster.return_value = ClusteringResult(
                strategy="hybrid",
                clusters=[
                    TopicCluster(
                        topic_index=0,
                        topic_name="Test Topic",
                        summary="Summary",
                        chunk_ids=[1, 2, 3],
                    )
                ],
                tokens_input=200,
                tokens_output=100,
                cost_usd=0.001,
            )

            result = await _cluster_phase(digest_job, chunks, mock_llm, store)

            assert digest_job.tokens_input == 200
            assert digest_job.tokens_output == 100
            assert digest_job.topics_created == 1


class TestSummarizePhase:
    """Tests for the summarize phase."""

    @pytest.mark.asyncio
    async def test_summarize_phase_generates_summary(self, mock_llm, digest_job):
        """Test that summarize phase generates summary and highlights."""
        store = get_digest_store()
        clustering_result = ClusteringResult(
            strategy="hybrid",
            clusters=[
                TopicCluster(
                    topic_index=0,
                    topic_name="AI Trends",
                    summary="AI is evolving",
                    chunk_ids=[1, 2],
                    key_points=["Point 1", "Point 2"],
                )
            ],
        )

        # Mock the LLM response for summary
        async def mock_chat(messages, temperature=0.7, max_tokens=None):
            response = MagicMock()
            response.content = '{"summary": "This week was about AI", "highlights": ["AI is growing", "ML is important"]}'
            response.tokens_input = 150
            response.tokens_output = 75
            return response

        mock_llm.chat = mock_chat

        summary, highlights = await _summarize_phase(
            digest_job, clustering_result, mock_llm, store
        )

        assert "AI" in summary
        assert len(highlights) == 2
        assert digest_job.summaries_generated == 1


class TestCompilePhase:
    """Tests for the compile phase."""

    @pytest.mark.asyncio
    async def test_compile_phase_saves_digest(self, mock_db, digest_job):
        """Test that compile phase saves digest to database."""
        store = get_digest_store()
        digest_job.date_from = datetime(2025, 12, 12, tzinfo=timezone.utc)
        digest_job.date_to = datetime(2025, 12, 19, tzinfo=timezone.utc)
        digest_job.docs_found = 5
        digest_job.chunks_found = 50
        digest_job.tokens_input = 1000
        digest_job.tokens_output = 500
        digest_job.cost_usd = 0.01

        clustering_result = ClusteringResult(
            strategy="hybrid",
            clusters=[
                TopicCluster(
                    topic_index=0,
                    topic_name="Test",
                    summary="Summary",
                    chunk_ids=[1],
                )
            ],
        )

        digest_id = await _compile_phase(
            digest_job,
            mock_db,
            clustering_result,
            "Overall summary text",
            ["Highlight 1", "Highlight 2"],
            store,
        )

        assert digest_id == 42
        mock_db.save_generated_digest.assert_called_once()
        call_kwargs = mock_db.save_generated_digest.call_args.kwargs
        assert call_kwargs["docs_analyzed"] == 5
        assert call_kwargs["chunks_analyzed"] == 50
        assert "2025-12-12" in call_kwargs["date_from"]


class TestEstimateDigest:
    """Tests for the estimate_digest function."""

    @pytest.mark.asyncio
    async def test_estimate_digest_returns_cost(self, mock_db):
        """Test that estimate_digest returns cost estimate."""
        result = await estimate_digest(days=7, db=mock_db, model="gpt-4.1-mini")

        assert result["days"] == 7
        assert result["chunks_count"] == 3
        assert result["docs_count"] == 2
        assert "total_cost_usd" in result


class TestRunDigestPipeline:
    """Integration tests for the full pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_emits_events(self, mock_db, digest_job):
        """Test that pipeline emits events for each phase."""
        with patch("app.core.digest_pipeline.get_chat_provider") as mock_provider:
            mock_llm = MagicMock()
            mock_llm.model_id = "gpt-4.1-mini"

            async def mock_chat(messages, temperature=0.7, max_tokens=None):
                response = MagicMock()
                response.content = '{"topic_name": "Test", "summary": "Summary", "key_points": []}'
                response.tokens_input = 100
                response.tokens_output = 50
                return response

            mock_llm.chat = mock_chat
            mock_llm.estimate_cost.return_value = 0.0001
            mock_provider.return_value = mock_llm

            with patch("app.core.digest_pipeline.cluster_chunks") as mock_cluster:
                mock_cluster.return_value = ClusteringResult(
                    strategy="hybrid",
                    clusters=[
                        TopicCluster(
                            topic_index=0,
                            topic_name="Test",
                            summary="Summary",
                            chunk_ids=[1],
                        )
                    ],
                    tokens_input=100,
                    tokens_output=50,
                    cost_usd=0.001,
                )

                events = []
                async for event in run_digest_pipeline(digest_job, mock_db):
                    events.append(event)

                # Should have events for each phase + final
                event_types = [e.type for e in events]
                assert DigestEventType.PHASE_COMPLETE in event_types
                assert DigestEventType.DIGEST_COMPLETE in event_types

                # Job should be completed
                assert digest_job.status == DigestStatus.COMPLETED
                assert digest_job.digest_id == 42
