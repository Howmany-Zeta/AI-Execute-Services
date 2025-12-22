"""
Unit tests for Enhanced Search Tool

Tests for quality analysis, intent detection, deduplication, context tracking,
and other enhanced features of the search tool package.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from aiecs.tools.search_tool import SearchTool
from aiecs.tools.search_tool.analyzers import (
    ResultQualityAnalyzer,
    QueryIntentAnalyzer,
    ResultSummarizer
)
from aiecs.tools.search_tool.deduplicator import ResultDeduplicator
from aiecs.tools.search_tool.context import SearchContext
from aiecs.tools.search_tool.metrics import EnhancedMetrics
from aiecs.tools.search_tool.constants import (
    QueryIntentType,
    CredibilityLevel
)


class TestResultQualityAnalyzer:
    """Test result quality analysis"""
    
    def setup_method(self):
        self.analyzer = ResultQualityAnalyzer()
    
    def test_analyze_result_quality(self):
        """Test quality analysis of a search result"""
        result = {
            'title': 'Python Tutorial - Official Documentation',
            'link': 'https://docs.python.org/tutorial',
            'snippet': 'Learn Python programming with this comprehensive tutorial covering basics and advanced topics.',
            'displayLink': 'docs.python.org',
            'metadata': {}
        }
        
        analysis = self.analyzer.analyze_result_quality(
            result,
            query='python tutorial',
            position=1
        )
        
        assert 'quality_score' in analysis
        assert 'authority_score' in analysis
        assert 'relevance_score' in analysis
        assert 'freshness_score' in analysis
        assert 'credibility_level' in analysis
        assert 'quality_signals' in analysis
        
        # High authority domain should have high authority score
        assert analysis['authority_score'] > 0.8
        
        # Good relevance for matching query terms
        assert analysis['relevance_score'] > 0.5
    
    def test_authority_score_calculation(self):
        """Test domain authority scoring"""
        # High authority domain
        assert self.analyzer._calculate_authority_score('docs.python.org') > 0.8
        
        # Government domain
        assert self.analyzer._calculate_authority_score('example.gov') > 0.8
        
        # Unknown domain gets default score
        assert self.analyzer._calculate_authority_score('unknown-site.com') == 0.5
    
    def test_relevance_score_calculation(self):
        """Test relevance scoring"""
        score = self.analyzer._calculate_relevance_score(
            query='machine learning tutorial',
            title='Machine Learning Tutorial for Beginners',
            snippet='Learn machine learning with this comprehensive tutorial',
            position=1
        )
        
        # Should have high relevance (all query terms present)
        assert score > 0.7
    
    def test_low_quality_detection(self):
        """Test low quality indicator detection"""
        result = {
            'title': 'Free Download - Click Here for Amazing Deals!',
            'link': 'http://clickbait-ads.com/download',
            'snippet': 'Download now and get free stuff!',
            'displayLink': 'clickbait-ads.com'
        }
        
        analysis = self.analyzer.analyze_result_quality(result, 'software', 1)
        
        # Should detect low quality indicators
        assert len(analysis['warnings']) > 0
        assert any('indicator' in w.lower() for w in analysis['warnings'])
    
    def test_rank_results(self):
        """Test result ranking"""
        results = [
            {
                '_quality': {
                    'quality_score': 0.5,
                    'authority_score': 0.6,
                    'relevance_score': 0.4
                },
                'title': 'Result 1'
            },
            {
                '_quality': {
                    'quality_score': 0.9,
                    'authority_score': 0.95,
                    'relevance_score': 0.85
                },
                'title': 'Result 2'
            },
            {
                '_quality': {
                    'quality_score': 0.7,
                    'authority_score': 0.8,
                    'relevance_score': 0.6
                },
                'title': 'Result 3'
            }
        ]
        
        # Rank by balanced quality
        ranked = self.analyzer.rank_results(results, 'balanced')
        assert ranked[0]['title'] == 'Result 2'
        assert ranked[1]['title'] == 'Result 3'
        assert ranked[2]['title'] == 'Result 1'
        
        # Rank by authority
        ranked = self.analyzer.rank_results(results, 'authority')
        assert ranked[0]['title'] == 'Result 2'


class TestQueryIntentAnalyzer:
    """Test query intent analysis"""
    
    def setup_method(self):
        self.analyzer = QueryIntentAnalyzer()
    
    def test_detect_how_to_intent(self):
        """Test detection of how-to queries"""
        analysis = self.analyzer.analyze_query_intent('how to learn python')
        
        assert analysis['intent_type'] == QueryIntentType.HOW_TO.value
        assert analysis['confidence'] > 0
        assert 'tutorial' in analysis['enhanced_query'].lower() or 'guide' in analysis['enhanced_query'].lower()
    
    def test_detect_definition_intent(self):
        """Test detection of definition queries"""
        analysis = self.analyzer.analyze_query_intent('what is machine learning')
        
        assert analysis['intent_type'] == QueryIntentType.DEFINITION.value
        assert analysis['confidence'] > 0
    
    def test_detect_comparison_intent(self):
        """Test detection of comparison queries"""
        analysis = self.analyzer.analyze_query_intent('python vs javascript')
        
        assert analysis['intent_type'] == QueryIntentType.COMPARISON.value
        assert analysis['confidence'] > 0
    
    def test_detect_news_intent(self):
        """Test detection of news queries"""
        analysis = self.analyzer.analyze_query_intent('latest AI news')
        
        assert analysis['intent_type'] == QueryIntentType.RECENT_NEWS.value
        assert analysis['confidence'] > 0
    
    def test_detect_academic_intent(self):
        """Test detection of academic queries"""
        analysis = self.analyzer.analyze_query_intent('machine learning research papers')
        
        assert analysis['intent_type'] == QueryIntentType.ACADEMIC.value
        assert analysis['confidence'] > 0
    
    def test_general_query(self):
        """Test general query without specific intent"""
        analysis = self.analyzer.analyze_query_intent('cats')
        
        assert analysis['intent_type'] == QueryIntentType.GENERAL.value
    
    def test_suggested_params(self):
        """Test suggested parameters generation"""
        analysis = self.analyzer.analyze_query_intent('how to build a website')
        
        assert 'suggested_params' in analysis
        assert len(analysis['suggested_params']) > 0
    
    def test_query_suggestions(self):
        """Test query optimization suggestions"""
        analysis = self.analyzer.analyze_query_intent('ai')
        
        assert 'suggestions' in analysis
        # Short query should get suggestion to add more terms
        assert any('short' in s.lower() for s in analysis['suggestions'])


class TestResultDeduplicator:
    """Test result deduplication"""
    
    def setup_method(self):
        self.deduplicator = ResultDeduplicator()
    
    def test_url_normalization(self):
        """Test URL normalization"""
        url1 = 'https://example.com/page?param=value#section'
        url2 = 'https://Example.com/page/'
        
        norm1 = self.deduplicator._normalize_url(url1)
        norm2 = self.deduplicator._normalize_url(url2)
        
        # Should normalize to same URL
        assert norm1 == norm2
    
    def test_deduplicate_exact_urls(self):
        """Test deduplication of exact duplicate URLs"""
        results = [
            {
                'title': 'Page 1',
                'link': 'https://example.com/page',
                'snippet': 'Content here'
            },
            {
                'title': 'Page 1 Again',
                'link': 'https://example.com/page?ref=google',
                'snippet': 'Content here'
            },
            {
                'title': 'Page 2',
                'link': 'https://example.com/other',
                'snippet': 'Different content'
            }
        ]
        
        unique = self.deduplicator.deduplicate_results(results)
        
        # Should keep only 2 unique URLs
        assert len(unique) == 2
    
    def test_deduplicate_similar_content(self):
        """Test deduplication of similar content"""
        results = [
            {
                'title': 'Python Tutorial',
                'link': 'https://site1.com/python',
                'snippet': 'Learn Python programming basics'
            },
            {
                'title': 'Python Tutorial',
                'link': 'https://site2.com/tutorial',
                'snippet': 'Learn Python programming basics'
            },
            {
                'title': 'JavaScript Guide',
                'link': 'https://site3.com/js',
                'snippet': 'Learn JavaScript development'
            }
        ]
        
        unique = self.deduplicator.deduplicate_results(results)
        
        # Should detect similar content and keep unique
        assert len(unique) == 2


class TestSearchContext:
    """Test search context management"""
    
    def setup_method(self):
        self.context = SearchContext(max_history=5)
    
    def test_add_search(self):
        """Test adding search to history"""
        results = [
            {'title': 'Result 1', 'link': 'https://example.com/1', 'displayLink': 'example.com'}
        ]
        
        self.context.add_search('test query', results)
        
        history = self.context.get_history()
        assert len(history) == 1
        assert history[0]['query'] == 'test query'
        assert history[0]['result_count'] == 1
    
    def test_history_size_limit(self):
        """Test history size limiting"""
        for i in range(10):
            self.context.add_search(f'query {i}', [])
        
        history = self.context.get_history()
        assert len(history) == 5  # max_history is 5
    
    def test_query_similarity(self):
        """Test query similarity calculation"""
        similarity = self.context._calculate_query_similarity(
            'machine learning tutorial',
            'machine learning guide'
        )
        
        # Should have high similarity (2 out of 3 words match)
        assert similarity > 0.5
    
    def test_learn_preferences(self):
        """Test learning user preferences from feedback"""
        results = [
            {'displayLink': 'docs.python.org'},
            {'displayLink': 'stackoverflow.com'},
            {'displayLink': 'spam-site.com'}
        ]
        
        feedback = {
            'clicked_indices': [0, 1],  # Liked first two
            'disliked_indices': [2]  # Disliked third
        }
        
        self.context.add_search('python help', results, feedback)
        
        prefs = self.context.get_preferences()
        assert 'docs.python.org' in prefs['preferred_domains']
        assert 'stackoverflow.com' in prefs['preferred_domains']
        assert 'spam-site.com' in prefs['avoided_domains']
    
    def test_contextual_suggestions(self):
        """Test contextual suggestions generation"""
        self.context.add_search('python tutorial', [])
        self.context.add_search('python documentation', [])
        
        suggestions = self.context.get_contextual_suggestions('python guide')
        
        assert 'related_queries' in suggestions
        # Should find related queries
        assert len(suggestions['related_queries']) > 0


class TestResultSummarizer:
    """Test result summarization"""
    
    def setup_method(self):
        self.summarizer = ResultSummarizer()
    
    def test_generate_summary(self):
        """Test summary generation"""
        results = [
            {
                'title': 'Result 1',
                'link': 'https://docs.python.org/1',
                'displayLink': 'docs.python.org',
                '_quality': {
                    'quality_score': 0.9,
                    'credibility_level': CredibilityLevel.HIGH.value,
                    'freshness_score': 0.8
                }
            },
            {
                'title': 'Result 2',
                'link': 'https://example.com/2',
                'displayLink': 'example.com',
                '_quality': {
                    'quality_score': 0.5,
                    'credibility_level': CredibilityLevel.MEDIUM.value,
                    'freshness_score': 0.5
                }
            },
            {
                'title': 'Result 3',
                'link': 'http://low-quality.com/3',
                'displayLink': 'low-quality.com',
                '_quality': {
                    'quality_score': 0.3,
                    'credibility_level': CredibilityLevel.LOW.value,
                    'freshness_score': 0.2
                }
            }
        ]
        
        summary = self.summarizer.generate_summary(results, 'python tutorial')
        
        assert summary['query'] == 'python tutorial'
        assert summary['total_results'] == 3
        assert summary['quality_distribution']['high'] == 1
        assert summary['quality_distribution']['medium'] == 1
        assert summary['quality_distribution']['low'] == 1
        
        # Should have recommended results
        assert len(summary['recommended_results']) > 0
        assert summary['recommended_results'][0]['_quality']['quality_score'] == 0.9
        
        # Should detect HTTPS warning
        assert any('HTTPS' in w for w in summary['warnings'])
    
    def test_empty_results_summary(self):
        """Test summary with no results"""
        summary = self.summarizer.generate_summary([], 'test query')
        
        assert summary['total_results'] == 0
        assert 'No results found' in summary['warnings']


class TestEnhancedMetrics:
    """Test enhanced metrics collection"""
    
    def setup_method(self):
        self.metrics = EnhancedMetrics()
    
    def test_record_successful_search(self):
        """Test recording successful search"""
        results = [
            {'_quality': {'quality_score': 0.8}},
            {'_quality': {'quality_score': 0.9}}
        ]
        
        self.metrics.record_search(
            query='test query',
            search_type='web',
            results=results,
            response_time_ms=150.0,
            cached=False,
            error=None
        )
        
        metrics = self.metrics.get_metrics()
        assert metrics['requests']['total'] == 1
        assert metrics['requests']['successful'] == 1
        assert metrics['requests']['failed'] == 0
        assert metrics['quality']['avg_results_per_query'] == 2
        assert metrics['quality']['avg_quality_score'] > 0
    
    def test_record_failed_search(self):
        """Test recording failed search"""
        error = Exception('Test error')
        
        self.metrics.record_search(
            query='test query',
            search_type='web',
            results=[],
            response_time_ms=100.0,
            cached=False,
            error=error
        )
        
        metrics = self.metrics.get_metrics()
        assert metrics['requests']['total'] == 1
        assert metrics['requests']['failed'] == 1
        assert metrics['errors']['error_rate'] == 1.0
        assert len(metrics['errors']['recent_errors']) == 1
    
    def test_cache_hit_rate(self):
        """Test cache hit rate calculation"""
        # Record some hits and misses
        for i in range(3):
            self.metrics.record_search('query', 'web', [], 100, cached=True)
        
        for i in range(7):
            self.metrics.record_search('query', 'web', [], 100, cached=False)
        
        metrics = self.metrics.get_metrics()
        assert metrics['cache']['hit_rate'] == 0.3  # 3 out of 10
    
    def test_health_score(self):
        """Test health score calculation"""
        # Record successful searches
        for i in range(10):
            self.metrics.record_search(
                'query', 'web',
                [{'_quality': {'quality_score': 0.8}}],
                200, cached=False
            )
        
        health = self.metrics.get_health_score()
        assert 0 <= health <= 1
        assert health > 0.5  # Should be healthy
    
    def test_generate_report(self):
        """Test report generation"""
        self.metrics.record_search('test', 'web', [], 100, cached=False)
        
        report = self.metrics.generate_report()
        assert 'Search Tool Performance Report' in report
        assert 'Overall Health Score' in report


class TestSearchToolIntegration:
    """Integration tests for SearchTool with enhanced features"""
    
    @patch('aiecs.tools.search_tool.core.build')
    def test_search_tool_initialization(self, mock_build):
        """Test SearchTool initialization with enhanced features"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        config = {
            'google_api_key': 'test_key',
            'google_cse_id': 'test_cse_id',
            'enable_quality_analysis': True,
            'enable_intent_analysis': True,
            'enable_deduplication': True,
            'enable_context_tracking': True,
            'enable_intelligent_cache': False  # Disable Redis for testing
        }
        
        tool = SearchTool(config)
        
        assert tool.quality_analyzer is not None
        assert tool.intent_analyzer is not None
        assert tool.deduplicator is not None
        assert tool.search_context is not None
        assert tool.metrics is not None
        assert tool.error_handler is not None
    
    @patch('aiecs.tools.search_tool.core.build')
    def test_search_tool_disabled_features(self, mock_build):
        """Test SearchTool with features disabled"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        config = {
            'google_api_key': 'test_key',
            'google_cse_id': 'test_cse_id',
            'enable_quality_analysis': False,
            'enable_intent_analysis': False,
            'enable_deduplication': False,
            'enable_context_tracking': False
        }
        
        tool = SearchTool(config)
        
        assert tool.quality_analyzer is None
        assert tool.intent_analyzer is None
        assert tool.deduplicator is None
        assert tool.search_context is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

