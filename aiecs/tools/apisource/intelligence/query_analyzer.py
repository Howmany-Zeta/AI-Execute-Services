"""
Query Intent Analysis and Enhancement

Provides intelligent query understanding and parameter auto-completion:
- Detect query intent (time_series, comparison, search, metadata)
- Extract entities (economic indicators, countries, etc.)
- Parse time ranges and geographic scope
- Suggest appropriate providers and operations
- Auto-complete missing parameters based on intent
"""

import logging
import re
from typing import Any, Dict, List, Optional, cast

logger = logging.getLogger(__name__)


class QueryIntentAnalyzer:
    """
    Analyzes query intent to help route requests and optimize parameters.
    """

    # Intent keywords
    INTENT_KEYWORDS = {
        "time_series": [
            "trend",
            "over time",
            "historical",
            "series",
            "change",
            "growth",
            "history",
        ],
        "comparison": [
            "compare",
            "versus",
            "vs",
            "difference",
            "between",
            "against",
            "relative to",
        ],
        "search": [
            "search",
            "find",
            "look for",
            "list",
            "show me",
            "what are",
        ],
        "metadata": [
            "info",
            "information",
            "about",
            "describe",
            "details",
            "metadata",
        ],
        "recent": [
            "recent",
            "latest",
            "current",
            "now",
            "today",
            "this week",
            "this month",
        ],
        "forecast": ["forecast", "predict", "future", "project", "estimate"],
    }

    # Economic indicators mapping
    ECONOMIC_INDICATORS = {
        "gdp": {
            "keywords": ["gdp", "gross domestic product", "economic output"],
            "providers": ["fred", "worldbank"],
            "fred_series": ["GDP", "GDPC1"],
            "wb_indicator": "NY.GDP.MKTP.CD",
        },
        "unemployment": {
            "keywords": ["unemployment", "jobless", "labor force"],
            "providers": ["fred"],
            "fred_series": ["UNRATE", "UNEMPLOY"],
        },
        "inflation": {
            "keywords": ["inflation", "cpi", "consumer price", "price index"],
            "providers": ["fred", "worldbank"],
            "fred_series": ["CPIAUCSL", "CPILFESL"],
            "wb_indicator": "FP.CPI.TOTL",
        },
        "interest_rate": {
            "keywords": [
                "interest rate",
                "fed rate",
                "federal funds",
                "treasury",
            ],
            "providers": ["fred"],
            "fred_series": ["DFF", "DGS10", "DGS30"],
        },
        "population": {
            "keywords": ["population", "demographic", "people count"],
            "providers": ["census", "worldbank"],
            "wb_indicator": "SP.POP.TOTL",
        },
        "trade": {
            "keywords": ["trade", "export", "import", "trade balance"],
            "providers": ["fred", "worldbank"],
            "fred_series": ["BOPGSTB"],
            "wb_indicator": "NE.EXP.GNFS.CD",
        },
    }

    # Country codes and names
    COUNTRIES = {
        "us": ["us", "usa", "united states", "america"],
        "uk": ["uk", "united kingdom", "britain"],
        "china": ["china", "cn"],
        "japan": ["japan", "jp"],
        "germany": ["germany", "de"],
        "france": ["france", "fr"],
        "india": ["india", "in"],
        "canada": ["canada", "ca"],
    }

    def analyze_intent(self, query_text: str) -> Dict[str, Any]:
        """
        Analyze query intent and extract key information.

        Args:
            query_text: Natural language query string

        Returns:
            Dictionary with:
                - intent_type: Primary intent (time_series, comparison, search, etc.)
                - entities: Extracted entities (indicators, countries, etc.)
                - time_range: Extracted time information
                - geographic_scope: Geographic context
                - suggested_providers: Recommended providers
                - suggested_operations: Recommended operations
                - confidence: Confidence score (0-1)
        """
        query_lower = query_text.lower()

        intent_result: Dict[str, Any] = {
            "intent_type": "search",  # Default
            "entities": [],
            "time_range": None,
            "geographic_scope": None,
            "suggested_providers": [],
            "suggested_operations": [],
            "confidence": 0.0,
            "keywords_matched": [],
        }

        # Detect intent type
        intent_scores = {}
        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                intent_scores[intent_type] = score

        if intent_scores:
            # Primary intent is the one with highest score
            primary_intent = max(intent_scores.items(), key=lambda x: x[1])
            intent_result["intent_type"] = primary_intent[0]
            intent_result["confidence"] += 0.3

        # Extract economic indicators
        entities = cast(List[Dict[str, Any]], intent_result["entities"])
        suggested_providers = cast(List[str], intent_result["suggested_providers"])
        keywords_matched = cast(List[str], intent_result["keywords_matched"])

        for indicator_name, indicator_info_raw in self.ECONOMIC_INDICATORS.items():
            indicator_info = cast(Dict[str, Any], indicator_info_raw)
            for keyword in indicator_info["keywords"]:
                if keyword in query_lower:
                    entities.append(
                        {
                            "type": "indicator",
                            "name": indicator_name,
                            "matched_keyword": keyword,
                        }
                    )
                    suggested_providers.extend(indicator_info["providers"])
                    intent_result["confidence"] += 0.2
                    keywords_matched.append(keyword)
                    break

        # Extract countries
        for country_code, country_names in self.COUNTRIES.items():
            for country_name in country_names:
                if country_name in query_lower:
                    intent_result["geographic_scope"] = country_code.upper()
                    intent_result["confidence"] += 0.2
                    break

        # Extract time range
        time_info = self._extract_time_range(query_lower)
        if time_info:
            intent_result["time_range"] = time_info
            intent_result["confidence"] += 0.2

        # Suggest operations based on intent
        intent_result["suggested_operations"] = self._suggest_operations(intent_result["intent_type"], intent_result["suggested_providers"])

        # Remove duplicates from providers
        intent_result["suggested_providers"] = list(set(intent_result["suggested_providers"]))

        # Cap confidence at 1.0
        intent_result["confidence"] = min(1.0, intent_result["confidence"])

        return intent_result

    def _extract_time_range(self, query_lower: str) -> Optional[Dict[str, Any]]:
        """
        Extract time range information from query.

        Args:
            query_lower: Lowercase query string

        Returns:
            Dictionary with start_date, end_date, or None
        """
        time_range: Dict[str, Any] = {}

        # Look for year patterns (4 digits)
        year_pattern = r"\b(19|20)\d{2}\b"
        years = re.findall(year_pattern, query_lower)

        if len(years) >= 2:
            # Found multiple years
            years_int = sorted([int(y) for y in years])
            time_range["start_date"] = f"{years_int[0]}-01-01"
            time_range["end_date"] = f"{years_int[-1]}-12-31"
            time_range["type"] = "explicit_range"
        elif len(years) == 1:
            # Single year mentioned
            year = int(years[0])
            time_range["start_date"] = f"{year}-01-01"
            time_range["end_date"] = f"{year}-12-31"
            time_range["type"] = "single_year"

        # Look for relative time expressions
        if "last" in query_lower or "past" in query_lower:
            # Extract number
            number_pattern = r"(last|past)\s+(\d+)\s+(year|month|day|week)"
            match = re.search(number_pattern, query_lower)
            if match:
                quantity = int(match.group(2))
                unit = match.group(3)
                time_range["type"] = "relative"
                time_range["quantity"] = quantity
                time_range["unit"] = unit

        return time_range if time_range else None

    def _suggest_operations(self, intent_type: str, providers: List[str]) -> List[Dict[str, str]]:
        """
        Suggest appropriate operations based on intent and providers.

        Args:
            intent_type: Detected intent type
            providers: List of suggested providers

        Returns:
            List of {provider, operation} dictionaries
        """
        suggestions = []

        for provider in providers:
            if intent_type == "time_series":
                if provider == "fred":
                    suggestions.append(
                        {
                            "provider": "fred",
                            "operation": "get_series_observations",
                        }
                    )
                elif provider == "worldbank":
                    suggestions.append({"provider": "worldbank", "operation": "get_indicator"})

            elif intent_type == "search":
                if provider == "fred":
                    suggestions.append({"provider": "fred", "operation": "search_series"})
                elif provider == "worldbank":
                    suggestions.append(
                        {
                            "provider": "worldbank",
                            "operation": "search_indicators",
                        }
                    )
                elif provider == "newsapi":
                    suggestions.append(
                        {
                            "provider": "newsapi",
                            "operation": "search_everything",
                        }
                    )

            elif intent_type == "metadata":
                if provider == "fred":
                    suggestions.append({"provider": "fred", "operation": "get_series_info"})

        return suggestions


class QueryEnhancer:
    """
    Enhances queries by auto-completing parameters based on intent.
    """

    def __init__(self, intent_analyzer: Optional[QueryIntentAnalyzer] = None):
        """
        Initialize query enhancer.

        Args:
            intent_analyzer: Intent analyzer instance (creates new if not provided)
        """
        self.intent_analyzer = intent_analyzer or QueryIntentAnalyzer()

    def auto_complete_params(
        self,
        provider: str,
        operation: str,
        params: Dict[str, Any],
        query_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Auto-complete missing parameters based on query intent.

        Args:
            provider: Provider name
            operation: Operation name
            params: Current parameters
            query_text: Optional natural language query for intent analysis

        Returns:
            Enhanced parameters dictionary
        """
        completed_params = params.copy()

        # Analyze intent if query text provided
        intent = None
        if query_text:
            intent = self.intent_analyzer.analyze_intent(query_text)

        # Add time range parameters if detected and not present
        if intent and intent.get("time_range") and provider == "fred":
            time_range = intent["time_range"]
            if time_range.get("type") in ["explicit_range", "single_year"]:
                if "observation_start" not in params and "start_date" in time_range:
                    completed_params["observation_start"] = time_range["start_date"]
                if "observation_end" not in params and "end_date" in time_range:
                    completed_params["observation_end"] = time_range["end_date"]

        # Add reasonable limits if not specified
        if "limit" not in params and "page_size" not in params:
            if intent and intent.get("intent_type") == "time_series":
                # Time series typically need more data
                if provider == "fred":
                    # FRED API max is 100000, but 1000 is reasonable default
                    completed_params["limit"] = 1000
                elif provider == "worldbank":
                    completed_params["per_page"] = 1000
            else:
                # Search results typically need fewer
                if provider == "fred":
                    completed_params["limit"] = 20
                elif provider == "worldbank":
                    completed_params["limit"] = 20
                elif provider == "newsapi":
                    completed_params["page_size"] = 10

        # Add sort order for time series
        if intent and intent.get("intent_type") == "time_series":
            if provider == "fred" and "sort_order" not in params:
                completed_params["sort_order"] = "desc"  # Most recent first

        # Add country code if detected and needed
        if intent and intent.get("geographic_scope"):
            if provider == "worldbank" and "country_code" not in params:
                completed_params["country_code"] = intent["geographic_scope"]

        return completed_params

    def enhance_query_text(self, query_text: str, provider: str) -> str:
        """
        Enhance query text for better search results.

        Args:
            query_text: Original query text
            provider: Target provider

        Returns:
            Enhanced query text
        """
        # Analyze intent
        intent = self.intent_analyzer.analyze_intent(query_text)

        # For searches, add indicator-specific terms
        enhanced = query_text

        if provider == "fred" and intent.get("entities"):
            # Add FRED series IDs if we recognize the indicator
            for entity in intent["entities"]:
                if entity["type"] == "indicator":
                    indicator_name = entity["name"]
                    indicator_info_raw = QueryIntentAnalyzer.ECONOMIC_INDICATORS.get(indicator_name, {})
                    indicator_info = cast(Dict[str, Any], indicator_info_raw)
                    if "fred_series" in indicator_info:
                        # Add common series IDs to improve search
                        series_ids = " ".join(indicator_info["fred_series"])
                        enhanced = f"{query_text} {series_ids}"
                        break

        return enhanced
