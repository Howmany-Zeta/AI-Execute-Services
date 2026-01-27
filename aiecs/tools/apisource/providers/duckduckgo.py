"""
DuckDuckGo Zero-Click Info API Provider

Provides access to DuckDuckGo's Instant Answer API for quick information retrieval.
Returns instant answers, abstracts, definitions, related topics, and infoboxes.

API Documentation: https://api.duckduckgo.com
No API key required - completely free and open

IMPORTANT - DuckDuckGo API Rules:
1. Rate Limiting: Be respectful - implement reasonable delays between requests
2. Caching: Cache responses when possible to reduce server load
3. User-Agent: Set a descriptive User-Agent header
4. No Scraping: This is an Instant Answer API, not a full search results API
5. Attribution: Consider attributing results to DuckDuckGo when displaying them
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

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


class DuckDuckGoProvider(BaseAPIProvider):
    """
    DuckDuckGo Zero-Click Info API provider for instant answers and information.

    Provides access to:
    - Instant answers for queries
    - Article abstracts and summaries
    - Definitions and explanations
    - Related topics and disambiguation
    - Infoboxes with structured data
    - Images and icons
    """

    BASE_URL = "https://api.duckduckgo.com/"

    @property
    def name(self) -> str:
        return "duckduckgo"

    @property
    def description(self) -> str:
        return "DuckDuckGo Zero-Click Info API for instant answers, abstracts, and quick information"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_instant_answer",
            "get_abstract",
            "get_definition",
            "get_related_topics",
            "get_infobox",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for DuckDuckGo operations"""

        if operation in ["get_instant_answer", "get_abstract", "get_definition", "get_related_topics", "get_infobox"]:
            if "query" not in params:
                return False, "Missing required parameter: query"
            if not params["query"] or not isinstance(params["query"], str):
                return False, "Parameter 'query' must be a non-empty string"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_instant_answer",
        description="Get instant answer for a query from DuckDuckGo",
    )
    def get_instant_answer(
        self,
        query: str,
        skip_disambig: Optional[bool] = None,
        no_redirect: Optional[bool] = None,
        no_html: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Get instant answer for a query.

        Args:
            query: Search query string
            skip_disambig: Skip disambiguation (default: False)
            no_redirect: Skip HTTP redirects (default: False)
            no_html: Remove HTML from text (default: False)

        Returns:
            Dictionary containing instant answer data and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if skip_disambig is not None:
            params["skip_disambig"] = skip_disambig
        if no_redirect is not None:
            params["no_redirect"] = no_redirect
        if no_html is not None:
            params["no_html"] = no_html

        return self.execute("get_instant_answer", params)

    @expose_operation(
        operation_name="get_abstract",
        description="Get article abstract/summary from DuckDuckGo",
    )
    def get_abstract(self, query: str) -> Dict[str, Any]:
        """
        Get article abstract for a query.

        Args:
            query: Search query string (typically an entity or topic name)

        Returns:
            Dictionary containing abstract text and source information
        """
        return self.execute("get_abstract", {"query": query})

    @expose_operation(
        operation_name="get_definition",
        description="Get definition for a term from DuckDuckGo",
    )
    def get_definition(self, query: str) -> Dict[str, Any]:
        """
        Get definition for a term.

        Args:
            query: Term to define

        Returns:
            Dictionary containing definition and source
        """
        return self.execute("get_definition", {"query": query})

    @expose_operation(
        operation_name="get_related_topics",
        description="Get related topics and disambiguation for a query",
    )
    def get_related_topics(self, query: str) -> Dict[str, Any]:
        """
        Get related topics for a query.

        Args:
            query: Search query string

        Returns:
            Dictionary containing related topics and categories
        """
        return self.execute("get_related_topics", {"query": query})

    @expose_operation(
        operation_name="get_infobox",
        description="Get structured infobox data for an entity",
    )
    def get_infobox(self, query: str) -> Dict[str, Any]:
        """
        Get infobox data for an entity.

        Args:
            query: Entity name (e.g., person, place, organization)

        Returns:
            Dictionary containing structured infobox data
        """
        return self.execute("get_infobox", {"query": query})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from DuckDuckGo Instant Answer API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for DuckDuckGo provider")

        timeout = self.config.get("timeout", 30)

        # Set User-Agent header for API etiquette
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)"
        )
        headers = {
            "User-Agent": user_agent,
        }

        # Build query parameters
        query_params = {
            "q": params["query"],
            "format": "json",
            "no_html": 1 if params.get("no_html", False) else 0,
            "skip_disambig": 1 if params.get("skip_disambig", False) else 0,
        }

        # Add optional parameters
        if params.get("no_redirect"):
            query_params["no_redirect"] = 1

        # Make API request
        try:
            response = requests.get(
                self.BASE_URL,
                params=query_params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()

            # Extract relevant data based on operation
            if operation == "get_instant_answer":
                result_data = self._extract_instant_answer(data)
            elif operation == "get_abstract":
                result_data = self._extract_abstract(data)
            elif operation == "get_definition":
                result_data = self._extract_definition(data)
            elif operation == "get_related_topics":
                result_data = self._extract_related_topics(data)
            elif operation == "get_infobox":
                result_data = self._extract_infobox(data)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"DuckDuckGo Instant Answer API - {params['query']}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"DuckDuckGo API request failed: {e}")
            raise Exception(f"DuckDuckGo API request failed: {str(e)}")

    def _extract_instant_answer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract instant answer from API response"""
        return {
            "heading": data.get("Heading", ""),
            "abstract": data.get("AbstractText", ""),
            "abstract_source": data.get("AbstractSource", ""),
            "abstract_url": data.get("AbstractURL", ""),
            "answer": data.get("Answer", ""),
            "answer_type": data.get("AnswerType", ""),
            "definition": data.get("Definition", ""),
            "definition_source": data.get("DefinitionSource", ""),
            "definition_url": data.get("DefinitionURL", ""),
            "image": data.get("Image", ""),
            "type": data.get("Type", ""),
            "redirect": data.get("Redirect", ""),
            "entity": data.get("Entity", ""),
            "has_infobox": bool(data.get("Infobox")),
            "has_related_topics": bool(data.get("RelatedTopics")),
        }

    def _extract_abstract(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract abstract from API response"""
        return {
            "heading": data.get("Heading", ""),
            "abstract": data.get("AbstractText", ""),
            "source": data.get("AbstractSource", ""),
            "url": data.get("AbstractURL", ""),
            "image": data.get("Image", ""),
        }

    def _extract_definition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract definition from API response"""
        return {
            "heading": data.get("Heading", ""),
            "definition": data.get("Definition", ""),
            "source": data.get("DefinitionSource", ""),
            "url": data.get("DefinitionURL", ""),
        }

    def _extract_related_topics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract related topics from API response"""
        related_topics = data.get("RelatedTopics", [])

        # Process related topics to extract structured data
        topics = []
        for topic in related_topics:
            if isinstance(topic, dict):
                if "Topics" in topic:
                    # This is a category with subtopics
                    topics.append({
                        "type": "category",
                        "name": topic.get("Name", ""),
                        "topics": [
                            {
                                "text": t.get("Text", ""),
                                "url": t.get("FirstURL", ""),
                                "icon": t.get("Icon", {}).get("URL", ""),
                            }
                            for t in topic.get("Topics", [])
                        ],
                    })
                else:
                    # This is a single topic
                    topics.append({
                        "type": "topic",
                        "text": topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "icon": topic.get("Icon", {}).get("URL", ""),
                    })

        return {
            "heading": data.get("Heading", ""),
            "related_topics": topics,
            "total_topics": len(topics),
        }

    def _extract_infobox(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract infobox from API response"""
        infobox_data = data.get("Infobox", {})

        # Parse infobox content if it's a string (JSON)
        if isinstance(infobox_data, str):
            try:
                import json
                infobox_data = json.loads(infobox_data)
            except (json.JSONDecodeError, ImportError):
                infobox_data = {}

        return {
            "heading": data.get("Heading", ""),
            "infobox": infobox_data,
            "image": data.get("Image", ""),
            "abstract": data.get("AbstractText", ""),
        }

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for DuckDuckGo operations"""

        schemas = {
            "get_instant_answer": {
                "description": "Get instant answer for a query from DuckDuckGo",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": [
                            "Albert Einstein",
                            "Python programming language",
                            "What is machine learning",
                            "weather in New York",
                        ],
                    },
                    "skip_disambig": {
                        "type": "boolean",
                        "required": False,
                        "description": "Skip disambiguation results",
                        "default": False,
                    },
                    "no_redirect": {
                        "type": "boolean",
                        "required": False,
                        "description": "Skip HTTP redirects",
                        "default": False,
                    },
                    "no_html": {
                        "type": "boolean",
                        "required": False,
                        "description": "Remove HTML from text",
                        "default": False,
                    },
                },
            },
            "get_abstract": {
                "description": "Get article abstract/summary from DuckDuckGo",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Entity or topic name",
                        "examples": [
                            "Nikola Tesla",
                            "Quantum Computing",
                            "Eiffel Tower",
                        ],
                    },
                },
            },
            "get_definition": {
                "description": "Get definition for a term from DuckDuckGo",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Term to define",
                        "examples": [
                            "algorithm",
                            "photosynthesis",
                            "cryptocurrency",
                        ],
                    },
                },
            },
            "get_related_topics": {
                "description": "Get related topics and disambiguation for a query",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": [
                            "Python",
                            "Mars",
                            "Apple",
                        ],
                    },
                },
            },
            "get_infobox": {
                "description": "Get structured infobox data for an entity",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Entity name (person, place, organization, etc.)",
                        "examples": [
                            "Steve Jobs",
                            "Microsoft Corporation",
                            "Mount Everest",
                        ],
                    },
                },
            },
        }

        return schemas.get(operation)

