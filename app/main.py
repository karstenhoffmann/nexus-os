from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.settings import Settings
from app.core.storage import get_db, init_db
from app.core.import_job import ImportStatus, get_import_store
from app.core.fetch_job import (
    FetchStatus,
    get_fetch_store,
    run_fetch_job,
)
from app.core.embed_job import generate_embeddings_batch, generate_embeddings_v2, generate_chunk_embeddings_v2
from app.core.chunking import get_chunking_info, chunk_document
from app.core.embeddings import get_embedding, serialize_f32
from app.core.embedding_providers import (
    get_provider,
    get_all_models,
    OpenAIProvider,
    OllamaProvider,
    EmbeddingError,
)
from app.providers.readwise import ImportEventType, ReadwiseAuthError, ReadwiseClient

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

jinja = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

app = FastAPI(title="nexus-os")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def _startup() -> None:
    init_db()


def render(template_name: str, **ctx) -> HTMLResponse:
    template = jinja.get_template(template_name)
    return HTMLResponse(template.render(**ctx))


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    s = Settings.from_env()
    return render("home.html", request=request, settings=s)


@app.get("/library", response_class=HTMLResponse)
async def library(request: Request, q: str = "", mode: str = "fts"):
    """Library search with FTS or semantic mode.

    Args:
        q: Search query
        mode: 'fts' for full-text search, 'semantic' for vector similarity
    """
    db = get_db()

    if not q or not q.strip():
        rows = db.search_documents("")
        return render("library.html", request=request, q=q, rows=rows, mode=mode)

    if mode == "semantic":
        try:
            query_embedding = await get_embedding(q.strip())
            embedding_bytes = serialize_f32(query_embedding)
            # Try chunk-based search first (includes citations and context)
            rows = db.semantic_search_with_chunks(
                embedding_bytes,
                dimensions=1536,  # OpenAI text-embedding-3-small
                limit=50,
                include_context=True,
            )
        except Exception as e:
            # Fallback to FTS on error
            rows = db.search_documents(q)
            mode = "fts"
    else:
        rows = db.search_documents(q)

    return render("library.html", request=request, q=q, rows=rows, mode=mode)


@app.get("/documents/{doc_id}", response_class=HTMLResponse)
def document_detail(request: Request, doc_id: int):
    """Show a single document with its highlights from the DB."""
    db = get_db()
    doc = db.get_document(doc_id)
    if not doc:
        return render("document_detail.html", request=request, doc=None, highlights=[], error="Dokument nicht gefunden")
    highlights = db.get_highlights_for_document(doc_id)
    return render("document_detail.html", request=request, doc=doc, highlights=highlights, error=None)


@app.get("/digests", response_class=HTMLResponse)
def digests(request: Request):
    db = get_db()
    digests = db.list_digests()
    return render("digests.html", request=request, digests=digests)


@app.post("/digests/create")
def digests_create(name: str = Form(...), query: str = Form(...)):
    db = get_db()
    db.create_digest(name=name, query=query)
    return RedirectResponse(url="/digests", status_code=303)


@app.get("/drafts", response_class=HTMLResponse)
def drafts(request: Request):
    db = get_db()
    drafts = db.list_drafts()
    return render("drafts.html", request=request, drafts=drafts)


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    s = Settings.from_env()
    db = get_db()
    stats = db.get_stats()
    embedding_stats = db.get_embedding_stats()
    return render("admin.html", request=request, settings=s, stats=stats, embedding_stats=embedding_stats)


@app.get("/admin/compare", response_class=HTMLResponse)
def admin_compare(request: Request):
    """Model comparison page for side-by-side embedding provider testing."""
    return render("admin_compare.html", request=request)


@app.get("/api/compare/search")
async def api_compare_search(q: str, provider: str = "openai", limit: int = 5):
    """Search using a specific provider for comparison.

    Args:
        q: Search query
        provider: 'openai' or 'ollama'
        limit: Maximum results (default 5)

    Returns:
        Search results with timing and cost info
    """
    import time

    if not q or not q.strip():
        return {"error": "Query is required", "results": []}

    try:
        embed_provider = get_provider(provider)

        # Get query embedding
        start = time.monotonic()
        query_embedding = await embed_provider.embed_single(q.strip())
        embed_time = time.monotonic() - start

        # Serialize and search
        embedding_bytes = serialize_f32(query_embedding)
        db = get_db()

        # Search using the legacy table (all docs have embeddings there)
        search_start = time.monotonic()
        results = db.semantic_search(embedding_bytes, limit=limit)
        search_time = time.monotonic() - search_start

        total_latency = int((embed_time + search_time) * 1000)

        # Estimate cost
        token_estimate = len(q) // 4
        cost_usd = embed_provider.estimate_cost(token_estimate)

        # Build response first (before any more DB operations)
        response = {
            "provider": embed_provider.name,
            "model": embed_provider.model_id,
            "results": results,
            "latency_ms": total_latency,
            "cost_usd": cost_usd,
            "query": q,
        }

        # Track usage (non-critical, wrapped in try/except)
        try:
            db.log_api_usage(
                provider=embed_provider.name.lower(),
                model=embed_provider.model_id,
                operation="compare_search",
                tokens_input=token_estimate,
                cost_usd=cost_usd,
                latency_ms=total_latency,
                success=True,
            )
        except Exception as log_err:
            # Don't fail the search if logging fails
            import logging
            logging.warning(f"Failed to log usage: {log_err}")

        return response

    except EmbeddingError as e:
        return {
            "provider": provider,
            "model": "unknown",
            "results": [],
            "error": str(e),
            "latency_ms": 0,
            "cost_usd": 0,
        }

    except Exception as e:
        return {
            "provider": provider,
            "model": "unknown",
            "results": [],
            "error": str(e),
            "latency_ms": 0,
            "cost_usd": 0,
        }


@app.post("/admin/embeddings/generate")
async def admin_generate_embeddings(limit: int = 100):
    """Generate embeddings for documents that don't have them yet.

    This is an async endpoint that processes up to `limit` documents.
    For 2600+ documents, call multiple times or use a larger limit.

    Returns: {"processed": int, "failed": int, "remaining": int}
    """
    result = await generate_embeddings_batch(limit=limit)
    return result


@app.get("/admin/embeddings/stats")
def admin_embedding_stats():
    """Get current embedding statistics."""
    db = get_db()
    return db.get_embedding_stats()


@app.post("/admin/fts/rebuild")
def admin_fts_rebuild():
    """Rebuild the FTS index from documents table.

    Should be called after fulltext fetch to update search.

    Returns:
        Dict with count of indexed documents
    """
    db = get_db()
    count = db.rebuild_fts()
    return {"indexed": count, "message": f"FTS Index rebuilt with {count} documents"}


@app.get("/api/providers/health")
async def api_providers_health():
    """Check health of all embedding providers.

    Returns status for both OpenAI and Ollama providers.
    Useful for admin UI to show which providers are available.
    """
    results = []

    # Check OpenAI
    try:
        openai_provider = OpenAIProvider()
        openai_health = await openai_provider.health_check()
        results.append({
            "provider": openai_health.provider,
            "model": openai_health.model,
            "healthy": openai_health.healthy,
            "message": openai_health.message,
            "latency_ms": openai_health.latency_ms,
            "details": openai_health.details,
        })
    except Exception as e:
        results.append({
            "provider": "OpenAI",
            "model": "text-embedding-3-small",
            "healthy": False,
            "message": str(e),
        })

    # Check Ollama
    try:
        ollama_provider = OllamaProvider()
        ollama_health = await ollama_provider.health_check()
        results.append({
            "provider": ollama_health.provider,
            "model": ollama_health.model,
            "healthy": ollama_health.healthy,
            "message": ollama_health.message,
            "latency_ms": ollama_health.latency_ms,
            "details": ollama_health.details,
        })
    except Exception as e:
        results.append({
            "provider": "Ollama",
            "model": "nomic-embed-text",
            "healthy": False,
            "message": str(e),
        })

    return {"providers": results}


@app.get("/api/providers/models")
def api_providers_models():
    """Get all available embedding models grouped by provider.

    Returns model details including dimensions, costs, and descriptions.
    """
    all_models = get_all_models()
    result = {}

    for provider_name, models in all_models.items():
        result[provider_name] = [
            {
                "model_id": info.model_id,
                "dimensions": info.dimensions,
                "cost_per_1m_tokens": info.cost_per_1m_tokens,
                "max_tokens": info.max_tokens,
                "description": info.description,
            }
            for info in models.values()
        ]

    return {"models": result}


@app.get("/api/providers/{provider}/health")
async def api_provider_health(provider: str, model: str | None = None):
    """Check health of a specific provider.

    Args:
        provider: 'openai' or 'ollama'
        model: Optional specific model to check
    """
    try:
        embed_provider = get_provider(provider, model)
        health = await embed_provider.health_check()
        return {
            "provider": health.provider,
            "model": health.model,
            "healthy": health.healthy,
            "message": health.message,
            "latency_ms": health.latency_ms,
            "details": health.details,
        }
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": str(e)}, 500


# ==================== V2 Embedding Endpoints ====================


@app.post("/api/embeddings/generate")
async def api_generate_embeddings(
    provider: str | None = None,
    model: str | None = None,
    limit: int = 100,
    include_chunks: bool = False,
):
    """Generate embeddings for documents using the specified provider.

    Args:
        provider: 'openai' or 'ollama' (uses default from settings if not specified)
        model: Model ID (uses provider default if not specified)
        limit: Maximum documents to process (default 100)
        include_chunks: Also generate chunk-level embeddings (default False)

    Returns:
        Dict with processed, failed, chunks_processed, cost_usd, provider, model
    """
    result = await generate_embeddings_v2(
        provider_name=provider,
        model=model,
        limit=limit,
        include_chunks=include_chunks,
    )
    return result


@app.post("/api/embeddings/generate-chunks")
async def api_generate_chunk_embeddings(
    provider: str | None = None,
    model: str | None = None,
    limit: int = 300,
):
    """Generate embeddings for document chunks.

    First creates chunks for documents that don't have them,
    then generates embeddings for chunks without embeddings.

    Args:
        provider: 'openai' or 'ollama'
        model: Model ID
        limit: Maximum chunks to process (default 300)

    Returns:
        Dict with processed, failed, chunks_created, cost_usd
    """
    result = await generate_chunk_embeddings_v2(
        provider_name=provider,
        model=model,
        limit=limit,
    )
    return result


@app.get("/api/embeddings/stats")
def api_embedding_stats_v2():
    """Get detailed embedding statistics by provider/model."""
    db = get_db()
    return db.get_embedding_stats_v2()


@app.post("/api/chunks/generate")
def api_generate_chunks_only(limit: int = 500):
    """Create chunks for documents with fulltext (without generating embeddings).

    This is a synchronous operation that avoids SQLite concurrency issues.

    Args:
        limit: Maximum documents to process (default 500)

    Returns:
        Dict with chunks_created, documents_processed counts
    """
    db = get_db()

    cur = db.conn.execute(
        """
        SELECT d.id, d.title, d.fulltext
        FROM documents d
        LEFT JOIN document_chunks c ON c.document_id = d.id
        WHERE c.id IS NULL AND d.fulltext IS NOT NULL AND d.fulltext != ''
        LIMIT ?
        """,
        (limit,),
    )
    docs_to_chunk = cur.fetchall()

    chunks_created = 0
    documents_processed = 0

    for doc_id, title, fulltext in docs_to_chunk:
        if not fulltext:
            continue
        chunks = chunk_document(fulltext, title or "")
        if chunks:
            db.save_chunks(doc_id, [c.to_dict() for c in chunks])
            chunks_created += len(chunks)
            documents_processed += 1

    # Get remaining count
    remaining = db.conn.execute(
        """
        SELECT COUNT(*)
        FROM documents d
        LEFT JOIN document_chunks c ON c.document_id = d.id
        WHERE c.id IS NULL AND d.fulltext IS NOT NULL AND d.fulltext != ''
        """
    ).fetchone()[0]

    return {
        "chunks_created": chunks_created,
        "documents_processed": documents_processed,
        "remaining_documents": remaining,
    }


@app.get("/api/chunking/info")
def api_chunking_info():
    """Get information about chunking parameters."""
    return get_chunking_info()


@app.get("/api/chunking/unchunked")
def api_unchunked_documents():
    """Get documents with fulltext that don't have chunks (for diagnostics)."""
    db = get_db()
    cur = db.conn.execute(
        """
        SELECT d.id, d.title, length(d.fulltext) as fulltext_length
        FROM documents d
        LEFT JOIN document_chunks c ON c.document_id = d.id
        WHERE c.id IS NULL AND d.fulltext IS NOT NULL AND d.fulltext != ''
        ORDER BY fulltext_length ASC
        LIMIT 20
        """
    )
    docs = [
        {"id": row[0], "title": row[1], "fulltext_length": row[2]}
        for row in cur.fetchall()
    ]
    return {
        "count": len(docs),
        "min_chunk_size_required": 100,
        "documents": docs,
        "explanation": "Documents shorter than 100 characters cannot be chunked (intentional)",
    }


@app.get("/api/usage/stats")
def api_usage_stats(period: str = "today"):
    """Get API usage statistics.

    Args:
        period: 'today', 'week', 'month', or 'all'
    """
    db = get_db()
    return db.get_usage_stats(period)


@app.get("/api/semantic-search")
async def api_semantic_search(q: str, limit: int = 10):
    """Search documents by semantic similarity.

    Args:
        q: Search query text
        limit: Maximum results (default 10)

    Returns:
        List of documents with similarity scores
    """
    if not q or not q.strip():
        return {"results": [], "error": "Query is required"}

    try:
        # Get embedding for query
        query_embedding = await get_embedding(q.strip())
        embedding_bytes = serialize_f32(query_embedding)

        # Search
        db = get_db()
        results = db.semantic_search(embedding_bytes, limit=limit)

        return {"results": results, "query": q}
    except Exception as e:
        return {"results": [], "error": str(e)}


# ==================== Fetch API Endpoints ====================


@app.get("/admin/fetch", response_class=HTMLResponse)
def admin_fetch(request: Request):
    """Fulltext fetch management page."""
    db = get_db()
    store = get_fetch_store()

    stats = db.count_documents_for_fetch()
    jobs = store.list_recent(limit=10)
    running_job = store.get_running()
    resumable_job = store.get_resumable()
    failure_summary = db.get_failure_summary()

    return render(
        "admin_fetch.html",
        request=request,
        stats=stats,
        jobs=jobs,
        running_job=running_job,
        resumable_job=resumable_job,
        failure_summary=failure_summary,
    )


@app.post("/api/fetch/start")
def api_fetch_start():
    """Start a new fulltext fetch job.

    Returns job ID for SSE stream connection.
    """
    db = get_db()
    store = get_fetch_store()

    # Check if a job is already running
    running = store.get_running()
    if running:
        return {"error": "A fetch job is already running", "job_id": running.id}

    # Get total count for progress tracking
    stats = db.count_documents_for_fetch()
    job = store.create(items_total=stats["pending"])

    return {"job_id": job.id, "items_total": stats["pending"]}


@app.post("/api/fetch/{job_id}/pause")
def api_fetch_pause(job_id: str):
    """Pause a running fetch job."""
    store = get_fetch_store()
    job = store.pause(job_id)

    if not job:
        return {"error": "Job not found or not running"}

    return {"status": job.status.value, "job": job.to_dict()}


@app.post("/api/fetch/{job_id}/resume")
def api_fetch_resume(job_id: str):
    """Resume a paused fetch job.

    Client should reconnect to SSE stream after calling this.
    """
    store = get_fetch_store()
    job = store.get(job_id)

    if not job:
        return {"error": "Job not found"}

    if job.status not in (FetchStatus.PAUSED, FetchStatus.FAILED):
        return {"error": f"Job cannot be resumed (status: {job.status.value})"}

    # Set to pending, will become running when stream starts
    job.status = FetchStatus.PENDING
    store.update(job)

    return {"status": job.status.value, "job": job.to_dict()}


@app.post("/api/fetch/{job_id}/cancel")
def api_fetch_cancel(job_id: str):
    """Cancel a fetch job."""
    store = get_fetch_store()
    job = store.cancel(job_id)

    if not job:
        return {"error": "Job not found or cannot be cancelled"}

    return {"status": job.status.value, "job": job.to_dict()}


@app.get("/api/fetch/{job_id}/status")
def api_fetch_status(job_id: str):
    """Get current status of a fetch job."""
    store = get_fetch_store()
    job = store.get(job_id)

    if not job:
        return {"error": "Job not found"}

    return job.to_dict()


@app.get("/api/fetch/{job_id}/stream")
async def api_fetch_stream(job_id: str):
    """SSE stream for fetch progress.

    Connect after starting or resuming a job to receive live updates.
    """
    store = get_fetch_store()
    job = store.get(job_id)

    if not job:
        return {"error": "Job not found"}

    if job.status not in (FetchStatus.PENDING, FetchStatus.RUNNING):
        return {"error": f"Job is not active (status: {job.status.value})"}

    db = get_db()

    async def event_generator():
        """Generate SSE events from fetch job."""
        try:
            async for event in run_fetch_job(job, db, store):
                yield event.to_sse()
        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/fetch/stats")
def api_fetch_stats():
    """Get fetch statistics.

    Returns counts of documents with/without fulltext, pending, failed.
    """
    db = get_db()
    stats = db.count_documents_for_fetch()
    failure_summary = db.get_failure_summary()

    return {
        **stats,
        "failures_by_type": failure_summary,
    }


@app.get("/api/fetch/failures")
def api_fetch_failures(error_type: str | None = None, limit: int = 100):
    """Get list of fetch failures.

    Args:
        error_type: Filter by error type (timeout, http_4xx, paywall, etc.)
        limit: Maximum results (default 100)
    """
    db = get_db()
    failures = db.get_fetch_failures(error_type=error_type, limit=limit)

    return {"failures": failures, "count": len(failures)}


@app.post("/api/fetch/retry-failed")
def api_fetch_retry_failed():
    """Clear retryable failures (timeout, http_5xx) so they can be fetched again.

    Returns number of failures cleared.
    """
    db = get_db()
    cleared = db.clear_retryable_failures()

    return {"cleared": cleared, "message": f"Cleared {cleared} retryable failures"}


@app.get("/api/fetch/jobs")
def api_fetch_jobs(limit: int = 10):
    """Get list of recent fetch jobs."""
    store = get_fetch_store()
    jobs = store.list_recent(limit=limit)

    return {"jobs": [j.to_dict() for j in jobs]}


@app.delete("/api/fetch/{job_id}")
def api_fetch_delete(job_id: str):
    """Delete a fetch job (only if not running)."""
    store = get_fetch_store()
    job = store.get(job_id)

    if job and job.status == FetchStatus.RUNNING:
        return {"error": "Cannot delete a running job"}

    deleted = store.delete(job_id)

    return {"deleted": deleted}


# ==================== Readwise Routes ====================


@app.get("/readwise/preview", response_class=HTMLResponse)
def readwise_preview(request: Request, token: str | None = None):
    s = Settings.from_env()
    effective_token = token or s.readwise_api_token
    if not effective_token:
        return render("readwise_preview.html", request=request, token=None, articles=[], error=None, token_param="")
    return _fetch_readwise_preview(request, effective_token)


@app.post("/readwise/preview", response_class=HTMLResponse)
def readwise_preview_post(request: Request, token: str = Form(...)):
    return _fetch_readwise_preview(request, token)


def _fetch_readwise_preview(request: Request, token: str) -> HTMLResponse:
    """Fetch articles from Readwise and render preview."""
    try:
        with ReadwiseClient(token) as client:
            client.validate_token()
            articles = list(client.fetch_documents(limit=20))
    except ReadwiseAuthError as e:
        return render("readwise_preview.html", request=request, token=None, articles=[], error=str(e), token_param="")
    except Exception as e:
        return render("readwise_preview.html", request=request, token=None, articles=[], error=f"Fehler: {e}", token_param="")
    return render("readwise_preview.html", request=request, token=token, articles=articles, error=None, token_param=token)


@app.get("/readwise/article/{article_id}", response_class=HTMLResponse)
def readwise_article(request: Request, article_id: str, token: str | None = None):
    """Show a single article with its highlights."""
    s = Settings.from_env()
    effective_token = token or s.readwise_api_token
    if not effective_token:
        return render("readwise_article.html", request=request, article=None, highlights=[], error="Kein Token vorhanden", token_param="")

    try:
        with ReadwiseClient(effective_token) as client:
            # Fetch the specific article
            article = None
            for doc in client.fetch_documents(with_html_content=True, limit=100):
                if doc.provider_id == article_id:
                    article = doc
                    break

            if not article:
                return render("readwise_article.html", request=request, article=None, highlights=[], error="Artikel nicht gefunden", token_param=effective_token)

            # Fetch highlights for this article
            highlights = client.fetch_highlights_for_article(article_id)

    except ReadwiseAuthError as e:
        return render("readwise_article.html", request=request, article=None, highlights=[], error=str(e), token_param="")
    except Exception as e:
        return render("readwise_article.html", request=request, article=None, highlights=[], error=f"Fehler: {e}", token_param="")

    return render("readwise_article.html", request=request, article=article, highlights=highlights, error=None, token_param=effective_token)


# --- Readwise Import Routes ---


@app.get("/readwise/import", response_class=HTMLResponse)
def readwise_import_page(request: Request):
    """Show import page with current/recent jobs."""
    s = Settings.from_env()
    store = get_import_store()
    jobs = store.list_recent(limit=10)
    resumable_job = store.get_resumable()
    return render(
        "readwise_import.html",
        request=request,
        token=s.readwise_api_token,
        jobs=jobs,
        resumable_job=resumable_job,
    )


@app.post("/readwise/import/start")
def readwise_import_start(token: str = Form(...)):
    """Start a new import job. Returns job ID for SSE stream."""
    store = get_import_store()
    job = store.create()
    # Store token temporarily in job for the stream to use
    # (In production, you'd want a more secure approach)
    job._token = token  # type: ignore[attr-defined]
    store.update(job)
    return {"job_id": job.id}


@app.post("/readwise/import/{job_id}/pause")
def readwise_import_pause(job_id: str):
    """Pause a running import job."""
    store = get_import_store()
    job = store.get(job_id)
    if not job:
        return {"error": "Job not found"}, 404
    if job.status == ImportStatus.RUNNING:
        job.status = ImportStatus.PAUSED
        store.update(job)
    return {"status": job.status.value}


@app.post("/readwise/import/{job_id}/resume")
def readwise_import_resume(job_id: str):
    """Resume a paused import job. Client should reconnect to SSE stream."""
    store = get_import_store()
    job = store.get(job_id)
    if not job:
        return {"error": "Job not found"}, 404
    if job.status == ImportStatus.PAUSED:
        job.status = ImportStatus.PENDING  # Will be set to RUNNING when stream starts
        store.update(job)
    return {"status": job.status.value}


@app.get("/readwise/import/{job_id}/stream")
def readwise_import_stream(job_id: str, token: str | None = None):
    """SSE stream for import progress. Connect after starting or resuming."""
    store = get_import_store()
    job = store.get(job_id)
    if not job:
        return {"error": "Job not found"}, 404

    s = Settings.from_env()
    effective_token = token or getattr(job, "_token", None) or s.readwise_api_token
    if not effective_token:
        return {"error": "No token available"}, 400

    def event_generator():
        """Generate SSE events from import stream."""
        db = get_db()
        try:
            with ReadwiseClient(effective_token) as client:
                url_index: dict[str, str] = {}
                for event in client.stream_import(job, url_index=url_index):
                    store.update(job)

                    # Persist article to DB on ITEM events
                    if event.type == ImportEventType.ITEM:
                        article_data = event.data.get("article", {})
                        if article_data.get("provider_id"):
                            html_content = article_data.get("html_content")
                            doc_id = db.save_article(
                                source=article_data.get("provider", "unknown"),
                                provider_id=article_data.get("provider_id", ""),
                                url_original=article_data.get("source_url"),
                                title=article_data.get("title"),
                                author=article_data.get("author"),
                                published_at=article_data.get("published_date"),
                                fulltext=html_content,
                                fulltext_source="readwise" if html_content else None,
                                summary=article_data.get("summary"),
                            )

                            # Save highlights if present (from Export API)
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

                    # Rebuild FTS index after import completes
                    if event.type == ImportEventType.COMPLETED:
                        fts_count = db.rebuild_fts()
                        print(f"FTS index rebuilt with {fts_count} documents")

                    yield event.to_sse()
        except ReadwiseAuthError as e:
            yield f"event: error\ndata: {{\"error\": \"{e}\"}}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {{\"error\": \"{e}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/readwise/import/{job_id}/status")
def readwise_import_status(job_id: str):
    """Get current status of an import job."""
    store = get_import_store()
    job = store.get(job_id)
    if not job:
        return {"error": "Job not found"}, 404
    return job.to_dict()


@app.get("/readwise/import/jobs-partial", response_class=HTMLResponse)
def readwise_jobs_partial(request: Request):
    """Return job list as HTML fragment for HTMX polling."""
    store = get_import_store()
    jobs = store.list_recent(limit=10)
    return render("partials/job_list.html", request=request, jobs=jobs)


@app.post("/readwise/jobs/{job_id}/cancel", response_class=HTMLResponse)
def readwise_job_cancel(request: Request, job_id: str):
    """Cancel a running or pending import job. Returns updated job list for HTMX swap."""
    store = get_import_store()
    store.cancel(job_id)
    jobs = store.list_recent(limit=10)
    return render("partials/job_list.html", request=request, jobs=jobs)


@app.delete("/readwise/jobs/{job_id}", response_class=HTMLResponse)
def readwise_job_delete(request: Request, job_id: str):
    """Delete an import job. Returns updated job list for HTMX swap."""
    store = get_import_store()
    job = store.get(job_id)
    # Only allow deleting completed, failed, or cancelled jobs (not running)
    if job and job.status.value in ("running", "pending"):
        jobs = store.list_recent(limit=10)
        return render("partials/job_list.html", request=request, jobs=jobs)
    store.delete(job_id)
    jobs = store.list_recent(limit=10)
    return render("partials/job_list.html", request=request, jobs=jobs)


@app.get("/readwise/jobs/{job_id}", response_class=HTMLResponse)
def readwise_job_detail(request: Request, job_id: str):
    """Show details for a specific import job."""
    store = get_import_store()
    job = store.get(job_id)
    if not job:
        return render("job_detail.html", request=request, job=None, error="Job nicht gefunden")
    return render("job_detail.html", request=request, job=job, error=None)
