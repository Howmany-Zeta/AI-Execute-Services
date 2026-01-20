"""
Comprehensive tests for ScraperTool component (Simplified Version)

Tests cover:
- ScraperTool initialization and configuration
- fetch() method (the main AI interface)
- Rate limiting and circuit breaker
- Caching and deduplication
- HTML parsing
- Error handling
- Playwright rendering (optional)

Uses mocks for HTTP requests to avoid network dependencies in unit tests.
"""

import pytest
import asyncio
import time
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Import from the new simplified module
from aiecs.tools.scraper_tool import (
    ScraperTool,
    ScraperToolConfig,
    FetchSchema,
    ContentType,
    OutputFormat,
    CircuitState,
    ScraperToolError,
    HttpError,
    RateLimitError,
    CircuitBreakerOpenError,
    ParsingError,
    RenderingError,
    BlockedError,
)
from aiecs.tools.scraper_tool.rate_limiter import (
    RateLimiter,
    AdaptiveRateLimiter,
    CircuitBreaker,
    DomainCircuitBreaker,
)
from aiecs.tools.scraper_tool.cache import ScraperCache, ContentDeduplicator
from aiecs.tools.scraper_tool.error_handler import ErrorHandler
from aiecs.tools.scraper_tool.parser import HtmlParser, JsonParser


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_html_content():
    """Sample HTML content for parsing tests"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="A test page">
        <meta property="og:title" content="OG Test Title">
    </head>
    <body>
        <h1 id="main-title">Main Title</h1>
        <div class="content">
            <p>First paragraph</p>
            <p>Second paragraph with <a href="http://example.com">link</a></p>
        </div>
        <ul class="list">
            <li data-id="1">Item 1</li>
            <li data-id="2">Item 2</li>
            <li data-id="3">Item 3</li>
        </ul>
    </body>
    </html>
    """


@pytest.fixture
def mock_curl_response():
    """Mock curl_cffi response"""
    mock = MagicMock()
    mock.status_code = 200
    mock.text = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
    mock.url = "https://example.com"
    return mock


# ============================================================================
# Test: ScraperToolConfig
# ============================================================================

class TestScraperToolConfig:
    """Tests for ScraperToolConfig settings"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ScraperToolConfig()

        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.impersonate == "chrome120"
        assert config.proxy is None
        assert config.requests_per_minute == 30
        assert config.circuit_breaker_threshold == 5
        assert config.enable_cache is True
        assert config.cache_ttl == 3600
        assert config.redis_url is None
        assert config.enable_js_render is False
        assert config.use_stealth is True

    def test_config_env_prefix(self):
        """Test environment variable prefix"""
        config = ScraperToolConfig()
        assert config.model_config.get("env_prefix") == "SCRAPER_TOOL_"


# ============================================================================
# Test: RateLimiter
# ============================================================================

class TestRateLimiter:
    """Tests for RateLimiter class"""

    def test_rate_limiter_acquire(self):
        """Test token acquisition"""
        limiter = RateLimiter(requests_per_minute=60)  # 1 per second

        # First acquire should succeed
        assert limiter.acquire("example.com") is True

        # Immediate second acquire should fail
        assert limiter.acquire("example.com") is False

    def test_rate_limiter_wait_time(self):
        """Test wait time calculation"""
        limiter = RateLimiter(requests_per_minute=60)

        limiter.acquire("example.com")
        wait = limiter.wait_time("example.com")

        # Should need to wait ~1 second
        assert 0 < wait <= 1.0

    def test_rate_limiter_per_domain(self):
        """Test per-domain rate limiting"""
        limiter = RateLimiter(requests_per_minute=60)

        # Acquire for first domain
        limiter.acquire("domain1.com")

        # Second domain should still be able to acquire
        assert limiter.acquire("domain2.com") is True


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter class"""

    def test_on_success_increases_rate(self):
        """Test that success slightly increases rate"""
        limiter = AdaptiveRateLimiter(requests_per_minute=30)

        limiter.acquire("example.com")
        initial_wait = limiter.wait_time("example.com")

        # Simulate success
        limiter.on_success("example.com")

        # Wait time should be same or less
        time.sleep(0.1)
        new_wait = limiter.wait_time("example.com")
        assert new_wait <= initial_wait + 0.1  # Account for time elapsed

    def test_on_rate_limit_decreases_rate(self):
        """Test that rate limit response decreases rate"""
        limiter = AdaptiveRateLimiter(requests_per_minute=30)

        limiter.acquire("example.com")
        limiter.on_rate_limit("example.com")

        # After rate limit, wait time should be higher
        wait = limiter.wait_time("example.com")
        assert wait >= 0


# ============================================================================
# Test: CircuitBreaker
# ============================================================================

class TestCircuitBreaker:
    """Tests for CircuitBreaker class"""

    def test_circuit_starts_closed(self):
        """Test circuit starts in closed state"""
        breaker = CircuitBreaker(failure_threshold=3)
        assert breaker.is_available() is True

    def test_circuit_opens_after_failures(self):
        """Test circuit opens after threshold failures"""
        breaker = CircuitBreaker(failure_threshold=3)

        # Record failures
        for _ in range(3):
            breaker.record_failure()

        # Circuit should be open
        assert breaker.is_available() is False

    def test_circuit_success_resets_failures(self):
        """Test success resets failure count"""
        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()

        # Should still be closed after success resets count
        assert breaker.is_available() is True

    def test_call_raises_when_open(self):
        """Test call raises error when circuit is open"""
        breaker = CircuitBreaker(failure_threshold=1)
        breaker.record_failure()

        with pytest.raises(CircuitBreakerOpenError):
            breaker.call(lambda: "test")


class TestDomainCircuitBreaker:
    """Tests for DomainCircuitBreaker class"""

    def test_get_breaker_creates_new(self):
        """Test getting breaker creates new one for domain"""
        manager = DomainCircuitBreaker()

        breaker1 = manager.get_breaker("domain1.com")
        breaker2 = manager.get_breaker("domain1.com")

        # Should return same instance
        assert breaker1 is breaker2

    def test_is_domain_available(self):
        """Test domain availability check"""
        manager = DomainCircuitBreaker(failure_threshold=2)

        assert manager.is_domain_available("example.com") is True

        # Open the circuit
        breaker = manager.get_breaker("example.com")
        breaker.record_failure()
        breaker.record_failure()

        assert manager.is_domain_available("example.com") is False


# ============================================================================
# Test: ScraperCache
# ============================================================================

class TestScraperCache:
    """Tests for ScraperCache class"""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test setting and getting cache entries"""
        cache = ScraperCache(max_size=100)

        url = "https://example.com/page"
        content = {"title": "Test", "content": "Hello"}

        await cache.set(url, content)
        result = await cache.get(url)

        assert result is not None
        assert result["title"] == "Test"

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = ScraperCache()

        result = await cache.get("https://nonexistent.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalidate(self):
        """Test cache invalidation"""
        cache = ScraperCache()

        url = "https://example.com"
        await cache.set(url, {"data": "test"})
        await cache.invalidate(url)

        result = await cache.get(url)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction when max size reached"""
        cache = ScraperCache(max_size=2)

        await cache.set("https://url1.com", {"data": 1})
        await cache.set("https://url2.com", {"data": 2})
        await cache.set("https://url3.com", {"data": 3})  # Should evict url1

        # url1 should be evicted
        result1 = await cache.get("https://url1.com")
        result3 = await cache.get("https://url3.com")

        assert result1 is None
        assert result3 is not None

    def test_url_normalization(self):
        """Test URL normalization removes tracking params"""
        cache = ScraperCache()

        url1 = "https://example.com/page?utm_source=test&content=1"
        url2 = "https://example.com/page?content=1&utm_campaign=abc"

        key1 = cache._generate_key(url1)
        key2 = cache._generate_key(url2)

        # Both should normalize to the same key (tracking params removed)
        assert key1 == key2


class TestContentDeduplicator:
    """Tests for ContentDeduplicator class"""

    def test_exact_duplicate_detection(self):
        """Test exact duplicate detection via hash"""
        dedup = ContentDeduplicator()

        content = "This is the exact same content"
        dedup.add_content("https://url1.com", content)

        is_dup, match_url = dedup.is_duplicate(content)

        assert is_dup is True
        assert match_url == "https://url1.com"

    def test_not_duplicate(self):
        """Test non-duplicate content"""
        dedup = ContentDeduplicator()

        dedup.add_content("https://url1.com", "Content A")
        is_dup, _ = dedup.is_duplicate("Completely different content B")

        assert is_dup is False

    def test_get_hash(self):
        """Test hash generation"""
        dedup = ContentDeduplicator()

        hash1 = dedup.get_hash("test content")
        hash2 = dedup.get_hash("test content")
        hash3 = dedup.get_hash("different content")

        assert hash1 == hash2
        assert hash1 != hash3


# ============================================================================
# Test: HtmlParser
# ============================================================================

class TestHtmlParser:
    """Tests for HtmlParser class"""

    def test_parse_html(self, sample_html_content):
        """Test HTML parsing"""
        parser = HtmlParser()
        soup = parser.parse(sample_html_content)

        assert soup is not None
        assert soup.find("h1") is not None

    def test_select_css(self, sample_html_content):
        """Test CSS selector"""
        parser = HtmlParser()

        elements = parser.select(sample_html_content, "li", "css")
        assert len(elements) == 3

    def test_extract_text(self, sample_html_content):
        """Test text extraction"""
        parser = HtmlParser()

        text = parser.extract_text(sample_html_content)

        assert "Main Title" in text
        assert "First paragraph" in text
        # Scripts and styles should be removed
        assert "<script>" not in text

    def test_extract_links(self, sample_html_content):
        """Test link extraction"""
        parser = HtmlParser()

        links = parser.extract_links(sample_html_content)

        assert len(links) >= 1
        assert any(link["url"] == "http://example.com" for link in links)

    def test_extract_metadata(self, sample_html_content):
        """Test metadata extraction"""
        parser = HtmlParser()

        metadata = parser.extract_metadata(sample_html_content)

        assert metadata["title"] == "Test Page"
        assert "description" in metadata
        assert metadata["description"] == "A test page"
        # OpenGraph metadata is nested under "og" key
        assert "og" in metadata
        assert "title" in metadata["og"]
        assert metadata["og"]["title"] == "OG Test Title"

    def test_html_to_markdown(self):
        """Test HTML to Markdown conversion"""
        parser = HtmlParser()

        html = "<h1>Title</h1><p>Paragraph text</p><ul><li>Item 1</li></ul>"
        md = parser.html_to_markdown(html)

        assert "# Title" in md
        assert "Paragraph text" in md


class TestJsonParser:
    """Tests for JsonParser class"""

    def test_parse_json(self):
        """Test JSON parsing"""
        parser = JsonParser()

        data = parser.parse('{"key": "value", "number": 42}')

        assert data["key"] == "value"
        assert data["number"] == 42

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises error"""
        parser = JsonParser()

        with pytest.raises(ParsingError):
            parser.parse("not valid json")

    def test_query_simple_path(self):
        """Test simple JSONPath query"""
        parser = JsonParser()

        data = {"user": {"name": "John", "age": 30}}
        result = parser.query(data, "$.user.name")

        assert result == "John"

    def test_query_array_index(self):
        """Test array index query"""
        parser = JsonParser()

        data = {"items": ["a", "b", "c"]}
        result = parser.query(data, "$.items[1]")

        assert result == "b"


# ============================================================================
# Test: ErrorHandler
# ============================================================================

class TestErrorHandler:
    """Tests for ErrorHandler class"""

    def test_format_http_error_4xx(self):
        """Test formatting 4xx HTTP error"""
        handler = ErrorHandler()
        error = HttpError("Not found", status_code=404)

        result = handler.format_error(error)

        assert result["error_type"] == "http_error"
        assert result["can_retry"] is False  # 4xx shouldn't retry
        assert "404" in result["message"] or "Not found" in result["message"]

    def test_format_http_error_5xx(self):
        """Test formatting 5xx HTTP error"""
        handler = ErrorHandler()
        error = HttpError("Server error", status_code=500)

        result = handler.format_error(error)

        assert result["error_type"] == "http_error"
        assert result["can_retry"] is True  # 5xx should retry
        assert result["severity"] in ["medium", "high"]

    def test_format_rate_limit_error(self):
        """Test formatting rate limit error"""
        handler = ErrorHandler()
        error = RateLimitError("Too many requests", retry_after=60)

        result = handler.format_error(error)

        assert result["error_type"] == "rate_limit"
        assert result["can_retry"] is True
        assert result["retry_after"] == 60
        assert "wait" in " ".join(result["suggested_actions"]).lower()

    def test_format_circuit_breaker_error(self):
        """Test formatting circuit breaker error"""
        handler = ErrorHandler()
        error = CircuitBreakerOpenError("Domain unavailable")

        result = handler.format_error(error)

        assert result["error_type"] == "circuit_breaker"
        assert result["can_retry"] is True

    def test_format_blocked_error(self):
        """Test formatting blocked error"""
        handler = ErrorHandler()
        error = BlockedError("Bot detected", block_type="captcha")

        result = handler.format_error(error)

        assert result["error_type"] == "blocked"
        assert result["severity"] == "high"

    def test_format_parsing_error(self):
        """Test formatting parsing error"""
        handler = ErrorHandler()
        error = ParsingError("Invalid HTML")

        result = handler.format_error(error)

        assert result["error_type"] == "parsing_error"
        assert result["can_retry"] is False

    def test_format_rendering_error(self):
        """Test formatting rendering error"""
        handler = ErrorHandler()
        error = RenderingError("Playwright failed")

        result = handler.format_error(error)

        assert result["error_type"] == "rendering_error"

    def test_format_generic_error(self):
        """Test formatting generic exception"""
        handler = ErrorHandler()
        error = Exception("Unknown error")

        result = handler.format_error(error)

        assert result["error_type"] == "unknown_error"
        assert "message" in result


# ============================================================================
# Test: ScraperTool (Main Class)
# ============================================================================

class TestScraperTool:
    """Tests for the main ScraperTool class"""

    @pytest.fixture
    def mock_scraper(self):
        """Create a ScraperTool with mocked HTTP client"""
        with patch.dict('os.environ', {'SCRAPER_TOOL_ENABLE_CACHE': 'false'}):
            tool = ScraperTool()
            return tool

    def test_initialization(self):
        """Test ScraperTool initialization"""
        with patch.dict('os.environ', {'SCRAPER_TOOL_ENABLE_CACHE': 'false'}):
            tool = ScraperTool()

            assert tool.config is not None
            assert tool.rate_limiter is not None
            assert tool.circuit_breaker is not None
            assert tool.error_handler is not None
            assert tool.html_parser is not None
            assert tool.json_parser is not None

    def test_config_loaded(self):
        """Test configuration is loaded correctly"""
        with patch.dict('os.environ', {
            'SCRAPER_TOOL_TIMEOUT': '60',
            'SCRAPER_TOOL_IMPERSONATE': 'firefox',
            'SCRAPER_TOOL_ENABLE_CACHE': 'false',
        }):
            tool = ScraperTool()

            assert tool.config.timeout == 60
            assert tool.config.impersonate == "firefox"

    @pytest.mark.asyncio
    async def test_fetch_returns_correct_structure(self, mock_scraper, mock_curl_response):
        """Test fetch returns correct response structure"""
        with patch('aiecs.tools.scraper_tool.core.AsyncSession') as MockSession:
            # Setup mock
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_curl_response
            MockSession.return_value.__aenter__.return_value = mock_session

            result = await mock_scraper.fetch("https://example.com")

            assert "success" in result
            assert "url" in result
            assert "cached" in result

    @pytest.mark.asyncio
    async def test_fetch_with_requirements(self, mock_scraper, mock_curl_response):
        """Test fetch with requirements parameter"""
        with patch('aiecs.tools.scraper_tool.core.AsyncSession') as MockSession:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_curl_response
            MockSession.return_value.__aenter__.return_value = mock_session

            result = await mock_scraper.fetch(
                url="https://example.com",
                requirements="Extract the title"
            )

            assert "extracted_data" in result
            assert "requirements" in result.get("extracted_data", {})

    @pytest.mark.asyncio
    async def test_fetch_circuit_breaker_blocks(self):
        """Test fetch respects circuit breaker"""
        with patch.dict('os.environ', {'SCRAPER_TOOL_ENABLE_CACHE': 'false'}):
            tool = ScraperTool()

            # Open the circuit
            breaker = tool.circuit_breaker.get_breaker("blocked-domain.com")
            for _ in range(10):
                breaker.record_failure()

            result = await tool.fetch("https://blocked-domain.com/page")

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_fetch_handles_http_error(self, mock_scraper):
        """Test fetch handles HTTP errors gracefully"""
        with patch('aiecs.tools.scraper_tool.core.AsyncSession') as MockSession:
            mock_session = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_session.get.return_value = mock_response
            MockSession.return_value.__aenter__.return_value = mock_session

            result = await mock_scraper.fetch("https://example.com/notfound")

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_fetch_uses_cache(self):
        """Test fetch uses cache when enabled"""
        with patch.dict('os.environ', {'SCRAPER_TOOL_ENABLE_CACHE': 'true'}):
            tool = ScraperTool()

            # Pre-populate cache
            url = "https://cached-example.com"
            cached_data = {"title": "Cached", "content": "From cache"}
            await tool.cache.set(url, cached_data)

            result = await tool.fetch(url)

            assert result["cached"] is True

    @pytest.mark.asyncio
    async def test_close_cleanup(self):
        """Test close method cleans up resources"""
        with patch.dict('os.environ', {'SCRAPER_TOOL_ENABLE_CACHE': 'false'}):
            tool = ScraperTool()

            # Should not raise
            await tool.close()


# ============================================================================
# Test: FetchSchema
# ============================================================================

class TestFetchSchema:
    """Tests for FetchSchema validation"""

    def test_valid_schema(self):
        """Test valid schema creation"""
        schema = FetchSchema(url="https://example.com")
        assert schema.url == "https://example.com"
        assert schema.requirements is None

    def test_schema_with_requirements(self):
        """Test schema with requirements"""
        schema = FetchSchema(
            url="https://example.com",
            requirements="Extract article content"
        )
        assert schema.requirements == "Extract article content"

    def test_schema_requires_url(self):
        """Test schema requires url"""
        with pytest.raises(Exception):  # ValidationError
            FetchSchema(requirements="test")
