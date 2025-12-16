from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.settings import Settings
from app.core.storage import get_db, init_db
from app.core.import_job import ImportStatus, get_import_store
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
def library(request: Request, q: str = ""):
    db = get_db()
    rows = db.search_documents(q)
    return render("library.html", request=request, q=q, rows=rows)


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
    return render("admin.html", request=request, settings=s, stats=stats)


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
    jobs = store.list_all()
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
                            doc_id = db.save_article(
                                source=article_data.get("provider", "unknown"),
                                provider_id=article_data.get("provider_id", ""),
                                url_original=article_data.get("source_url"),
                                title=article_data.get("title"),
                                author=article_data.get("author"),
                                published_at=article_data.get("published_date"),
                                fulltext=article_data.get("html_content"),
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
