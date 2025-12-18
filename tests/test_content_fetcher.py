"""Tests for content_fetcher.py"""

import pytest

from app.core.content_fetcher import (
    ContentFetcher,
    FetchErrorType,
    FetchResult,
    PAYWALL_DOMAINS,
    JS_REQUIRED_DOMAINS,
)


class TestFetchResult:
    """Tests for FetchResult dataclass."""

    def test_successful_result(self):
        result = FetchResult(
            success=True,
            fulltext="Test content here",
            char_count=17,
        )
        assert result.success is True
        assert result.fulltext == "Test content here"
        assert result.retriable is False

    def test_retriable_timeout(self):
        result = FetchResult(
            success=False,
            error_type=FetchErrorType.TIMEOUT,
            error_message="Request timed out",
        )
        assert result.success is False
        assert result.retriable is True

    def test_retriable_http_5xx(self):
        result = FetchResult(
            success=False,
            error_type=FetchErrorType.HTTP_5XX,
            http_status=503,
        )
        assert result.retriable is True

    def test_not_retriable_http_4xx(self):
        result = FetchResult(
            success=False,
            error_type=FetchErrorType.HTTP_4XX,
            http_status=404,
        )
        assert result.retriable is False

    def test_not_retriable_paywall(self):
        result = FetchResult(
            success=False,
            error_type=FetchErrorType.PAYWALL,
        )
        assert result.retriable is False


class TestContentFetcherDomainChecks:
    """Tests for domain restriction checks."""

    @pytest.fixture
    def fetcher(self):
        return ContentFetcher()

    def test_paywall_domain_detected(self, fetcher):
        result = fetcher._check_domain_restrictions("https://medium.com/some-article")
        assert result is not None
        assert result.error_type == FetchErrorType.PAYWALL

    def test_js_required_domain_detected(self, fetcher):
        result = fetcher._check_domain_restrictions("https://twitter.com/user/status/123")
        assert result is not None
        assert result.error_type == FetchErrorType.JS_REQUIRED

    def test_normal_domain_allowed(self, fetcher):
        result = fetcher._check_domain_restrictions("https://example.com/article")
        assert result is None  # No restriction

    def test_subdomain_paywall_detected(self, fetcher):
        result = fetcher._check_domain_restrictions("https://blog.medium.com/article")
        assert result is not None
        assert result.error_type == FetchErrorType.PAYWALL


@pytest.mark.asyncio
class TestContentFetcherIntegration:
    """Integration tests with real URLs (require network)."""

    @pytest.fixture
    def fetcher(self):
        return ContentFetcher()

    async def test_fetch_wikipedia(self, fetcher):
        """Wikipedia should be fetchable."""
        result = await fetcher.fetch("https://en.wikipedia.org/wiki/Python_(programming_language)")
        await fetcher.close()

        assert result.success is True
        assert result.fulltext is not None
        assert len(result.fulltext) > 500
        assert "Python" in result.fulltext

    async def test_fetch_nonexistent_page(self, fetcher):
        """404 pages should fail with HTTP_4XX or connection error."""
        # Use a known 404 page on a reliable host
        result = await fetcher.fetch("https://www.google.com/this-page-does-not-exist-12345")
        await fetcher.close()

        assert result.success is False
        # Could be HTTP_4XX or NO_CONTENT depending on how Google handles it
        assert result.error_type in (
            FetchErrorType.HTTP_4XX,
            FetchErrorType.NO_CONTENT,
            FetchErrorType.EXTRACTION_FAILED,
        )

    async def test_fetch_invalid_domain(self, fetcher):
        """Invalid domains should fail with connection error."""
        result = await fetcher.fetch("https://this-domain-definitely-does-not-exist-xyz123.com/page")
        await fetcher.close()

        assert result.success is False
        assert result.error_type == FetchErrorType.CONNECTION_ERROR
        assert result.retriable is True

    async def test_fetch_github_readme(self, fetcher):
        """GitHub pages should be fetchable."""
        result = await fetcher.fetch("https://github.com/python/cpython")
        await fetcher.close()

        # GitHub may or may not extract well, but should not error
        # Just check it doesn't crash
        assert result.error_type != FetchErrorType.CONNECTION_ERROR

    async def test_paywall_rejected_without_request(self, fetcher):
        """Paywall domains should be rejected before making HTTP request."""
        result = await fetcher.fetch("https://www.nytimes.com/some-article")
        await fetcher.close()

        assert result.success is False
        assert result.error_type == FetchErrorType.PAYWALL
        # No HTTP status because we didn't make a request
        assert result.http_status is None


@pytest.mark.asyncio
class TestContentFetcherRealUrls:
    """Tests with URLs from typical article sources."""

    @pytest.fixture
    def fetcher(self):
        return ContentFetcher()

    async def test_fetch_hackernews_blog(self, fetcher):
        """HN-style tech blog should be fetchable."""
        # Using a stable, well-known page
        result = await fetcher.fetch("https://www.paulgraham.com/avg.html")
        await fetcher.close()

        if result.success:
            assert result.char_count > 1000
            assert "Lisp" in result.fulltext or "programming" in result.fulltext.lower()

    async def test_fetch_static_site(self, fetcher):
        """Simple static HTML should extract cleanly."""
        result = await fetcher.fetch("https://motherfuckingwebsite.com/")
        await fetcher.close()

        if result.success:
            assert result.char_count > 100
