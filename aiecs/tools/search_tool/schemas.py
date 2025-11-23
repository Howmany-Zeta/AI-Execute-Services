"""
Pydantic Schema Definitions for SearchTool Operations

Provides input validation, type safety, and automatic documentation
for all SearchTool operations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class SearchWebSchema(BaseModel):
    """Schema for search_web operation"""

    query: str = Field(description="Search query string")
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results to return (1-100)",
    )
    start_index: int = Field(
        default=1,
        ge=1,
        le=91,
        description="Starting index for pagination (1-91)",
    )
    language: str = Field(
        default="en",
        description="Language code for results (e.g., 'en', 'zh-CN', 'es')",
    )
    country: str = Field(
        default="us",
        description="Country code for geolocation (e.g., 'us', 'cn', 'uk')",
    )
    safe_search: str = Field(
        default="medium",
        description="Safe search level: 'off', 'medium', or 'high'",
    )
    date_restrict: Optional[str] = Field(
        default=None,
        description="Date restriction (e.g., 'd7' for last 7 days, 'm3' for last 3 months)",
    )
    file_type: Optional[str] = Field(
        default=None,
        description="File type filter (e.g., 'pdf', 'doc', 'xls')",
    )
    exclude_terms: Optional[List[str]] = Field(default=None, description="Terms to exclude from search results")
    auto_enhance: bool = Field(
        default=True,
        description="Whether to automatically enhance query based on detected intent",
    )
    return_summary: bool = Field(
        default=False,
        description="Whether to return a structured summary of results",
    )

    @field_validator("safe_search")
    @classmethod
    def validate_safe_search(cls, v: str) -> str:
        """Validate safe search level"""
        allowed = ["off", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"safe_search must be one of {allowed}")
        return v


class SearchImagesSchema(BaseModel):
    """Schema for search_images operation"""

    query: str = Field(description="Image search query string")
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of image results to return (1-100)",
    )
    image_size: Optional[str] = Field(
        default=None,
        description="Image size filter: 'icon', 'small', 'medium', 'large', 'xlarge', 'xxlarge', 'huge'",
    )
    image_type: Optional[str] = Field(
        default=None,
        description="Image type filter: 'clipart', 'face', 'lineart', 'stock', 'photo', 'animated'",
    )
    image_color_type: Optional[str] = Field(
        default=None,
        description="Color type filter: 'color', 'gray', 'mono', 'trans'",
    )
    safe_search: str = Field(
        default="medium",
        description="Safe search level: 'off', 'medium', or 'high'",
    )

    @field_validator("safe_search")
    @classmethod
    def validate_safe_search(cls, v: str) -> str:
        """Validate safe search level"""
        allowed = ["off", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"safe_search must be one of {allowed}")
        return v


class SearchNewsSchema(BaseModel):
    """Schema for search_news operation"""

    query: str = Field(description="News search query string")
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of news results to return (1-100)",
    )
    start_index: int = Field(
        default=1,
        ge=1,
        le=91,
        description="Starting index for pagination (1-91)",
    )
    language: str = Field(
        default="en",
        description="Language code for news articles (e.g., 'en', 'zh-CN', 'es')",
    )
    date_restrict: Optional[str] = Field(
        default=None,
        description="Date restriction (e.g., 'd7' for last 7 days, 'm1' for last month)",
    )
    sort_by: str = Field(
        default="date",
        description="Sort order: 'date' for newest first, 'relevance' for most relevant",
    )

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort order"""
        allowed = ["date", "relevance"]
        if v not in allowed:
            raise ValueError(f"sort_by must be one of {allowed}")
        return v


class SearchVideosSchema(BaseModel):
    """Schema for search_videos operation"""

    query: str = Field(description="Video search query string")
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of video results to return (1-100)",
    )
    start_index: int = Field(
        default=1,
        ge=1,
        le=91,
        description="Starting index for pagination (1-91)",
    )
    language: str = Field(
        default="en",
        description="Language code for videos (e.g., 'en', 'zh-CN', 'es')",
    )
    safe_search: str = Field(
        default="medium",
        description="Safe search level: 'off', 'medium', or 'high'",
    )

    @field_validator("safe_search")
    @classmethod
    def validate_safe_search(cls, v: str) -> str:
        """Validate safe search level"""
        allowed = ["off", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"safe_search must be one of {allowed}")
        return v


class SearchPaginatedSchema(BaseModel):
    """Schema for search_paginated operation"""

    query: str = Field(description="Search query string")
    total_results: int = Field(
        ge=1,
        le=1000,
        description="Total number of results to retrieve (1-1000)",
    )
    search_type: str = Field(
        default="web",
        description="Type of search: 'web', 'images', 'news', or 'videos'",
    )

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, v: str) -> str:
        """Validate search type"""
        allowed = ["web", "images", "news", "videos"]
        if v not in allowed:
            raise ValueError(f"search_type must be one of {allowed}")
        return v


class SearchBatchSchema(BaseModel):
    """Schema for search_batch operation"""

    queries: List[str] = Field(description="List of search queries to execute in batch")
    search_type: str = Field(
        default="web",
        description="Type of search: 'web', 'images', 'news', or 'videos'",
    )
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results per query (1-100)",
    )

    @field_validator("queries")
    @classmethod
    def validate_queries(cls, v: List[str]) -> List[str]:
        """Validate queries list"""
        if not v:
            raise ValueError("queries list cannot be empty")
        if len(v) > 50:
            raise ValueError("Maximum 50 queries allowed in batch")
        return v

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, v: str) -> str:
        """Validate search type"""
        allowed = ["web", "images", "news", "videos"]
        if v not in allowed:
            raise ValueError(f"search_type must be one of {allowed}")
        return v


class ValidateCredentialsSchema(BaseModel):
    """Schema for validate_credentials operation (no parameters required)"""


class GetQuotaStatusSchema(BaseModel):
    """Schema for get_quota_status operation (no parameters required)"""


class GetMetricsSchema(BaseModel):
    """Schema for get_metrics operation (no parameters required)"""


class GetMetricsReportSchema(BaseModel):
    """Schema for get_metrics_report operation (no parameters required)"""


class GetHealthScoreSchema(BaseModel):
    """Schema for get_health_score operation (no parameters required)"""


class GetSearchContextSchema(BaseModel):
    """Schema for get_search_context operation (no parameters required)"""


__all__ = [
    "SearchWebSchema",
    "SearchImagesSchema",
    "SearchNewsSchema",
    "SearchVideosSchema",
    "SearchPaginatedSchema",
    "SearchBatchSchema",
    "ValidateCredentialsSchema",
    "GetQuotaStatusSchema",
    "GetMetricsSchema",
    "GetMetricsReportSchema",
    "GetHealthScoreSchema",
    "GetSearchContextSchema",
]
