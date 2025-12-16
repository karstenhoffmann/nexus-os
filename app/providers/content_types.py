"""Provider-agnostic content types for articles and highlights."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Article:
    """A document/article from any content provider."""

    id: str
    source_url: str
    title: str
    author: str | None = None
    summary: str | None = None
    word_count: int | None = None
    published_date: datetime | None = None
    category: str = "article"
    html_content: str | None = None
    image_url: str | None = None
    provider: str = "unknown"
    provider_id: str | None = None
    highlight_sources: tuple[str, ...] = ()  # e.g. ("reader", "snipd")


@dataclass(frozen=True)
class Highlight:
    """A highlight/annotation belonging to an article."""

    id: str
    article_id: str
    text: str
    note: str | None = None
    created_at: datetime | None = None
    provider: str = "unknown"
    provider_id: str | None = None
