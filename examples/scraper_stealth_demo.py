"""
Demonstration of ScraperTool with Playwright Stealth Mode

This example shows how to use the ScraperTool with stealth mode enabled
to avoid bot detection when scraping websites.

Prerequisites:
    pip install playwright-stealth
    playwright install chromium

Usage:
    python examples/scraper_stealth_demo.py
"""

import asyncio
import logging
from aiecs.tools.scraper_tool import ScraperTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def demo_stealth_mode():
    """Demonstrate stealth mode usage."""
    print("=" * 80)
    print("ScraperTool Stealth Mode Demo")
    print("=" * 80)
    
    # Example 1: Using stealth mode via configuration
    print("\n1. Using stealth mode via configuration:")
    print("-" * 80)
    
    scraper_with_stealth = ScraperTool(config={"use_stealth": True})
    
    try:
        result = await scraper_with_stealth.render(
            url="https://httpbin.org/html",
            wait_time=3,
            screenshot=False
        )
        print(f"✓ Successfully rendered page with stealth mode")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        print(f"  HTML length: {len(result['html'])} characters")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    # Example 2: Using stealth mode via parameter
    print("\n2. Using stealth mode via parameter:")
    print("-" * 80)
    
    scraper_default = ScraperTool()
    
    try:
        result = await scraper_default.render(
            url="https://httpbin.org/html",
            wait_time=3,
            screenshot=False,
            use_stealth=True  # Override config with parameter
        )
        print(f"✓ Successfully rendered page with stealth mode (parameter)")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        print(f"  HTML length: {len(result['html'])} characters")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    # Example 3: Without stealth mode (default)
    print("\n3. Without stealth mode (default):")
    print("-" * 80)
    
    try:
        result = await scraper_default.render(
            url="https://httpbin.org/html",
            wait_time=3,
            screenshot=False,
            use_stealth=False
        )
        print(f"✓ Successfully rendered page without stealth mode")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        print(f"  HTML length: {len(result['html'])} characters")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    # Example 4: Using environment variable
    print("\n4. Using environment variable:")
    print("-" * 80)
    print("Set SCRAPER_TOOL_USE_STEALTH=true in your environment to enable stealth mode globally")
    
    print("\n" + "=" * 80)
    print("Demo completed!")
    print("=" * 80)


async def demo_stealth_with_screenshot():
    """Demonstrate stealth mode with screenshot."""
    print("\n" + "=" * 80)
    print("ScraperTool Stealth Mode with Screenshot Demo")
    print("=" * 80)
    
    scraper = ScraperTool(config={"use_stealth": True})
    
    try:
        result = await scraper.render(
            url="https://httpbin.org/html",
            wait_time=3,
            screenshot=True,
            screenshot_path="./storage/scraper_stealth_screenshot.png",
            use_stealth=True
        )
        print(f"✓ Successfully rendered page with stealth mode and screenshot")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        print(f"  Screenshot saved to: {result['screenshot']}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")


if __name__ == "__main__":
    # Run the demos
    asyncio.run(demo_stealth_mode())
    asyncio.run(demo_stealth_with_screenshot())

