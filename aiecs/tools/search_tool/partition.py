# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Backend-aware M-D.1b partition (M-D.5 §3.3).

``partition_profile=cse`` keeps existing CSE rules; ``grounding`` applies citation
trust floor, relaxed relevance, social demotion, and must_scrape fallbacks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from .analyzers import (
    ResultQualityAnalyzer,
    build_must_scrape_urls as build_must_scrape_urls_cse,
    partition_search_results as partition_search_results_cse,
)
from .constants import QueryIntentType

PartitionProfile = str  # "cse" | "grounding"


def resolve_partition_profile(
    backend_used: str | None,
    *,
    grounding_trust_citations: bool = True,
) -> PartitionProfile:
    """Map ``backend_used`` → ``cse`` | ``grounding`` (§3.3)."""
    if not grounding_trust_citations:
        return "cse"
    name = (backend_used or "").strip().lower()
    if not name or name == "google_cse":
        return "cse"
    return "grounding"


def partition_search_results(
    quality_analyzer: ResultQualityAnalyzer,
    results: List[Dict[str, Any]],
    *,
    num_results: int,
    partition_profile: PartitionProfile = "cse",
    query: str = "",
    intent_type: str | None = None,
    grounding_citations: list[str] | None = None,
    low_signal_threshold: float = ResultQualityAnalyzer.LOW_SIGNAL_QUALITY_THRESHOLD,
    grounding_trust_citations: bool = True,
    grounding_relevance_threshold: float = 0.5,
    grounding_sparse_snippet_max_len: int = 80,
    grounding_citation_trust_top_k: int = 3,
    grounding_min_must_scrape: int = 1,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Dispatch CSE vs grounding partition rules."""
    if partition_profile != "grounding":
        return partition_search_results_cse(
            quality_analyzer,
            results,
            num_results=num_results,
            low_signal_threshold=low_signal_threshold,
        )

    return partition_grounding_results(
        quality_analyzer,
        results,
        num_results=num_results,
        query=query,
        intent_type=intent_type,
        grounding_citations=grounding_citations,
        low_signal_threshold=low_signal_threshold,
        grounding_trust_citations=grounding_trust_citations,
        grounding_relevance_threshold=grounding_relevance_threshold,
        grounding_sparse_snippet_max_len=grounding_sparse_snippet_max_len,
        grounding_citation_trust_top_k=grounding_citation_trust_top_k,
        grounding_min_must_scrape=grounding_min_must_scrape,
    )


def partition_grounding_results(
    quality_analyzer: ResultQualityAnalyzer,
    results: List[Dict[str, Any]],
    *,
    num_results: int,
    query: str = "",
    intent_type: str | None = None,
    grounding_citations: list[str] | None = None,
    low_signal_threshold: float = ResultQualityAnalyzer.LOW_SIGNAL_QUALITY_THRESHOLD,
    grounding_trust_citations: bool = True,
    grounding_relevance_threshold: float = 0.5,
    grounding_sparse_snippet_max_len: int = 80,
    grounding_citation_trust_top_k: int = 3,
    grounding_min_must_scrape: int = 1,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Partition grounding citations with trust floor + social demotion (§3.3)."""
    if not results:
        return [], [], []

    enriched = _enrich_grounding_quality(
        quality_analyzer,
        results,
        query=query,
        relevance_threshold=grounding_relevance_threshold,
        sparse_snippet_max_len=grounding_sparse_snippet_max_len,
    )

    # Prefer provider citation order for trust floor; rank_results still used as tie-break.
    ordered = sorted(
        enriched,
        key=lambda r: (
            r.get("_citation_rank") or 999,
            -float((r.get("_quality") or {}).get("quality_score", 0.0)),
        ),
    )

    primary: List[Dict[str, Any]] = []
    low_signal: List[Dict[str, Any]] = []

    for result in ordered:
        if _is_social_noise(quality_analyzer, result):
            low_signal.append(result)
            continue

        quality = result.get("_quality") or {}
        summary = result.get("_quality_summary") or {}
        quality_score = float(quality.get("quality_score", 0.0))
        is_relevant = bool(summary.get("is_relevant", False))
        snippet_len = len(result.get("snippet") or "")
        rank = int(result.get("_citation_rank") or 999)
        trust_floor = grounding_trust_citations and rank <= grounding_citation_trust_top_k and snippet_len < grounding_sparse_snippet_max_len

        demote_for_quality = quality_score < low_signal_threshold
        demote_for_irrelevant = (not is_relevant) and quality_score < 0.55

        if demote_for_quality:
            low_signal.append(result)
        elif demote_for_irrelevant and not trust_floor:
            low_signal.append(result)
        else:
            primary.append(result)

    # Rule 4: sparse-set primary promotion
    if not primary:
        non_social = [r for r in ordered if not _is_social_noise(quality_analyzer, r)]
        if non_social:
            primary = non_social[: max(1, min(num_results, len(non_social)))]
            primary_ids = {id(r) for r in primary}
            low_signal = [r for r in ordered if id(r) not in primary_ids]
        else:
            primary = []
            low_signal = list(ordered)

    primary = primary[:num_results]

    must_scrape = build_must_scrape_urls_grounding(
        ordered,
        primary=primary,
        grounding_citations=grounding_citations,
        intent_type=intent_type,
        grounding_min_must_scrape=grounding_min_must_scrape,
        top_k=max(3, grounding_min_must_scrape),
    )
    return primary, low_signal, must_scrape


def build_must_scrape_urls_grounding(
    results: List[Dict[str, Any]],
    *,
    primary: List[Dict[str, Any]] | None = None,
    grounding_citations: list[str] | None = None,
    intent_type: str | None = None,
    grounding_min_must_scrape: int = 1,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """CSE must_scrape plus grounding fallback / intent floor (§3.3 rules 5–6)."""
    must_scrape = build_must_scrape_urls_cse(results, top_k=top_k)
    non_social = [r for r in results if not _is_social_noise_domain(_result_domain(r))]
    citation_urls = [u for u in (grounding_citations or []) if u and not _url_is_social(u)]
    if not citation_urls:
        citation_urls = [(r.get("link") or r.get("url") or "") for r in non_social if (r.get("link") or r.get("url"))]

    # Rule 5: fallback when empty but non-social citations exist
    if not must_scrape and citation_urls:
        for url in citation_urls[:top_k]:
            must_scrape.append(
                {
                    "url": url,
                    "score": 0.5,
                    "reason": "grounding_citation",
                }
            )

    # Rule 6: demographic/causal floor
    intent = (intent_type or "").lower()
    needs_floor = intent in {
        QueryIntentType.DEMOGRAPHIC.value,
        QueryIntentType.CAUSAL.value,
        "demographic",
        "causal",
    }
    if needs_floor and citation_urls and len(must_scrape) < grounding_min_must_scrape:
        existing = {item.get("url") for item in must_scrape}
        for url in citation_urls:
            if url in existing:
                continue
            must_scrape.append(
                {
                    "url": url,
                    "score": 0.5,
                    "reason": "grounding_citation",
                }
            )
            if len(must_scrape) >= grounding_min_must_scrape:
                break

    # Prefer primary non-social URLs first when filling floor from thin quality
    if needs_floor and primary and len(must_scrape) < grounding_min_must_scrape:
        existing = {item.get("url") for item in must_scrape}
        for result in primary:
            if _is_social_noise_domain(_result_domain(result)):
                continue
            url = result.get("link") or result.get("url") or ""
            if not url or url in existing:
                continue
            must_scrape.append(
                {
                    "url": url,
                    "score": float((result.get("_quality") or {}).get("quality_score", 0.5)),
                    "reason": "grounding_citation",
                }
            )
            if len(must_scrape) >= grounding_min_must_scrape:
                break

    return must_scrape[:top_k]


def _enrich_grounding_quality(
    quality_analyzer: ResultQualityAnalyzer,
    results: List[Dict[str, Any]],
    *,
    query: str,
    relevance_threshold: float,
    sparse_snippet_max_len: int,
) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for position, original in enumerate(results, start=1):
        result = dict(original)
        snippet = result.get("snippet") or ""
        analysis_row = result
        if len(snippet.strip()) < sparse_snippet_max_len:
            # Score title + displayLink when snippets are thin/empty (§3.3 rule 2)
            analysis_row = {
                **result,
                "snippet": f"{result.get('title', '')} {result.get('displayLink', '')}".strip(),
            }

        if "_quality" not in result or not result.get("_quality_summary"):
            quality = quality_analyzer.analyze_result_quality(analysis_row, query or "", position)
            result["_quality"] = quality
            result["_quality_summary"] = {
                "score": quality["quality_score"],
                "level": quality["credibility_level"],
                "is_authoritative": quality["authority_score"] > 0.8,
                "is_relevant": quality["relevance_score"] > relevance_threshold,
                "is_fresh": quality["freshness_score"] > 0.7,
                "warnings_count": len(quality["warnings"]),
            }
        else:
            # Re-apply relaxed relevance threshold for grounding
            quality = result.get("_quality") or {}
            summary = dict(result.get("_quality_summary") or {})
            summary["is_relevant"] = float(quality.get("relevance_score", 0.0)) > relevance_threshold
            result["_quality_summary"] = summary

        # Trust-floor bootstrap for top sparse citations
        rank = int(result.get("_citation_rank") or position)
        if rank <= 3 and len(snippet.strip()) < sparse_snippet_max_len and not _is_social_noise(quality_analyzer, result):
            summary = dict(result.get("_quality_summary") or {})
            if not summary.get("is_relevant"):
                # Soft bootstrap: keep score but mark relevant enough for trust floor path
                summary.setdefault("is_relevant", False)
            result["_quality_summary"] = summary

        enriched.append(result)
    return enriched


def _is_social_noise(quality_analyzer: ResultQualityAnalyzer, result: Dict[str, Any]) -> bool:
    return _is_social_noise_domain(_result_domain(result), quality_analyzer)


def _is_social_noise_domain(
    domain: str,
    quality_analyzer: ResultQualityAnalyzer | None = None,
) -> bool:
    domain_lower = (domain or "").lower().lstrip(".")
    if not domain_lower:
        return False
    social_map = quality_analyzer.SOCIAL_NOISE_DOMAINS if quality_analyzer is not None else ResultQualityAnalyzer.SOCIAL_NOISE_DOMAINS
    if domain_lower in social_map:
        return True
    for social_domain in social_map:
        if domain_lower == social_domain or domain_lower.endswith("." + social_domain):
            return True
        # "www.facebook.com".endswith("facebook.com")
        if domain_lower.endswith(social_domain) and (len(domain_lower) == len(social_domain) or domain_lower[-(len(social_domain) + 1)] == "."):
            return True
    return False


def _result_domain(result: Dict[str, Any]) -> str:
    domain = result.get("displayLink") or result.get("domain") or ""
    if domain:
        return str(domain)
    link = result.get("link") or result.get("url") or ""
    return urlparse(str(link)).netloc


def _url_is_social(url: str) -> bool:
    return _is_social_noise_domain(urlparse(url).netloc)
