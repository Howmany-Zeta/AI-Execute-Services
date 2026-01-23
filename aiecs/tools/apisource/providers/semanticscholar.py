"""
Semantic Scholar API Provider

Provides access to Semantic Scholar's extensive academic paper database.
Supports paper search, metadata retrieval, author information, and citation data.

API Documentation: https://api.semanticscholar.org/api-docs/
No API key required - completely free and open
Rate Limit: 100 requests per 5 minutes (1 request per 3 seconds recommended)

IMPORTANT - Semantic Scholar API Rules:
1. Rate Limiting: Recommended 1 request per second for sustained use
2. User-Agent: Set a descriptive User-Agent header
3. Polite Pool: Include contact email in User-Agent for better rate limits
4. Max Results: Limited to 100 results per request, use pagination for more
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


class SemanticScholarProvider(BaseAPIProvider):
    """
    Semantic Scholar API provider for academic papers and research.

    Provides access to:
    - Paper search by query, title, author
    - Paper metadata retrieval by ID (S2 ID, DOI, arXiv ID, etc.)
    - Author information and publications
    - Citation data and references
    - Paper recommendations
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    @property
    def name(self) -> str:
        return "semanticscholar"

    @property
    def description(self) -> str:
        return "Semantic Scholar API for academic papers, citations, and research metadata"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_papers",
            "get_paper",
            "get_paper_authors",
            "get_paper_citations",
            "get_paper_references",
            "get_author",
            "get_author_papers",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Semantic Scholar operations"""

        if operation == "search_papers":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_paper":
            if "paper_id" not in params:
                return False, "Missing required parameter: paper_id"

        elif operation in ["get_paper_authors", "get_paper_citations", "get_paper_references"]:
            if "paper_id" not in params:
                return False, "Missing required parameter: paper_id"

        elif operation == "get_author":
            if "author_id" not in params:
                return False, "Missing required parameter: author_id"

        elif operation == "get_author_papers":
            if "author_id" not in params:
                return False, "Missing required parameter: author_id"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_papers",
        description="Search for papers by query string",
    )
    def search_papers(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for papers on Semantic Scholar.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 10, max: 100)
            offset: Starting offset for pagination (default: 0)
            fields: Comma-separated list of fields to return (e.g., 'title,authors,abstract')

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if fields:
            params["fields"] = fields

        return self.execute("search_papers", params)

    @expose_operation(
        operation_name="get_paper",
        description="Get paper details by ID (S2 ID, DOI, arXiv ID, etc.)",
    )
    def get_paper(
        self,
        paper_id: str,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get paper details by ID.

        Args:
            paper_id: Paper identifier (S2 ID, DOI, arXiv ID, etc.)
            fields: Comma-separated list of fields to return

        Returns:
            Dictionary containing paper information
        """
        params: Dict[str, Any] = {"paper_id": paper_id}
        if fields:
            params["fields"] = fields

        return self.execute("get_paper", params)

    @expose_operation(
        operation_name="get_paper_authors",
        description="Get authors of a paper",
    )
    def get_paper_authors(
        self,
        paper_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get authors of a specific paper.

        Args:
            paper_id: Paper identifier
            limit: Maximum number of authors to return
            offset: Starting offset for pagination

        Returns:
            Dictionary containing author information
        """
        params: Dict[str, Any] = {"paper_id": paper_id}
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        return self.execute("get_paper_authors", params)

    @expose_operation(
        operation_name="get_paper_citations",
        description="Get papers that cite this paper",
    )
    def get_paper_citations(
        self,
        paper_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get papers that cite this paper.

        Args:
            paper_id: Paper identifier
            limit: Maximum number of citations to return (max: 1000)
            offset: Starting offset for pagination
            fields: Comma-separated list of fields to return

        Returns:
            Dictionary containing citing papers
        """
        params: Dict[str, Any] = {"paper_id": paper_id}
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if fields:
            params["fields"] = fields

        return self.execute("get_paper_citations", params)

    @expose_operation(
        operation_name="get_paper_references",
        description="Get papers referenced by this paper",
    )
    def get_paper_references(
        self,
        paper_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get papers referenced by this paper.

        Args:
            paper_id: Paper identifier
            limit: Maximum number of references to return (max: 1000)
            offset: Starting offset for pagination
            fields: Comma-separated list of fields to return

        Returns:
            Dictionary containing referenced papers
        """
        params: Dict[str, Any] = {"paper_id": paper_id}
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if fields:
            params["fields"] = fields

        return self.execute("get_paper_references", params)

    @expose_operation(
        operation_name="get_author",
        description="Get author details by ID",
    )
    def get_author(
        self,
        author_id: str,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get author details by ID.

        Args:
            author_id: Author identifier (S2 author ID)
            fields: Comma-separated list of fields to return

        Returns:
            Dictionary containing author information
        """
        params: Dict[str, Any] = {"author_id": author_id}
        if fields:
            params["fields"] = fields

        return self.execute("get_author", params)

    @expose_operation(
        operation_name="get_author_papers",
        description="Get papers by a specific author",
    )
    def get_author_papers(
        self,
        author_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get papers by a specific author.

        Args:
            author_id: Author identifier
            limit: Maximum number of papers to return (max: 1000)
            offset: Starting offset for pagination
            fields: Comma-separated list of fields to return

        Returns:
            Dictionary containing author's papers
        """
        params: Dict[str, Any] = {"author_id": author_id}
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if fields:
            params["fields"] = fields

        return self.execute("get_author_papers", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Semantic Scholar API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Semantic Scholar provider")

        timeout = self.config.get("timeout", 30)

        # Set User-Agent header as recommended by Semantic Scholar
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)"
        )
        headers = {
            "User-Agent": user_agent,
        }

        # Build URL and query parameters based on operation
        url = ""
        query_params: Dict[str, Any] = {}

        if operation == "search_papers":
            # Paper search endpoint
            url = f"{self.BASE_URL}/paper/search"
            query_params["query"] = params["query"]
            query_params["limit"] = params.get("limit", 10)
            if query_params["limit"] > 100:
                self.logger.warning(f"limit {query_params['limit']} exceeds API max of 100, capping at 100")
                query_params["limit"] = 100
            query_params["offset"] = params.get("offset", 0)
            if "fields" in params:
                query_params["fields"] = params["fields"]
            else:
                # Default fields for comprehensive results
                query_params["fields"] = "paperId,title,abstract,authors,year,citationCount,referenceCount,url,venue,publicationDate"

        elif operation == "get_paper":
            # Get specific paper by ID
            paper_id = params["paper_id"]
            url = f"{self.BASE_URL}/paper/{paper_id}"
            if "fields" in params:
                query_params["fields"] = params["fields"]
            else:
                query_params["fields"] = "paperId,title,abstract,authors,year,citationCount,referenceCount,url,venue,publicationDate,externalIds"

        elif operation == "get_paper_authors":
            # Get paper authors
            paper_id = params["paper_id"]
            url = f"{self.BASE_URL}/paper/{paper_id}/authors"
            if "limit" in params:
                query_params["limit"] = params["limit"]
            if "offset" in params:
                query_params["offset"] = params["offset"]

        elif operation == "get_paper_citations":
            # Get papers citing this paper
            paper_id = params["paper_id"]
            url = f"{self.BASE_URL}/paper/{paper_id}/citations"
            query_params["limit"] = params.get("limit", 100)
            if query_params["limit"] > 1000:
                self.logger.warning(f"limit {query_params['limit']} exceeds API max of 1000, capping at 1000")
                query_params["limit"] = 1000
            query_params["offset"] = params.get("offset", 0)
            if "fields" in params:
                query_params["fields"] = params["fields"]
            else:
                query_params["fields"] = "paperId,title,authors,year,citationCount"

        elif operation == "get_paper_references":
            # Get papers referenced by this paper
            paper_id = params["paper_id"]
            url = f"{self.BASE_URL}/paper/{paper_id}/references"
            query_params["limit"] = params.get("limit", 100)
            if query_params["limit"] > 1000:
                self.logger.warning(f"limit {query_params['limit']} exceeds API max of 1000, capping at 1000")
                query_params["limit"] = 1000
            query_params["offset"] = params.get("offset", 0)
            if "fields" in params:
                query_params["fields"] = params["fields"]
            else:
                query_params["fields"] = "paperId,title,authors,year,citationCount"

        elif operation == "get_author":
            # Get author details
            author_id = params["author_id"]
            url = f"{self.BASE_URL}/author/{author_id}"
            if "fields" in params:
                query_params["fields"] = params["fields"]
            else:
                query_params["fields"] = "authorId,name,affiliations,paperCount,citationCount,hIndex,url"

        elif operation == "get_author_papers":
            # Get author's papers
            author_id = params["author_id"]
            url = f"{self.BASE_URL}/author/{author_id}/papers"
            query_params["limit"] = params.get("limit", 100)
            if query_params["limit"] > 1000:
                self.logger.warning(f"limit {query_params['limit']} exceeds API max of 1000, capping at 1000")
                query_params["limit"] = 1000
            query_params["offset"] = params.get("offset", 0)
            if "fields" in params:
                query_params["fields"] = params["fields"]
            else:
                query_params["fields"] = "paperId,title,year,citationCount,authors"

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(
                url,
                params=query_params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Extract data based on operation
            if operation == "search_papers":
                # Search returns {'total': N, 'offset': M, 'next': K, 'data': [...]}
                result_data = data.get("data", [])
                total = data.get("total", len(result_data))
            elif operation in ["get_paper_citations", "get_paper_references", "get_paper_authors", "get_author_papers"]:
                # These return {'offset': M, 'next': K, 'data': [...]}
                result_data = data.get("data", [])
                total = None
            else:
                # Single item endpoints return the object directly
                result_data = data
                total = None

            # Format response
            response_dict = self._format_response(
                operation=operation,
                data=result_data,
                source=f"Semantic Scholar API - {url}",
            )

            # Add total to metadata if available
            if total is not None:
                if "metadata" not in response_dict:
                    response_dict["metadata"] = {}
                response_dict["metadata"]["total_results"] = total

            return response_dict

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.error(f"Semantic Scholar resource not found: {url}")
                raise Exception(f"Resource not found: {str(e)}")
            elif e.response.status_code == 429:
                self.logger.error("Semantic Scholar rate limit exceeded")
                raise Exception("Rate limit exceeded. Please wait before making more requests.")
            else:
                self.logger.error(f"Semantic Scholar API HTTP error: {e}")
                raise Exception(f"API HTTP error: {str(e)}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Semantic Scholar API request failed: {e}")
            raise Exception(f"API request failed: {str(e)}")
        except ValueError as e:
            self.logger.error(f"Failed to parse Semantic Scholar API response: {e}")
            raise Exception(f"Failed to parse API response: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for operation parameters"""

        schemas = {
            "search_papers": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting offset for pagination (default: 0)",
                        "minimum": 0,
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return",
                    },
                },
                "required": ["query"],
            },
            "get_paper": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper identifier (S2 ID, DOI, arXiv ID, etc.)",
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return",
                    },
                },
                "required": ["paper_id"],
            },
            "get_paper_authors": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper identifier",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of authors to return",
                        "minimum": 1,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting offset for pagination",
                        "minimum": 0,
                    },
                },
                "required": ["paper_id"],
            },
            "get_paper_citations": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper identifier",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of citations to return (max: 1000)",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting offset for pagination",
                        "minimum": 0,
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return",
                    },
                },
                "required": ["paper_id"],
            },
            "get_paper_references": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper identifier",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of references to return (max: 1000)",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting offset for pagination",
                        "minimum": 0,
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return",
                    },
                },
                "required": ["paper_id"],
            },
            "get_author": {
                "type": "object",
                "properties": {
                    "author_id": {
                        "type": "string",
                        "description": "Author identifier (S2 author ID)",
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return",
                    },
                },
                "required": ["author_id"],
            },
            "get_author_papers": {
                "type": "object",
                "properties": {
                    "author_id": {
                        "type": "string",
                        "description": "Author identifier",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of papers to return (max: 1000)",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting offset for pagination",
                        "minimum": 0,
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return",
                    },
                },
                "required": ["author_id"],
            },
        }

        return schemas.get(operation)

