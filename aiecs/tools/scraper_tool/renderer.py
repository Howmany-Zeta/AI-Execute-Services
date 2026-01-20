"""
JavaScript rendering with Playwright and stealth mode.
"""

import asyncio
import random
import logging
from typing import Any, Dict, Optional

from .constants import RenderingError

logger = logging.getLogger(__name__)

# Check if playwright is available
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None

# Check if playwright-stealth is available
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    stealth_async = None


# Common viewport sizes for randomization
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

# Common timezones
TIMEZONES = [
    "America/New_York",
    "America/Los_Angeles", 
    "Europe/London",
    "Europe/Berlin",
    "Asia/Tokyo",
]


class PlaywrightRenderer:
    """JavaScript page renderer with stealth capabilities."""
    
    def __init__(
        self,
        headless: bool = True,
        use_stealth: bool = True,
        randomize_viewport: bool = True,
    ):
        if not PLAYWRIGHT_AVAILABLE:
            raise RenderingError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        self.headless = headless
        self.use_stealth = use_stealth
        self.randomize_viewport = randomize_viewport
        self._browser = None
        self._playwright = None
    
    async def _ensure_browser(self):
        """Ensure browser is started."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
    
    async def render(
        self,
        url: str,
        wait_time: int = 3,
        wait_selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Render a page with JavaScript.
        
        Returns:
            {"html": str, "title": str, "url": str}
        """
        await self._ensure_browser()
        
        # Random viewport and timezone
        viewport = random.choice(VIEWPORTS) if self.randomize_viewport else VIEWPORTS[0]
        timezone = random.choice(TIMEZONES)
        
        context = await self._browser.new_context(
            viewport=viewport,
            timezone_id=timezone,
            locale="en-US",
        )
        
        page = await context.new_page()
        
        try:
            # Apply stealth if available
            if self.use_stealth and STEALTH_AVAILABLE:
                await stealth_async(page)
            elif self.use_stealth:
                await self._apply_manual_stealth(page)
            
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for selector or time
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=wait_time * 1000)
            else:
                await asyncio.sleep(wait_time)
            
            html = await page.content()
            title = await page.title()
            final_url = page.url
            
            return {
                "html": html,
                "title": title,
                "url": final_url,
            }
        except Exception as e:
            raise RenderingError(f"Failed to render {url}: {e}")
        finally:
            await context.close()
    
    async def _apply_manual_stealth(self, page):
        """Apply manual stealth evasions when playwright-stealth is not available."""
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        """)
    
    async def close(self):
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


__all__ = ["PlaywrightRenderer", "PLAYWRIGHT_AVAILABLE"]

