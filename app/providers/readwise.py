"""Readwise Reader API client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Iterator
from urllib.parse import urlparse, urlunparse

import time

import httpx

from app.providers.content_types import Article, Highlight

if TYPE_CHECKING:
    from app.core.import_job import ImportJob


class ImportEventType(str, Enum):
    """Type of import event for SSE streaming."""

    ITEM = "item"
    ITEM_ERROR = "item_error"  # Single item failed but import continues
    PROGRESS = "progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ImportEvent:
    """Event yielded during streaming import for SSE."""

    type: ImportEventType
    data: dict[str, Any]

    def to_sse(self) -> str:
        """Format as SSE message."""
        import json

        return f"event: {self.type.value}\ndata: {json.dumps(self.data)}\n\n"

logger = logging.getLogger(__name__)

READWISE_BASE_URL = "https://readwise.io/api"


def normalize_url(url: str | None) -> str | None:
    """Normalize URL for consistent comparison.

    - Convert to lowercase
    - Remove trailing slash
    - Normalize http to https
    - Remove query parameters
    """
    if not url:
        return None
    url = url.strip().lower()
    if url.startswith("http://"):
        url = "https://" + url[7:]
    # Parse and rebuild without query params
    parsed = urlparse(url)
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path.rstrip("/"),
        "",  # params
        "",  # query
        "",  # fragment
    ))
    return normalized or None


class ReadwiseError(Exception):
    """Base exception for Readwise API errors."""


class ReadwiseAuthError(ReadwiseError):
    """Authentication failed."""


class ReadwiseRateLimitError(ReadwiseError):
    """Rate limit exceeded after all retries."""


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

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> httpx.Response:
        """Make HTTP request with exponential backoff retry on 429.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL path relative to base
            params: Query parameters
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries

        Returns:
            httpx.Response on success

        Raises:
            ReadwiseRateLimitError: If rate limited after all retries
            ReadwiseAuthError: If authentication fails
        """
        delay = base_delay

        for attempt in range(max_retries + 1):
            resp = self._client.request(method, url, params=params)

            if resp.status_code == 401:
                raise ReadwiseAuthError("Invalid Readwise API token")

            if resp.status_code == 429:
                if attempt == max_retries:
                    raise ReadwiseRateLimitError(
                        f"Rate limit exceeded after {max_retries} retries"
                    )

                # Check Retry-After header
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_time = float(retry_after)
                    except ValueError:
                        wait_time = delay
                else:
                    wait_time = delay

                wait_time = min(wait_time, max_delay)
                logger.warning(
                    f"Rate limited (429). Waiting {wait_time:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(wait_time)
                delay = min(delay * 2, max_delay)  # Exponential backoff
                continue

            # Success or other error
            resp.raise_for_status()
            return resp

        # Should not reach here, but just in case
        raise ReadwiseRateLimitError("Rate limit handling failed")

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

            resp = self._request_with_retry("GET", "/v3/list/", params=params)
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
        params: dict[str, str] = {"category": "highlight"}
        highlights: list[Highlight] = []
        next_cursor: str | None = None

        while True:
            if next_cursor:
                params["pageCursor"] = next_cursor

            resp = self._request_with_retry("GET", "/v3/list/", params=params)
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
            id=f"reader:{doc['id']}",
            source_url=doc.get("source_url") or doc.get("url", ""),
            title=doc.get("title", "Untitled"),
            author=doc.get("author"),
            summary=doc.get("summary"),
            word_count=doc.get("word_count"),
            published_date=published,
            category=doc.get("category", "article"),
            html_content=doc.get("html_content"),
            image_url=doc.get("image_url"),
            provider="reader",
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
            id=f"reader:{doc['id']}",
            article_id=f"reader:{article_id}",
            text=text,
            note=doc.get("notes"),
            created_at=created,
            provider="reader",
            provider_id=doc["id"],
        )

    # --- Export API (v2) Methods ---

    def fetch_export_books(
        self,
        *,
        updated_after: datetime | None = None,
        cursor: str | None = None,
        category: str | None = None,
        limit: int | None = None,
    ) -> Iterator[tuple[Article, list[Highlight], str | None]]:
        """Fetch books/sources from Readwise Export API (v2).

        Yields tuples of (article, highlights, next_cursor) to enable
        cursor persistence for pause/resume functionality.

        Args:
            updated_after: Only fetch items updated after this datetime
            cursor: Pagination cursor from previous request
            category: Filter by category (books, articles, tweets, podcasts)
            limit: Maximum number of items to return

        Yields:
            Tuple of (Article, list[Highlight], next_cursor)
        """
        params: dict[str, str] = {}
        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()
        if cursor:
            params["pageCursor"] = cursor

        count = 0

        while True:
            resp = self._request_with_retry("GET", "/v2/export/", params=params)
            data = resp.json()
            results = data.get("results", [])
            next_cursor = data.get("nextPageCursor")

            for book in results:
                # Filter by category if specified
                book_category = book.get("category", "articles")
                if category and book_category != category:
                    continue

                article = self._parse_export_book(book)
                highlights = [
                    self._parse_export_highlight(hl, book.get("source", "export"))
                    for hl in book.get("highlights", [])
                ]

                yield article, highlights, next_cursor
                count += 1

                if limit and count >= limit:
                    return

            if not next_cursor:
                break

            params["pageCursor"] = next_cursor

    def _parse_export_book(self, book: dict) -> Article:
        """Convert Export API book to Article DTO."""
        # Parse published date if available
        published = None
        # Export API doesn't have published_date directly, but may have last_highlight_at
        if book.get("last_highlight_at"):
            try:
                published = datetime.fromisoformat(
                    book["last_highlight_at"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Source identifies where the highlights came from (snipd, kindle, etc.)
        source = book.get("source", "export")

        return Article(
            id=f"export:{book['user_book_id']}",
            source_url=book.get("source_url") or book.get("unique_url", ""),
            title=book.get("title", "Untitled"),
            author=book.get("author"),
            summary=book.get("summary"),
            word_count=None,  # Export API doesn't provide word count
            published_date=published,
            category=book.get("category", "articles"),
            html_content=None,  # Export API doesn't provide full content
            image_url=book.get("cover_image_url"),
            provider=source,  # e.g. "snipd", "kindle", "instapaper"
            provider_id=str(book["user_book_id"]),
        )

    def _parse_export_highlight(self, hl: dict, source: str) -> Highlight:
        """Convert Export API highlight to Highlight DTO."""
        created = None
        if hl.get("highlighted_at"):
            try:
                created = datetime.fromisoformat(
                    hl["highlighted_at"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        return Highlight(
            id=f"export:{hl['id']}",
            article_id=f"export:{hl['book_id']}",
            text=hl.get("text", ""),
            note=hl.get("note"),
            created_at=created,
            provider=source,  # e.g. "snipd", "kindle"
            provider_id=str(hl["id"]),
        )

    # --- Streaming Import ---

    def stream_import(
        self,
        job: ImportJob,
        *,
        url_index: dict[str, str] | None = None,
    ) -> Iterator[ImportEvent]:
        """Stream import from both APIs with pause/resume support.

        Yields ImportEvents for SSE streaming. Checks job.status at each
        iteration to support pause functionality.

        Args:
            job: ImportJob tracking state (cursors, counters, status)
            url_index: Optional dict mapping normalized URLs to existing IDs
                       for merge detection. Will be populated during import.

        Yields:
            ImportEvent for each item, progress update, or state change
        """
        from app.core.import_job import ImportStatus

        if url_index is None:
            url_index = {}

        # Set job to running
        job.status = ImportStatus.RUNNING

        try:
            # Phase 1: Reader API (has full content, import first)
            if not job.reader_done:
                yield from self._stream_reader_api(job, url_index)

            # Check if paused or cancelled after Reader API
            if job.status == ImportStatus.PAUSED:
                yield ImportEvent(
                    type=ImportEventType.PAUSED,
                    data={"items_imported": job.items_imported},
                )
                return
            if job.status == ImportStatus.CANCELLED:
                return

            # Phase 2: Export API (supplements with highlights)
            if not job.export_done:
                yield from self._stream_export_api(job, url_index)

            # Check if paused or cancelled after Export API
            if job.status == ImportStatus.PAUSED:
                yield ImportEvent(
                    type=ImportEventType.PAUSED,
                    data={"items_imported": job.items_imported},
                )
                return
            if job.status == ImportStatus.CANCELLED:
                return

            # Completed successfully
            job.status = ImportStatus.COMPLETED
            yield ImportEvent(
                type=ImportEventType.COMPLETED,
                data={
                    "items_imported": job.items_imported,
                    "items_merged": job.items_merged,
                    "items_failed": job.items_failed,
                },
            )

        except Exception as e:
            job.status = ImportStatus.FAILED
            job.error = str(e)
            logger.exception("Import failed")
            yield ImportEvent(
                type=ImportEventType.ERROR,
                data={"error": str(e)},
            )

    def _stream_reader_api(
        self,
        job: ImportJob,
        url_index: dict[str, str],
    ) -> Iterator[ImportEvent]:
        """Stream items from Reader API."""
        from app.core.import_job import ImportStatus

        # Request full HTML content from Readwise Reader
        params: dict[str, str] = {"withHtmlContent": "true"}
        if job.reader_cursor:
            params["pageCursor"] = job.reader_cursor

        is_first_page = job.reader_cursor is None

        while True:
            # Check for pause or cancel request
            if job.status in (ImportStatus.PAUSED, ImportStatus.CANCELLED):
                return

            resp = self._request_with_retry("GET", "/v3/list/", params=params)
            data = resp.json()
            results = data.get("results", [])
            next_cursor = data.get("nextPageCursor")

            # On first page, capture total count from API
            if is_first_page and job.items_total is None:
                api_count = data.get("count")
                if api_count is not None:
                    job.items_total = api_count
                is_first_page = False

            for doc in results:
                # Check for pause or cancel request
                if job.status in (ImportStatus.PAUSED, ImportStatus.CANCELLED):
                    return

                # Skip highlights/notes (they have parent_id set)
                if doc.get("parent_id"):
                    continue

                try:
                    article = self._parse_article(doc)

                    # Track URL for merge detection
                    norm_url = normalize_url(article.source_url)
                    if norm_url:
                        url_index[norm_url] = article.id

                    job.items_imported += 1
                    job.reader_cursor = next_cursor
                    job.touch()

                    yield ImportEvent(
                        type=ImportEventType.ITEM,
                        data={
                            "article": {
                                "id": article.id,
                                "title": article.title,
                                "source_url": article.source_url,
                                "category": article.category,
                                "provider": article.provider,
                                "provider_id": article.provider_id,
                                "author": article.author,
                                "summary": article.summary,
                                "html_content": article.html_content,
                                "published_date": article.published_date.isoformat() if article.published_date else None,
                                "word_count": article.word_count,
                                "saved_at": doc.get("saved_at") or doc.get("created_at"),
                            },
                            "source": "reader",
                        },
                    )

                except Exception as e:
                    # Log error but continue with next item
                    doc_id = doc.get("id", "unknown")
                    doc_title = doc.get("title", "unknown")[:50]
                    logger.warning(f"Failed to process Reader doc {doc_id} ({doc_title}): {e}")
                    job.items_failed += 1
                    job.touch()

                    yield ImportEvent(
                        type=ImportEventType.ITEM_ERROR,
                        data={
                            "doc_id": doc_id,
                            "title": doc_title,
                            "error": str(e),
                            "source": "reader",
                        },
                    )

                # Progress event every 10 items
                if (job.items_imported + job.items_failed) % 10 == 0:
                    yield ImportEvent(
                        type=ImportEventType.PROGRESS,
                        data={
                            "items_imported": job.items_imported,
                            "items_merged": job.items_merged,
                            "items_failed": job.items_failed,
                            "items_total": job.items_total,
                            "phase": "reader",
                        },
                    )

            # Update cursor for next page
            if next_cursor:
                params["pageCursor"] = next_cursor
                job.reader_cursor = next_cursor
            else:
                # Reader API done
                job.reader_done = True
                job.reader_cursor = None
                break

    def _stream_export_api(
        self,
        job: ImportJob,
        url_index: dict[str, str],
    ) -> Iterator[ImportEvent]:
        """Stream items from Export API, merging with Reader items by URL."""
        from app.core.import_job import ImportStatus

        params: dict[str, str] = {}
        if job.export_cursor:
            params["pageCursor"] = job.export_cursor

        while True:
            # Check for pause or cancel request
            if job.status in (ImportStatus.PAUSED, ImportStatus.CANCELLED):
                return

            resp = self._request_with_retry("GET", "/v2/export/", params=params)
            data = resp.json()
            results = data.get("results", [])
            next_cursor = data.get("nextPageCursor")

            for book in results:
                # Check for pause or cancel request
                if job.status in (ImportStatus.PAUSED, ImportStatus.CANCELLED):
                    return

                try:
                    article = self._parse_export_book(book)
                    highlights = [
                        self._parse_export_highlight(hl, book.get("source", "export"))
                        for hl in book.get("highlights", [])
                    ]

                    # Check for merge by URL
                    norm_url = normalize_url(article.source_url)
                    merged_with: str | None = None
                    if norm_url and norm_url in url_index:
                        merged_with = url_index[norm_url]
                        job.items_merged += 1
                    else:
                        # New item, track URL
                        if norm_url:
                            url_index[norm_url] = article.id
                        job.items_imported += 1

                    job.export_cursor = next_cursor
                    job.touch()

                    yield ImportEvent(
                        type=ImportEventType.ITEM,
                        data={
                            "article": {
                                "id": article.id,
                                "title": article.title,
                                "source_url": article.source_url,
                                "category": article.category,
                                "provider": article.provider,
                                "provider_id": article.provider_id,
                                "author": article.author,
                                "summary": article.summary,
                                "html_content": article.html_content,
                                "published_date": article.published_date.isoformat() if article.published_date else None,
                                "word_count": article.word_count,
                                "saved_at": book.get("updated") or book.get("last_highlight_at"),
                            },
                            "highlights": [
                                {
                                    "id": hl.id,
                                    "text": hl.text,
                                    "note": hl.note,
                                    "highlighted_at": hl.created_at.isoformat() if hl.created_at else None,
                                    "provider": hl.provider,
                                    "provider_id": hl.provider_id,
                                }
                                for hl in highlights
                            ],
                            "source": "export",
                            "merged_with": merged_with,
                        },
                    )

                except Exception as e:
                    # Log error but continue with next item
                    book_id = book.get("user_book_id", "unknown")
                    book_title = book.get("title", "unknown")[:50]
                    logger.warning(f"Failed to process Export book {book_id} ({book_title}): {e}")
                    job.items_failed += 1
                    job.touch()

                    yield ImportEvent(
                        type=ImportEventType.ITEM_ERROR,
                        data={
                            "doc_id": book_id,
                            "title": book_title,
                            "error": str(e),
                            "source": "export",
                        },
                    )

                # Progress event every 10 items
                if (job.items_imported + job.items_merged + job.items_failed) % 10 == 0:
                    yield ImportEvent(
                        type=ImportEventType.PROGRESS,
                        data={
                            "items_imported": job.items_imported,
                            "items_merged": job.items_merged,
                            "items_failed": job.items_failed,
                            "items_total": job.items_total,
                            "phase": "export",
                        },
                    )

            # Update cursor for next page
            if next_cursor:
                params["pageCursor"] = next_cursor
                job.export_cursor = next_cursor
            else:
                # Export API done
                job.export_done = True
                job.export_cursor = None
                break
