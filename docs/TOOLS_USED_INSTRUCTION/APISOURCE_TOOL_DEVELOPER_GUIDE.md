# APISource Tool - Developer Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Advanced Usage](#advanced-usage)
5. [LangChain Integration](#langchain-integration)
6. [Best Practices](#best-practices)
7. [Common Patterns](#common-patterns)
8. [Troubleshooting](#troubleshooting)

---

## 1. Quick Start

### 5-Minute Setup

```python
from aiecs.tools.apisource import APISourceTool

# 1. Create tool instance with API keys
tool = APISourceTool({
    'fred_api_key': 'YOUR_FRED_API_KEY',
    'newsapi_api_key': 'YOUR_NEWSAPI_KEY',
    'census_api_key': 'YOUR_CENSUS_KEY'
})

# 2. Query economic data
result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={'series_id': 'GDP'},
    query_text="Get GDP data for last 5 years"
)

# 3. Access the data
print(f"Data points: {len(result['data'])}")
print(f"Quality score: {result['metadata']['quality']['score']}")
```

### What You Get

- **Automatic Parameter Enhancement**: Query text is analyzed to add missing parameters
- **Quality Metadata**: Every result includes quality scores
- **Error Handling**: Automatic retries and helpful error messages
- **Fallback Support**: Seamless failover to alternative providers

---

## 2. Installation

### Prerequisites

```bash
# Python 3.8+
python --version

# Required packages
pip install requests pydantic
```

### API Keys Setup

#### FRED (Federal Reserve Economic Data)
1. Visit https://fred.stlouisfed.org/docs/api/api_key.html
2. Register for a free API key
3. Set environment variable:
```bash
export APISOURCE_FRED_API_KEY="your_fred_api_key"
```

#### News API
1. Visit https://newsapi.org/register
2. Get your API key
3. Set environment variable:
```bash
export APISOURCE_NEWSAPI_API_KEY="your_newsapi_key"
```

#### Census Bureau
1. Visit https://api.census.gov/data/key_signup.html
2. Request an API key
3. Set environment variable:
```bash
export APISOURCE_CENSUS_API_KEY="your_census_key"
```

#### World Bank
No API key required - public access

### Configuration File

Create `apisource_config.json`:
```json
{
    "fred_api_key": "YOUR_FRED_KEY",
    "newsapi_api_key": "YOUR_NEWS_KEY",
    "census_api_key": "YOUR_CENSUS_KEY",
    "cache_ttl": 300,
    "default_timeout": 30,
    "max_retries": 3,
    "enable_fallback": true,
    "enable_data_fusion": true,
    "enable_query_enhancement": true
}
```

Load configuration:
```python
import json

with open('apisource_config.json') as f:
    config = json.load(f)

tool = APISourceTool(config)
```

---

## 3. Basic Usage

### 3.1 FRED Provider - Economic Data

#### Get Time Series Data

```python
# GDP data
result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={
        'series_id': 'GDP',
        'observation_start': '2020-01-01',
        'observation_end': '2023-12-31'
    }
)

# Access data
for obs in result['data']:
    print(f"{obs['date']}: ${obs['value']} billion")
```

#### Search for Series

```python
# Search for unemployment data
result = tool.query(
    provider='fred',
    operation='search_series',
    params={
        'search_text': 'unemployment rate',
        'limit': 10
    }
)

# List results
for series in result['data']:
    print(f"{series['id']}: {series['title']}")
```

#### Get Series Information

```python
# Get metadata about a series
result = tool.query(
    provider='fred',
    operation='get_series_info',
    params={'series_id': 'UNRATE'}
)

info = result['data']
print(f"Title: {info['title']}")
print(f"Units: {info['units']}")
print(f"Frequency: {info['frequency']}")
print(f"Last Updated: {info['last_updated']}")
```

### 3.2 World Bank Provider - Global Development

#### Get Indicator Data

```python
# GDP for multiple countries
result = tool.query(
    provider='worldbank',
    operation='get_indicator_data',
    params={
        'indicator': 'NY.GDP.MKTP.CD',  # GDP (current US$)
        'countries': ['USA', 'CHN', 'JPN', 'DEU'],
        'date_range': '2015:2023'
    }
)

# Process data
for entry in result['data']:
    print(f"{entry['country']}: ${entry['value']:,.0f}")
```

#### Search Indicators

```python
# Find population indicators
result = tool.query(
    provider='worldbank',
    operation='search_indicators',
    params={
        'search_text': 'population',
        'limit': 20
    }
)

for indicator in result['data']:
    print(f"{indicator['id']}: {indicator['name']}")
```

### 3.3 News API Provider - News Articles

#### Get Top Headlines

```python
# Business headlines
result = tool.query(
    provider='newsapi',
    operation='get_top_headlines',
    params={
        'category': 'business',
        'country': 'us',
        'page_size': 10
    }
)

for article in result['data']:
    print(f"{article['title']}")
    print(f"Source: {article['source']['name']}")
    print(f"Published: {article['publishedAt']}\n")
```

#### Search Articles

```python
# Search for AI news
result = tool.query(
    provider='newsapi',
    operation='search_articles',
    params={
        'q': 'artificial intelligence',
        'from_date': '2024-01-01',
        'sort_by': 'relevancy',
        'language': 'en',
        'page_size': 20
    }
)
```

### 3.4 Census Provider - US Demographics

#### Get Census Data

```python
# State population data
result = tool.query(
    provider='census',
    operation='get_data',
    params={
        'dataset': 'acs/acs5',
        'year': 2021,
        'variables': ['B01001_001E'],  # Total population
        'for': 'state:*'
    }
)

for row in result['data']:
    print(f"State {row['state']}: {row['B01001_001E']:,} people")
```

---

## 4. Advanced Usage

### 4.1 Query Enhancement

Let the tool automatically enhance your parameters:

```python
# Minimal parameters + natural language query
result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={'series_id': 'GDP'},
    query_text="Get GDP data for the last 5 years with quarterly frequency",
    enable_enhancement=True
)

# Tool automatically adds:
# - observation_start: calculated from "last 5 years"
# - observation_end: current date
# - frequency: 'q' (quarterly)
```

### 4.2 Multi-Provider Search

Search across multiple providers with automatic fusion:

```python
# Search for unemployment data across providers
results = tool.search(
    query="unemployment rate trends",
    providers=['fred', 'worldbank'],
    enable_fusion=True,
    fusion_strategy='best_quality',
    search_options={
        'relevance_threshold': 0.3,
        'sort_by': 'composite',
        'max_results': 10
    }
)

# Results are ranked and deduplicated
for result in results['results']:
    print(f"Source: {result['provider']}")
    print(f"Relevance: {result['relevance_score']:.2f}")
    print(f"Title: {result['title']}\n")
```

### 4.3 Fallback Strategy

Automatic failover to alternative providers:

```python
# Try FRED, fallback to World Bank if needed
result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={'series_id': 'GDP'},
    enable_fallback=True
)

# Check if fallback was used
if result['metadata'].get('fallback_used'):
    print(f"Fallback to: {result['metadata']['actual_provider']}")
```

### 4.4 Data Fusion

Combine data from multiple sources:

```python
from aiecs.tools.apisource.intelligence import DataFusionEngine

fusion = DataFusionEngine()

# Get GDP from both FRED and World Bank
fred_result = tool.query(provider='fred', operation='get_series_observations', 
                         params={'series_id': 'GDP'})
wb_result = tool.query(provider='worldbank', operation='get_indicator_data',
                       params={'indicator': 'NY.GDP.MKTP.CD', 'countries': ['USA']})

# Fuse results
fused = fusion.fuse_multi_provider_results(
    results=[fred_result, wb_result],
    fusion_strategy='best_quality'
)

print(f"Selected source: {fused['metadata']['fusion']['selected_source']}")
print(f"Quality scores: {fused['metadata']['fusion']['quality_scores']}")
```

### 4.5 Batch Queries

Execute multiple queries efficiently:

```python
# Define queries
queries = [
    {'provider': 'fred', 'operation': 'get_series_observations', 
     'params': {'series_id': 'GDP'}},
    {'provider': 'fred', 'operation': 'get_series_observations',
     'params': {'series_id': 'UNRATE'}},
    {'provider': 'fred', 'operation': 'get_series_observations',
     'params': {'series_id': 'CPIAUCSL'}}
]

# Execute in batch
results = []
for query_spec in queries:
    result = tool.query(**query_spec)
    results.append(result)

# Process results
for i, result in enumerate(results):
    print(f"Query {i+1}: {len(result['data'])} data points")
```

---

## 5. LangChain Integration

### 5.1 Basic Integration

```python
from aiecs.tools.apisource import APISourceTool
from aiecs.tools.apisource.adapters import LangChainAdapter

# Create tool
apisource_tool = APISourceTool({
    'fred_api_key': 'YOUR_KEY'
})

# Create LangChain adapter
adapter = LangChainAdapter(apisource_tool)

# Get LangChain tools
langchain_tools = adapter.get_tools()

# Use with LangChain agent
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI

llm = OpenAI(temperature=0)
agent = initialize_agent(
    langchain_tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Ask questions
response = agent.run("What is the current US unemployment rate?")
```

### 5.2 Provider-Specific Tools

```python
# Get tools for specific providers only
fred_tools = adapter.get_tools(providers=['fred'])

# Each provider operation becomes a separate tool
for tool in fred_tools:
    print(f"Tool: {tool.name}")
    print(f"Description: {tool.description}\n")
```

### 5.3 Custom Tool Configuration

```python
# Configure tool behavior
adapter = LangChainAdapter(
    apisource_tool,
    config={
        'enable_enhancement': True,
        'enable_fallback': True,
        'max_results': 10
    }
)
```

---

## 6. Best Practices

### 6.1 API Key Management

**DO**:
```python
# Use environment variables
import os
tool = APISourceTool({
    'fred_api_key': os.getenv('APISOURCE_FRED_API_KEY')
})

# Or use configuration files
import json
with open('config.json') as f:
    config = json.load(f)
tool = APISourceTool(config)
```

**DON'T**:
```python
# Don't hardcode API keys
tool = APISourceTool({
    'fred_api_key': 'abc123...'  # BAD!
})
```

### 6.2 Error Handling

```python
from aiecs.tools.apisource.exceptions import (
    APISourceError,
    APIRateLimitError,
    APIAuthenticationError
)

try:
    result = tool.query(
        provider='fred',
        operation='get_series_observations',
        params={'series_id': 'GDP'}
    )
except APIRateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after}s")
    # Implement backoff strategy
except APIAuthenticationError as e:
    print(f"Authentication failed: {e.message}")
    # Check API key
except APISourceError as e:
    print(f"Error: {e.message}")
    # Handle general errors
```

### 6.3 Performance Optimization

#### Enable Caching

```python
tool = APISourceTool({
    'cache_ttl': 600,  # Cache for 10 minutes
    'enable_intelligent_cache': True
})
```

#### Use Appropriate Timeouts

```python
tool = APISourceTool({
    'default_timeout': 30,  # 30 seconds
    'max_retries': 3
})
```

#### Limit Result Size

```python
# Request only what you need
result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={
        'series_id': 'GDP',
        'observation_start': '2023-01-01',  # Limit date range
        'limit': 100  # Limit number of results
    }
)
```

### 6.4 Data Quality Checks

```python
result = tool.query(...)

# Check quality score
quality = result['metadata']['quality']
if quality['score'] < 0.7:
    print("Warning: Low quality data")
    print(f"Completeness: {quality['completeness']}")
    print(f"Freshness: {quality['freshness']}")

# Check for missing values
data = result['data']
missing_count = sum(1 for item in data if item.get('value') is None)
if missing_count > 0:
    print(f"Warning: {missing_count} missing values")
```

---

## 7. Common Patterns

### 7.1 Economic Research Assistant

```python
class EconomicResearchAssistant:
    def __init__(self, tool):
        self.tool = tool
    
    def get_economic_indicators(self, country='US', start_date='2020-01-01'):
        """Get key economic indicators"""
        indicators = {
            'gdp': 'GDP',
            'unemployment': 'UNRATE',
            'inflation': 'CPIAUCSL',
            'interest_rate': 'DFF'
        }
        
        results = {}
        for name, series_id in indicators.items():
            result = self.tool.query(
                provider='fred',
                operation='get_series_observations',
                params={
                    'series_id': series_id,
                    'observation_start': start_date
                }
            )
            results[name] = result['data']
        
        return results
    
    def compare_countries(self, indicator, countries, years='2015:2023'):
        """Compare indicator across countries"""
        result = self.tool.query(
            provider='worldbank',
            operation='get_indicator_data',
            params={
                'indicator': indicator,
                'countries': countries,
                'date_range': years
            }
        )
        return result['data']

# Usage
assistant = EconomicResearchAssistant(tool)
indicators = assistant.get_economic_indicators()
comparison = assistant.compare_countries('NY.GDP.MKTP.CD', ['USA', 'CHN', 'JPN'])
```

### 7.2 News Aggregator

```python
class NewsAggregator:
    def __init__(self, tool):
        self.tool = tool
    
    def get_market_news(self, keywords, days=7):
        """Get recent market news"""
        from datetime import datetime, timedelta
        
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        result = self.tool.query(
            provider='newsapi',
            operation='search_articles',
            params={
                'q': keywords,
                'from_date': from_date,
                'sort_by': 'relevancy',
                'language': 'en'
            }
        )
        
        return result['data']
    
    def get_trending_topics(self, category='business'):
        """Get trending topics"""
        result = self.tool.query(
            provider='newsapi',
            operation='get_top_headlines',
            params={
                'category': category,
                'country': 'us',
                'page_size': 20
            }
        )
        
        return result['data']

# Usage
aggregator = NewsAggregator(tool)
market_news = aggregator.get_market_news('stock market')
trending = aggregator.get_trending_topics()
```

### 7.3 Multi-Source Data Aggregator

```python
def aggregate_gdp_data(tool, country_code='USA', years='2015:2023'):
    """Aggregate GDP data from multiple sources"""
    
    # Get FRED data
    fred_result = tool.query(
        provider='fred',
        operation='get_series_observations',
        params={'series_id': 'GDP'}
    )
    
    # Get World Bank data
    wb_result = tool.query(
        provider='worldbank',
        operation='get_indicator_data',
        params={
            'indicator': 'NY.GDP.MKTP.CD',
            'countries': [country_code],
            'date_range': years
        }
    )
    
    # Fuse results
    from aiecs.tools.apisource.intelligence import DataFusionEngine
    fusion = DataFusionEngine()
    
    fused = fusion.fuse_multi_provider_results(
        results=[fred_result, wb_result],
        fusion_strategy='best_quality'
    )
    
    return fused

# Usage
gdp_data = aggregate_gdp_data(tool)
```

---

## 8. Troubleshooting

### 8.1 Common Issues

#### Issue: "Provider not found"

**Cause**: Provider name is incorrect or not registered

**Solution**:
```python
# List available providers
providers = tool.list_providers()
for p in providers:
    print(f"Provider: {p['name']}")

# Use correct provider name
result = tool.query(provider='fred', ...)  # Not 'FRED' or 'Fred'
```

#### Issue: "API authentication failed"

**Cause**: Invalid or missing API key

**Solution**:
```python
# Check API key is set
import os
print(os.getenv('APISOURCE_FRED_API_KEY'))

# Verify key in configuration
tool = APISourceTool({'fred_api_key': 'YOUR_KEY'})

# Test provider
info = tool.get_provider_info('fred')
print(f"Health: {info['health']}")
```

#### Issue: "Rate limit exceeded"

**Cause**: Too many requests to API

**Solution**:
```python
# Enable caching
tool = APISourceTool({
    'cache_ttl': 600,
    'enable_intelligent_cache': True
})

# Reduce request frequency
import time
for query in queries:
    result = tool.query(**query)
    time.sleep(1)  # Wait between requests

# Check quota status
metrics = tool.get_metrics()
print(f"Request count: {metrics['overall']['total_requests']}")
```

#### Issue: "Timeout error"

**Cause**: Request took too long

**Solution**:
```python
# Increase timeout
tool = APISourceTool({
    'default_timeout': 60  # 60 seconds
})

# Reduce data range
result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={
        'series_id': 'GDP',
        'observation_start': '2023-01-01',  # Smaller range
        'limit': 100
    }
)
```

### 8.2 Debugging

#### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('aiecs.tools.apisource')
logger.setLevel(logging.DEBUG)

# Now all operations will log detailed information
result = tool.query(...)
```

#### Check Metrics

```python
# Get detailed metrics
metrics = tool.get_metrics()
print(json.dumps(metrics, indent=2))

# Get metrics report
report = tool.get_metrics_report()
print(report)
```

#### Inspect Result Metadata

```python
result = tool.query(...)

# Check execution details
metadata = result['metadata']
print(f"Provider: {metadata['provider']}")
print(f"Execution time: {metadata['execution_time_ms']}ms")
print(f"Quality score: {metadata['quality']['score']}")

# Check if enhancement was applied
if metadata.get('enhancement', {}).get('applied'):
    print("Original params:", metadata['enhancement']['original_params'])
    print("Enhanced params:", metadata['enhancement']['enhanced_params'])
```

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-18  
**Maintainer**: AIECS Tools Team
