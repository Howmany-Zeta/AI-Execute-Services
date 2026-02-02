# Scraper Tool Stealth Mode - Quick Start Guide

## What is Stealth Mode?

Stealth mode helps the ScraperTool's Playwright browser avoid detection by anti-bot systems. It applies various techniques to make the automated browser appear more like a regular user's browser.

## Quick Installation

```bash
# Install playwright-stealth
pip install playwright-stealth

# Or install all scraper extras
pip install aiecs[scraper]

# Verify installation
python -c "from playwright_stealth import stealth_async; print('✓ Stealth mode ready')"
```

## Quick Usage

### Method 1: Enable Globally via Environment Variable

```bash
# In your .env file or shell
export SCRAPER_TOOL_USE_STEALTH=true
```

```python
from aiecs.tools.scraper_tool import ScraperTool

scraper = ScraperTool(config={'enable_js_render': True})
result = await scraper.fetch(url="https://example.com")
# Stealth mode is automatically enabled
```

### Method 2: Enable via Configuration

```python
from aiecs.tools.scraper_tool import ScraperTool

scraper = ScraperTool(config={'use_stealth': True, 'enable_js_render': True})
result = await scraper.fetch(url="https://example.com")
```

### Method 3: Enable Per Request

```python
from aiecs.tools.scraper_tool import ScraperTool

# Enable stealth globally
scraper = ScraperTool(config={'use_stealth': True, 'enable_js_render': True})

# Fetch with stealth enabled
result = await scraper.fetch(url="https://example.com")

# Disable stealth for specific requests (configure separately)
scraper_no_stealth = ScraperTool(config={'use_stealth': False, 'enable_js_render': True})
result = await scraper_no_stealth.fetch(url="https://another-site.com")
```

## Complete Example

```python
import asyncio
from aiecs.tools.scraper_tool import ScraperTool

async def scrape_with_stealth():
    # Initialize scraper with stealth mode
    scraper = ScraperTool(config={
        'use_stealth': True,
        'enable_js_render': True,
        'timeout': 30
    })

    try:
        # Fetch a page with JavaScript rendering
        result = await scraper.fetch(url="https://example.com")

        if result.get('success'):
            print(f"✓ Page fetched successfully")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  URL: {result.get('url')}")
            print(f"  Content length: {len(result.get('content', ''))}")
        else:
            print(f"✗ Fetch failed: {result.get('error')}")

        return result

    except Exception as e:
        print(f"✗ Error: {e}")
        return None

# Run the scraper
asyncio.run(scrape_with_stealth())
```

## When to Use Stealth Mode

### ✅ Use Stealth Mode When:
- Scraping sites with Cloudflare protection
- Accessing content that blocks automated browsers
- Sites show "Please verify you are human" messages
- Getting 403 Forbidden errors with regular scraping
- Testing website behavior with realistic browser profiles

### ❌ Don't Need Stealth Mode When:
- Scraping simple static HTML pages
- Using APIs instead of web scraping
- Site explicitly allows bots (check robots.txt)
- Using regular HTTP requests (not Playwright rendering)

## Troubleshooting

### Issue: "playwright-stealth is not installed" warning

**Solution:**
```bash
pip install playwright-stealth
```

### Issue: Still getting detected as a bot

**Try these solutions:**

1. **Use a realistic user agent:**
```python
scraper = ScraperTool(config={
    'use_stealth': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})
```

2. **Add delays between requests:**
```python
import asyncio

result1 = await scraper.render(url1, use_stealth=True)
await asyncio.sleep(3)  # Wait 3 seconds
result2 = await scraper.render(url2, use_stealth=True)
```

3. **Increase wait time:**
```python
result = await scraper.render(
    url="https://example.com",
    wait_time=10,  # Wait longer for page to load
    use_stealth=True
)
```

## Important Notes

- ⚠️ Stealth mode only works with Playwright rendering (`render()` method)
- ⚠️ Does NOT work with regular HTTP requests (`get_httpx()`, `get_urllib()`)
- ⚠️ Not 100% foolproof against advanced bot detection
- ⚠️ Always respect robots.txt and website terms of service
- ⚠️ Some sites may still detect automation despite stealth mode

## Configuration Reference

| Method | Priority | Example |
|--------|----------|---------|
| Parameter | Highest | `render(url, use_stealth=True)` |
| Config | Medium | `ScraperTool(config={'use_stealth': True})` |
| Environment | Lowest | `SCRAPER_TOOL_USE_STEALTH=true` |

## See Also

- [Full Scraper Tool Configuration Guide](SCRAPER_TOOL_CONFIGURATION.md)
- [Playwright Documentation](https://playwright.dev/python/)
- [playwright-stealth GitHub](https://github.com/AtuboDad/playwright_stealth)

