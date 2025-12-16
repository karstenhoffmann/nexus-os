from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.settings import Settings
from app.core.storage import get_db, init_db

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
