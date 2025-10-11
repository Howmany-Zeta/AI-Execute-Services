# Scraper Tool Configuration Guide

## Overview

The Scraper Tool provides comprehensive web scraping capabilities with multiple HTTP clients, JavaScript rendering, HTML parsing, and security features. It supports httpx, urllib, Playwright for JavaScript rendering, BeautifulSoup for HTML parsing, and Scrapy integration for advanced crawling. The tool can be configured via environment variables using the `SCRAPER_TOOL_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Scraper Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
SCRAPER_TOOL_USER_AGENT=MyScraperBot/1.0
SCRAPER_TOOL_MAX_CONTENT_LENGTH=10485760
SCRAPER_TOOL_OUTPUT_DIR=/path/to/outputs
SCRAPER_TOOL_SCRAPY_COMMAND=scrapy
SCRAPER_TOOL_ALLOWED_DOMAINS=["example.com","api.example.com"]
SCRAPER_TOOL_BLOCKED_DOMAINS=["blocked.com","malicious.com"]
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.scraper_tool import ScraperTool

# The tool will automatically use the environment variables
scraper_tool = ScraperTool()
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

from aiecs.tools.task_tools.scraper_tool import ScraperTool
scraper_tool = ScraperTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for security and performance
SCRAPER_TOOL_USER_AGENT=ProductionScraper/2.0
SCRAPER_TOOL_MAX_CONTENT_LENGTH=52428800
SCRAPER_TOOL_OUTPUT_DIR=/app/scraper_outputs
SCRAPER_TOOL_ALLOWED_DOMAINS=["trusted-site.com","api.trusted-site.com"]
SCRAPER_TOOL_BLOCKED_DOMAINS=["malicious.com","spam.com"]
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
SCRAPER_TOOL_USER_AGENT=DevScraper/1.0
SCRAPER_TOOL_MAX_CONTENT_LENGTH=10485760
SCRAPER_TOOL_OUTPUT_DIR=./scraper_outputs
SCRAPER_TOOL_ALLOWED_DOMAINS=[]
SCRAPER_TOOL_BLOCKED_DOMAINS=[]
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
   # Scraper Tool Configuration
   
   # User agent for HTTP requests
   SCRAPER_TOOL_USER_AGENT=MyScraperBot/1.0
   
   # Maximum content length in bytes (10MB)
   SCRAPER_TOOL_MAX_CONTENT_LENGTH=10485760
   
   # Directory for output files
   SCRAPER_TOOL_OUTPUT_DIR=./scraper_outputs
   
   # Command to run Scrapy
   SCRAPER_TOOL_SCRAPY_COMMAND=scrapy
   
   # Allowed domains for scraping (JSON array)
   SCRAPER_TOOL_ALLOWED_DOMAINS=["example.com","api.example.com"]
   
   # Blocked domains for scraping (JSON array)
   SCRAPER_TOOL_BLOCKED_DOMAINS=["blocked.com","malicious.com"]
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Strings: Plain text: `MyScraperBot/1.0`, `scrapy`
   - Integers: Plain numbers: `10485760`, `52428800`
   - Lists: JSON array format: `["example.com","api.example.com"]`

## Configuration Options

### 1. User Agent

**Environment Variable:** `SCRAPER_TOOL_USER_AGENT`

**Type:** String

**Default:** `"PythonMiddlewareScraper/2.0"`

**Description:** User agent string sent with HTTP requests. This identifies your scraper to web servers and should be descriptive and respectful.

**Best Practices:**
- Use a descriptive name: `MyCompanyBot/1.0`
- Include contact information: `MyBot/1.0 (contact@example.com)`
- Follow robots.txt guidelines
- Be honest about your bot's purpose

**Example:**
```bash
export SCRAPER_TOOL_USER_AGENT="MyResearchBot/1.0 (research@university.edu)"
```

**Legal Note:** Always respect robots.txt and website terms of service.

### 2. Max Content Length

**Environment Variable:** `SCRAPER_TOOL_MAX_CONTENT_LENGTH`

**Type:** Integer

**Default:** `10 * 1024 * 1024` (10MB)

**Description:** Maximum content length in bytes for HTTP responses. This prevents memory issues with extremely large files and ensures reasonable processing times.

**Common Values:**
- `5 * 1024 * 1024` - 5MB (small files)
- `10 * 1024 * 1024` - 10MB (default)
- `50 * 1024 * 1024` - 50MB (large files)
- `100 * 1024 * 1024` - 100MB (very large files)

**Example:**
```bash
export SCRAPER_TOOL_MAX_CONTENT_LENGTH=52428800
```

**Memory Note:** Larger values use more memory but allow processing of bigger files. Adjust based on available system resources.

### 3. Output Directory

**Environment Variable:** `SCRAPER_TOOL_OUTPUT_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'scraper_outputs')`

**Description:** Directory where scraped content and output files are saved. The directory will be created automatically if it doesn't exist.

**Example:**
```bash
export SCRAPER_TOOL_OUTPUT_DIR="/app/scraper_outputs"
```

**Security Note:** Ensure the directory has appropriate permissions and is not accessible via web servers.

### 4. Scrapy Command

**Environment Variable:** `SCRAPER_TOOL_SCRAPY_COMMAND`

**Type:** String

**Default:** `"scrapy"`

**Description:** Command to run Scrapy spiders. This can be customized for different Scrapy installations or virtual environments.

**Common Values:**
- `scrapy` - Standard Scrapy command
- `python -m scrapy` - Python module execution
- `/path/to/venv/bin/scrapy` - Virtual environment Scrapy
- `docker exec container scrapy` - Docker container execution

**Example:**
```bash
export SCRAPER_TOOL_SCRAPY_COMMAND="python -m scrapy"
```

**Note:** Ensure Scrapy is installed and accessible via the specified command.

### 5. Allowed Domains

**Environment Variable:** `SCRAPER_TOOL_ALLOWED_DOMAINS`

**Type:** List[str]

**Default:** `[]` (empty list - no restrictions)

**Description:** List of allowed domains for scraping. This is a security feature that restricts scraping to specific domains. Empty list means no restrictions.

**Format:** JSON array string with double quotes

**Security Configurations:**
- **Restrictive:** `["trusted-site.com","api.trusted-site.com"]`
- **Permissive:** `[]` (no restrictions)
- **API only:** `["api.example.com"]`

**Example:**
```bash
# Allow only specific domains
export SCRAPER_TOOL_ALLOWED_DOMAINS='["example.com","api.example.com"]'

# No restrictions (development only)
export SCRAPER_TOOL_ALLOWED_DOMAINS='[]'
```

**Security Note:** Use restrictive domain lists in production to prevent unauthorized scraping.

### 6. Blocked Domains

**Environment Variable:** `SCRAPER_TOOL_BLOCKED_DOMAINS`

**Type:** List[str]

**Default:** `[]` (empty list - no blocks)

**Description:** List of blocked domains for scraping. This prevents scraping of known malicious or problematic domains.

**Format:** JSON array string with double quotes

**Common Blocked Domains:**
- Malicious sites
- Sites with aggressive anti-bot measures
- Sites that violate terms of service
- Sites with known security issues

**Example:**
```bash
# Block known problematic domains
export SCRAPER_TOOL_BLOCKED_DOMAINS='["malicious.com","spam.com","blocked-site.com"]'
```

**Security Note:** Regularly update blocked domains list based on security advisories.

### 7. Playwright Available (Read-Only)

**Environment Variable:** Not configurable via environment

**Type:** Boolean

**Default:** `False` (auto-detected)

**Description:** Whether Playwright is available for JavaScript rendering. This is automatically detected during initialization and cannot be set via environment variables.

**Auto-Detection:** The tool automatically checks if Playwright is installed and sets this field accordingly.

**Installation:**
```bash
pip install playwright
playwright install
```

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom scraping parameters
export SCRAPER_TOOL_USER_AGENT="MyBot/1.0"
export SCRAPER_TOOL_MAX_CONTENT_LENGTH=52428800
export SCRAPER_TOOL_OUTPUT_DIR="/app/scraper_outputs"

# Run your application
python app.py
```

### Example 2: Security-Focused Configuration

```bash
# Strict security settings
export SCRAPER_TOOL_USER_AGENT="SecureBot/1.0 (contact@company.com)"
export SCRAPER_TOOL_ALLOWED_DOMAINS='["trusted-site.com","api.trusted-site.com"]'
export SCRAPER_TOOL_BLOCKED_DOMAINS='["malicious.com","spam.com"]'
export SCRAPER_TOOL_MAX_CONTENT_LENGTH=10485760
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export SCRAPER_TOOL_USER_AGENT="DevBot/1.0"
export SCRAPER_TOOL_OUTPUT_DIR="./scraper_outputs"
export SCRAPER_TOOL_ALLOWED_DOMAINS='[]'
export SCRAPER_TOOL_BLOCKED_DOMAINS='[]'
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.scraper_tool import ScraperTool

# Initialize with custom configuration
scraper_tool = ScraperTool(config={
    'user_agent': 'MyBot/1.0',
    'max_content_length': 52428800,
    'output_dir': '/app/scraper_outputs',
    'allowed_domains': ['example.com', 'api.example.com'],
    'blocked_domains': ['malicious.com']
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export SCRAPER_TOOL_USER_AGENT="DefaultBot/1.0"
export SCRAPER_TOOL_MAX_CONTENT_LENGTH=10485760
```

```python
# Override for specific instance
scraper_tool = ScraperTool(config={
    'user_agent': 'CustomBot/2.0',  # This overrides the environment variable
    'max_content_length': 52428800  # This overrides the environment variable
})
```

## Configuration Priority

When the Scraper Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `SCRAPER_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export SCRAPER_TOOL_USER_AGENT=MyBot/1.0
export SCRAPER_TOOL_SCRAPY_COMMAND=scrapy
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export SCRAPER_TOOL_MAX_CONTENT_LENGTH=10485760
```

### List Values

Lists must be provided as JSON arrays with double quotes:

```bash
# Correct
export SCRAPER_TOOL_ALLOWED_DOMAINS='["example.com","api.example.com"]'

# Incorrect (will not parse)
export SCRAPER_TOOL_ALLOWED_DOMAINS="example.com,api.example.com"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export SCRAPER_TOOL_ALLOWED_DOMAINS='["example.com","api.example.com"]'
#                                      ^                    ^
#                                      Single quotes for shell
#                                         ^      ^
#                                         Double quotes for JSON
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `user_agent` must be a non-empty string
- `max_content_length` must be a positive integer
- `output_dir` must be a non-empty string
- `scrapy_command` must be a non-empty string
- `allowed_domains` must be a list of strings
- `blocked_domains` must be a list of strings
- `playwright_available` must be a boolean

### Runtime Validation

When scraping, the tool validates:

1. **Domain restrictions** - URLs must be in allowed domains (if specified)
2. **Domain blocks** - URLs must not be in blocked domains
3. **Content length** - Response content must not exceed max_content_length
4. **Output directory** - Output directory must be writable
5. **External tools** - Scrapy and Playwright availability is checked

## Operations Supported

The Scraper Tool supports comprehensive web scraping operations:

### HTTP Clients

#### Httpx Client
- `get_httpx` - Modern async HTTP client with full feature support
- Supports all HTTP methods (GET, POST, PUT, DELETE, etc.)
- Built-in SSL verification and redirect handling
- Cookie and authentication support

#### Urllib Client
- `get_urllib` - Standard library HTTP client
- Lightweight alternative to httpx
- Good for simple requests without advanced features

#### Legacy Methods
- `get_requests` - Legacy method (now uses httpx in sync mode)
- `get_aiohttp` - Legacy method (now uses httpx in async mode)

### JavaScript Rendering

#### Playwright Rendering
- `render` - Render JavaScript-heavy pages
- Supports waiting for specific elements
- Screenshot capture capabilities
- Scroll and interaction support

### HTML Parsing

#### BeautifulSoup Parsing
- `parse_html` - Parse HTML content with CSS selectors
- XPath support via lxml
- Attribute and text extraction
- Flexible selector types

### Scrapy Integration

#### Spider Execution
- `crawl_scrapy` - Execute Scrapy spiders
- Custom spider arguments support
- Output file generation
- Execution monitoring

### Output Formats

#### Multiple Formats
- **Text** - Plain text output
- **JSON** - Structured JSON data
- **HTML** - Raw HTML content
- **Markdown** - Formatted markdown
- **CSV** - Tabular data export

## Troubleshooting

### Issue: SSL certificate errors

**Error:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions:**
1. Update certificates: `pip install --upgrade certifi`
2. Disable SSL verification (not recommended): Set `verify_ssl=False`
3. Use custom CA bundle: Set `verify_ssl="/path/to/ca-bundle.pem"`

### Issue: Playwright not available

**Error:** `Playwright is not available`

**Solutions:**
```bash
# Install Playwright
pip install playwright

# Install browser binaries
playwright install

# Verify installation
python -c "import playwright; print('Playwright installed')"
```

### Issue: Scrapy command not found

**Error:** `Scrapy crawl failed: command not found`

**Solutions:**
```bash
# Install Scrapy
pip install scrapy

# Check command
export SCRAPER_TOOL_SCRAPY_COMMAND="python -m scrapy"

# Or use full path
export SCRAPER_TOOL_SCRAPY_COMMAND="/path/to/venv/bin/scrapy"
```

### Issue: Content too large

**Error:** `Response content too large`

**Solutions:**
```bash
# Increase content length limit
export SCRAPER_TOOL_MAX_CONTENT_LENGTH=52428800

# Or process content in chunks
# Use streaming requests for large files
```

### Issue: Domain not allowed

**Error:** `Domain not in allowed list`

**Solutions:**
```bash
# Add domain to allowed list
export SCRAPER_TOOL_ALLOWED_DOMAINS='["example.com","new-domain.com"]'

# Or remove restrictions (development only)
export SCRAPER_TOOL_ALLOWED_DOMAINS='[]'
```

### Issue: Rate limiting

**Error:** `Rate limit exceeded` or `429 Too Many Requests`

**Solutions:**
1. Implement delays between requests
2. Use rotating user agents
3. Respect robots.txt
4. Use proxy rotation
5. Implement exponential backoff

### Issue: Timeout errors

**Error:** `Request timeout` or `Connection timeout`

**Solutions:**
1. Increase timeout values
2. Check network connectivity
3. Use retry mechanisms
4. Implement circuit breakers

### Issue: List parsing error

**Error:** Configuration parsing fails for domain lists

**Solution:**
```bash
# Use proper JSON array syntax
export SCRAPER_TOOL_ALLOWED_DOMAINS='["example.com","api.example.com"]'

# NOT: [example.com,api.example.com] or example.com,api.example.com
```

### Issue: Output directory not writable

**Error:** `Permission denied` when saving files

**Solutions:**
```bash
# Set writable output directory
export SCRAPER_TOOL_OUTPUT_DIR="/writable/path"

# Or create directory with proper permissions
mkdir -p /path/to/outputs
chmod 755 /path/to/outputs
```

## Best Practices

### Web Scraping Ethics

1. **Respect robots.txt** - Always check and follow robots.txt files
2. **Rate limiting** - Implement delays between requests
3. **User agent identification** - Use descriptive, honest user agents
4. **Terms of service** - Read and follow website terms of service
5. **Legal compliance** - Ensure compliance with local laws and regulations

### Security

1. **Domain filtering** - Use allowed/blocked domain lists
2. **Content validation** - Validate scraped content for malicious code
3. **SSL verification** - Always verify SSL certificates in production
4. **Input sanitization** - Sanitize URLs and parameters
5. **Output security** - Secure output directories and files

### Performance

1. **Connection pooling** - Reuse HTTP connections when possible
2. **Async operations** - Use async methods for better concurrency
3. **Memory management** - Monitor memory usage with large content
4. **Caching** - Implement caching for frequently accessed content
5. **Resource limits** - Set appropriate content length limits

### Error Handling

1. **Retry mechanisms** - Implement exponential backoff for failed requests
2. **Circuit breakers** - Stop requests to failing services
3. **Graceful degradation** - Handle partial failures gracefully
4. **Logging** - Log errors and performance metrics
5. **Monitoring** - Monitor scraping success rates and performance

### Development vs Production

**Development:**
```bash
SCRAPER_TOOL_USER_AGENT=DevBot/1.0
SCRAPER_TOOL_OUTPUT_DIR=./scraper_outputs
SCRAPER_TOOL_ALLOWED_DOMAINS='[]'
SCRAPER_TOOL_BLOCKED_DOMAINS='[]'
SCRAPER_TOOL_MAX_CONTENT_LENGTH=10485760
```

**Production:**
```bash
SCRAPER_TOOL_USER_AGENT=ProductionBot/2.0 (contact@company.com)
SCRAPER_TOOL_OUTPUT_DIR=/app/scraper_outputs
SCRAPER_TOOL_ALLOWED_DOMAINS='["trusted-site.com","api.trusted-site.com"]'
SCRAPER_TOOL_BLOCKED_DOMAINS='["malicious.com","spam.com"]'
SCRAPER_TOOL_MAX_CONTENT_LENGTH=52428800
```

### Error Handling

Always wrap scraping operations in try-except blocks:

```python
from aiecs.tools.task_tools.scraper_tool import ScraperTool, HttpError, TimeoutError, RateLimitError

scraper_tool = ScraperTool()

try:
    result = await scraper_tool.get_httpx(url)
except HttpError as e:
    print(f"HTTP error: {e}")
except TimeoutError as e:
    print(f"Timeout error: {e}")
except RateLimitError as e:
    print(f"Rate limit error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Installation Requirements

### Core Dependencies

```bash
# Install core scraping dependencies
pip install httpx beautifulsoup4 lxml

# Install optional dependencies
pip install playwright scrapy
```

### Playwright Setup

```bash
# Install Playwright
pip install playwright

# Install browser binaries
playwright install

# Install specific browsers
playwright install chromium
playwright install firefox
playwright install webkit
```

### Scrapy Setup

```bash
# Install Scrapy
pip install scrapy

# Create a Scrapy project
scrapy startproject myproject

# Create a spider
cd myproject
scrapy genspider myspider example.com
```

### Verification

```python
# Test Playwright installation
try:
    import playwright
    print("Playwright installed successfully")
except ImportError:
    print("Playwright not installed")

# Test Scrapy installation
try:
    import scrapy
    print("Scrapy installed successfully")
except ImportError:
    print("Scrapy not installed")
```

## Related Documentation

- Tool implementation details in the source code
- Httpx documentation: https://www.python-httpx.org/
- BeautifulSoup documentation: https://www.crummy.com/software/BeautifulSoup/
- Playwright documentation: https://playwright.dev/python/
- Scrapy documentation: https://docs.scrapy.org/
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Scraper Tool configuration:
- Check the tool source code for implementation details
- Review HTTP client documentation for specific features
- Consult the main aiecs documentation for architecture overview
- Test with simple URLs first to isolate configuration vs. scraping issues
- Monitor network traffic and response times
- Validate SSL certificates and domain restrictions
- Check robots.txt and terms of service compliance
