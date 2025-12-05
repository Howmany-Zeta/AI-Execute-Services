import os
import json
import time
import logging
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Union
import csv
from enum import Enum

import httpx
from bs4 import BeautifulSoup
from urllib import request as urllib_request
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool

# Enums for configuration options


class HttpMethod(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"
    HEAD = "head"
    OPTIONS = "options"
    PATCH = "patch"


class ContentType(str, Enum):
    HTML = "html"
    JSON = "json"
    TEXT = "text"
    BINARY = "binary"


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"


class RenderEngine(str, Enum):
    NONE = "none"
    PLAYWRIGHT = "playwright"


# Exceptions
class ScraperToolError(Exception):
    """Base exception for ScraperTool errors."""


class HttpError(ScraperToolError):
    """Raised when HTTP requests fail."""


class TimeoutError(ScraperToolError):
    """Raised when operations time out."""


class RateLimitError(ScraperToolError):
    """Raised when rate limits are exceeded."""


class ParsingError(ScraperToolError):
    """Raised when HTML parsing fails."""


class RenderingError(ScraperToolError):
    """Raised when rendering fails."""


class ExternalToolError(ScraperToolError):
    """Raised when external tools fail."""


class FileOperationError(ScraperToolError):
    """Raised when file operations fail."""


@register_tool("scraper")
class ScraperTool(BaseTool):
    """
    Enhanced web scraping tool with multiple HTTP clients, JavaScript rendering,
    HTML parsing, and security features.

    Features:
    - Multiple HTTP clients: httpx, urllib
    - JavaScript rendering with Playwright or Selenium
    - HTML parsing with BeautifulSoup
    - Scrapy integration for advanced crawling
    - Output in various formats: text, JSON, HTML, Markdown, CSV
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the scraper tool
        
        Automatically reads from environment variables with SCRAPER_TOOL_ prefix.
        Example: SCRAPER_TOOL_USER_AGENT -> user_agent
        """

        model_config = SettingsConfigDict(env_prefix="SCRAPER_TOOL_")

        user_agent: str = Field(
            default="PythonMiddlewareScraper/2.0",
            description="User agent for HTTP requests",
        )
        max_content_length: int = Field(
            default=10 * 1024 * 1024,
            description="Maximum content length in bytes",
        )
        output_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "scraper_outputs"),
            description="Directory for output files",
        )
        scrapy_command: str = Field(default="scrapy", description="Command to run Scrapy")
        allowed_domains: List[str] = Field(default=[], description="Allowed domains for scraping")
        blocked_domains: List[str] = Field(default=[], description="Blocked domains for scraping")
        playwright_available: bool = Field(
            default=False,
            description="Whether Playwright is available (auto-detected)",
        )

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """
        Initialize ScraperTool with settings and resources.

        Args:
            config (Dict, optional): Configuration overrides for ScraperTool.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Raises:
            ValueError: If config contains invalid settings.

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/scraper.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        os.makedirs(self.config.output_dir, exist_ok=True)
        self._check_external_tools()

    def _check_external_tools(self):
        """Check if external tools are available."""
        try:
            self.config.playwright_available = True
        except ImportError:
            self.config.playwright_available = False

    async def _save_output(self, content: Any, path: str, format: OutputFormat) -> None:
        """Save content to file in the specified format."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            if format == OutputFormat.TEXT:
                with open(path, "w", encoding="utf-8") as f:
                    if isinstance(content, dict):
                        f.write(json.dumps(content, indent=2))
                    else:
                        f.write(str(content))
            elif format == OutputFormat.JSON:
                with open(path, "w", encoding="utf-8") as f:
                    if isinstance(content, dict):
                        json.dump(content, f, indent=2)
                    else:
                        json.dump({"content": content}, f, indent=2)
            elif format == OutputFormat.HTML:
                with open(path, "w", encoding="utf-8") as f:
                    if isinstance(content, dict) and "html" in content:
                        f.write(content["html"])
                    else:
                        f.write(str(content))
            elif format == OutputFormat.MARKDOWN:
                with open(path, "w", encoding="utf-8") as f:
                    if isinstance(content, dict):
                        f.write("# Scraper Results\n\n")
                        for key, value in content.items():
                            f.write(f"## {key}\n\n")
                            f.write(f"{value}\n\n")
                    else:
                        f.write("# Scraper Results\n\n")
                        f.write(str(content))
            elif format == OutputFormat.CSV:
                import csv

                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer: Union[Any, Any]  # csv.writer or csv.DictWriter instance
                    if isinstance(content, dict):
                        writer = csv.writer(f)
                        writer.writerow(content.keys())
                        writer.writerow(content.values())
                    elif isinstance(content, list) and all(isinstance(item, dict) for item in content):
                        if content:
                            writer = csv.DictWriter(f, fieldnames=content[0].keys())
                            writer.writeheader()
                            writer.writerows(content)
                    else:
                        writer = csv.writer(f)
                        writer.writerow(["content"])
                        writer.writerow([str(content)])
        except Exception as e:
            raise FileOperationError(f"Error saving output: {str(e)}")

    async def get_httpx(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        verify_ssl: Optional[bool] = None,
        allow_redirects: bool = True,
        content_type: ContentType = ContentType.TEXT,
        headers: Optional[Dict[str, str]] = None,
        output_format: Optional[OutputFormat] = None,
        output_path: Optional[str] = None,
        async_mode: bool = True,
    ) -> Any:
        """
        Execute HTTP request using httpx library (supports both sync and async).

        Args:
            url (str): URL to scrape.
            method (HttpMethod): HTTP method to use.
            params (Optional[Dict[str, str]]): Query parameters.
            data (Optional[Dict[str, Any]]): Form data.
            json_data (Optional[Dict[str, Any]]): JSON data.
            cookies (Optional[Dict[str, str]]): Cookies.
            auth (Optional[Tuple[str, str]]): Authentication credentials.
            verify_ssl (Optional[bool]): Verify SSL certificates.
            allow_redirects (bool): Allow redirects.
            content_type (ContentType): Expected content type.
            headers (Optional[Dict[str, str]]): Custom headers.
            output_format (Optional[OutputFormat]): Output format.
            output_path (Optional[str]): Path to save output.
            async_mode (bool): Whether to use async client.

        Returns:
            Any: Scraped content (dict, str, or bytes).

        Raises:
            HttpError: If the request fails.
        """
        try:
            headers = headers or {}
            if "User-Agent" not in headers:
                headers["User-Agent"] = self.config.user_agent
            kwargs: Dict[str, Any] = {
                "params": params,
                "headers": headers,
                "follow_redirects": allow_redirects,
            }
            if auth:
                kwargs["auth"] = auth  # httpx accepts Tuple[str, str] for auth
            if cookies:
                kwargs["cookies"] = cookies
            if json_data:
                kwargs["json"] = json_data
            elif data:
                kwargs["data"] = data

            if async_mode:
                async with httpx.AsyncClient(verify=verify_ssl if verify_ssl is not None else True) as client:
                    method_fn = getattr(client, method.value)
                    resp = await method_fn(str(url), **kwargs)
            else:
                with httpx.Client(verify=verify_ssl if verify_ssl is not None else True) as client:
                    method_fn = getattr(client, method.value)
                    resp = method_fn(str(url), **kwargs)

            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise HttpError(f"HTTP {e.response.status_code}: {e.response.reason_phrase} for {url}")

            if len(resp.content) > self.config.max_content_length:
                raise HttpError(f"Response content too large: {len(resp.content)} bytes")

            if content_type == ContentType.JSON:
                result = resp.json()
            elif content_type == ContentType.HTML:
                result = {
                    "html": resp.text,
                    "url": str(resp.url),
                    "status": resp.status_code,
                }
            elif content_type == ContentType.BINARY:
                result = {
                    "content": resp.content,
                    "url": str(resp.url),
                    "status": resp.status_code,
                }
            else:
                result = resp.text

            if output_format and output_path:
                await self._save_output(result, output_path, output_format)
                if isinstance(result, dict):
                    result["saved_to"] = output_path
                else:
                    result = {"content": result, "saved_to": output_path}
            return result
        except httpx.RequestError as e:
            raise HttpError(f"Request failed: {str(e)}")

    async def get_urllib(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        data: Optional[Dict[str, Any]] = None,
        content_type: ContentType = ContentType.TEXT,
        headers: Optional[Dict[str, str]] = None,
        output_format: Optional[OutputFormat] = None,
        output_path: Optional[str] = None,
    ) -> Any:
        """
        Execute HTTP request using urllib.

        Args:
            url (str): URL to scrape.
            method (HttpMethod): HTTP method to use.
            data (Optional[Dict[str, Any]]): Form data.
            content_type (ContentType): Expected content type.
            headers (Optional[Dict[str, str]]): Custom headers.
            output_format (Optional[OutputFormat]): Output format.
            output_path (Optional[str]): Path to save output.

        Returns:
            Any: Scraped content (dict, str, or bytes).

        Raises:
            HttpError: If the request fails.
        """
        try:
            import urllib.parse
            import urllib.error

            headers = headers or {}
            if "User-Agent" not in headers:
                headers["User-Agent"] = self.config.user_agent
            data_bytes = None
            if data:
                data_bytes = urllib.parse.urlencode(data).encode()
            req = urllib_request.Request(
                str(url),
                data=data_bytes,
                headers=headers,
                method=method.value.upper(),
            )
            with urllib_request.urlopen(req) as resp:
                content_length = resp.getheader("Content-Length")
                if content_length and int(content_length) > self.config.max_content_length:
                    raise HttpError(f"Response content too large: {content_length} bytes")
                content = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                if content_type == ContentType.JSON:
                    result = json.loads(content.decode(charset, errors="ignore"))
                elif content_type == ContentType.HTML:
                    result = {
                        "html": content.decode(charset, errors="ignore"),
                        "url": resp.url,
                        "status": resp.status,
                    }
                elif content_type == ContentType.BINARY:
                    result = {
                        "content": content,
                        "url": resp.url,
                        "status": resp.status,
                    }
                else:
                    result = content.decode(charset, errors="ignore")
                if output_format and output_path:
                    await self._save_output(result, output_path, output_format)
                    if isinstance(result, dict):
                        result["saved_to"] = output_path
                    else:
                        result = {"content": result, "saved_to": output_path}
                return result
        except urllib.error.URLError as e:
            raise HttpError(f"Request failed: {str(e)}")

    # Legacy method names for backward compatibility
    async def get_requests(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        verify_ssl: Optional[bool] = None,
        allow_redirects: bool = True,
        content_type: ContentType = ContentType.TEXT,
        headers: Optional[Dict[str, str]] = None,
        output_format: Optional[OutputFormat] = None,
        output_path: Optional[str] = None,
    ) -> Any:
        """Legacy method - now uses httpx in sync mode."""
        return await self.get_httpx(
            url,
            method,
            params,
            data,
            json_data,
            cookies,
            auth,
            verify_ssl,
            allow_redirects,
            content_type,
            headers,
            output_format,
            output_path,
            async_mode=False,
        )

    async def get_aiohttp(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        verify_ssl: Optional[bool] = None,
        allow_redirects: bool = True,
        content_type: ContentType = ContentType.TEXT,
        headers: Optional[Dict[str, str]] = None,
        output_format: Optional[OutputFormat] = None,
        output_path: Optional[str] = None,
    ) -> Any:
        """Legacy method - now uses httpx in async mode."""
        return await self.get_httpx(
            url,
            method,
            params,
            data,
            json_data,
            cookies,
            auth,
            verify_ssl,
            allow_redirects,
            content_type,
            headers,
            output_format,
            output_path,
            async_mode=True,
        )

    async def render(
        self,
        url: str,
        engine: RenderEngine = RenderEngine.PLAYWRIGHT,
        wait_time: int = 5,
        wait_selector: Optional[str] = None,
        scroll_to_bottom: bool = False,
        screenshot: bool = False,
        screenshot_path: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        output_format: Optional[OutputFormat] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Render a web page using a headless browser (Playwright).

        Args:
            url (str): URL to render.
            engine (RenderEngine): Rendering engine to use (only PLAYWRIGHT supported).
            wait_time (int): Time to wait for JS execution.
            wait_selector (Optional[str]): CSS selector to wait for.
            scroll_to_bottom (bool): Whether to scroll to the bottom of the page.
            screenshot (bool): Whether to take a screenshot.
            screenshot_path (Optional[str]): Path to save the screenshot.
            headers (Optional[Dict[str, str]]): Custom headers.
            output_format (Optional[OutputFormat]): Output format.
            output_path (Optional[str]): Path to save output.

        Returns:
            Dict[str, Any]: Rendered page content {'html': str, 'title': str, 'url': str, 'screenshot': Optional[str]}.

        Raises:
            RenderingError: If rendering fails.
        """
        try:
            if engine == RenderEngine.PLAYWRIGHT:
                if not self.config.playwright_available:
                    raise RenderingError("Playwright is not available. Install with 'pip install playwright'")
                result = await self._render_with_playwright(
                    url,
                    wait_time,
                    wait_selector,
                    scroll_to_bottom,
                    screenshot,
                    screenshot_path,
                )
            else:
                raise RenderingError(f"Unsupported rendering engine: {engine}. Only PLAYWRIGHT is supported.")
            if output_format and output_path:
                await self._save_output(result, output_path, output_format)
                result["saved_to"] = output_path
            return result
        except Exception as e:
            raise RenderingError(f"Failed to render page: {str(e)}")

    async def _render_with_playwright(
        self,
        url: str,
        wait_time: int,
        wait_selector: Optional[str],
        scroll_to_bottom: bool,
        screenshot: bool,
        screenshot_path: Optional[str],
    ) -> Dict[str, Any]:
        """Render a web page using Playwright with async API."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(
                user_agent=self.config.user_agent,
                viewport={"width": 1280, "height": 800},
            )
            try:
                await page.goto(url)
                if wait_selector:
                    await page.wait_for_selector(wait_selector)
                else:
                    await page.wait_for_load_state("networkidle")
                if scroll_to_bottom:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)
                screenshot_result = None
                if screenshot:
                    screenshot_path = screenshot_path or os.path.join(
                        self.config.output_dir,
                        f"screenshot_{int(time.time())}.png",
                    )
                    os.makedirs(
                        os.path.dirname(os.path.abspath(screenshot_path)),
                        exist_ok=True,
                    )
                    await page.screenshot(path=screenshot_path)
                    screenshot_result = screenshot_path
                html = await page.content()
                title = await page.title()
                result = {
                    "html": html,
                    "title": title,
                    "url": page.url,
                    "screenshot": screenshot_result,
                }
                return result
            finally:
                await browser.close()

    def crawl_scrapy(
        self,
        project_path: str,
        spider_name: str,
        output_path: str,
        spider_args: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        output_format: Optional[OutputFormat] = None,
    ) -> Dict[str, Any]:
        """
        Execute a Scrapy spider in an existing project and output results to a file.

        Args:
            project_path (str): Path to the Scrapy project.
            spider_name (str): Name of the spider to run.
            output_path (str): Path to save the output.
            spider_args (Optional[Dict[str, str]]): Arguments to pass to the spider.
            headers (Optional[Dict[str, str]]): Custom headers.
            output_format (Optional[OutputFormat]): Output format.

        Returns:
            Dict[str, Any]: Crawl results {'output_path': str, 'execution_time': float, 'file_size': int, 'stdout': str, 'stderr': str}.

        Raises:
            ExternalToolError: If Scrapy fails.
            TimeoutError: If the operation times out.
        """
        try:
            start_time = time.time()
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            cmd = [
                self.config.scrapy_command,
                "crawl",
                spider_name,
                "-o",
                output_path,
                "-s",
                f"USER_AGENT={self.config.user_agent}",
                "-s",
                "LOG_LEVEL=INFO",
            ]
            if spider_args:
                for k, v in spider_args.items():
                    cmd += ["-a", f"{k}={v}"]
            process = subprocess.run(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if process.returncode != 0:
                error_msg = process.stderr.strip()
                raise ExternalToolError(f"Scrapy crawl failed: {error_msg}")
            if not os.path.exists(output_path):
                raise ExternalToolError(f"Scrapy crawl did not create output file: {output_path}")
            file_size = os.path.getsize(output_path)
            result = {
                "output_path": output_path,
                "execution_time": time.time() - start_time,
                "file_size": file_size,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
            }
            return result
        except subprocess.TimeoutExpired:
            raise TimeoutError("Scrapy crawl timed out")
        except Exception as e:
            raise ExternalToolError(f"Error running Scrapy: {str(e)}")

    def parse_html(
        self,
        html: str,
        selector: str,
        selector_type: str = "css",
        extract_attr: Optional[str] = None,
        extract_text: bool = True,
    ) -> Dict[str, Any]:
        """
        Parse HTML content using BeautifulSoup.

        Args:
            html (str): HTML content to parse.
            selector (str): CSS or XPath selector.
            selector_type (str): Selector type ('css' or 'xpath').
            extract_attr (Optional[str]): Attribute to extract.
            extract_text (bool): Whether to extract text content.

        Returns:
            Dict[str, Any]: Parsed results {'selector': str, 'selector_type': str, 'count': int, 'results': List[str]}.

        Raises:
            ParsingError: If parsing fails.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            if selector_type == "css":
                elements = soup.select(selector)
            else:
                from lxml.html import fromstring
                from lxml.etree import XPath

                root = fromstring(html)
                xpath = XPath(selector)
                elements = xpath(root)
            results = []
            for element in elements:
                if extract_attr:
                    value = element.get(extract_attr) if hasattr(element, "get") else element.get(extract_attr)
                    if value is not None:
                        results.append(value)
                elif extract_text:
                    if hasattr(element, "text_content") and callable(getattr(element, "text_content")):
                        # lxml element
                        text = element.text_content()  # type: ignore[misc]
                    else:
                        # BeautifulSoup element
                        text = element.get_text()  # type: ignore[misc]

                    if text and text.strip():  # type: ignore[misc]
                        results.append(text.strip())  # type: ignore[misc]
            return {
                "selector": selector,
                "selector_type": selector_type,
                "count": len(results),
                "results": results,
            }
        except Exception as e:
            raise ParsingError(f"Error parsing HTML: {str(e)}")

    # HTTP method shortcuts
    get = get_httpx
    post = get_httpx
    put = get_httpx
    delete = get_httpx
    head = get_httpx
    options = get_httpx
    patch = get_httpx
