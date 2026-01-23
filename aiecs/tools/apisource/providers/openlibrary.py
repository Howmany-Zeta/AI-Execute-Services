"""
Open Library API Provider

Provides access to Open Library's extensive book database.
Supports book search, author search, work/edition details, and subject queries.

API Documentation: https://openlibrary.org/developers/api
No API key required - completely free and open
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


class OpenLibraryProvider(BaseAPIProvider):
    """
    Open Library API provider for book and author information.

    Provides access to:
    - Book search by title, author, ISBN, etc.
    - Author information and works
    - Work and edition details
    - Subject-based book discovery
    - Book covers and metadata
    """

    BASE_URL = "https://openlibrary.org"

    @property
    def name(self) -> str:
        return "openlibrary"

    @property
    def description(self) -> str:
        return "Open Library API for books, authors, and bibliographic data"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_books",
            "get_work",
            "get_edition",
            "get_author",
            "search_authors",
            "get_subject",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Open Library operations"""

        if operation == "search_books":
            if not any(key in params for key in ["q", "title", "author", "isbn"]):
                return False, "At least one search parameter required: q, title, author, or isbn"

        elif operation == "get_work":
            if "work_id" not in params:
                return False, "Missing required parameter: work_id"

        elif operation == "get_edition":
            if "edition_id" not in params:
                return False, "Missing required parameter: edition_id"

        elif operation == "get_author":
            if "author_id" not in params:
                return False, "Missing required parameter: author_id"

        elif operation == "search_authors":
            if "q" not in params:
                return False, "Missing required parameter: q"

        elif operation == "get_subject":
            if "subject" not in params:
                return False, "Missing required parameter: subject"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_books",
        description="Search for books by title, author, ISBN, or general query",
    )
    def search_books(
        self,
        q: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        isbn: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for books in Open Library.

        Args:
            q: General search query
            title: Search by book title
            author: Search by author name
            isbn: Search by ISBN
            limit: Maximum number of results to return (default: 10)
            offset: Number of results to skip for pagination

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if title:
            params["title"] = title
        if author:
            params["author"] = author
        if isbn:
            params["isbn"] = isbn
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        return self.execute("search_books", params)

    @expose_operation(
        operation_name="get_work",
        description="Get detailed information about a specific work by Open Library work ID",
    )
    def get_work(self, work_id: str) -> Dict[str, Any]:
        """
        Get work details by Open Library work ID.

        Args:
            work_id: Open Library work ID (e.g., 'OL27448W')

        Returns:
            Dictionary containing work information
        """
        return self.execute("get_work", {"work_id": work_id})

    @expose_operation(
        operation_name="get_edition",
        description="Get detailed information about a specific edition by Open Library edition ID",
    )
    def get_edition(self, edition_id: str) -> Dict[str, Any]:
        """
        Get edition details by Open Library edition ID.

        Args:
            edition_id: Open Library edition ID (e.g., 'OL7353617M')

        Returns:
            Dictionary containing edition information
        """
        return self.execute("get_edition", {"edition_id": edition_id})

    @expose_operation(
        operation_name="get_author",
        description="Get detailed information about an author by Open Library author ID",
    )
    def get_author(self, author_id: str) -> Dict[str, Any]:
        """
        Get author details by Open Library author ID.

        Args:
            author_id: Open Library author ID (e.g., 'OL26320A')

        Returns:
            Dictionary containing author information
        """
        return self.execute("get_author", {"author_id": author_id})

    @expose_operation(
        operation_name="search_authors",
        description="Search for authors by name",
    )
    def search_authors(self, q: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Search for authors.

        Args:
            q: Author name or search query
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"q": q}
        if limit:
            params["limit"] = limit

        return self.execute("search_authors", params)

    @expose_operation(
        operation_name="get_subject",
        description="Get books by subject category",
    )
    def get_subject(self, subject: str, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """
        Get books by subject.

        Args:
            subject: Subject name (e.g., 'science_fiction', 'history')
            limit: Maximum number of results to return
            offset: Number of results to skip for pagination

        Returns:
            Dictionary containing books in the subject
        """
        params: Dict[str, Any] = {"subject": subject}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        return self.execute("get_subject", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Open Library API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Open Library provider")

        # Open Library doesn't require API key
        timeout = self.config.get("timeout", 30)

        # Build endpoint based on operation
        if operation == "search_books":
            endpoint = f"{self.BASE_URL}/search.json"
            query_params = {}

            # Add search parameters
            if "q" in params:
                query_params["q"] = params["q"]
            if "title" in params:
                query_params["title"] = params["title"]
            if "author" in params:
                query_params["author"] = params["author"]
            if "isbn" in params:
                query_params["isbn"] = params["isbn"]

            # Pagination
            query_params["limit"] = params.get("limit", 10)
            if "offset" in params:
                query_params["offset"] = params["offset"]

        elif operation == "get_work":
            work_id = params["work_id"]
            # Ensure work_id has proper format
            if not work_id.startswith("OL") and not work_id.startswith("/works/"):
                work_id = f"OL{work_id}W" if not work_id.endswith("W") else f"OL{work_id}"
            if not work_id.startswith("/works/"):
                work_id = f"/works/{work_id}"
            endpoint = f"{self.BASE_URL}{work_id}.json"
            query_params = {}

        elif operation == "get_edition":
            edition_id = params["edition_id"]
            # Ensure edition_id has proper format
            if not edition_id.startswith("OL") and not edition_id.startswith("/books/"):
                edition_id = f"OL{edition_id}M" if not edition_id.endswith("M") else f"OL{edition_id}"
            if not edition_id.startswith("/books/"):
                edition_id = f"/books/{edition_id}"
            endpoint = f"{self.BASE_URL}{edition_id}.json"
            query_params = {}

        elif operation == "get_author":
            author_id = params["author_id"]
            # Ensure author_id has proper format
            if not author_id.startswith("OL") and not author_id.startswith("/authors/"):
                author_id = f"OL{author_id}A" if not author_id.endswith("A") else f"OL{author_id}"
            if not author_id.startswith("/authors/"):
                author_id = f"/authors/{author_id}"
            endpoint = f"{self.BASE_URL}{author_id}.json"
            query_params = {}

        elif operation == "search_authors":
            endpoint = f"{self.BASE_URL}/search/authors.json"
            query_params = {"q": params["q"]}
            if "limit" in params:
                query_params["limit"] = params["limit"]

        elif operation == "get_subject":
            subject = params["subject"].lower().replace(" ", "_")
            endpoint = f"{self.BASE_URL}/subjects/{subject}.json"
            query_params = {}
            if "limit" in params:
                query_params["limit"] = params["limit"]
            if "offset" in params:
                query_params["offset"] = params["offset"]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(endpoint, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # For search operations, extract the docs
            if operation in ["search_books", "search_authors"]:
                result_data = data.get("docs", [])
            elif operation == "get_subject":
                # Subject endpoint returns works in a 'works' field
                result_data = data.get("works", data)
            else:
                # For get operations, return the full response
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"Open Library API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Open Library API request failed: {e}")
            raise Exception(f"Open Library API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for Open Library operations"""

        schemas = {
            "search_books": {
                "description": "Search for books by title, author, ISBN, or general query",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "General search query",
                        "examples": ["the lord of the rings", "python programming", "1984"],
                    },
                    "title": {
                        "type": "string",
                        "required": False,
                        "description": "Search by book title",
                        "examples": ["The Great Gatsby", "To Kill a Mockingbird"],
                    },
                    "author": {
                        "type": "string",
                        "required": False,
                        "description": "Search by author name",
                        "examples": ["J.R.R. Tolkien", "Jane Austen", "Stephen King"],
                    },
                    "isbn": {
                        "type": "string",
                        "required": False,
                        "description": "Search by ISBN",
                        "examples": ["9780140328721", "0451524934"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 10,
                    },
                    "offset": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results to skip for pagination",
                        "examples": [0, 10, 20],
                    },
                },
            },
            "get_work": {
                "description": "Get detailed information about a specific work",
                "parameters": {
                    "work_id": {
                        "type": "string",
                        "required": True,
                        "description": "Open Library work ID",
                        "examples": ["OL27448W", "OL45804W", "OL45883W"],
                    }
                },
            },
            "get_edition": {
                "description": "Get detailed information about a specific edition",
                "parameters": {
                    "edition_id": {
                        "type": "string",
                        "required": True,
                        "description": "Open Library edition ID",
                        "examples": ["OL7353617M", "OL7353618M"],
                    }
                },
            },
            "get_author": {
                "description": "Get detailed information about an author",
                "parameters": {
                    "author_id": {
                        "type": "string",
                        "required": True,
                        "description": "Open Library author ID",
                        "examples": ["OL26320A", "OL23919A", "OL34184A"],
                    }
                },
            },
            "search_authors": {
                "description": "Search for authors by name",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": True,
                        "description": "Author name or search query",
                        "examples": ["Mark Twain", "Virginia Woolf", "Isaac Asimov"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 10,
                    },
                },
            },
            "get_subject": {
                "description": "Get books by subject category",
                "parameters": {
                    "subject": {
                        "type": "string",
                        "required": True,
                        "description": "Subject name",
                        "examples": ["science_fiction", "history", "romance", "biography"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 10,
                    },
                    "offset": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results to skip for pagination",
                        "examples": [0, 10, 20],
                    },
                },
            },
        }

        return schemas.get(operation)

