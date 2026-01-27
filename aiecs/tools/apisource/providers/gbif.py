"""
GBIF (Global Biodiversity Information Facility) API Provider

Provides access to GBIF's extensive biodiversity database with over 2 billion occurrence records.
Supports species search, occurrence data, dataset information, and taxonomic lookups.

API Documentation: https://techdocs.gbif.org/en/openapi/
No API key required - completely free and open

GBIF API Features:
1. Species API: Taxonomic names and species information
2. Occurrence API: Biodiversity occurrence records
3. Dataset API: Dataset metadata and information
4. Registry API: Publishing organizations and networks
5. Maps API: Geospatial data visualization

Rate Limiting: Be respectful - implement reasonable delays between requests
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


class GBIFProvider(BaseAPIProvider):
    """
    GBIF API provider for biodiversity and species occurrence data.

    Provides access to:
    - Species search and taxonomic information
    - Occurrence records and observations
    - Dataset metadata and information
    - Name matching and lookup services
    - Geographic and temporal occurrence data
    """

    BASE_URL = "https://api.gbif.org/v1"

    @property
    def name(self) -> str:
        return "gbif"

    @property
    def description(self) -> str:
        return "GBIF API for biodiversity data, species occurrences, and taxonomic information"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_species",
            "get_species_by_key",
            "match_species_name",
            "search_occurrences",
            "get_occurrence_by_key",
            "search_datasets",
            "get_dataset_by_key",
            "get_species_vernacular_names",
            "get_species_children",
            "get_species_parents",
            "get_occurrence_count",
            "search_organizations",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for GBIF operations"""

        if operation == "search_species":
            if "q" not in params:
                return False, "Missing required parameter: q (query string)"

        elif operation == "get_species_by_key":
            if "key" not in params:
                return False, "Missing required parameter: key (species key)"

        elif operation == "match_species_name":
            if "name" not in params:
                return False, "Missing required parameter: name (scientific name)"

        elif operation == "search_occurrences":
            # No required params - can search with various filters
            pass

        elif operation == "get_occurrence_by_key":
            if "key" not in params:
                return False, "Missing required parameter: key (occurrence key)"

        elif operation == "search_datasets":
            # No required params
            pass

        elif operation == "get_dataset_by_key":
            if "key" not in params:
                return False, "Missing required parameter: key (dataset key)"

        elif operation == "get_species_vernacular_names":
            if "key" not in params:
                return False, "Missing required parameter: key (species key)"

        elif operation == "get_species_children":
            if "key" not in params:
                return False, "Missing required parameter: key (species key)"

        elif operation == "get_species_parents":
            if "key" not in params:
                return False, "Missing required parameter: key (species key)"

        elif operation == "get_occurrence_count":
            # No required params - can count with various filters
            pass

        elif operation == "search_organizations":
            # No required params
            pass

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_species",
        description="Search for species by name or other criteria",
    )
    def search_species(
        self,
        q: str,
        rank: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for species in GBIF.

        Args:
            q: Search query string (species name, common name, etc.)
            rank: Taxonomic rank filter (e.g., 'SPECIES', 'GENUS', 'FAMILY')
            limit: Maximum number of results to return (default: 20, max: 1000)
            offset: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"q": q}
        if rank:
            params["rank"] = rank
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        return self.execute("search_species", params)

    @expose_operation(
        operation_name="get_species_by_key",
        description="Get detailed species information by GBIF key",
    )
    def get_species_by_key(self, key: int) -> Dict[str, Any]:
        """
        Get species details by GBIF key.

        Args:
            key: GBIF species key (taxon key)

        Returns:
            Dictionary containing species information
        """
        return self.execute("get_species_by_key", {"key": key})

    @expose_operation(
        operation_name="match_species_name",
        description="Match a scientific name to GBIF taxonomy",
    )
    def match_species_name(
        self,
        name: str,
        kingdom: Optional[str] = None,
        rank: Optional[str] = None,
        strict: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Match a scientific name to GBIF's taxonomic backbone.

        Args:
            name: Scientific name to match
            kingdom: Kingdom to narrow down the match (e.g., 'Animalia', 'Plantae')
            rank: Expected taxonomic rank
            strict: Use strict matching (default: False)

        Returns:
            Dictionary containing matched species information
        """
        params: Dict[str, Any] = {"name": name}
        if kingdom:
            params["kingdom"] = kingdom
        if rank:
            params["rank"] = rank
        if strict is not None:
            params["strict"] = strict

        return self.execute("match_species_name", params)

    @expose_operation(
        operation_name="search_occurrences",
        description="Search for species occurrence records",
    )
    def search_occurrences(
        self,
        taxon_key: Optional[int] = None,
        country: Optional[str] = None,
        year: Optional[str] = None,
        basis_of_record: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for occurrence records.

        Args:
            taxon_key: GBIF taxon key to filter by species
            country: ISO 2-letter country code (e.g., 'US', 'GB')
            year: Year or year range (e.g., '2020' or '2010,2020')
            basis_of_record: Type of record (e.g., 'HUMAN_OBSERVATION', 'PRESERVED_SPECIMEN')
            limit: Maximum number of results to return (default: 20, max: 300)
            offset: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing occurrence records
        """
        params: Dict[str, Any] = {}
        if taxon_key:
            params["taxonKey"] = taxon_key
        if country:
            params["country"] = country
        if year:
            params["year"] = year
        if basis_of_record:
            params["basisOfRecord"] = basis_of_record
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        return self.execute("search_occurrences", params)

    @expose_operation(
        operation_name="get_occurrence_by_key",
        description="Get detailed occurrence record by key",
    )
    def get_occurrence_by_key(self, key: int) -> Dict[str, Any]:
        """
        Get occurrence details by GBIF key.

        Args:
            key: GBIF occurrence key

        Returns:
            Dictionary containing occurrence information
        """
        return self.execute("get_occurrence_by_key", {"key": key})

    @expose_operation(
        operation_name="search_datasets",
        description="Search for datasets in GBIF",
    )
    def search_datasets(
        self,
        q: Optional[str] = None,
        type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for datasets.

        Args:
            q: Search query string
            type: Dataset type (e.g., 'OCCURRENCE', 'CHECKLIST', 'METADATA')
            limit: Maximum number of results to return (default: 20)
            offset: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing dataset information
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if type:
            params["type"] = type
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        return self.execute("search_datasets", params)

    @expose_operation(
        operation_name="get_dataset_by_key",
        description="Get detailed dataset information by key",
    )
    def get_dataset_by_key(self, key: str) -> Dict[str, Any]:
        """
        Get dataset details by GBIF key.

        Args:
            key: GBIF dataset key (UUID)

        Returns:
            Dictionary containing dataset information
        """
        return self.execute("get_dataset_by_key", {"key": key})

    @expose_operation(
        operation_name="get_species_vernacular_names",
        description="Get common/vernacular names for a species",
    )
    def get_species_vernacular_names(self, key: int) -> Dict[str, Any]:
        """
        Get vernacular (common) names for a species.

        Args:
            key: GBIF species key

        Returns:
            Dictionary containing vernacular names in different languages
        """
        return self.execute("get_species_vernacular_names", {"key": key})

    @expose_operation(
        operation_name="get_species_children",
        description="Get direct children taxa of a species",
    )
    def get_species_children(
        self,
        key: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get direct children taxa.

        Args:
            key: GBIF species key
            limit: Maximum number of results to return (default: 20)
            offset: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing child taxa
        """
        params: Dict[str, Any] = {"key": key}
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        return self.execute("get_species_children", params)

    @expose_operation(
        operation_name="get_species_parents",
        description="Get parent taxa hierarchy for a species",
    )
    def get_species_parents(self, key: int) -> Dict[str, Any]:
        """
        Get parent taxa hierarchy.

        Args:
            key: GBIF species key

        Returns:
            Dictionary containing parent taxa hierarchy
        """
        return self.execute("get_species_parents", {"key": key})

    @expose_operation(
        operation_name="get_occurrence_count",
        description="Get count of occurrence records matching criteria",
    )
    def get_occurrence_count(
        self,
        taxon_key: Optional[int] = None,
        country: Optional[str] = None,
        year: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get count of occurrence records.

        Args:
            taxon_key: GBIF taxon key to filter by species
            country: ISO 2-letter country code
            year: Year or year range

        Returns:
            Dictionary containing occurrence count
        """
        params: Dict[str, Any] = {}
        if taxon_key:
            params["taxonKey"] = taxon_key
        if country:
            params["country"] = country
        if year:
            params["year"] = year

        return self.execute("get_occurrence_count", params)

    @expose_operation(
        operation_name="search_organizations",
        description="Search for publishing organizations",
    )
    def search_organizations(
        self,
        q: Optional[str] = None,
        country: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for publishing organizations.

        Args:
            q: Search query string
            country: ISO 2-letter country code
            limit: Maximum number of results to return (default: 20)
            offset: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing organization information
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if country:
            params["country"] = country
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        return self.execute("search_organizations", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from GBIF API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for GBIF provider")

        timeout = self.config.get("timeout", 30)

        # Set User-Agent header as best practice
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; contact@example.com)"
        )
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

        # Build endpoint and query parameters based on operation
        endpoint = ""
        query_params: Dict[str, Any] = {}

        if operation == "search_species":
            endpoint = f"{self.BASE_URL}/species/search"
            query_params["q"] = params["q"]
            if "rank" in params:
                query_params["rank"] = params["rank"]
            if "limit" in params:
                query_params["limit"] = min(params["limit"], 1000)
            else:
                query_params["limit"] = 20
            if "offset" in params:
                query_params["offset"] = params["offset"]

        elif operation == "get_species_by_key":
            key = params["key"]
            endpoint = f"{self.BASE_URL}/species/{key}"

        elif operation == "match_species_name":
            endpoint = f"{self.BASE_URL}/species/match"
            query_params["name"] = params["name"]
            if "kingdom" in params:
                query_params["kingdom"] = params["kingdom"]
            if "rank" in params:
                query_params["rank"] = params["rank"]
            if "strict" in params:
                query_params["strict"] = str(params["strict"]).lower()

        elif operation == "search_occurrences":
            endpoint = f"{self.BASE_URL}/occurrence/search"
            if "taxonKey" in params:
                query_params["taxonKey"] = params["taxonKey"]
            if "country" in params:
                query_params["country"] = params["country"]
            if "year" in params:
                query_params["year"] = params["year"]
            if "basisOfRecord" in params:
                query_params["basisOfRecord"] = params["basisOfRecord"]
            if "limit" in params:
                query_params["limit"] = min(params["limit"], 300)
            else:
                query_params["limit"] = 20
            if "offset" in params:
                query_params["offset"] = params["offset"]

        elif operation == "get_occurrence_by_key":
            key = params["key"]
            endpoint = f"{self.BASE_URL}/occurrence/{key}"

        elif operation == "search_datasets":
            endpoint = f"{self.BASE_URL}/dataset/search"
            if "q" in params:
                query_params["q"] = params["q"]
            if "type" in params:
                query_params["type"] = params["type"]
            if "limit" in params:
                query_params["limit"] = params["limit"]
            else:
                query_params["limit"] = 20
            if "offset" in params:
                query_params["offset"] = params["offset"]

        elif operation == "get_dataset_by_key":
            key = params["key"]
            endpoint = f"{self.BASE_URL}/dataset/{key}"

        elif operation == "get_species_vernacular_names":
            key = params["key"]
            endpoint = f"{self.BASE_URL}/species/{key}/vernacularNames"

        elif operation == "get_species_children":
            key = params["key"]
            endpoint = f"{self.BASE_URL}/species/{key}/children"
            if "limit" in params:
                query_params["limit"] = params["limit"]
            else:
                query_params["limit"] = 20
            if "offset" in params:
                query_params["offset"] = params["offset"]

        elif operation == "get_species_parents":
            key = params["key"]
            endpoint = f"{self.BASE_URL}/species/{key}/parents"

        elif operation == "get_occurrence_count":
            endpoint = f"{self.BASE_URL}/occurrence/count"
            if "taxonKey" in params:
                query_params["taxonKey"] = params["taxonKey"]
            if "country" in params:
                query_params["country"] = params["country"]
            if "year" in params:
                query_params["year"] = params["year"]

        elif operation == "search_organizations":
            endpoint = f"{self.BASE_URL}/organization"
            if "q" in params:
                query_params["q"] = params["q"]
            if "country" in params:
                query_params["country"] = params["country"]
            if "limit" in params:
                query_params["limit"] = params["limit"]
            else:
                query_params["limit"] = 20
            if "offset" in params:
                query_params["offset"] = params["offset"]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(
                endpoint,
                params=query_params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Format response based on operation type
            if operation in ["search_species", "search_occurrences", "search_datasets",
                           "search_organizations", "get_species_children"]:
                # These return paginated results with 'results' array
                result_data = data.get("results", [])

                # Build response with metadata
                response_dict = self._format_response(
                    operation=operation,
                    data=result_data,
                    source=f"GBIF API - {endpoint}",
                )

                # Add pagination metadata
                if "metadata" not in response_dict:
                    response_dict["metadata"] = {}
                response_dict["metadata"]["count"] = data.get("count", len(result_data))
                response_dict["metadata"]["offset"] = data.get("offset", 0)
                response_dict["metadata"]["limit"] = data.get("limit", 20)
                response_dict["metadata"]["endOfRecords"] = data.get("endOfRecords", False)

            elif operation == "get_occurrence_count":
                # Count returns a simple number
                result_data = {"count": data}
                response_dict = self._format_response(
                    operation=operation,
                    data=result_data,
                    source=f"GBIF API - {endpoint}",
                )

            elif operation == "get_species_vernacular_names":
                # Returns array of vernacular names
                result_data = data.get("results", data) if isinstance(data, dict) else data
                response_dict = self._format_response(
                    operation=operation,
                    data=result_data,
                    source=f"GBIF API - {endpoint}",
                )

            elif operation == "get_species_parents":
                # Returns array of parent taxa
                result_data = data
                response_dict = self._format_response(
                    operation=operation,
                    data=result_data,
                    source=f"GBIF API - {endpoint}",
                )

            else:
                # Single record operations (get_species_by_key, get_occurrence_by_key, etc.)
                result_data = data
                response_dict = self._format_response(
                    operation=operation,
                    data=result_data,
                    source=f"GBIF API - {endpoint}",
                )

            return response_dict

        except requests.exceptions.RequestException as e:
            self.logger.error(f"GBIF API request failed: {e}")
            raise Exception(f"GBIF API request failed: {str(e)}")
        except ValueError as e:
            self.logger.error(f"Failed to parse GBIF API response: {e}")
            raise Exception(f"Failed to parse GBIF API response: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for operation parameters"""

        schemas = {
            "search_species": {
                "description": "Search for species by name or other criteria",
                "parameters": {
                    "q": {
                        "type": "string",
                        "description": "Search query string (species name, common name, etc.)",
                        "required": True,
                    },
                    "rank": {
                        "type": "string",
                        "description": "Taxonomic rank filter (e.g., 'SPECIES', 'GENUS', 'FAMILY')",
                        "required": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20, max: 1000)",
                        "required": False,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "required": False,
                    },
                },
                "examples": [
                    {
                        "description": "Search for Panthera genus",
                        "params": {"q": "Panthera", "rank": "GENUS", "limit": 10},
                    }
                ],
            },
            "get_species_by_key": {
                "description": "Get detailed species information by GBIF key",
                "parameters": {
                    "key": {
                        "type": "integer",
                        "description": "GBIF species key (taxon key)",
                        "required": True,
                    },
                },
                "examples": [
                    {
                        "description": "Get Panthera leo (lion) details",
                        "params": {"key": 5219404},
                    }
                ],
            },
            "match_species_name": {
                "description": "Match a scientific name to GBIF taxonomy",
                "parameters": {
                    "name": {
                        "type": "string",
                        "description": "Scientific name to match",
                        "required": True,
                    },
                    "kingdom": {
                        "type": "string",
                        "description": "Kingdom to narrow down the match (e.g., 'Animalia', 'Plantae')",
                        "required": False,
                    },
                    "rank": {
                        "type": "string",
                        "description": "Expected taxonomic rank",
                        "required": False,
                    },
                    "strict": {
                        "type": "boolean",
                        "description": "Use strict matching (default: False)",
                        "required": False,
                    },
                },
                "examples": [
                    {
                        "description": "Match Panthera leo",
                        "params": {"name": "Panthera leo", "kingdom": "Animalia"},
                    }
                ],
            },
            "search_occurrences": {
                "description": "Search for species occurrence records",
                "parameters": {
                    "taxonKey": {
                        "type": "integer",
                        "description": "GBIF taxon key to filter by species",
                        "required": False,
                    },
                    "country": {
                        "type": "string",
                        "description": "ISO 2-letter country code (e.g., 'US', 'GB')",
                        "required": False,
                    },
                    "year": {
                        "type": "string",
                        "description": "Year or year range (e.g., '2020' or '2010,2020')",
                        "required": False,
                    },
                    "basisOfRecord": {
                        "type": "string",
                        "description": "Type of record (e.g., 'HUMAN_OBSERVATION', 'PRESERVED_SPECIMEN')",
                        "required": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20, max: 300)",
                        "required": False,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "required": False,
                    },
                },
                "examples": [
                    {
                        "description": "Search for lion occurrences in Kenya",
                        "params": {"taxonKey": 5219404, "country": "KE", "limit": 50},
                    }
                ],
            },
            "get_occurrence_by_key": {
                "description": "Get detailed occurrence record by key",
                "parameters": {
                    "key": {
                        "type": "integer",
                        "description": "GBIF occurrence key",
                        "required": True,
                    },
                },
            },
            "search_datasets": {
                "description": "Search for datasets in GBIF",
                "parameters": {
                    "q": {
                        "type": "string",
                        "description": "Search query string",
                        "required": False,
                    },
                    "type": {
                        "type": "string",
                        "description": "Dataset type (e.g., 'OCCURRENCE', 'CHECKLIST', 'METADATA')",
                        "required": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20)",
                        "required": False,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "required": False,
                    },
                },
            },
            "get_dataset_by_key": {
                "description": "Get detailed dataset information by key",
                "parameters": {
                    "key": {
                        "type": "string",
                        "description": "GBIF dataset key (UUID)",
                        "required": True,
                    },
                },
            },
            "get_species_vernacular_names": {
                "description": "Get common/vernacular names for a species",
                "parameters": {
                    "key": {
                        "type": "integer",
                        "description": "GBIF species key",
                        "required": True,
                    },
                },
            },
            "get_species_children": {
                "description": "Get direct children taxa of a species",
                "parameters": {
                    "key": {
                        "type": "integer",
                        "description": "GBIF species key",
                        "required": True,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20)",
                        "required": False,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "required": False,
                    },
                },
            },
            "get_species_parents": {
                "description": "Get parent taxa hierarchy for a species",
                "parameters": {
                    "key": {
                        "type": "integer",
                        "description": "GBIF species key",
                        "required": True,
                    },
                },
            },
            "get_occurrence_count": {
                "description": "Get count of occurrence records matching criteria",
                "parameters": {
                    "taxonKey": {
                        "type": "integer",
                        "description": "GBIF taxon key to filter by species",
                        "required": False,
                    },
                    "country": {
                        "type": "string",
                        "description": "ISO 2-letter country code",
                        "required": False,
                    },
                    "year": {
                        "type": "string",
                        "description": "Year or year range",
                        "required": False,
                    },
                },
            },
            "search_organizations": {
                "description": "Search for publishing organizations",
                "parameters": {
                    "q": {
                        "type": "string",
                        "description": "Search query string",
                        "required": False,
                    },
                    "country": {
                        "type": "string",
                        "description": "ISO 2-letter country code",
                        "required": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20)",
                        "required": False,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "required": False,
                    },
                },
            },
        }

        return schemas.get(operation)

