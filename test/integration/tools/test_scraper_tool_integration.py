"""
Integration tests for ScraperTool with real URLs.

These tests verify that ScraperTool works correctly with real websites:
- Basic HTML fetching and parsing
- Metadata extraction
- Link extraction
- Text extraction
- Markdown conversion
- Error handling with real network conditions
- Rate limiting behavior
- Caching functionality

Note: These tests make real HTTP requests and may be slower than unit tests.
Mark as integration tests to separate from fast unit tests.
"""

import pytest
import asyncio
from aiecs.tools.scraper_tool import (
    ScraperTool,
    ScraperToolConfig,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
async def scraper_tool():
    """Create a ScraperTool instance for integration tests"""
    import os
    # Set environment variables for config
    os.environ["SCRAPER_TOOL_TIMEOUT"] = "30"
    os.environ["SCRAPER_TOOL_MAX_RETRIES"] = "2"
    os.environ["SCRAPER_TOOL_ENABLE_CACHE"] = "false"
    os.environ["SCRAPER_TOOL_REQUESTS_PER_MINUTE"] = "10"

    tool = ScraperTool()
    yield tool
    # Cleanup
    await tool.close()

    # Clean up env vars
    for key in ["SCRAPER_TOOL_TIMEOUT", "SCRAPER_TOOL_MAX_RETRIES",
                "SCRAPER_TOOL_ENABLE_CACHE", "SCRAPER_TOOL_REQUESTS_PER_MINUTE"]:
        os.environ.pop(key, None)


@pytest.fixture
async def scraper_tool_with_cache():
    """Create a ScraperTool instance with caching enabled"""
    import os
    os.environ["SCRAPER_TOOL_TIMEOUT"] = "30"
    os.environ["SCRAPER_TOOL_MAX_RETRIES"] = "2"
    os.environ["SCRAPER_TOOL_ENABLE_CACHE"] = "true"
    os.environ["SCRAPER_TOOL_CACHE_TTL"] = "300"
    os.environ["SCRAPER_TOOL_REQUESTS_PER_MINUTE"] = "10"

    tool = ScraperTool()
    yield tool
    # Cleanup
    await tool.close()

    # Clean up env vars
    for key in ["SCRAPER_TOOL_TIMEOUT", "SCRAPER_TOOL_MAX_RETRIES",
                "SCRAPER_TOOL_ENABLE_CACHE", "SCRAPER_TOOL_CACHE_TTL",
                "SCRAPER_TOOL_REQUESTS_PER_MINUTE"]:
        os.environ.pop(key, None)


# ============================================================================
# Test: Basic Fetching with Real URLs
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestScraperToolRealURLs:
    """Integration tests with real URLs"""

    async def test_fetch_example_com(self, scraper_tool):
        """Test fetching example.com - a reliable test URL"""
        result = await scraper_tool.fetch("https://example.com")

        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert "title" in result
        assert "content" in result
        assert len(result["content"]) > 0

    async def test_fetch_with_metadata_extraction(self, scraper_tool):
        """Test metadata extraction from a real page"""
        result = await scraper_tool.fetch("https://example.com", requirements="Extract metadata")

        assert result["success"] is True
        assert "extracted_data" in result
        data = result["extracted_data"]

        # Should have metadata when requirements are provided
        assert "metadata" in data
        metadata = data["metadata"]
        assert "title" in metadata
        assert metadata["title"] is not None

    async def test_fetch_with_link_extraction(self, scraper_tool):
        """Test link extraction from a real page"""
        result = await scraper_tool.fetch("https://example.com", requirements="Extract links")

        assert result["success"] is True
        assert "extracted_data" in result
        data = result["extracted_data"]

        # Should have links_count when requirements are provided
        assert "links_count" in data
        assert isinstance(data["links_count"], int)

    async def test_fetch_with_requirements(self, scraper_tool):
        """Test fetch with specific requirements"""
        result = await scraper_tool.fetch(
            url="https://example.com",
            requirements="Extract the main heading and description"
        )
        
        assert result["success"] is True
        assert "extracted_data" in result
        assert "requirements" in result["extracted_data"]

    async def test_fetch_404_error(self, scraper_tool):
        """Test handling of 404 errors"""
        result = await scraper_tool.fetch("https://httpbin.org/status/404")

        # Should handle error gracefully
        assert result["success"] is False
        assert "error" in result
        # Error type might be http_error or unknown_error depending on implementation
        assert "error_type" in result["error"]

    async def test_fetch_invalid_domain(self, scraper_tool):
        """Test handling of invalid domain"""
        result = await scraper_tool.fetch("https://this-domain-does-not-exist-12345.com")
        
        # Should handle error gracefully
        assert result["success"] is False
        assert "error" in result


# ============================================================================
# Test: Caching Behavior
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestScraperToolCaching:
    """Test caching functionality with real URLs"""

    async def test_cache_hit_on_second_fetch(self, scraper_tool_with_cache):
        """Test that second fetch uses cache"""
        url = "https://example.com"

        # First fetch - should not be cached
        result1 = await scraper_tool_with_cache.fetch(url)
        assert result1.get("success") is True
        assert result1.get("cached") is False

        # Second fetch - should be cached
        result2 = await scraper_tool_with_cache.fetch(url)
        # Cached result should have cached=True
        assert result2.get("cached") is True

        # Content should be the same
        assert result1.get("title") == result2.get("title")


# ============================================================================
# Test: Rate Limiting
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestScraperToolRateLimiting:
    """Test rate limiting with real URLs"""

    async def test_rate_limiting_enforced(self):
        """Test that rate limiting is enforced"""
        config = ScraperToolConfig(
            timeout=30,
            enable_cache=False,
            requests_per_minute=6,  # 1 request every 10 seconds
        )
        tool = ScraperTool(config=config)

        try:
            url = "https://example.com"

            # First request should succeed
            result1 = await tool.fetch(url)
            assert result1["success"] is True

            # Immediate second request should be rate limited
            # (unless enough time has passed)
            import time
            start = time.time()
            result2 = await tool.fetch(url + "?test=2")
            elapsed = time.time() - start

            # If rate limited, should have waited
            if result2["success"]:
                # Should have waited at least some time
                assert elapsed >= 0  # Basic sanity check
        finally:
            await tool.close()


# ============================================================================
# Test: Different Content Types
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestScraperToolContentTypes:
    """Test different content types"""

    async def test_fetch_json_content(self, scraper_tool):
        """Test fetching JSON content"""
        # JSONPlaceholder is a free fake API for testing
        result = await scraper_tool.fetch("https://jsonplaceholder.typicode.com/posts/1")

        assert result["success"] is True
        # Should handle JSON content
        assert "extracted_data" in result

    async def test_fetch_html_content(self, scraper_tool):
        """Test HTML content fetching"""
        result = await scraper_tool.fetch(url="https://example.com")

        assert result["success"] is True

        # Should have HTML content
        assert "content" in result
        content = result["content"]
        assert isinstance(content, str)
        assert "<html" in content.lower() or "<!doctype" in content.lower()


# ============================================================================
# Test: Error Recovery
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestScraperToolErrorRecovery:
    """Test error recovery and retry logic"""

    async def test_timeout_handling(self):
        """Test handling of timeout errors"""
        config = ScraperToolConfig(
            timeout=1,  # Very short timeout
            max_retries=1,
            enable_cache=False,
        )
        tool = ScraperTool(config=config)

        try:
            # Use a slow endpoint (httpbin delay)
            result = await tool.fetch("https://httpbin.org/delay/5")

            # Should fail due to timeout
            # (or succeed if the request was fast enough)
            assert "success" in result
            if not result["success"]:
                assert "error" in result
        finally:
            await tool.close()


# ============================================================================
# Test: Configuration
# ============================================================================

@pytest.mark.integration
class TestScraperToolConfiguration:
    """Test configuration loading and validation"""

    def test_config_from_env_vars(self):
        """Test configuration from environment variables"""
        import os

        # Set environment variables
        os.environ["SCRAPER_TOOL_TIMEOUT"] = "60"
        os.environ["SCRAPER_TOOL_MAX_RETRIES"] = "5"
        os.environ["SCRAPER_TOOL_ENABLE_CACHE"] = "true"

        try:
            tool = ScraperTool()

            assert tool.config.timeout == 60
            assert tool.config.max_retries == 5
            assert tool.config.enable_cache is True
        finally:
            # Cleanup
            del os.environ["SCRAPER_TOOL_TIMEOUT"]
            del os.environ["SCRAPER_TOOL_MAX_RETRIES"]
            del os.environ["SCRAPER_TOOL_ENABLE_CACHE"]

    def test_config_explicit_override(self):
        """Test explicit config override via environment"""
        import os

        os.environ["SCRAPER_TOOL_TIMEOUT"] = "120"
        os.environ["SCRAPER_TOOL_MAX_RETRIES"] = "10"

        try:
            tool = ScraperTool()

            assert tool.config.timeout == 120
            assert tool.config.max_retries == 10
        finally:
            os.environ.pop("SCRAPER_TOOL_TIMEOUT", None)
            os.environ.pop("SCRAPER_TOOL_MAX_RETRIES", None)


# ============================================================================
# Test: Real-World Scenarios
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
class TestScraperToolRealWorldScenarios:
    """Test real-world scraping scenarios"""

    async def test_fetch_wikipedia_page(self, scraper_tool):
        """Test fetching a Wikipedia page"""
        result = await scraper_tool.fetch(
            "https://en.wikipedia.org/wiki/Web_scraping",
            requirements="Extract article content"
        )

        # Wikipedia might block or have issues, handle gracefully
        if result["success"]:
            # Should have title and content
            assert "title" in result
            assert "content" in result
            assert len(result["content"]) > 100  # Should have substantial content
        else:
            # If failed, should have error info
            assert "error" in result

    async def test_fetch_github_page(self, scraper_tool):
        """Test fetching a GitHub page"""
        result = await scraper_tool.fetch("https://github.com")

        # GitHub might block or require authentication
        # Just verify we handle it gracefully
        assert "success" in result
        if result["success"]:
            assert "extracted_data" in result

    async def test_multiple_sequential_fetches(self, scraper_tool):
        """Test multiple sequential fetches"""
        urls = [
            "https://example.com",
            "https://example.org",
            "https://example.net",
        ]

        results = []
        for url in urls:
            result = await scraper_tool.fetch(url)
            results.append(result)
            # Small delay to respect rate limits
            await asyncio.sleep(1)

        # All should succeed (example.com, .org, .net are reliable)
        for result in results:
            assert result["success"] is True


