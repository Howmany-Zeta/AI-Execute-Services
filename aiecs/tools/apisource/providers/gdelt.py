"""
GDELT Project API Provider

Provides access to the GDELT Project's comprehensive global news and events database.
Supports DOC 2.0 API (document search) and GEO 2.0 API (geographic analysis).

The GDELT Project monitors news media from around the world in over 100 languages,
identifying events, locations, themes, emotions, and more.

API Documentation:
- DOC 2.0 API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- GEO 2.0 API: https://blog.gdeltproject.org/gdelt-geo-2-0-api-debuts/
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, quote

from aiecs.tools.apisource.providers.base import (
    BaseAPIProvider,
    expose_operation,
)

logger = logging.getLogger(__name__)

# Optional HTTP client
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class GDELTProvider(BaseAPIProvider):
    """
    GDELT Project API provider for global news and events analysis.

    Provides access to:
    - Document search across global news (DOC 2.0 API)
    - Geographic analysis of news coverage (GEO 2.0 API)
    - Timeline analysis and trend tracking
    - Image search and visual analysis
    - Tone and sentiment analysis
    - Multi-language news monitoring (65+ languages)
    """

    DOC_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    GEO_BASE_URL = "https://api.gdeltproject.org/api/v2/geo/geo"

    @property
    def name(self) -> str:
        return "gdelt"

    @property
    def description(self) -> str:
        return "GDELT Project API for global news monitoring, events analysis, and geographic intelligence across 100+ languages"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_articles",
            "get_timeline",
            "get_tone_chart",
            "search_images",
            "get_geo_map",
            "get_source_country_map",
            "get_top_themes",
            "search_by_theme",
            "get_article_list",
            "get_timeline_volume",
            "get_timeline_tone",
            "get_timeline_lang",
            "get_timeline_source_country",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for GDELT API operations"""

        # search_by_theme uses 'theme' parameter instead of 'query'
        if operation == "search_by_theme":
            if "theme" not in params or not params["theme"]:
                return False, "Missing required parameter: theme"
        # All other operations require a query
        elif operation in self.supported_operations:
            if "query" not in params or not params["query"]:
                return False, "Missing required parameter: query"

        # Validate timespan if provided
        if "timespan" in params:
            timespan = params["timespan"]
            if isinstance(timespan, str):
                # Check format (e.g., "1d", "24h", "3months")
                if not any(timespan.endswith(suffix) for suffix in ["min", "h", "hours", "d", "days", "w", "weeks", "m", "months"]):
                    return False, "Invalid timespan format. Use format like '1d', '24h', '3months'"

        # Validate mode if provided - operation-specific validation
        if "mode" in params:
            mode = params["mode"].lower()

            # get_geo_map has specific valid modes
            if operation == "get_geo_map":
                valid_modes = ["pointdata", "country", "adm1", "sourcecountry"]
                if mode not in valid_modes:
                    return False, f"Invalid mode for get_geo_map. Must be one of: {', '.join(valid_modes)}"
            # Other operations have different valid modes
            else:
                valid_modes = [
                    "artlist", "artgallery", "imagecollage", "imagecollageinfo",
                    "imagegallery", "timelinevol", "timelinevolraw", "timelinevolinfo",
                    "timelinetone", "timelinelang", "timelinesourcecountry", "tonechart"
                ]
                if mode not in valid_modes:
                    return False, f"Invalid mode. Must be one of: {', '.join(valid_modes)}"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_articles",
        description="Search global news articles by keywords, themes, or advanced queries across 100+ languages"
    )
    def search_articles(
        self,
        query: str,
        timespan: Optional[str] = None,
        max_records: int = 75,
        sort_by: Optional[str] = None,
        source_lang: Optional[str] = None,
        source_country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for news articles across global media.

        Args:
            query: Search query (keywords, phrases, or advanced operators)
            timespan: Time period to search (e.g., '1d', '1week', '3months'). Default: 3 months
            max_records: Maximum number of results (1-250). Default: 75
            sort_by: Sort order ('datedesc', 'dateasc', 'tonedesc', 'toneasc'). Default: relevance
            source_lang: Filter by source language (e.g., 'english', 'spanish', 'chinese')
            source_country: Filter by source country (e.g., 'us', 'china', 'france')

        Returns:
            Dictionary containing article list and metadata
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records,
        }

        if timespan:
            params["timespan"] = timespan
        if sort_by:
            params["sort"] = sort_by
        if source_lang:
            params["query"] = f"{params['query']} sourcelang:{source_lang}"
        if source_country:
            params["query"] = f"{params['query']} sourcecountry:{source_country}"

        return self.execute("search_articles", params)

    @expose_operation(
        operation_name="get_timeline",
        description="Get timeline visualization of news coverage volume over time"
    )
    def get_timeline(
        self,
        query: str,
        timespan: Optional[str] = None,
        mode: str = "timelinevol",
        smoothing: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get timeline of news coverage.

        Args:
            query: Search query
            timespan: Time period (e.g., '7d', '1month'). Default: 3 months
            mode: Timeline mode ('timelinevol', 'timelinevolinfo', 'timelinetone',
                  'timelinelang', 'timelinesourcecountry'). Default: 'timelinevol'
            smoothing: Moving average smoothing (1-30 days)

        Returns:
            Dictionary containing timeline data
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": mode,
            "format": "json",
        }

        if timespan:
            params["timespan"] = timespan
        if smoothing:
            params["timelinesmooth"] = min(30, max(1, smoothing))

        return self.execute("get_timeline", params)

    @expose_operation(
        operation_name="get_tone_chart",
        description="Analyze emotional tone distribution of news coverage from negative to positive"
    )
    def get_tone_chart(
        self,
        query: str,
        timespan: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get tone distribution chart for news coverage.

        Args:
            query: Search query
            timespan: Time period to analyze. Default: 3 months

        Returns:
            Dictionary containing tone distribution data
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": "tonechart",
            "format": "json",
        }

        if timespan:
            params["timespan"] = timespan

        return self.execute("get_tone_chart", params)

    @expose_operation(
        operation_name="search_images",
        description="Search news images using visual recognition, captions, and metadata"
    )
    def search_images(
        self,
        query: str,
        timespan: Optional[str] = None,
        max_records: int = 75,
        image_tag: Optional[str] = None,
        image_web_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for news images.

        Args:
            query: Base search query
            timespan: Time period to search. Default: 3 months
            max_records: Maximum number of images (1-250). Default: 75
            image_tag: Visual content tag (e.g., 'flood', 'protest', 'fire')
            image_web_tag: Caption/metadata tag (e.g., 'election', 'climate change')

        Returns:
            Dictionary containing image results
        """
        # Build image query
        image_query = query
        if image_tag:
            image_query = f'{image_query} imagetag:"{image_tag}"'
        if image_web_tag:
            image_query = f'{image_query} imagewebtag:"{image_web_tag}"'

        params: Dict[str, Any] = {
            "query": image_query,
            "mode": "imagecollageinfo",
            "format": "json",
            "maxrecords": max_records,
        }

        if timespan:
            params["timespan"] = timespan

        return self.execute("search_images", params)

    @expose_operation(
        operation_name="get_geo_map",
        description="Get geographic map of locations mentioned in news coverage"
    )
    def get_geo_map(
        self,
        query: str,
        mode: str = "pointdata",
        timespan: Optional[str] = "24h",
        max_points: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get geographic map of news coverage.

        Args:
            query: Search query
            mode: Map mode ('pointdata', 'country', 'adm1', 'sourcecountry'). Default: 'pointdata'
            timespan: Time period. Default: 24 hours
            max_points: Maximum locations to return (mode dependent)

        Returns:
            Dictionary containing geographic data
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": mode,
            "format": "json",
        }

        if timespan:
            params["timespan"] = timespan
        if max_points:
            params["maxpoints"] = max_points

        return self.execute("get_geo_map", params)

    @expose_operation(
        operation_name="get_source_country_map",
        description="Map which countries are reporting on a topic in their domestic media"
    )
    def get_source_country_map(
        self,
        query: str,
        timespan: Optional[str] = "24h",
    ) -> Dict[str, Any]:
        """
        Get map of source countries reporting on a topic.

        Args:
            query: Search query
            timespan: Time period. Default: 24 hours

        Returns:
            Dictionary containing source country data
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": "sourcecountry",
            "format": "json",
        }

        if timespan:
            params["timespan"] = timespan

        return self.execute("get_source_country_map", params)

    @expose_operation(
        operation_name="search_by_theme",
        description="Search using GDELT's Global Knowledge Graph themes for complex topics"
    )
    def search_by_theme(
        self,
        theme: str,
        timespan: Optional[str] = None,
        max_records: int = 75,
    ) -> Dict[str, Any]:
        """
        Search by GKG theme.

        Args:
            theme: GKG theme code (e.g., 'TERROR', 'ENV_CLIMATECHANGE', 'HEALTH')
            timespan: Time period to search. Default: 3 months
            max_records: Maximum number of results. Default: 75

        Returns:
            Dictionary containing themed articles
        """
        params: Dict[str, Any] = {
            "query": f"theme:{theme}",
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records,
        }

        if timespan:
            params["timespan"] = timespan

        return self.execute("search_by_theme", params)

    @expose_operation(
        operation_name="get_article_list",
        description="Get detailed list of articles matching search criteria"
    )
    def get_article_list(
        self,
        query: str,
        timespan: Optional[str] = None,
        max_records: int = 100,
        sort_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get list of articles with full details.

        Args:
            query: Search query
            timespan: Time period. Default: 3 months
            max_records: Maximum results (1-250). Default: 100
            sort_by: Sort order ('datedesc', 'dateasc', 'tonedesc', 'toneasc')

        Returns:
            Dictionary containing article list
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records,
        }

        if timespan:
            params["timespan"] = timespan
        if sort_by:
            params["sort"] = sort_by

        return self.execute("get_article_list", params)

    @expose_operation(
        operation_name="get_timeline_volume",
        description="Get volume timeline showing coverage intensity over time"
    )
    def get_timeline_volume(
        self,
        query: str,
        timespan: Optional[str] = None,
        raw_counts: bool = False,
        smoothing: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get timeline of coverage volume.

        Args:
            query: Search query
            timespan: Time period. Default: 3 months
            raw_counts: Return raw article counts instead of percentages
            smoothing: Moving average smoothing (1-30)

        Returns:
            Dictionary containing volume timeline
        """
        mode = "timelinevolraw" if raw_counts else "timelinevol"
        params: Dict[str, Any] = {
            "query": query,
            "mode": mode,
            "format": "json",
        }

        if timespan:
            params["timespan"] = timespan
        if smoothing:
            params["timelinesmooth"] = min(30, max(1, smoothing))

        return self.execute("get_timeline_volume", params)

    @expose_operation(
        operation_name="get_timeline_tone",
        description="Get timeline showing average emotional tone over time"
    )
    def get_timeline_tone(
        self,
        query: str,
        timespan: Optional[str] = None,
        smoothing: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get timeline of average tone.

        Args:
            query: Search query
            timespan: Time period. Default: 3 months
            smoothing: Moving average smoothing (1-30)

        Returns:
            Dictionary containing tone timeline
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": "timelinetone",
            "format": "json",
        }

        if timespan:
            params["timespan"] = timespan
        if smoothing:
            params["timelinesmooth"] = min(30, max(1, smoothing))

        return self.execute("get_timeline_tone", params)

    @expose_operation(
        operation_name="get_timeline_lang",
        description="Get timeline showing coverage breakdown by language"
    )
    def get_timeline_lang(
        self,
        query: str,
        timespan: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get timeline broken down by language.

        Args:
            query: Search query
            timespan: Time period. Default: 3 months

        Returns:
            Dictionary containing language timeline
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": "timelinelang",
            "format": "json",
        }

        if timespan:
            params["timespan"] = timespan

        return self.execute("get_timeline_lang", params)

    @expose_operation(
        operation_name="get_timeline_source_country",
        description="Get timeline showing coverage breakdown by source country"
    )
    def get_timeline_source_country(
        self,
        query: str,
        timespan: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get timeline broken down by source country.

        Args:
            query: Search query
            timespan: Time period. Default: 3 months

        Returns:
            Dictionary containing source country timeline
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": "timelinesourcecountry",
            "format": "json",
        }

        if timespan:
            params["timespan"] = timespan

        return self.execute("get_timeline_source_country", params)

    @expose_operation(
        operation_name="get_top_themes",
        description="Get top themes and topics from matching articles"
    )
    def get_top_themes(
        self,
        query: str,
        timespan: Optional[str] = None,
        max_records: int = 100,
    ) -> Dict[str, Any]:
        """
        Get top themes from articles.

        Args:
            query: Search query
            timespan: Time period. Default: 3 months
            max_records: Maximum articles to analyze. Default: 100

        Returns:
            Dictionary containing theme analysis
        """
        params: Dict[str, Any] = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records,
        }

        if timespan:
            params["timespan"] = timespan

        return self.execute("get_top_themes", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from GDELT API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for GDELT provider")

        timeout = self.config.get("timeout", 30)

        # Determine which API to use based on operation
        if operation in ["get_geo_map", "get_source_country_map"]:
            base_url = self.GEO_BASE_URL
        else:
            base_url = self.DOC_BASE_URL

        # Build query parameters
        query_params = {}
        for key, value in params.items():
            if value is not None:
                query_params[key] = value

        # Make API request
        try:
            response = requests.get(base_url, params=query_params, timeout=timeout)
            response.raise_for_status()

            # GDELT returns JSON for format=json
            if params.get("format") == "json":
                data = response.json()
            else:
                # Handle other formats if needed
                data = {"raw_response": response.text}

            return self._format_response(
                operation=operation,
                data=data,
                source=f"GDELT {operation}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"GDELT API request failed: {e}")
            raise Exception(f"GDELT API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for GDELT operations"""

        schemas = {
            "search_articles": {
                "description": "Search global news articles across 100+ languages",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query (keywords, phrases, or advanced operators)",
                        "examples": [
                            "climate change",
                            '"artificial intelligence"',
                            "(trump OR biden)",
                            'theme:TERROR',
                        ],
                    },
                    "timespan": {
                        "type": "string",
                        "required": False,
                        "description": "Time period (e.g., '1d', '1week', '3months')",
                        "examples": ["24h", "7d", "1week", "3months"],
                        "default": "3months",
                    },
                    "max_records": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum results (1-250)",
                        "examples": [50, 100, 250],
                        "default": 75,
                    },
                    "sort_by": {
                        "type": "string",
                        "required": False,
                        "description": "Sort order",
                        "examples": ["datedesc", "dateasc", "tonedesc", "toneasc"],
                    },
                    "source_lang": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by source language",
                        "examples": ["english", "spanish", "chinese", "arabic"],
                    },
                    "source_country": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by source country",
                        "examples": ["us", "china", "france", "brazil"],
                    },
                },
            },
            "get_timeline": {
                "description": "Get timeline of news coverage volume",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query",
                        "examples": ["ukraine", "climate summit", "election"],
                    },
                    "timespan": {
                        "type": "string",
                        "required": False,
                        "description": "Time period",
                        "examples": ["7d", "1month", "3months"],
                        "default": "3months",
                    },
                    "mode": {
                        "type": "string",
                        "required": False,
                        "description": "Timeline mode",
                        "examples": ["timelinevol", "timelinevolinfo", "timelinetone"],
                        "default": "timelinevol",
                    },
                    "smoothing": {
                        "type": "integer",
                        "required": False,
                        "description": "Moving average smoothing (1-30 days)",
                        "examples": [5, 7, 14],
                    },
                },
            },
            "get_tone_chart": {
                "description": "Analyze emotional tone distribution",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query",
                        "examples": ["donald trump", "climate change", "covid"],
                    },
                    "timespan": {
                        "type": "string",
                        "required": False,
                        "description": "Time period",
                        "examples": ["7d", "1month"],
                        "default": "3months",
                    },
                },
            },
            "search_images": {
                "description": "Search news images using visual recognition",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Base search query",
                        "examples": ["protest", "natural disaster", "election"],
                    },
                    "image_tag": {
                        "type": "string",
                        "required": False,
                        "description": "Visual content tag",
                        "examples": ["flood", "fire", "protest", "vehicle"],
                    },
                    "image_web_tag": {
                        "type": "string",
                        "required": False,
                        "description": "Caption/metadata tag",
                        "examples": ["election", "climate change", "red cross"],
                    },
                    "timespan": {
                        "type": "string",
                        "required": False,
                        "description": "Time period",
                        "examples": ["1d", "1week"],
                        "default": "3months",
                    },
                    "max_records": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum images (1-250)",
                        "examples": [50, 100, 150],
                        "default": 75,
                    },
                },
            },
            "get_geo_map": {
                "description": "Get geographic map of locations mentioned in news",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query",
                        "examples": ["earthquake", "election", "trade"],
                    },
                    "mode": {
                        "type": "string",
                        "required": False,
                        "description": "Map mode",
                        "examples": ["pointdata", "country", "adm1", "sourcecountry"],
                        "default": "pointdata",
                    },
                    "timespan": {
                        "type": "string",
                        "required": False,
                        "description": "Time period",
                        "examples": ["24h", "7d"],
                        "default": "24h",
                    },
                },
            },
        }

        return schemas.get(operation)

