# APISource Tool - Complete Technical Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Providers](#providers)
5. [Intelligence Features](#intelligence-features)
6. [Reliability Mechanisms](#reliability-mechanisms)
7. [API Reference](#api-reference)
8. [Data Structures](#data-structures)
9. [Advanced Topics](#advanced-topics)

---

## 1. Overview

### 1.1 Purpose

The **APISource Tool** is a unified interface for querying various external real-time API data sources including economic indicators, news, public databases, and custom APIs. It provides a plugin architecture that enables seamless integration of multiple data providers with intelligent query understanding, data fusion, and comprehensive reliability mechanisms.

### 1.2 Key Capabilities

- **Multi-Provider Support**: FRED, World Bank, News API, Census Bureau
- **Intelligent Query Understanding**: Automatic intent detection and parameter enhancement
- **Cross-Provider Data Fusion**: Merge results from multiple sources intelligently
- **Automatic Fallback**: Seamless failover to alternative providers
- **Advanced Search**: Relevance scoring and composite ranking
- **Comprehensive Monitoring**: Detailed metrics and health scoring
- **Plugin Architecture**: Easy addition of new providers

### 1.3 Architecture Overview

```
APISourceTool (BaseTool)
├── Providers Layer
│   ├── FRED Provider (Economic Data)
│   ├── World Bank Provider (Global Development)
│   ├── News API Provider (News Articles)
│   └── Census Provider (US Demographics)
├── Intelligence Layer
│   ├── QueryIntentAnalyzer (Intent Detection)
│   ├── QueryEnhancer (Parameter Auto-completion)
│   ├── DataFusionEngine (Multi-source Merging)
│   └── SearchEnhancer (Relevance Ranking)
├── Reliability Layer
│   ├── SmartErrorHandler (Retry Logic)
│   └── FallbackStrategy (Provider Failover)
├── Monitoring Layer
│   └── DetailedMetrics (Performance Tracking)
└── Utils Layer
    └── DataValidator (Quality Assurance)
```

---

## 2. Architecture

### 2.1 Package Structure

```
aiecs/tools/apisource/
├── __init__.py              # Main entry point
├── tool.py                  # APISourceTool main class
├── README.md                # Package documentation
│
├── providers/               # API provider implementations
│   ├── __init__.py         # Provider registration and management
│   ├── base.py             # BaseAPIProvider abstract class
│   ├── fred.py             # Federal Reserve Economic Data
│   ├── worldbank.py        # World Bank API
│   ├── newsapi.py          # News API
│   └── census.py           # US Census Bureau
│
├── intelligence/            # Intelligent analysis modules
│   ├── __init__.py
│   ├── query_analyzer.py   # Query intent analysis
│   ├── query_enhancer.py   # Parameter enhancement (uses analyzer)
│   ├── data_fusion.py      # Cross-provider data fusion
│   └── search_enhancer.py  # Search result ranking
│
├── reliability/             # Reliability mechanisms
│   ├── __init__.py
│   ├── error_handler.py    # Smart error handling and retry
│   └── fallback_strategy.py # Provider failover logic
│
├── monitoring/              # Monitoring and metrics
│   ├── __init__.py
│   └── metrics.py          # Detailed performance metrics
│
└── utils/                   # Utility functions
    ├── __init__.py
    └── validators.py       # Data validation tools
```

### 2.2 Component Interaction Flow

**Query Flow**:
```
User Request
    ↓
APISourceTool.query()
    ↓
1. QueryEnhancer (Parameter Enhancement)
    ↓
2. FallbackStrategy (Provider Selection)
    ↓
3. Provider.execute()
    ↓
4. SmartErrorHandler (Error Handling + Retry)
    ↓
5. Data Validation and Cleaning
    ↓
6. Quality Metadata Calculation
    ↓
7. DetailedMetrics (Record Metrics)
    ↓
Return Result (with rich metadata)
```

**Search Flow**:
```
Search Request
    ↓
1. QueryIntentAnalyzer (Intent Analysis)
    ↓
2. Multi-Provider Parallel Query
    ↓
3. DataFusionEngine (Data Fusion)
    ↓
4. SearchEnhancer (Ranking and Filtering)
    ↓
Return Enhanced Search Results
```

### 2.3 Design Principles

1. **Modularity**: Each module has a single responsibility
2. **Extensibility**: New providers can be added without modifying existing code
3. **Testability**: Each module can be tested independently
4. **Backward Compatibility**: Maintains compatibility with original API
5. **Error Friendliness**: Provides detailed error information and recovery suggestions

---

## 3. Core Components

### 3.1 APISourceTool Class

**Location**: `aiecs/tools/apisource/tool.py`

**Inheritance**: `BaseTool`

**Key Attributes**:
```python
class APISourceTool(BaseTool):
    config: Config                          # Configuration object
    query_analyzer: QueryIntentAnalyzer     # Intent analysis
    query_enhancer: QueryEnhancer           # Parameter enhancement
    data_fusion: DataFusionEngine           # Data fusion
    fallback_strategy: FallbackStrategy     # Failover logic
    search_enhancer: SearchEnhancer         # Search ranking
    _providers: Dict[str, BaseAPIProvider]  # Loaded providers
```

**Configuration Schema**:
```python
class Config(BaseModel):
    # Performance
    cache_ttl: int = 300                    # Cache TTL in seconds
    default_timeout: int = 30               # Request timeout
    max_retries: int = 3                    # Max retry attempts
    
    # Feature Flags
    enable_rate_limiting: bool = True       # Enable rate limiting
    enable_fallback: bool = True            # Enable provider fallback
    enable_data_fusion: bool = True         # Enable data fusion
    enable_query_enhancement: bool = True   # Enable query enhancement
    
    # API Keys
    fred_api_key: Optional[str] = None      # FRED API key
    newsapi_api_key: Optional[str] = None   # News API key
    census_api_key: Optional[str] = None    # Census API key
```

### 3.2 Provider Registry

**Location**: `aiecs/tools/apisource/providers/__init__.py`

**Purpose**: Manages provider registration and instantiation

**Key Functions**:
```python
def register_provider(provider_class: Type[BaseAPIProvider]):
    """Register a provider class"""
    
def get_provider(name: str, config: Optional[Dict] = None) -> BaseAPIProvider:
    """Get a provider instance by name"""
    
def list_providers() -> List[Dict[str, Any]]:
    """List all registered providers with metadata"""
```

**Auto-Registration**:
All providers are automatically registered on import:
```python
register_provider(FREDProvider)
register_provider(WorldBankProvider)
register_provider(NewsAPIProvider)
register_provider(CensusProvider)
```

---

## 4. Providers

### 4.1 BaseAPIProvider

**Location**: `aiecs/tools/apisource/providers/base.py`

**Purpose**: Abstract base class for all API providers

**Key Features**:
- Rate limiting with token bucket algorithm
- Standardized error handling
- Metadata about provider capabilities
- Parameter validation
- Response formatting
- Data quality assessment

**Abstract Methods**:
```python
@property
@abstractmethod
def name(self) -> str:
    """Provider name (e.g., 'fred')"""

@property
@abstractmethod
def description(self) -> str:
    """Provider description"""

@property
@abstractmethod
def supported_operations(self) -> List[str]:
    """List of supported operation names"""

@abstractmethod
def validate_params(self, operation: str, params: Dict) -> Tuple[bool, Optional[str]]:
    """Validate operation parameters"""

@abstractmethod
def fetch(self, operation: str, params: Dict) -> Any:
    """Fetch data from the API"""
```

**Provided Methods**:
```python
def execute(self, operation: str, params: Dict) -> Dict[str, Any]:
    """Execute operation with rate limiting, error handling, and metrics"""

def get_metadata(self) -> Dict[str, Any]:
    """Get provider metadata including health status"""

def get_operation_schema(self, operation: str) -> Optional[Dict]:
    """Get schema for a specific operation"""

def validate_and_clean_data(self, data: Any, operation: str) -> Any:
    """Validate and clean response data"""

def calculate_data_quality(self, data: Any, operation: str) -> Dict[str, Any]:
    """Calculate data quality metrics"""
```

### 4.2 Rate Limiter

**Location**: `aiecs/tools/apisource/providers/base.py`

**Algorithm**: Token Bucket

**Implementation**:
```python
class RateLimiter:
    def __init__(self, tokens_per_second: float, max_tokens: int):
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_update = time.time()
    
    def acquire(self, tokens: int = 1) -> bool:
        """Attempt to acquire tokens"""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def wait(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """Wait until tokens are available"""
```

**Features**:
- Automatic token refill
- Configurable rate and burst size
- Timeout support
- Thread-safe implementation

### 4.3 FRED Provider

**Location**: `aiecs/tools/apisource/providers/fred.py`

**Purpose**: Access Federal Reserve Economic Data

**Supported Operations**:
- `get_series`: Get series metadata
- `search_series`: Search for economic series
- `get_series_observations`: Get time series data
- `get_series_info`: Get detailed series information
- `get_categories`: Get data categories
- `get_releases`: Get data releases

**Example**:
```python
from aiecs.tools.apisource.providers import get_provider

fred = get_provider('fred', {'api_key': 'YOUR_KEY'})

# Get GDP observations
result = fred.execute('get_series_observations', {
    'series_id': 'GDP',
    'observation_start': '2020-01-01',
    'observation_end': '2023-12-31'
})

# Search for series
results = fred.execute('search_series', {
    'search_text': 'unemployment',
    'limit': 10
})
```

**Data Quality Assessment**:
- Completeness: Checks for missing values
- Freshness: Evaluates data recency
- Consistency: Validates data format
- Reliability: Based on FRED's authoritative status

### 4.4 World Bank Provider

**Location**: `aiecs/tools/apisource/providers/worldbank.py`

**Purpose**: Access global development indicators

**Supported Operations**:
- `get_indicators`: List available indicators
- `get_indicator_data`: Get indicator data for countries
- `get_countries`: List countries
- `search_indicators`: Search for indicators

**Example**:
```python
wb = get_provider('worldbank')

# Get GDP data for multiple countries
result = wb.execute('get_indicator_data', {
    'indicator': 'NY.GDP.MKTP.CD',
    'countries': ['USA', 'CHN', 'JPN'],
    'date_range': '2015:2023'
})
```

### 4.5 News API Provider

**Location**: `aiecs/tools/apisource/providers/newsapi.py`

**Purpose**: Access news articles and headlines

**Supported Operations**:
- `get_top_headlines`: Get top headlines
- `search_articles`: Search news articles
- `get_sources`: Get news sources

**Example**:
```python
news = get_provider('newsapi', {'api_key': 'YOUR_KEY'})

# Get top headlines
result = news.execute('get_top_headlines', {
    'category': 'business',
    'country': 'us',
    'page_size': 10
})

# Search articles
results = news.execute('search_articles', {
    'q': 'artificial intelligence',
    'from_date': '2023-01-01',
    'sort_by': 'relevancy'
})
```

### 4.6 Census Provider

**Location**: `aiecs/tools/apisource/providers/census.py`

**Purpose**: Access US Census Bureau data

**Supported Operations**:
- `get_data`: Get census data
- `get_variables`: List available variables
- `get_geographies`: Get geographic levels

**Example**:
```python
census = get_provider('census', {'api_key': 'YOUR_KEY'})

# Get population data
result = census.execute('get_data', {
    'dataset': 'acs/acs5',
    'year': 2021,
    'variables': ['B01001_001E'],  # Total population
    'for': 'state:*'
})
```

---

## 5. Intelligence Features

### 5.1 Query Intent Analyzer

**Location**: `aiecs/tools/apisource/intelligence/query_analyzer.py`

**Purpose**: Analyze query intent to optimize routing and parameters

**Intent Types**:
- `time_series`: Historical data trends
- `comparison`: Comparing entities
- `search`: Finding data
- `metadata`: Information about data
- `recent`: Latest data
- `forecast`: Future predictions

**Economic Indicators Mapping**:
```python
ECONOMIC_INDICATORS = {
    'gdp': {
        'keywords': ['gdp', 'gross domestic product'],
        'providers': ['fred', 'worldbank'],
        'fred_series': ['GDP', 'GDPC1'],
        'wb_indicator': 'NY.GDP.MKTP.CD'
    },
    'unemployment': {
        'keywords': ['unemployment', 'jobless'],
        'providers': ['fred'],
        'fred_series': ['UNRATE', 'UNEMPLOY']
    },
    # ... more indicators
}
```

**Analysis Output**:
```python
{
    'intent_type': 'time_series',
    'entities': {
        'indicators': ['gdp'],
        'countries': ['us'],
        'time_references': ['last 5 years']
    },
    'time_range': {
        'start': '2019-01-01',
        'end': '2024-01-01',
        'granularity': 'yearly'
    },
    'geographic_scope': ['us'],
    'suggested_providers': ['fred', 'worldbank'],
    'suggested_operations': {
        'fred': 'get_series_observations',
        'worldbank': 'get_indicator_data'
    },
    'confidence': 0.85
}
```

**Example**:
```python
from aiecs.tools.apisource.intelligence import QueryIntentAnalyzer

analyzer = QueryIntentAnalyzer()
intent = analyzer.analyze_intent("GDP trends over last 5 years")

print(f"Intent: {intent['intent_type']}")
print(f"Suggested providers: {intent['suggested_providers']}")
print(f"Time range: {intent['time_range']}")
```

### 5.2 Query Enhancer

**Location**: `aiecs/tools/apisource/intelligence/query_analyzer.py`

**Purpose**: Auto-complete missing parameters based on query intent

**Enhancement Process**:
1. Analyze query intent
2. Extract time references
3. Map to provider-specific parameters
4. Add missing required parameters
5. Optimize parameter values

**Example**:
```python
from aiecs.tools.apisource.intelligence import QueryEnhancer

enhancer = QueryEnhancer(analyzer)

# Original params
params = {'series_id': 'GDP'}

# Enhanced with query text
enhanced = enhancer.enhance_params(
    provider='fred',
    operation='get_series_observations',
    params=params,
    query_text="Get GDP data for last 5 years"
)

# Result
{
    'series_id': 'GDP',
    'observation_start': '2019-01-01',  # Auto-added
    'observation_end': '2024-01-01',    # Auto-added
    'frequency': 'a'                     # Auto-added (annual)
}
```

### 5.3 Data Fusion Engine

**Location**: `aiecs/tools/apisource/intelligence/data_fusion.py`

**Purpose**: Intelligently merge results from multiple providers

**Fusion Strategies**:

1. **best_quality**: Select result with highest quality score
2. **merge_all**: Merge all results, preserving sources
3. **consensus**: Use data points agreed upon by multiple sources
4. **first_success**: Use first successful result

**Features**:
- Duplicate detection
- Conflict resolution
- Quality-based selection
- Provenance tracking

**Example**:
```python
from aiecs.tools.apisource.intelligence import DataFusionEngine

fusion = DataFusionEngine()

# Fuse results from FRED and World Bank
fused = fusion.fuse_multi_provider_results(
    results=[fred_result, wb_result],
    fusion_strategy='best_quality'
)

# Result includes fusion metadata
{
    'data': [...],
    'metadata': {
        'fusion': {
            'strategy': 'best_quality',
            'sources': ['fred', 'worldbank'],
            'selected_source': 'fred',
            'quality_scores': {'fred': 0.95, 'worldbank': 0.85}
        }
    }
}
```

**Duplicate Detection**:
```python
def _detect_duplicates(self, results: List[Dict]) -> List[Tuple[int, int]]:
    """
    Detect duplicate data points across results.
    
    Uses:
    - Timestamp matching for time series
    - Entity matching for cross-sectional data
    - Value similarity for numeric data
    """
```

### 5.4 Search Enhancer

**Location**: `aiecs/tools/apisource/intelligence/search_enhancer.py`

**Purpose**: Rank and filter search results

**Ranking Factors**:
- **Relevance** (50%): Query term matching
- **Popularity** (30%): Usage frequency
- **Recency** (20%): Data freshness

**Composite Score**:
```python
composite_score = (
    relevance_weight * relevance_score +
    popularity_weight * popularity_score +
    recency_weight * recency_score
)
```

**Features**:
- Configurable weights
- Multiple sort options
- Relevance threshold filtering
- Deduplication

**Example**:
```python
from aiecs.tools.apisource.intelligence import SearchEnhancer

enhancer = SearchEnhancer(
    relevance_weight=0.5,
    popularity_weight=0.3,
    recency_weight=0.2
)

# Enhance search results
enhanced = enhancer.enhance_search_results(
    results=raw_results,
    query='unemployment rate',
    options={
        'sort_by': 'composite',
        'relevance_threshold': 0.3,
        'max_results': 10
    }
)
```

---

## 6. Reliability Mechanisms

### 6.1 Smart Error Handler

**Location**: `aiecs/tools/apisource/reliability/error_handler.py`

**Purpose**: Intelligent error handling with automatic retry

**Error Classification**:
- **Retryable**: Network errors, timeouts, rate limits
- **Non-retryable**: Authentication errors, invalid parameters

**Retry Strategy**:
- Exponential backoff: `delay = base_delay * (2 ** attempt)`
- Jitter: Random variation to prevent thundering herd
- Max retries: Configurable limit

**Example**:
```python
from aiecs.tools.apisource.reliability import SmartErrorHandler

handler = SmartErrorHandler(max_retries=3, base_delay=1.0)

result = handler.execute_with_retry(
    operation_func=lambda: fetch_data(),
    operation_name='get_data'
)
```

**Error Response**:
```python
{
    'error': {
        'type': 'RateLimitError',
        'message': 'API rate limit exceeded',
        'is_retryable': True,
        'retry_after': 60,
        'suggestions': [
            'Wait 60 seconds before retrying',
            'Reduce request frequency',
            'Enable caching to reduce API calls'
        ]
    }
}
```

### 6.2 Fallback Strategy

**Location**: `aiecs/tools/apisource/reliability/fallback_strategy.py`

**Purpose**: Automatic failover to alternative providers

**Fallback Chains**:
```python
FALLBACK_CHAINS = {
    'fred': {
        'get_series_observations': [
            ('worldbank', 'get_indicator_data', param_mapper)
        ]
    },
    'worldbank': {
        'get_indicator_data': [
            ('fred', 'get_series_observations', param_mapper)
        ]
    }
}
```

**Features**:
- Provider-to-provider mapping
- Operation mapping
- Parameter transformation
- Quality preservation

**Example**:
```python
from aiecs.tools.apisource.reliability import FallbackStrategy

strategy = FallbackStrategy()

# Try FRED, fallback to World Bank if needed
result = strategy.execute_with_fallback(
    primary_provider='fred',
    operation='get_series_observations',
    params={'series_id': 'GDP'},
    providers={'fred': fred_instance, 'worldbank': wb_instance}
)
```

---

## 7. API Reference

### 7.1 Core Operations

#### query()

**Purpose**: Execute a query against a specific provider

**Signature**:
```python
def query(
    provider: str,
    operation: str,
    params: Dict[str, Any],
    query_text: Optional[str] = None,
    enable_enhancement: Optional[bool] = None,
    enable_fallback: Optional[bool] = None
) -> Dict[str, Any]
```

**Parameters**:
- `provider` (str): Provider name ('fred', 'worldbank', 'newsapi', 'census')
- `operation` (str): Operation to perform
- `params` (Dict): Operation parameters
- `query_text` (Optional[str]): Natural language query for enhancement
- `enable_enhancement` (Optional[bool]): Enable parameter enhancement
- `enable_fallback` (Optional[bool]): Enable provider fallback

**Returns**:
```python
{
    'data': [...],              # Result data
    'metadata': {
        'provider': 'fred',
        'operation': 'get_series_observations',
        'timestamp': '2024-01-01T00:00:00Z',
        'quality': {
            'score': 0.95,
            'completeness': 1.0,
            'freshness': 0.9,
            'reliability': 1.0
        },
        'enhancement': {
            'applied': True,
            'original_params': {...},
            'enhanced_params': {...}
        }
    }
}
```

**Example**:
```python
tool = APISourceTool({'fred_api_key': 'YOUR_KEY'})

result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={'series_id': 'GDP'},
    query_text="Get GDP data for last 5 years"
)
```

#### search()

**Purpose**: Search across multiple providers with fusion

**Signature**:
```python
def search(
    query: str,
    providers: Optional[List[str]] = None,
    limit: int = 10,
    enable_fusion: Optional[bool] = None,
    enable_enhancement: Optional[bool] = None,
    fusion_strategy: str = 'best_quality',
    search_options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters**:
- `query` (str): Search query
- `providers` (Optional[List[str]]): Providers to search (None = all)
- `limit` (int): Max results per provider
- `enable_fusion` (Optional[bool]): Enable data fusion
- `enable_enhancement` (Optional[bool]): Enable query enhancement
- `fusion_strategy` (str): Fusion strategy to use
- `search_options` (Optional[Dict]): Additional search options

**Search Options**:
```python
{
    'relevance_threshold': 0.3,  # Min relevance score
    'sort_by': 'composite',      # Sort method
    'max_results': 10,           # Max total results
    'deduplicate': True          # Remove duplicates
}
```

**Returns**:
```python
{
    'results': [...],
    'metadata': {
        'query': 'unemployment rate',
        'providers_searched': ['fred', 'worldbank'],
        'total_results': 15,
        'fusion_applied': True,
        'intent_analysis': {...}
    }
}
```

**Example**:
```python
results = tool.search(
    query="unemployment trends",
    providers=['fred', 'worldbank'],
    enable_fusion=True,
    fusion_strategy='best_quality',
    search_options={
        'relevance_threshold': 0.3,
        'sort_by': 'composite',
        'max_results': 10
    }
)
```

### 7.2 Provider Management

#### list_providers()

**Purpose**: List all available providers

**Signature**:
```python
def list_providers(self) -> List[Dict[str, Any]]
```

**Returns**:
```python
[
    {
        'name': 'fred',
        'description': 'Federal Reserve Economic Data',
        'operations': ['get_series', 'search_series', ...],
        'stats': {...},
        'health': {'score': 0.95, 'status': 'healthy'},
        'config': {...}
    },
    ...
]
```

#### get_provider_info()

**Purpose**: Get detailed information about a specific provider

**Signature**:
```python
def get_provider_info(self, provider: str) -> Dict[str, Any]
```

**Returns**: Detailed provider metadata

### 7.3 Monitoring Operations

#### get_metrics()

**Purpose**: Get performance metrics

**Signature**:
```python
def get_metrics(self) -> Dict[str, Any]
```

**Returns**:
```python
{
    'overall': {
        'total_requests': 150,
        'successful_requests': 142,
        'failed_requests': 8,
        'success_rate': 0.947
    },
    'providers': {
        'fred': {
            'requests': 100,
            'success_rate': 0.95,
            'avg_response_time': 245.5,
            'health_score': 0.92
        }
    }
}
```

#### get_metrics_report()

**Purpose**: Get human-readable metrics report

**Signature**:
```python
def get_metrics_report(self) -> Dict[str, Any]
```

---

## 8. Data Structures

### 8.1 Result Structure

```python
{
    'data': Any,                    # Actual result data
    'metadata': {
        'provider': str,            # Provider name
        'operation': str,           # Operation performed
        'timestamp': str,           # ISO 8601 timestamp
        'execution_time_ms': float, # Execution time
        'quality': {
            'score': float,         # Overall quality (0-1)
            'completeness': float,  # Data completeness (0-1)
            'freshness': float,     # Data freshness (0-1)
            'reliability': float    # Source reliability (0-1)
        },
        'enhancement': {
            'applied': bool,
            'original_params': Dict,
            'enhanced_params': Dict
        },
        'fusion': {                 # If fusion applied
            'strategy': str,
            'sources': List[str],
            'selected_source': str
        }
    }
}
```

### 8.2 Exception Hierarchy

```python
APISourceError                   # Base exception
├── ProviderNotFoundError       # Provider not registered
├── APIRateLimitError           # Rate limit exceeded
└── APIAuthenticationError      # Authentication failed
```

---

## 9. Advanced Topics

### 9.1 Adding Custom Providers

**Step 1**: Create provider class
```python
from aiecs.tools.apisource.providers import BaseAPIProvider, expose_operation

class CustomProvider(BaseAPIProvider):
    @property
    def name(self) -> str:
        return "custom"
    
    @property
    def description(self) -> str:
        return "Custom API provider"
    
    @property
    def supported_operations(self) -> List[str]:
        return ['get_data', 'search']
    
    def validate_params(self, operation: str, params: Dict) -> Tuple[bool, Optional[str]]:
        # Validation logic
        return True, None
    
    def fetch(self, operation: str, params: Dict) -> Any:
        # API call logic
        pass
    
    @expose_operation(
        operation_name='get_data',
        description='Get data from custom API'
    )
    def get_data(self, id: str, **kwargs):
        # Implementation
        pass
```

**Step 2**: Register provider
```python
from aiecs.tools.apisource.providers import register_provider

register_provider(CustomProvider)
```

### 9.2 Custom Fusion Strategies

```python
from aiecs.tools.apisource.intelligence import DataFusionEngine

class CustomFusionEngine(DataFusionEngine):
    def _fuse_custom_strategy(self, results: List[Dict]) -> Dict:
        # Custom fusion logic
        pass
```

### 9.3 Performance Optimization

**Caching**:
```python
tool = APISourceTool({
    'cache_ttl': 600,  # 10 minutes
    'enable_intelligent_cache': True
})
```

**Parallel Queries**:
```python
import asyncio

async def parallel_search():
    results = await tool.search_async(
        query="unemployment",
        providers=['fred', 'worldbank']
    )
```

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-18  
**Maintainer**: AIECS Tools Team
