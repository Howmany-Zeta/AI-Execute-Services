"""
E2E Tests for APISource Tool

Tests real API calls to various data providers (FRED, News API, etc.).

Note: This test will be skipped if API keys are not available.
"""

import pytest
import os
from test.e2e.base import E2EToolTestBase, log_test_info


@pytest.mark.e2e
@pytest.mark.requires_api
class TestAPISourceE2E(E2EToolTestBase):
    """E2E tests for APISource tool."""
    
    @pytest.mark.skipif(
        not os.getenv("FRED_API_KEY"),
        reason="FRED_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_apisource_fred_data(self):
        """Test FRED economic data retrieval."""
        log_test_info(
            "APISource FRED Data",
            provider="FRED",
            series="GDP"
        )
        
        try:
            from aiecs.tools.apisource import APISourceTool
            
            tool = APISourceTool(provider="fred")
            
            response, latency = await self.measure_latency_async(
                tool.get_data,
                series_id="GDP",
                limit=10  # Minimal data points
            )
            
            self.record_api_call()
            
            # Assertions
            self.assert_tool_result_valid(response)
            assert "data" in response or "observations" in response, \
                "Response should contain data"
            
            print(f"\n✅ FRED data retrieved in {latency:.2f}s")
            
        except ImportError:
            pytest.skip("APISource tool not available")
        except Exception as e:
            pytest.fail(f"FRED API call failed: {e}")
    
    @pytest.mark.skipif(
        not os.getenv("NEWSAPI_API_KEY"),
        reason="NEWSAPI_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_apisource_news_data(self):
        """Test News API data retrieval."""
        log_test_info(
            "APISource News Data",
            provider="NewsAPI",
            query="technology"
        )
        
        try:
            from aiecs.tools.apisource import APISourceTool
            
            tool = APISourceTool(provider="newsapi")
            
            response, latency = await self.measure_latency_async(
                tool.get_news,
                query="technology",
                page_size=5  # Minimal articles
            )
            
            self.record_api_call()
            
            # Assertions
            self.assert_tool_result_valid(response)
            assert "articles" in response or "results" in response, \
                "Response should contain articles"
            
            print(f"\n✅ News data retrieved in {latency:.2f}s")
            
        except ImportError:
            pytest.skip("APISource tool not available")
        except Exception as e:
            pytest.fail(f"NewsAPI call failed: {e}")
    
    def test_apisource_provider_validation(self):
        """Test provider validation and error handling."""
        log_test_info(
            "APISource Provider Validation",
            test="Invalid provider"
        )
        
        try:
            from aiecs.tools.apisource import APISourceTool
            
            with pytest.raises((ValueError, Exception)):
                tool = APISourceTool(provider="invalid_provider_name")
                tool.get_data()
            
            print(f"\n✅ Provider validation works correctly")
            
        except ImportError:
            pytest.skip("APISource tool not available")
