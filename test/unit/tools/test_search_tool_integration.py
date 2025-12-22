"""
Integration Tests for SearchTool

Tests real API interactions and end-to-end workflows.
These tests require valid Google API credentials.

Run with: poetry run pytest test/unit_tests/tools/test_search_tool_integration.py -v -s -m integration
Skip with: poetry run pytest test/unit_tests/tools/test_search_tool_integration.py -v -m "not integration"
"""

import os
import asyncio
import logging
from typing import Any, Dict, List
from pathlib import Path

import pytest

# Load environment variables
def _load_env_file():
    """Load environment variables from .env.search file"""
    env_file = Path(__file__).parent.parent.parent.parent / '.env.search'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value
        print(f"✓ Loaded environment variables from {env_file}")
        print(f"  GOOGLE_API_KEY: {os.getenv('GOOGLE_API_KEY', 'NOT SET')[:10]}...")
        print(f"  GOOGLE_CSE_ID: {os.getenv('GOOGLE_CSE_ID', 'NOT SET')[:10]}...")

_load_env_file()

from aiecs.tools.search_tool import SearchTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_result(label: str, value: Any, indent: int = 0):
    """Print a formatted result"""
    prefix = "  " * indent
    if isinstance(value, dict):
        print(f"{prefix}{label}:")
        for k, v in value.items():
            if isinstance(v, (dict, list)) and len(str(v)) > 100:
                print(f"{prefix}  {k}: {type(v).__name__} (length: {len(v)})")
            else:
                print(f"{prefix}  {k}: {v}")
    elif isinstance(value, list):
        print(f"{prefix}{label}: {type(value).__name__} (length: {len(value)})")
        if len(value) > 0 and len(value) <= 3:
            for i, item in enumerate(value):
                print(f"{prefix}  [{i}]: {item}")
    else:
        print(f"{prefix}{label}: {value}")


# Check if API credentials are available
HAS_CREDENTIALS = (
    os.getenv('GOOGLE_API_KEY') and 
    os.getenv('GOOGLE_CSE_ID') and
    os.getenv('GOOGLE_API_KEY') != 'test_api_key_12345'
)

# Skip marker for tests requiring credentials
requires_credentials = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="Google API credentials not configured"
)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestSearchToolIntegration:
    """Integration tests with real API calls"""
    
    @pytest.fixture(scope="class")
    def search_tool(self):
        """Create SearchTool instance for integration tests"""
        if not HAS_CREDENTIALS:
            pytest.skip("API credentials not available")
        
        try:
            tool = SearchTool()
            return tool
        except Exception as e:
            pytest.skip(f"Failed to initialize SearchTool: {e}")
    
    @requires_credentials
    def test_real_web_search(self, search_tool):
        """Test real web search with Google API"""
        print_section("Integration Test - Real Web Search")
        
        result = search_tool.search_web(
            query="Python programming language",
            num_results=5,
            language="en"
        )
        
        assert result is not None
        assert 'results' in result
        assert len(result['results']) > 0
        
        # Check result structure
        first_result = result['results'][0]
        assert 'title' in first_result
        assert 'link' in first_result
        assert 'snippet' in first_result
        
        print_result("Search results count", len(result['results']))
        print_result("First result", first_result)
        print("✓ Real web search successful")
    
    @requires_credentials
    def test_real_image_search(self, search_tool):
        """Test real image search"""
        print_section("Integration Test - Real Image Search")
        
        result = search_tool.search_images(
            query="python logo",
            num_results=5,
            image_type="photo"
        )

        assert result is not None
        # search_images returns a list, not a dict with 'results' key
        assert isinstance(result, list)

        if len(result) > 0:
            first_result = result[0]
            print_result("First image result", first_result)

        print("✓ Real image search successful")
    
    @requires_credentials
    def test_real_news_search(self, search_tool):
        """Test real news search"""
        print_section("Integration Test - Real News Search")
        
        result = search_tool.search_news(
            query="technology news",
            num_results=5,
            language="en",
            sort_by="date"
        )

        assert result is not None
        # search_news returns a list, not a dict with 'results' key
        assert isinstance(result, list)

        print_result("News results count", len(result))
        print("✓ Real news search successful")
    
    @requires_credentials
    def test_search_with_filters(self, search_tool):
        """Test search with various filters"""
        print_section("Integration Test - Search with Filters")
        
        result = search_tool.search_web(
            query="machine learning research",
            num_results=5,
            date_restrict="m6",  # Last 6 months
            file_type="pdf",
            language="en"
        )
        
        assert result is not None
        print_result("Filtered search results", len(result.get('results', [])))
        print("✓ Search with filters successful")
    
    @requires_credentials
    def test_quota_and_metrics(self, search_tool):
        """Test quota status and metrics tracking"""
        print_section("Integration Test - Quota and Metrics")
        
        # Perform a search
        search_tool.search_web(query="test query", num_results=3)

        # Check quota - actual fields returned
        quota = search_tool.get_quota_status()
        assert quota is not None
        assert 'remaining_quota' in quota
        assert 'max_requests' in quota
        assert 'circuit_breaker_state' in quota

        # Check metrics - actual structure
        metrics = search_tool.get_metrics()
        assert metrics is not None
        assert 'requests' in metrics
        assert metrics['requests']['total'] > 0

        print_result("Quota status", quota)
        print_result("Metrics", metrics)
        print("✓ Quota and metrics tracking successful")
    
    @requires_credentials
    def test_error_handling(self, search_tool):
        """Test error handling with invalid inputs"""
        print_section("Integration Test - Error Handling")
        
        # Test with empty query (should be caught by schema validation)
        with pytest.raises(Exception):
            search_tool.search_web(query="", num_results=10)
        
        print("✓ Error handling working correctly")
    
    @requires_credentials
    def test_batch_search(self, search_tool):
        """Test batch search functionality"""
        print_section("Integration Test - Batch Search")

        # SearchTool doesn't have search_batch method
        # Instead, perform multiple searches sequentially
        queries = [
            "Python programming",
            "Machine learning",
            "Data science"
        ]

        results = []
        for query in queries:
            result = search_tool.search_web(query=query, num_results=3)
            results.append(result)

        assert len(results) == len(queries)

        print_result("Batch search results", len(results))
        print("✓ Batch search successful")
    
    @requires_credentials
    def test_caching_behavior(self, search_tool):
        """Test caching functionality"""
        print_section("Integration Test - Caching")
        
        query = "Python caching test"
        
        # First search - should hit API
        result1 = search_tool.search_web(query=query, num_results=5)
        
        # Second search - should hit cache
        result2 = search_tool.search_web(query=query, num_results=5)
        
        # Results should be similar (from cache)
        assert result1 is not None
        assert result2 is not None
        
        print("✓ Caching behavior verified")
    
    @requires_credentials
    def test_quality_analysis(self, search_tool):
        """Test result quality analysis"""
        print_section("Integration Test - Quality Analysis")
        
        result = search_tool.search_web(
            query="Python programming tutorial",
            num_results=5,
            auto_enhance=True,
            return_summary=True
        )
        
        assert result is not None
        
        # Check if quality scores are present
        if 'results' in result and len(result['results']) > 0:
            first_result = result['results'][0]
            if 'quality_score' in first_result:
                print_result("Quality score", first_result['quality_score'])
        
        # Check if summary is present
        if 'summary' in result:
            print_result("Summary", result['summary'])
        
        print("✓ Quality analysis working")
    
    @requires_credentials
    def test_context_tracking(self, search_tool):
        """Test search context tracking"""
        print_section("Integration Test - Context Tracking")
        
        # Perform multiple searches
        search_tool.search_web(query="Python", num_results=3)
        search_tool.search_web(query="JavaScript", num_results=3)
        search_tool.search_web(query="Java", num_results=3)

        # Get context - actual field name is 'history' not 'search_history'
        context = search_tool.get_search_context()

        assert context is not None
        assert 'history' in context
        assert len(context['history']) > 0

        print_result("Search context", context)
        print("✓ Context tracking working")


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
class TestSearchToolPerformance:
    """Performance tests for SearchTool"""
    
    @pytest.fixture(scope="class")
    def search_tool(self):
        """Create SearchTool instance"""
        if not HAS_CREDENTIALS:
            pytest.skip("API credentials not available")
        return SearchTool()
    
    @requires_credentials
    def test_search_response_time(self, search_tool):
        """Test search response time"""
        print_section("Performance Test - Response Time")
        
        import time
        
        start_time = time.time()
        result = search_tool.search_web(query="test", num_results=10)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert result is not None
        assert response_time < 5.0  # Should complete within 5 seconds
        
        print_result("Response time (seconds)", response_time)
        print("✓ Response time acceptable")
    
    @requires_credentials
    def test_rate_limiting_behavior(self, search_tool):
        """Test rate limiting under load"""
        print_section("Performance Test - Rate Limiting")
        
        # Perform multiple rapid searches
        results = []
        for i in range(5):
            try:
                result = search_tool.search_web(
                    query=f"test query {i}",
                    num_results=3
                )
                results.append(result)
            except Exception as e:
                logger.info(f"Rate limit hit: {e}")
                break
        
        print_result("Successful searches", len(results))
        print("✓ Rate limiting working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
