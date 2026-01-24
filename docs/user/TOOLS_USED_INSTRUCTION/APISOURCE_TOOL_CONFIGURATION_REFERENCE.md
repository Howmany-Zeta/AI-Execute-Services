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

### 3.9 CoinGecko API

**No API Key Required**:
```python
# CoinGecko API is free for basic usage
tool = APISourceTool()  # No key needed for free tier
```

**Rate Limits**:
- Free tier: 10-50 calls/minute (varies by endpoint)
- Pro tier available with API key for higher limits

### 3.10 OpenWeatherMap API

**Obtaining the Key**:
1. Visit https://openweathermap.org/api
2. Sign up for a free account
3. Generate an API key from your account dashboard

**Configuration**:
```python
tool = APISourceTool({'openweathermap_api_key': 'YOUR_OPENWEATHERMAP_KEY'})
```

**Rate Limits**:
- Free tier: 60 calls/minute, 1,000,000 calls/month
- Various paid tiers available

### 3.11 Wikipedia API

**No API Key Required**:
```python
# Wikipedia API is completely free and open
tool = APISourceTool()  # No key needed for Wikipedia
```

**Configuration with User-Agent (REQUIRED)**:
```python
config = {
    'wikipedia_config': {
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)'
    }
}
tool = APISourceTool(config)
```

**Rate Limits**:
- Maximum: 200 requests per second
- Recommended: 10 requests per second (default in configuration)
- Be respectful of the free service

**API Rules** (https://www.mediawiki.org/wiki/API:Etiquette):
1. **User-Agent Header REQUIRED**: Must include a unique User-Agent header with:
   - Application name and version
   - Contact URL or email address
   - Format: `"AppName/Version (URL; contact@email.com)"`
2. **Rate Limiting**: Limit to 200 requests/second maximum
3. **Caching**: Cache responses when possible to reduce load

**API Documentation**:
- MediaWiki Action API: https://www.mediawiki.org/wiki/API:Main_page
- REST API: https://en.wikipedia.org/api/rest_v1/
- API Etiquette: https://www.mediawiki.org/wiki/API:Etiquette

### 3.12 GitHub API

**API Key Recommended**:
```python
config = {
    'github_api_key': 'YOUR_GITHUB_TOKEN'
}
tool = APISourceTool(config)
```

**Environment Variable**:
```bash
export GITHUB_API_KEY="your_github_personal_access_token"
```

**Rate Limits**:
- **Authenticated**: 5,000 requests per hour
- **Unauthenticated**: 60 requests per hour
- Strongly recommended to use authentication for higher limits

**Obtaining an API Key**:
1. Visit https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Select scopes based on your needs:
   - `public_repo` - Access public repositories
   - `repo` - Full control of private repositories (if needed)
   - `user` - Read user profile data
4. Generate and copy the token

**API Documentation**:
- REST API: https://docs.github.com/en/rest
- Authentication: https://docs.github.com/en/rest/authentication
- Rate Limiting: https://docs.github.com/en/rest/rate-limit

### 3.13 arXiv API

**No API Key Required**:
```python
# arXiv API is completely free and open
tool = APISourceTool()  # No key needed for arXiv
```

**Configuration (Optional)**:
```python
config = {
    'arxiv_config': {
        'timeout': 30,
        'rate_limit': 0.33,  # ~3 second delays between requests (1/3 req/s)
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)'
    }
}
tool = APISourceTool(config)
```

**Important API Rules**:
1. **Rate Limiting**: Be respectful - implement 3 second delays between requests
2. **Max Results**: Limited to 30,000 results in slices of at most 2,000 at a time
3. **Caching**: Cache responses when possible to reduce server load
4. **User-Agent**: Set a descriptive User-Agent header

**API Documentation**:
- API User Manual: https://info.arxiv.org/help/api/user-manual.html
- API Basics: https://info.arxiv.org/help/api/basics.html
- arXiv Categories: https://arxiv.org/category_taxonomy

### 3.14 PubMed/NCBI E-utilities API

**API Key Optional but Recommended**:
```python
# Works without API key (3 requests/second limit)
tool = APISourceTool()

# With API key (10 requests/second limit)
config = {
    'pubmed_api_key': 'YOUR_PUBMED_API_KEY'
}
tool = APISourceTool(config)
```

**Environment Variable**:
```bash
export PUBMED_API_KEY="your_ncbi_api_key"
```

**Configuration (Optional)**:
```python
config = {
    'pubmed_config': {
        'api_key': 'YOUR_API_KEY',  # Optional but recommended
        'timeout': 30,
        'rate_limit': 3,  # 3 req/s without key, 10 with key
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)'
    }
}
tool = APISourceTool(config)
```

**Rate Limits**:
- **Without API key**: 3 requests per second
- **With API key**: 10 requests per second
- API key strongly recommended for better service

**Obtaining an API Key**:
1. Visit https://www.ncbi.nlm.nih.gov/account/
2. Register for a free NCBI account
3. Go to Settings → API Key Management
4. Generate a new API key

**Important API Rules**:
1. **Rate Limiting**: Max 3 requests/second without API key, 10 with API key
2. **User-Agent**: Set a descriptive User-Agent header with email
3. **Caching**: Cache responses when possible to reduce server load
4. **API Key**: Recommended for higher rate limits and better service

**API Documentation**:
- E-utilities Quick Start: https://www.ncbi.nlm.nih.gov/books/NBK25500/
- E-utilities API Guide: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- PubMed Help: https://pubmed.ncbi.nlm.nih.gov/help/

**Supported Operations**:
- `search_papers`: Search for papers by query string
- `get_paper_by_id`: Get paper metadata by PubMed ID (PMID)
- `search_by_author`: Search for papers by author name
- `get_paper_details`: Get detailed paper information including abstract and citations

### 3.15 CrossRef API

**No API Key Required**:
```python
# CrossRef API is completely free and open
tool = APISourceTool()  # No key needed for CrossRef
```

**Configuration (Optional)**:
```python
config = {
    'crossref_config': {
        'mailto': 'your-email@example.com',  # For polite pool access (better rate limits)
        'timeout': 30,
        'rate_limit': 10,
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; your-email@example.com)'
    }
}
tool = APISourceTool(config)
```

**Environment Variable**:
```bash
export CROSSREF_MAILTO="your-email@example.com"
```

**Important API Rules**:
1. **Rate Limiting**: Use polite pool (include mailto parameter) for better rate limits
2. **User-Agent**: Set a descriptive User-Agent header
3. **Caching**: Cache responses when possible to reduce server load
4. **Attribution**: Acknowledge CrossRef when using the data

**API Documentation**:
- REST API Documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- API Etiquette: https://github.com/CrossRef/rest-api-doc#etiquette
- Metadata Plus: https://www.crossref.org/services/metadata-delivery/

**Supported Operations**:
- `get_work_by_doi`: Get metadata for a work by its DOI
- `search_works`: Search for works by query string
- `get_journal_works`: Get works published in a specific journal by ISSN
- `search_funders`: Search for funders in the Open Funder Registry
- `get_funder_works`: Get works associated with a specific funder

### 3.16 Semantic Scholar API

**No API Key Required**:
```python
# Semantic Scholar API is completely free and open
tool = APISourceTool()  # No key needed for Semantic Scholar
```

**Configuration (Optional)**:
```python
config = {
    'semanticscholar_config': {
        'timeout': 30,
        'rate_limit': 1,  # Requests per second (recommended for sustained use)
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; your-email@example.com)'
    }
}
tool = APISourceTool(config)
```

**Environment Variables**:
```bash
export SEMANTICSCHOLAR_TIMEOUT=30
export SEMANTICSCHOLAR_RATE_LIMIT=1
export SEMANTICSCHOLAR_MAX_BURST=5
```

**Rate Limits**:
- Free tier: 1 request per second recommended (100 requests per 5 minutes)
- Higher limits available upon request

**Important API Rules**:
1. **Rate Limiting**: Recommended 1 request per second for sustained use
2. **Max Results**: Limited to 100 results per request for search, use pagination for more
3. **Caching**: Cache responses when possible to reduce server load
4. **User-Agent**: Set a descriptive User-Agent header

**API Documentation**:
- API Documentation: https://api.semanticscholar.org/api-docs/
- Academic Graph API: https://www.semanticscholar.org/product/api
- API Tutorial: https://www.semanticscholar.org/product/api/tutorial

**Supported Operations**:
- `search_papers`: Search for papers by query string
- `get_paper`: Get paper details by ID (S2 ID, DOI, arXiv ID, etc.)
- `get_paper_authors`: Get authors of a specific paper
- `get_paper_citations`: Get papers that cite this paper
- `get_paper_references`: Get papers referenced by this paper
- `get_author`: Get author details by ID
- `get_author_papers`: Get papers by a specific author

### 3.17 CORE API Key

**Obtaining the Key**:
1. Visit https://core.ac.uk/services/api
2. Register for a free account
3. Request an API key from your account dashboard

**Configuration**:
```python
# Method 1: Direct configuration
tool = APISourceTool({'core_api_key': 'YOUR_CORE_KEY'})

# Method 2: Environment variable
export CORE_API_KEY="YOUR_CORE_KEY"

# Method 3: Configuration file
{
    "core_api_key": "YOUR_CORE_KEY"
}
```

**Rate Limits**:
- Free tier: Reasonable usage with rate limiting
- Contact CORE for higher limits if needed

**Features**:
- Access to millions of open access research papers
- Search by query, DOI, or title
- Full metadata including authors, abstract, citations
- Support for pagination

### 3.18 USPTO API Key

**Obtaining the Key**:
1. Visit https://developer.uspto.gov/
2. Register for a free developer account
3. Request an API key from your account dashboard

**Configuration**:
```python
# Method 1: Direct configuration
tool = APISourceTool({'uspto_api_key': 'YOUR_USPTO_KEY'})

# Method 2: Environment variable
export USPTO_API_KEY="YOUR_USPTO_KEY"

# Method 3: Configuration file
{
    "uspto_api_key": "YOUR_USPTO_KEY"
}
```

**Rate Limits**:
- Free tier: Reasonable usage with rate limiting
- Contact USPTO for higher limits if needed

**Features**:
- Search US patents by query, inventor, or assignee
- Get detailed patent information by patent number
- Access to comprehensive US patent database
- Full metadata including inventors, assignees, classifications, citations

### 3.19 SEC EDGAR API

**No API Key Required**:
```python
# SEC EDGAR API is publicly accessible
# User-Agent header is REQUIRED
config = {
    'secedgar_config': {
        'user_agent': 'YourCompanyName contact@example.com'
    }
}
tool = APISourceTool(config)
```

**Environment Variable**:
```bash
export SECEDGAR_USER_AGENT="YourCompanyName contact@example.com"
```

**Configuration with User-Agent (REQUIRED)**:
```python
config = {
    'secedgar_config': {
        'user_agent': 'AIECS-APISource contact@example.com',
        'timeout': 30,
        'rate_limit': 10,
        'max_burst': 20
    }
}
tool = APISourceTool(config)
```

**Rate Limits**:
- Maximum: 10 requests per second
- SEC may block access if rules are not followed
- Be respectful of the free service

**API Rules** (https://www.sec.gov/os/accessing-edgar-data):
1. **User-Agent Header REQUIRED**: Must include:
   - Company or individual name
   - Contact email address
   - Format: `"CompanyName contact@email.com"`
2. **Rate Limiting**: Limit to 10 requests per second maximum
3. **Caching**: Cache responses when possible to reduce load
4. **Fair Access**: SEC monitors usage and may block non-compliant access

**API Documentation**:
- API Overview: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Accessing EDGAR Data: https://www.sec.gov/os/accessing-edgar-data
- Data Sets: https://www.sec.gov/data-research/sec-markets-data

**Features**:
- Company submissions and filing history
- XBRL financial data and concepts
- Company facts across all filings
- No API key required - completely free

**Supported Operations**:
- `get_company_submissions` - Get company filing history by CIK
- `get_company_concept` - Get XBRL concept data for specific metrics
- `get_company_facts` - Get all XBRL facts for a company

**Example CIKs**:
- Apple Inc.: 0000320193
- Tesla Inc.: 0001318605
- Microsoft Corp.: 0000789019

### 3.20 Stack Exchange API

**API Key Optional (Recommended)**:
```python
# Stack Exchange API works without key but has lower rate limits
# API key strongly recommended for production use
config = {
    'stackexchange_config': {
        'api_key': 'YOUR_STACKEXCHANGE_API_KEY'
    }
}
tool = APISourceTool(config)
```

**Environment Variable**:
```bash
export STACKEXCHANGE_API_KEY="your_api_key_here"
```

**Get Your API Key**:
1. Visit https://stackapps.com/apps/oauth/register
2. Register your application
3. Copy your API key

**Configuration**:
```python
config = {
    'stackexchange_config': {
        'api_key': 'YOUR_API_KEY',  # Optional but recommended
        'timeout': 30,
        'rate_limit': 10,
        'max_burst': 20
    }
}
tool = APISourceTool(config)
```

**Rate Limits**:
- Without API key: 300 requests per day
- With API key: 10,000 requests per day
- Respect the backoff field in API responses

**API Rules** (https://api.stackexchange.com/docs/throttle):
1. **API Key Recommended**: Increases daily quota from 300 to 10,000 requests
2. **Backoff**: Respect the backoff field in responses when present
3. **Compression**: API returns gzip compressed responses by default
4. **Attribution**: Required when displaying Stack Exchange content
5. **Fair Use**: Follow the API terms of service

**API Documentation**:
- API Documentation: https://api.stackexchange.com/docs
- Authentication: https://api.stackexchange.com/docs/authentication
- Throttling: https://api.stackexchange.com/docs/throttle

**Features**:
- Search questions across Stack Exchange network
- Get detailed question and answer data
- Search for users and their profiles
- Browse tags and their statistics
- Access all Stack Exchange sites (Stack Overflow, Server Fault, Super User, etc.)
- Rich metadata including votes, views, acceptance status, and bounties

**Supported Operations**:
- `search_questions` - Search for questions by query and tags
- `get_question` - Get detailed information about a specific question
- `get_answers` - Get answers for a specific question
- `search_users` - Search for users by name
- `get_tags` - Get tags and their statistics
- `get_sites` - Get all sites in the Stack Exchange network

**Popular Sites**:
- Stack Overflow: `stackoverflow`
- Server Fault: `serverfault`
- Super User: `superuser`
- Ask Ubuntu: `askubuntu`
- Mathematics: `math`

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

### 6.9 CoinGecko Provider

```python
config = {
    'coingecko_config': {
        'base_url': 'https://api.coingecko.com/api/v3',
        'timeout': 30,
        'rate_limit': 10,  # Requests per second (free tier)
        'max_burst': 20    # Maximum burst size
    }
}
```

**Note**: CoinGecko free tier does not require an API key. For higher rate limits and additional features, consider the Pro API.

### 6.10 OpenWeatherMap Provider

```python
config = {
    'openweathermap_api_key': 'YOUR_KEY',
    'openweathermap_config': {
        'base_url': 'https://api.openweathermap.org/data/2.5',
        'geo_url': 'https://api.openweathermap.org/geo/1.0',
        'timeout': 30,
        'rate_limit': 10,  # Requests per second
        'max_burst': 20    # Maximum burst size
    }
}
```

**Obtaining the Key**:
1. Visit https://openweathermap.org/api
2. Sign up for a free account
3. Generate an API key from your account dashboard

### 6.11 Wikipedia Provider

```python
config = {
    'wikipedia_config': {
        'base_url': 'https://en.wikipedia.org/w/api.php',
        'rest_base_url': 'https://en.wikipedia.org/api/rest_v1',
        'timeout': 30,
        'rate_limit': 10,  # Requests per second (max 200 allowed)
        'max_burst': 20,   # Maximum burst size
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)'  # REQUIRED
    }
}
```

**Features**:
- Article search by title or content
- Page summaries and extracts
- Full page content retrieval
- Random article discovery
- Page metadata and information

**Important Configuration Notes**:
- **No API Key Required**: Wikipedia API is completely free and open
- **User-Agent REQUIRED**: Must set a unique User-Agent with contact information
- **Rate Limit**: Maximum 200 req/s allowed, default config uses 10 req/s
- **API Etiquette**: Follow https://www.mediawiki.org/wiki/API:Etiquette

### 6.12 GitHub Provider

```python
config = {
    'github_api_key': 'YOUR_GITHUB_TOKEN',  # Recommended for higher rate limits
    'github_config': {
        'base_url': 'https://api.github.com',
        'timeout': 30,
        'rate_limit': 10,  # Requests per second
        'max_burst': 20,   # Maximum burst size
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs)'
    }
}
```

**Features**:
- Repository information and statistics
- Search repositories, users, and code
- User profiles and activity
- Repository issues and pull requests
- Organization data

**Supported Operations**:
- `get_repository` - Get detailed repository information
- `search_repositories` - Search for repositories
- `get_user` - Get user profile information
- `search_users` - Search for users
- `get_repository_issues` - Get repository issues
- `get_repository_pulls` - Get repository pull requests
- `search_code` - Search for code across repositories

**Important Configuration Notes**:
- **API Key Recommended**: Use a Personal Access Token for 5,000 req/hour (vs 60 unauthenticated)
- **Rate Limits**: Authenticated: 5,000/hour, Unauthenticated: 60/hour
- **Token Scopes**: Use minimal scopes needed (e.g., `public_repo` for public data)
- **API Version**: Uses GitHub REST API v3 with `application/vnd.github+json` accept header

**Obtaining the Key**:
1. Visit https://github.com/settings/tokens
2. Generate new token (classic)
3. Select appropriate scopes
4. Copy and store the token securely

### 6.13 arXiv Provider

```python
config = {
    'arxiv_config': {
        'base_url': 'http://export.arxiv.org/api/query',
        'timeout': 30,
        'rate_limit': 0.33,  # Requests per second (~3 second delays between requests)
        'max_burst': 2,      # Maximum burst size
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)'
    }
}
```

**Features**:
- Search papers by query (all fields)
- Get paper by arXiv ID
- Search by author name
- Search by category (e.g., cs.AI, math.CO)
- Pagination support
- Full metadata including authors, abstract, categories, PDF links

**Important Configuration Notes**:
- **No API Key Required**: arXiv API is completely free and open
- **Rate Limit**: Be respectful - implement 3 second delays between requests
- **Max Results**: Limited to 30,000 results in slices of at most 2,000 at a time
- **Caching**: Strongly recommended to cache responses to reduce server load
- **API Etiquette**: Follow https://info.arxiv.org/help/api/user-manual.html

**Obtaining the Key**:
- No API key required - completely free and open access

**API Documentation**:
- API User Manual: https://info.arxiv.org/help/api/user-manual.html
- API Basics: https://info.arxiv.org/help/api/basics.html
- Category Taxonomy: https://arxiv.org/category_taxonomy

### 6.14 PubMed Provider

```python
config = {
    'pubmed_api_key': 'YOUR_NCBI_API_KEY',  # Optional but recommended
    'pubmed_config': {
        'base_url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils',
        'timeout': 30,
        'rate_limit': 3,     # Requests per second (3 without key, 10 with key)
        'max_burst': 5,      # Maximum burst size
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)'
    }
}
```

**Features**:
- Search biomedical and life sciences literature
- Get paper metadata by PubMed ID (PMID)
- Search by author name
- Get detailed paper information including abstracts
- Access to 35+ million citations from MEDLINE, PubMed, and other databases
- Full metadata including authors, journal, DOI, publication date

**Supported Operations**:
- `search_papers` - Search for papers by query string
- `get_paper_by_id` - Get paper metadata by PMID
- `search_by_author` - Search for papers by author name
- `get_paper_details` - Get detailed paper information including abstract

**Important Configuration Notes**:
- **API Key Optional but Recommended**: Increases rate limit from 3 to 10 requests/second
- **Rate Limits**: 3 req/s without API key, 10 req/s with API key
- **User-Agent**: Should include contact email for NCBI to reach you if needed
- **Caching**: Strongly recommended to cache responses to reduce server load
- **API Etiquette**: Follow NCBI E-utilities guidelines

**Obtaining the Key**:
1. Visit https://www.ncbi.nlm.nih.gov/account/
2. Register for a free NCBI account
3. Go to Settings → API Key Management
4. Generate a new API key

**API Documentation**:
- E-utilities Quick Start: https://www.ncbi.nlm.nih.gov/books/NBK25500/
- E-utilities API Guide: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- PubMed Help: https://pubmed.ncbi.nlm.nih.gov/help/

### 6.15 CrossRef Provider

```python
config = {
    'crossref_config': {
        'base_url': 'https://api.crossref.org',
        'mailto': 'your-email@example.com',  # For polite pool access
        'timeout': 30,
        'rate_limit': 10,    # Requests per second
        'max_burst': 20,     # Maximum burst size
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; your-email@example.com)'
    }
}
```

**Features**:
- Get work metadata by DOI
- Search for scholarly works
- Get works from specific journals by ISSN
- Search for funders in Open Funder Registry
- Get works funded by specific funders
- Access to extensive scholarly metadata including citations, references, authors, affiliations

**Supported Operations**:
- `get_work_by_doi` - Get metadata for a work by its DOI
- `search_works` - Search for works by query string with pagination and sorting
- `get_journal_works` - Get works published in a specific journal by ISSN
- `search_funders` - Search for funders in the Open Funder Registry
- `get_funder_works` - Get works associated with a specific funder

**Important Configuration Notes**:
- **No API Key Required**: CrossRef API is completely free and open
- **Polite Pool**: Provide an email address (mailto parameter) for better rate limits
- **User-Agent**: Set a descriptive User-Agent header with contact information
- **Caching**: Strongly recommended to cache responses to reduce server load
- **Attribution**: Acknowledge CrossRef when using the data in publications

**Obtaining Access**:
- No API key required - completely free and open access
- Optional: Register email for polite pool access (better rate limits)

**API Documentation**:
- REST API Documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- API Etiquette: https://github.com/CrossRef/rest-api-doc#etiquette
- Metadata Plus: https://www.crossref.org/services/metadata-delivery/

### 6.16 Semantic Scholar Provider

```python
config = {
    'semanticscholar_config': {
        'base_url': 'https://api.semanticscholar.org/graph/v1',
        'timeout': 30,
        'rate_limit': 1,     # Requests per second (recommended for sustained use)
        'max_burst': 5,      # Maximum burst size
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; your-email@example.com)'
    }
}
```

**Features**:
- Search for academic papers by query
- Get paper metadata by ID (S2 ID, DOI, arXiv ID, etc.)
- Get paper authors, citations, and references
- Get author information and publications
- Access to extensive academic paper database with citation data
- Support for multiple paper ID formats (S2 ID, DOI, arXiv ID, PubMed ID, etc.)

**Supported Operations**:
- `search_papers` - Search for papers by query string
- `get_paper` - Get paper details by ID (S2 ID, DOI, arXiv ID, etc.)
- `get_paper_authors` - Get authors of a specific paper
- `get_paper_citations` - Get papers that cite this paper
- `get_paper_references` - Get papers referenced by this paper
- `get_author` - Get author details by ID
- `get_author_papers` - Get papers by a specific author

**Important Configuration Notes**:
- **No API Key Required**: Semantic Scholar API is completely free and open
- **Rate Limit**: Recommended 1 request per second for sustained use (100 requests per 5 minutes)
- **Max Results**: Limited to 100 results per request for search, use pagination for more
- **User-Agent**: Set a descriptive User-Agent header with contact information
- **Caching**: Strongly recommended to cache responses to reduce server load
- **Paper IDs**: Supports multiple ID formats (S2 ID, DOI, arXiv ID, PubMed ID, etc.)

**Obtaining Access**:
- No API key required - completely free and open access
- Optional: Contact Semantic Scholar for higher rate limits if needed

**API Documentation**:
- API Documentation: https://api.semanticscholar.org/api-docs/
- Academic Graph API: https://www.semanticscholar.org/product/api
- API Tutorial: https://www.semanticscholar.org/product/api/tutorial

### 6.17 CORE Provider

```python
config = {
    'core_api_key': 'YOUR_CORE_API_KEY',  # Required
    'core_config': {
        'base_url': 'https://api.core.ac.uk/v3',
        'timeout': 30,
        'rate_limit': 10,    # Requests per second
        'max_burst': 20,     # Maximum burst size
    }
}
```

**Features**:
- Search for open access research papers
- Get work metadata by CORE ID
- Search by DOI
- Search by title
- Access to millions of open access research papers
- Full metadata including authors, abstract, publication date, citations

**Supported Operations**:
- `search_works` - Search for works by query string
- `get_work` - Get work details by CORE ID
- `search_by_doi` - Search for works by DOI
- `search_by_title` - Search for works by title

**Important Configuration Notes**:
- **API Key Required**: CORE API requires an API key for access
- **Rate Limit**: Free tier allows reasonable usage with rate limiting
- **Max Results**: Limited to 100 results per request for search, use pagination for more
- **Caching**: Strongly recommended to cache responses to reduce server load
- **Attribution**: Acknowledge CORE when using the data in publications

**Obtaining the Key**:
1. Visit https://core.ac.uk/services/api
2. Register for a free account
3. Request an API key from your account dashboard

**API Documentation**:
- API Documentation: https://core.ac.uk/documentation/api
- API Services: https://core.ac.uk/services/api
- About CORE: https://core.ac.uk/about

### 6.18 USPTO Provider

```python
config = {
    'uspto_api_key': 'YOUR_USPTO_API_KEY',  # Required
    'uspto_config': {
        'base_url': 'https://developer.uspto.gov/ibd-api/v1',
        'timeout': 30,
        'rate_limit': 10,    # Requests per second
        'max_burst': 20,     # Maximum burst size
    }
}
```

**Features**:
- Search for US patents by query
- Get patent details by patent number
- Search patents by inventor name
- Search patents by assignee (company/organization)
- Access to comprehensive US patent database
- Full metadata including title, abstract, inventors, assignees, classifications, citations

**Supported Operations**:
- `search_patents` - Search for patents by query string
- `get_patent` - Get patent details by patent number/ID
- `search_by_inventor` - Search for patents by inventor name
- `search_by_assignee` - Search for patents by assignee name

**Important Configuration Notes**:
- **API Key Required**: USPTO API requires an API key for access
- **Rate Limit**: Free tier allows reasonable usage with rate limiting
- **Max Results**: Pagination supported for large result sets
- **Caching**: Strongly recommended to cache responses to reduce server load
- **Attribution**: Acknowledge USPTO when using patent data in publications

**Obtaining the Key**:
1. Visit https://developer.uspto.gov/
2. Register for a free developer account
3. Request an API key from your account dashboard

**API Documentation**:
- API Catalog: https://developer.uspto.gov/api-catalog
- Patent Search API: https://developer.uspto.gov/api-catalog/patent-search-api
- Developer Portal: https://developer.uspto.gov/

### 6.19 SEC EDGAR Provider

```python
config = {
    'secedgar_config': {
        'base_url': 'https://data.sec.gov',
        'user_agent': 'YourCompanyName contact@example.com',  # REQUIRED
        'timeout': 30,
        'rate_limit': 10,    # Requests per second (max allowed by SEC)
        'max_burst': 20,     # Maximum burst size
    }
}
```

**Features**:
- Get company submissions and filing history by CIK
- Access XBRL financial data and concepts
- Retrieve company facts across all filings
- Search company filings (10-K, 10-Q, 8-K, etc.)
- Download actual filing documents (10-K, 10-Q, 8-K full text)
- Calculate financial ratios automatically
- Get formatted financial statements
- Access insider trading data (Form 4)
- Access to comprehensive SEC filing database
- Full metadata including company info, filing dates, XBRL tags

**Supported Operations**:

*Basic Data Retrieval:*
- `get_company_submissions` - Get company filing history and submission data
- `get_company_concept` - Get XBRL concept data for specific financial metrics
- `get_company_facts` - Get all XBRL facts for a company

*Filing Document Access:*
- `search_filings` - Search for filings by CIK and form type
- `get_filings_by_type` - Get recent filings of a specific form type
- `get_filing_documents` - Get filing document URLs and metadata
- `get_filing_text` - Download full text of filing documents

*Financial Analysis:*
- `calculate_financial_ratios` - Calculate common financial ratios (P/E, ROE, ROA, etc.)
- `get_financial_statement` - Get formatted financial statements (balance sheet, income statement, cash flow)

*Corporate Governance:*
- `get_insider_transactions` - Get insider trading transactions (Form 4 filings)

**Important Configuration Notes**:
- **No API Key Required**: SEC EDGAR API is completely free and open
- **User-Agent REQUIRED**: Must include company/individual name and contact email
  - Format: `"CompanyName contact@email.com"`
  - SEC will block access if User-Agent is missing or generic
- **Rate Limit**: Maximum 10 requests per second (enforced by SEC)
- **CIK Format**: Central Index Key must be 10 digits with leading zeros (e.g., "0000320193")
- **Caching**: Strongly recommended to cache responses to reduce server load
- **Fair Access**: SEC monitors usage and may block non-compliant access

**Example Usage**:
```python
# 1. Get Apple Inc. filings (CIK: 0000320193)
result = tool.query(
    provider='secedgar',
    operation='get_company_submissions',
    params={'cik': '0000320193'}
)

# 2. Search for specific form type (10-K annual reports)
result = tool.query(
    provider='secedgar',
    operation='search_filings',
    params={
        'cik': '0000320193',
        'form_type': '10-K',
        'limit': 5
    }
)

# 3. Get Apple's Assets data from XBRL
result = tool.query(
    provider='secedgar',
    operation='get_company_concept',
    params={
        'cik': '0000320193',
        'taxonomy': 'us-gaap',
        'tag': 'Assets'
    }
)

# 4. Calculate financial ratios
result = tool.query(
    provider='secedgar',
    operation='calculate_financial_ratios',
    params={'cik': '0000320193'}
)
# Returns: current_ratio, debt_to_equity, profit_margin, ROA, ROE, etc.

# 5. Get formatted balance sheet
result = tool.query(
    provider='secedgar',
    operation='get_financial_statement',
    params={
        'cik': '0000320193',
        'statement_type': 'balance_sheet',
        'period': 'annual'
    }
)

# 6. Get insider transactions (Form 4)
result = tool.query(
    provider='secedgar',
    operation='get_insider_transactions',
    params={
        'cik': '0000320193',
        'start_date': '2024-01-01'
    }
)

# 7. Download filing document text
result = tool.query(
    provider='secedgar',
    operation='get_filing_text',
    params={
        'cik': '0000320193',
        'accession_number': '0000320193-23-000077'
    }
)
```

**Common CIKs**:
- Apple Inc.: 0000320193
- Tesla Inc.: 0001318605
- Microsoft Corp.: 0000789019
- Amazon.com Inc.: 0001018724
- Alphabet Inc.: 0001652044

**Finding CIKs**:
- Company Search: https://www.sec.gov/edgar/searchedgar/companysearch.html
- CIK Lookup Tool: https://www.sec.gov/cgi-bin/browse-edgar

**API Documentation**:
- API Overview: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Accessing EDGAR Data: https://www.sec.gov/os/accessing-edgar-data
- XBRL Data Sets: https://www.sec.gov/dera/data/financial-statement-data-sets.html
- Company Submissions: https://data.sec.gov/submissions/
- XBRL API: https://data.sec.gov/api/xbrl/

### 6.20 Stack Exchange Provider

```python
config = {
    'stackexchange_config': {
        'base_url': 'https://api.stackexchange.com/2.3',
        'api_key': 'YOUR_API_KEY',  # Optional but recommended
        'timeout': 30,
        'rate_limit': 10,    # Requests per second
        'max_burst': 20,     # Maximum burst size
    }
}
```

**Features**:
- Search questions across Stack Exchange network
- Get detailed question and answer information
- Search for users and their profiles
- Browse tags and their statistics
- Access all Stack Exchange sites
- Rich metadata including votes, views, acceptance status

**Supported Operations**:

*Question Operations:*
- `search_questions` - Search for questions by query and tags
- `get_question` - Get detailed information about a specific question
- `get_answers` - Get answers for a specific question

*User and Tag Operations:*
- `search_users` - Search for users by name
- `get_tags` - Get tags and their statistics
- `get_sites` - Get all sites in the Stack Exchange network

**Important Notes**:
- **API Key Optional**: Works without key but has much lower rate limits (300 vs 10,000 requests/day)
- **Compression**: API returns gzip compressed responses by default
- **Backoff**: Respect the backoff field in responses when present
- **Attribution**: Required when displaying Stack Exchange content

**Example Usage**:
```python
# 1. Search for Python questions on Stack Overflow
result = tool.query(
    provider='stackexchange',
    operation='search_questions',
    params={
        'site': 'stackoverflow',
        'q': 'python async',
        'tagged': 'python',
        'sort': 'votes',
        'pagesize': 10
    }
)

# 2. Get a specific question by ID
result = tool.query(
    provider='stackexchange',
    operation='get_question',
    params={
        'question_id': 11227809,
        'site': 'stackoverflow'
    }
)

# 3. Get answers for a question
result = tool.query(
    provider='stackexchange',
    operation='get_answers',
    params={
        'question_id': 11227809,
        'site': 'stackoverflow',
        'sort': 'votes',
        'pagesize': 5
    }
)

# 4. Search for users
result = tool.query(
    provider='stackexchange',
    operation='search_users',
    params={
        'site': 'stackoverflow',
        'inname': 'Jon Skeet',
        'pagesize': 10
    }
)

# 5. Get popular Python tags
result = tool.query(
    provider='stackexchange',
    operation='get_tags',
    params={
        'site': 'stackoverflow',
        'inname': 'python',
        'sort': 'popular',
        'pagesize': 20
    }
)

# 6. Get all Stack Exchange sites
result = tool.query(
    provider='stackexchange',
    operation='get_sites',
    params={'pagesize': 50}
)
```

**Popular Sites**:
- Stack Overflow: `stackoverflow`
- Server Fault: `serverfault`
- Super User: `superuser`
- Ask Ubuntu: `askubuntu`
- Mathematics: `math`
- Unix & Linux: `unix`

**API Documentation**:
- API Documentation: https://api.stackexchange.com/docs
- Authentication: https://api.stackexchange.com/docs/authentication
- Throttling: https://api.stackexchange.com/docs/throttle
- Register App: https://stackapps.com/apps/oauth/register

### 6.21 Hacker News Provider

```python
config = {
    'hackernews_config': {
        'base_url': 'http://hn.algolia.com/api/v1',
        'timeout': 30,
        'rate_limit': 10,    # Requests per second
        'max_burst': 20,     # Maximum burst size
        'user_agent': 'AIECS-APISource/2.0 (https://github.com/your-org/aiecs; your-email@example.com)'
    }
}
```

**Features**:
- Search Hacker News stories by keywords
- Search comments by keywords
- Search items sorted by date (most recent first)
- Get item details by ID (story, comment, poll, etc.)
- Get user information by username
- Full metadata including title, author, points, comments, URL
- Pagination support for large result sets

**Supported Operations**:
- `search_stories` - Search for stories by keywords (sorted by relevance)
- `search_comments` - Search for comments by keywords
- `search_by_date` - Search for items sorted by date (most recent first)
- `get_item` - Get item details by ID (story, comment, poll, etc.)
- `get_user` - Get user information by username

**Important Configuration Notes**:
- **No API Key Required**: Hacker News Algolia API is completely free and open
- **Rate Limiting**: Be respectful - implement reasonable delays between requests
- **Max Results**: Limited to 1000 results per query (pagination available)
- **User-Agent**: Set a descriptive User-Agent header for API etiquette
- **Caching**: Strongly recommended to cache responses to reduce server load

**Example Usage**:
```python
# 1. Search for Python-related stories
result = tool.query(
    provider='hackernews',
    operation='search_stories',
    params={
        'query': 'python',
        'hits_per_page': 20
    }
)

# 2. Search for stories with minimum comments
result = tool.query(
    provider='hackernews',
    operation='search_stories',
    params={
        'query': 'AI',
        'num_comments': 50,  # Minimum 50 comments
        'hits_per_page': 10
    }
)

# 3. Search comments about machine learning
result = tool.query(
    provider='hackernews',
    operation='search_comments',
    params={
        'query': 'machine learning',
        'hits_per_page': 20
    }
)

# 4. Get recent AI stories sorted by date
result = tool.query(
    provider='hackernews',
    operation='search_by_date',
    params={
        'query': 'AI',
        'tags': 'story',
        'hits_per_page': 20
    }
)

# 5. Get specific item details
result = tool.query(
    provider='hackernews',
    operation='get_item',
    params={'item_id': 1}  # The first HN story ever posted
)

# 6. Get user information
result = tool.query(
    provider='hackernews',
    operation='get_user',
    params={'username': 'pg'}  # Paul Graham
)
```

**Common Tags**:
- `story` - Filter for stories only
- `comment` - Filter for comments only
- `poll` - Filter for polls only
- `author_pg` - Filter by author (e.g., Paul Graham)
- Combine tags: `story,author_pg` - Stories by Paul Graham

**Obtaining Access**:
- No API key required - completely free and open access

**API Documentation**:
- API Documentation: https://hn.algolia.com/api
- Hacker News Official: https://news.ycombinator.com/
- Search Interface: https://hn.algolia.com/

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
export APISOURCE_OPENWEATHERMAP_API_KEY="your_openweathermap_key"
export APISOURCE_GITHUB_API_KEY="your_github_token"  # Recommended
export APISOURCE_PUBMED_API_KEY="your_ncbi_api_key"  # Optional but recommended
export CROSSREF_MAILTO="your-email@example.com"  # Optional but recommended for polite pool
export APISOURCE_CORE_API_KEY="your_core_api_key"  # Required
export APISOURCE_USPTO_API_KEY="your_uspto_api_key"  # Required
export SECEDGAR_USER_AGENT="YourCompanyName contact@example.com"  # REQUIRED for SEC EDGAR
export STACKEXCHANGE_API_KEY="your_stackexchange_api_key"  # Optional but recommended

# Provider-specific Configuration
export SEMANTICSCHOLAR_TIMEOUT=30
export SEMANTICSCHOLAR_RATE_LIMIT=1
export SEMANTICSCHOLAR_MAX_BURST=5
export CORE_TIMEOUT=30
export CORE_RATE_LIMIT=10
export CORE_MAX_BURST=20
export USPTO_TIMEOUT=30
export USPTO_RATE_LIMIT=10
export USPTO_MAX_BURST=20
export SECEDGAR_TIMEOUT=30
export SECEDGAR_RATE_LIMIT=10
export SECEDGAR_MAX_BURST=20
export STACKEXCHANGE_TIMEOUT=30
export STACKEXCHANGE_RATE_LIMIT=10
export STACKEXCHANGE_MAX_BURST=20
export HACKERNEWS_TIMEOUT=30
export HACKERNEWS_RATE_LIMIT=10
export HACKERNEWS_MAX_BURST=20
export STACKEXCHANGE_RATE_LIMIT=10
export STACKEXCHANGE_MAX_BURST=20

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
