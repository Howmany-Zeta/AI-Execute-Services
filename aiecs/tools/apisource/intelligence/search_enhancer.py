"""
Search Result Enhancement and Ranking

Intelligently scores and filters search results:
- Calculate relevance scores using keyword matching
- Compute popularity scores
- Calculate recency/freshness scores
- Apply composite scoring with configurable weights
- Filter by quality, relevance, and date ranges
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SearchEnhancer:
    """
    Enhances search results with relevance scoring and intelligent filtering.
    """

    def __init__(
        self,
        relevance_weight: float = 0.5,
        popularity_weight: float = 0.3,
        recency_weight: float = 0.2,
    ):
        """
        Initialize search enhancer.

        Args:
            relevance_weight: Weight for relevance score in composite score
            popularity_weight: Weight for popularity score in composite score
            recency_weight: Weight for recency score in composite score
        """
        self.relevance_weight = relevance_weight
        self.popularity_weight = popularity_weight
        self.recency_weight = recency_weight

        # Normalize weights
        total_weight = relevance_weight + popularity_weight + recency_weight
        self.relevance_weight /= total_weight
        self.popularity_weight /= total_weight
        self.recency_weight /= total_weight

    def enhance_search_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enhance search results with scoring and filtering.

        Args:
            query: Original search query
            results: Raw search results
            options: Enhancement options:
                - relevance_threshold: Minimum composite score (0-1)
                - sort_by: Sort method ('relevance', 'popularity', 'recency', 'composite')
                - date_range: {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}
                - min_quality_score: Minimum quality score (0-1)
                - max_results: Maximum number of results to return

        Returns:
            Enhanced and filtered results
        """
        if not results:
            return []

        options = options or {}
        enhanced = []

        for result in results:
            # Calculate scores
            relevance = self._calculate_relevance(query, result)
            popularity = self._get_popularity_score(result)
            recency = self._calculate_recency(result)

            # Calculate composite score
            composite_score = relevance * self.relevance_weight + popularity * self.popularity_weight + recency * self.recency_weight

            # Add search metadata
            result_copy = result.copy()
            result_copy["_search_metadata"] = {
                "relevance_score": round(relevance, 3),
                "popularity_score": round(popularity, 3),
                "recency_score": round(recency, 3),
                "composite_score": round(composite_score, 3),
                "match_type": self._get_match_type(query, result),
            }

            # Apply filters
            if self._passes_filters(result_copy, options):
                enhanced.append(result_copy)

        # Sort results
        enhanced = self._sort_results(enhanced, options.get("sort_by", "composite"))

        # Apply max results limit
        max_results = options.get("max_results")
        if max_results and max_results > 0:
            enhanced = enhanced[:max_results]

        return enhanced

    def _calculate_relevance(self, query: str, result: Dict[str, Any]) -> float:
        """
        Calculate relevance score using keyword matching.

        Args:
            query: Search query
            result: Result item

        Returns:
            Relevance score (0-1)
        """
        query_terms = set(query.lower().split())
        if not query_terms:
            return 0.0

        # Extract searchable text from result

        title_text = ""
        description_text = ""

        for field in ["title", "name"]:
            if field in result:
                title_text += " " + str(result[field]).lower()

        for field in ["description", "notes", "sourceNote"]:
            if field in result:
                description_text += " " + str(result[field]).lower()

        # Count matches in title (weighted higher)
        title_matches = sum(1 for term in query_terms if term in title_text)
        title_score = min(title_matches / len(query_terms), 1.0)

        # Count matches in description
        desc_matches = sum(1 for term in query_terms if term in description_text)
        desc_score = min(desc_matches / len(query_terms), 1.0)

        # Weight title matches more heavily
        relevance = title_score * 0.7 + desc_score * 0.3

        # Boost for exact phrase match
        query_lower = query.lower()
        if query_lower in title_text:
            relevance = min(relevance * 1.5, 1.0)

        return relevance

    def _get_popularity_score(self, result: Dict[str, Any]) -> float:
        """
        Calculate popularity score based on usage indicators.

        Args:
            result: Result item

        Returns:
            Popularity score (0-1)
        """
        # Look for popularity indicators
        popularity_fields = [
            "popularity",
            "usage_count",
            "frequency",
            "popularity_rank",
        ]

        for field in popularity_fields:
            if field in result:
                value = result[field]
                if isinstance(value, (int, float)):
                    # Normalize to 0-1 range (assumes max popularity of 100)
                    return min(value / 100, 1.0)

        # Check for "popular" or "commonly used" in metadata
        frequency = result.get("frequency")
        if frequency in ["Daily", "Weekly", "Monthly"]:
            # More frequent updates = more popular
            frequency_scores = {"Daily": 1.0, "Weekly": 0.8, "Monthly": 0.6}
            return frequency_scores.get(str(frequency) if frequency else "", 0.5)

        # Default: medium popularity
        return 0.5

    def _calculate_recency(self, result: Dict[str, Any]) -> float:
        """
        Calculate recency/freshness score.

        Args:
            result: Result item

        Returns:
            Recency score (0-1)
        """
        # Look for date fields
        date_fields = [
            "updated",
            "last_updated",
            "observation_end",
            "date",
            "publishedAt",
            "last_modified",
        ]

        latest_date = None

        for field in date_fields:
            if field in result:
                date_str = result[field]
                try:
                    # Parse date
                    if "T" in str(date_str):
                        # ISO format
                        date_obj = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                    else:
                        # Simple date format
                        date_obj = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")

                    if latest_date is None or date_obj > latest_date:
                        latest_date = date_obj
                except (ValueError, TypeError):
                    continue

        if latest_date is None:
            # No date found, assume moderate recency
            return 0.5

        # Calculate age in days
        now = datetime.utcnow()
        age_days = (now - latest_date).days

        # Score based on age
        if age_days < 7:
            return 1.0  # Very recent
        elif age_days < 30:
            return 0.9  # Recent
        elif age_days < 90:
            return 0.7  # Somewhat recent
        elif age_days < 365:
            return 0.5  # This year
        elif age_days < 365 * 2:
            return 0.3  # Last 2 years
        else:
            # Older data, score decreases slowly
            return max(0.1, 0.3 - (age_days - 365 * 2) / (365 * 10))

    def _get_match_type(self, query: str, result: Dict[str, Any]) -> str:
        """
        Determine the type of match.

        Args:
            query: Search query
            result: Result item

        Returns:
            Match type string ('exact', 'partial', 'fuzzy')
        """
        query_lower = query.lower()

        # Check title/name fields
        for field in ["title", "name", "id", "series_id"]:
            if field in result:
                value = str(result[field]).lower()

                if value == query_lower:
                    return "exact"
                elif query_lower in value or value in query_lower:
                    return "partial"

        return "fuzzy"

    def _passes_filters(self, result: Dict[str, Any], options: Dict[str, Any]) -> bool:
        """
        Check if result passes filter criteria.

        Args:
            result: Result with _search_metadata
            options: Filter options

        Returns:
            True if result passes all filters
        """
        # Relevance threshold
        threshold = options.get("relevance_threshold", 0.0)
        composite_score = result["_search_metadata"]["composite_score"]
        if composite_score < threshold:
            return False

        # Quality score threshold
        min_quality = options.get("min_quality_score")
        if min_quality is not None:
            # Check if result has quality metadata
            quality_score = result.get("_quality", {}).get("score")
            if quality_score is None:
                quality_score = result.get("metadata", {}).get("quality", {}).get("score")

            if quality_score is not None and quality_score < min_quality:
                return False

        # Date range filter
        date_range = options.get("date_range")
        if date_range:
            # Check if result falls within date range
            result_date = self._extract_date(result)
            if result_date:
                start = date_range.get("start")
                end = date_range.get("end")

                try:
                    if start:
                        start_date = datetime.strptime(start, "%Y-%m-%d")
                        if result_date < start_date:
                            return False

                    if end:
                        end_date = datetime.strptime(end, "%Y-%m-%d")
                        if result_date > end_date:
                            return False
                except ValueError:
                    logger.warning(f"Invalid date range format: {date_range}")

        return True

    def _extract_date(self, result: Dict[str, Any]) -> Optional[datetime]:
        """Extract date from result"""
        date_fields = [
            "date",
            "observation_end",
            "last_updated",
            "publishedAt",
        ]

        for field in date_fields:
            if field in result:
                try:
                    date_str = str(result[field])
                    if "T" in date_str:
                        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        return datetime.strptime(date_str[:10], "%Y-%m-%d")
                except (ValueError, TypeError):
                    continue

        return None

    def _sort_results(self, results: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """
        Sort results by specified criteria.

        Args:
            results: Results with _search_metadata
            sort_by: Sort method

        Returns:
            Sorted results
        """
        if sort_by == "relevance":
            return sorted(
                results,
                key=lambda x: x["_search_metadata"]["relevance_score"],
                reverse=True,
            )
        elif sort_by == "popularity":
            return sorted(
                results,
                key=lambda x: x["_search_metadata"]["popularity_score"],
                reverse=True,
            )
        elif sort_by == "recency":
            return sorted(
                results,
                key=lambda x: x["_search_metadata"]["recency_score"],
                reverse=True,
            )
        else:  # composite (default)
            return sorted(
                results,
                key=lambda x: x["_search_metadata"]["composite_score"],
                reverse=True,
            )
