"""
CourtListener (Free Law Project) API Provider

Provides access to comprehensive legal data from CourtListener including opinions,
dockets, judges, oral arguments, and citations.

CourtListener is a free legal research website containing millions of legal opinions
from federal and state courts, as well as extensive PACER data.

API Documentation: https://www.courtlistener.com/help/api/rest/
Interactive API Docs: https://www.courtlistener.com/api/rest-info/

API Key Required - Register at: https://www.courtlistener.com/sign-in/register/

IMPORTANT - CourtListener API Rules:
1. API Key Required: Must register for a free API key
2. Rate Limiting: Default is 5,000 requests per hour for authenticated users
3. Attribution: Acknowledge Free Law Project when using the data
4. Data Freshness: Data is updated regularly from court sources and PACER
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


class CourtListenerProvider(BaseAPIProvider):
    """
    CourtListener API provider for comprehensive legal data.

    Provides access to:
    - Legal opinions and case law
    - Court dockets and filings
    - Judges and judicial information
    - Oral argument audio recordings
    - Legal citations and citation networks
    - PACER data and RECAP archive
    """

    BASE_URL = "https://www.courtlistener.com/api/rest/v4"

    @property
    def name(self) -> str:
        return "courtlistener"

    @property
    def description(self) -> str:
        return "CourtListener (Free Law Project) API for legal opinions, dockets, judges, oral arguments, and citations"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_opinions",
            "get_opinion",
            "search_dockets",
            "get_docket",
            "search_judges",
            "get_judge",
            "search_oral_arguments",
            "get_oral_argument",
            "search_citations",
            "get_citation",
            "search_courts",
            "get_court",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for CourtListener operations"""

        if operation == "search_opinions":
            # At least one search parameter is recommended
            if not any(key in params for key in ["q", "case_name", "court", "judge", "cited_by"]):
                return False, "At least one search parameter is recommended (q, case_name, court, judge, or cited_by)"

        elif operation == "get_opinion":
            if "opinion_id" not in params:
                return False, "Missing required parameter: opinion_id"

        elif operation == "search_dockets":
            # At least one search parameter is recommended
            if not any(key in params for key in ["q", "docket_number", "court", "case_name"]):
                return False, "At least one search parameter is recommended (q, docket_number, court, or case_name)"

        elif operation == "get_docket":
            if "docket_id" not in params:
                return False, "Missing required parameter: docket_id"

        elif operation == "search_judges":
            # At least one search parameter is recommended
            if not any(key in params for key in ["q", "name", "court"]):
                return False, "At least one search parameter is recommended (q, name, or court)"

        elif operation == "get_judge":
            if "judge_id" not in params:
                return False, "Missing required parameter: judge_id"

        elif operation == "search_oral_arguments":
            # At least one search parameter is recommended
            if not any(key in params for key in ["q", "case_name", "court", "judge"]):
                return False, "At least one search parameter is recommended (q, case_name, court, or judge)"

        elif operation == "get_oral_argument":
            if "audio_id" not in params:
                return False, "Missing required parameter: audio_id"

        elif operation == "search_citations":
            # At least one search parameter is recommended
            if not any(key in params for key in ["citing_opinion", "cited_opinion"]):
                return False, "At least one search parameter is recommended (citing_opinion or cited_opinion)"

        elif operation == "get_citation":
            if "citation_id" not in params:
                return False, "Missing required parameter: citation_id"

        elif operation == "get_court":
            if "court_id" not in params:
                return False, "Missing required parameter: court_id"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_opinions",
        description="Search for legal opinions and case law with advanced filtering",
    )
    def search_opinions(
        self,
        q: Optional[str] = None,
        case_name: Optional[str] = None,
        court: Optional[str] = None,
        judge: Optional[str] = None,
        cited_by: Optional[int] = None,
        date_filed_after: Optional[str] = None,
        date_filed_before: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for legal opinions and case law.

        Args:
            q: Full-text search query
            case_name: Case name to search for
            court: Court identifier (e.g., 'ca9', 'scotus')
            judge: Judge name to filter by
            cited_by: Opinion ID that cites the results
            date_filed_after: Filter opinions filed after this date (YYYY-MM-DD)
            date_filed_before: Filter opinions filed before this date (YYYY-MM-DD)
            page: Page number for pagination
            page_size: Results per page (max 100)

        Returns:
            Dictionary containing opinion search results
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if case_name:
            params["case_name"] = case_name
        if court:
            params["court"] = court
        if judge:
            params["judge"] = judge
        if cited_by:
            params["cited_by"] = cited_by
        if date_filed_after:
            params["date_filed_after"] = date_filed_after
        if date_filed_before:
            params["date_filed_before"] = date_filed_before
        if page:
            params["page"] = page
        if page_size:
            params["page_size"] = page_size

        return self.execute("search_opinions", params)

    @expose_operation(
        operation_name="get_opinion",
        description="Get detailed information about a specific legal opinion",
    )
    def get_opinion(self, opinion_id: int) -> Dict[str, Any]:
        """
        Get detailed opinion information.

        Args:
            opinion_id: CourtListener opinion ID

        Returns:
            Dictionary containing detailed opinion information
        """
        return self.execute("get_opinion", {"opinion_id": opinion_id})

    @expose_operation(
        operation_name="search_dockets",
        description="Search for court dockets and case filings",
    )
    def search_dockets(
        self,
        q: Optional[str] = None,
        docket_number: Optional[str] = None,
        court: Optional[str] = None,
        case_name: Optional[str] = None,
        date_filed_after: Optional[str] = None,
        date_filed_before: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for court dockets.

        Args:
            q: Full-text search query
            docket_number: Docket number to search for
            court: Court identifier
            case_name: Case name to search for
            date_filed_after: Filter dockets filed after this date (YYYY-MM-DD)
            date_filed_before: Filter dockets filed before this date (YYYY-MM-DD)
            page: Page number for pagination
            page_size: Results per page (max 100)

        Returns:
            Dictionary containing docket search results
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if docket_number:
            params["docket_number"] = docket_number
        if court:
            params["court"] = court
        if case_name:
            params["case_name"] = case_name
        if date_filed_after:
            params["date_filed_after"] = date_filed_after
        if date_filed_before:
            params["date_filed_before"] = date_filed_before
        if page:
            params["page"] = page
        if page_size:
            params["page_size"] = page_size

        return self.execute("search_dockets", params)

    @expose_operation(
        operation_name="get_docket",
        description="Get detailed information about a specific docket",
    )
    def get_docket(self, docket_id: int) -> Dict[str, Any]:
        """
        Get detailed docket information.

        Args:
            docket_id: CourtListener docket ID

        Returns:
            Dictionary containing detailed docket information
        """
        return self.execute("get_docket", {"docket_id": docket_id})

    @expose_operation(
        operation_name="search_judges",
        description="Search for judges and judicial information",
    )
    def search_judges(
        self,
        q: Optional[str] = None,
        name: Optional[str] = None,
        court: Optional[str] = None,
        appointer: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for judges.

        Args:
            q: Full-text search query
            name: Judge name to search for
            court: Court identifier
            appointer: Name of appointing authority
            page: Page number for pagination
            page_size: Results per page (max 100)

        Returns:
            Dictionary containing judge search results
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if name:
            params["name"] = name
        if court:
            params["court"] = court
        if appointer:
            params["appointer"] = appointer
        if page:
            params["page"] = page
        if page_size:
            params["page_size"] = page_size

        return self.execute("search_judges", params)

    @expose_operation(
        operation_name="get_judge",
        description="Get detailed information about a specific judge",
    )
    def get_judge(self, judge_id: int) -> Dict[str, Any]:
        """
        Get detailed judge information.

        Args:
            judge_id: CourtListener judge/person ID

        Returns:
            Dictionary containing detailed judge information
        """
        return self.execute("get_judge", {"judge_id": judge_id})

    @expose_operation(
        operation_name="search_oral_arguments",
        description="Search for oral argument audio recordings",
    )
    def search_oral_arguments(
        self,
        q: Optional[str] = None,
        case_name: Optional[str] = None,
        court: Optional[str] = None,
        judge: Optional[str] = None,
        date_argued_after: Optional[str] = None,
        date_argued_before: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for oral argument audio recordings.

        Args:
            q: Full-text search query
            case_name: Case name to search for
            court: Court identifier
            judge: Judge name to filter by
            date_argued_after: Filter arguments after this date (YYYY-MM-DD)
            date_argued_before: Filter arguments before this date (YYYY-MM-DD)
            page: Page number for pagination
            page_size: Results per page (max 100)

        Returns:
            Dictionary containing oral argument search results
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if case_name:
            params["case_name"] = case_name
        if court:
            params["court"] = court
        if judge:
            params["judge"] = judge
        if date_argued_after:
            params["date_argued_after"] = date_argued_after
        if date_argued_before:
            params["date_argued_before"] = date_argued_before
        if page:
            params["page"] = page
        if page_size:
            params["page_size"] = page_size

        return self.execute("search_oral_arguments", params)

    @expose_operation(
        operation_name="get_oral_argument",
        description="Get detailed information about a specific oral argument",
    )
    def get_oral_argument(self, audio_id: int) -> Dict[str, Any]:
        """
        Get detailed oral argument information.

        Args:
            audio_id: CourtListener audio ID

        Returns:
            Dictionary containing detailed oral argument information
        """
        return self.execute("get_oral_argument", {"audio_id": audio_id})

    @expose_operation(
        operation_name="search_citations",
        description="Search for legal citations and citation networks",
    )
    def search_citations(
        self,
        citing_opinion: Optional[int] = None,
        cited_opinion: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for legal citations.

        Args:
            citing_opinion: Opinion ID that cites other opinions
            cited_opinion: Opinion ID that is cited by other opinions
            page: Page number for pagination
            page_size: Results per page (max 100)

        Returns:
            Dictionary containing citation search results
        """
        params: Dict[str, Any] = {}
        if citing_opinion:
            params["citing_opinion"] = citing_opinion
        if cited_opinion:
            params["cited_opinion"] = cited_opinion
        if page:
            params["page"] = page
        if page_size:
            params["page_size"] = page_size

        return self.execute("search_citations", params)

    @expose_operation(
        operation_name="get_citation",
        description="Get detailed information about a specific citation",
    )
    def get_citation(self, citation_id: int) -> Dict[str, Any]:
        """
        Get detailed citation information.

        Args:
            citation_id: CourtListener citation ID

        Returns:
            Dictionary containing detailed citation information
        """
        return self.execute("get_citation", {"citation_id": citation_id})

    @expose_operation(
        operation_name="search_courts",
        description="Search for court information",
    )
    def search_courts(
        self,
        q: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for courts.

        Args:
            q: Full-text search query
            jurisdiction: Jurisdiction filter (e.g., 'F' for federal, 'S' for state)
            page: Page number for pagination
            page_size: Results per page (max 100)

        Returns:
            Dictionary containing court search results
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if page:
            params["page"] = page
        if page_size:
            params["page_size"] = page_size

        return self.execute("search_courts", params)

    @expose_operation(
        operation_name="get_court",
        description="Get detailed information about a specific court",
    )
    def get_court(self, court_id: str) -> Dict[str, Any]:
        """
        Get detailed court information.

        Args:
            court_id: CourtListener court ID (e.g., 'scotus', 'ca9')

        Returns:
            Dictionary containing detailed court information
        """
        return self.execute("get_court", {"court_id": court_id})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from CourtListener API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for CourtListener provider")

        # Get API key from config
        api_key = self._get_api_key("COURTLISTENER_API_KEY")
        if not api_key:
            raise ValueError("CourtListener API key is required. Register at https://www.courtlistener.com/sign-in/register/")

        timeout = self.config.get("timeout", 30)

        # Build headers with authentication
        headers = {
            "Authorization": f"Token {api_key}",
        }

        # Build endpoint based on operation
        if operation == "search_opinions":
            endpoint = f"{self.BASE_URL}/search/"
            query_params = {"type": "o"}  # 'o' for opinions

            # Add search parameters
            for key in ["q", "case_name", "court", "judge", "cited_by", "date_filed_after", "date_filed_before", "page", "page_size"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_opinion":
            opinion_id = params["opinion_id"]
            endpoint = f"{self.BASE_URL}/opinions/{opinion_id}/"
            query_params = {}

        elif operation == "search_dockets":
            endpoint = f"{self.BASE_URL}/search/"
            query_params = {"type": "r"}  # 'r' for RECAP/dockets

            # Add search parameters
            for key in ["q", "docket_number", "court", "case_name", "date_filed_after", "date_filed_before", "page", "page_size"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_docket":
            docket_id = params["docket_id"]
            endpoint = f"{self.BASE_URL}/dockets/{docket_id}/"
            query_params = {}

        elif operation == "search_judges":
            endpoint = f"{self.BASE_URL}/search/"
            query_params = {"type": "p"}  # 'p' for people/judges

            # Add search parameters
            for key in ["q", "name", "court", "appointer", "page", "page_size"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_judge":
            judge_id = params["judge_id"]
            endpoint = f"{self.BASE_URL}/people/{judge_id}/"
            query_params = {}

        elif operation == "search_oral_arguments":
            endpoint = f"{self.BASE_URL}/search/"
            query_params = {"type": "oa"}  # 'oa' for oral arguments

            # Add search parameters
            for key in ["q", "case_name", "court", "judge", "date_argued_after", "date_argued_before", "page", "page_size"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_oral_argument":
            audio_id = params["audio_id"]
            endpoint = f"{self.BASE_URL}/audio/{audio_id}/"
            query_params = {}

        elif operation == "search_citations":
            endpoint = f"{self.BASE_URL}/opinions-cited/"
            query_params = {}

            # Add search parameters
            for key in ["citing_opinion", "cited_opinion", "page", "page_size"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_citation":
            citation_id = params["citation_id"]
            endpoint = f"{self.BASE_URL}/opinions-cited/{citation_id}/"
            query_params = {}

        elif operation == "search_courts":
            endpoint = f"{self.BASE_URL}/courts/"
            query_params = {}

            # Add search parameters
            for key in ["q", "jurisdiction", "page", "page_size"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_court":
            court_id = params["court_id"]
            endpoint = f"{self.BASE_URL}/courts/{court_id}/"
            query_params = {}

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request with proper headers
        try:
            response = requests.get(
                endpoint,
                params=query_params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()

            # CourtListener API returns data in 'results' key for search endpoints
            # and direct object for detail endpoints
            return self._format_response(
                operation=operation,
                data=data,
                source=f"CourtListener API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"CourtListener API request failed: {e}")
            raise Exception(f"CourtListener API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for CourtListener API operations"""

        schemas = {
            "search_opinions": {
                "description": "Search for legal opinions and case law with advanced filtering",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Full-text search query",
                        "examples": ["constitutional law", "habeas corpus", "first amendment"],
                    },
                    "case_name": {
                        "type": "string",
                        "required": False,
                        "description": "Case name to search for",
                        "examples": ["Brown v. Board of Education", "Roe v. Wade"],
                    },
                    "court": {
                        "type": "string",
                        "required": False,
                        "description": "Court identifier",
                        "examples": ["scotus", "ca9", "ca2", "dcd"],
                    },
                    "judge": {
                        "type": "string",
                        "required": False,
                        "description": "Judge name to filter by",
                        "examples": ["Sotomayor", "Roberts", "Ginsburg"],
                    },
                    "cited_by": {
                        "type": "integer",
                        "required": False,
                        "description": "Opinion ID that cites the results",
                        "examples": [123456, 789012],
                    },
                    "date_filed_after": {
                        "type": "string",
                        "required": False,
                        "description": "Filter opinions filed after this date (YYYY-MM-DD)",
                        "examples": ["2020-01-01", "2023-06-15"],
                    },
                    "date_filed_before": {
                        "type": "string",
                        "required": False,
                        "description": "Filter opinions filed before this date (YYYY-MM-DD)",
                        "examples": ["2024-12-31", "2023-12-31"],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                        "examples": [1, 2, 3],
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                        "examples": [10, 25, 50, 100],
                    },
                },
            },
            "get_opinion": {
                "description": "Get detailed information about a specific legal opinion",
                "parameters": {
                    "opinion_id": {
                        "type": "integer",
                        "required": True,
                        "description": "CourtListener opinion ID",
                        "examples": [123456, 789012],
                    },
                },
            },
            "search_dockets": {
                "description": "Search for court dockets and case filings",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Full-text search query",
                        "examples": ["patent infringement", "securities fraud"],
                    },
                    "docket_number": {
                        "type": "string",
                        "required": False,
                        "description": "Docket number to search for",
                        "examples": ["1:20-cv-12345", "22-cv-1234"],
                    },
                    "court": {
                        "type": "string",
                        "required": False,
                        "description": "Court identifier",
                        "examples": ["dcd", "nysd", "cand"],
                    },
                    "case_name": {
                        "type": "string",
                        "required": False,
                        "description": "Case name to search for",
                        "examples": ["Smith v. Jones", "United States v. Doe"],
                    },
                    "date_filed_after": {
                        "type": "string",
                        "required": False,
                        "description": "Filter dockets filed after this date (YYYY-MM-DD)",
                    },
                    "date_filed_before": {
                        "type": "string",
                        "required": False,
                        "description": "Filter dockets filed before this date (YYYY-MM-DD)",
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                    },
                },
            },
            "get_docket": {
                "description": "Get detailed information about a specific docket",
                "parameters": {
                    "docket_id": {
                        "type": "integer",
                        "required": True,
                        "description": "CourtListener docket ID",
                        "examples": [123456, 789012],
                    },
                },
            },
            "search_judges": {
                "description": "Search for judges and judicial information",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Full-text search query",
                        "examples": ["Sotomayor", "Roberts"],
                    },
                    "name": {
                        "type": "string",
                        "required": False,
                        "description": "Judge name to search for",
                        "examples": ["Sonia Sotomayor", "John Roberts"],
                    },
                    "court": {
                        "type": "string",
                        "required": False,
                        "description": "Court identifier",
                        "examples": ["scotus", "ca9"],
                    },
                    "appointer": {
                        "type": "string",
                        "required": False,
                        "description": "Name of appointing authority",
                        "examples": ["Obama", "Trump", "Biden"],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                    },
                },
            },
            "get_judge": {
                "description": "Get detailed information about a specific judge",
                "parameters": {
                    "judge_id": {
                        "type": "integer",
                        "required": True,
                        "description": "CourtListener judge/person ID",
                        "examples": [123, 456],
                    },
                },
            },
            "search_oral_arguments": {
                "description": "Search for oral argument audio recordings",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Full-text search query",
                        "examples": ["constitutional law", "civil rights"],
                    },
                    "case_name": {
                        "type": "string",
                        "required": False,
                        "description": "Case name to search for",
                        "examples": ["Brown v. Board of Education"],
                    },
                    "court": {
                        "type": "string",
                        "required": False,
                        "description": "Court identifier",
                        "examples": ["scotus", "ca9"],
                    },
                    "judge": {
                        "type": "string",
                        "required": False,
                        "description": "Judge name to filter by",
                        "examples": ["Sotomayor", "Roberts"],
                    },
                    "date_argued_after": {
                        "type": "string",
                        "required": False,
                        "description": "Filter arguments after this date (YYYY-MM-DD)",
                        "examples": ["2020-01-01"],
                    },
                    "date_argued_before": {
                        "type": "string",
                        "required": False,
                        "description": "Filter arguments before this date (YYYY-MM-DD)",
                        "examples": ["2024-12-31"],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                    },
                },
            },
            "get_oral_argument": {
                "description": "Get detailed information about a specific oral argument",
                "parameters": {
                    "audio_id": {
                        "type": "integer",
                        "required": True,
                        "description": "CourtListener audio ID",
                        "examples": [123456, 789012],
                    },
                },
            },
            "search_citations": {
                "description": "Search for legal citations and citation networks",
                "parameters": {
                    "citing_opinion": {
                        "type": "integer",
                        "required": False,
                        "description": "Opinion ID that cites other opinions",
                        "examples": [123456],
                    },
                    "cited_opinion": {
                        "type": "integer",
                        "required": False,
                        "description": "Opinion ID that is cited by other opinions",
                        "examples": [789012],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                    },
                },
            },
            "get_citation": {
                "description": "Get detailed information about a specific citation",
                "parameters": {
                    "citation_id": {
                        "type": "integer",
                        "required": True,
                        "description": "CourtListener citation ID",
                        "examples": [123456],
                    },
                },
            },
            "search_courts": {
                "description": "Search for court information",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Full-text search query",
                        "examples": ["supreme court", "district court"],
                    },
                    "jurisdiction": {
                        "type": "string",
                        "required": False,
                        "description": "Jurisdiction filter (e.g., 'F' for federal, 'S' for state)",
                        "examples": ["F", "S", "FD", "FB"],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                    },
                },
            },
            "get_court": {
                "description": "Get detailed information about a specific court",
                "parameters": {
                    "court_id": {
                        "type": "string",
                        "required": True,
                        "description": "CourtListener court ID",
                        "examples": ["scotus", "ca9", "ca2", "dcd", "nysd"],
                    },
                },
            },
        }

        return schemas.get(operation)

