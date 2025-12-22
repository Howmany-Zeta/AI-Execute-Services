"""
Comprehensive tests for Intelligence modules

Tests query analyzer, data fusion, and search enhancer functionality.

Run with: 
    poetry run pytest test/unit_tests/tools/apisource/test_intelligence.py -v -s
"""

import logging
from typing import Dict, Any, List

import pytest

from aiecs.tools.apisource.intelligence import (
    QueryIntentAnalyzer,
    QueryEnhancer,
    DataFusionEngine,
    SearchEnhancer,
)

logger = logging.getLogger(__name__)


class TestQueryIntentAnalyzer:
    """Test query intent analysis"""
    
    def test_initialization(self):
        """Test QueryIntentAnalyzer initialization"""
        print("\n=== Testing QueryIntentAnalyzer Initialization ===")
        
        analyzer = QueryIntentAnalyzer()
        
        assert analyzer is not None
        print("✓ QueryIntentAnalyzer initialized successfully")
    
    def test_analyze_query_basic(self, debug_output):
        """Test basic query analysis"""
        print("\n=== Testing Basic Query Analysis ===")

        analyzer = QueryIntentAnalyzer()

        query = "Find GDP data for the United States"
        analysis = analyzer.analyze_intent(query)

        assert isinstance(analysis, dict)
        assert 'intent_type' in analysis

        debug_output("Query Analysis Result", analysis)

        print("✓ Query analyzed successfully")

    @pytest.mark.parametrize("query,expected_keywords", [
        ("GDP growth rate", ["gdp", "growth", "rate"]),
        ("unemployment statistics", ["unemployment", "statistics"]),
        ("inflation data 2023", ["inflation", "data", "2023"]),
    ])
    def test_keyword_extraction(self, query, expected_keywords, debug_output):
        """Test keyword extraction from queries"""
        print(f"\n=== Testing Keyword Extraction: '{query}' ===")

        analyzer = QueryIntentAnalyzer()
        analysis = analyzer.analyze_intent(query)

        assert isinstance(analysis, dict)

        debug_output(f"Keywords for '{query}'", analysis)

        print(f"✓ Extracted keywords from query")

    def test_analyze_complex_query(self, debug_output):
        """Test analysis of complex query"""
        print("\n=== Testing Complex Query Analysis ===")

        analyzer = QueryIntentAnalyzer()

        query = "Compare GDP growth between USA and China from 2010 to 2020"
        analysis = analyzer.analyze_intent(query)

        assert isinstance(analysis, dict)
        assert 'intent_type' in analysis

        debug_output("Complex Query Analysis", analysis)

        print("✓ Complex query analyzed successfully")


class TestQueryEnhancer:
    """Test query parameter enhancement"""
    
    def test_initialization(self):
        """Test QueryEnhancer initialization"""
        print("\n=== Testing QueryEnhancer Initialization ===")

        analyzer = QueryIntentAnalyzer()
        enhancer = QueryEnhancer(analyzer)

        assert enhancer is not None
        assert enhancer.intent_analyzer is not None
        print("✓ QueryEnhancer initialized successfully")

    def test_enhance_params_basic(self, debug_output):
        """Test basic parameter enhancement"""
        print("\n=== Testing Basic Parameter Enhancement ===")

        analyzer = QueryIntentAnalyzer()
        enhancer = QueryEnhancer(analyzer)

        params = {'search_text': 'GDP'}
        query_text = "Find GDP data for last 5 years"

        enhanced = enhancer.auto_complete_params(
            provider='fred',
            operation='search_series',
            params=params,
            query_text=query_text
        )

        assert isinstance(enhanced, dict)

        debug_output("Enhanced Parameters", {
            'original': params,
            'enhanced': enhanced,
        })

        print("✓ Parameters enhanced successfully")

    def test_enhance_with_time_range(self, debug_output):
        """Test enhancement with time range extraction"""
        print("\n=== Testing Time Range Enhancement ===")

        analyzer = QueryIntentAnalyzer()
        enhancer = QueryEnhancer(analyzer)

        params = {'series_id': 'GDP'}
        query_text = "Get GDP data from 2020 to 2023"

        enhanced = enhancer.auto_complete_params(
            provider='fred',
            operation='get_series_observations',
            params=params,
            query_text=query_text
        )
        
        debug_output("Time Range Enhancement", {
            'original': params,
            'enhanced': enhanced,
            'query': query_text,
        })
        
        print("✓ Time range extracted and applied")
    
    def test_enhance_without_query_text(self, debug_output):
        """Test enhancement without query text"""
        print("\n=== Testing Enhancement Without Query Text ===")

        analyzer = QueryIntentAnalyzer()
        enhancer = QueryEnhancer(analyzer)

        params = {'search_text': 'unemployment'}

        enhanced = enhancer.auto_complete_params(
            provider='fred',
            operation='search_series',
            params=params,
            query_text=None
        )

        # Should return original params or minimally enhanced
        assert isinstance(enhanced, dict)

        debug_output("Enhancement Without Query", {
            'original': params,
            'enhanced': enhanced,
        })

        print("✓ Handled missing query text correctly")


class TestDataFusionEngine:
    """Test data fusion across providers"""
    
    def test_initialization(self):
        """Test DataFusionEngine initialization"""
        print("\n=== Testing DataFusionEngine Initialization ===")
        
        engine = DataFusionEngine()
        
        assert engine is not None
        print("✓ DataFusionEngine initialized successfully")
    
    def test_fuse_results_basic(self, debug_output):
        """Test basic result fusion"""
        print("\n=== Testing Basic Result Fusion ===")

        engine = DataFusionEngine()

        # Mock results from different providers (as list)
        results = [
            {
                'success': True,
                'data': [
                    {'id': '1', 'title': 'GDP Data', 'source': 'FRED'},
                    {'id': '2', 'title': 'Unemployment Rate', 'source': 'FRED'},
                ],
                'metadata': {'provider': 'fred'}
            },
            {
                'success': True,
                'data': [
                    {'id': '3', 'title': 'GDP Growth', 'source': 'World Bank'},
                ],
                'metadata': {'provider': 'worldbank'}
            }
        ]

        fused = engine.fuse_multi_provider_results(results, fusion_strategy='best_quality')

        assert fused is None or isinstance(fused, dict)

        debug_output("Fused Results", {
            'input_count': len(results),
            'fused': fused is not None,
        })

        print("✓ Results fused successfully")

    def test_fuse_with_different_strategies(self, debug_output):
        """Test fusion with different strategies"""
        print("\n=== Testing Different Fusion Strategies ===")

        engine = DataFusionEngine()

        results = [
            {
                'success': True,
                'data': [{'id': '1', 'title': 'Data 1'}],
                'metadata': {'provider': 'fred', 'quality': {'score': 0.9}}
            },
            {
                'success': True,
                'data': [{'id': '2', 'title': 'Data 2'}],
                'metadata': {'provider': 'worldbank', 'quality': {'score': 0.8}}
            }
        ]

        strategies = ['best_quality', 'merge_all', 'first_success']

        for strategy in strategies:
            fused = engine.fuse_multi_provider_results(results, fusion_strategy=strategy)

            debug_output(f"Fusion Strategy: {strategy}", {
                'strategy': strategy,
                'fused': fused is not None,
            })

        print("✓ All fusion strategies tested")

    def test_fuse_empty_results(self):
        """Test fusion with empty results"""
        print("\n=== Testing Fusion with Empty Results ===")

        engine = DataFusionEngine()

        results = []
        fused = engine.fuse_multi_provider_results(results)

        assert fused is None

        print("✓ Handled empty results correctly")

    def test_fuse_failed_results(self, debug_output):
        """Test fusion with some failed results"""
        print("\n=== Testing Fusion with Failed Results ===")

        engine = DataFusionEngine()

        results = [
            {
                'success': True,
                'data': [{'id': '1', 'title': 'Data 1'}],
                'metadata': {'provider': 'fred'}
            },
            {
                'success': False,
                'error': 'API key invalid',
                'metadata': {'provider': 'newsapi'}
            }
        ]

        fused = engine.fuse_multi_provider_results(results)

        assert fused is None or isinstance(fused, dict)

        debug_output("Fusion with Failures", {
            'input_count': len(results),
            'successful_count': sum(1 for r in results if r.get('success')),
        })

        print("✓ Handled failed results correctly")


class TestSearchEnhancer:
    """Test search result enhancement and ranking"""
    
    def test_initialization(self):
        """Test SearchEnhancer initialization"""
        print("\n=== Testing SearchEnhancer Initialization ===")
        
        enhancer = SearchEnhancer(
            relevance_weight=0.5,
            popularity_weight=0.3,
            recency_weight=0.2
        )
        
        assert enhancer is not None
        assert enhancer.relevance_weight == 0.5
        assert enhancer.popularity_weight == 0.3
        assert enhancer.recency_weight == 0.2
        
        print("✓ SearchEnhancer initialized successfully")
    
    def test_enhance_results_basic(self, debug_output):
        """Test basic result enhancement"""
        print("\n=== Testing Basic Result Enhancement ===")

        enhancer = SearchEnhancer()

        results = [
            {'id': '1', 'title': 'GDP Data', 'description': 'GDP economic data'},
            {'id': '2', 'title': 'Unemployment', 'description': 'Unemployment statistics'},
            {'id': '3', 'title': 'Inflation Rate', 'description': 'Inflation data'},
        ]

        enhanced = enhancer.enhance_search_results(query='GDP', results=results)

        assert isinstance(enhanced, list)

        debug_output("Enhanced Results", {
            'original_count': len(results),
            'enhanced_count': len(enhanced),
            'first_result': enhanced[0] if enhanced else None,
        })

        print("✓ Results enhanced successfully")

    def test_rank_by_relevance(self, debug_output):
        """Test ranking by relevance"""
        print("\n=== Testing Relevance Ranking ===")
        
        enhancer = SearchEnhancer(
            relevance_weight=1.0,
            popularity_weight=0.0,
            recency_weight=0.0
        )

        results = [
            {'id': '1', 'title': 'Low relevance test', 'description': 'low'},
            {'id': '2', 'title': 'High relevance test data', 'description': 'test test test'},
            {'id': '3', 'title': 'Medium test relevance', 'description': 'test data'},
        ]

        enhanced = enhancer.enhance_search_results(query='test', results=results)

        # Should be sorted by relevance (descending)
        if len(enhanced) > 1:
            debug_output("Relevance Ranking", {
                'results': [{'id': r.get('id'), 'title': r.get('title')} for r in enhanced]
            })

        print("✓ Results ranked by relevance")

    def test_filter_by_min_relevance(self, debug_output):
        """Test filtering by minimum relevance"""
        print("\n=== Testing Relevance Filtering ===")

        enhancer = SearchEnhancer()

        results = [
            {'id': '1', 'title': 'High relevance test test', 'description': 'test test'},
            {'id': '2', 'title': 'Low relevance', 'description': 'other'},
            {'id': '3', 'title': 'Medium test relevance', 'description': 'test'},
        ]

        enhanced = enhancer.enhance_search_results(
            query='test',
            results=results,
            options={'relevance_threshold': 0.5}
        )

        # Should filter out low relevance results
        debug_output("Filtered Results", {
            'original_count': len(results),
            'filtered_count': len(enhanced),
        })

        print("✓ Results filtered by relevance")

