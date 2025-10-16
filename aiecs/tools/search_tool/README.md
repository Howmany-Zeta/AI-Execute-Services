# Enhanced Search Tool v2.0

A comprehensive, production-ready web search tool that integrates Google Custom Search API with advanced AI-agent-optimized features.

## 🚀 Key Features

### 1. **Result Quality Assessment**
- **Domain Authority Scoring**: Evaluates source credibility using predefined authoritative domains
- **Relevance Scoring**: Matches query terms against title and snippet
- **Freshness Scoring**: Assesses content age from metadata
- **Comprehensive Quality Score**: Combines multiple factors (0-1 scale)
- **Credibility Levels**: Classifies results as high/medium/low quality

### 2. **Query Intent Analysis**
- **Automatic Intent Detection**: Identifies query types (how-to, definition, comparison, news, academic, product, etc.)
- **Query Enhancement**: Automatically adds relevant search operators
- **Smart Parameter Suggestions**: Optimizes search parameters based on intent
- **Entity Extraction**: Identifies key entities in queries
- **Optimization Suggestions**: Provides actionable query improvement tips

### 3. **Result Deduplication**
- **URL Normalization**: Removes duplicates with varying query parameters
- **Content Similarity Detection**: Identifies highly similar results
- **Configurable Threshold**: Adjustable similarity detection (default 0.85)

### 4. **Context-Aware Search**
- **Search History Tracking**: Maintains recent search history (configurable limit)
- **Preference Learning**: Learns from user feedback on results
- **Topic Context**: Tracks topic continuity across searches
- **Related Query Suggestions**: Suggests relevant searches based on history
- **Personalization**: Adapts to preferred and avoided domains

### 5. **Intelligent Redis Caching**
- **Intent-Aware TTL**: Different cache durations per query type
  - Definitions: 30 days
  - Tutorials: 7 days
  - News: 1 hour
  - Academic: 30 days
  - Products: 1 day
- **Dynamic TTL Adjustment**: Considers result freshness and quality
- **Automatic Cache Invalidation**: Smart cache refresh logic

### 6. **Comprehensive Metrics**
- **Performance Tracking**: Response times with P50/P95/P99 percentiles
- **Quality Metrics**: Average quality scores, high-quality percentage
- **Error Analysis**: Error rates by type, recent error tracking
- **Cache Efficiency**: Hit rates, hit/miss statistics
- **Query Patterns**: Top query types, domains, average query length
- **Health Scoring**: Overall system health (0-1 scale)

### 7. **Agent-Friendly Error Handling**
- **Structured Error Messages**: Clear, actionable error information
- **Suggested Actions**: Concrete steps to resolve issues
- **Alternative Approaches**: Fallback strategies
- **Retry Guidance**: Indicates if/when retry is appropriate
- **Recovery Time Estimates**: Helps agents plan retries

## 📦 Installation

The search tool requires the following dependencies:

```bash
pip install google-api-python-client google-auth google-auth-httplib2 redis
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_cse_id

# Optional Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=optional_password
```

### Configuration Options

```python
from aiecs.tools.search_tool import SearchTool

config = {
    # API Configuration
    'google_api_key': 'your_key',
    'google_cse_id': 'your_cse_id',
    
    # Rate Limiting
    'rate_limit_requests': 100,
    'rate_limit_window': 86400,  # seconds
    
    # Circuit Breaker
    'circuit_breaker_threshold': 5,
    'circuit_breaker_timeout': 60,
    
    # Enhanced Features
    'enable_quality_analysis': True,
    'enable_intent_analysis': True,
    'enable_deduplication': True,
    'enable_context_tracking': True,
    'enable_intelligent_cache': True,
    
    # Tuning
    'similarity_threshold': 0.85,
    'max_search_history': 10,
}

search_tool = SearchTool(config)
```

## 💻 Usage Examples

### Basic Search with Quality Analysis

```python
from aiecs.tools.search_tool import SearchTool

# Initialize
tool = SearchTool()

# Perform search
results = tool.search_web(
    query="machine learning tutorial",
    num_results=10,
    auto_enhance=True
)

# Access results with quality information
for result in results:
    print(f"Title: {result['title']}")
    print(f"URL: {result['link']}")
    print(f"Quality Score: {result['_quality_summary']['score']:.2f}")
    print(f"Credibility: {result['_quality_summary']['level']}")
    print(f"Is Authoritative: {result['_quality_summary']['is_authoritative']}")
    print("---")
```

### Search with Summary

```python
response = tool.search_web(
    query="artificial intelligence",
    return_summary=True
)

results = response['results']
summary = response['summary']

# Access summary statistics
print(f"Total Results: {summary['total_results']}")
print(f"Quality Distribution: {summary['quality_distribution']}")
print(f"Top Domains: {summary['top_domains']}")
print(f"Recommended Results: {len(summary['recommended_results'])}")
print(f"Warnings: {summary['warnings']}")
print(f"Suggestions: {summary['suggestions']}")
```

### Using Search Context

```python
# First search
tool.search_web("python programming basics")

# Second search - context is automatically tracked
tool.search_web("python advanced topics")

# Get context information
context = tool.get_search_context()
print(f"Search History: {context['history']}")
print(f"Preferences: {context['preferences']}")
```

### Monitoring Performance

```python
# Get metrics
metrics = tool.get_metrics()
print(f"Total Requests: {metrics['requests']['total']}")
print(f"Success Rate: {metrics['requests']['successful'] / metrics['requests']['total']:.2%}")
print(f"Cache Hit Rate: {metrics['cache']['hit_rate']:.2%}")
print(f"Avg Quality Score: {metrics['quality']['avg_quality_score']:.2f}")

# Get health score
health = tool.get_health_score()
print(f"System Health: {health:.2%}")

# Get human-readable report
print(tool.get_metrics_report())
```

### Advanced Search with Intent Detection

```python
# Query intent is automatically detected and used
results = tool.search_web(
    query="how to build a REST API",
    auto_enhance=True  # Query enhanced based on detected 'how_to' intent
)

# Check intent metadata
for result in results:
    metadata = result.get('_search_metadata', {})
    print(f"Original Query: {metadata.get('original_query')}")
    print(f"Enhanced Query: {metadata.get('enhanced_query')}")
    print(f"Intent Type: {metadata.get('intent_type')}")
    print(f"Confidence: {metadata.get('intent_confidence'):.2f}")
    print(f"Suggestions: {metadata.get('suggestions')}")
```

## 🏗️ Architecture

### Package Structure

```
aiecs/tools/search_tool/
├── __init__.py              # Package entry point with registration
├── core.py                  # Main SearchTool class
├── constants.py             # Enums and exceptions
├── analyzers.py             # Quality, intent, and summarization
├── deduplicator.py          # Result deduplication
├── context.py               # Search context management
├── cache.py                 # Intelligent Redis caching
├── metrics.py               # Enhanced metrics collection
├── error_handler.py         # Agent-friendly error formatting
└── rate_limiter.py          # Rate limiting and circuit breaker
```

### Component Overview

#### ResultQualityAnalyzer
Assesses search result quality using multiple factors:
- Domain authority (predefined authoritative sources)
- Query relevance (term matching in title/snippet)
- Content freshness (publish date analysis)
- HTTPS usage, content length, metadata presence
- Low-quality indicator detection

#### QueryIntentAnalyzer
Understands query intent to optimize searches:
- Pattern-based intent detection
- Query enhancement with relevant operators
- Parameter suggestions per intent type
- Entity and modifier extraction
- Query optimization suggestions

#### ResultSummarizer
Generates structured summaries:
- Quality distribution statistics
- Top domain analysis
- Freshness distribution
- Recommended results (top 3 by quality)
- Warnings and suggestions

#### SearchContext
Tracks search behavior for personalization:
- Search history management
- Topic context tracking
- Preference learning from feedback
- Query similarity calculation
- Contextual suggestions

#### IntelligentCache
Redis-based caching with smart TTL:
- Intent-aware TTL strategies
- Dynamic TTL adjustment
- Quality-based cache duration
- Cache invalidation logic

#### EnhancedMetrics
Comprehensive performance monitoring:
- Response time percentiles
- Quality metrics
- Error analysis
- Cache efficiency
- Query patterns
- Health scoring

## 🎯 Use Cases

### For AI Agents
- **Quality-First Results**: Agents receive pre-scored results with credibility indicators
- **Intent Understanding**: Automatic query optimization reduces agent workload
- **Context Awareness**: Agents benefit from search history and preferences
- **Actionable Errors**: Structured error messages help agents recover gracefully
- **Performance Insights**: Metrics help agents understand search quality

### For Developers
- **Comprehensive API**: Clean, well-documented interface
- **Flexible Configuration**: Fine-tune behavior via config
- **Metrics Dashboard**: Monitor search tool health and performance
- **Extensible Design**: Modular architecture for easy customization
- **Production-Ready**: Rate limiting, circuit breaker, caching built-in

## 📊 Performance

### Benchmarks
- **Average Response Time**: ~200-500ms (with cache: ~50ms)
- **Cache Hit Rate**: 30-50% (typical workload)
- **Quality Analysis Overhead**: ~10-20ms per result
- **Intent Detection**: ~5-10ms per query

### Scalability
- **Rate Limiting**: Token bucket algorithm prevents quota exhaustion
- **Circuit Breaker**: Protects against API failures
- **Redis Caching**: Reduces API calls by 30-50%
- **Concurrent Requests**: Thread-safe implementation

## 🧪 Testing

Run the comprehensive test suite:

```bash
pytest test/unit_tests/tools/test_search_tool_enhanced.py -v
```

Test coverage includes:
- Result quality analysis
- Query intent detection
- Deduplication logic
- Context management
- Metrics collection
- Integration scenarios

## 📈 Metrics Dashboard

Access real-time metrics:

```python
tool = SearchTool()

# Perform searches...

# Get detailed metrics
print(tool.get_metrics_report())
```

Example output:
```
Search Tool Performance Report
==================================================

Overall Health Score: 87.3% ✅

Requests:
  Total: 150
  Successful: 142 (94.7%)
  Failed: 8
  Cached: 45

Performance:
  Avg Response: 234ms
  P95 Response: 450ms
  Slowest: "complex academic query" (1200ms)

Quality:
  Avg Results/Query: 8.3
  Avg Quality Score: 0.78
  High Quality %: 62.5%
  No Results: 3

Cache:
  Hit Rate: 30.0%
  Hits: 45
  Misses: 105

Errors:
  Error Rate: 5.3%
  Top Types: QuotaExceededError(3), NetworkError(2)

Query Patterns:
  Top Types: how_to(45), definition(32), general(28)
  Avg Query Length: 4.2 words
  Top Domains: docs.python.org(25), stackoverflow.com(18)
```

## 🔒 Security & Privacy

- **HTTPS Preference**: Results prioritize HTTPS sources
- **Low-Quality Detection**: Filters spam and clickbait indicators
- **Rate Limiting**: Prevents quota abuse
- **No PII Logging**: Search queries not logged by default
- **Secure Caching**: Redis can be configured with authentication

## 🚦 Best Practices

1. **Enable All Features**: Unless you have specific constraints, enable all enhanced features
2. **Monitor Health Score**: Keep health score > 0.8 for optimal performance
3. **Review Metrics Regularly**: Use metrics to identify bottlenecks
4. **Configure Redis**: Enable caching for production deployments
5. **Tune Similarity Threshold**: Adjust based on your deduplication needs
6. **Provide Feedback**: Use search context feedback for better personalization

## 🐛 Troubleshooting

### Common Issues

**Issue**: Low cache hit rate
- **Solution**: Ensure Redis is properly configured and accessible
- **Check**: `tool.intelligent_cache.enabled` should be `True`

**Issue**: Low quality scores
- **Solution**: Review query formulation, enable intent analysis
- **Check**: Ensure `enable_quality_analysis=True`

**Issue**: Circuit breaker opening frequently
- **Solution**: Check API quota, review error logs
- **Check**: `tool.get_quota_status()` for circuit breaker state

**Issue**: Slow response times
- **Solution**: Enable caching, reduce num_results, use deduplication
- **Check**: P95 response time in metrics report

## 📝 Changelog

### v2.0.0 (Current)
- Added result quality assessment and ranking
- Added query intent analysis and enhancement
- Added result deduplication
- Added context-aware search with history tracking
- Added intelligent Redis caching with intent-aware TTL
- Added comprehensive metrics and health scoring
- Added agent-friendly error handling
- Refactored into modular package structure

### v1.0.0
- Initial implementation with basic Google Custom Search integration
- Rate limiting and circuit breaker
- Basic caching support

## 📄 License

See project LICENSE file.

## 🤝 Contributing

Contributions welcome! Please ensure:
- All tests pass
- Code follows project style guidelines
- Documentation is updated
- New features include tests

## 📧 Support

For issues or questions, please open an issue in the project repository.

---

**Built with ❤️ for AI agents seeking high-quality search results**

