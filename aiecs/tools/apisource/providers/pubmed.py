"""
PubMed/NCBI E-utilities API Provider

Provides access to PubMed's extensive database of biomedical literature.
Supports paper search, metadata retrieval, and citation information.

API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
API key recommended but not required - improves rate limits from 3 to 10 requests/second

IMPORTANT - NCBI E-utilities API Rules:
1. Rate Limiting: Max 3 requests/second without API key, 10 with API key
2. User-Agent: Set a descriptive User-Agent header with email
3. API Key: Register for free at https://www.ncbi.nlm.nih.gov/account/
4. Caching: Cache responses when possible to reduce server load
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

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


class PubMedProvider(BaseAPIProvider):
    """
    PubMed/NCBI E-utilities API provider for biomedical literature.

    Provides access to:
    - Paper search by keywords, authors, journals
    - Paper metadata retrieval by PubMed ID (PMID)
    - Citation information and abstracts
    - MeSH terms and publication types
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    @property
    def name(self) -> str:
        return "pubmed"

    @property
    def description(self) -> str:
        return "PubMed/NCBI E-utilities API for biomedical and life sciences literature"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_papers",
            "get_paper_by_id",
            "search_by_author",
            "get_paper_details",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for PubMed operations"""

        if operation == "search_papers":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_paper_by_id":
            if "pmid" not in params:
                return False, "Missing required parameter: pmid"

        elif operation == "search_by_author":
            if "author" not in params:
                return False, "Missing required parameter: author"

        elif operation == "get_paper_details":
            if "pmid" not in params:
                return False, "Missing required parameter: pmid"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_papers",
        description="Search for papers in PubMed by query string",
    )
    def search_papers(
        self,
        query: str,
        max_results: Optional[int] = None,
        start: Optional[int] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for papers in PubMed.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 20, max: 10000)
            start: Starting index for pagination (default: 0)
            sort: Sort order - 'relevance', 'pub_date', 'author', 'journal' (default: relevance)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if max_results:
            params["max_results"] = max_results
        if start is not None:
            params["start"] = start
        if sort:
            params["sort"] = sort

        return self.execute("search_papers", params)

    @expose_operation(
        operation_name="get_paper_by_id",
        description="Get paper metadata by PubMed ID (PMID)",
    )
    def get_paper_by_id(self, pmid: str) -> Dict[str, Any]:
        """
        Get paper details by PubMed ID.

        Args:
            pmid: PubMed identifier (e.g., '12345678')

        Returns:
            Dictionary containing paper information
        """
        return self.execute("get_paper_by_id", {"pmid": pmid})

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
            max_results: Maximum number of results to return (default: 20)
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
        operation_name="get_paper_details",
        description="Get detailed paper information including abstract and citations",
    )
    def get_paper_details(self, pmid: str) -> Dict[str, Any]:
        """
        Get detailed paper information.

        Args:
            pmid: PubMed identifier (e.g., '12345678')

        Returns:
            Dictionary containing detailed paper information
        """
        return self.execute("get_paper_details", {"pmid": pmid})

    def _parse_esearch_result(self, xml_content: str) -> Dict[str, Any]:
        """Parse ESearch XML response"""
        root = ET.fromstring(xml_content)

        # Extract ID list
        id_list = []
        id_list_elem = root.find("IdList")
        if id_list_elem is not None:
            for id_elem in id_list_elem.findall("Id"):
                if id_elem.text:
                    id_list.append(id_elem.text)

        # Extract count and metadata
        count_elem = root.find("Count")
        ret_max_elem = root.find("RetMax")
        ret_start_elem = root.find("RetStart")

        result = {
            "pmids": id_list,
            "count": int(count_elem.text) if count_elem is not None and count_elem.text else 0,
            "ret_max": int(ret_max_elem.text) if ret_max_elem is not None and ret_max_elem.text else 0,
            "ret_start": int(ret_start_elem.text) if ret_start_elem is not None and ret_start_elem.text else 0,
        }

        return result

    def _parse_efetch_result(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse EFetch XML response"""
        root = ET.fromstring(xml_content)
        papers = []

        # Find all PubmedArticle elements
        for article_elem in root.findall(".//PubmedArticle"):
            paper: Dict[str, Any] = {}

            # Extract PMID
            pmid_elem = article_elem.find(".//PMID")
            if pmid_elem is not None and pmid_elem.text:
                paper["pmid"] = pmid_elem.text

            # Extract article title
            title_elem = article_elem.find(".//ArticleTitle")
            if title_elem is not None and title_elem.text:
                paper["title"] = title_elem.text

            # Extract abstract
            abstract_elem = article_elem.find(".//Abstract/AbstractText")
            if abstract_elem is not None and abstract_elem.text:
                paper["abstract"] = abstract_elem.text

            # Extract authors
            authors = []
            author_list = article_elem.find(".//AuthorList")
            if author_list is not None:
                for author_elem in author_list.findall("Author"):
                    last_name = author_elem.find("LastName")
                    fore_name = author_elem.find("ForeName")
                    if last_name is not None and last_name.text:
                        author_name = last_name.text
                        if fore_name is not None and fore_name.text:
                            author_name = f"{fore_name.text} {author_name}"
                        authors.append(author_name)
            if authors:
                paper["authors"] = authors

            # Extract journal
            journal_elem = article_elem.find(".//Journal/Title")
            if journal_elem is not None and journal_elem.text:
                paper["journal"] = journal_elem.text

            # Extract publication date
            pub_date_elem = article_elem.find(".//PubDate")
            if pub_date_elem is not None:
                year = pub_date_elem.find("Year")
                month = pub_date_elem.find("Month")
                day = pub_date_elem.find("Day")
                date_parts = []
                if year is not None and year.text:
                    date_parts.append(year.text)
                if month is not None and month.text:
                    date_parts.append(month.text)
                if day is not None and day.text:
                    date_parts.append(day.text)
                if date_parts:
                    paper["publication_date"] = "-".join(date_parts)

            # Extract DOI
            doi_elem = article_elem.find(".//ArticleId[@IdType='doi']")
            if doi_elem is not None and doi_elem.text:
                paper["doi"] = doi_elem.text

            # Extract MeSH terms
            mesh_terms = []
            mesh_list = article_elem.find(".//MeshHeadingList")
            if mesh_list is not None:
                for mesh_elem in mesh_list.findall("MeshHeading"):
                    descriptor = mesh_elem.find("DescriptorName")
                    if descriptor is not None and descriptor.text:
                        mesh_terms.append(descriptor.text)
            if mesh_terms:
                paper["mesh_terms"] = mesh_terms

            papers.append(paper)

        return papers

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from PubMed E-utilities API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for PubMed provider")

        timeout = self.config.get("timeout", 30)
        api_key = self._get_api_key()

        # Set User-Agent header as required by NCBI API etiquette
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)"
        )
        headers = {
            "User-Agent": user_agent,
        }

        try:
            if operation in ["search_papers", "search_by_author"]:
                # Use ESearch to search for papers
                search_params: Dict[str, Any] = {
                    "db": "pubmed",
                    "retmode": "xml",
                    "retmax": params.get("max_results", 20),
                    "retstart": params.get("start", 0),
                }

                if operation == "search_papers":
                    search_params["term"] = params["query"]
                    if "sort" in params:
                        sort_map = {
                            "relevance": "relevance",
                            "pub_date": "pub+date",
                            "author": "author",
                            "journal": "journal",
                        }
                        search_params["sort"] = sort_map.get(params["sort"], "relevance")
                elif operation == "search_by_author":
                    search_params["term"] = f"{params['author']}[Author]"

                if api_key:
                    search_params["api_key"] = api_key

                # Make ESearch request
                search_url = f"{self.BASE_URL}/esearch.fcgi"
                response = requests.get(
                    search_url,
                    params=search_params,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()

                # Parse search results
                search_result = self._parse_esearch_result(response.text)
                pmids = search_result["pmids"]

                # If we have PMIDs, fetch details
                if pmids:
                    # Fetch details for the PMIDs
                    fetch_params: Dict[str, Any] = {
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "retmode": "xml",
                    }
                    if api_key:
                        fetch_params["api_key"] = api_key

                    fetch_url = f"{self.BASE_URL}/efetch.fcgi"
                    fetch_response = requests.get(
                        fetch_url,
                        params=fetch_params,
                        headers=headers,
                        timeout=timeout
                    )
                    fetch_response.raise_for_status()

                    # Parse paper details
                    papers = self._parse_efetch_result(fetch_response.text)

                    # Format response with search metadata
                    response = self._format_response(
                        operation=operation,
                        data=papers,
                        source=f"PubMed E-utilities - {self.BASE_URL}",
                    )

                    # Add search-specific metadata
                    response["metadata"]["search_info"] = {
                        "total_results": search_result["count"],
                        "returned_results": len(papers),
                        "start_index": search_result["ret_start"],
                    }

                    return response
                else:
                    # Format response for empty results
                    response = self._format_response(
                        operation=operation,
                        data=[],
                        source=f"PubMed E-utilities - {self.BASE_URL}",
                    )

                    # Add search-specific metadata
                    response["metadata"]["search_info"] = {
                        "total_results": 0,
                        "returned_results": 0,
                        "start_index": 0,
                    }

                    return response

            elif operation in ["get_paper_by_id", "get_paper_details"]:
                # Use EFetch to get paper details
                pmid = params["pmid"]
                fetch_params: Dict[str, Any] = {
                    "db": "pubmed",
                    "id": pmid,
                    "retmode": "xml",
                }
                if api_key:
                    fetch_params["api_key"] = api_key

                fetch_url = f"{self.BASE_URL}/efetch.fcgi"
                response = requests.get(
                    fetch_url,
                    params=fetch_params,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()

                # Parse paper details
                papers = self._parse_efetch_result(response.text)

                # Return single paper for get_paper_by_id, full details for get_paper_details
                result_data = papers[0] if papers else {}

                return self._format_response(
                    operation=operation,
                    data=result_data,
                    source=f"PubMed E-utilities - {self.BASE_URL}",
                )

            else:
                raise ValueError(f"Unknown operation: {operation}")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"PubMed API request failed: {e}")
            raise Exception(f"PubMed API request failed: {str(e)}")
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse PubMed API response: {e}")
            raise Exception(f"Failed to parse PubMed API response: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for operation parameters"""

        schemas = {
            "search_papers": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (supports PubMed search syntax)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20, max: 10000)",
                        "minimum": 1,
                        "maximum": 10000,
                    },
                    "start": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "minimum": 0,
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort order",
                        "enum": ["relevance", "pub_date", "author", "journal"],
                    },
                },
                "required": ["query"],
            },
            "get_paper_by_id": {
                "type": "object",
                "properties": {
                    "pmid": {
                        "type": "string",
                        "description": "PubMed identifier (e.g., '12345678')",
                    },
                },
                "required": ["pmid"],
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
                        "description": "Maximum number of results to return (default: 20)",
                        "minimum": 1,
                        "maximum": 10000,
                    },
                    "start": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "minimum": 0,
                    },
                },
                "required": ["author"],
            },
            "get_paper_details": {
                "type": "object",
                "properties": {
                    "pmid": {
                        "type": "string",
                        "description": "PubMed identifier (e.g., '12345678')",
                    },
                },
                "required": ["pmid"],
            },
        }

        return schemas.get(operation)

