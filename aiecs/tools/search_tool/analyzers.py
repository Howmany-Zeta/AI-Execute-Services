# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Search Result Analyzers

This module contains analyzers for assessing search result quality,
understanding query intent, and generating result summaries.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple, cast

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

    # Social / forum domains — demote in ranking (M-D.1)
    SOCIAL_NOISE_DOMAINS = {
        "facebook.com": 0.12,
        "m.facebook.com": 0.12,
        "reddit.com": 0.18,
        "www.reddit.com": 0.18,
        "old.reddit.com": 0.18,
        "twitter.com": 0.15,
        "x.com": 0.15,
        "instagram.com": 0.12,
        "tiktok.com": 0.12,
    }

    # Survey / institutional sources — boost for research intents
    INSTITUTIONAL_DOMAINS = {
        "yougov.com": 0.92,
        "kpmg.com": 0.88,
        "pewresearch.org": 0.90,
        "statista.com": 0.85,
        "mckinsey.com": 0.88,
        "gartner.com": 0.85,
        "deloitte.com": 0.85,
    }

    LOW_SIGNAL_QUALITY_THRESHOLD = 0.45

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
        domain_lower = domain.lower()

        if domain_lower in self.SOCIAL_NOISE_DOMAINS:
            return self.SOCIAL_NOISE_DOMAINS[domain_lower]
        for social_domain, score in self.SOCIAL_NOISE_DOMAINS.items():
            if domain_lower.endswith(social_domain):
                return score

        if domain_lower in self.INSTITUTIONAL_DOMAINS:
            return self.INSTITUTIONAL_DOMAINS[domain_lower]
        for inst_domain, score in self.INSTITUTIONAL_DOMAINS.items():
            if domain_lower.endswith(inst_domain):
                return score

        # Exact match
        if domain_lower in self.AUTHORITATIVE_DOMAINS:
            return self.AUTHORITATIVE_DOMAINS[domain_lower]

        # Suffix match
        for auth_domain, score in self.AUTHORITATIVE_DOMAINS.items():
            if domain_lower.endswith(auth_domain):
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


def partition_search_results(
    quality_analyzer: ResultQualityAnalyzer,
    results: List[Dict[str, Any]],
    *,
    num_results: int,
    low_signal_threshold: float = ResultQualityAnalyzer.LOW_SIGNAL_QUALITY_THRESHOLD,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Re-rank results and split primary hits from low-signal noise."""
    if not results:
        return [], [], []

    ranked = quality_analyzer.rank_results(results, "balanced")
    primary: List[Dict[str, Any]] = []
    low_signal: List[Dict[str, Any]] = []

    for result in ranked:
        quality = result.get("_quality", {})
        summary = result.get("_quality_summary", {})
        quality_score = quality.get("quality_score", 0.0)
        is_relevant = summary.get("is_relevant", False)

        if quality_score < low_signal_threshold or (not is_relevant and quality_score < 0.55):
            low_signal.append(result)
        else:
            primary.append(result)

    if not primary:
        primary = ranked[:num_results]
        low_signal = ranked[num_results:]

    primary = primary[:num_results]
    must_scrape_urls = build_must_scrape_urls(ranked)
    return primary, low_signal, must_scrape_urls


def merge_batch_search_results(
    quality_analyzer: ResultQualityAnalyzer,
    per_query_buckets: List[Dict[str, Any]],
    *,
    merged_num_results: int,
    deduplicator: Any | None = None,
    similarity_threshold: float = 0.85,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Merge per-query primary hits into one ranked list (M-D.1 batch)."""
    combined: List[Dict[str, Any]] = []
    for bucket in per_query_buckets:
        source_query = bucket.get("_metadata", {}).get("query") or bucket.get("query", "")
        for result in bucket.get("results", []):
            merged = dict(result)
            merged["_batch_source_query"] = source_query
            combined.append(merged)

    if not combined:
        return [], [], []

    if deduplicator is not None:
        combined = deduplicator.deduplicate_results(combined, similarity_threshold)

    return partition_search_results(
        quality_analyzer,
        combined,
        num_results=merged_num_results,
    )


def build_batch_intent_analysis(per_query_buckets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pick a representative intent analysis for merged batch next_steps."""
    for bucket in per_query_buckets:
        metadata = bucket.get("_search_metadata") or bucket.get("_metadata") or {}
        intent_type = metadata.get("intent_type")
        if intent_type and intent_type != QueryIntentType.GENERAL.value:
            return {
                "intent_type": intent_type,
                "confidence": metadata.get("intent_confidence", metadata.get("confidence", 0.0)),
            }
    if per_query_buckets:
        metadata = per_query_buckets[0].get("_search_metadata") or per_query_buckets[0].get("_metadata") or {}
        if metadata.get("intent_type"):
            return {
                "intent_type": metadata["intent_type"],
                "confidence": metadata.get("intent_confidence", metadata.get("confidence", 0.0)),
            }
    return None


def build_must_scrape_urls(results: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """Select top URLs the consumer should scrape next."""
    candidates: List[Dict[str, Any]] = []
    for result in results:
        quality = result.get("_quality", {})
        summary = result.get("_quality_summary", {})
        quality_score = quality.get("quality_score", 0.0)
        authority_score = quality.get("authority_score", 0.0)
        is_relevant = summary.get("is_relevant", False)

        if not (is_relevant or authority_score >= 0.75 or quality_score >= 0.65):
            continue

        reasons: List[str] = []
        if is_relevant:
            reasons.append("high relevance")
        if summary.get("is_authoritative") or authority_score >= 0.8:
            reasons.append("high domain_authority")
        if summary.get("is_fresh"):
            reasons.append("fresh content")

        candidates.append(
            {
                "url": result.get("link", ""),
                "score": round(quality_score, 2),
                "reason": " / ".join(reasons) if reasons else "quality score",
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return [item for item in candidates[:top_k] if item.get("url")]


def build_search_next_steps(
    must_scrape_urls: List[Dict[str, Any]],
    intent_analysis: Optional[Dict[str, Any]],
) -> List[str]:
    """Actionable next steps for agent consumers."""
    steps: List[str] = []
    if must_scrape_urls:
        steps.append("scrape must_scrape_urls before issuing another web_search")

    intent_type = (intent_analysis or {}).get("intent_type", QueryIntentType.GENERAL.value)
    if intent_type == QueryIntentType.DEMOGRAPHIC.value:
        steps.append("prefer allowed_domains for survey publishers when intent=demographic")
    elif intent_type == QueryIntentType.CAUSAL.value:
        steps.append("prefer institutional or survey sources explaining causal factors")
    elif intent_type == QueryIntentType.BRAND.value:
        steps.append("prefer brand perception and reputation studies over social chatter")

    return steps


# ============================================================================
# Query Intent Analyzer
# ============================================================================


class QueryIntentAnalyzer:
    """Analyzer for understanding query intent and optimizing queries"""

    _STOP_WORDS = frozenset(
        {
            "a",
            "an",
            "the",
            "and",
            "or",
            "of",
            "in",
            "on",
            "for",
            "to",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "among",
            "affecting",
            "about",
            "with",
            "from",
            "that",
            "this",
            "their",
            "why",
            "how",
            "what",
            "when",
            "where",
            "who",
        }
    )

    _QUESTION_STARTERS = ("why ", "how ", "what ", "when ", "where ", "who ")

    _DEMOGRAPHIC_PHRASES = (
        "young people",
        "gen z",
        "gen-z",
        "millennials",
        "generation z",
        "youth",
        "teenagers",
        "demographic",
        "cohort",
        "age group",
    )

    _CAUSAL_PHRASES = (
        "why is",
        "why are",
        "what causes",
        "reasons for",
        "factors behind",
    )

    _CAUSAL_WORDS = frozenset(
        {
            "why",
            "cause",
            "reason",
            "popular",
            "popularity",
            "trend",
            "impact",
            "driving",
            "factors",
        }
    )

    _BRAND_PHRASES = ("brand image", "brand perception", "brand reputation")
    _BRAND_WORDS = frozenset({"brand", "reputation", "perception", "image"})

    _COMMA_STACK_FILLER = frozenset({"reports", "articles", "information", "data", "sources"})

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
        QueryIntentType.CAUSAL.value: {
            "keywords": [
                "why",
                "cause",
                "reason",
                "factor",
                "driving",
                "lead to",
                "impact",
                "popular",
                "popularity",
            ],
            "query_enhancement": "",
            "suggested_params": {"num_results": 10},
        },
        QueryIntentType.DEMOGRAPHIC.value: {
            "keywords": [
                "young people",
                "gen z",
                "millennials",
                "youth",
                "demographic",
                "generation",
                "cohort",
                "teen",
            ],
            "query_enhancement": "",
            "suggested_params": {"num_results": 10},
        },
        QueryIntentType.BRAND.value: {
            "keywords": [
                "brand",
                "reputation",
                "perception",
                "image",
                "company",
            ],
            "query_enhancement": "",
            "suggested_params": {"num_results": 10},
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
            "rewrite_applied": False,
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

        cohort_present = any(phrase in query_lower for phrase in self._DEMOGRAPHIC_PHRASES)
        if cohort_present and (detected_intent in (QueryIntentType.CAUSAL.value, QueryIntentType.GENERAL.value) or "popular" in query_lower or "popularity" in query_lower):
            detected_intent = QueryIntentType.DEMOGRAPHIC.value
            max_confidence = max(max_confidence, 0.72)
            analysis["intent_type"] = detected_intent
            analysis["confidence"] = max_confidence
            intent_config = self.INTENT_PATTERNS[detected_intent]
            analysis["suggested_params"] = cast(Dict[str, Any], intent_config["suggested_params"]).copy()

        if detected_intent == QueryIntentType.GENERAL.value:
            research_intent, research_confidence = self._detect_research_intent(query_lower)
            if research_intent != QueryIntentType.GENERAL.value:
                detected_intent = research_intent
                max_confidence = max(max_confidence, research_confidence)
                analysis["intent_type"] = detected_intent
                analysis["confidence"] = max_confidence
                intent_config = self.INTENT_PATTERNS[detected_intent]
                analysis["suggested_params"] = cast(Dict[str, Any], intent_config["suggested_params"]).copy()

        should_keyword_rewrite = detected_intent in {
            QueryIntentType.CAUSAL.value,
            QueryIntentType.DEMOGRAPHIC.value,
            QueryIntentType.BRAND.value,
        } or (detected_intent == QueryIntentType.GENERAL.value and self._should_heuristic_rewrite(query))
        if should_keyword_rewrite:
            rewritten = self._rewrite_to_keywords(query, detected_intent)
            if rewritten and rewritten.strip().lower() != query.strip().lower():
                analysis["enhanced_query"] = rewritten
                if analysis["confidence"] <= 0.0:
                    analysis["confidence"] = 0.35

        analysis["rewrite_applied"] = analysis["enhanced_query"].strip().lower() != query.strip().lower()

        if detected_intent != QueryIntentType.GENERAL.value and not analysis["suggested_params"]:
            intent_config = self.INTENT_PATTERNS[detected_intent]
            analysis["suggested_params"] = cast(Dict[str, Any], intent_config["suggested_params"]).copy()

        # Legacy boolean-style enhancement for non-research intents
        if (
            detected_intent != QueryIntentType.GENERAL.value
            and detected_intent
            not in {
                QueryIntentType.CAUSAL.value,
                QueryIntentType.DEMOGRAPHIC.value,
                QueryIntentType.BRAND.value,
            }
            and not analysis["rewrite_applied"]
        ):
            intent_config = self.INTENT_PATTERNS[detected_intent]
            enhancement = intent_config["query_enhancement"]
            if enhancement:
                analysis["enhanced_query"] = f"{query} {enhancement}"
                analysis["rewrite_applied"] = True

        # Extract entities and modifiers
        analysis["query_entities"] = self._extract_entities(query)
        analysis["query_modifiers"] = self._extract_modifiers(query)

        # Generate suggestions
        analysis["suggestions"] = self._generate_suggestions(query, detected_intent)

        return analysis

    def _detect_research_intent(self, query_lower: str) -> Tuple[str, float]:
        """Detect causal / demographic / brand intents missed by keyword patterns."""
        demographic_score = sum(1.5 for phrase in self._DEMOGRAPHIC_PHRASES if phrase in query_lower)
        causal_score = sum(2.0 for phrase in self._CAUSAL_PHRASES if phrase in query_lower)
        causal_score += sum(0.75 for word in self._CAUSAL_WORDS if word in query_lower.split())
        brand_score = sum(2.0 for phrase in self._BRAND_PHRASES if phrase in query_lower)
        brand_score += sum(0.75 for word in self._BRAND_WORDS if word in query_lower.split())

        scores = {
            QueryIntentType.DEMOGRAPHIC.value: demographic_score,
            QueryIntentType.CAUSAL.value: causal_score,
            QueryIntentType.BRAND.value: brand_score,
        }
        best_intent, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score <= 0:
            return QueryIntentType.GENERAL.value, 0.0

        has_cohort = any(phrase in query_lower for phrase in self._DEMOGRAPHIC_PHRASES)
        has_popularity = "popular" in query_lower or "popularity" in query_lower
        if has_cohort and (causal_score > 0 or has_popularity):
            confidence = min(1.0, 0.55 + demographic_score * 0.1 + min(causal_score, 2.0) * 0.05)
            return QueryIntentType.DEMOGRAPHIC.value, confidence

        if demographic_score > 0 and causal_score > 0 and demographic_score >= causal_score:
            best_intent = QueryIntentType.DEMOGRAPHIC.value
            best_score = demographic_score + (causal_score * 0.25)
        elif causal_score > demographic_score:
            best_intent = QueryIntentType.CAUSAL.value
            best_score = causal_score

        confidence = min(1.0, 0.45 + best_score * 0.12)
        return best_intent, confidence

    def _should_heuristic_rewrite(self, query: str) -> bool:
        stripped = query.strip()
        lowered = stripped.lower()
        if stripped.endswith("?"):
            return True
        if stripped.count(",") >= 2:
            return True
        return any(lowered.startswith(starter) for starter in self._QUESTION_STARTERS)

    def _rewrite_to_keywords(self, query: str, intent_type: str) -> str:
        raw = self._normalize_query_text(query.strip().rstrip("?").strip())
        if raw.count(",") >= 2:
            fragments = [fragment.strip() for fragment in raw.split(",") if fragment.strip()]
            terms: List[str] = []
            for fragment in fragments:
                terms.extend(self._tokenize_keywords(fragment))
        else:
            terms = self._tokenize_keywords(raw)

        terms = self._dedupe_terms_preserve_order(terms)
        terms = self._inject_intent_terms(terms, intent_type)
        return " ".join(terms) if terms else query

    def _normalize_query_text(self, text: str) -> str:
        normalized = text.replace("'s", "").replace("'", " ")
        normalized = re.sub(r"\bgen\s*-?\s*z\b", "GenZ", normalized, flags=re.IGNORECASE)
        return normalized

    def _tokenize_keywords(self, text: str) -> List[str]:
        cleaned = self._normalize_query_text(text).replace("-", " ")
        tokens: List[str] = []
        for word in cleaned.split():
            normalized = word.strip('.,;:!?()[]"')
            if not normalized:
                continue
            if normalized == "GenZ":
                tokens.append("Gen Z")
                continue
            lower = normalized.lower()
            if lower in self._STOP_WORDS or lower in self._COMMA_STACK_FILLER:
                continue
            if normalized[0].isupper() and len(normalized) > 1:
                tokens.append(normalized)
            elif lower not in self._STOP_WORDS:
                tokens.append(normalized)
        return tokens

    def _dedupe_terms_preserve_order(self, terms: List[str]) -> List[str]:
        seen: set[str] = set()
        deduped: List[str] = []
        for term in terms:
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(term)
        return deduped

    def _inject_intent_terms(self, terms: List[str], intent_type: str) -> List[str]:
        lowered = {term.lower() for term in terms}
        current_year = datetime.now().year
        year_range = f"{current_year - 2}..{current_year}"

        if intent_type == QueryIntentType.DEMOGRAPHIC.value:
            for extra in ("Gen Z", "Millennials", "survey", year_range):
                if extra.lower() not in lowered:
                    terms.append(extra)
                    lowered.add(extra.lower())
        elif intent_type == QueryIntentType.CAUSAL.value:
            for extra in ("reasons", "factors", year_range):
                if extra.lower() not in lowered:
                    terms.append(extra)
                    lowered.add(extra.lower())
        elif intent_type == QueryIntentType.BRAND.value:
            for extra in ("brand", "reputation", year_range):
                if extra.lower() not in lowered:
                    terms.append(extra)
                    lowered.add(extra.lower())
        return terms

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

        elif intent_type == QueryIntentType.DEMOGRAPHIC.value:
            suggestions.append("Prefer survey publishers and cohort-specific sources")

        elif intent_type == QueryIntentType.CAUSAL.value:
            suggestions.append("Prefer reports explaining reasons and contributing factors")

        elif intent_type == QueryIntentType.BRAND.value:
            suggestions.append("Prefer brand perception and reputation studies")

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
