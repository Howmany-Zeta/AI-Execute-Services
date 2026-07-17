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
    optionally ``grounding_answer``, ``grounding_chunks``, ``grounding_supports``.

    ``grounding_chunks`` / ``grounding_supports`` use the full provider chunk index
    table and are **not** truncated by ``num_results`` (which only slices ``results[]``).
    """
    citations = list(raw.citations or [])
    grounding_chunks = list(raw.grounding_chunks or [])
    grounding_supports = list(raw.grounding_supports or [])
    # Gemini: post-filter blocked domains (§3.6) — defense in depth if backend skipped it.
    if blocked_domains and (backend_used == "gemini" or raw.backend == "gemini"):
        citations = filter_blocked_domain_citations(citations, blocked_domains)
        if grounding_chunks or grounding_supports:
            grounding_chunks, grounding_supports = filter_blocked_domain_grounding_alignment(
                grounding_chunks,
                grounding_supports,
                blocked_domains,
            )

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
    if grounding_chunks:
        partial["grounding_chunks"] = grounding_chunks
    if grounding_supports:
        partial["grounding_supports"] = grounding_supports
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
        if _domain_is_blocked(domain, blocked):
            continue
        kept.append(citation)
    return kept


def filter_blocked_domain_grounding_alignment(
    chunks: list[dict[str, Any]],
    supports: list[dict[str, Any]],
    blocked_domains: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply citation blocked-domain rules to Layer A chunks; prune orphan supports.

    Chunk ``index`` values stay stable (provider order). A support is dropped only
    when **all** of its ``grounding_chunk_indices`` refer to removed chunks.
    """
    blocked = {d.lower().lstrip(".") for d in blocked_domains if d}
    if not blocked:
        return list(chunks), list(supports)

    kept_chunks: list[dict[str, Any]] = []
    kept_indices: set[int] = set()
    for chunk in chunks:
        domain = (chunk.get("domain") or urlparse(str(chunk.get("url") or "")).netloc or "").lower()
        if _domain_is_blocked(domain, blocked):
            continue
        kept_chunks.append(chunk)
        try:
            kept_indices.add(int(chunk["index"]))
        except (KeyError, TypeError, ValueError):
            continue

    kept_supports: list[dict[str, Any]] = []
    for support in supports:
        indices = [int(i) for i in (support.get("grounding_chunk_indices") or [])]
        if not indices or any(i in kept_indices for i in indices):
            kept_supports.append(support)
    return kept_chunks, kept_supports


def _domain_is_blocked(domain: str, blocked: set[str]) -> bool:
    domain = (domain or "").lower()
    return any(domain == b or domain.endswith("." + b) for b in blocked)


def _citation_link(citation: dict[str, Any]) -> str:
    link = citation.get("url") or citation.get("link") or ""
    return str(link).strip()
