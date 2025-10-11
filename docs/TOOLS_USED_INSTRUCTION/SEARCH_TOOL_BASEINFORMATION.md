# Search Tool Technical Documentation

## 1. Overview

**Purpose**: The `SearchTool` is a production-ready web search tool that integrates Google Custom Search API with comprehensive features for AI agents. It provides multiple search types (web, image, news, video) with advanced capabilities including rate limiting, circuit breaker pattern, intelligent caching, and full AIECS architecture compliance.

**Core Value**:
- **Multiple Search Types**: Web, image, news, and video search
- **Dual Authentication**: API key and service account support
- **Rate Protection**: Token bucket rate limiter prevents quota exhaustion
- **Resilience**: Circuit breaker handles API failures gracefully
- **Performance**: Intelligent caching reduces redundant API calls
- **Batch Operations**: Parallel execution for multiple queries
- **Production Ready**: Comprehensive error handling and monitoring

## 2. Features

### 2.1 Search Types

1. **Web Search** (`search_web`)
   - Standard web search with comprehensive filters
   - Language and country targeting
   - Safe search control
   - Date restrictions
   - File type filtering
   - Term exclusion

2. **Image Search** (`search_images`)
   - Image-specific search
   - Size filtering (icon to huge)
   - Type filtering (clipart, photo, etc.)
   - Color type filtering
   - Thumbnail and full-size URLs

3. **News Search** (`search_news`)
   - News article search
   - Date-based filtering
   - Sort by date or relevance
   - Language targeting

4. **Video Search** (`search_videos`)
   - Video content search
   - Safe search control
   - Language targeting

### 2.2 Advanced Features

1. **Paginated Search** (`search_paginated`)
   - Automatically handle pagination
   - Retrieve up to 100 results
   - Intelligent quota management

2. **Batch Search** (`search_batch`)
   - Execute multiple queries in parallel
   - Async execution for efficiency
   - Per-query error handling

3. **Rate Limiting**
   - Token bucket algorithm
   - Configurable limits (default: 100 requests/day)
   - Automatic refill mechanism
   - Real-time quota tracking

4. **Circuit Breaker**
   - Three states: CLOSED, OPEN, HALF_OPEN
   - Automatic failure detection
   - Exponential backoff recovery
   - Health check mechanism

5. **Intelligent Caching**
   - Content-based cache keys
   - Configurable TTL (default: 1 hour)
   - Automatic cache invalidation
   - Cache hit tracking

## 3. Installation & Setup

### 3.1 Dependencies

The Search Tool requires Google API libraries. These are automatically included in the AIECS package dependencies:

```bash
# Dependencies are included in pyproject.toml
google-api-python-client>=2.108.0
google-auth>=2.25.0
google-auth-httplib2>=0.2.0
google-auth-oauthlib>=1.2.0
```

### 3.2 Google Custom Search Setup

1. **Create a Custom Search Engine**:
   - Go to https://programmablesearchengine.google.com/
   - Create a new search engine
   - Note down your **Search Engine ID (CSE ID)**

2. **Get API Credentials**:

   **Option A: API Key (Recommended for Custom Search)**
   - Go to https://console.cloud.google.com/apis/credentials
   - Create an API key
   - Enable "Custom Search API"
   - Note down your **API Key**

   **Option B: Service Account (Advanced)**
   - Go to https://console.cloud.google.com/iam-admin/serviceaccounts
   - Create a service account
   - Download the JSON key file
   - Enable "Custom Search API"

### 3.3 Configuration

Set environment variables in your `.env` file:

```bash
# Required: API Key Method (Recommended)
GOOGLE_API_KEY=your_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id

# OR: Service Account Method
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CSE_ID=your_custom_search_engine_id

# Optional: Rate Limiting (defaults shown)
SEARCH_TOOL_RATE_LIMIT_REQUESTS=100
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400  # 24 hours
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=5
SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=60
```

## 4. Usage Examples

### 4.1 Basic Usage

```python
from aiecs.tools import get_tool

# Initialize the search tool
search_tool = get_tool('search')

# Simple web search
results = search_tool.search_web("artificial intelligence", num_results=5)
for result in results:
    print(f"Title: {result['title']}")
    print(f"URL: {result['link']}")
    print(f"Snippet: {result['snippet']}\n")
```

### 4.2 Advanced Web Search

```python
# Web search with filters
results = search_tool.search_web(
    query="climate change research",
    num_results=10,
    language="en",
    country="us",
    safe_search="medium",
    date_restrict="m6",  # Last 6 months
    file_type="pdf",     # Only PDF files
    exclude_terms="opinion"
)
```

### 4.3 Image Search

```python
# Search for images
images = search_tool.search_images(
    query="sunset beach",
    num_results=10,
    image_size="large",
    image_type="photo",
    image_color_type="color",
    safe_search="high"
)

for img in images:
    print(f"Image URL: {img['link']}")
    print(f"Thumbnail: {img['image']['thumbnailLink']}")
    print(f"Dimensions: {img['image']['width']}x{img['image']['height']}\n")
```

### 4.4 News Search

```python
# Search for recent news
news = search_tool.search_news(
    query="technology innovation",
    num_results=10,
    language="en",
    date_restrict="d7",  # Last 7 days
    sort_by="date"
)
```

### 4.5 Paginated Search

```python
# Get more than 10 results (up to 100)
results = search_tool.search_paginated(
    query="machine learning",
    total_results=50,
    search_type="web",
    language="en"
)

print(f"Retrieved {len(results)} results")
```

### 4.6 Batch Search

```python
import asyncio

# Search multiple queries in parallel
queries = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural networks"
]

results = asyncio.run(search_tool.search_batch(
    queries=queries,
    search_type="web",
    num_results=5
))

for query, query_results in results.items():
    print(f"\nResults for '{query}':")
    for result in query_results:
        print(f"  - {result['title']}")
```

### 4.7 Monitoring & Quota

```python
# Check quota status
quota = search_tool.get_quota_status()
print(f"Remaining quota: {quota['remaining_quota']}")
print(f"Circuit breaker state: {quota['circuit_breaker_state']}")
print(f"Total requests: {quota['metrics']['total_requests']}")

# Get detailed metrics
metrics = search_tool.get_metrics()
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Cache hits: {metrics['cache_hits']}")
```

### 4.8 Credential Validation

```python
# Validate API credentials
status = search_tool.validate_credentials()
if status['valid']:
    print(f"✓ Credentials valid ({status['method']})")
else:
    print(f"✗ Validation failed: {status['error']}")
```

## 5. LangChain Integration

### 5.1 Using with LangChain Agents

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from aiecs.tools.langchain_adapter import get_langchain_tools

# Get search tools for LangChain
tools = get_langchain_tools(['search'])

# Create agent
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Use the agent
result = agent_executor.invoke({
    "input": "Find recent news about artificial intelligence"
})
print(result['output'])
```

### 5.2 Available LangChain Tools

The Search Tool creates 9 individual LangChain tools:
- `search_search_web` - Web search
- `search_search_images` - Image search
- `search_search_news` - News search
- `search_search_videos` - Video search
- `search_search_paginated` - Paginated search
- `search_search_batch` - Batch search
- `search_validate_credentials` - Credential validation
- `search_get_quota_status` - Quota status
- `search_get_metrics` - Usage metrics

## 6. Error Handling

### 6.1 Exception Hierarchy

```python
SearchToolError                  # Base exception
├── AuthenticationError          # Invalid credentials
├── QuotaExceededError           # API quota exceeded
├── RateLimitError               # Rate limit reached
├── CircuitBreakerOpenError      # Circuit breaker open
├── SearchAPIError               # API errors
└── ValidationError              # Input validation errors
```

### 6.2 Error Handling Examples

```python
from aiecs.tools.task_tools.search_tool import (
    RateLimitError,
    QuotaExceededError,
    AuthenticationError
)

try:
    results = search_tool.search_web("query")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Wait and retry
except QuotaExceededError as e:
    print(f"API quota exceeded: {e}")
    # Implement fallback or notify admin
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Check credentials
except Exception as e:
    print(f"Unexpected error: {e}")
```

## 7. Configuration Reference

### 7.1 Search Tool Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `google_api_key` | str | "" | Google API key |
| `google_cse_id` | str | "" | Custom Search Engine ID |
| `google_application_credentials` | str | "" | Service account JSON path |
| `max_results_per_query` | int | 10 | Max results per request |
| `cache_ttl` | int | 3600 | Cache TTL in seconds |
| `rate_limit_requests` | int | 100 | Max requests per window |
| `rate_limit_window` | int | 86400 | Rate limit window (seconds) |
| `circuit_breaker_threshold` | int | 5 | Failures before opening |
| `circuit_breaker_timeout` | int | 60 | Timeout before half-open |
| `retry_attempts` | int | 3 | Number of retries |
| `retry_backoff` | float | 2.0 | Backoff multiplier |
| `timeout` | int | 30 | Request timeout |

### 7.2 Environment Variables

```bash
# Global Configuration (in .env)
GOOGLE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_cse_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json

# Tool-specific overrides
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
SEARCH_TOOL_CACHE_TTL=3600
SEARCH_TOOL_RATE_LIMIT_REQUESTS=100
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=5
SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=60
SEARCH_TOOL_RETRY_ATTEMPTS=3
SEARCH_TOOL_RETRY_BACKOFF=2.0
SEARCH_TOOL_TIMEOUT=30
```

## 8. Best Practices

### 8.1 Performance Optimization

1. **Use Caching**:
   ```python
   # Results are automatically cached for 1 hour
   # Identical queries will use cached results
   ```

2. **Batch Similar Queries**:
   ```python
   # Use batch search for multiple queries
   results = await search_tool.search_batch(queries)
   ```

3. **Paginate Wisely**:
   ```python
   # Only request what you need
   results = search_tool.search_paginated(query, total_results=20)
   ```

### 8.2 Quota Management

1. **Monitor Quota**:
   ```python
   quota = search_tool.get_quota_status()
   if quota['remaining_quota'] < 10:
       print("Warning: Low quota remaining")
   ```

2. **Handle Rate Limits**:
   ```python
   try:
       results = search_tool.search_web(query)
   except RateLimitError as e:
       # Implement exponential backoff
       time.sleep(60)
   ```

3. **Configure Appropriate Limits**:
   ```bash
   # For high-volume applications
   SEARCH_TOOL_RATE_LIMIT_REQUESTS=1000
   SEARCH_TOOL_RATE_LIMIT_WINDOW=86400
   ```

### 8.3 Error Resilience

1. **Use Circuit Breaker**:
   ```python
   # Circuit breaker automatically handles API failures
   # No manual intervention needed
   ```

2. **Implement Fallbacks**:
   ```python
   try:
       results = search_tool.search_web(query)
   except QuotaExceededError:
       # Use alternative search source
       results = fallback_search(query)
   ```

## 9. API Limits & Quotas

### 9.1 Google Custom Search Limits

- **Free Tier**: 100 queries/day
- **Paid Tier**: Up to 10,000 queries/day
- **Results per Query**: Maximum 10 results
- **Total Results**: Maximum 100 results via pagination

### 9.2 Quota Management

The Search Tool implements several mechanisms to manage quotas:

1. **Rate Limiting**: Token bucket algorithm
2. **Circuit Breaker**: Prevents cascading failures
3. **Retry Logic**: Exponential backoff for transient errors
4. **Caching**: Reduces redundant API calls

## 10. Troubleshooting

### 10.1 Common Issues

**Issue: AuthenticationError**
```
Solution: Check that GOOGLE_API_KEY and GOOGLE_CSE_ID are set correctly
```

**Issue: QuotaExceededError**
```
Solution: You've reached your daily quota. Wait 24 hours or upgrade your plan
```

**Issue: RateLimitError**
```
Solution: You're making requests too quickly. The tool will automatically back off
```

**Issue: CircuitBreakerOpenError**
```
Solution: The API is experiencing issues. Wait for the circuit breaker to recover
```

### 10.2 Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Now all tool operations will be logged
search_tool = get_tool('search')
```

## 11. Testing

### 11.1 Unit Tests

```python
from aiecs.tools import get_tool

def test_search_tool_initialization():
    tool = get_tool('search')
    assert tool is not None
    assert tool.__class__.__name__ == 'SearchTool'

def test_quota_status():
    tool = get_tool('search')
    status = tool.get_quota_status()
    assert 'remaining_quota' in status
    assert 'circuit_breaker_state' in status
```

### 11.2 Integration Tests

```python
def test_web_search():
    tool = get_tool('search')
    results = tool.search_web("test query", num_results=5)
    assert isinstance(results, list)
    assert len(results) <= 5
    assert all('title' in r for r in results)
```

## 12. Related Documentation

- [Base Tool Documentation](TOOLS_BASE_TOOL.md)
- [LangChain Adapter](TOOLS_LANGCHAIN_ADAPTER.md)
- [Schema Generator](TOOLS_SCHEMA_GENERATOR.md)
- [Tool Naming Convention](TOOL_NAMING_CONVENTION.md)
- [Tool Development Guide](../../aiecs/scripts/tools_develop/README.md)

## 13. Changelog

### Version 1.0.0 (2025-10-11)
- Initial release
- Web, image, news, and video search
- Dual authentication support
- Rate limiting and circuit breaker
- Intelligent caching
- Batch and paginated search
- Full LangChain integration

---

**Last Updated**: 2025-10-11  
**Maintainer**: AIECS Tools Team

