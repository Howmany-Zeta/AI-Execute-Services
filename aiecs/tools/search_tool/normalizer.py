# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Grounding result normalization (M-D.5 §10 / §3.3).

Maps ``BackendRawResult`` citations into the SearchTool envelope shape and tags
each row with ``_result_source`` / ``_citation_rank`` for grounding partition.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .backends.protocol import BackendRawResult


def normalize_grounding_result(
    raw: BackendRawResult,
    backend_used: str,
    *,
    blocked_domains: list[str] | None = None,
    num_results: int | None = None,
) -> dict[str, Any]:
    """
    Normalize a successful grounding ``BackendRawResult`` into a partial envelope.

    Returns keys: ``results``, ``grounding_citations``, ``_search_metadata``;
    optionally ``grounding_answer`` when the provider returned synthesized text.
    """
    citations = list(raw.citations or [])
    # Gemini: post-filter blocked domains (§3.6) — defense in depth if backend skipped it.
    if blocked_domains and (backend_used == "gemini" or raw.backend == "gemini"):
        citations = filter_blocked_domain_citations(citations, blocked_domains)

    if num_results is not None and num_results > 0:
        citations = citations[:num_results]

    results: list[dict[str, Any]] = []
    grounding_citations: list[str] = []
    for rank, citation in enumerate(citations, start=1):
        link = _citation_link(citation)
        if not link:
            continue
        display = citation.get("domain") or citation.get("displayLink") or urlparse(link).netloc or ""
        snippet = citation.get("snippet") or ""
        results.append(
            {
                "title": citation.get("title") or "",
                "link": link,
                "url": link,
                "snippet": snippet,
                "displayLink": display,
                "formattedUrl": link,
                "_result_source": "grounding_citation",
                "_citation_rank": rank,
            }
        )
        grounding_citations.append(link)

    partial: dict[str, Any] = {
        "results": results,
        "grounding_citations": grounding_citations,
        "_search_metadata": {
            "backend_used": backend_used,
            "params_applied": list(raw.params_applied or []),
            "params_ignored": list(raw.params_ignored or []),
        },
    }
    if raw.answer:
        partial["grounding_answer"] = raw.answer
    return partial


def filter_blocked_domain_citations(
    citations: list[dict[str, Any]],
    blocked_domains: list[str],
) -> list[dict[str, Any]]:
    """Drop citations whose domain matches any blocked suffix (Gemini post-filter)."""
    blocked = {d.lower().lstrip(".") for d in blocked_domains if d}
    if not blocked:
        return list(citations)

    kept: list[dict[str, Any]] = []
    for citation in citations:
        domain = (citation.get("domain") or citation.get("displayLink") or urlparse(_citation_link(citation)).netloc or "").lower()
        if any(domain == b or domain.endswith("." + b) for b in blocked):
            continue
        kept.append(citation)
    return kept


def _citation_link(citation: dict[str, Any]) -> str:
    link = citation.get("url") or citation.get("link") or ""
    return str(link).strip()
