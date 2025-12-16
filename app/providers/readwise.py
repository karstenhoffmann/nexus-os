"""Readwise Reader API client."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterator

import httpx

from app.providers.content_types import Article, Highlight

logger = logging.getLogger(__name__)

READWISE_BASE_URL = "https://readwise.io/api"


class ReadwiseError(Exception):
    """Base exception for Readwise API errors."""


class ReadwiseAuthError(ReadwiseError):
    """Authentication failed."""


class ReadwiseClient:
    """Client for Readwise Reader API (v3)."""

    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("Readwise API token is required")
        self._token = token
        self._client = httpx.Client(
            base_url=READWISE_BASE_URL,
            headers={"Authorization": f"Token {token}"},
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ReadwiseClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def validate_token(self) -> bool:
        """Check if the token is valid. Returns True if valid, raises ReadwiseAuthError otherwise."""
        resp = self._client.get("/v2/auth/")
        if resp.status_code == 204:
            return True
        if resp.status_code == 401:
            raise ReadwiseAuthError("Invalid Readwise API token")
        resp.raise_for_status()
        return True

    def fetch_documents(
        self,
        *,
        location: str | None = None,
        category: str | None = None,
        updated_after: datetime | None = None,
        with_html_content: bool = False,
        limit: int | None = None,
    ) -> Iterator[Article]:
        """Fetch documents from Readwise Reader API.

        Args:
            location: Filter by location (new, later, shortlist, archive, feed)
            category: Filter by category (article, email, rss, highlight, note, pdf, epub, tweet, video)
            updated_after: Only fetch documents updated after this datetime
            with_html_content: Include full HTML content (increases response size)
            limit: Maximum number of documents to return (None = all)

        Yields:
            Article objects (excludes highlights/notes which have parent_id set)
        """
        params: dict[str, str] = {}
        if location:
            params["location"] = location
        if category:
            params["category"] = category
        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()
        if with_html_content:
            params["withHtmlContent"] = "true"

        count = 0
        next_cursor: str | None = None

        while True:
            if next_cursor:
                params["pageCursor"] = next_cursor

            resp = self._client.get("/v3/list/", params=params)
            if resp.status_code == 401:
                raise ReadwiseAuthError("Invalid Readwise API token")
            resp.raise_for_status()

            data = resp.json()
            results = data.get("results", [])

            for doc in results:
                # Skip highlights/notes (they have parent_id set)
                if doc.get("parent_id"):
                    continue

                article = self._parse_article(doc)
                yield article
                count += 1

                if limit and count >= limit:
                    return

            next_cursor = data.get("nextPageCursor")
            if not next_cursor:
                break

    def fetch_highlights_for_article(self, article_id: str) -> list[Highlight]:
        """Fetch all highlights for a specific article.

        Highlights in Reader API are documents with parent_id = article_id.
        """
        params = {"category": "highlight"}
        highlights: list[Highlight] = []
        next_cursor: str | None = None

        while True:
            if next_cursor:
                params["pageCursor"] = next_cursor

            resp = self._client.get("/v3/list/", params=params)
            if resp.status_code == 401:
                raise ReadwiseAuthError("Invalid Readwise API token")
            resp.raise_for_status()

            data = resp.json()
            results = data.get("results", [])

            for doc in results:
                if doc.get("parent_id") == article_id:
                    highlights.append(self._parse_highlight(doc, article_id))

            next_cursor = data.get("nextPageCursor")
            if not next_cursor:
                break

        return highlights

    def _parse_article(self, doc: dict) -> Article:
        """Convert Readwise document to Article DTO."""
        published = None
        if doc.get("published_date"):
            try:
                published = datetime.fromisoformat(doc["published_date"])
            except ValueError:
                pass

        return Article(
            id=f"readwise:{doc['id']}",
            source_url=doc.get("source_url") or doc.get("url", ""),
            title=doc.get("title", "Untitled"),
            author=doc.get("author"),
            summary=doc.get("summary"),
            word_count=doc.get("word_count"),
            published_date=published,
            category=doc.get("category", "article"),
            html_content=doc.get("html_content"),
            image_url=doc.get("image_url"),
            provider="readwise",
            provider_id=doc["id"],
        )

    def _parse_highlight(self, doc: dict, article_id: str) -> Highlight:
        """Convert Readwise highlight document to Highlight DTO."""
        created = None
        if doc.get("created_at"):
            try:
                created = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00"))
            except ValueError:
                pass

        # Highlight text is in the 'content' or 'title' field
        text = doc.get("content") or doc.get("title") or ""

        return Highlight(
            id=f"readwise:{doc['id']}",
            article_id=f"readwise:{article_id}",
            text=text,
            note=doc.get("notes"),
            created_at=created,
            provider="readwise",
            provider_id=doc["id"],
        )
