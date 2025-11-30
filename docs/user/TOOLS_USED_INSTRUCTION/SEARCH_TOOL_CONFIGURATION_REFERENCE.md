# Search Tool - Configuration Reference

## Table of Contents
1. [Configuration Overview](#configuration-overview)
2. [API Credentials](#api-credentials)
3. [Performance Settings](#performance-settings)
4. [Rate Limiting](#rate-limiting)
5. [Circuit Breaker](#circuit-breaker)
6. [Enhanced Features](#enhanced-features)
7. [Caching Configuration](#caching-configuration)
8. [Environment Variables](#environment-variables)
9. [Configuration Examples](#configuration-examples)
10. [Validation & Testing](#validation--testing)

---

## 1. Configuration Overview

### 1.1 Configuration Methods

The Search Tool supports three configuration methods (in priority order):

1. **Programmatic Configuration** (Highest Priority)
   ```python
   tool = SearchTool(config={'google_api_key': 'key'})
   ```

2. **Environment Variables**
   ```bash
   export SEARCH_TOOL_GOOGLE_API_KEY="key"
   ```

3. **Global Settings** (via AIECS config)
   ```bash
   export GOOGLE_API_KEY="key"
   ```

4. **Default Values** (Lowest Priority)

### 1.2 Configuration Schema

```python
class Config(BaseModel):
    # API Credentials
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    google_application_credentials: Optional[str] = None
    
    # Performance
    max_results_per_query: int = 10
    cache_ttl: int = 3600
    timeout: int = 30
    user_agent: str = "AIECS-SearchTool/2.0"
    
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
```

---

## 2. API Credentials

### 2.1 Google API Key

**Parameter**: `google_api_key`  
**Environment Variable**: `GOOGLE_API_KEY` or `SEARCH_TOOL_GOOGLE_API_KEY`  
**Type**: `Optional[str]`  
**Default**: `None`  
**Required**: Yes (unless using service account)

**Description**: Google API key for Custom Search API access.

**How to Obtain**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Navigate to "APIs & Services" → "Credentials"
4. Click "Create Credentials" → "API Key"
5. Copy the generated key
6. (Recommended) Restrict the key to "Custom Search API"

**Configuration**:
```bash
# Environment variable
export GOOGLE_API_KEY="AIzaSyBvOkBwv7wjHjf7hK8l9m0n1o2p3q4r5s6t7u8v9w0"

# Or in .env file
GOOGLE_API_KEY=AIzaSyBvOkBwv7wjHjf7hK8l9m0n1o2p3q4r5s6t7u8v9w0
```

```python
# Programmatic
tool = SearchTool(config={
    'google_api_key': 'AIzaSyBvOkBwv7wjHjf7hK8l9m0n1o2p3q4r5s6t7u8v9w0'
})
```

**Security Best Practices**:
- Never commit API keys to version control
- Use environment variables or secret management
- Restrict API key to specific APIs and IPs
- Rotate keys regularly
- Monitor usage in Google Cloud Console

### 2.2 Google CSE ID

**Parameter**: `google_cse_id`  
**Environment Variable**: `GOOGLE_CSE_ID` or `SEARCH_TOOL_GOOGLE_CSE_ID`  
**Type**: `Optional[str]`  
**Default**: `None`  
**Required**: Yes

**Description**: Custom Search Engine ID that identifies your search engine configuration.

**How to Obtain**:
1. Go to [Google Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click "Add" to create a new search engine
3. Configure search settings:
   - Sites to search (leave blank for web-wide)
   - Language preferences
   - Search features
4. Click "Create"
5. Copy the "Search engine ID"

**Configuration**:
```bash
# Environment variable
export GOOGLE_CSE_ID="012345678901234567890:abcdefghijk"

# Or in .env file
GOOGLE_CSE_ID=012345678901234567890:abcdefghijk
```

```python
# Programmatic
tool = SearchTool(config={
    'google_cse_id': '012345678901234567890:abcdefghijk'
})
```

### 2.3 Service Account Credentials

**Parameter**: `google_application_credentials`  
**Environment Variable**: `GOOGLE_APPLICATION_CREDENTIALS` or `SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS`  
**Type**: `Optional[str]`  
**Default**: `None`  
**Required**: No (alternative to API key)

**Description**: Path to Google service account JSON file for authentication.

**How to Set Up**:
1. Go to Google Cloud Console
2. Navigate to "IAM & Admin" → "Service Accounts"
3. Click "Create Service Account"
4. Fill in details and create
5. Click on the service account
6. Go to "Keys" tab
7. Click "Add Key" → "Create new key"
8. Choose JSON format and download
9. Enable "Custom Search API" for the project

**Configuration**:
```bash
# Environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Or in .env file
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

```python
# Programmatic
tool = SearchTool(config={
    'google_application_credentials': '/path/to/service-account.json'
})
```

**When to Use**:
- Server-to-server applications
- Enhanced security requirements
- Centralized credential management
- Multiple API access needs

---

## 3. Performance Settings

### 3.1 Max Results Per Query

**Parameter**: `max_results_per_query`  
**Environment Variable**: `SEARCH_TOOL_MAX_RESULTS_PER_QUERY`  
**Type**: `int`  
**Default**: `10`  
**Range**: `1-100`

**Description**: Maximum number of results to return per single search query.

**Configuration**:
```bash
# Environment variable
export SEARCH_TOOL_MAX_RESULTS_PER_QUERY=20
```

```python
# Programmatic
tool = SearchTool(config={'max_results_per_query': 20})
```

**Recommendations**:
- **Development**: `5` - Faster testing
- **Production**: `10` - Standard
- **Data Collection**: `20-50` - Comprehensive results
- **Maximum**: `100` - Google API limit

**Impact**:
- Higher values increase API quota usage
- Higher values increase response time
- Higher values provide more comprehensive results

### 3.2 Cache TTL

**Parameter**: `cache_ttl`  
**Environment Variable**: `SEARCH_TOOL_CACHE_TTL`  
**Type**: `int`  
**Default**: `3600` (1 hour)  
**Unit**: Seconds

**Description**: Default cache time-to-live for search results.

**Configuration**:
```bash
# Environment variable
export SEARCH_TOOL_CACHE_TTL=7200  # 2 hours
```

```python
# Programmatic
tool = SearchTool(config={'cache_ttl': 7200})
```

**Recommendations**:
- **News/Real-time**: `1800` (30 minutes)
- **General**: `3600` (1 hour)
- **Stable Content**: `7200` (2 hours)
- **Definitions**: `86400` (24 hours)

**Note**: Intelligent cache uses intent-aware TTL that may override this default.

### 3.3 Timeout

**Parameter**: `timeout`  
**Environment Variable**: `SEARCH_TOOL_TIMEOUT`  
**Type**: `int`  
**Default**: `30`  
**Unit**: Seconds

**Description**: API request timeout duration.

**Configuration**:
```bash
export SEARCH_TOOL_TIMEOUT=45
```

```python
tool = SearchTool(config={'timeout': 45})
```

**Recommendations**:
- **Fast Networks**: `15-20` seconds
- **Standard**: `30` seconds
- **Slow Networks**: `45-60` seconds
- **Enterprise**: `60-120` seconds

### 3.4 User Agent

**Parameter**: `user_agent`  
**Environment Variable**: `SEARCH_TOOL_USER_AGENT`  
**Type**: `str`  
**Default**: `"AIECS-SearchTool/2.0"`

**Description**: User agent string sent with API requests.

**Configuration**:
```bash
export SEARCH_TOOL_USER_AGENT="MyCompanyBot/1.0 (contact@company.com)"
```

```python
tool = SearchTool(config={
    'user_agent': 'MyCompanyBot/1.0 (contact@company.com)'
})
```

**Best Practices**:
- Include application name and version
- Include contact information
- Follow Google's user agent guidelines
- Be descriptive and professional

---

## 4. Rate Limiting

### 4.1 Rate Limit Requests

**Parameter**: `rate_limit_requests`  
**Environment Variable**: `SEARCH_TOOL_RATE_LIMIT_REQUESTS`  
**Type**: `int`  
**Default**: `100`

**Description**: Maximum number of requests allowed within the rate limit window.

**Configuration**:
```bash
export SEARCH_TOOL_RATE_LIMIT_REQUESTS=50
```

```python
tool = SearchTool(config={'rate_limit_requests': 50})
```

**Recommendations**:
- **Free Tier**: `100` (Google's free limit)
- **Paid Tier**: `1000-10000` (based on your quota)
- **Development**: `10-20` (conservative)
- **Production**: Match your API quota

**Google Custom Search Quotas**:
- Free: 100 queries/day
- Paid: Up to 10,000 queries/day

### 4.2 Rate Limit Window

**Parameter**: `rate_limit_window`  
**Environment Variable**: `SEARCH_TOOL_RATE_LIMIT_WINDOW`  
**Type**: `int`  
**Default**: `86400` (24 hours)  
**Unit**: Seconds

**Description**: Time window for rate limiting.

**Configuration**:
```bash
export SEARCH_TOOL_RATE_LIMIT_WINDOW=3600  # 1 hour
```

```python
tool = SearchTool(config={'rate_limit_window': 3600})
```

**Common Values**:
- `3600` - 1 hour
- `86400` - 24 hours (default, matches Google's quota reset)
- `604800` - 7 days

**Note**: Should align with your API quota reset period.

### 4.3 Rate Limiting Algorithm

The Search Tool uses a **Token Bucket** algorithm:

```
Initial tokens: rate_limit_requests
Refill rate: rate_limit_requests / rate_limit_window per second
Each request consumes 1 token
Requests blocked when tokens < 1
```

**Example**:
```
rate_limit_requests = 100
rate_limit_window = 86400 (24 hours)

Refill rate = 100 / 86400 = 0.00116 tokens/second
            = 1 token every ~14.4 minutes
```

---

## 5. Circuit Breaker

### 5.1 Circuit Breaker Threshold

**Parameter**: `circuit_breaker_threshold`  
**Environment Variable**: `SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD`  
**Type**: `int`  
**Default**: `5`

**Description**: Number of consecutive failures before opening the circuit breaker.

**Configuration**:
```bash
export SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=3
```

```python
tool = SearchTool(config={'circuit_breaker_threshold': 3})
```

**Recommendations**:
- **Sensitive**: `3` - Opens quickly on failures
- **Standard**: `5` - Balanced
- **Tolerant**: `10` - More permissive

**Impact**:
- Lower values: Faster failure detection, may open on transient issues
- Higher values: More tolerant, slower to detect persistent failures

### 5.2 Circuit Breaker Timeout

**Parameter**: `circuit_breaker_timeout`  
**Environment Variable**: `SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT`  
**Type**: `int`  
**Default**: `60`  
**Unit**: Seconds

**Description**: Time to wait before attempting to close the circuit breaker (half-open state).

**Configuration**:
```bash
export SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=120
```

```python
tool = SearchTool(config={'circuit_breaker_timeout': 120})
```

**Recommendations**:
- **Quick Recovery**: `30` seconds
- **Standard**: `60` seconds
- **Conservative**: `120-300` seconds

**Circuit Breaker States**:
1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Failures exceeded threshold, requests blocked
3. **HALF_OPEN**: Testing recovery, limited requests allowed

---

## 6. Enhanced Features

### 6.1 Quality Analysis

**Parameter**: `enable_quality_analysis`  
**Environment Variable**: `SEARCH_TOOL_ENABLE_QUALITY_ANALYSIS`  
**Type**: `bool`  
**Default**: `True`

**Description**: Enable automatic result quality assessment and scoring.

**Configuration**:
```bash
export SEARCH_TOOL_ENABLE_QUALITY_ANALYSIS=true
```

```python
tool = SearchTool(config={'enable_quality_analysis': True})
```

**Features When Enabled**:
- Domain authority scoring
- Relevance scoring
- Freshness scoring
- Credibility level classification
- Quality signals analysis
- Warning detection

**Performance Impact**: ~10-20ms per result

### 6.2 Intent Analysis

**Parameter**: `enable_intent_analysis`  
**Environment Variable**: `SEARCH_TOOL_ENABLE_INTENT_ANALYSIS`  
**Type**: `bool`  
**Default**: `True`

**Description**: Enable query intent detection and automatic query enhancement.

**Configuration**:
```bash
export SEARCH_TOOL_ENABLE_INTENT_ANALYSIS=true
```

```python
tool = SearchTool(config={'enable_intent_analysis': True})
```

**Features When Enabled**:
- Intent type detection (definition, how-to, comparison, etc.)
- Automatic query enhancement
- Parameter suggestions
- Entity extraction
- Optimization suggestions

**Performance Impact**: ~5-10ms per query

### 6.3 Deduplication

**Parameter**: `enable_deduplication`  
**Environment Variable**: `SEARCH_TOOL_ENABLE_DEDUPLICATION`  
**Type**: `bool`  
**Default**: `True`

**Description**: Enable result deduplication to remove duplicate and similar results.

**Configuration**:
```bash
export SEARCH_TOOL_ENABLE_DEDUPLICATION=true
```

```python
tool = SearchTool(config={'enable_deduplication': True})
```

**Features When Enabled**:
- URL normalization
- Content similarity detection
- Configurable similarity threshold

**Related Setting**: `similarity_threshold`

### 6.4 Context Tracking

**Parameter**: `enable_context_tracking`  
**Environment Variable**: `SEARCH_TOOL_ENABLE_CONTEXT_TRACKING`  
**Type**: `bool`  
**Default**: `True`

**Description**: Enable search context tracking and preference learning.

**Configuration**:
```bash
export SEARCH_TOOL_ENABLE_CONTEXT_TRACKING=true
```

```python
tool = SearchTool(config={'enable_context_tracking': True})
```

**Features When Enabled**:
- Search history tracking
- Topic context awareness
- Preference learning
- Related query suggestions
- Domain preference tracking

**Related Setting**: `max_search_history`

### 6.5 Intelligent Cache

**Parameter**: `enable_intelligent_cache`  
**Environment Variable**: `SEARCH_TOOL_ENABLE_INTELLIGENT_CACHE`  
**Type**: `bool`  
**Default**: `True`

**Description**: Enable Redis-based intelligent caching with intent-aware TTL.

**Configuration**:
```bash
export SEARCH_TOOL_ENABLE_INTELLIGENT_CACHE=true
```

```python
tool = SearchTool(config={'enable_intelligent_cache': True})
```

**Requirements**: Redis server must be available

**Features When Enabled**:
- Intent-aware TTL strategies
- Dynamic TTL adjustment
- Quality-based caching
- Automatic cache invalidation

**Intent-Aware TTL**:
- Definitions: 30 days
- Tutorials: 7 days
- News: 1 hour
- Academic: 30 days
- Products: 1 day
- General: 1 hour (default)

### 6.6 Similarity Threshold

**Parameter**: `similarity_threshold`  
**Environment Variable**: `SEARCH_TOOL_SIMILARITY_THRESHOLD`  
**Type**: `float`  
**Default**: `0.85`  
**Range**: `0.0-1.0`

**Description**: Similarity threshold for deduplication (0=different, 1=identical).

**Configuration**:
```bash
export SEARCH_TOOL_SIMILARITY_THRESHOLD=0.90
```

```python
tool = SearchTool(config={'similarity_threshold': 0.90})
```

**Recommendations**:
- **Strict**: `0.90-0.95` - Only very similar results removed
- **Standard**: `0.85` - Balanced
- **Aggressive**: `0.70-0.80` - More deduplication

### 6.7 Max Search History

**Parameter**: `max_search_history`  
**Environment Variable**: `SEARCH_TOOL_MAX_SEARCH_HISTORY`  
**Type**: `int`  
**Default**: `10`

**Description**: Maximum number of searches to keep in context history.

**Configuration**:
```bash
export SEARCH_TOOL_MAX_SEARCH_HISTORY=20
```

```python
tool = SearchTool(config={'max_search_history': 20})
```

**Recommendations**:
- **Minimal**: `5` - Recent context only
- **Standard**: `10` - Balanced
- **Comprehensive**: `20-50` - Extended context

---

## 7. Caching Configuration

### 7.1 Redis Configuration

The intelligent cache requires Redis. Configure Redis connection via AIECS global settings:

```bash
# .env file
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=optional_password
REDIS_SSL=false
```

### 7.2 Cache Key Structure

```
search:{query}:{num_results}:{language}:{country}:{date_restrict}:{file_type}
```

Example:
```
search:machine learning:10:en:us::
search:climate change:10:en:us:m6:pdf
```

### 7.3 Cache Invalidation

Caches are automatically invalidated based on:
- TTL expiration
- Intent-aware TTL strategies
- Quality-based adjustments
- Manual invalidation (if needed)

---

## 8. Environment Variables

### 8.1 Complete Environment Variable List

```bash
# API Credentials
GOOGLE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_cse_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Performance
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
SEARCH_TOOL_CACHE_TTL=3600
SEARCH_TOOL_TIMEOUT=30
SEARCH_TOOL_USER_AGENT="AIECS-SearchTool/2.0"

# Rate Limiting
SEARCH_TOOL_RATE_LIMIT_REQUESTS=100
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400

# Circuit Breaker
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=5
SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=60

# Retry Logic
SEARCH_TOOL_RETRY_ATTEMPTS=3
SEARCH_TOOL_RETRY_BACKOFF=2.0

# Enhanced Features
SEARCH_TOOL_ENABLE_QUALITY_ANALYSIS=true
SEARCH_TOOL_ENABLE_INTENT_ANALYSIS=true
SEARCH_TOOL_ENABLE_DEDUPLICATION=true
SEARCH_TOOL_ENABLE_CONTEXT_TRACKING=true
SEARCH_TOOL_ENABLE_INTELLIGENT_CACHE=true

# Tuning
SEARCH_TOOL_SIMILARITY_THRESHOLD=0.85
SEARCH_TOOL_MAX_SEARCH_HISTORY=10

# Redis (for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### 8.2 Environment Variable Naming

**Pattern**: `SEARCH_TOOL_{PARAMETER_NAME}`

**Examples**:
- `google_api_key` → `SEARCH_TOOL_GOOGLE_API_KEY`
- `max_results_per_query` → `SEARCH_TOOL_MAX_RESULTS_PER_QUERY`
- `enable_quality_analysis` → `SEARCH_TOOL_ENABLE_QUALITY_ANALYSIS`

**Global Overrides** (without `SEARCH_TOOL_` prefix):
- `GOOGLE_API_KEY`
- `GOOGLE_CSE_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`

---

## 9. Configuration Examples

### 9.1 Development Configuration

```bash
# .env.development
GOOGLE_API_KEY=dev_api_key
GOOGLE_CSE_ID=dev_cse_id

# Conservative limits for testing
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=5
SEARCH_TOOL_CACHE_TTL=1800
SEARCH_TOOL_RATE_LIMIT_REQUESTS=10
SEARCH_TOOL_RATE_LIMIT_WINDOW=3600
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=10
SEARCH_TOOL_TIMEOUT=15

# Enable all features for testing
SEARCH_TOOL_ENABLE_QUALITY_ANALYSIS=true
SEARCH_TOOL_ENABLE_INTENT_ANALYSIS=true
SEARCH_TOOL_ENABLE_DEDUPLICATION=true
SEARCH_TOOL_ENABLE_CONTEXT_TRACKING=true
SEARCH_TOOL_ENABLE_INTELLIGENT_CACHE=true
```

### 9.2 Production Configuration

```bash
# .env.production
GOOGLE_API_KEY=prod_api_key
GOOGLE_CSE_ID=prod_cse_id

# Optimized for performance and reliability
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
SEARCH_TOOL_CACHE_TTL=7200
SEARCH_TOOL_RATE_LIMIT_REQUESTS=100
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=3
SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=60
SEARCH_TOOL_RETRY_ATTEMPTS=5
SEARCH_TOOL_RETRY_BACKOFF=2.0
SEARCH_TOOL_TIMEOUT=45

# All features enabled
SEARCH_TOOL_ENABLE_QUALITY_ANALYSIS=true
SEARCH_TOOL_ENABLE_INTENT_ANALYSIS=true
SEARCH_TOOL_ENABLE_DEDUPLICATION=true
SEARCH_TOOL_ENABLE_CONTEXT_TRACKING=true
SEARCH_TOOL_ENABLE_INTELLIGENT_CACHE=true

# Redis for caching
REDIS_HOST=redis.production.com
REDIS_PORT=6379
REDIS_PASSWORD=secure_password
REDIS_SSL=true
```

### 9.3 High-Volume Configuration

```bash
# .env.high-volume
GOOGLE_API_KEY=enterprise_api_key
GOOGLE_CSE_ID=enterprise_cse_id

# High throughput settings
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=20
SEARCH_TOOL_CACHE_TTL=3600
SEARCH_TOOL_RATE_LIMIT_REQUESTS=10000
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=10
SEARCH_TOOL_TIMEOUT=60

# Aggressive caching
SEARCH_TOOL_ENABLE_INTELLIGENT_CACHE=true
REDIS_HOST=redis-cluster.com
REDIS_PORT=6379
```

### 9.4 Minimal Configuration

```bash
# .env.minimal
GOOGLE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_cse_id

# Disable enhanced features for minimal overhead
SEARCH_TOOL_ENABLE_QUALITY_ANALYSIS=false
SEARCH_TOOL_ENABLE_INTENT_ANALYSIS=false
SEARCH_TOOL_ENABLE_DEDUPLICATION=false
SEARCH_TOOL_ENABLE_CONTEXT_TRACKING=false
SEARCH_TOOL_ENABLE_INTELLIGENT_CACHE=false
```

### 9.5 Programmatic Configuration

```python
from aiecs.tools.search_tool import SearchTool

# Development
dev_tool = SearchTool(config={
    'google_api_key': 'dev_key',
    'google_cse_id': 'dev_cse',
    'max_results_per_query': 5,
    'rate_limit_requests': 10,
    'circuit_breaker_threshold': 10
})

# Production
prod_tool = SearchTool(config={
    'google_api_key': 'prod_key',
    'google_cse_id': 'prod_cse',
    'max_results_per_query': 10,
    'cache_ttl': 7200,
    'rate_limit_requests': 100,
    'circuit_breaker_threshold': 3,
    'retry_attempts': 5,
    'enable_quality_analysis': True,
    'enable_intent_analysis': True,
    'enable_intelligent_cache': True
})

# Custom
custom_tool = SearchTool(config={
    'google_api_key': 'key',
    'google_cse_id': 'cse',
    'user_agent': 'MyBot/1.0 (contact@company.com)',
    'similarity_threshold': 0.90,
    'max_search_history': 20
})
```

---

## 10. Validation & Testing

### 10.1 Validate Configuration

```python
from aiecs.tools import get_tool

tool = get_tool('search')

# Validate credentials
status = tool.validate_credentials()
print(f"Valid: {status['valid']}")
print(f"Method: {status['method']}")
print(f"CSE ID Present: {status['cse_id_present']}")

if not status['valid']:
    print(f"Error: {status['error']}")
```

### 10.2 Test Configuration

```python
# Test basic search
try:
    results = tool.search_web("test", num_results=1)
    print("✓ Search working")
except Exception as e:
    print(f"✗ Search failed: {e}")

# Check quota
quota = tool.get_quota_status()
print(f"Quota: {quota['remaining_quota']}/{quota['quota_limit']}")
print(f"Circuit Breaker: {quota['circuit_breaker_state']}")

# Check features
print(f"Quality Analysis: {tool.config.enable_quality_analysis}")
print(f"Intent Analysis: {tool.config.enable_intent_analysis}")
print(f"Intelligent Cache: {tool.config.enable_intelligent_cache}")
```

### 10.3 Configuration Checklist

- [ ] API credentials configured (API key or service account)
- [ ] CSE ID configured
- [ ] Rate limits match API quota
- [ ] Circuit breaker threshold appropriate
- [ ] Cache TTL appropriate for use case
- [ ] Enhanced features enabled as needed
- [ ] Redis configured (if using intelligent cache)
- [ ] User agent set appropriately
- [ ] Timeout appropriate for network conditions
- [ ] Configuration validated successfully
- [ ] Test search successful

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-18  
**Maintainer**: AIECS Tools Team
