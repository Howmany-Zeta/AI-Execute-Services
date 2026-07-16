# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Routing-aware cache fingerprint for SearchTool (M-D.5 §3.2).

Included in ``@cache_result_with_strategy`` keys via ``_cache_routing_fingerprint``
so grounding rollout does not reuse CSE-era cache entries.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .backends.registry import normalize_backend_name, normalize_provider_chain

CACHE_SCHEMA_VERSION = "m-d.5"

_BUILTIN_BACKENDS = frozenset({"gemini", "grok", "google_cse", "auto"})


def build_routing_cache_fingerprint(
    config: Any,
    overrides: Mapping[str, Any] | None = None,
    custom_backend_names: Sequence[str] | None = None,
) -> str:
    """
    Build a stable fingerprint string for search cache keys.

    Does **not** include API keys or credential file paths — only auth *modes*,
    routing configuration, and partition / grounding tuning knobs (§3.2 / §3.3).
    """
    overrides = dict(overrides or {})

    provider = overrides.get("grounding_provider")
    if provider is None:
        provider = getattr(config, "grounding_provider", "auto")
    provider = normalize_backend_name(str(provider or "auto"))

    chain_raw = overrides.get("grounding_provider_chain")
    if chain_raw is None:
        chain_raw = getattr(config, "grounding_provider_chain", "gemini,grok,google_cse")
    chain = ",".join(normalize_provider_chain(str(chain_raw or "")))

    batch_mode = overrides.get("batch_routing_mode")
    if batch_mode is None:
        batch_mode = getattr(config, "batch_routing_mode", "pin_on_first_success")

    schema = getattr(config, "cache_schema_version", None) or CACHE_SCHEMA_VERSION
    custom = sorted({str(n).strip() for n in (custom_backend_names or []) if str(n).strip()})

    payload = {
        "cache_schema_version": str(schema),
        "grounding_provider": provider,
        "grounding_provider_chain": chain,
        "gemini_grounding_auth": str(getattr(config, "gemini_grounding_auth", "auto") or "auto").lower(),
        "grok_grounding_auth": str(getattr(config, "grok_grounding_auth", "auto") or "auto").lower(),
        "grok_maas_web_search_enabled": bool(getattr(config, "grok_maas_web_search_enabled", False)),
        "custom_backend_names": custom,
        "rewrite_before_grounding": bool(getattr(config, "rewrite_before_grounding", True)),
        "batch_routing_mode": str(batch_mode or "pin_on_first_success"),
        "search_error_mode": str(getattr(config, "search_error_mode", "auto") or "auto").lower(),
        # Partition / grounding profile knobs — changing these must miss cache (§3.3).
        "grounding_trust_citations": bool(getattr(config, "grounding_trust_citations", True)),
        "grounding_relevance_threshold": float(getattr(config, "grounding_relevance_threshold", 0.5) or 0.5),
        "grounding_sparse_snippet_max_len": int(getattr(config, "grounding_sparse_snippet_max_len", 80) or 80),
        "grounding_citation_trust_top_k": int(getattr(config, "grounding_citation_trust_top_k", 3) or 3),
        "grounding_min_must_scrape": int(getattr(config, "grounding_min_must_scrape", 1) or 1),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def filter_custom_backend_names(registered_names: Sequence[str]) -> list[str]:
    """Return sorted consumer backend names (exclude built-ins)."""
    names: list[str] = []
    for name in registered_names:
        canonical = normalize_backend_name(str(name or ""))
        if not canonical or canonical in _BUILTIN_BACKENDS:
            continue
        names.append(canonical)
    return sorted(set(names))
