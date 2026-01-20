"""
Simplified schemas for Scraper Tool.

AI only needs to provide url and requirements - all other options are 
configured by developers via YAML/environment variables.
"""

from typing import Optional
from pydantic import BaseModel, Field


class FetchSchema(BaseModel):
    """
    Schema for the fetch operation - the only method AI needs to call.
    
    Attributes:
        url: The URL to fetch
        requirements: Optional description of what data to extract
    """
    url: str = Field(
        ...,
        description="The URL to fetch"
    )
    requirements: Optional[str] = Field(
        default=None,
        description="Description of what data to extract from the page (optional)"
    )


class ParseHtmlSchema(BaseModel):
    """Schema for HTML parsing operation."""
    html: str = Field(..., description="HTML content to parse")
    selector: str = Field(..., description="CSS selector or XPath expression")
    selector_type: str = Field(default="css", description="Selector type: 'css' or 'xpath'")


__all__ = [
    "FetchSchema",
    "ParseHtmlSchema",
]

