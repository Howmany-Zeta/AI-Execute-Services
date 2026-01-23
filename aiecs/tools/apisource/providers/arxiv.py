"""
arXiv API Provider

Provides access to arXiv's extensive repository of scientific papers.
Supports paper search, metadata retrieval, and category-based queries.

API Documentation: https://info.arxiv.org/help/api/user-manual.html
No API key required - completely free and open

IMPORTANT - arXiv API Rules:
1. Rate Limiting: Be respectful - implement 3 second delays between requests
2. Caching: Cache responses when possible to reduce server load
3. User-Agent: Set a descriptive User-Agent header
4. Max Results: Limited to 30,000 results in slices of at most 2,000 at a time
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

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


class ArxivProvider(BaseAPIProvider):
    """
    arXiv API provider for scientific papers and preprints.

    Provides access to:
    - Paper search by title, author, abstract, category
    - Paper metadata retrieval by arXiv ID
    - Category-based paper discovery
    - Advanced query construction with Boolean operators
    """

    BASE_URL = "http://export.arxiv.org/api/query"

    # Atom namespace for parsing XML responses
    ATOM_NS = "{http://www.w3.org/2005/Atom}"
    ARXIV_NS = "{http://arxiv.org/schemas/atom}"
    OPENSEARCH_NS = "{http://a9.com/-/spec/opensearch/1.1/}"

    @property
    def name(self) -> str:
        return "arxiv"

    @property
    def description(self) -> str:
        return "arXiv API for scientific papers, preprints, and research articles"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_papers",
            "get_paper_by_id",
            "search_by_author",
            "search_by_category",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for arXiv operations"""

        if operation == "search_papers":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_paper_by_id":
            if "arxiv_id" not in params:
                return False, "Missing required parameter: arxiv_id"

        elif operation == "search_by_author":
            if "author" not in params:
                return False, "Missing required parameter: author"

        elif operation == "search_by_category":
            if "category" not in params:
                return False, "Missing required parameter: category"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_papers",
        description="Search for papers by query string (searches all fields)",
    )
    def search_papers(
        self,
        query: str,
        max_results: Optional[int] = None,
        start: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for papers on arXiv.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 10, max: 2000)
            start: Starting index for pagination (default: 0)
            sort_by: Sort by 'relevance', 'lastUpdatedDate', or 'submittedDate'
            sort_order: Sort order 'ascending' or 'descending'

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if max_results:
            params["max_results"] = max_results
        if start is not None:
            params["start"] = start
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order

        return self.execute("search_papers", params)

    @expose_operation(
        operation_name="get_paper_by_id",
        description="Get paper metadata by arXiv ID",
    )
    def get_paper_by_id(self, arxiv_id: str) -> Dict[str, Any]:
        """
        Get paper details by arXiv ID.

        Args:
            arxiv_id: arXiv identifier (e.g., '2301.00001' or 'cs.AI/0001001')

        Returns:
            Dictionary containing paper information
        """
        return self.execute("get_paper_by_id", {"arxiv_id": arxiv_id})

    @expose_operation(
        operation_name="search_by_author",
        description="Search for papers by author name",
    )
    def search_by_author(
        self,
        author: str,
        max_results: Optional[int] = None,
        start: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for papers by author.

        Args:
            author: Author name to search for
            max_results: Maximum number of results to return (default: 10)
            start: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"author": author}
        if max_results:
            params["max_results"] = max_results
        if start is not None:
            params["start"] = start

        return self.execute("search_by_author", params)

    @expose_operation(
        operation_name="search_by_category",
        description="Search for papers by arXiv category",
    )
    def search_by_category(
        self,
        category: str,
        max_results: Optional[int] = None,
        start: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for papers by category.

        Args:
            category: arXiv category (e.g., 'cs.AI', 'math.CO', 'physics.gen-ph')
            max_results: Maximum number of results to return (default: 10)
            start: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing papers in the category
        """
        params: Dict[str, Any] = {"category": category}
        if max_results:
            params["max_results"] = max_results
        if start is not None:
            params["start"] = start

        return self.execute("search_by_category", params)

    def _parse_atom_entry(self, entry: ET.Element) -> Dict[str, Any]:
        """Parse a single Atom entry into a paper dictionary"""
        paper: Dict[str, Any] = {}

        # Extract basic fields
        title_elem = entry.find(f"{self.ATOM_NS}title")
        if title_elem is not None and title_elem.text:
            paper["title"] = title_elem.text.strip()

        id_elem = entry.find(f"{self.ATOM_NS}id")
        if id_elem is not None and id_elem.text:
            paper["id"] = id_elem.text.strip()
            # Extract just the arXiv ID from the URL
            if "/abs/" in paper["id"]:
                paper["arxiv_id"] = paper["id"].split("/abs/")[-1]

        summary_elem = entry.find(f"{self.ATOM_NS}summary")
        if summary_elem is not None and summary_elem.text:
            paper["abstract"] = summary_elem.text.strip()

        published_elem = entry.find(f"{self.ATOM_NS}published")
        if published_elem is not None and published_elem.text:
            paper["published"] = published_elem.text.strip()

        updated_elem = entry.find(f"{self.ATOM_NS}updated")
        if updated_elem is not None and updated_elem.text:
            paper["updated"] = updated_elem.text.strip()

        # Extract authors
        authors = []
        for author_elem in entry.findall(f"{self.ATOM_NS}author"):
            name_elem = author_elem.find(f"{self.ATOM_NS}name")
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())
        if authors:
            paper["authors"] = authors

        # Extract categories
        categories = []
        for category_elem in entry.findall(f"{self.ATOM_NS}category"):
            term = category_elem.get("term")
            if term:
                categories.append(term)
        if categories:
            paper["categories"] = categories

        # Extract primary category
        primary_cat_elem = entry.find(f"{self.ARXIV_NS}primary_category")
        if primary_cat_elem is not None:
            primary_term = primary_cat_elem.get("term")
            if primary_term:
                paper["primary_category"] = primary_term

        # Extract links (PDF, abstract page)
        for link_elem in entry.findall(f"{self.ATOM_NS}link"):
            rel = link_elem.get("rel")
            href = link_elem.get("href")
            title = link_elem.get("title")

            if rel == "alternate" and href:
                paper["abs_url"] = href
            elif title == "pdf" and href:
                paper["pdf_url"] = href

        # Extract arXiv-specific fields
        comment_elem = entry.find(f"{self.ARXIV_NS}comment")
        if comment_elem is not None and comment_elem.text:
            paper["comment"] = comment_elem.text.strip()

        journal_ref_elem = entry.find(f"{self.ARXIV_NS}journal_ref")
        if journal_ref_elem is not None and journal_ref_elem.text:
            paper["journal_ref"] = journal_ref_elem.text.strip()

        doi_elem = entry.find(f"{self.ARXIV_NS}doi")
        if doi_elem is not None and doi_elem.text:
            paper["doi"] = doi_elem.text.strip()

        return paper

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from arXiv API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for arXiv provider")

        timeout = self.config.get("timeout", 30)

        # Set User-Agent header as required by arXiv API etiquette
        # Use same format as Wikipedia provider for consistency
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)"
        )
        headers = {
            "User-Agent": user_agent,
        }

        # Build query parameters based on operation
        query_params: Dict[str, Any] = {}

        if operation == "search_papers":
            # General search query
            query_params["search_query"] = f"all:{params['query']}"
            max_results = params.get("max_results", 10)
            # Enforce arXiv API limit: max 2000 results per request
            if max_results > 2000:
                self.logger.warning(f"max_results {max_results} exceeds arXiv limit of 2000, capping at 2000")
                max_results = 2000
            query_params["max_results"] = max_results
            query_params["start"] = params.get("start", 0)

            if "sort_by" in params:
                query_params["sortBy"] = params["sort_by"]
            if "sort_order" in params:
                query_params["sortOrder"] = params["sort_order"]

        elif operation == "get_paper_by_id":
            # Get specific paper by ID
            arxiv_id = params["arxiv_id"]
            query_params["id_list"] = arxiv_id
            query_params["max_results"] = 1

        elif operation == "search_by_author":
            # Search by author
            author = params["author"]
            query_params["search_query"] = f"au:{author}"
            max_results = params.get("max_results", 10)
            # Enforce arXiv API limit: max 2000 results per request
            if max_results > 2000:
                self.logger.warning(f"max_results {max_results} exceeds arXiv limit of 2000, capping at 2000")
                max_results = 2000
            query_params["max_results"] = max_results
            query_params["start"] = params.get("start", 0)

        elif operation == "search_by_category":
            # Search by category
            category = params["category"]
            query_params["search_query"] = f"cat:{category}"
            max_results = params.get("max_results", 10)
            # Enforce arXiv API limit: max 2000 results per request
            if max_results > 2000:
                self.logger.warning(f"max_results {max_results} exceeds arXiv limit of 2000, capping at 2000")
                max_results = 2000
            query_params["max_results"] = max_results
            query_params["start"] = params.get("start", 0)

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request with proper headers
        try:
            response = requests.get(
                self.BASE_URL,
                params=query_params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            # Parse Atom XML response
            root = ET.fromstring(response.content)

            # Extract entries
            entries = root.findall(f"{self.ATOM_NS}entry")
            papers = []

            for entry in entries:
                # Check if this is an error entry
                entry_id = entry.find(f"{self.ATOM_NS}id")
                if entry_id is not None and entry_id.text and "api/errors" in entry_id.text:
                    # This is an error entry
                    summary_elem = entry.find(f"{self.ATOM_NS}summary")
                    error_msg = summary_elem.text if summary_elem is not None and summary_elem.text else "Unknown error"
                    raise Exception(f"arXiv API error: {error_msg}")

                paper = self._parse_atom_entry(entry)
                papers.append(paper)

            # Extract total results from OpenSearch elements
            total_results_elem = root.find(f"{self.OPENSEARCH_NS}totalResults")
            total_results = None
            if total_results_elem is not None and total_results_elem.text:
                try:
                    total_results = int(total_results_elem.text)
                except ValueError:
                    pass

            # For single paper lookup, return just the paper
            if operation == "get_paper_by_id":
                result_data = papers[0] if papers else {}
            else:
                result_data = papers

            # Add total results to metadata if available
            response_dict = self._format_response(
                operation=operation,
                data=result_data,
                source=f"arXiv API - {self.BASE_URL}",
            )

            # Add total results to metadata
            if total_results is not None:
                if "metadata" not in response_dict:
                    response_dict["metadata"] = {}
                response_dict["metadata"]["total_results"] = total_results

            return response_dict

        except requests.exceptions.RequestException as e:
            self.logger.error(f"arXiv API request failed: {e}")
            raise Exception(f"arXiv API request failed: {str(e)}")
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse arXiv API response: {e}")
            raise Exception(f"Failed to parse arXiv API response: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for operation parameters"""

        schemas = {
            "search_papers": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (searches all fields)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 2000)",
                        "minimum": 1,
                        "maximum": 2000,
                    },
                    "start": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "minimum": 0,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort by field",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "Sort order",
                        "enum": ["ascending", "descending"],
                    },
                },
                "required": ["query"],
            },
            "get_paper_by_id": {
                "type": "object",
                "properties": {
                    "arxiv_id": {
                        "type": "string",
                        "description": "arXiv identifier (e.g., '2301.00001' or 'cs.AI/0001001')",
                    },
                },
                "required": ["arxiv_id"],
            },
            "search_by_author": {
                "type": "object",
                "properties": {
                    "author": {
                        "type": "string",
                        "description": "Author name to search for",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "minimum": 1,
                        "maximum": 2000,
                    },
                    "start": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "minimum": 0,
                    },
                },
                "required": ["author"],
            },
            "search_by_category": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "arXiv category (e.g., 'cs.AI', 'math.CO', 'physics.gen-ph')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "minimum": 1,
                        "maximum": 2000,
                    },
                    "start": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "minimum": 0,
                    },
                },
                "required": ["category"],
            },
        }

        return schemas.get(operation)

