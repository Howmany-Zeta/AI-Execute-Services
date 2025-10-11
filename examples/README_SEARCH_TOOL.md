# Search Tool Examples

This directory contains examples demonstrating the AIECS Search Tool capabilities.

## Quick Start

### 1. Setup Credentials

Create or update your `.env` file in the project root:

```bash
# Option A: API Key (Recommended)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id

# Option B: Service Account
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CSE_ID=your_custom_search_engine_id
```

### 2. Get API Credentials

**Google Custom Search API:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Create or select a project
3. Enable "Custom Search API"
4. Create an API key
5. Note down your API key

**Custom Search Engine:**
1. Go to https://programmablesearchengine.google.com/
2. Create a new search engine
3. Configure search settings (search the entire web or specific sites)
4. Note down your Search Engine ID (CSE ID)

### 3. Run Examples

```bash
# Run the comprehensive demo
python examples/search_tool_demo.py

# Or run individual examples in Python
python3 -c "
from aiecs.tools import discover_tools, get_tool
discover_tools()
tool = get_tool('search')

# Simple search
results = tool.search_web('artificial intelligence', num_results=5)
for r in results:
    print(f'{r[\"title\"]}: {r[\"link\"]}')
"
```

## Examples Overview

### search_tool_demo.py

Comprehensive demonstration of all Search Tool features:

- Basic web search
- Advanced web search with filters
- Image search
- News search
- Video search
- Paginated search (multiple pages)
- Batch search (parallel queries)
- Quota monitoring
- Credential validation
- Error handling

Run it:
```bash
python examples/search_tool_demo.py
```

## Common Use Cases

### 1. Simple Web Search

```python
from aiecs.tools import get_tool

tool = get_tool('search')
results = tool.search_web("python programming", num_results=10)
```

### 2. Search with Filters

```python
# Search for recent PDFs
results = tool.search_web(
    query="machine learning research",
    date_restrict="m6",  # Last 6 months
    file_type="pdf",
    language="en"
)
```

### 3. Image Search

```python
# Find large photos
images = tool.search_images(
    query="mountain landscape",
    image_size="large",
    image_type="photo"
)
```

### 4. News Search

```python
# Get recent news
news = tool.search_news(
    query="technology",
    date_restrict="d7",  # Last 7 days
    sort_by="date"
)
```

### 5. Batch Search

```python
import asyncio

queries = ["AI", "ML", "DL"]
results = asyncio.run(tool.search_batch(queries, num_results=5))
```

### 6. Monitor Quota

```python
status = tool.get_quota_status()
print(f"Remaining: {status['remaining_quota']}")
print(f"State: {status['circuit_breaker_state']}")
```

## API Limits

- **Free Tier**: 100 queries/day
- **Paid Tier**: Up to 10,000 queries/day  
- **Results per Query**: Maximum 10 results per request
- **Total Results**: Maximum 100 results via pagination

## Troubleshooting

### "Custom Search API has not been used"
Enable the Custom Search API in your Google Cloud Console:
https://console.developers.google.com/apis/api/customsearch.googleapis.com/overview

### "Invalid API key" or "Authentication failed"
- Check that `GOOGLE_API_KEY` is set correctly
- Verify your API key is valid and not restricted
- Ensure Custom Search API is enabled for your project

### "Quota exceeded"
- You've reached your daily quota (default: 100 queries/day)
- Wait 24 hours or upgrade to a paid plan
- Monitor usage with `tool.get_quota_status()`

### "Circuit breaker is OPEN"
- The tool detected repeated API failures
- Wait for the circuit breaker timeout (default: 60 seconds)
- The circuit will automatically try to recover

## Rate Limiting

The Search Tool implements rate limiting to protect your quota:

```python
# Default limits
SEARCH_TOOL_RATE_LIMIT_REQUESTS=100    # Max requests
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400    # Per 24 hours

# Circuit breaker
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=5   # Failures before opening
SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=60    # Seconds before retry
```

## Best Practices

1. **Use Caching**: Identical queries are cached for 1 hour by default
2. **Monitor Quota**: Check remaining quota before large operations
3. **Handle Errors**: Always wrap API calls in try/except blocks
4. **Batch Queries**: Use `search_batch()` for multiple queries
5. **Paginate Wisely**: Only request the results you need

## Additional Resources

- [Search Tool Documentation](../docs/TOOLS/TOOLS_SEARCH_TOOL.md)
- [Google Custom Search API Docs](https://developers.google.com/custom-search/v1/overview)
- [AIECS Tools Guide](../docs/TOOLS/TOOLS_BASE_TOOL.md)

## Support

For issues or questions:
- Check the [documentation](../docs/TOOLS/TOOLS_SEARCH_TOOL.md)
- Review [error messages](#troubleshooting)
- Open an issue on GitHub

