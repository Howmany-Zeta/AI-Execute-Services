# API Sources - Provider Plugins for API Source Tool

This directory contains plugin-based API data source providers for the API Source Tool.

## Architecture

The API Sources module uses a plugin architecture where each external API is implemented as a separate provider that inherits from `BaseAPIProvider`.

### Benefits

1. **Horizontal Scalability**: Add new APIs by creating a single provider file
2. **Maintainability**: Each API isolated with its own logic
3. **Auto-Discovery**: Providers are automatically registered on import
4. **Testability**: Test each provider independently
5. **Graceful Degradation**: Missing dependencies don't break the system

## Directory Structure

```
api_sources/
├── __init__.py              # Provider registry with auto-discovery
├── base_provider.py         # BaseAPIProvider abstract class
├── fred_provider.py         # Federal Reserve Economic Data
├── worldbank_provider.py    # World Bank API
├── newsapi_provider.py      # News API
├── census_provider.py       # US Census Bureau
└── README.md               # This file
```

## Current Providers

### 1. FRED Provider (`fred_provider.py`)

**Federal Reserve Economic Data API**

- Economic indicators (GDP, unemployment, inflation)
- Interest rates and monetary indicators
- Regional economic data
- Time series observations

**Operations**:
- `get_series`: Get time series data
- `search_series`: Search for data series
- `get_series_observations`: Get detailed observations
- `get_series_info`: Get series metadata
- `get_categories`: List data categories
- `get_releases`: List data releases

**API Key**: Set `FRED_API_KEY` environment variable

**Example**:
```python
from aiecs.tools import get_tool
tool = get_tool('apisource')
result = tool.query(
    provider='fred',
    operation='get_series',
    params={'series_id': 'GDP', 'limit': 10}
)
```

### 2. World Bank Provider (`worldbank_provider.py`)

**World Bank Development Indicators API**

- Economic indicators (GDP, trade, inflation)
- Social indicators (education, health, population)
- Environmental data
- Country-specific statistics

**Operations**:
- `get_indicator`: Get indicator data for a country
- `search_indicators`: Search available indicators
- `get_country_data`: Get country information
- `list_countries`: List all countries
- `list_indicators`: List all indicators

**API Key**: Not required (public API)

**Example**:
```python
result = tool.query(
    provider='worldbank',
    operation='get_indicator',
    params={
        'country_code': 'USA',
        'indicator_code': 'NY.GDP.MKTP.CD'
    }
)
```

### 3. News API Provider (`newsapi_provider.py`)

**News API for Articles and Headlines**

- Top headlines from various sources
- Article search by keywords
- News sources listing
- Multi-language support

**Operations**:
- `get_top_headlines`: Get current top headlines
- `search_everything`: Search all articles
- `get_sources`: List news sources

**API Key**: Set `NEWSAPI_API_KEY` environment variable  
Get your key at: https://newsapi.org

**Example**:
```python
result = tool.query(
    provider='newsapi',
    operation='get_top_headlines',
    params={
        'q': 'technology',
        'country': 'us',
        'page_size': 10
    }
)
```

### 4. Census Provider (`census_provider.py`)

**US Census Bureau API**

- American Community Survey (ACS) data
- Decennial Census
- Economic indicators
- Population estimates
- Geographic data

**Operations**:
- `get_acs_data`: Get ACS survey data
- `get_population`: Get population estimates
- `get_economic_data`: Get economic census data
- `list_datasets`: List available datasets
- `list_variables`: List variables for a dataset

**API Key**: Set `CENSUS_API_KEY` environment variable (optional for some datasets)

**Example**:
```python
result = tool.query(
    provider='census',
    operation='get_acs_data',
    params={
        'variables': ['B01001_001E'],  # Total population
        'geography': 'state:*',
        'year': '2021'
    }
)
```

## Adding a New Provider

### Step 1: Create Provider File

Create a new file `{name}_provider.py`:

```python
from typing import Any, Dict, List, Optional, Tuple
from aiecs.tools.task_tools.api_sources import register_provider
from aiecs.tools.task_tools.api_sources.base_provider import BaseAPIProvider

class MyAPIProvider(BaseAPIProvider):
    """Description of the API provider"""
    
    @property
    def name(self) -> str:
        return "myapi"
    
    @property
    def description(self) -> str:
        return "My API provider description"
    
    @property
    def supported_operations(self) -> List[str]:
        return ['get_data', 'search']
    
    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        # Validate parameters
        if operation == 'get_data' and 'id' not in params:
            return False, "Missing required parameter: id"
        return True, None
    
    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implement API calls
        api_key = self._get_api_key('MYAPI_API_KEY')
        # ... make request ...
        return self._format_response(operation, data, source)

# Register the provider
register_provider(MyAPIProvider)
```

### Step 2: Test the Provider

The provider will be automatically discovered and available immediately:

```python
from aiecs.tools import get_tool
tool = get_tool('apisource')

# List providers (should include your new one)
providers = tool.list_providers()

# Query your provider
result = tool.query(
    provider='myapi',
    operation='get_data',
    params={'id': '123'}
)
```

### Step 3: No Configuration Needed!

- The provider auto-registers on import
- The main tool auto-discovers it
- No need to modify any other files

## Base Provider Features

All providers inherit common functionality from `BaseAPIProvider`:

### Rate Limiting
- Token bucket algorithm
- Configurable tokens per second
- Automatic request throttling

### Error Handling
- Structured exception handling
- Request statistics tracking
- Detailed logging

### Response Formatting
- Standardized response structure
- Metadata inclusion
- Source tracking

### API Key Management
- Environment variable support
- Config-based keys
- Graceful degradation

## Best Practices

1. **Error Handling**: Always catch and log API-specific errors
2. **Rate Limiting**: Respect API rate limits in validate_params
3. **Documentation**: Provide clear docstrings for all operations
4. **Testing**: Test with and without API keys
5. **Dependencies**: Make HTTP client imports optional with graceful fallback

## Troubleshooting

### Provider Not Showing Up

1. Ensure file ends with `_provider.py`
2. Check that `register_provider()` is called
3. Verify no import errors in the provider file

### API Key Not Found

1. Set environment variable: `export {PROVIDER}_API_KEY=your_key`
2. Or pass in config: `{'api_key': 'your_key'}`
3. Check provider's `_get_api_key()` implementation

### Rate Limit Exceeded

1. Reduce request frequency
2. Increase `max_burst` in provider config
3. Add delays between requests

## Resources

- [FRED API Docs](https://fred.stlouisfed.org/docs/api/fred/)
- [World Bank API Docs](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)
- [News API Docs](https://newsapi.org/docs)
- [Census API Docs](https://www.census.gov/data/developers/guidance.html)

---

For questions or contributions, refer to the main aiecs.tools documentation.

