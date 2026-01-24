"""
SEC EDGAR API Provider

Provides access to SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval)
system for company filings, financial data, and XBRL information.

API Documentation: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
Base URL: https://data.sec.gov
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from aiecs.tools.apisource.providers.base import (
    BaseAPIProvider,
    expose_operation,
)

logger = logging.getLogger(__name__)

# Optional HTTP client - graceful degradation
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class SECEdgarProvider(BaseAPIProvider):
    """
    SEC EDGAR API provider for company filings and financial data.

    Provides access to:
    - Company submissions and filing history
    - XBRL financial data
    - Company facts and concepts
    - Mutual fund prospectuses
    """

    BASE_URL = "https://data.sec.gov"

    @property
    def name(self) -> str:
        return "secedgar"

    @property
    def description(self) -> str:
        return "SEC EDGAR API for company filings, financial data, and XBRL information"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_company_submissions",
            "get_company_concept",
            "get_company_facts",
            "search_filings",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for SEC EDGAR operations with detailed guidance"""

        if operation == "get_company_submissions":
            if "cik" not in params:
                return False, (
                    "Missing required parameter: cik\n"
                    "Example: {'cik': '0000320193'}\n"
                    "CIK must be a 10-digit string (padded with leading zeros)"
                )

        elif operation == "get_company_concept":
            if "cik" not in params:
                return False, "Missing required parameter: cik"
            if "taxonomy" not in params:
                return False, (
                    "Missing required parameter: taxonomy\n"
                    "Example: 'us-gaap' or 'ifrs-full'"
                )
            if "tag" not in params:
                return False, (
                    "Missing required parameter: tag\n"
                    "Example: 'AccountsPayableCurrent' or 'Assets'"
                )

        elif operation == "get_company_facts":
            if "cik" not in params:
                return False, "Missing required parameter: cik"

        elif operation == "search_filings":
            if "query" not in params:
                return False, (
                    "Missing required parameter: query\n"
                    "Example: {'query': 'Apple Inc', 'form_type': '10-K'}"
                )

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_company_submissions",
        description="Get company filing history and submission data from SEC EDGAR",
    )
    def get_company_submissions(self, cik: str) -> Dict[str, Any]:
        """
        Get company submissions and filing history.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier (e.g., '0000320193' for Apple)

        Returns:
            Dictionary containing company information and filing history
        """
        # Ensure CIK is properly formatted (10 digits with leading zeros)
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {"cik": cik_formatted}

        return self.execute("get_company_submissions", params)

    @expose_operation(
        operation_name="get_company_concept",
        description="Get XBRL concept data for a specific company and financial metric",
    )
    def get_company_concept(
        self,
        cik: str,
        taxonomy: str,
        tag: str,
    ) -> Dict[str, Any]:
        """
        Get XBRL concept data for a company.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier
            taxonomy: Taxonomy (e.g., 'us-gaap', 'ifrs-full', 'dei')
            tag: XBRL tag (e.g., 'AccountsPayableCurrent', 'Assets', 'Revenues')

        Returns:
            Dictionary containing XBRL concept data across all filings
        """
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {
            "cik": cik_formatted,
            "taxonomy": taxonomy,
            "tag": tag,
        }

        return self.execute("get_company_concept", params)

    @expose_operation(
        operation_name="get_company_facts",
        description="Get all XBRL facts for a specific company",
    )
    def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """
        Get all XBRL facts for a company.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier

        Returns:
            Dictionary containing all XBRL facts for the company
        """
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {"cik": cik_formatted}

        return self.execute("get_company_facts", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from SEC EDGAR API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests library is required for SEC EDGAR provider. Install with: pip install requests"
            )

        # SEC requires a User-Agent header
        # Format: User-Agent: Sample Company Name AdminContact@<sample company domain>.com
        user_agent = self.config.get(
            "user_agent",
            "APISourceTool contact@example.com"
        )

        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

        # Build endpoint based on operation
        if operation == "get_company_submissions":
            cik = params["cik"]
            endpoint = f"{self.BASE_URL}/submissions/CIK{cik}.json"
            query_params = {}

        elif operation == "get_company_concept":
            cik = params["cik"]
            taxonomy = params["taxonomy"]
            tag = params["tag"]
            endpoint = f"{self.BASE_URL}/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json"
            query_params = {}

        elif operation == "get_company_facts":
            cik = params["cik"]
            endpoint = f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json"
            query_params = {}

        elif operation == "search_filings":
            # Note: SEC doesn't have a direct search API endpoint
            # This would require using the full-text search on sec.gov
            # For now, we'll return an error suggesting to use get_company_submissions
            raise ValueError(
                "Direct search is not supported by SEC EDGAR API. "
                "Use get_company_submissions with a known CIK instead. "
                "You can find CIKs at https://www.sec.gov/edgar/searchedgar/companysearch.html"
            )

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        timeout = self.config.get("timeout", 30)
        try:
            response = requests.get(endpoint, params=query_params, headers=headers, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Format the response based on operation
            if operation == "get_company_submissions":
                # Extract relevant submission data
                result_data = {
                    "cik": data.get("cik"),
                    "entityType": data.get("entityType"),
                    "sic": data.get("sic"),
                    "sicDescription": data.get("sicDescription"),
                    "name": data.get("name"),
                    "tickers": data.get("tickers", []),
                    "exchanges": data.get("exchanges", []),
                    "filings": data.get("filings", {}),
                }
            elif operation in ["get_company_concept", "get_company_facts"]:
                # Return full XBRL data
                result_data = data
            else:
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"SEC EDGAR - {endpoint}",
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.error(f"SEC EDGAR resource not found: {endpoint}")
                raise Exception(
                    f"SEC EDGAR resource not found. "
                    f"Please verify the CIK or parameters are correct. "
                    f"Error: {str(e)}"
                )
            else:
                self.logger.error(f"SEC EDGAR API request failed: {e}")
                raise Exception(f"SEC EDGAR API request failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"SEC EDGAR API request failed: {e}")
            raise Exception(f"SEC EDGAR API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for SEC EDGAR operations"""

        schemas = {
            "get_company_submissions": {
                "description": "Get company filing history and submission data from SEC EDGAR",
                "parameters": {
                    "cik": {
                        "type": "string",
                        "required": True,
                        "description": "Central Index Key (CIK) - 10-digit company identifier",
                        "examples": ["0000320193", "0001318605", "0000789019"],
                        "validation": {
                            "pattern": r"^\d{10}$",
                            "note": "CIK must be 10 digits with leading zeros",
                        },
                    },
                },
                "examples": [
                    {
                        "description": "Get Apple Inc. filings",
                        "params": {"cik": "0000320193"},
                    },
                    {
                        "description": "Get Tesla Inc. filings",
                        "params": {"cik": "0001318605"},
                    },
                ],
            },
            "get_company_concept": {
                "description": "Get XBRL concept data for a specific company and financial metric",
                "parameters": {
                    "cik": {
                        "type": "string",
                        "required": True,
                        "description": "Central Index Key (CIK) - 10-digit company identifier",
                        "examples": ["0000320193", "0001318605"],
                    },
                    "taxonomy": {
                        "type": "string",
                        "required": True,
                        "description": "XBRL taxonomy (e.g., us-gaap, ifrs-full, dei)",
                        "examples": ["us-gaap", "ifrs-full", "dei"],
                    },
                    "tag": {
                        "type": "string",
                        "required": True,
                        "description": "XBRL tag/concept name",
                        "examples": [
                            "AccountsPayableCurrent",
                            "Assets",
                            "Revenues",
                            "NetIncomeLoss",
                        ],
                    },
                },
                "examples": [
                    {
                        "description": "Get Apple's Assets data",
                        "params": {
                            "cik": "0000320193",
                            "taxonomy": "us-gaap",
                            "tag": "Assets",
                        },
                    },
                ],
            },
            "get_company_facts": {
                "description": "Get all XBRL facts for a specific company",
                "parameters": {
                    "cik": {
                        "type": "string",
                        "required": True,
                        "description": "Central Index Key (CIK) - 10-digit company identifier",
                        "examples": ["0000320193", "0001318605"],
                    },
                },
                "examples": [
                    {
                        "description": "Get all XBRL facts for Apple Inc.",
                        "params": {"cik": "0000320193"},
                    },
                ],
            },
            "search_filings": {
                "description": "Search for company filings (Note: Direct search not supported, use get_company_submissions)",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query (not directly supported by API)",
                    },
                },
                "note": "SEC EDGAR API does not support direct search. Use get_company_submissions with a known CIK.",
            },
        }

        return schemas.get(operation)

    def calculate_data_quality(self, operation: str, data: Any, response_time_ms: float) -> Dict[str, Any]:
        """Calculate quality metadata specific to SEC EDGAR data"""

        # Get base quality from parent
        quality = super().calculate_data_quality(operation, data, response_time_ms)

        # SEC EDGAR-specific quality enhancements
        # SEC data is official regulatory filings
        quality["authority_level"] = "official"
        quality["confidence"] = 0.99  # Very high confidence in SEC data
        quality["freshness_hours"] = None  # Varies by filing

        # SEC data is highly structured and validated
        quality["completeness"] = 1.0

        return quality

