"""
Metropolitan Museum of Art (The Met) API Provider

Provides access to The Met's extensive art collection database.
Supports object search, detailed object information, department browsing, and more.

API Documentation: https://metmuseum.github.io/
No API key required - completely free and open
Base URL: https://collectionapi.metmuseum.org/public/collection/v1
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


class MetMuseumProvider(BaseAPIProvider):
    """
    Metropolitan Museum of Art API provider for art collection data.

    Provides access to:
    - Object search by query, department, location, date range
    - Detailed object information including images and metadata
    - Department listings
    - Comprehensive artwork analysis data for frontend visualization
    - Artist information and related works
    - Medium, culture, and period filtering
    """

    BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"

    @property
    def name(self) -> str:
        return "metmuseum"

    @property
    def description(self) -> str:
        return "Metropolitan Museum of Art API for art collection, objects, and metadata"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_objects",
            "get_object",
            "get_departments",
            "get_objects_by_department",
            "search_by_artist",
            "search_by_medium",
            "search_by_culture",
            "search_highlight_objects",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Met Museum operations"""

        if operation == "search_objects":
            if "q" not in params:
                return False, "Missing required parameter: q (search query)"

        elif operation == "get_object":
            if "object_id" not in params:
                return False, "Missing required parameter: object_id"

        elif operation == "get_departments":
            # No required parameters
            pass

        elif operation == "get_objects_by_department":
            if "department_id" not in params:
                return False, "Missing required parameter: department_id"

        elif operation == "search_by_artist":
            if "artist_name" not in params:
                return False, "Missing required parameter: artist_name"

        elif operation == "search_by_medium":
            if "medium" not in params:
                return False, "Missing required parameter: medium"

        elif operation == "search_by_culture":
            if "culture" not in params:
                return False, "Missing required parameter: culture"

        elif operation == "search_highlight_objects":
            # No required parameters - searches for highlighted/featured objects
            pass

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_objects",
        description="Search for art objects in The Met collection by query, with optional filters",
    )
    def search_objects(
        self,
        q: str,
        has_images: Optional[bool] = None,
        is_highlight: Optional[bool] = None,
        is_on_view: Optional[bool] = None,
        artist_or_culture: Optional[bool] = None,
        medium: Optional[str] = None,
        geo_location: Optional[str] = None,
        date_begin: Optional[int] = None,
        date_end: Optional[int] = None,
        department_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for art objects in The Met collection.

        Args:
            q: Search query (e.g., 'sunflowers', 'egyptian', 'picasso')
            has_images: Filter to objects with images
            is_highlight: Filter to highlighted/featured objects
            is_on_view: Filter to objects currently on view
            artist_or_culture: Search in artist/culture fields
            medium: Filter by medium (e.g., 'Paintings', 'Sculpture')
            geo_location: Filter by geographic location
            date_begin: Filter by start date (year)
            date_end: Filter by end date (year)
            department_id: Filter by department ID
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"q": q}
        if has_images is not None:
            params["hasImages"] = has_images
        if is_highlight is not None:
            params["isHighlight"] = is_highlight
        if is_on_view is not None:
            params["isOnView"] = is_on_view
        if artist_or_culture is not None:
            params["artistOrCulture"] = artist_or_culture
        if medium:
            params["medium"] = medium
        if geo_location:
            params["geoLocation"] = geo_location
        if date_begin is not None:
            params["dateBegin"] = date_begin
        if date_end is not None:
            params["dateEnd"] = date_end
        if department_id is not None:
            params["departmentId"] = department_id
        if limit:
            params["limit"] = limit

        return self.execute("search_objects", params)

    @expose_operation(
        operation_name="get_object",
        description="Get detailed information about a specific art object by ID",
    )
    def get_object(self, object_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific art object.

        Args:
            object_id: The Met object ID

        Returns:
            Dictionary containing detailed object information
        """
        return self.execute("get_object", {"object_id": object_id})

    @expose_operation(
        operation_name="get_departments",
        description="Get list of all departments at The Met",
    )
    def get_departments(self) -> Dict[str, Any]:
        """
        Get list of all departments at The Met.

        Returns:
            Dictionary containing department information
        """
        return self.execute("get_departments", {})

    @expose_operation(
        operation_name="get_objects_by_department",
        description="Get all objects in a specific department",
    )
    def get_objects_by_department(
        self,
        department_id: int,
        has_images: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get all objects in a specific department.

        Args:
            department_id: Department ID from get_departments
            has_images: Filter to objects with images
            limit: Maximum number of results to return

        Returns:
            Dictionary containing objects in the department
        """
        params: Dict[str, Any] = {"department_id": department_id}
        if has_images is not None:
            params["hasImages"] = has_images
        if limit:
            params["limit"] = limit

        return self.execute("get_objects_by_department", params)

    @expose_operation(
        operation_name="search_by_artist",
        description="Search for artworks by artist name",
    )
    def search_by_artist(
        self,
        artist_name: str,
        has_images: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for artworks by artist name.

        Args:
            artist_name: Name of the artist
            has_images: Filter to objects with images
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"artist_name": artist_name}
        if has_images is not None:
            params["hasImages"] = has_images
        if limit:
            params["limit"] = limit

        return self.execute("search_by_artist", params)

    @expose_operation(
        operation_name="search_by_medium",
        description="Search for artworks by medium (e.g., Paintings, Sculpture)",
    )
    def search_by_medium(
        self,
        medium: str,
        has_images: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for artworks by medium.

        Args:
            medium: Medium type (e.g., 'Paintings', 'Sculpture', 'Drawings')
            has_images: Filter to objects with images
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"medium": medium}
        if has_images is not None:
            params["hasImages"] = has_images
        if limit:
            params["limit"] = limit

        return self.execute("search_by_medium", params)

    @expose_operation(
        operation_name="search_by_culture",
        description="Search for artworks by culture or civilization",
    )
    def search_by_culture(
        self,
        culture: str,
        has_images: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for artworks by culture or civilization.

        Args:
            culture: Culture name (e.g., 'Egyptian', 'Greek', 'Chinese')
            has_images: Filter to objects with images
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"culture": culture}
        if has_images is not None:
            params["hasImages"] = has_images
        if limit:
            params["limit"] = limit

        return self.execute("search_by_culture", params)

    @expose_operation(
        operation_name="search_highlight_objects",
        description="Search for highlighted/featured objects in The Met collection",
    )
    def search_highlight_objects(
        self,
        q: Optional[str] = None,
        department_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for highlighted/featured objects.

        Args:
            q: Optional search query to filter highlights
            department_id: Optional department filter
            limit: Maximum number of results to return

        Returns:
            Dictionary containing highlighted objects
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        else:
            params["q"] = "*"  # Search all if no query provided
        params["isHighlight"] = True
        if department_id is not None:
            params["departmentId"] = department_id
        if limit:
            params["limit"] = limit

        return self.execute("search_highlight_objects", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from The Met Museum API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Met Museum provider")

        # The Met API doesn't require an API key
        timeout = self.config.get("timeout", 30)

        # Build endpoint based on operation
        if operation == "get_departments":
            endpoint = f"{self.BASE_URL}/departments"
            query_params = {}

        elif operation == "get_object":
            object_id = params["object_id"]
            endpoint = f"{self.BASE_URL}/objects/{object_id}"
            query_params = {}

        elif operation in ["search_objects", "search_by_artist", "search_by_medium",
                          "search_by_culture", "search_highlight_objects", "get_objects_by_department"]:
            endpoint = f"{self.BASE_URL}/search"
            query_params = {}

            # Handle different search operations
            if operation == "search_objects":
                query_params["q"] = params["q"]
                if "hasImages" in params:
                    query_params["hasImages"] = str(params["hasImages"]).lower()
                if "isHighlight" in params:
                    query_params["isHighlight"] = str(params["isHighlight"]).lower()
                if "isOnView" in params:
                    query_params["isOnView"] = str(params["isOnView"]).lower()
                if "artistOrCulture" in params:
                    query_params["artistOrCulture"] = str(params["artistOrCulture"]).lower()
                if "medium" in params:
                    query_params["medium"] = params["medium"]
                if "geoLocation" in params:
                    query_params["geoLocation"] = params["geoLocation"]
                if "dateBegin" in params:
                    query_params["dateBegin"] = params["dateBegin"]
                if "dateEnd" in params:
                    query_params["dateEnd"] = params["dateEnd"]
                if "departmentId" in params:
                    query_params["departmentId"] = params["departmentId"]

            elif operation == "search_by_artist":
                query_params["q"] = params["artist_name"]
                query_params["artistOrCulture"] = "true"
                if "hasImages" in params:
                    query_params["hasImages"] = str(params["hasImages"]).lower()

            elif operation == "search_by_medium":
                query_params["q"] = params["medium"]
                query_params["medium"] = params["medium"]
                if "hasImages" in params:
                    query_params["hasImages"] = str(params["hasImages"]).lower()

            elif operation == "search_by_culture":
                query_params["q"] = params["culture"]
                query_params["artistOrCulture"] = "true"
                if "hasImages" in params:
                    query_params["hasImages"] = str(params["hasImages"]).lower()

            elif operation == "search_highlight_objects":
                query_params["q"] = params.get("q", "*")
                query_params["isHighlight"] = "true"
                if "departmentId" in params:
                    query_params["departmentId"] = params["departmentId"]

            elif operation == "get_objects_by_department":
                query_params["q"] = "*"
                query_params["departmentId"] = params["department_id"]
                if "hasImages" in params:
                    query_params["hasImages"] = str(params["hasImages"]).lower()

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(endpoint, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Process response based on operation
            if operation == "get_departments":
                result_data = data.get("departments", [])
            elif operation == "get_object":
                result_data = data
            elif operation in ["search_objects", "search_by_artist", "search_by_medium",
                              "search_by_culture", "search_highlight_objects", "get_objects_by_department"]:
                # Search operations return objectIDs
                # Note: objectIDs can be None if no results found
                object_ids = data.get("objectIDs") or []

                # Apply limit if specified
                limit = params.get("limit")
                if limit and object_ids:
                    object_ids = object_ids[:limit]

                # For comprehensive frontend analysis, fetch detailed info for each object
                # But limit to avoid too many requests
                max_detailed_fetch = min(len(object_ids), limit if limit else 20) if object_ids else 0
                detailed_objects = []

                for obj_id in object_ids[:max_detailed_fetch]:
                    try:
                        obj_response = requests.get(
                            f"{self.BASE_URL}/objects/{obj_id}",
                            timeout=timeout
                        )
                        if obj_response.status_code == 200:
                            detailed_objects.append(obj_response.json())
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch object {obj_id}: {e}")
                        continue

                result_data = {
                    "total": data.get("total", len(object_ids)),
                    "objectIDs": object_ids,
                    "objects": detailed_objects,
                }
            else:
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"Met Museum API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Met Museum API request failed: {e}")
            raise Exception(f"Met Museum API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for Met Museum operations"""

        schemas = {
            "search_objects": {
                "description": "Search for art objects in The Met collection",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": True,
                        "description": "Search query",
                        "examples": ["sunflowers", "egyptian", "picasso", "impressionism"],
                    },
                    "hasImages": {
                        "type": "boolean",
                        "required": False,
                        "description": "Filter to objects with images",
                        "examples": [True, False],
                    },
                    "isHighlight": {
                        "type": "boolean",
                        "required": False,
                        "description": "Filter to highlighted objects",
                        "examples": [True, False],
                    },
                    "isOnView": {
                        "type": "boolean",
                        "required": False,
                        "description": "Filter to objects currently on view",
                        "examples": [True, False],
                    },
                    "artistOrCulture": {
                        "type": "boolean",
                        "required": False,
                        "description": "Search in artist/culture fields",
                        "examples": [True, False],
                    },
                    "medium": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by medium",
                        "examples": ["Paintings", "Sculpture", "Drawings", "Photographs"],
                    },
                    "geoLocation": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by geographic location",
                        "examples": ["France", "Egypt", "China", "Italy"],
                    },
                    "dateBegin": {
                        "type": "integer",
                        "required": False,
                        "description": "Filter by start date (year)",
                        "examples": [1800, 1900, 2000],
                    },
                    "dateEnd": {
                        "type": "integer",
                        "required": False,
                        "description": "Filter by end date (year)",
                        "examples": [1900, 2000, 2020],
                    },
                    "departmentId": {
                        "type": "integer",
                        "required": False,
                        "description": "Filter by department ID",
                        "examples": [1, 11, 21],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
            "get_object": {
                "description": "Get detailed information about a specific art object",
                "parameters": {
                    "object_id": {
                        "type": "integer",
                        "required": True,
                        "description": "The Met object ID",
                        "examples": [45734, 436535, 437853],
                    }
                },
            },
            "get_departments": {
                "description": "Get list of all departments at The Met",
                "parameters": {},
            },
            "get_objects_by_department": {
                "description": "Get all objects in a specific department",
                "parameters": {
                    "department_id": {
                        "type": "integer",
                        "required": True,
                        "description": "Department ID",
                        "examples": [1, 11, 21],
                    },
                    "hasImages": {
                        "type": "boolean",
                        "required": False,
                        "description": "Filter to objects with images",
                        "examples": [True, False],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
            "search_by_artist": {
                "description": "Search for artworks by artist name",
                "parameters": {
                    "artist_name": {
                        "type": "string",
                        "required": True,
                        "description": "Name of the artist",
                        "examples": ["Vincent van Gogh", "Pablo Picasso", "Claude Monet"],
                    },
                    "hasImages": {
                        "type": "boolean",
                        "required": False,
                        "description": "Filter to objects with images",
                        "examples": [True, False],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
            "search_by_medium": {
                "description": "Search for artworks by medium",
                "parameters": {
                    "medium": {
                        "type": "string",
                        "required": True,
                        "description": "Medium type",
                        "examples": ["Paintings", "Sculpture", "Drawings", "Photographs"],
                    },
                    "hasImages": {
                        "type": "boolean",
                        "required": False,
                        "description": "Filter to objects with images",
                        "examples": [True, False],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
            "search_by_culture": {
                "description": "Search for artworks by culture or civilization",
                "parameters": {
                    "culture": {
                        "type": "string",
                        "required": True,
                        "description": "Culture name",
                        "examples": ["Egyptian", "Greek", "Chinese", "Roman"],
                    },
                    "hasImages": {
                        "type": "boolean",
                        "required": False,
                        "description": "Filter to objects with images",
                        "examples": [True, False],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
            "search_highlight_objects": {
                "description": "Search for highlighted/featured objects",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Optional search query",
                        "examples": ["impressionism", "ancient", "modern"],
                    },
                    "departmentId": {
                        "type": "integer",
                        "required": False,
                        "description": "Optional department filter",
                        "examples": [1, 11, 21],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
        }

        return schemas.get(operation)

