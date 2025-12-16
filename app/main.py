from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.settings import Settings
from app.core.storage import get_db, init_db
from app.providers.readwise import ReadwiseAuthError, ReadwiseClient

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
