"""
ScraperTool - Simplified web scraper for AI agents.

AI only needs to call: fetch(url, requirements)
All other settings are configured via environment variables.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool

from .constants import (
    ScraperToolError,
    HttpError,
    BlockedError,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
)
from .schemas import FetchSchema
from .rate_limiter import AdaptiveRateLimiter, DomainCircuitBreaker
from .cache import ScraperCache, ContentDeduplicator
from .error_handler import ErrorHandler
from .parser import HtmlParser, JsonParser
from .renderer import PlaywrightRenderer, PLAYWRIGHT_AVAILABLE

logger = logging.getLogger(__name__)

# Check if curl_cffi is available
try:
    from curl_cffi import requests as curl_requests
    from curl_cffi.requests import AsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    curl_requests = None
    AsyncSession = None


class ScraperToolConfig(BaseSettings):
    """Configuration loaded from environment variables."""
    
    model_config = SettingsConfigDict(env_prefix="SCRAPER_TOOL_")
    
    # HTTP settings
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Max retry attempts")
    impersonate: str = Field(default="chrome120", description="Browser to impersonate (curl_cffi)")
    proxy: Optional[str] = Field(default=None, description="Proxy URL")
    
    # Rate limiting
    requests_per_minute: int = Field(default=30, description="Max requests per minute per domain")
    circuit_breaker_threshold: int = Field(default=5, description="Failures before circuit opens")
    
    # Caching
    enable_cache: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=3600, description="Default cache TTL in seconds")
    redis_url: Optional[str] = Field(default=None, description="Redis URL for distributed cache")
    
    # JS Rendering
    enable_js_render: bool = Field(default=False, description="Enable Playwright for JS pages")
    use_stealth: bool = Field(default=True, description="Use stealth mode for rendering")


@register_tool("scraper")
class ScraperTool(BaseTool):
    """
    Simplified web scraper for AI agents.
    
    AI only needs to call fetch(url, requirements) - all other settings
    are configured by developers via environment variables.
    """
    
    Config = ScraperToolConfig
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load config
        self.config = ScraperToolConfig()
        
        # Initialize components
        self.rate_limiter = AdaptiveRateLimiter(self.config.requests_per_minute)
        self.circuit_breaker = DomainCircuitBreaker(
            failure_threshold=self.config.circuit_breaker_threshold
        )
        self.cache = ScraperCache(
            default_ttl=self.config.cache_ttl,
            redis_url=self.config.redis_url,
        ) if self.config.enable_cache else None
        self.deduplicator = ContentDeduplicator()
        self.error_handler = ErrorHandler()
        self.html_parser = HtmlParser()
        self.json_parser = JsonParser()
        self.renderer = None  # Lazy init
        
        # curl_cffi session
        self._session = None
    
    async def fetch(self, url: str, requirements: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch a webpage and optionally extract data.
        
        This is the main method AI should call.
        
        Args:
            url: The URL to fetch
            requirements: Optional description of what data to extract
            
        Returns:
            {
                "success": bool,
                "url": str,
                "title": str,
                "content": str,  # HTML or text
                "extracted_data": dict,  # If requirements provided
                "cached": bool,
                "error": dict  # If failed
            }
        """
        domain = urlparse(url).netloc
        
        try:
            # Check circuit breaker
            if not self.circuit_breaker.is_domain_available(domain):
                raise BlockedError(f"Domain {domain} is temporarily unavailable (circuit open)")
            
            # Check cache
            if self.cache:
                cached = await self.cache.get(url)
                if cached:
                    logger.debug(f"Cache hit for {url}")
                    return {**cached, "cached": True}
            
            # Rate limiting
            wait_time = self.rate_limiter.wait_time(domain)
            if wait_time > 0:
                logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            self.rate_limiter.acquire(domain)
            
            # Fetch content
            if self.config.enable_js_render:
                result = await self._fetch_with_js(url)
            else:
                result = await self._fetch_with_curl(url)
            
            # Parse and extract
            result["extracted_data"] = {}
            if requirements:
                result["extracted_data"] = self._extract_data(result["content"], requirements)
            
            # Cache result
            if self.cache:
                await self.cache.set(url, result)
            
            # Record success
            self.rate_limiter.on_success(domain)
            self.circuit_breaker.get_breaker(domain).record_success()
            
            return {**result, "success": True, "cached": False}
            
        except Exception as e:
            # Record failure
            if isinstance(e, (HttpError, BlockedError)):
                self.circuit_breaker.get_breaker(domain).record_failure()
                self.rate_limiter.on_error(domain)
            
            error_info = self.error_handler.format_error(e, {"url": url})
            return {
                "success": False,
                "url": url,
                "error": error_info,
                "cached": False,
            }

    async def _fetch_with_curl(self, url: str) -> Dict[str, Any]:
        """Fetch using curl_cffi with TLS fingerprint simulation."""
        if not CURL_CFFI_AVAILABLE:
            # Fallback to httpx if curl_cffi not available
            import httpx
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return {
                    "url": str(resp.url),
                    "title": "",
                    "content": resp.text,
                    "status_code": resp.status_code,
                }

        async with AsyncSession() as session:
            resp = await session.get(
                url,
                impersonate=self.config.impersonate,
                timeout=self.config.timeout,
                proxy=self.config.proxy,
            )

            if resp.status_code >= 400:
                raise HttpError(f"HTTP {resp.status_code}", status_code=resp.status_code)

            html = resp.text
            metadata = self.html_parser.extract_metadata(html)

            return {
                "url": str(resp.url),
                "title": metadata.get("title", ""),
                "content": html,
                "status_code": resp.status_code,
            }

    async def _fetch_with_js(self, url: str) -> Dict[str, Any]:
        """Fetch using Playwright for JavaScript-rendered pages."""
        if self.renderer is None:
            self.renderer = PlaywrightRenderer(
                use_stealth=self.config.use_stealth,
            )

        result = await self.renderer.render(url)
        return {
            "url": result["url"],
            "title": result["title"],
            "content": result["html"],
            "status_code": 200,
        }

    def _extract_data(self, html: str, requirements: str) -> Dict[str, Any]:
        """Extract data based on requirements (basic implementation)."""
        # Basic extraction - can be enhanced with LLM
        metadata = self.html_parser.extract_metadata(html)
        text = self.html_parser.extract_text(html)
        links = self.html_parser.extract_links(html)

        return {
            "metadata": metadata,
            "text_preview": text[:1000] if text else "",
            "links_count": len(links),
            "requirements": requirements,
        }

    async def close(self) -> None:
        """Clean up resources."""
        if self.renderer:
            await self.renderer.close()


__all__ = ["ScraperTool", "ScraperToolConfig"]

