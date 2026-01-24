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
            "get_filing_documents",
            "get_filing_text",
            "get_filings_by_type",
            "calculate_financial_ratios",
            "get_financial_statement",
            "get_insider_transactions",
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
            if "cik" not in params:
                return False, (
                    "Missing required parameter: cik\n"
                    "Example: {'cik': '0000320193', 'form_type': '10-K'}"
                )

        elif operation == "get_filing_documents":
            if "cik" not in params:
                return False, "Missing required parameter: cik"
            if "accession_number" not in params:
                return False, (
                    "Missing required parameter: accession_number\n"
                    "Example: {'cik': '0000320193', 'accession_number': '0000320193-23-000077'}"
                )

        elif operation == "get_filing_text":
            if "cik" not in params:
                return False, "Missing required parameter: cik"
            if "accession_number" not in params:
                return False, "Missing required parameter: accession_number"

        elif operation == "get_filings_by_type":
            if "cik" not in params:
                return False, "Missing required parameter: cik"
            if "form_type" not in params:
                return False, (
                    "Missing required parameter: form_type\n"
                    "Example: {'cik': '0000320193', 'form_type': '10-K'}"
                )

        elif operation == "calculate_financial_ratios":
            if "cik" not in params:
                return False, "Missing required parameter: cik"

        elif operation == "get_financial_statement":
            if "cik" not in params:
                return False, "Missing required parameter: cik"
            if "statement_type" not in params:
                return False, (
                    "Missing required parameter: statement_type\n"
                    "Options: 'balance_sheet', 'income_statement', 'cash_flow'"
                )

        elif operation == "get_insider_transactions":
            if "cik" not in params:
                return False, "Missing required parameter: cik"

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

    @expose_operation(
        operation_name="get_filing_documents",
        description="Get filing documents and metadata for a specific accession number",
    )
    def get_filing_documents(
        self,
        cik: str,
        accession_number: str,
    ) -> Dict[str, Any]:
        """
        Get filing documents for a specific accession number.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier
            accession_number: SEC accession number (e.g., '0000320193-23-000077')

        Returns:
            Dictionary containing filing documents and metadata
        """
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {
            "cik": cik_formatted,
            "accession_number": accession_number,
        }

        return self.execute("get_filing_documents", params)

    @expose_operation(
        operation_name="get_filing_text",
        description="Get the full text content of a specific filing document",
    )
    def get_filing_text(
        self,
        cik: str,
        accession_number: str,
        document_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get the full text of a filing document.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier
            accession_number: SEC accession number
            document_name: Optional specific document name (defaults to primary document)

        Returns:
            Dictionary containing the filing text content
        """
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {
            "cik": cik_formatted,
            "accession_number": accession_number,
        }
        if document_name:
            params["document_name"] = document_name

        return self.execute("get_filing_text", params)

    @expose_operation(
        operation_name="get_filings_by_type",
        description="Get recent filings of a specific form type for a company",
    )
    def get_filings_by_type(
        self,
        cik: str,
        form_type: str,
        count: int = 10,
    ) -> Dict[str, Any]:
        """
        Get recent filings by form type.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier
            form_type: Form type (e.g., '10-K', '10-Q', '8-K', 'DEF 14A')
            count: Number of filings to return (default: 10)

        Returns:
            Dictionary containing list of filings
        """
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {
            "cik": cik_formatted,
            "form_type": form_type,
            "count": count,
        }

        return self.execute("get_filings_by_type", params)

    @expose_operation(
        operation_name="calculate_financial_ratios",
        description="Calculate common financial ratios from XBRL data",
    )
    def calculate_financial_ratios(
        self,
        cik: str,
        fiscal_year: Optional[int] = None,
        fiscal_quarter: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculate financial ratios for a company.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier
            fiscal_year: Optional fiscal year (defaults to most recent)
            fiscal_quarter: Optional fiscal quarter (1-4, for quarterly ratios)

        Returns:
            Dictionary containing calculated financial ratios
        """
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {"cik": cik_formatted}
        if fiscal_year:
            params["fiscal_year"] = fiscal_year
        if fiscal_quarter:
            params["fiscal_quarter"] = fiscal_quarter

        return self.execute("calculate_financial_ratios", params)

    @expose_operation(
        operation_name="get_financial_statement",
        description="Get formatted financial statement (balance sheet, income statement, or cash flow)",
    )
    def get_financial_statement(
        self,
        cik: str,
        statement_type: str,
        period: str = "annual",
        fiscal_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get formatted financial statement.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier
            statement_type: Type of statement ('balance_sheet', 'income_statement', 'cash_flow')
            period: 'annual' or 'quarterly' (default: 'annual')
            fiscal_year: Optional fiscal year (defaults to most recent)

        Returns:
            Dictionary containing formatted financial statement
        """
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {
            "cik": cik_formatted,
            "statement_type": statement_type,
            "period": period,
        }
        if fiscal_year:
            params["fiscal_year"] = fiscal_year

        return self.execute("get_financial_statement", params)

    @expose_operation(
        operation_name="get_insider_transactions",
        description="Get insider trading transactions (Form 4 filings)",
    )
    def get_insider_transactions(
        self,
        cik: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get insider transactions for a company.

        Args:
            cik: Central Index Key (CIK) - 10-digit identifier
            start_date: Optional start date (YYYY-MM-DD format)
            end_date: Optional end date (YYYY-MM-DD format)

        Returns:
            Dictionary containing insider transactions
        """
        cik_formatted = str(cik).zfill(10)
        params: Dict[str, Any] = {"cik": cik_formatted}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self.execute("get_insider_transactions", params)

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
            # Implement search using company submissions
            cik = params["cik"]
            endpoint = f"{self.BASE_URL}/submissions/CIK{cik}.json"
            query_params = {}

        elif operation == "get_filing_documents":
            # Get filing documents index
            cik = params["cik"]
            accession_number = params["accession_number"].replace("-", "")
            endpoint = f"{self.BASE_URL}/submissions/CIK{cik}.json"
            query_params = {}

        elif operation == "get_filing_text":
            # Get filing text - will be handled specially
            return self._fetch_filing_text(params, headers)

        elif operation == "get_filings_by_type":
            # Get filings by type using submissions
            cik = params["cik"]
            endpoint = f"{self.BASE_URL}/submissions/CIK{cik}.json"
            query_params = {}

        elif operation == "calculate_financial_ratios":
            # Calculate ratios from company facts
            return self._calculate_ratios(params)

        elif operation == "get_financial_statement":
            # Get formatted financial statement
            return self._get_formatted_statement(params)

        elif operation == "get_insider_transactions":
            # Get insider transactions (Form 4)
            return self._get_insider_data(params, headers)

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
            elif operation == "search_filings":
                # Filter filings based on form_type if provided
                form_type = params.get("form_type")
                filings = data.get("filings", {}).get("recent", {})
                result_data = self._filter_filings(filings, form_type, params.get("limit", 100))

            elif operation == "get_filing_documents":
                # Extract filing documents for specific accession number
                accession_number = params["accession_number"]
                filings = data.get("filings", {}).get("recent", {})
                result_data = self._extract_filing_documents(filings, accession_number, params["cik"])

            elif operation == "get_filings_by_type":
                # Filter by form type
                form_type = params["form_type"]
                count = params.get("count", 10)
                filings = data.get("filings", {}).get("recent", {})
                result_data = self._filter_filings_by_type(filings, form_type, count)

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

    def _filter_filings(self, filings: Dict[str, Any], form_type: Optional[str], limit: int) -> Dict[str, Any]:
        """Filter filings by form type"""
        if not filings:
            return {"filings": [], "count": 0}

        # Get filing arrays
        accession_numbers = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        report_dates = filings.get("reportDate", [])
        form_types = filings.get("form", [])
        primary_documents = filings.get("primaryDocument", [])

        # Filter by form type if specified
        filtered_filings = []
        for i in range(len(accession_numbers)):
            if form_type and form_types[i] != form_type:
                continue

            filtered_filings.append({
                "accessionNumber": accession_numbers[i],
                "filingDate": filing_dates[i],
                "reportDate": report_dates[i] if i < len(report_dates) else None,
                "formType": form_types[i],
                "primaryDocument": primary_documents[i] if i < len(primary_documents) else None,
            })

            if len(filtered_filings) >= limit:
                break

        return {
            "filings": filtered_filings,
            "count": len(filtered_filings),
            "form_type_filter": form_type,
        }

    def _filter_filings_by_type(self, filings: Dict[str, Any], form_type: str, count: int) -> Dict[str, Any]:
        """Filter filings by specific form type"""
        return self._filter_filings(filings, form_type, count)

    def _extract_filing_documents(self, filings: Dict[str, Any], accession_number: str, cik: str) -> Dict[str, Any]:
        """Extract filing documents for a specific accession number"""
        if not filings:
            return {"error": "No filings found"}

        # Find the filing with matching accession number
        accession_numbers = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        form_types = filings.get("form", [])
        primary_documents = filings.get("primaryDocument", [])

        # Normalize accession number (remove dashes)
        accession_normalized = accession_number.replace("-", "")

        for i, acc_num in enumerate(accession_numbers):
            if acc_num.replace("-", "") == accession_normalized:
                # Build document URLs
                cik_no_leading = cik.lstrip("0")
                base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading}/{accession_normalized}"

                primary_doc = primary_documents[i] if i < len(primary_documents) else None

                return {
                    "accessionNumber": acc_num,
                    "filingDate": filing_dates[i] if i < len(filing_dates) else None,
                    "formType": form_types[i] if i < len(form_types) else None,
                    "primaryDocument": primary_doc,
                    "primaryDocumentUrl": f"{base_url}/{primary_doc}" if primary_doc else None,
                    "indexUrl": f"{base_url}-index.html",
                    "baseUrl": base_url,
                }

        return {"error": f"Filing with accession number {accession_number} not found"}

    def _fetch_filing_text(self, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Fetch the full text of a filing document"""
        cik = params["cik"]
        accession_number = params["accession_number"].replace("-", "")
        document_name = params.get("document_name")

        # First, get the filing documents to find the primary document
        if not document_name:
            # Get submissions to find primary document
            submissions_url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
            timeout = self.config.get("timeout", 30)

            try:
                response = requests.get(submissions_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                data = response.json()

                filings = data.get("filings", {}).get("recent", {})
                filing_info = self._extract_filing_documents(filings, accession_number, cik)

                if "error" in filing_info:
                    raise Exception(filing_info["error"])

                document_name = filing_info.get("primaryDocument")
                if not document_name:
                    raise Exception("Primary document not found for this filing")

            except Exception as e:
                raise Exception(f"Failed to get filing information: {str(e)}")

        # Build document URL
        cik_no_leading = cik.lstrip("0")
        document_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading}/{accession_number}/{document_name}"

        # Fetch the document (HTML/TXT)
        headers_text = headers.copy()
        headers_text["Accept"] = "text/html,text/plain,application/xhtml+xml"

        try:
            response = requests.get(document_url, headers=headers_text, timeout=timeout)
            response.raise_for_status()

            result_data = {
                "accessionNumber": params["accession_number"],
                "documentName": document_name,
                "documentUrl": document_url,
                "content": response.text,
                "contentType": response.headers.get("Content-Type", "text/html"),
                "contentLength": len(response.text),
            }

            return self._format_response(
                operation="get_filing_text",
                data=result_data,
                source=f"SEC EDGAR - {document_url}",
            )

        except Exception as e:
            raise Exception(f"Failed to fetch filing text: {str(e)}")

    def _calculate_ratios(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate financial ratios from XBRL data"""
        cik = params["cik"]
        fiscal_year = params.get("fiscal_year")
        fiscal_quarter = params.get("fiscal_quarter")

        # Get company facts
        facts_params = {"cik": cik}
        facts_result = self.execute("get_company_facts", facts_params)
        facts_data = facts_result.get("data", {})

        if not facts_data or "facts" not in facts_data:
            raise Exception("Unable to retrieve company facts for ratio calculation")

        # Extract US-GAAP facts
        us_gaap = facts_data.get("facts", {}).get("us-gaap", {})

        # Helper function to get most recent value
        def get_recent_value(concept_name: str, period_type: str = "annual"):
            concept = us_gaap.get(concept_name, {})
            units = concept.get("units", {})
            usd_data = units.get("USD", [])

            if not usd_data:
                return None

            # Filter by fiscal year/quarter if specified
            filtered = usd_data
            if fiscal_year:
                filtered = [d for d in filtered if d.get("fy") == fiscal_year]
            if fiscal_quarter:
                filtered = [d for d in filtered if d.get("fp") == f"Q{fiscal_quarter}"]

            # Get most recent
            if filtered:
                # Sort by end date
                sorted_data = sorted(filtered, key=lambda x: x.get("end", ""), reverse=True)
                return sorted_data[0].get("val")

            return None

        # Calculate common ratios
        assets = get_recent_value("Assets")
        liabilities = get_recent_value("Liabilities")
        equity = get_recent_value("StockholdersEquity")
        current_assets = get_recent_value("AssetsCurrent")
        current_liabilities = get_recent_value("LiabilitiesCurrent")
        revenue = get_recent_value("Revenues")
        net_income = get_recent_value("NetIncomeLoss")

        ratios = {}

        # Liquidity Ratios
        if current_assets and current_liabilities and current_liabilities != 0:
            ratios["current_ratio"] = current_assets / current_liabilities

        # Leverage Ratios
        if liabilities and equity and equity != 0:
            ratios["debt_to_equity"] = liabilities / equity

        if liabilities and assets and assets != 0:
            ratios["debt_ratio"] = liabilities / assets

        # Profitability Ratios
        if net_income and revenue and revenue != 0:
            ratios["profit_margin"] = net_income / revenue

        if net_income and assets and assets != 0:
            ratios["return_on_assets"] = net_income / assets

        if net_income and equity and equity != 0:
            ratios["return_on_equity"] = net_income / equity

        result_data = {
            "cik": cik,
            "fiscal_year": fiscal_year,
            "fiscal_quarter": fiscal_quarter,
            "ratios": ratios,
            "raw_values": {
                "assets": assets,
                "liabilities": liabilities,
                "equity": equity,
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
                "revenue": revenue,
                "net_income": net_income,
            }
        }

        return self._format_response(
            operation="calculate_financial_ratios",
            data=result_data,
            source="SEC EDGAR - Calculated from XBRL data",
        )

    def _get_formatted_statement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted financial statement"""
        cik = params["cik"]
        statement_type = params["statement_type"]
        period = params.get("period", "annual")
        fiscal_year = params.get("fiscal_year")

        # Get company facts
        facts_params = {"cik": cik}
        facts_result = self.execute("get_company_facts", facts_params)
        facts_data = facts_result.get("data", {})

        if not facts_data or "facts" not in facts_data:
            raise Exception("Unable to retrieve company facts")

        us_gaap = facts_data.get("facts", {}).get("us-gaap", {})

        # Define statement line items
        statement_items = {
            "balance_sheet": [
                "AssetsCurrent", "AssetsNoncurrent", "Assets",
                "LiabilitiesCurrent", "LiabilitiesNoncurrent", "Liabilities",
                "StockholdersEquity", "LiabilitiesAndStockholdersEquity"
            ],
            "income_statement": [
                "Revenues", "CostOfRevenue", "GrossProfit",
                "OperatingExpenses", "OperatingIncomeLoss",
                "InterestExpense", "IncomeTaxExpense",
                "NetIncomeLoss", "EarningsPerShareBasic", "EarningsPerShareDiluted"
            ],
            "cash_flow": [
                "NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByUsedInInvestingActivities",
                "NetCashProvidedByUsedInFinancingActivities",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
            ]
        }

        items = statement_items.get(statement_type, [])
        statement_data = {}

        for item in items:
            concept = us_gaap.get(item, {})
            units = concept.get("units", {})
            usd_data = units.get("USD", [])

            if usd_data:
                # Filter by fiscal year if specified
                filtered = usd_data
                if fiscal_year:
                    filtered = [d for d in filtered if d.get("fy") == fiscal_year]

                # Get most recent
                if filtered:
                    sorted_data = sorted(filtered, key=lambda x: x.get("end", ""), reverse=True)
                    statement_data[item] = {
                        "value": sorted_data[0].get("val"),
                        "end_date": sorted_data[0].get("end"),
                        "fiscal_year": sorted_data[0].get("fy"),
                        "fiscal_period": sorted_data[0].get("fp"),
                    }

        result_data = {
            "cik": cik,
            "statement_type": statement_type,
            "period": period,
            "fiscal_year": fiscal_year,
            "line_items": statement_data,
        }

        return self._format_response(
            operation="get_financial_statement",
            data=result_data,
            source="SEC EDGAR - Formatted from XBRL data",
        )

    def _get_insider_data(self, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Get insider transactions (Form 4 filings)"""
        cik = params["cik"]
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        # Get company submissions
        submissions_url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
        timeout = self.config.get("timeout", 30)

        try:
            response = requests.get(submissions_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            filings = data.get("filings", {}).get("recent", {})

            # Filter for Form 4 filings
            form_4_filings = self._filter_filings_by_type(filings, "4", 100)

            # Further filter by date range if specified
            if start_date or end_date:
                filtered_filings = []
                for filing in form_4_filings.get("filings", []):
                    filing_date = filing.get("filingDate")
                    if start_date and filing_date < start_date:
                        continue
                    if end_date and filing_date > end_date:
                        continue
                    filtered_filings.append(filing)

                form_4_filings["filings"] = filtered_filings
                form_4_filings["count"] = len(filtered_filings)

            result_data = {
                "cik": cik,
                "start_date": start_date,
                "end_date": end_date,
                "insider_transactions": form_4_filings.get("filings", []),
                "count": form_4_filings.get("count", 0),
            }

            return self._format_response(
                operation="get_insider_transactions",
                data=result_data,
                source=f"SEC EDGAR - {submissions_url}",
            )

        except Exception as e:
            raise Exception(f"Failed to get insider transactions: {str(e)}")

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

