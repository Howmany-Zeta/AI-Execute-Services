"""
Image processing utilities for LLM vision support.

This module provides functions to handle images in various formats:
- Image URLs
- Base64-encoded images
- Local file paths
"""

import os
import base64
import mimetypes
from typing import Union, Optional, Dict, Any
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ImageContent:
    """Represents image content for LLM messages."""

    def __init__(
        self,
        source: str,
        mime_type: Optional[str] = None,
        detail: Optional[str] = None,
    ):
        """
        Initialize image content.

        Args:
            source: Image source - can be URL, base64 data URI, or file path
            mime_type: MIME type (e.g., 'image/jpeg', 'image/png'). Auto-detected if not provided.
            detail: Detail level for OpenAI API ('low', 'high', 'auto'). Defaults to 'auto'.
        """
        self.source = source
        self.mime_type = mime_type or self._detect_mime_type(source)
        self.detail = detail or "auto"

    def _detect_mime_type(self, source: str) -> str:
        """Detect MIME type from source."""
        # Check if it's a data URI
        if source.startswith("data:"):
            header = source.split(",")[0]
            mime_type = header.split(":")[1].split(";")[0]
            return mime_type

        # Check if it's a URL
        if source.startswith(("http://", "https://")):
            parsed = urlparse(source)
            mime_type, _ = mimetypes.guess_type(parsed.path)
            if mime_type and mime_type.startswith("image/"):
                return mime_type

        # Check if it's a file path
        if os.path.exists(source):
            mime_type, _ = mimetypes.guess_type(source)
            if mime_type and mime_type.startswith("image/"):
                return mime_type

        # Default to jpeg if cannot detect
        logger.warning(f"Could not detect MIME type for {source}, defaulting to image/jpeg")
        return "image/jpeg"

    def is_url(self) -> bool:
        """Check if source is a URL."""
        return self.source.startswith(("http://", "https://"))

    def is_base64(self) -> bool:
        """Check if source is a base64 data URI."""
        return self.source.startswith("data:")

    def is_file_path(self) -> bool:
        """Check if source is a local file path."""
        return os.path.exists(self.source) and not self.is_url() and not self.is_base64()

    def get_base64_data(self) -> str:
        """
        Get base64-encoded image data.

        Returns:
            Base64 string without data URI prefix
        """
        if self.is_base64():
            # Extract base64 data from data URI
            return self.source.split(",", 1)[1]
        elif self.is_file_path():
            # Read file and encode to base64
            with open(self.source, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        else:
            raise ValueError(f"Cannot get base64 data from URL: {self.source}. Use URL directly or download first.")

    def get_url(self) -> str:
        """
        Get image URL.

        Returns:
            URL string
        """
        if self.is_url():
            return self.source
        else:
            raise ValueError(f"Source is not a URL: {self.source}")


def parse_image_source(source: Union[str, Dict[str, Any]]) -> ImageContent:
    """
    Parse image source into ImageContent object.

    Args:
        source: Can be:
            - String URL (http://... or https://...)
            - String base64 data URI (data:image/...;base64,...)
            - String file path
            - Dict with 'url', 'data', or 'path' key

    Returns:
        ImageContent object
    """
    if isinstance(source, dict):
        # Handle dict format
        if "url" in source:
            return ImageContent(
                source=source["url"],
                mime_type=source.get("mime_type"),
                detail=source.get("detail"),
            )
        elif "data" in source:
            # Base64 data
            mime_type = source.get("mime_type", "image/jpeg")
            data = source["data"]
            if not data.startswith("data:"):
                data = f"data:{mime_type};base64,{data}"
            return ImageContent(
                source=data,
                mime_type=mime_type,
                detail=source.get("detail"),
            )
        elif "path" in source:
            return ImageContent(
                source=source["path"],
                mime_type=source.get("mime_type"),
                detail=source.get("detail"),
            )
        else:
            raise ValueError(f"Invalid image dict format: {source}")
    elif isinstance(source, str):
        return ImageContent(source=source)
    else:
        raise TypeError(f"Image source must be str or dict, got {type(source)}")


def validate_image_source(source: str) -> bool:
    """
    Validate that image source is accessible.

    Args:
        source: Image source (URL, base64, or file path)

    Returns:
        True if source is valid and accessible
    """
    try:
        img = ImageContent(source)
        if img.is_file_path():
            return os.path.exists(source) and os.path.isfile(source)
        elif img.is_url():
            # URL validation - just check format, not accessibility
            parsed = urlparse(source)
            return bool(parsed.scheme and parsed.netloc)
        elif img.is_base64():
            # Base64 validation - check format
            parts = source.split(",", 1)
            return len(parts) == 2 and parts[0].startswith("data:image/")
        return False
    except Exception:
        return False
