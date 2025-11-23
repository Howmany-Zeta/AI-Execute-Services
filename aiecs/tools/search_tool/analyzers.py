"""
Search Result Analyzers

This module contains analyzers for assessing search result quality,
understanding query intent, and generating result summaries.
"""

from datetime import datetime
from typing import Any, Dict, List, cast

from .constants import QueryIntentType, CredibilityLevel


# ============================================================================
# Result Quality Analyzer
# ============================================================================


class ResultQualityAnalyzer:
    """Analyzer for assessing search result quality"""

    # High authority domains with trust scores
    AUTHORITATIVE_DOMAINS = {
        # Academic and research
        "scholar.google.com": 0.95,
        "arxiv.org": 0.95,
        "ieee.org": 0.95,
        "acm.org": 0.95,
        "nature.com": 0.95,
        "science.org": 0.95,
        # Government and official
        ".gov": 0.90,
        ".edu": 0.85,
        "who.int": 0.90,
        "un.org": 0.90,
        # Major media
        "nytimes.com": 0.80,
        "bbc.com": 0.80,
        "reuters.com": 0.85,
        "apnews.com": 0.85,
        # Technical documentation
        "docs.python.org": 0.90,
        "developer.mozilla.org": 0.90,
        "stackoverflow.com": 0.75,
        "github.com": 0.70,
        # Encyclopedia
        "wikipedia.org": 0.75,
    }

    # Low quality indicators
    LOW_QUALITY_INDICATORS = [
        "clickbait",
        "ads",
        "spam",
        "scam",
        "download-now",
        "free-download",
        "xxx",
        "adult",
        "casino",
        "pills",
    ]

    def analyze_result_quality(self, result: Dict[str, Any], query: str, position: int) -> Dict[str, Any]:
        """
        Analyze quality of a single search result.

        Args:
            result: Search result dictionary
            query: Original search query
            position: Position in search results (1-based)

        Returns:
            Quality analysis dictionary with scores and signals
        """
        quality_analysis: Dict[str, Any] = {
            "quality_score": 0.0,
            "authority_score": 0.0,
            "relevance_score": 0.0,
            "freshness_score": 0.0,
            "credibility_level": CredibilityLevel.MEDIUM.value,
            "quality_signals": {},
            "warnings": [],
        }

        # 1. Evaluate domain authority
        domain = result.get("displayLink", "").lower()
        authority_score = self._calculate_authority_score(domain)
        quality_analysis["authority_score"] = authority_score
        quality_signals = cast(Dict[str, Any], quality_analysis["quality_signals"])
        quality_signals["domain_authority"] = "high" if authority_score > 0.8 else "medium" if authority_score > 0.5 else "low"

        # 2. Evaluate relevance
        relevance_score = self._calculate_relevance_score(query, result.get("title", ""), result.get("snippet", ""), position)
        quality_analysis["relevance_score"] = relevance_score

        # 3. Evaluate freshness
        freshness_score = self._calculate_freshness_score(result)
        quality_analysis["freshness_score"] = freshness_score

        # 4. Check HTTPS
        link = result.get("link", "")
        has_https = link.startswith("https://")
        quality_signals["has_https"] = has_https
        warnings = cast(List[str], quality_analysis["warnings"])
        if not has_https:
            warnings.append("No HTTPS - security concern")

        # 5. Check content length
        snippet_length = len(result.get("snippet", ""))
        quality_signals["content_length"] = "adequate" if snippet_length > 100 else "short"
        if snippet_length < 50:
            warnings.append("Very short snippet - may lack detail")

        # 6. Check metadata
        has_metadata = "metadata" in result
        quality_signals["has_metadata"] = has_metadata

        # 7. Position ranking (Google's ranking is a quality signal)
        position_score = max(0, 1.0 - (position - 1) * 0.05)
        quality_signals["position_rank"] = position

        # 8. Detect low quality indicators
        url_lower = link.lower()
        title_lower = result.get("title", "").lower()
        for indicator in self.LOW_QUALITY_INDICATORS:
            if indicator in url_lower or indicator in title_lower:
                warnings.append(f"Low quality indicator detected: {indicator}")
                authority_score *= 0.5  # Significantly reduce authority

        # 9. Calculate comprehensive quality score
        quality_score = (
            authority_score * 0.35  # Authority 35%
            + relevance_score * 0.30  # Relevance 30%
            + position_score * 0.20  # Position 20%
            + freshness_score * 0.10  # Freshness 10%
            + (0.05 if has_https else 0)  # HTTPS 5%
        )
        quality_analysis["quality_score"] = quality_score

        # 10. Determine credibility level
        if quality_score > 0.75:
            quality_analysis["credibility_level"] = CredibilityLevel.HIGH.value
        elif quality_score > 0.5:
            quality_analysis["credibility_level"] = CredibilityLevel.MEDIUM.value
        else:
            quality_analysis["credibility_level"] = CredibilityLevel.LOW.value

        return quality_analysis

    def _calculate_authority_score(self, domain: str) -> float:
        """Calculate domain authority score"""
        # Exact match
        if domain in self.AUTHORITATIVE_DOMAINS:
            return self.AUTHORITATIVE_DOMAINS[domain]

        # Suffix match
        for auth_domain, score in self.AUTHORITATIVE_DOMAINS.items():
            if domain.endswith(auth_domain):
                return score

        # Default medium authority
        return 0.5

    def _calculate_relevance_score(self, query: str, title: str, snippet: str, position: int) -> float:
        """Calculate relevance score based on query match"""
        query_terms = set(query.lower().split())
        title_lower = title.lower()
        snippet_lower = snippet.lower()

        # Title matching
        title_matches = sum(1 for term in query_terms if term in title_lower)
        title_score = title_matches / len(query_terms) if query_terms else 0

        # Snippet matching
        snippet_matches = sum(1 for term in query_terms if term in snippet_lower)
        snippet_score = snippet_matches / len(query_terms) if query_terms else 0

        # Position bonus (top 3 get extra credit)
        position_bonus = 0.2 if position <= 3 else 0.1 if position <= 10 else 0

        # Combined relevance
        relevance = title_score * 0.6 + snippet_score * 0.3 + position_bonus  # Title weighted higher  # Snippet secondary  # Position bonus

        return min(1.0, relevance)

    def _calculate_freshness_score(self, result: Dict[str, Any]) -> float:
        """Calculate freshness score from publish date metadata"""
        metadata = result.get("metadata", {})

        # Look for date in various metadata fields
        date_fields = ["metatags", "article", "newsarticle"]
        publish_date = None

        for field in date_fields:
            if field in metadata:
                items = metadata[field]
                if isinstance(items, list) and items:
                    item = items[0]
                    # Common date field names
                    for date_key in [
                        "publishdate",
                        "datepublished",
                        "article:published_time",
                    ]:
                        if date_key in item:
                            publish_date = item[date_key]
                            break
                if publish_date:
                    break

        if not publish_date:
            # No date info, return neutral score
            return 0.5

        try:
            # Parse date
            pub_dt = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
            now = datetime.now(pub_dt.tzinfo)

            days_old = (now - pub_dt).days

            # Freshness scoring
            if days_old < 7:
                return 1.0  # < 1 week - very fresh
            elif days_old < 30:
                return 0.9  # < 1 month - fresh
            elif days_old < 90:
                return 0.7  # < 3 months - moderately fresh
            elif days_old < 365:
                return 0.5  # < 1 year - neutral
            elif days_old < 730:
                return 0.3  # < 2 years - dated
            else:
                return 0.1  # > 2 years - old
        except Exception:
            return 0.5

    def rank_results(self, results: List[Dict[str, Any]], ranking_strategy: str = "balanced") -> List[Dict[str, Any]]:
        """
        Re-rank results by quality metrics.

        Args:
            results: List of results with quality analysis
            ranking_strategy: Ranking strategy ('balanced', 'authority', 'relevance', 'freshness')

        Returns:
            Sorted list of results
        """
        if ranking_strategy == "authority":
            return sorted(
                results,
                key=lambda x: x.get("_quality", {}).get("authority_score", 0),
                reverse=True,
            )
        elif ranking_strategy == "relevance":
            return sorted(
                results,
                key=lambda x: x.get("_quality", {}).get("relevance_score", 0),
                reverse=True,
            )
        elif ranking_strategy == "freshness":
            return sorted(
                results,
                key=lambda x: x.get("_quality", {}).get("freshness_score", 0),
                reverse=True,
            )
        else:  # balanced
            return sorted(
                results,
                key=lambda x: x.get("_quality", {}).get("quality_score", 0),
                reverse=True,
            )


# ============================================================================
# Query Intent Analyzer
# ============================================================================


class QueryIntentAnalyzer:
    """Analyzer for understanding query intent and optimizing queries"""

    # Intent patterns with keywords and enhancements
    INTENT_PATTERNS = {
        QueryIntentType.DEFINITION.value: {
            "keywords": ["what is", "define", "meaning of", "definition"],
            "query_enhancement": 'definition OR meaning OR "what is"',
            "suggested_params": {"num_results": 5},
        },
        QueryIntentType.HOW_TO.value: {
            "keywords": [
                "how to",
                "how do i",
                "tutorial",
                "guide",
                "steps to",
            ],
            "query_enhancement": 'tutorial OR guide OR "step by step"',
            "suggested_params": {"num_results": 10},
        },
        QueryIntentType.COMPARISON.value: {
            "keywords": [
                "vs",
                "versus",
                "compare",
                "difference between",
                "better than",
            ],
            "query_enhancement": 'comparison OR versus OR "vs"',
            "suggested_params": {"num_results": 10},
        },
        QueryIntentType.FACTUAL.value: {
            "keywords": [
                "when",
                "where",
                "who",
                "which",
                "statistics",
                "data",
            ],
            "query_enhancement": "",
            "suggested_params": {"num_results": 5},
        },
        QueryIntentType.RECENT_NEWS.value: {
            "keywords": ["latest", "recent", "news", "today", "current"],
            "query_enhancement": "news OR latest",
            "suggested_params": {"date_restrict": "w1", "sort_by": "date"},
        },
        QueryIntentType.ACADEMIC.value: {
            "keywords": ["research", "study", "paper", "journal", "academic"],
            "query_enhancement": "research OR study OR paper",
            "suggested_params": {"file_type": "pdf", "num_results": 10},
        },
        QueryIntentType.PRODUCT.value: {
            "keywords": ["buy", "price", "review", "best", "top rated"],
            "query_enhancement": "review OR comparison",
            "suggested_params": {"num_results": 15},
        },
    }

    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine intent and generate enhancements.

        Args:
            query: Search query string

        Returns:
            Intent analysis with enhanced query and suggestions
        """
        query_lower = query.lower()

        analysis: Dict[str, Any] = {
            "original_query": query,
            "intent_type": QueryIntentType.GENERAL.value,
            "confidence": 0.0,
            "enhanced_query": query,
            "suggested_params": {},
            "query_entities": [],
            "query_modifiers": [],
            "suggestions": [],
        }

        # Detect intent type
        max_confidence = 0.0
        detected_intent = QueryIntentType.GENERAL.value

        for intent_type, intent_config in self.INTENT_PATTERNS.items():
            keywords = intent_config["keywords"]
            matches = sum(1 for kw in keywords if kw in query_lower)

            if matches > 0:
                confidence = min(1.0, matches / len(keywords) * 2)
                if confidence > max_confidence:
                    max_confidence = confidence
                    detected_intent = intent_type

        analysis["intent_type"] = detected_intent
        analysis["confidence"] = max_confidence

        # Enhance query if intent detected
        if detected_intent != QueryIntentType.GENERAL.value:
            intent_config = self.INTENT_PATTERNS[detected_intent]
            enhancement = intent_config["query_enhancement"]

            if enhancement:
                analysis["enhanced_query"] = f"{query} {enhancement}"

            suggested_params = cast(Dict[str, Any], intent_config["suggested_params"])
            analysis["suggested_params"] = suggested_params.copy()

        # Extract entities and modifiers
        analysis["query_entities"] = self._extract_entities(query)
        analysis["query_modifiers"] = self._extract_modifiers(query)

        # Generate suggestions
        analysis["suggestions"] = self._generate_suggestions(query, detected_intent)

        return analysis

    def _extract_entities(self, query: str) -> List[str]:
        """Extract potential entities from query (simplified)"""
        words = query.split()
        entities = []

        for word in words:
            # Simple rule: capitalized words might be entities
            if word and word[0].isupper() and len(word) > 2:
                entities.append(word)

        return entities

    def _extract_modifiers(self, query: str) -> List[str]:
        """Extract query modifiers"""
        modifiers = []
        modifier_words = [
            "best",
            "top",
            "latest",
            "new",
            "old",
            "cheap",
            "expensive",
            "free",
            "open source",
            "commercial",
            "beginner",
            "advanced",
        ]

        query_lower = query.lower()
        for modifier in modifier_words:
            if modifier in query_lower:
                modifiers.append(modifier)

        return modifiers

    def _generate_suggestions(self, query: str, intent_type: str) -> List[str]:
        """Generate query optimization suggestions"""
        suggestions = []

        if intent_type == QueryIntentType.HOW_TO.value:
            if "beginner" not in query.lower() and "advanced" not in query.lower():
                suggestions.append('Consider adding "beginner" or "advanced" to target skill level')

        elif intent_type == QueryIntentType.COMPARISON.value:
            if " vs " not in query.lower():
                suggestions.append('Use "vs" or "versus" for better comparison results')

        elif intent_type == QueryIntentType.ACADEMIC.value:
            if "pdf" not in query.lower():
                suggestions.append('Consider adding "filetype:pdf" to find research papers')

        elif intent_type == QueryIntentType.RECENT_NEWS.value:
            suggestions.append("Results will be filtered to last week for freshness")

        # General suggestions
        if len(query.split()) < 3:
            suggestions.append("Query is short - consider adding more specific terms")

        if len(query.split()) > 10:
            suggestions.append("Query is long - consider simplifying to key terms")

        return suggestions


# ============================================================================
# Result Summarizer
# ============================================================================


class ResultSummarizer:
    """Generator of structured summaries from search results"""

    def generate_summary(self, results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """
        Generate comprehensive summary of search results.

        Args:
            results: List of search results with quality analysis
            query: Original search query

        Returns:
            Summary dictionary with statistics and recommendations
        """
        summary: Dict[str, Any] = {
            "query": query,
            "total_results": len(results),
            "quality_distribution": {"high": 0, "medium": 0, "low": 0},
            "top_domains": [],
            "content_types": {},
            "freshness_distribution": {
                "very_fresh": 0,
                "fresh": 0,
                "moderate": 0,
                "old": 0,
            },
            "recommended_results": [],
            "warnings": [],
            "suggestions": [],
        }

        if not results:
            warnings = cast(List[str], summary["warnings"])
            warnings.append("No results found")
            return summary

        # Gather statistics
        domain_stats: Dict[str, Dict[str, Any]] = {}

        quality_distribution = cast(Dict[str, int], summary["quality_distribution"])
        freshness_distribution = cast(Dict[str, int], summary["freshness_distribution"])
        warnings = cast(List[str], summary["warnings"])
        suggestions = cast(List[str], summary["suggestions"])

        for result in results:
            quality = result.get("_quality", {})
            quality_level = quality.get("credibility_level", "medium")
            quality_distribution[quality_level] += 1

            # Domain statistics
            domain = result.get("displayLink", "unknown")
            if domain not in domain_stats:
                domain_stats[domain] = {"count": 0, "total_quality": 0.0}
            domain_stats[domain]["count"] += 1
            domain_stats[domain]["total_quality"] += quality.get("quality_score", 0.5)

            # Freshness distribution
            freshness = quality.get("freshness_score", 0.5)
            if freshness > 0.9:
                freshness_distribution["very_fresh"] += 1
            elif freshness > 0.7:
                freshness_distribution["fresh"] += 1
            elif freshness > 0.5:
                freshness_distribution["moderate"] += 1
            else:
                freshness_distribution["old"] += 1

        # Top domains
        top_domains: List[Dict[str, Any]] = []
        for domain, stats in domain_stats.items():
            avg_quality = stats["total_quality"] / stats["count"]
            top_domains.append(
                {
                    "domain": domain,
                    "count": stats["count"],
                    "avg_quality": avg_quality,
                }
            )

        summary["top_domains"] = sorted(
            top_domains,
            key=lambda x: (x["count"], x["avg_quality"]),
            reverse=True,
        )[:5]

        # Recommended results (top 3 by quality)
        sorted_results = sorted(
            results,
            key=lambda x: x.get("_quality", {}).get("quality_score", 0),
            reverse=True,
        )
        summary["recommended_results"] = sorted_results[:3]

        # Generate warnings
        if quality_distribution["low"] > 0:
            warnings.append(f"{quality_distribution['low']} low quality result(s) detected")

        https_count = sum(1 for r in results if r.get("link", "").startswith("https://"))
        if https_count < len(results):
            warnings.append(f"{len(results) - https_count} result(s) lack HTTPS")

        # Generate suggestions
        if freshness_distribution["old"] > len(results) / 2:
            suggestions.append("Many results are outdated - consider adding date filter")

        if quality_distribution["high"] < 3:
            suggestions.append("Few high-quality results - try refining your query")

        return summary
