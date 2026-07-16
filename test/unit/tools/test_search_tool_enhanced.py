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

    def test_demographic_causal_fixture_rewrite(self):
        """M-D.1a: research queries get non-idle intent and keyword rewrite."""
        analysis = self.analyzer.analyze_query_intent('Why is Tesla popular among young people?')

        assert analysis['intent_type'] == QueryIntentType.DEMOGRAPHIC.value
        assert analysis['confidence'] > 0
        assert analysis['rewrite_applied'] is True
        assert analysis['enhanced_query'] != analysis['original_query']
        assert '?' not in analysis['enhanced_query']
        assert 'Tesla' in analysis['enhanced_query']
        assert 'survey' in analysis['enhanced_query'].lower()

    def test_comma_stack_fixture_rewrite(self):
        """M-D.1a: comma-stacked prose is rewritten, not passed verbatim."""
        query = (
            "criticisms of Tesla and Elon Musk affecting young people's popularity, "
            "Gen Z, Millennials, reports, articles"
        )
        analysis = self.analyzer.analyze_query_intent(query)

        assert analysis['intent_type'] == QueryIntentType.DEMOGRAPHIC.value
        assert analysis['rewrite_applied'] is True
        assert analysis['enhanced_query'] != query
        assert 'reports' not in analysis['enhanced_query'].lower()
        assert 'articles' not in analysis['enhanced_query'].lower()


class TestSearchResultPostProcessing:
    """Test re-rank partition and must_scrape_urls (M-D.1b)."""

    def setup_method(self):
        self.analyzer = ResultQualityAnalyzer()

    def _build_result(self, domain: str, title: str, query: str, position: int = 1) -> dict:
        result = {
            'title': title,
            'link': f'https://{domain}/page',
            'snippet': title,
            'displayLink': domain,
            'metadata': {},
        }
        quality = self.analyzer.analyze_result_quality(result, query, position)
        result['_quality'] = quality
        result['_quality_summary'] = {
            'score': quality['quality_score'],
            'level': quality['credibility_level'],
            'is_authoritative': quality['authority_score'] > 0.8,
            'is_relevant': quality['relevance_score'] > 0.7,
            'is_fresh': quality['freshness_score'] > 0.7,
            'warnings_count': len(quality['warnings']),
        }
        return result

    def test_partition_demotes_social_noise(self):
        from aiecs.tools.search_tool.analyzers import partition_search_results

        query = 'Tesla Gen Z Millennials popularity survey'
        results = [
            self._build_result('facebook.com', 'Tesla fans', query, 1),
            self._build_result('reddit.com', 'Tesla thread', query, 2),
            self._build_result('yougov.com', 'Tesla brand survey Gen Z', query, 3),
        ]

        primary, low_signal, must_scrape = partition_search_results(
            self.analyzer,
            results,
            num_results=2,
        )

        assert [item['displayLink'] for item in primary] == ['yougov.com']
        assert {item['displayLink'] for item in low_signal} == {'facebook.com', 'reddit.com'}
        assert len(must_scrape) >= 1
        assert must_scrape[0]['url'].startswith('https://yougov.com')

    def test_build_must_scrape_urls_requires_signal(self):
        from aiecs.tools.search_tool.analyzers import build_must_scrape_urls

        weak = self._build_result('facebook.com', 'noise', 'unrelated query', 1)
        strong = self._build_result('yougov.com', 'Tesla survey Gen Z Millennials', 'Tesla Gen Z survey', 1)

        must_scrape = build_must_scrape_urls([weak, strong])
        assert len(must_scrape) == 1
        assert 'yougov.com' in must_scrape[0]['url']
        assert must_scrape[0]['score'] > 0


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
        
        # Jaccard: 2 shared / 4 union = 0.5 for tutorial vs guide
        assert similarity >= 0.5
    
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
        self.context.add_search('python machine learning tutorial', [])
        self.context.add_search('python machine learning guide', [])
        
        suggestions = self.context.get_contextual_suggestions('python machine learning course')
        
        assert 'related_queries' in suggestions
        # Jaccard > 0.5 against history entries that share most tokens
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
    
    def test_search_tool_initialization(self):
        """Test SearchTool initialization with enhanced features"""
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

    def test_search_tool_disabled_features(self):
        """Test SearchTool with features disabled"""
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


class TestSearchBatch:
    """Test batch search (M-D.1 Phase 2)."""

    @pytest.fixture
    def mock_search_tool(self):
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()

        responses = [
            {
                'items': [
                    {
                        'title': 'Tesla Gen Z survey',
                        'link': 'https://yougov.com/tesla-gen-z',
                        'snippet': 'Tesla popularity among Gen Z survey results',
                        'displayLink': 'yougov.com',
                    },
                    {
                        'title': 'Tesla Reddit thread',
                        'link': 'https://reddit.com/r/tesla/popularity',
                        'snippet': 'Discussion about Tesla popularity',
                        'displayLink': 'reddit.com',
                    },
                ]
            },
            {
                'items': [
                    {
                        'title': 'Tesla brand perception Millennials',
                        'link': 'https://kpmg.com/tesla-millennials',
                        'snippet': 'Millennials Tesla brand perception report',
                        'displayLink': 'kpmg.com',
                    },
                    {
                        'title': 'Tesla Facebook group',
                        'link': 'https://facebook.com/groups/tesla',
                        'snippet': 'Facebook group for Tesla fans',
                        'displayLink': 'facebook.com',
                    },
                ]
            },
        ]
        mock_list.execute.side_effect = responses
        mock_cse.list.return_value = mock_list
        mock_service.cse.return_value = mock_cse

        tool = SearchTool(
            {
                'google_api_key': 'test_key',
                'google_cse_id': 'test_cse_id',
                'enable_intelligent_cache': False,
            }
        )
        tool.service = mock_service
        yield tool

    def test_merge_batch_search_results_deduplicates_urls(self):
        from aiecs.tools.search_tool.analyzers import merge_batch_search_results

        analyzer = ResultQualityAnalyzer()
        deduplicator = ResultDeduplicator()
        shared_link = 'https://yougov.com/shared'
        per_query = [
            {
                'query': 'query-a',
                '_metadata': {'query': 'query-a'},
                'results': [
                    {
                        'title': 'A1',
                        'link': shared_link,
                        'snippet': 'A1',
                        'displayLink': 'yougov.com',
                        '_quality': {'quality_score': 0.9, 'authority_score': 0.92, 'relevance_score': 0.8},
                        '_quality_summary': {'is_relevant': True, 'is_authoritative': True, 'is_fresh': False},
                    }
                ],
            },
            {
                'query': 'query-b',
                '_metadata': {'query': 'query-b'},
                'results': [
                    {
                        'title': 'B1 duplicate',
                        'link': shared_link,
                        'snippet': 'B1',
                        'displayLink': 'yougov.com',
                        '_quality': {'quality_score': 0.85, 'authority_score': 0.92, 'relevance_score': 0.75},
                        '_quality_summary': {'is_relevant': True, 'is_authoritative': True, 'is_fresh': False},
                    },
                    {
                        'title': 'B2',
                        'link': 'https://kpmg.com/report',
                        'snippet': 'B2',
                        'displayLink': 'kpmg.com',
                        '_quality': {'quality_score': 0.88, 'authority_score': 0.88, 'relevance_score': 0.78},
                        '_quality_summary': {'is_relevant': True, 'is_authoritative': True, 'is_fresh': False},
                    },
                ],
            },
        ]

        merged, low_signal, must_scrape = merge_batch_search_results(
            analyzer,
            per_query,
            merged_num_results=3,
            deduplicator=deduplicator,
        )

        links = [item['link'] for item in merged]
        assert len(links) == len(set(links))
        assert shared_link in links
        assert len(must_scrape) >= 1

    def test_search_batch_returns_per_query_and_merged(self, mock_search_tool):
        result = mock_search_tool.search_batch(
            queries=[
                'Why is Tesla popular among young people?',
                'Tesla Gen Z brand perception survey',
            ],
            num_results=2,
            merged_num_results=2,
        )

        assert len(result['per_query']) == 2
        assert result['_metadata']['batch_size'] == 2
        assert len(result['results']) <= 2
        assert all('results' in bucket for bucket in result['per_query'])
        assert result['per_query'][0]['query'] != result['per_query'][1]['query']
        assert any(
            item.get('displayLink') in {'yougov.com', 'kpmg.com'}
            for item in result['results']
        )

    def test_search_batch_rejects_too_many_queries(self, mock_search_tool):
        from aiecs.tools.search_tool.constants import ValidationError

        with pytest.raises(ValidationError):
            mock_search_tool.search_batch(
                queries=[
                    'query one',
                    'query two',
                    'query three',
                    'query four',
                ]
            )

    def test_search_batch_rejects_non_web_type(self, mock_search_tool):
        from aiecs.tools.search_tool.constants import ValidationError

        with pytest.raises(ValidationError):
            mock_search_tool.search_batch(
                queries=['query one', 'query two'],
                search_type='news',
            )


class TestGroundingPipelineE2E:
    """P4-04: Tesla / comma-stack fixtures through full search_web pipeline."""

    @pytest.mark.gate_p4
    def test_tesla_demographic_search_web_must_scrape_after_partition(self):
        from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
        from test.unit.tools.search_tool.fakes import FakeGroundingBackend

        gemini = FakeGroundingBackend(
            'gemini',
            citations=[
                {
                    'url': 'https://www.yougov.com/topics/tesla-gen-z',
                    'title': 'YouGov Tesla Gen Z brand survey',
                    'domain': 'www.yougov.com',
                    'snippet': '',
                },
                {
                    'url': 'https://www.facebook.com/groups/tesla',
                    'title': 'Tesla fans',
                    'domain': 'www.facebook.com',
                    'snippet': '',
                },
            ],
        )
        original = gemini.search

        def with_answer(params):
            result = original(params)
            result.answer = 'Synthesized Tesla Gen Z overview'
            return result

        gemini.search = with_answer  # type: ignore[method-assign]

        tool = SearchTool(
            {
                'grounding_provider': 'auto',
                'grounding_provider_chain': 'gemini,grok,google_cse',
                'enable_intent_analysis': True,
                'enable_quality_analysis': True,
                'enable_intelligent_cache': False,
                'enable_deduplication': False,
                'enable_context_tracking': False,
            }
        )
        registry = GroundingBackendRegistry()
        registry.register(gemini)
        registry.register(FakeGroundingBackend('grok', configured=False))
        registry.register(FakeGroundingBackend('google_cse', configured=False))
        tool._registry = registry

        out = tool.search_web(
            'Why is Tesla popular among young people?',
            num_results=5,
            auto_enhance=True,
        )

        assert out['_search_metadata']['partition_profile'] == 'grounding'
        assert out['_search_metadata']['intent_type'] == QueryIntentType.DEMOGRAPHIC.value
        assert len(out['must_scrape_urls']) >= 1
        assert out.get('grounding_answer')
        joined = ' '.join(
            [*(r.get('displayLink', '') for r in out['results']), *(u['url'] for u in out['must_scrape_urls'])]
        )
        assert 'yougov.com' in joined
        assert any('facebook.com' in (r.get('displayLink') or '') for r in out['low_signal'])

    @pytest.mark.gate_p4
    def test_comma_stack_search_web_uses_rewritten_query(self):
        from aiecs.tools.search_tool.backends.registry import GroundingBackendRegistry
        from test.unit.tools.search_tool.fakes import FakeGroundingBackend

        query = (
            "criticisms of Tesla and Elon Musk affecting young people's popularity, "
            "Gen Z, Millennials, reports, articles"
        )
        gemini = FakeGroundingBackend(
            'gemini',
            citations=[
                {
                    'url': 'https://www.yougov.com/tesla',
                    'title': 'YouGov',
                    'domain': 'www.yougov.com',
                    'snippet': '',
                }
            ],
        )
        tool = SearchTool(
            {
                'grounding_provider': 'auto',
                'enable_intent_analysis': True,
                'enable_quality_analysis': True,
                'enable_intelligent_cache': False,
                'enable_deduplication': False,
                'enable_context_tracking': False,
            }
        )
        registry = GroundingBackendRegistry()
        registry.register(gemini)
        registry.register(FakeGroundingBackend('grok', configured=False))
        registry.register(FakeGroundingBackend('google_cse', configured=False))
        tool._registry = registry

        out = tool.search_web(query, auto_enhance=True)
        enhanced = out['_search_metadata']['enhanced_query']
        assert enhanced != query
        assert 'reports' not in enhanced.lower()
        assert gemini.search_calls[0].query == enhanced


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

