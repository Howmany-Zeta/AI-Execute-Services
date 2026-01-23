# APISource Tool - Configuration Reference

## Table of Contents
1. [Configuration Overview](#configuration-overview)
2. [Configuration Parameters](#configuration-parameters)
3. [API Credentials](#api-credentials)
4. [Performance Settings](#performance-settings)
5. [Feature Flags](#feature-flags)
6. [Provider-Specific Configuration](#provider-specific-configuration)
7. [Environment Variables](#environment-variables)
8. [Configuration Examples](#configuration-examples)
9. [Validation and Testing](#validation-and-testing)

---

## 1. Configuration Overview

### 1.1 Configuration Methods

The APISource Tool supports multiple configuration methods:

1. **Dictionary Configuration**:
```python
from aiecs.tools.apisource import APISourceTool

config = {
    'fred_api_key': 'YOUR_KEY',
    'cache_ttl': 300,
    'enable_fallback': True
}
tool = APISourceTool(config)
```

2. **Environment Variables**:
```python
import os
os.environ['APISOURCE_FRED_API_KEY'] = 'YOUR_KEY'
os.environ['APISOURCE_CACHE_TTL'] = '300'

tool = APISourceTool()  # Auto-loads from environment
```

3. **Configuration File**:
```python
import json

with open('apisource_config.json') as f:
    config = json.load(f)

tool = APISourceTool(config)
```

4. **Pydantic Model**:
```python
from aiecs.tools.apisource.tool import Config

config = Config(
    fred_api_key='YOUR_KEY',
    cache_ttl=300,
    enable_fallback=True
)
tool = APISourceTool(config)
```

### 1.2 Configuration Priority

When multiple configuration sources are present, the priority is:

1. **Explicit parameters** (highest priority)
2. **Configuration dictionary/object**
3. **Environment variables**
4. **Default values** (lowest priority)

---

## 2. Configuration Parameters

### 2.1 Complete Parameter Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fred_api_key` | str | None | FRED API key |
| `newsapi_api_key` | str | None | News API key |
| `census_api_key` | str | None | Census Bureau API key |
| `cache_ttl` | int | 300 | Cache TTL in seconds |
| `default_timeout` | int | 30 | Request timeout in seconds |
| `max_retries` | int | 3 | Maximum retry attempts |
| `enable_rate_limiting` | bool | True | Enable rate limiting |
| `enable_fallback` | bool | True | Enable provider fallback |
| `enable_data_fusion` | bool | True | Enable data fusion |
| `enable_query_enhancement` | bool | True | Enable query enhancement |
| `enable_intelligent_cache` | bool | True | Enable intelligent caching |
| `log_level` | str | 'INFO' | Logging level |
| `metrics_enabled` | bool | True | Enable metrics collection |

### 2.2 Parameter Details

#### cache_ttl
- **Type**: Integer
- **Default**: 300 (5 minutes)
- **Range**: 0-86400 (0 = no cache, 86400 = 24 hours)
- **Description**: Time-to-live for cached results in seconds
- **Recommendation**: 
  - Development: 60-300 seconds
  - Production: 300-3600 seconds
  - High-frequency data: 60-300 seconds
  - Static data: 3600-86400 seconds

#### default_timeout
- **Type**: Integer
- **Default**: 30 seconds
- **Range**: 5-300 seconds
- **Description**: Maximum time to wait for API response
- **Recommendation**:
  - Fast APIs (FRED, News): 10-30 seconds
  - Slow APIs (World Bank): 30-60 seconds
  - Batch operations: 60-120 seconds

#### max_retries
- **Type**: Integer
- **Default**: 3
- **Range**: 0-10
- **Description**: Maximum number of retry attempts for failed requests
- **Recommendation**:
  - Production: 3-5 retries
  - Development: 1-2 retries
  - Critical operations: 5-10 retries

#### enable_rate_limiting
- **Type**: Boolean
- **Default**: True
- **Description**: Enable automatic rate limiting to prevent API quota exhaustion
- **Recommendation**: Always True in production

#### enable_fallback
- **Type**: Boolean
- **Default**: True
- **Description**: Enable automatic failover to alternative providers
- **Recommendation**: True for high-availability applications

#### enable_data_fusion
- **Type**: Boolean
- **Default**: True
- **Description**: Enable intelligent merging of multi-provider results
- **Recommendation**: True for search operations

#### enable_query_enhancement
- **Type**: Boolean
- **Default**: True
- **Description**: Enable automatic parameter completion from query text
- **Recommendation**: True for AI agent integration

#### enable_intelligent_cache
- **Type**: Boolean
- **Default**: True
- **Description**: Enable intent-aware cache TTL strategies
- **Recommendation**: True for optimal performance

---

## 3. API Credentials

### 3.1 FRED API Key

**Obtaining the Key**:
1. Visit https://fred.stlouisfed.org/docs/api/api_key.html
2. Register for a free account
3. Request an API key

**Configuration**:
```python
# Method 1: Direct configuration
tool = APISourceTool({'fred_api_key': 'YOUR_FRED_KEY'})

# Method 2: Environment variable
export APISOURCE_FRED_API_KEY="YOUR_FRED_KEY"

# Method 3: Configuration file
{
    "fred_api_key": "YOUR_FRED_KEY"
}
```

**Rate Limits**:
- Free tier: 120 requests per minute
- No daily limit

### 3.2 News API Key

**Obtaining the Key**:
1. Visit https://newsapi.org/register
2. Choose a plan (Free tier available)
3. Get your API key

**Configuration**:
```python
tool = APISourceTool({'newsapi_api_key': 'YOUR_NEWS_KEY'})
```

**Rate Limits**:
- Free tier: 100 requests per day
- Developer tier: 250 requests per day
- Business tier: 250,000 requests per day

### 3.3 Census Bureau API Key

**Obtaining the Key**:
1. Visit https://api.census.gov/data/key_signup.html
2. Fill out the request form
3. Receive key via email

**Configuration**:
```python
tool = APISourceTool({'census_api_key': 'YOUR_CENSUS_KEY'})
```

**Rate Limits**:
- 500 requests per IP per day (without key)
- Higher limits with API key

### 3.4 World Bank API

**No API Key Required**:
```python
# World Bank API is publicly accessible
tool = APISourceTool()  # No key needed for World Bank
```

**Rate Limits**:
- No official rate limit
- Recommended: Max 10 requests per second

### 3.5 Alpha Vantage API Key

**Obtaining the Key**:
1. Visit https://www.alphavantage.co/support/#api-key
2. Register for a free account
3. Get your API key

**Configuration**:
```python
tool = APISourceTool({'alphavantage_api_key': 'YOUR_ALPHAVANTAGE_KEY'})
```

**Rate Limits**:
- Free tier: 5 API requests per minute, 500 per day
- Premium tiers available with higher limits

### 3.6 REST Countries API

**No API Key Required**:
```python
# REST Countries API is publicly accessible
tool = APISourceTool()  # No key needed for REST Countries
```

**Rate Limits**:
- No official rate limit
- Recommended: Max 10 requests per second

### 3.7 ExchangeRate-API

**No API Key Required (Free Tier)**:
```python
# ExchangeRate-API free tier works without key
tool = APISourceTool()  # No key needed for free tier
```

**Optional API Key for Enhanced Features**:
```python
tool = APISourceTool({'exchangerate_api_key': 'YOUR_EXCHANGERATE_KEY'})
```

**Rate Limits**:
- Free tier: 1,500 requests per month
- Standard tier: Higher limits with API key

### 3.8 Open Library API

**No API Key Required**:
```python
# Open Library API is completely free and open
tool = APISourceTool()  # No key needed for Open Library
```

**Rate Limits**:
- No official rate limit
- Recommended: Max 10 requests per second
- Be respectful of the free service

---

## 4. Performance Settings

### 4.1 Caching Configuration

```python
config = {
    # Basic caching
    'cache_ttl': 300,  # 5 minutes
    
    # Intelligent caching (intent-aware TTL)
    'enable_intelligent_cache': True,
    
    # Cache backend (optional)
    'cache_backend': 'redis',  # 'memory' or 'redis'
    'redis_url': 'redis://localhost:6379/0'
}
```

**Intelligent Cache TTL Strategies**:
- **Recent data queries**: 60 seconds
- **Historical data**: 3600 seconds (1 hour)
- **Metadata queries**: 86400 seconds (24 hours)
- **Search queries**: 300 seconds (5 minutes)

### 4.2 Timeout Configuration

```python
config = {
    # Global timeout
    'default_timeout': 30,
    
    # Provider-specific timeouts
    'provider_timeouts': {
        'fred': 15,
        'worldbank': 45,
        'newsapi': 20,
        'census': 30
    }
}
```

### 4.3 Retry Configuration

```python
config = {
    'max_retries': 3,
    'retry_backoff_factor': 2.0,  # Exponential backoff multiplier
    'retry_jitter': True,          # Add random jitter to prevent thundering herd
    'retry_on_status_codes': [429, 500, 502, 503, 504]
}
```

**Retry Delay Calculation**:
```
delay = base_delay * (backoff_factor ** attempt) + random_jitter
```

Example:
- Attempt 1: 1.0s + jitter
- Attempt 2: 2.0s + jitter
- Attempt 3: 4.0s + jitter

---

## 5. Feature Flags

### 5.1 Query Enhancement

```python
config = {
    'enable_query_enhancement': True,
    'query_enhancement_config': {
        'confidence_threshold': 0.5,  # Min confidence for auto-enhancement
        'max_enhancements': 5,         # Max parameters to add
        'preserve_explicit_params': True  # Don't override user params
    }
}
```

### 5.2 Fallback Strategy

```python
config = {
    'enable_fallback': True,
    'fallback_config': {
        'max_fallback_attempts': 2,
        'fallback_timeout_multiplier': 1.5,  # Increase timeout for fallback
        'preserve_quality_threshold': 0.7     # Min quality for fallback result
    }
}
```

### 5.3 Data Fusion

```python
config = {
    'enable_data_fusion': True,
    'data_fusion_config': {
        'default_strategy': 'best_quality',  # 'best_quality', 'merge_all', 'consensus'
        'quality_weight': 0.6,
        'freshness_weight': 0.3,
        'completeness_weight': 0.1
    }
}
```

### 5.4 Rate Limiting

```python
config = {
    'enable_rate_limiting': True,
    'rate_limit_config': {
        'fred': {
            'tokens_per_second': 2.0,  # 120 per minute
            'max_tokens': 10
        },
        'newsapi': {
            'tokens_per_second': 0.001,  # ~100 per day
            'max_tokens': 5
        },
        'census': {
            'tokens_per_second': 0.005,  # ~500 per day
            'max_tokens': 10
        }
    }
}
```

---

## 6. Provider-Specific Configuration

### 6.1 FRED Provider

```python
config = {
    'fred_api_key': 'YOUR_KEY',
    'fred_config': {
        'base_url': 'https://api.stlouisfed.org/fred',
        'timeout': 15,
        'default_file_type': 'json',
        'default_frequency': 'a',  # Annual
        'default_units': 'lin'     # Linear
    }
}
```

### 6.2 World Bank Provider

```python
config = {
    'worldbank_config': {
        'base_url': 'https://api.worldbank.org/v2',
        'timeout': 45,
        'default_format': 'json',
        'default_per_page': 50,
        'default_language': 'en'
    }
}
```

### 6.3 News API Provider

```python
config = {
    'newsapi_api_key': 'YOUR_KEY',
    'newsapi_config': {
        'base_url': 'https://newsapi.org/v2',
        'timeout': 20,
        'default_language': 'en',
        'default_page_size': 20,
        'default_sort_by': 'publishedAt'
    }
}
```

### 6.4 Census Provider

```python
config = {
    'census_api_key': 'YOUR_KEY',
    'census_config': {
        'base_url': 'https://api.census.gov/data',
        'timeout': 30,
        'default_year': 2021,
        'default_dataset': 'acs/acs5'
    }
}
```

### 6.5 Alpha Vantage Provider

```python
config = {
    'alphavantage_api_key': 'YOUR_KEY',
    'alphavantage_config': {
        'base_url': 'https://www.alphavantage.co/query',
        'timeout': 30,
        'default_datatype': 'json'
    }
}
```

### 6.6 REST Countries Provider

```python
config = {
    'restcountries_config': {
        'base_url': 'https://restcountries.com/v3.1',
        'timeout': 30
    }
}
```

### 6.7 ExchangeRate Provider

```python
config = {
    'exchangerate_api_key': 'YOUR_KEY',  # Optional
    'exchangerate_config': {
        'base_url': 'https://api.exchangerate-api.com/v4',
        'timeout': 30
    }
}
```

### 6.8 Open Library Provider

```python
config = {
    'openlibrary_config': {
        'base_url': 'https://openlibrary.org',
        'timeout': 30,
        'rate_limit': 10,  # Requests per second
        'max_burst': 20    # Maximum burst size
    }
}
```

---

## 7. Environment Variables

### 7.1 Variable Reference

All configuration parameters can be set via environment variables with the `APISOURCE_` prefix:

```bash
# API Keys
export APISOURCE_FRED_API_KEY="your_fred_key"
export APISOURCE_NEWSAPI_API_KEY="your_news_key"
export APISOURCE_CENSUS_API_KEY="your_census_key"
export APISOURCE_ALPHAVANTAGE_API_KEY="your_alphavantage_key"
export APISOURCE_EXCHANGERATE_API_KEY="your_exchangerate_key"  # Optional

# Performance
export APISOURCE_CACHE_TTL="300"
export APISOURCE_DEFAULT_TIMEOUT="30"
export APISOURCE_MAX_RETRIES="3"

# Feature Flags
export APISOURCE_ENABLE_RATE_LIMITING="true"
export APISOURCE_ENABLE_FALLBACK="true"
export APISOURCE_ENABLE_DATA_FUSION="true"
export APISOURCE_ENABLE_QUERY_ENHANCEMENT="true"

# Logging
export APISOURCE_LOG_LEVEL="INFO"
export APISOURCE_METRICS_ENABLED="true"
```

### 7.2 Loading from .env File

```bash
# .env file
APISOURCE_FRED_API_KEY=your_fred_key
APISOURCE_NEWSAPI_API_KEY=your_news_key
APISOURCE_CACHE_TTL=300
APISOURCE_ENABLE_FALLBACK=true
```

```python
# Load with python-dotenv
from dotenv import load_dotenv
load_dotenv()

# Tool automatically picks up environment variables
tool = APISourceTool()
```

---

## 8. Configuration Examples

### 8.1 Development Configuration

```json
{
    "fred_api_key": "YOUR_FRED_KEY",
    "newsapi_api_key": "YOUR_NEWS_KEY",
    "cache_ttl": 60,
    "default_timeout": 30,
    "max_retries": 1,
    "enable_rate_limiting": false,
    "enable_fallback": true,
    "enable_data_fusion": true,
    "enable_query_enhancement": true,
    "log_level": "DEBUG",
    "metrics_enabled": true
}
```

### 8.2 Production Configuration

```json
{
    "fred_api_key": "${FRED_API_KEY}",
    "newsapi_api_key": "${NEWSAPI_API_KEY}",
    "census_api_key": "${CENSUS_API_KEY}",
    "cache_ttl": 600,
    "default_timeout": 30,
    "max_retries": 5,
    "enable_rate_limiting": true,
    "enable_fallback": true,
    "enable_data_fusion": true,
    "enable_query_enhancement": true,
    "enable_intelligent_cache": true,
    "log_level": "INFO",
    "metrics_enabled": true,
    "cache_backend": "redis",
    "redis_url": "redis://redis:6379/0"
}
```

### 8.3 High-Volume Configuration

```json
{
    "fred_api_key": "${FRED_API_KEY}",
    "cache_ttl": 3600,
    "default_timeout": 15,
    "max_retries": 3,
    "enable_rate_limiting": true,
    "enable_fallback": true,
    "enable_data_fusion": false,
    "enable_query_enhancement": false,
    "enable_intelligent_cache": true,
    "log_level": "WARNING",
    "metrics_enabled": true,
    "rate_limit_config": {
        "fred": {
            "tokens_per_second": 1.5,
            "max_tokens": 5
        }
    }
}
```

### 8.4 Minimal Configuration

```json
{
    "fred_api_key": "YOUR_FRED_KEY"
}
```

All other parameters use defaults.

---

## 9. Validation and Testing

### 9.1 Configuration Validation

```python
from aiecs.tools.apisource.tool import Config

# Validate configuration
try:
    config = Config(
        fred_api_key='YOUR_KEY',
        cache_ttl=300,
        max_retries=3
    )
    print("Configuration valid!")
except ValueError as e:
    print(f"Configuration error: {e}")
```

### 9.2 Testing Configuration

```python
from aiecs.tools.apisource import APISourceTool

# Create tool with configuration
tool = APISourceTool(config)

# Test provider connectivity
providers = tool.list_providers()
for provider in providers:
    print(f"Provider: {provider['name']}")
    print(f"Health: {provider['health']['status']}")
    print(f"Score: {provider['health']['score']}\n")

# Test a simple query
try:
    result = tool.query(
        provider='fred',
        operation='get_series_info',
        params={'series_id': 'GDP'}
    )
    print("Configuration working correctly!")
except Exception as e:
    print(f"Configuration issue: {e}")
```

### 9.3 Configuration Best Practices

1. **Use Environment Variables for Secrets**:
```python
import os
config = {
    'fred_api_key': os.getenv('FRED_API_KEY'),
    'newsapi_api_key': os.getenv('NEWSAPI_KEY')
}
```

2. **Validate Before Deployment**:
```python
def validate_config(config):
    required_keys = ['fred_api_key']
    for key in required_keys:
        if not config.get(key):
            raise ValueError(f"Missing required config: {key}")
    return True
```

3. **Use Different Configs for Different Environments**:
```python
import os

env = os.getenv('ENVIRONMENT', 'development')
config_file = f'config.{env}.json'

with open(config_file) as f:
    config = json.load(f)
```

4. **Monitor Configuration Impact**:
```python
# Check metrics after configuration changes
metrics = tool.get_metrics()
print(f"Success rate: {metrics['overall']['success_rate']}")
print(f"Avg response time: {metrics['overall']['avg_response_time']}")
```

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-18  
**Maintainer**: AIECS Tools Team
