"""Content fetcher for extracting article text from URLs.

Uses trafilatura for high-accuracy content extraction.
Designed for M1 Mac with 16GB RAM - memory efficient.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# trafilatura is optional - check at runtime
try:
    import trafilatura
    from trafilatura.settings import use_config

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    trafilatura = None  # type: ignore


class FetchErrorType(str, Enum):
    """Classification of fetch errors for retry strategy."""

    TIMEOUT = "timeout"  # Retriable
    HTTP_4XX = "http_4xx"  # Not retriable (404, 403, etc.)
    HTTP_5XX = "http_5xx"  # Retriable (server error)
    PAYWALL = "paywall"  # Not retriable
    JS_REQUIRED = "js_required"  # Not retriable (needs Playwright)
    EXTRACTION_FAILED = "extraction_failed"  # Not retriable
    CONNECTION_ERROR = "connection_error"  # Retriable
    NO_CONTENT = "no_content"  # Not retriable


# Error types that can be retried
RETRIABLE_ERRORS = {FetchErrorType.TIMEOUT, FetchErrorType.HTTP_5XX, FetchErrorType.CONNECTION_ERROR}


@dataclass
class FetchResult:
    """Result of a content fetch operation."""

    success: bool
    fulltext: str | None = None
    char_count: int = 0
    error_type: FetchErrorType | None = None
    error_message: str | None = None
    http_status: int | None = None

    @property
    def retriable(self) -> bool:
        """Whether this error can be retried."""
        return self.error_type in RETRIABLE_ERRORS if self.error_type else False


# Known paywall domains
PAYWALL_DOMAINS = {
    "medium.com",
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "economist.com",
    "bloomberg.com",
    "washingtonpost.com",
    "theathletic.com",
    "businessinsider.com",
    "seekingalpha.com",
}

# Domains that require JavaScript rendering
JS_REQUIRED_DOMAINS = {
    "twitter.com",
    "x.com",
    "instagram.com",
    "facebook.com",
    "linkedin.com",
}

# Minimum content length to consider extraction successful
MIN_CONTENT_LENGTH = 200

# Maximum content size to fetch (10MB)
MAX_CONTENT_SIZE = 10 * 1024 * 1024

# HTTP timeout
FETCH_TIMEOUT = 30.0


class ContentFetcher:
    """Extracts article content from URLs using trafilatura.

    Designed for:
    - High accuracy content extraction
    - Memory efficiency (M1 16GB)
    - Proper error classification
    - Polite crawling (respects rate limits externally)
    """

    def __init__(self) -> None:
        """Initialize the content fetcher."""
        if not TRAFILATURA_AVAILABLE:
            raise RuntimeError(
                "trafilatura not installed. Run: pip install trafilatura"
            )

        # Configure trafilatura for better extraction
        self._config = use_config()
        self._config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
        self._config.set("DEFAULT", "MIN_OUTPUT_SIZE", str(MIN_CONTENT_LENGTH))

        # HTTP client with sensible defaults
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(FETCH_TIMEOUT),
                follow_redirects=True,
                limits=httpx.Limits(max_connections=10),
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; NexusOS/1.0; +https://github.com/nexus-os)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def _check_domain_restrictions(self, url: str) -> FetchResult | None:
        """Check if domain has known restrictions.

        Returns FetchResult with error if restricted, None if OK.
        """
        domain = self._get_domain(url)

        # Check for paywall
        for paywall_domain in PAYWALL_DOMAINS:
            if domain == paywall_domain or domain.endswith("." + paywall_domain):
                return FetchResult(
                    success=False,
                    error_type=FetchErrorType.PAYWALL,
                    error_message=f"Domain {domain} requires subscription",
                )

        # Check for JS requirement
        for js_domain in JS_REQUIRED_DOMAINS:
            if domain == js_domain or domain.endswith("." + js_domain):
                return FetchResult(
                    success=False,
                    error_type=FetchErrorType.JS_REQUIRED,
                    error_message=f"Domain {domain} requires JavaScript rendering",
                )

        return None

    async def fetch(self, url: str) -> FetchResult:
        """Fetch and extract content from a URL.

        Args:
            url: The URL to fetch content from.

        Returns:
            FetchResult with extracted text or error information.
        """
        # Check domain restrictions first
        restriction = self._check_domain_restrictions(url)
        if restriction:
            return restriction

        try:
            client = await self._get_client()

            # Fetch HTML with streaming to limit memory
            response = await client.get(url)

            # Check HTTP status
            if response.status_code >= 500:
                return FetchResult(
                    success=False,
                    error_type=FetchErrorType.HTTP_5XX,
                    error_message=f"Server error: {response.status_code}",
                    http_status=response.status_code,
                )

            if response.status_code >= 400:
                return FetchResult(
                    success=False,
                    error_type=FetchErrorType.HTTP_4XX,
                    error_message=f"Client error: {response.status_code}",
                    http_status=response.status_code,
                )

            # Check content size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_CONTENT_SIZE:
                return FetchResult(
                    success=False,
                    error_type=FetchErrorType.EXTRACTION_FAILED,
                    error_message=f"Content too large: {content_length} bytes",
                    http_status=response.status_code,
                )

            html = response.text

            # Extract content using trafilatura in thread pool
            # (trafilatura is CPU-bound)
            fulltext = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: trafilatura.extract(
                    html,
                    config=self._config,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False,
                    favor_recall=True,  # Get more content
                ),
            )

            if not fulltext:
                return FetchResult(
                    success=False,
                    error_type=FetchErrorType.NO_CONTENT,
                    error_message="No content could be extracted",
                    http_status=response.status_code,
                )

            if len(fulltext) < MIN_CONTENT_LENGTH:
                return FetchResult(
                    success=False,
                    error_type=FetchErrorType.EXTRACTION_FAILED,
                    error_message=f"Content too short: {len(fulltext)} chars",
                    http_status=response.status_code,
                )

            # Success!
            return FetchResult(
                success=True,
                fulltext=fulltext,
                char_count=len(fulltext),
                http_status=response.status_code,
            )

        except httpx.TimeoutException:
            return FetchResult(
                success=False,
                error_type=FetchErrorType.TIMEOUT,
                error_message=f"Request timed out after {FETCH_TIMEOUT}s",
            )

        except httpx.ConnectError as e:
            return FetchResult(
                success=False,
                error_type=FetchErrorType.CONNECTION_ERROR,
                error_message=f"Connection error: {e}",
            )

        except Exception as e:
            logger.exception(f"Unexpected error fetching {url}")
            return FetchResult(
                success=False,
                error_type=FetchErrorType.EXTRACTION_FAILED,
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )

    async def fetch_batch(
        self,
        urls: list[dict[str, Any]],
        on_result: Any | None = None,
    ) -> dict[str, int]:
        """Fetch multiple URLs sequentially with callbacks.

        Note: Sequential to respect rate limits. Use DomainRateLimiter
        in fetch_job.py for proper throttling.

        Args:
            urls: List of dicts with 'id', 'url', 'title'
            on_result: Optional callback(doc_id, result) for each result

        Returns:
            Dict with succeeded, failed, skipped counts
        """
        succeeded = 0
        failed = 0
        skipped = 0

        for item in urls:
            doc_id = item["id"]
            url = item.get("url")

            if not url:
                skipped += 1
                continue

            result = await self.fetch(url)

            if result.success:
                succeeded += 1
            else:
                failed += 1

            if on_result:
                on_result(doc_id, result)

        return {"succeeded": succeeded, "failed": failed, "skipped": skipped}


# Module-level instance for convenience
_fetcher: ContentFetcher | None = None


def get_fetcher() -> ContentFetcher:
    """Get or create the module-level ContentFetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = ContentFetcher()
    return _fetcher


async def fetch_url(url: str) -> FetchResult:
    """Convenience function to fetch a single URL."""
    fetcher = get_fetcher()
    return await fetcher.fetch(url)
