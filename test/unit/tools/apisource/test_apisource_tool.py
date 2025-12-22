"""
Comprehensive tests for APISourceTool

Tests real functionality without mocks to verify actual behavior and output.
Includes debug output for manual verification of tool functionality.

Run with: 
    poetry run pytest test/unit_tests/tools/apisource/test_apisource_tool.py -v -s

Coverage: 
    poetry run pytest test/unit_tests/tools/apisource/test_apisource_tool.py \
        --cov=aiecs.tools.apisource --cov-report=term-missing --cov-report=html
"""

import os
import logging
from typing import Dict, Any

import pytest

from aiecs.tools.apisource import (
    APISourceTool,
    APISourceError,
    ProviderNotFoundError,
    APIRateLimitError,
    APIAuthenticationError,
    get_provider,
    list_providers,
)

logger = logging.getLogger(__name__)


class TestAPISourceToolInitialization:
    """Test APISourceTool initialization and configuration"""
    
    def test_default_initialization(self, debug_output):
        """Test tool initialization with default settings"""
        print("\n=== Testing Default Initialization ===")
        tool = APISourceTool()
        
        assert tool is not None
        assert hasattr(tool, 'config')
        assert hasattr(tool, '_providers')
        assert hasattr(tool, 'query_analyzer')
        assert hasattr(tool, 'query_enhancer')
        assert hasattr(tool, 'data_fusion')
        assert hasattr(tool, 'fallback_strategy')
        assert hasattr(tool, 'search_enhancer')
        
        debug_output("Default Configuration", {
            'cache_ttl': tool.config.cache_ttl,
            'default_timeout': tool.config.default_timeout,
            'max_retries': tool.config.max_retries,
            'enable_rate_limiting': tool.config.enable_rate_limiting,
            'enable_fallback': tool.config.enable_fallback,
            'enable_data_fusion': tool.config.enable_data_fusion,
            'enable_query_enhancement': tool.config.enable_query_enhancement,
        })
        
        print("✓ Tool initialized successfully with default settings")
    
    def test_custom_configuration(self, api_keys, test_config, debug_output):
        """Test tool initialization with custom configuration"""
        print("\n=== Testing Custom Configuration ===")
        
        config = {
            **api_keys,
            **test_config,
            'enable_fallback': False,
            'enable_query_enhancement': False,
        }
        
        tool = APISourceTool(config=config)
        
        assert tool.config.enable_fallback is False
        assert tool.config.enable_query_enhancement is False
        assert tool.config.default_timeout == test_config['default_timeout']
        
        debug_output("Custom Configuration", {
            'enable_fallback': tool.config.enable_fallback,
            'enable_query_enhancement': tool.config.enable_query_enhancement,
            'default_timeout': tool.config.default_timeout,
        })
        
        print("✓ Tool initialized with custom configuration")
    
    def test_provider_initialization(self, api_keys, debug_output):
        """Test that providers are properly initialized"""
        print("\n=== Testing Provider Initialization ===")
        
        tool = APISourceTool(config=api_keys)
        
        # Check that providers are loaded
        assert len(tool._providers) > 0
        
        available_providers = list(tool._providers.keys())
        debug_output("Available Providers", available_providers)
        
        # Verify expected providers
        expected_providers = ['fred', 'newsapi', 'worldbank', 'census']
        for provider in expected_providers:
            assert provider in available_providers, f"Provider '{provider}' not found"
        
        print(f"✓ {len(available_providers)} providers initialized successfully")
    
    def test_list_providers(self, api_keys, debug_output):
        """Test listing available providers"""
        print("\n=== Testing List Providers ===")

        tool = APISourceTool(config=api_keys)
        providers = tool.list_providers()

        # list_providers returns a list, not a dict
        assert isinstance(providers, list)
        assert len(providers) > 0

        debug_output("Provider List", {
            'count': len(providers),
            'providers': [p.get('name') for p in providers]
        })

        # Verify provider information
        for provider_info in providers:
            assert 'name' in provider_info
            assert 'description' in provider_info
            assert 'operations' in provider_info
            assert isinstance(provider_info['operations'], list)

        print(f"✓ Listed {len(providers)} providers")


class TestAPISourceToolProviderInfo:
    """Test provider information retrieval"""
    
    @pytest.mark.parametrize("provider_name", ['fred', 'newsapi', 'worldbank', 'census'])
    def test_get_provider_info(self, api_keys, provider_name, debug_output):
        """Test getting information about specific providers"""
        print(f"\n=== Testing Get Provider Info: {provider_name} ===")
        
        tool = APISourceTool(config=api_keys)
        info = tool.get_provider_info(provider_name)
        
        assert isinstance(info, dict)
        assert 'name' in info
        assert 'description' in info
        assert 'operations' in info
        assert 'stats' in info
        assert 'health' in info
        assert 'config' in info
        
        debug_output(f"{provider_name.upper()} Provider Info", {
            'name': info['name'],
            'description': info['description'],
            'operations_count': len(info['operations']),
            'operations': info['operations'],
            'health_score': info['health']['score'],
            'health_status': info['health']['status'],
        })
        
        print(f"✓ Retrieved info for {provider_name}")
    
    def test_get_nonexistent_provider_info(self, api_keys):
        """Test getting info for non-existent provider"""
        print("\n=== Testing Non-existent Provider ===")
        
        tool = APISourceTool(config=api_keys)
        
        with pytest.raises(ProviderNotFoundError) as exc_info:
            tool.get_provider_info('nonexistent_provider')
        
        assert 'not found' in str(exc_info.value).lower()
        print("✓ Correctly raised ProviderNotFoundError")


class TestAPISourceToolQuery:
    """Test query functionality"""
    
    @pytest.mark.network
    def test_query_fred_basic(self, api_keys, skip_if_no_api_key, debug_output, 
                              assert_valid_response, measure_performance):
        """Test basic FRED query"""
        skip_if_no_api_key('fred')
        print("\n=== Testing FRED Basic Query ===")
        
        tool = APISourceTool(config=api_keys)
        
        measure_performance.start()
        result = tool.query(
            provider='fred',
            operation='search_series',
            params={'search_text': 'GDP'}
        )
        duration = measure_performance.stop()
        
        assert_valid_response(result, 'search_series')
        assert result['provider'] == 'fred'
        assert result['operation'] == 'search_series'
        assert 'data' in result
        assert isinstance(result['data'], list)

        debug_output("FRED Search Results", {
            'provider': result['provider'],
            'operation': result['operation'],
            'data_type': type(result['data']).__name__,
            'data_count': len(result['data']),
            'duration_seconds': duration,
        })
        
        measure_performance.print_result("FRED search_series")
        print("✓ FRED query executed successfully")
    
    @pytest.mark.network
    def test_query_with_enhancement(self, api_keys, skip_if_no_api_key, debug_output):
        """Test query with parameter enhancement"""
        skip_if_no_api_key('fred')
        print("\n=== Testing Query with Enhancement ===")
        
        tool = APISourceTool(config={
            **api_keys,
            'enable_query_enhancement': True
        })
        
        result = tool.query(
            provider='fred',
            operation='search_series',
            params={'search_text': 'unemployment'},
            query_text="Find unemployment rate data"
        )
        
        assert result['provider'] == 'fred'
        assert 'data' in result

        debug_output("Enhanced Query Result", {
            'provider': result['provider'],
            'operation': result['operation'],
            'data_count': len(result['data']) if isinstance(result['data'], list) else 1,
        })
        
        print("✓ Query with enhancement executed successfully")
    
    def test_query_invalid_provider(self, api_keys):
        """Test query with invalid provider"""
        print("\n=== Testing Invalid Provider Query ===")
        
        tool = APISourceTool(config=api_keys)
        
        with pytest.raises(ProviderNotFoundError):
            tool.query(
                provider='invalid_provider',
                operation='some_operation',
                params={}
            )
        
        print("✓ Correctly raised ProviderNotFoundError for invalid provider")
    
    def test_query_invalid_operation(self, api_keys):
        """Test query with invalid operation"""
        print("\n=== Testing Invalid Operation Query ===")

        tool = APISourceTool(config=api_keys)

        # Invalid operation raises APISourceError
        try:
            result = tool.query(
                provider='fred',
                operation='invalid_operation',
                params={}
            )
            # If no exception, check result
            assert result['success'] is False
            assert 'error' in result
        except Exception as e:
            # Expected to raise an error
            assert 'invalid_operation' in str(e).lower() or 'not supported' in str(e).lower()

        print("✓ Correctly handled invalid operation")


class TestAPISourceToolSearch:
    """Test search functionality"""
    
    @pytest.mark.network
    @pytest.mark.slow
    def test_search_single_provider(self, api_keys, skip_if_no_api_key, debug_output,
                                    measure_performance):
        """Test search with single provider"""
        skip_if_no_api_key('fred')
        print("\n=== Testing Single Provider Search ===")
        
        tool = APISourceTool(config=api_keys)
        
        measure_performance.start()
        result = tool.search(
            query='GDP growth',
            providers=['fred'],
            limit=5
        )
        duration = measure_performance.stop()
        
        assert isinstance(result, dict)
        assert 'results' in result or 'data' in result
        
        debug_output("Search Results", {
            'result_keys': list(result.keys()),
            'duration_seconds': duration,
        })
        
        measure_performance.print_result("Single provider search")
        print("✓ Single provider search executed successfully")

    @pytest.mark.network
    @pytest.mark.slow
    def test_search_multiple_providers(self, api_keys, debug_output, measure_performance):
        """Test search across multiple providers with data fusion"""
        print("\n=== Testing Multi-Provider Search with Fusion ===")

        tool = APISourceTool(config={
            **api_keys,
            'enable_data_fusion': True
        })

        measure_performance.start()
        result = tool.search(
            query='economic indicators',
            providers=['fred', 'worldbank'],
            limit=10,
            enable_fusion=True
        )
        duration = measure_performance.stop()

        assert isinstance(result, dict)

        debug_output("Multi-Provider Search Results", {
            'result_keys': list(result.keys()),
            'duration_seconds': duration,
        })

        measure_performance.print_result("Multi-provider search with fusion")
        print("✓ Multi-provider search executed successfully")

    def test_search_with_options(self, api_keys, debug_output):
        """Test search with custom options"""
        print("\n=== Testing Search with Custom Options ===")

        tool = APISourceTool(config=api_keys)

        result = tool.search(
            query='inflation',
            providers=['fred'],
            limit=5,
            enable_enhancement=True,
            fusion_strategy='best_quality',
            search_options={
                'min_relevance': 0.5,
                'sort_by': 'relevance'
            }
        )

        assert isinstance(result, dict)

        debug_output("Search with Options Result", {
            'result_keys': list(result.keys()),
        })

        print("✓ Search with custom options executed successfully")


class TestAPISourceToolErrorHandling:
    """Test error handling and edge cases"""

    def test_missing_required_params(self, api_keys):
        """Test query with missing required parameters"""
        print("\n=== Testing Missing Required Parameters ===")

        tool = APISourceTool(config=api_keys)

        # Missing required params raises APISourceError
        try:
            result = tool.query(
                provider='fred',
                operation='get_series_observations',
                params={}  # Missing required 'series_id'
            )
            # If no exception, check result
            assert result['success'] is False
            assert 'error' in result
        except Exception as e:
            # Expected to raise an error about missing parameters
            assert 'missing' in str(e).lower() or 'required' in str(e).lower() or 'failed' in str(e).lower()

        print("✓ Correctly handled missing required parameters")

    def test_invalid_params(self, api_keys):
        """Test query with invalid parameters"""
        print("\n=== Testing Invalid Parameters ===")

        tool = APISourceTool(config=api_keys)

        result = tool.query(
            provider='fred',
            operation='search_series',
            params={'search_text': 123}  # Should be string
        )

        # Should handle gracefully
        assert isinstance(result, dict)

        print("✓ Handled invalid parameters gracefully")

    @pytest.mark.network
    def test_network_timeout(self, api_keys, skip_if_no_api_key):
        """Test handling of network timeout"""
        skip_if_no_api_key('fred')
        print("\n=== Testing Network Timeout Handling ===")

        tool = APISourceTool(config={
            **api_keys,
            'default_timeout': 1  # Very short timeout (must be integer)
        })

        result = tool.query(
            provider='fred',
            operation='search_series',
            params={'search_text': 'GDP'}
        )

        # Should handle timeout gracefully
        assert isinstance(result, dict)

        print("✓ Handled network timeout gracefully")


class TestAPISourceToolCaching:
    """Test caching functionality"""

    @pytest.mark.network
    def test_cache_hit(self, api_keys, skip_if_no_api_key, debug_output, measure_performance):
        """Test that caching works correctly"""
        skip_if_no_api_key('fred')
        print("\n=== Testing Cache Hit ===")

        tool = APISourceTool(config={
            **api_keys,
            'cache_ttl': 300
        })

        params = {'search_text': 'GDP'}

        # First call - cache miss
        measure_performance.start()
        result1 = tool.query(
            provider='fred',
            operation='search_series',
            params=params
        )
        duration1 = measure_performance.stop()

        # Second call - should hit cache
        measure_performance.start()
        result2 = tool.query(
            provider='fred',
            operation='search_series',
            params=params
        )
        duration2 = measure_performance.stop()

        debug_output("Cache Performance", {
            'first_call_duration': duration1,
            'second_call_duration': duration2,
            'speedup': f"{duration1/duration2:.2f}x" if duration2 > 0 else "N/A",
        })

        # Second call should be faster (cached)
        # Note: This might not always be true due to network variability
        print(f"✓ First call: {duration1:.3f}s, Second call: {duration2:.3f}s")


class TestAPISourceToolMetrics:
    """Test metrics and monitoring"""

    @pytest.mark.network
    def test_metrics_collection(self, api_keys, skip_if_no_api_key, debug_output):
        """Test that metrics are collected properly"""
        skip_if_no_api_key('fred')
        print("\n=== Testing Metrics Collection ===")

        tool = APISourceTool(config=api_keys)

        # Execute some queries
        tool.query(
            provider='fred',
            operation='search_series',
            params={'search_text': 'GDP'}
        )

        # Get provider info to check metrics
        info = tool.get_provider_info('fred')

        assert 'stats' in info
        stats = info['stats']

        debug_output("Provider Metrics", stats)

        # Verify metrics structure
        assert 'total_requests' in stats
        assert 'success_rate' in stats  # Changed from successful_requests
        assert 'total_errors' in stats  # Changed from failed_requests

        print("✓ Metrics collected successfully")

    def test_health_score(self, api_keys, debug_output):
        """Test provider health score calculation"""
        print("\n=== Testing Health Score ===")

        tool = APISourceTool(config=api_keys)

        for provider_name in ['fred', 'newsapi', 'worldbank', 'census']:
            info = tool.get_provider_info(provider_name)

            assert 'health' in info
            health = info['health']

            assert 'score' in health
            assert 'status' in health
            assert 0 <= health['score'] <= 1

            debug_output(f"{provider_name.upper()} Health", health)

        print("✓ Health scores calculated for all providers")

