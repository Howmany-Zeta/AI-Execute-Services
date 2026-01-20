"""
HTML and JSON parsing utilities for Scraper Tool.
"""

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .constants import ParsingError

# Try to use lxml for better performance
try:
    import lxml  # noqa: F401
    DEFAULT_PARSER = "lxml"
except ImportError:
    DEFAULT_PARSER = "html.parser"


class HtmlParser:
    """HTML parsing utilities using BeautifulSoup."""

    def __init__(self):
        self.parser = DEFAULT_PARSER

    def parse(self, html: str) -> BeautifulSoup:
        """Parse HTML string into BeautifulSoup object."""
        try:
            return BeautifulSoup(html, self.parser)
        except Exception as e:
            raise ParsingError(f"Failed to parse HTML: {e}")

    def select(self, html: str, selector: str, selector_type: str = "css") -> List:
        """Select elements using CSS or XPath selector."""
        soup = self.parse(html)
        try:
            if selector_type == "css":
                return soup.select(selector)
            elif selector_type == "xpath":
                # BeautifulSoup doesn't support XPath natively
                raise ParsingError("XPath requires lxml; use CSS selectors instead")
            else:
                raise ParsingError(f"Unknown selector type: {selector_type}")
        except Exception as e:
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(f"Selection failed: {e}")

    def extract_text(self, html: str) -> str:
        """Extract all text content from HTML."""
        soup = self.parse(html)
        # Remove script and style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Normalize whitespace
        return re.sub(r"\s+", " ", text).strip()

    def extract_links(self, html: str, base_url: Optional[str] = None) -> List[Dict]:
        """Extract all links from HTML."""
        soup = self.parse(html)
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if base_url:
                href = urljoin(base_url, href)
            links.append({
                "url": href,
                "text": a.get_text(strip=True),
                "title": a.get("title", ""),
            })
        return links

    def extract_metadata(self, html: str) -> Dict:
        """Extract metadata: title, description, Open Graph tags."""
        soup = self.parse(html)
        metadata = {"title": "", "description": "", "og": {}}

        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        # Meta description
        desc = soup.find("meta", attrs={"name": "description"})
        if desc and desc.get("content"):
            metadata["description"] = desc["content"]

        # Open Graph tags
        for og in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
            prop = og.get("property", "").replace("og:", "")
            if prop and og.get("content"):
                metadata["og"][prop] = og["content"]

        return metadata

    def html_to_markdown(self, html: str) -> str:
        """Convert HTML to simple markdown."""
        soup = self.parse(html)
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        lines = []
        for elem in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "a"]):
            text = elem.get_text(strip=True)
            if not text:
                continue
            if elem.name == "h1":
                lines.append(f"# {text}")
            elif elem.name == "h2":
                lines.append(f"## {text}")
            elif elem.name == "h3":
                lines.append(f"### {text}")
            elif elem.name in ("h4", "h5", "h6"):
                lines.append(f"#### {text}")
            elif elem.name == "li":
                lines.append(f"- {text}")
            elif elem.name == "a" and elem.get("href"):
                lines.append(f"[{text}]({elem['href']})")
            elif elem.name == "p":
                lines.append(text)
        return "\n\n".join(lines)


class JsonParser:
    """JSON parsing utilities with simple path queries."""

    def parse(self, content: str) -> Any:
        """Parse JSON string."""
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ParsingError(f"Invalid JSON: {e}")

    def query(self, data: Any, path: str) -> Any:
        """Query data using simple JSONPath-like syntax ($.key.subkey or $.arr[0])."""
        if not path.startswith("$"):
            raise ParsingError("Path must start with '$'")

        path = path[1:]  # Remove leading $
        if not path:
            return data

        result = data
        # Split by . but handle array indices
        parts = re.split(r"\.(?![^\[]*\])", path.lstrip("."))

        for part in parts:
            if not part:
                continue
            # Handle array index: key[0]
            match = re.match(r"^(\w+)\[(\d+)\]$", part)
            if match:
                key, idx = match.group(1), int(match.group(2))
                if isinstance(result, dict) and key in result:
                    result = result[key]
                    if isinstance(result, list) and 0 <= idx < len(result):
                        result = result[idx]
                    else:
                        return None
                else:
                    return None
            elif isinstance(result, dict) and part in result:
                result = result[part]
            else:
                return None
        return result

