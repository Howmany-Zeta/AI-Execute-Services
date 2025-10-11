# Search Tool Configuration Guide

## Overview

The Search Tool provides comprehensive web search capabilities using Google Custom Search API with advanced features including multiple search types (web, image, news, video), rate limiting, circuit breaker protection, intelligent caching, and comprehensive error handling. The tool can be configured via environment variables using the `SEARCH_TOOL_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Search Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
SEARCH_TOOL_GOOGLE_API_KEY=your_google_api_key_here
SEARCH_TOOL_GOOGLE_CSE_ID=your_custom_search_engine_id_here
SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
SEARCH_TOOL_CACHE_TTL=3600
SEARCH_TOOL_RATE_LIMIT_REQUESTS=100
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=5
SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=60
SEARCH_TOOL_RETRY_ATTEMPTS=3
SEARCH_TOOL_RETRY_BACKOFF=2.0
SEARCH_TOOL_TIMEOUT=30
SEARCH_TOOL_USER_AGENT=MySearchBot/1.0
SEARCH_TOOL_ALLOWED_SEARCH_TYPES=["web","image","news","video"]
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.search_tool import SearchTool

# The tool will automatically use the environment variables
search_tool = SearchTool()
```

### Multiple Environment Files

You can use different `.env` files for different environments:

```python
import os
from dotenv import load_dotenv

# Load environment-specific configuration
env = os.getenv('APP_ENV', 'development')

if env == 'production':
    load_dotenv('.env.production')
elif env == 'staging':
    load_dotenv('.env.staging')
else:
    load_dotenv('.env.development')

from aiecs.tools.task_tools.search_tool import SearchTool
search_tool = SearchTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for reliability and performance
SEARCH_TOOL_GOOGLE_API_KEY=prod_api_key_here
SEARCH_TOOL_GOOGLE_CSE_ID=prod_cse_id_here
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
SEARCH_TOOL_CACHE_TTL=7200
SEARCH_TOOL_RATE_LIMIT_REQUESTS=50
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=3
SEARCH_TOOL_RETRY_ATTEMPTS=5
SEARCH_TOOL_TIMEOUT=45
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
SEARCH_TOOL_GOOGLE_API_KEY=dev_api_key_here
SEARCH_TOOL_GOOGLE_CSE_ID=dev_cse_id_here
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=5
SEARCH_TOOL_CACHE_TTL=1800
SEARCH_TOOL_RATE_LIMIT_REQUESTS=10
SEARCH_TOOL_RATE_LIMIT_WINDOW=3600
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=10
SEARCH_TOOL_RETRY_ATTEMPTS=2
SEARCH_TOOL_TIMEOUT=15
```

### Best Practices for .env Files

1. **Never commit .env files to version control** - Add `.env` to your `.gitignore`:
   ```gitignore
   # .gitignore
   .env
   .env.local
   .env.*.local
   .env.production
   .env.staging
   ```

2. **Provide a template** - Create `.env.example` with documented dummy values:
   ```bash
   # .env.example
   # Search Tool Configuration
   
   # Google API key for Custom Search
   SEARCH_TOOL_GOOGLE_API_KEY=your_google_api_key_here
   
   # Custom Search Engine ID
   SEARCH_TOOL_GOOGLE_CSE_ID=your_custom_search_engine_id_here
   
   # Path to service account JSON (optional)
   SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   
   # Maximum results per single query
   SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
   
   # Cache time-to-live in seconds
   SEARCH_TOOL_CACHE_TTL=3600
   
   # Rate limiting settings
   SEARCH_TOOL_RATE_LIMIT_REQUESTS=100
   SEARCH_TOOL_RATE_LIMIT_WINDOW=86400
   
   # Circuit breaker settings
   SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=5
   SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=60
   
   # Retry settings
   SEARCH_TOOL_RETRY_ATTEMPTS=3
   SEARCH_TOOL_RETRY_BACKOFF=2.0
   
   # API request timeout in seconds
   SEARCH_TOOL_TIMEOUT=30
   
   # User agent string
   SEARCH_TOOL_USER_AGENT=MySearchBot/1.0
   
   # Allowed search types (JSON array)
   SEARCH_TOOL_ALLOWED_SEARCH_TYPES=["web","image","news","video"]
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Strings: Plain text: `your_api_key_here`, `MySearchBot/1.0`
   - Integers: Plain numbers: `10`, `3600`, `100`
   - Floats: Decimal numbers: `2.0`, `1.5`
   - Lists: JSON array format: `["web","image","news","video"]`

## Configuration Options

### 1. Google API Key

**Environment Variable:** `SEARCH_TOOL_GOOGLE_API_KEY`

**Type:** Optional[str]

**Default:** `None`

**Description:** Google API key for Custom Search API. This is required for all search operations. You can obtain this from the Google Cloud Console.

**How to get:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Custom Search API
4. Go to "Credentials" and create an API key
5. Restrict the API key to Custom Search API

**Example:**
```bash
export SEARCH_TOOL_GOOGLE_API_KEY="AIzaSyBvOkBwv7wjHjf7hK8l9m0n1o2p3q4r5s6t7u8v9w0"
```

**Security Note:** Never commit API keys to version control. Use environment variables or secure secret management.

### 2. Google CSE ID

**Environment Variable:** `SEARCH_TOOL_GOOGLE_CSE_ID`

**Type:** Optional[str]

**Default:** `None`

**Description:** Custom Search Engine ID. This identifies your specific search engine configuration. You can create this at [Google Custom Search](https://cse.google.com/).

**How to get:**
1. Go to [Google Custom Search](https://cse.google.com/)
2. Click "Add" to create a new search engine
3. Configure your search engine settings
4. Copy the Search Engine ID from the setup page

**Example:**
```bash
export SEARCH_TOOL_GOOGLE_CSE_ID="012345678901234567890:abcdefghijk"
```

**Note:** The CSE ID is required for all search operations.

### 3. Google Application Credentials

**Environment Variable:** `SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS`

**Type:** Optional[str]

**Default:** `None`

**Description:** Path to Google service account JSON file. This provides an alternative authentication method using service accounts instead of API keys.

**How to set up:**
1. Go to Google Cloud Console
2. Create a service account
3. Download the JSON key file
4. Set the path to the file

**Example:**
```bash
export SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

**Security Note:** Keep service account files secure and never commit them to version control.

### 4. Max Results Per Query

**Environment Variable:** `SEARCH_TOOL_MAX_RESULTS_PER_QUERY`

**Type:** Integer

**Default:** `10`

**Description:** Maximum number of results to return per single search query. This helps manage API quota usage and response sizes.

**Common Values:**
- `5` - Small result sets (development)
- `10` - Standard result sets (default)
- `20` - Large result sets (production)
- `50` - Very large result sets (data collection)

**Example:**
```bash
export SEARCH_TOOL_MAX_RESULTS_PER_QUERY=20
```

**API Note:** Google Custom Search API has a maximum of 100 results per query.

### 5. Cache TTL

**Environment Variable:** `SEARCH_TOOL_CACHE_TTL`

**Type:** Integer

**Default:** `3600` (1 hour)

**Description:** Cache time-to-live in seconds. This determines how long search results are cached to reduce API calls and improve performance.

**Common Values:**
- `1800` - 30 minutes (frequent updates)
- `3600` - 1 hour (default)
- `7200` - 2 hours (stable content)
- `86400` - 24 hours (rarely changing content)

**Example:**
```bash
export SEARCH_TOOL_CACHE_TTL=7200
```

**Performance Note:** Longer TTL reduces API calls but may return stale results.

### 6. Rate Limit Requests

**Environment Variable:** `SEARCH_TOOL_RATE_LIMIT_REQUESTS`

**Type:** Integer

**Default:** `100`

**Description:** Maximum number of requests allowed within the rate limit window. This prevents exceeding Google's API quotas.

**Common Values:**
- `10` - Conservative (development)
- `50` - Moderate (staging)
- `100` - Standard (default)
- `1000` - High volume (enterprise)

**Example:**
```bash
export SEARCH_TOOL_RATE_LIMIT_REQUESTS=50
```

**Quota Note:** Google Custom Search API has daily quotas. Check your quota limits in the Google Cloud Console.

### 7. Rate Limit Window

**Environment Variable:** `SEARCH_TOOL_RATE_LIMIT_WINDOW`

**Type:** Integer

**Default:** `86400` (24 hours)

**Description:** Time window in seconds for rate limiting. This defines the period over which the rate limit is applied.

**Common Values:**
- `3600` - 1 hour (short-term limiting)
- `86400` - 24 hours (daily limiting, default)
- `604800` - 7 days (weekly limiting)

**Example:**
```bash
export SEARCH_TOOL_RATE_LIMIT_WINDOW=3600
```

**Note:** This should align with your API quota reset period.

### 8. Circuit Breaker Threshold

**Environment Variable:** `SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD`

**Type:** Integer

**Default:** `5`

**Description:** Number of consecutive failures before the circuit breaker opens. This prevents cascading failures when the API is down.

**Common Values:**
- `3` - Sensitive (opens quickly)
- `5` - Standard (default)
- `10` - Tolerant (opens slowly)

**Example:**
```bash
export SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=3
```

**Reliability Note:** Lower thresholds provide faster failure detection but may open on temporary issues.

### 9. Circuit Breaker Timeout

**Environment Variable:** `SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT`

**Type:** Integer

**Default:** `60` (1 minute)

**Description:** Timeout in seconds before the circuit breaker attempts to close (half-open state). This determines how long to wait before retrying after failures.

**Common Values:**
- `30` - Quick recovery (30 seconds)
- `60` - Standard recovery (1 minute, default)
- `300` - Slow recovery (5 minutes)

**Example:**
```bash
export SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=120
```

**Recovery Note:** Longer timeouts give more time for external issues to resolve.

### 10. Retry Attempts

**Environment Variable:** `SEARCH_TOOL_RETRY_ATTEMPTS`

**Type:** Integer

**Default:** `3`

**Description:** Number of retry attempts for failed requests. This helps handle temporary network issues and API errors.

**Common Values:**
- `1` - Minimal retries
- `3` - Standard retries (default)
- `5` - Aggressive retries
- `10` - Maximum retries

**Example:**
```bash
export SEARCH_TOOL_RETRY_ATTEMPTS=5
```

**Resilience Note:** More retries improve reliability but may increase response times.

### 11. Retry Backoff

**Environment Variable:** `SEARCH_TOOL_RETRY_BACKOFF`

**Type:** Float

**Default:** `2.0`

**Description:** Exponential backoff factor for retry delays. This determines how much the delay increases between retry attempts.

**Common Values:**
- `1.5` - Gentle backoff
- `2.0` - Standard backoff (default)
- `3.0` - Aggressive backoff

**Example:**
```bash
export SEARCH_TOOL_RETRY_BACKOFF=1.5
```

**Backoff Note:** Higher factors reduce server load but increase total retry time.

### 12. Timeout

**Environment Variable:** `SEARCH_TOOL_TIMEOUT`

**Type:** Integer

**Default:** `30` (30 seconds)

**Description:** API request timeout in seconds. This prevents hanging requests and ensures timely responses.

**Common Values:**
- `15` - Fast timeout (development)
- `30` - Standard timeout (default)
- `60` - Long timeout (slow networks)
- `120` - Very long timeout (enterprise)

**Example:**
```bash
export SEARCH_TOOL_TIMEOUT=45
```

**Network Note:** Adjust based on your network conditions and API response times.

### 13. User Agent

**Environment Variable:** `SEARCH_TOOL_USER_AGENT`

**Type:** String

**Default:** `"AIECS-SearchTool/1.0"`

**Description:** User agent string sent with API requests. This identifies your application to Google's servers.

**Best Practices:**
- Use descriptive names: `MyCompanySearchBot/1.0`
- Include contact information: `MyBot/1.0 (contact@company.com)`
- Follow Google's guidelines for user agents

**Example:**
```bash
export SEARCH_TOOL_USER_AGENT="MyResearchBot/1.0 (research@university.edu)"
```

**Compliance Note:** Always follow Google's terms of service and API usage guidelines.

### 14. Allowed Search Types

**Environment Variable:** `SEARCH_TOOL_ALLOWED_SEARCH_TYPES`

**Type:** List[str]

**Default:** `["web", "image", "news", "video"]`

**Description:** List of allowed search types. This restricts which search operations are permitted, providing security and quota management.

**Format:** JSON array string with double quotes

**Available Types:**
- `web` - General web search
- `image` - Image search
- `news` - News search
- `video` - Video search

**Example:**
```bash
# Allow all search types
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES='["web","image","news","video"]'

# Restrict to web search only
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES='["web"]'

# Allow web and image search
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES='["web","image"]'
```

**Security Note:** Restrict search types based on your application's needs to prevent unauthorized usage.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set essential API credentials
export SEARCH_TOOL_GOOGLE_API_KEY="your_api_key_here"
export SEARCH_TOOL_GOOGLE_CSE_ID="your_cse_id_here"
export SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
export SEARCH_TOOL_CACHE_TTL=3600

# Run your application
python app.py
```

### Example 2: Production Configuration

```bash
# Production settings with conservative limits
export SEARCH_TOOL_GOOGLE_API_KEY="prod_api_key_here"
export SEARCH_TOOL_GOOGLE_CSE_ID="prod_cse_id_here"
export SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
export SEARCH_TOOL_CACHE_TTL=7200
export SEARCH_TOOL_RATE_LIMIT_REQUESTS=50
export SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=3
export SEARCH_TOOL_RETRY_ATTEMPTS=5
export SEARCH_TOOL_TIMEOUT=45
```

### Example 3: Development Configuration

```bash
# Development settings with permissive limits
export SEARCH_TOOL_GOOGLE_API_KEY="dev_api_key_here"
export SEARCH_TOOL_GOOGLE_CSE_ID="dev_cse_id_here"
export SEARCH_TOOL_MAX_RESULTS_PER_QUERY=5
export SEARCH_TOOL_CACHE_TTL=1800
export SEARCH_TOOL_RATE_LIMIT_REQUESTS=10
export SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=10
export SEARCH_TOOL_RETRY_ATTEMPTS=2
export SEARCH_TOOL_TIMEOUT=15
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.search_tool import SearchTool

# Initialize with custom configuration
search_tool = SearchTool(config={
    'google_api_key': 'your_api_key_here',
    'google_cse_id': 'your_cse_id_here',
    'max_results_per_query': 20,
    'cache_ttl': 7200,
    'rate_limit_requests': 50,
    'circuit_breaker_threshold': 3,
    'retry_attempts': 5,
    'timeout': 45
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
export SEARCH_TOOL_CACHE_TTL=3600
```

```python
# Override for specific instance
search_tool = SearchTool(config={
    'max_results_per_query': 20,  # This overrides the environment variable
    'cache_ttl': 7200             # This overrides the environment variable
})
```

## Configuration Priority

When the Search Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `SEARCH_TOOL_*` variables
3. **Global settings** - Values from aiecs global configuration
4. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export SEARCH_TOOL_GOOGLE_API_KEY=your_api_key_here
export SEARCH_TOOL_USER_AGENT=MySearchBot/1.0
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
export SEARCH_TOOL_CACHE_TTL=3600
export SEARCH_TOOL_TIMEOUT=30
```

### Float Values

Floats should be provided as decimal strings:

```bash
export SEARCH_TOOL_RETRY_BACKOFF=2.0
```

### List Values

Lists must be provided as JSON arrays with double quotes:

```bash
# Correct
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES='["web","image","news","video"]'

# Incorrect (will not parse)
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES="web,image,news,video"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES='["web","image","news","video"]'
#                                      ^                    ^
#                                      Single quotes for shell
#                                         ^      ^
#                                         Double quotes for JSON
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `google_api_key` must be a string or None
- `google_cse_id` must be a string or None
- `google_application_credentials` must be a string or None
- `max_results_per_query` must be a positive integer
- `cache_ttl` must be a positive integer
- `rate_limit_requests` must be a positive integer
- `rate_limit_window` must be a positive integer
- `circuit_breaker_threshold` must be a positive integer
- `circuit_breaker_timeout` must be a positive integer
- `retry_attempts` must be a positive integer
- `retry_backoff` must be a positive float
- `timeout` must be a positive integer
- `user_agent` must be a non-empty string
- `allowed_search_types` must be a list of strings

### Runtime Validation

When performing searches, the tool validates:

1. **API credentials** - Google API key and CSE ID must be provided
2. **Search type authorization** - Search type must be in allowed list
3. **Rate limits** - Requests must not exceed rate limits
4. **Circuit breaker state** - Circuit breaker must not be open
5. **Input parameters** - Search queries and parameters must be valid

## Operations Supported

The Search Tool supports comprehensive search operations:

### Web Search
- `search_web` - General web search with customizable parameters
- Supports pagination, language filtering, and date ranges
- Returns structured results with titles, snippets, and URLs

### Image Search
- `search_images` - Image search with size, type, and color filters
- Supports various image formats and quality levels
- Returns image URLs, dimensions, and metadata

### News Search
- `search_news` - News search with date and source filtering
- Supports recent news and historical news searches
- Returns news articles with publication dates and sources

### Video Search
- `search_videos` - Video search with duration and quality filters
- Supports various video platforms and formats
- Returns video URLs, durations, and metadata

### Batch Operations
- `batch_search` - Perform multiple searches in parallel
- Supports different search types in a single operation
- Efficient processing of multiple queries

### Advanced Features
- **Pagination** - Navigate through large result sets
- **Filtering** - Filter results by date, language, site, etc.
- **Caching** - Intelligent caching to reduce API calls
- **Rate limiting** - Automatic rate limiting to prevent quota exhaustion
- **Circuit breaker** - Automatic failure protection
- **Retry logic** - Automatic retry with exponential backoff

## Troubleshooting

### Issue: API key not found

**Error:** `AuthenticationError: Google API key not provided`

**Solutions:**
1. Set API key: `export SEARCH_TOOL_GOOGLE_API_KEY="your_api_key_here"`
2. Check API key validity in Google Cloud Console
3. Ensure API key has Custom Search API enabled

### Issue: CSE ID not found

**Error:** `AuthenticationError: Google CSE ID not provided`

**Solutions:**
1. Set CSE ID: `export SEARCH_TOOL_GOOGLE_CSE_ID="your_cse_id_here"`
2. Create Custom Search Engine at [Google Custom Search](https://cse.google.com/)
3. Verify CSE ID is correct

### Issue: Quota exceeded

**Error:** `QuotaExceededError: API quota exceeded`

**Solutions:**
```bash
# Reduce rate limits
export SEARCH_TOOL_RATE_LIMIT_REQUESTS=10
export SEARCH_TOOL_RATE_LIMIT_WINDOW=3600

# Increase cache TTL
export SEARCH_TOOL_CACHE_TTL=7200
```

### Issue: Rate limit exceeded

**Error:** `RateLimitError: Rate limit exceeded`

**Solutions:**
```bash
# Reduce request rate
export SEARCH_TOOL_RATE_LIMIT_REQUESTS=5
export SEARCH_TOOL_RATE_LIMIT_WINDOW=3600

# Implement delays between requests
```

### Issue: Circuit breaker open

**Error:** `CircuitBreakerOpenError: Circuit breaker is open`

**Solutions:**
```bash
# Adjust circuit breaker settings
export SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=10
export SEARCH_TOOL_CIRCUIT_BREAKER_TIMEOUT=120

# Check API status and network connectivity
```

### Issue: Search type not allowed

**Error:** `ValidationError: Search type not allowed`

**Solutions:**
```bash
# Add search type to allowed list
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES='["web","image","news","video"]'

# Or allow all types
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES='["web","image","news","video"]'
```

### Issue: Timeout errors

**Error:** `TimeoutError` or `Request timeout`

**Solutions:**
```bash
# Increase timeout
export SEARCH_TOOL_TIMEOUT=60

# Check network connectivity
# Verify API endpoint accessibility
```

### Issue: Service account authentication fails

**Error:** `AuthenticationError: Service account authentication failed`

**Solutions:**
1. Verify service account file path: `export SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS="/correct/path"`
2. Check file permissions and format
3. Ensure service account has proper roles

### Issue: List parsing error

**Error:** Configuration parsing fails for `allowed_search_types`

**Solution:**
```bash
# Use proper JSON array syntax
export SEARCH_TOOL_ALLOWED_SEARCH_TYPES='["web","image","news","video"]'

# NOT: [web,image,news,video] or web,image,news,video
```

## Best Practices

### API Key Security

1. **Never commit API keys** - Use environment variables or secret management
2. **Restrict API keys** - Limit to specific APIs and IP addresses
3. **Rotate keys regularly** - Change API keys periodically
4. **Monitor usage** - Track API key usage and costs
5. **Use service accounts** - For server applications, use service accounts

### Rate Limiting

1. **Monitor quotas** - Track daily API usage
2. **Implement caching** - Reduce API calls with intelligent caching
3. **Use batch operations** - Combine multiple requests when possible
4. **Respect limits** - Stay well below quota limits
5. **Handle rate limits gracefully** - Implement proper error handling

### Caching Strategy

1. **Set appropriate TTL** - Balance freshness vs. performance
2. **Cache by query** - Use query-specific cache keys
3. **Invalidate stale data** - Clear cache when needed
4. **Monitor cache hit rates** - Optimize cache effectiveness
5. **Use persistent storage** - For long-term caching

### Error Handling

1. **Implement retry logic** - Handle temporary failures
2. **Use circuit breakers** - Prevent cascading failures
3. **Log errors appropriately** - Monitor and debug issues
4. **Provide fallbacks** - Graceful degradation when possible
5. **Monitor error rates** - Track and alert on failures

### Performance Optimization

1. **Optimize queries** - Use specific, targeted search terms
2. **Limit result sets** - Request only needed results
3. **Use pagination** - For large result sets
4. **Implement async operations** - For concurrent requests
5. **Monitor response times** - Track and optimize performance

### Development vs Production

**Development:**
```bash
SEARCH_TOOL_GOOGLE_API_KEY=dev_api_key_here
SEARCH_TOOL_GOOGLE_CSE_ID=dev_cse_id_here
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=5
SEARCH_TOOL_CACHE_TTL=1800
SEARCH_TOOL_RATE_LIMIT_REQUESTS=10
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=10
SEARCH_TOOL_RETRY_ATTEMPTS=2
SEARCH_TOOL_TIMEOUT=15
```

**Production:**
```bash
SEARCH_TOOL_GOOGLE_API_KEY=prod_api_key_here
SEARCH_TOOL_GOOGLE_CSE_ID=prod_cse_id_here
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
SEARCH_TOOL_CACHE_TTL=7200
SEARCH_TOOL_RATE_LIMIT_REQUESTS=50
SEARCH_TOOL_CIRCUIT_BREAKER_THRESHOLD=3
SEARCH_TOOL_RETRY_ATTEMPTS=5
SEARCH_TOOL_TIMEOUT=45
```

### Error Handling

Always wrap search operations in try-except blocks:

```python
from aiecs.tools.task_tools.search_tool import SearchTool, SearchToolError, AuthenticationError, QuotaExceededError

search_tool = SearchTool()

try:
    results = await search_tool.search_web("python programming")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except QuotaExceededError as e:
    print(f"Quota exceeded: {e}")
except SearchToolError as e:
    print(f"Search error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Google Custom Search Setup

### Creating a Custom Search Engine

1. **Go to Google Custom Search** - Visit [https://cse.google.com/](https://cse.google.com/)
2. **Create new search engine** - Click "Add" to create a new CSE
3. **Configure search settings**:
   - Enter sites to search (or leave blank for web-wide search)
   - Set language and region preferences
   - Configure advanced options
4. **Get your CSE ID** - Copy the Search Engine ID from the setup page
5. **Test your search engine** - Use the test interface to verify configuration

### API Key Setup

1. **Go to Google Cloud Console** - Visit [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. **Create or select project** - Choose your project
3. **Enable Custom Search API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Custom Search API"
   - Click "Enable"
4. **Create API key**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy the generated API key
5. **Restrict API key** (recommended):
   - Click on the API key to edit
   - Restrict to "Custom Search API"
   - Add IP address restrictions if needed

### Service Account Setup (Optional)

1. **Create service account**:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Fill in details and create
2. **Download key file**:
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format and download
3. **Set environment variable**:
   ```bash
   export SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
   ```

## Related Documentation

- Tool implementation details in the source code
- Google Custom Search API documentation: https://developers.google.com/custom-search/v1/introduction
- Google Cloud Console: https://console.cloud.google.com/
- Google Custom Search Engine: https://cse.google.com/
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Search Tool configuration:
- Check the tool source code for implementation details
- Review Google Custom Search API documentation
- Consult the main aiecs documentation for architecture overview
- Test with simple queries first to isolate configuration vs. API issues
- Monitor API quotas and usage in Google Cloud Console
- Verify API key and CSE ID configuration
- Check network connectivity and firewall settings
