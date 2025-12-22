"""
E2E Tests for Search Tool (Google Custom Search)

Tests real Google Custom Search Engine API calls.
"""

import pytest
import os
from test.e2e.base import E2EToolTestBase, log_test_info


@pytest.mark.e2e
@pytest.mark.requires_api
class TestSearchToolE2E(E2EToolTestBase):
    """E2E tests for Search Tool with Google CSE."""
    
    @pytest.fixture(autouse=True)
    def setup(self, google_cse_config):
        """Setup Google CSE configuration."""
        self.cse_id = google_cse_config["cse_id"]
        self.api_key = google_cse_config["api_key"]
    
    @pytest.mark.asyncio
    async def test_search_basic_query(self):
        """Test basic search query with Google CSE."""
        log_test_info(
            "Search Tool Basic Query",
            query="python programming",
            api="Google Custom Search"
        )
        
        try:
            from aiecs.tools.search_tool import SearchTool
            
            tool = SearchTool(
                api_key=self.api_key,
                cse_id=self.cse_id
            )
            
            query = "python programming"
            response, latency = await self.measure_latency_async(
                tool.search,
                query=query,
                num_results=3  # Minimal results
            )
            
            self.record_api_call()
            
            # Assertions
            self.assert_tool_result_valid(response)
            assert "results" in response, "Response should contain results"
            
            results = response.get("results", [])
            self.assert_search_results_valid(results)
            
            assert len(results) <= 3, "Should return requested number of results"
            assert latency < 5.0, f"Search took {latency:.2f}s (should be < 5s)"
            
            print(f"\n✅ Search completed in {latency:.2f}s")
            print(f"📊 Found {len(results)} results")
            
        except ImportError:
            pytest.skip("Search tool not available")
        except Exception as e:
            pytest.fail(f"Search API call failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """Test search with date and type filters."""
        log_test_info(
            "Search Tool with Filters",
            query="AI news",
            filters="recent"
        )
        
        try:
            from aiecs.tools.search_tool import SearchTool
            
            tool = SearchTool(
                api_key=self.api_key,
                cse_id=self.cse_id
            )
            
            query = "AI news"
            response, latency = await self.measure_latency_async(
                tool.search,
                query=query,
                num_results=2,
                date_restrict="m1"  # Last month
            )
            
            self.record_api_call()
            
            # Assertions
            self.assert_tool_result_valid(response)
            results = response.get("results", [])
            assert len(results) > 0, "Should return results"
            
            print(f"\n✅ Filtered search completed in {latency:.2f}s")
            
        except ImportError:
            pytest.skip("Search tool not available")
        except Exception as e:
            pytest.fail(f"Filtered search failed: {e}")
    
    def test_search_error_handling(self):
        """Test search error handling with invalid configuration."""
        log_test_info(
            "Search Tool Error Handling",
            test="Invalid API key"
        )
        
        try:
            from aiecs.tools.search_tool import SearchTool
            
            tool = SearchTool(
                api_key="invalid_key_test",
                cse_id="invalid_cse_id"
            )
            
            with pytest.raises(Exception):
                tool.search(query="test")
            
            print(f"\n✅ Error handling works correctly")
            
        except ImportError:
            pytest.skip("Search tool not available")
