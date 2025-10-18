# Search Tool - Complete Technical Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Enhanced Features](#enhanced-features)
5. [API Reference](#api-reference)
6. [Data Structures](#data-structures)
7. [Error Handling](#error-handling)
8. [Performance & Optimization](#performance--optimization)
9. [Testing](#testing)
10. [Advanced Topics](#advanced-topics)

---

## 1. Overview

### 1.1 Purpose

The **SearchTool** is an enterprise-grade web search tool that integrates Google Custom Search API with advanced AI-agent-optimized features. It provides intelligent search capabilities with quality assessment, intent analysis, context awareness, and comprehensive reliability mechanisms.

### 1.2 Key Capabilities

- **Multi-Type Search**: Web, image, news, and video search
- **Quality Assessment**: Automatic result quality scoring and credibility analysis
- **Intent Analysis**: Query intent detection with automatic enhancement
- **Context Awareness**: Search history tracking and preference learning
- **Intelligent Caching**: Redis-based caching with intent-aware TTL strategies
- **Reliability**: Rate limiting, circuit breaker, and retry mechanisms
- **Deduplication**: Advanced result deduplication with similarity detection
- **Metrics & Monitoring**: Comprehensive performance tracking and health scoring

### 1.3 Architecture Overview

```
SearchTool (BaseTool)
├── Core Components
│   ├── Google Custom Search API Client
│   ├── Rate Limiter (Token Bucket)
│   ├── Circuit Breaker (3-State)
│   └── Retry Handler (Exponential Backoff)
├── Enhanced Features
│   ├── ResultQualityAnalyzer
│   ├── QueryIntentAnalyzer
│   ├── ResultDeduplicator
│   ├── SearchContext
│   ├── IntelligentCache (Redis)
│   ├── ResultSummarizer
│   └── EnhancedMetrics
└── Error Handling
    └── AgentFriendlyErrorHandler
```

---

## 2. Architecture

### 2.1 Package Structure

```
aiecs/tools/search_tool/
├── __init__.py              # Package entry point with tool registration
├── core.py                  # Main SearchTool class
├── constants.py             # Enums, exceptions, and constants
├── schemas.py               # Pydantic schemas for input validation
├── analyzers.py             # Quality, intent, and summarization analyzers
├── deduplicator.py          # Result deduplication logic
├── context.py               # Search context management
├── cache.py                 # Intelligent Redis caching
├── metrics.py               # Enhanced metrics collection
├── error_handler.py         # Agent-friendly error formatting
├── rate_limiter.py          # Rate limiting and circuit breaker
└── README.md                # Package documentation
```

### 2.2 Component Interaction Flow

```
User Request
    ↓
SearchTool.search_web()
    ↓
[Rate Limiter Check] → RateLimitError if exceeded
    ↓
[Circuit Breaker Check] → CircuitBreakerOpenError if open
    ↓
[Intent Analysis] → Query enhancement
    ↓
[Cache Check] → Return cached if available
    ↓
[Google API Call] → With retry logic
    ↓
[Quality Analysis] → Score each result
    ↓
[Deduplication] → Remove duplicates
    ↓
[Context Update] → Track search history
    ↓
[Cache Store] → Store with intelligent TTL
    ↓
[Metrics Update] → Record performance
    ↓
Return Results
```

### 2.3 Integration Points

- **AIECS Base Tool**: Inherits from `BaseTool` for standardized interface
- **Redis**: Optional integration for intelligent caching
- **LangChain**: Full adapter support for agent integration
- **Google Custom Search API**: Primary search backend
- **Metrics System**: Integration with AIECS metrics infrastructure

---

## 3. Core Components

### 3.1 SearchTool Class

**Location**: `aiecs/tools/search_tool/core.py`

**Inheritance**: `BaseTool`

**Key Attributes**:
```python
class SearchTool(BaseTool):
    config: Config                          # Configuration object
    rate_limiter: RateLimiter              # Rate limiting
    circuit_breaker: CircuitBreaker        # Failure protection
    quality_analyzer: ResultQualityAnalyzer # Quality assessment
    intent_analyzer: QueryIntentAnalyzer   # Intent detection
    deduplicator: ResultDeduplicator       # Deduplication
    search_context: SearchContext          # Context tracking
    intelligent_cache: IntelligentCache    # Redis caching
    metrics: EnhancedMetrics               # Performance metrics
    error_handler: AgentFriendlyErrorHandler # Error formatting
```

**Configuration Schema**:
```python
class Config(BaseModel):
    # API Configuration
    google_api_key: Optional[str]
    google_cse_id: Optional[str]
    google_application_credentials: Optional[str]
    
    # Performance
    max_results_per_query: int = 10
    cache_ttl: int = 3600
    timeout: int = 30
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 86400
    
    # Circuit Breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    
    # Retry Logic
    retry_attempts: int = 3
    retry_backoff: float = 2.0
    
    # Enhanced Features
    enable_quality_analysis: bool = True
    enable_intent_analysis: bool = True
    enable_deduplication: bool = True
    enable_context_tracking: bool = True
    enable_intelligent_cache: bool = True
    
    # Tuning
    similarity_threshold: float = 0.85
    max_search_history: int = 10
    user_agent: str = "AIECS-SearchTool/2.0"
```

### 3.2 Rate Limiter

**Location**: `aiecs/tools/search_tool/rate_limiter.py`

**Algorithm**: Token Bucket

**Purpose**: Prevents API quota exhaustion by limiting request rate

**Implementation**:
```python
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.tokens = max_requests
        self.last_refill = time.time()
    
    def acquire(self) -> bool:
        """Attempt to acquire a token for request"""
        self._refill_tokens()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = (elapsed / self.window_seconds) * self.max_requests
        self.tokens = min(self.max_requests, self.tokens + refill_amount)
        self.last_refill = now
```

**Features**:
- Automatic token refill based on time window
- Thread-safe implementation
- Configurable request limits
- Real-time quota tracking

### 3.3 Circuit Breaker

**Location**: `aiecs/tools/search_tool/rate_limiter.py`

**Pattern**: Three-State Circuit Breaker

**States**:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Failures exceeded threshold, requests blocked
- **HALF_OPEN**: Testing recovery, limited requests allowed

**Implementation**:
```python
class CircuitBreaker:
    def __init__(self, threshold: int, timeout: int):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

**Features**:
- Automatic failure detection
- Configurable failure threshold
- Time-based recovery attempts
- Health check mechanism

---

## 4. Enhanced Features

### 4.1 Result Quality Analyzer

**Location**: `aiecs/tools/search_tool/analyzers.py`

**Purpose**: Assess search result quality using multiple factors

**Quality Factors**:
1. **Domain Authority** (0-1 score)
   - Authoritative domains (`.gov`, `.edu`, academic sites)
   - Major media outlets
   - Technical documentation sites
   - Community platforms

2. **Relevance Score** (0-1 score)
   - Query term matching in title
   - Query term matching in snippet
   - Position in search results

3. **Freshness Score** (0-1 score)
   - Publication date analysis
   - Content age assessment

4. **Quality Signals**
   - HTTPS usage
   - Content length
   - Metadata presence
   - Low-quality indicator detection

**Authoritative Domains**:
```python
AUTHORITATIVE_DOMAINS = {
    # Academic and research
    'scholar.google.com': 0.95,
    'arxiv.org': 0.95,
    'ieee.org': 0.95,
    'nature.com': 0.95,
    
    # Government and official
    '.gov': 0.90,
    '.edu': 0.85,
    
    # Major media
    'reuters.com': 0.85,
    'apnews.com': 0.85,
    
    # Technical documentation
    'docs.python.org': 0.90,
    'developer.mozilla.org': 0.90,
    'stackoverflow.com': 0.75,
}
```

**Output Structure**:
```python
{
    'quality_score': 0.85,           # Overall quality (0-1)
    'authority_score': 0.90,         # Domain authority (0-1)
    'relevance_score': 0.80,         # Query relevance (0-1)
    'freshness_score': 0.85,         # Content freshness (0-1)
    'credibility_level': 'high',     # high/medium/low
    'quality_signals': {
        'domain_authority': 'high',
        'has_https': True,
        'has_metadata': True,
        'content_length': 'adequate'
    },
    'warnings': []                   # Quality warnings
}
```

### 4.2 Query Intent Analyzer

**Location**: `aiecs/tools/search_tool/analyzers.py`

**Purpose**: Detect query intent and enhance queries automatically

**Intent Types**:
```python
class QueryIntentType(str, Enum):
    DEFINITION = "definition"        # "what is X"
    HOW_TO = "how_to"               # "how to X"
    COMPARISON = "comparison"        # "X vs Y"
    FACTUAL = "factual"             # "when/where/who"
    RECENT_NEWS = "recent_news"     # "latest X"
    ACADEMIC = "academic"           # "research on X"
    PRODUCT = "product"             # "buy X", "X review"
    GENERAL = "general"             # General queries
```

**Intent Detection Patterns**:
```python
INTENT_PATTERNS = {
    'definition': {
        'patterns': [r'\bwhat is\b', r'\bdefine\b', r'\bmeaning of\b'],
        'query_enhancement': 'definition explanation',
        'suggested_params': {'num_results': 5}
    },
    'how_to': {
        'patterns': [r'\bhow to\b', r'\bhow do\b', r'\bsteps to\b'],
        'query_enhancement': 'tutorial guide step-by-step',
        'suggested_params': {'num_results': 10}
    },
    'comparison': {
        'patterns': [r'\bvs\b', r'\bversus\b', r'\bcompare\b', r'\bdifference between\b'],
        'query_enhancement': 'comparison differences',
        'suggested_params': {'num_results': 10}
    },
    'academic': {
        'patterns': [r'\bresearch\b', r'\bstudy\b', r'\bpaper\b', r'\bjournal\b'],
        'query_enhancement': 'research paper study',
        'suggested_params': {'file_type': 'pdf', 'num_results': 10}
    }
}
```

**Query Enhancement**:
- Automatically adds relevant search operators
- Suggests optimal search parameters
- Improves result quality for specific intent types

**Output Structure**:
```python
{
    'intent_type': 'how_to',
    'confidence': 0.95,
    'original_query': 'how to build REST API',
    'enhanced_query': 'how to build REST API tutorial guide step-by-step',
    'suggested_params': {'num_results': 10},
    'query_entities': ['REST API', 'build'],
    'query_modifiers': ['how to'],
    'suggestions': ['Consider adding programming language', 'Specify framework']
}
```

### 4.3 Result Deduplicator

**Location**: `aiecs/tools/search_tool/deduplicator.py`

**Purpose**: Remove duplicate and highly similar results

**Deduplication Methods**:

1. **URL Normalization**
   - Remove query parameters
   - Normalize protocols (http/https)
   - Handle URL variations

2. **Content Similarity**
   - Title similarity comparison
   - Snippet similarity comparison
   - Configurable threshold (default: 0.85)

**Implementation**:
```python
class ResultDeduplicator:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate and similar results"""
        seen_urls = set()
        unique_results = []

        for result in results:
            normalized_url = self._normalize_url(result['link'])

            if normalized_url in seen_urls:
                continue

            if self._is_similar_to_existing(result, unique_results):
                continue

            seen_urls.add(normalized_url)
            unique_results.append(result)

        return unique_results
```

### 4.4 Search Context

**Location**: `aiecs/tools/search_tool/context.py`

**Purpose**: Track search history and learn user preferences

**Features**:
- Search history management (configurable limit)
- Topic context tracking
- Preference learning from feedback
- Related query suggestions
- Domain preference tracking

**Context Structure**:
```python
{
    'history': [
        {
            'query': 'machine learning',
            'timestamp': '2025-10-18T10:30:00',
            'results_count': 10,
            'avg_quality': 0.85
        }
    ],
    'preferences': {
        'preferred_domains': ['arxiv.org', 'github.com'],
        'avoided_domains': ['spam-site.com'],
        'preferred_quality_level': 'high'
    },
    'topic_context': {
        'current_topic': 'machine learning',
        'related_queries': ['deep learning', 'neural networks']
    }
}
```

### 4.5 Intelligent Cache

**Location**: `aiecs/tools/search_tool/cache.py`

**Backend**: Redis

**Purpose**: Reduce API calls with smart caching strategies

**Intent-Aware TTL**:
```python
TTL_STRATEGIES = {
    'definition': 2592000,      # 30 days (stable content)
    'how_to': 604800,           # 7 days (tutorials)
    'academic': 2592000,        # 30 days (research papers)
    'recent_news': 3600,        # 1 hour (news)
    'product': 86400,           # 1 day (products)
    'general': 3600             # 1 hour (default)
}
```

**Dynamic TTL Adjustment**:
- Higher quality results cached longer
- Fresh content cached shorter
- User feedback influences TTL

**Cache Key Generation**:
```python
def _generate_cache_key(query: str, params: Dict) -> str:
    """Generate unique cache key"""
    key_parts = [
        query.lower().strip(),
        str(params.get('num_results', 10)),
        params.get('language', 'en'),
        params.get('country', 'us'),
        params.get('date_restrict', ''),
        params.get('file_type', '')
    ]
    return f"search:{':'.join(key_parts)}"
```

### 4.6 Enhanced Metrics

**Location**: `aiecs/tools/search_tool/metrics.py`

**Purpose**: Comprehensive performance tracking and health monitoring

**Metrics Categories**:

1. **Request Metrics**
   - Total requests
   - Successful requests
   - Failed requests
   - Cached requests

2. **Performance Metrics**
   - Response times (P50, P95, P99)
   - Average response time
   - Slowest queries

3. **Quality Metrics**
   - Average quality score
   - High-quality result percentage
   - Results per query
   - No-result queries

4. **Cache Metrics**
   - Hit rate
   - Cache hits/misses
   - Cache efficiency

5. **Error Metrics**
   - Error rate
   - Errors by type
   - Recent errors

6. **Query Pattern Metrics**
   - Top query types
   - Top domains
   - Average query length

**Health Score Calculation**:
```python
def calculate_health_score(self) -> float:
    """Calculate overall system health (0-1)"""
    factors = {
        'success_rate': 0.4,      # 40% weight
        'cache_hit_rate': 0.2,    # 20% weight
        'avg_quality': 0.2,       # 20% weight
        'error_rate': 0.2         # 20% weight (inverted)
    }

    health = (
        factors['success_rate'] * self.success_rate +
        factors['cache_hit_rate'] * self.cache_hit_rate +
        factors['avg_quality'] * self.avg_quality_score +
        factors['error_rate'] * (1 - self.error_rate)
    )

    return max(0.0, min(1.0, health))
```

---

## 5. API Reference

### 5.1 Search Operations

#### search_web()

**Purpose**: Perform web search with comprehensive filters

**Signature**:
```python
def search_web(
    query: str,
    num_results: int = 10,
    start_index: int = 1,
    language: str = "en",
    country: str = "us",
    safe_search: str = "medium",
    date_restrict: Optional[str] = None,
    file_type: Optional[str] = None,
    exclude_terms: Optional[str] = None,
    auto_enhance: bool = True,
    return_summary: bool = False
) -> Union[List[Dict], Dict[str, Any]]
```

**Parameters**:
- `query` (str): Search query string
- `num_results` (int): Number of results (1-100)
- `start_index` (int): Pagination start (1-91)
- `language` (str): Language code (e.g., 'en', 'zh-CN')
- `country` (str): Country code (e.g., 'us', 'cn')
- `safe_search` (str): 'off', 'medium', or 'high'
- `date_restrict` (Optional[str]): Date filter (e.g., 'd7', 'm3', 'y1')
- `file_type` (Optional[str]): File type filter (e.g., 'pdf', 'doc')
- `exclude_terms` (Optional[str]): Terms to exclude
- `auto_enhance` (bool): Enable query enhancement
- `return_summary` (bool): Return structured summary

**Returns**:
- If `return_summary=False`: `List[Dict]` - List of search results
- If `return_summary=True`: `Dict` with 'results' and 'summary' keys

**Result Structure**:
```python
{
    'title': 'Result Title',
    'link': 'https://example.com',
    'snippet': 'Result description...',
    'displayLink': 'example.com',
    'formattedUrl': 'https://example.com/page',

    # Enhanced fields (if quality analysis enabled)
    '_quality_summary': {
        'score': 0.85,
        'level': 'high',
        'is_authoritative': True,
        'authority_score': 0.90,
        'relevance_score': 0.80
    },

    # Metadata (if intent analysis enabled)
    '_search_metadata': {
        'original_query': 'machine learning',
        'enhanced_query': 'machine learning tutorial guide',
        'intent_type': 'how_to',
        'intent_confidence': 0.95
    }
}
```

**Example**:
```python
# Basic search
results = tool.search_web("artificial intelligence", num_results=10)

# Advanced search with filters
results = tool.search_web(
    query="climate change research",
    num_results=10,
    language="en",
    date_restrict="m6",  # Last 6 months
    file_type="pdf",
    auto_enhance=True,
    return_summary=True
)

# Access results
for result in results['results']:
    print(f"Title: {result['title']}")
    print(f"Quality: {result['_quality_summary']['score']}")
```

#### search_images()

**Purpose**: Search for images with size and type filters

**Signature**:
```python
def search_images(
    query: str,
    num_results: int = 10,
    image_size: Optional[str] = None,
    image_type: Optional[str] = None,
    image_color_type: Optional[str] = None,
    safe_search: str = "medium"
) -> List[Dict[str, Any]]
```

**Parameters**:
- `query` (str): Image search query
- `num_results` (int): Number of images (1-100)
- `image_size` (Optional[str]): 'icon', 'small', 'medium', 'large', 'xlarge', 'xxlarge', 'huge'
- `image_type` (Optional[str]): 'clipart', 'face', 'lineart', 'stock', 'photo', 'animated'
- `image_color_type` (Optional[str]): 'color', 'gray', 'mono', 'trans'
- `safe_search` (str): 'off', 'medium', or 'high'

**Returns**: List of image results with URLs and metadata

**Example**:
```python
images = tool.search_images(
    query="sunset beach",
    num_results=10,
    image_size="large",
    image_type="photo",
    image_color_type="color"
)

for img in images:
    print(f"Image: {img['link']}")
    print(f"Thumbnail: {img['image']['thumbnailLink']}")
```

#### search_news()

**Purpose**: Search for news articles

**Signature**:
```python
def search_news(
    query: str,
    num_results: int = 10,
    start_index: int = 1,
    language: str = "en",
    date_restrict: Optional[str] = None,
    sort_by: str = "date"
) -> List[Dict[str, Any]]
```

**Parameters**:
- `query` (str): News search query
- `num_results` (int): Number of articles (1-100)
- `start_index` (int): Pagination start
- `language` (str): Language code
- `date_restrict` (Optional[str]): Date filter (e.g., 'd7' for last 7 days)
- `sort_by` (str): 'date' or 'relevance'

**Example**:
```python
news = tool.search_news(
    query="technology innovation",
    num_results=10,
    date_restrict="d7",  # Last 7 days
    sort_by="date"
)
```

#### search_videos()

**Purpose**: Search for videos

**Signature**:
```python
def search_videos(
    query: str,
    num_results: int = 10,
    safe_search: str = "medium",
    language: str = "en"
) -> List[Dict[str, Any]]
```

#### search_paginated()

**Purpose**: Retrieve more than 10 results (up to 100) with automatic pagination

**Signature**:
```python
def search_paginated(
    query: str,
    total_results: int = 50,
    search_type: str = "web",
    **kwargs
) -> List[Dict[str, Any]]
```

**Parameters**:
- `query` (str): Search query
- `total_results` (int): Total results to retrieve (1-100)
- `search_type` (str): 'web', 'images', 'news', or 'videos'
- `**kwargs`: Additional parameters for specific search type

**Example**:
```python
# Get 50 web results
results = tool.search_paginated(
    query="machine learning",
    total_results=50,
    search_type="web",
    language="en"
)
```

#### search_batch()

**Purpose**: Execute multiple queries in parallel

**Signature**:
```python
async def search_batch(
    queries: List[str],
    search_type: str = "web",
    num_results: int = 10,
    **kwargs
) -> Dict[str, List[Dict]]
```

**Parameters**:
- `queries` (List[str]): List of search queries (max 50)
- `search_type` (str): Type of search
- `num_results` (int): Results per query
- `**kwargs`: Additional search parameters

**Returns**: Dictionary mapping queries to their results

**Example**:
```python
import asyncio

queries = ["AI", "ML", "DL", "NLP"]
results = asyncio.run(tool.search_batch(
    queries=queries,
    search_type="web",
    num_results=5
))

for query, query_results in results.items():
    print(f"Results for '{query}': {len(query_results)}")
```

### 5.2 Monitoring Operations

#### get_metrics()

**Purpose**: Get detailed performance metrics

**Signature**:
```python
def get_metrics(self) -> Dict[str, Any]
```

**Returns**:
```python
{
    'requests': {
        'total': 150,
        'successful': 142,
        'failed': 8,
        'cached': 45
    },
    'performance': {
        'avg_response_time': 234.5,
        'p50_response_time': 200.0,
        'p95_response_time': 450.0,
        'p99_response_time': 800.0
    },
    'quality': {
        'avg_results_per_query': 8.3,
        'avg_quality_score': 0.78,
        'high_quality_percentage': 62.5,
        'no_results_count': 3
    },
    'cache': {
        'hit_rate': 0.30,
        'hits': 45,
        'misses': 105
    },
    'errors': {
        'error_rate': 0.053,
        'errors_by_type': {
            'QuotaExceededError': 3,
            'NetworkError': 2
        }
    }
}
```

#### get_metrics_report()

**Purpose**: Get human-readable metrics report

**Signature**:
```python
def get_metrics_report(self) -> str
```

**Returns**: Formatted string report

#### get_health_score()

**Purpose**: Get overall system health score

**Signature**:
```python
def get_health_score(self) -> float
```

**Returns**: Health score (0-1), where >0.8 is healthy

#### get_quota_status()

**Purpose**: Get current quota and circuit breaker status

**Signature**:
```python
def get_quota_status(self) -> Dict[str, Any]
```

**Returns**:
```python
{
    'remaining_quota': 85,
    'quota_limit': 100,
    'quota_window_seconds': 86400,
    'circuit_breaker_state': 'closed',
    'circuit_breaker_failures': 0,
    'metrics': {
        'total_requests': 15,
        'successful_requests': 15,
        'failed_requests': 0
    }
}
```

#### validate_credentials()

**Purpose**: Validate Google API credentials

**Signature**:
```python
def validate_credentials(self) -> Dict[str, Any]
```

**Returns**:
```python
{
    'valid': True,
    'method': 'api_key',  # or 'service_account'
    'cse_id_present': True,
    'error': None
}
```

### 5.3 Context Operations

#### get_search_context()

**Purpose**: Get current search context and history

**Signature**:
```python
def get_search_context(self) -> Dict[str, Any]
```

**Returns**: Search context with history and preferences

---

## 6. Data Structures

### 6.1 Enumerations

```python
# Search Types
class SearchType(str, Enum):
    WEB = "web"
    IMAGE = "image"
    NEWS = "news"
    VIDEO = "video"

# Safe Search Levels
class SafeSearch(str, Enum):
    OFF = "off"
    MEDIUM = "medium"
    HIGH = "high"

# Query Intent Types
class QueryIntentType(str, Enum):
    DEFINITION = "definition"
    HOW_TO = "how_to"
    COMPARISON = "comparison"
    FACTUAL = "factual"
    RECENT_NEWS = "recent_news"
    ACADEMIC = "academic"
    PRODUCT = "product"
    GENERAL = "general"

# Credibility Levels
class CredibilityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# Circuit Breaker States
class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
```

### 6.2 Exception Hierarchy

```python
SearchToolError                  # Base exception
├── AuthenticationError          # Invalid/missing credentials
├── QuotaExceededError          # API quota exceeded
├── RateLimitError              # Rate limit reached
├── CircuitBreakerOpenError     # Circuit breaker open
├── SearchAPIError              # Google API errors
├── ValidationError             # Input validation errors
└── CacheError                  # Cache-related errors
```

---

## 7. Error Handling

### 7.1 Agent-Friendly Error Handler

**Location**: `aiecs/tools/search_tool/error_handler.py`

**Purpose**: Format errors in a way that AI agents can understand and act upon

**Error Structure**:
```python
{
    'error_type': 'QuotaExceededError',
    'message': 'API quota exceeded for today',
    'severity': 'high',
    'is_retryable': False,
    'suggested_actions': [
        'Wait 24 hours for quota reset',
        'Upgrade to paid tier',
        'Use cached results if available'
    ],
    'alternative_approaches': [
        'Use alternative search source',
        'Reduce search frequency'
    ],
    'recovery_time_estimate': '24 hours',
    'context': {
        'current_quota': 100,
        'quota_limit': 100,
        'reset_time': '2025-10-19T00:00:00Z'
    }
}
```

### 7.2 Error Handling Best Practices

```python
from aiecs.tools.search_tool import (
    SearchTool,
    RateLimitError,
    QuotaExceededError,
    CircuitBreakerOpenError,
    AuthenticationError
)

tool = SearchTool()

try:
    results = tool.search_web("query")

except RateLimitError as e:
    # Rate limit exceeded - wait and retry
    error_info = tool.error_handler.format_error(e)
    wait_time = error_info.get('recovery_time_estimate', 60)
    time.sleep(wait_time)
    # Retry...

except QuotaExceededError as e:
    # Quota exceeded - use fallback
    error_info = tool.error_handler.format_error(e)
    # Use cached results or alternative source

except CircuitBreakerOpenError as e:
    # Circuit breaker open - API is down
    error_info = tool.error_handler.format_error(e)
    # Wait for recovery or use fallback

except AuthenticationError as e:
    # Invalid credentials - fix configuration
    error_info = tool.error_handler.format_error(e)
    # Check API key and CSE ID

except Exception as e:
    # Unexpected error
    logger.error(f"Unexpected error: {e}")
```

---

## 8. Performance & Optimization

### 8.1 Performance Benchmarks

**Average Response Times**:
- With cache hit: ~50ms
- Without cache (API call): ~200-500ms
- Quality analysis overhead: ~10-20ms per result
- Intent detection: ~5-10ms per query

**Cache Performance**:
- Typical hit rate: 30-50%
- API call reduction: 30-50%
- Storage overhead: ~5KB per cached query

### 8.2 Optimization Strategies

1. **Enable All Caching**
```python
config = {
    'enable_intelligent_cache': True,
    'cache_ttl': 3600  # Adjust based on content freshness needs
}
```

2. **Use Batch Operations**
```python
# Instead of multiple individual calls
results = await tool.search_batch(queries=['q1', 'q2', 'q3'])
```

3. **Optimize Result Count**
```python
# Only request what you need
results = tool.search_web(query, num_results=5)  # Not 100
```

4. **Leverage Context**
```python
# Context helps avoid redundant searches
tool.search_web("python basics")
tool.search_web("python advanced")  # Context aware
```

5. **Configure Rate Limits Appropriately**
```python
config = {
    'rate_limit_requests': 100,  # Match your API quota
    'rate_limit_window': 86400   # 24 hours
}
```

### 8.3 Scalability Considerations

**Horizontal Scaling**:
- Redis cache shared across instances
- Stateless design (except context)
- Thread-safe implementation

**Vertical Scaling**:
- Async batch operations
- Connection pooling
- Efficient memory usage

**Quota Management**:
- Distributed rate limiting via Redis
- Circuit breaker prevents cascading failures
- Intelligent caching reduces API calls

---

## 9. Testing

### 9.1 Unit Tests

**Location**: `test/unit_tests/tools/test_search_tool_enhanced.py`

**Test Coverage**:
- Result quality analysis
- Query intent detection
- Deduplication logic
- Context management
- Metrics collection
- Error handling
- Cache operations

**Example Tests**:
```python
def test_quality_analysis():
    analyzer = ResultQualityAnalyzer()
    result = {
        'title': 'Machine Learning Tutorial',
        'snippet': 'Learn machine learning basics',
        'displayLink': 'docs.python.org'
    }
    analysis = analyzer.analyze_result_quality(result, 'machine learning', 1)
    assert analysis['authority_score'] > 0.8
    assert analysis['credibility_level'] == 'high'

def test_intent_detection():
    analyzer = QueryIntentAnalyzer()
    analysis = analyzer.analyze_query_intent('how to build REST API')
    assert analysis['intent_type'] == 'how_to'
    assert analysis['confidence'] > 0.8
```

### 9.2 Integration Tests

```python
def test_web_search_integration():
    tool = SearchTool()
    results = tool.search_web("test query", num_results=5)
    assert isinstance(results, list)
    assert len(results) <= 5
    assert all('title' in r for r in results)
    assert all('link' in r for r in results)

def test_cache_integration():
    tool = SearchTool()
    # First call - cache miss
    results1 = tool.search_web("cache test")
    # Second call - cache hit
    results2 = tool.search_web("cache test")
    assert results1 == results2
```

---

## 10. Advanced Topics

### 10.1 Custom Quality Analyzers

You can extend the quality analyzer with custom domain authorities:

```python
from aiecs.tools.search_tool.analyzers import ResultQualityAnalyzer

class CustomQualityAnalyzer(ResultQualityAnalyzer):
    AUTHORITATIVE_DOMAINS = {
        **ResultQualityAnalyzer.AUTHORITATIVE_DOMAINS,
        'mycompany.com': 0.95,
        'trusted-source.org': 0.90
    }

# Use custom analyzer
tool = SearchTool()
tool.quality_analyzer = CustomQualityAnalyzer()
```

### 10.2 Custom Intent Patterns

Add custom intent patterns:

```python
from aiecs.tools.search_tool.analyzers import QueryIntentAnalyzer

class CustomIntentAnalyzer(QueryIntentAnalyzer):
    INTENT_PATTERNS = {
        **QueryIntentAnalyzer.INTENT_PATTERNS,
        'troubleshooting': {
            'patterns': [r'\berror\b', r'\bfix\b', r'\btroubleshoot\b'],
            'query_enhancement': 'solution fix troubleshooting',
            'suggested_params': {'num_results': 10}
        }
    }
```

### 10.3 Custom Cache Strategies

Implement custom TTL strategies:

```python
from aiecs.tools.search_tool.cache import IntelligentCache

def custom_ttl_strategy(result, args, kwargs):
    """Custom TTL based on result quality"""
    quality_score = result.get('_quality_summary', {}).get('score', 0)
    if quality_score > 0.9:
        return 86400  # 24 hours for high quality
    elif quality_score > 0.7:
        return 3600   # 1 hour for medium quality
    else:
        return 1800   # 30 minutes for low quality

# Apply custom strategy
tool.intelligent_cache.set_ttl_strategy(custom_ttl_strategy)
```

### 10.4 Monitoring Integration

Integrate with external monitoring systems:

```python
from aiecs.tools.search_tool import SearchTool

tool = SearchTool()

# Get metrics periodically
import time
while True:
    metrics = tool.get_metrics()
    health = tool.get_health_score()

    # Send to monitoring system
    monitoring_system.send_metric('search_tool.health', health)
    monitoring_system.send_metric('search_tool.requests', metrics['requests']['total'])
    monitoring_system.send_metric('search_tool.cache_hit_rate', metrics['cache']['hit_rate'])

    time.sleep(60)  # Every minute
```

---

**Document Version**: 2.0
**Last Updated**: 2025-10-18
**Maintainer**: AIECS Tools Team

