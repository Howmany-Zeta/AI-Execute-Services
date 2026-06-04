# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Resolve Graphiti ``group_id`` values for agent/session isolation.

Graphiti ``validate_group_id`` allows ASCII alphanumerics, dashes, and underscores only.
Do not embed raw PII (emails, names) in group ids — use opaque agent/session identifiers.
"""

from __future__ import annotations

import re

from aiecs.config.config import Settings, get_settings

_GRAPHITI_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9_-]+")


def _sanitize_segment(value: str) -> str:
    """Map arbitrary ids to Graphiti-safe segments."""
    cleaned = _GRAPHITI_SAFE_SEGMENT.sub("_", (value or "").strip())
    return cleaned or "default"


def build_group_ids(
    agent_id: str,
    session_id: str,
    tenant_id: str | None = None,
    *,
    settings: Settings | None = None,
) -> list[str]:
    """
    Build group_ids for ingest and search.

    Primary: ``{prefix}:{agent_id}:{session_id}``
    Optional tenant scope: ``{prefix}:tenant:{tenant_id}`` when tenant_id is set.
    """
    settings = settings or get_settings()
    prefix = _sanitize_segment(settings.tm_group_id_prefix or "aiecs")
    agent = _sanitize_segment(agent_id)
    session = _sanitize_segment(session_id)

    group_ids = [f"{prefix}:{agent}:{session}"]

    if tenant_id:
        tenant = _sanitize_segment(tenant_id)
        group_ids.append(f"{prefix}:tenant:{tenant}")

    return group_ids


def select_search_group_ids(
    group_ids: list[str],
    *,
    settings: Settings | None = None,
) -> list[str]:
    """Return group_ids passed to store search (primary-only when configured)."""
    settings = settings or get_settings()
    if settings.tm_search_primary_group_only and group_ids:
        return [group_ids[0]]
    return list(group_ids)


def select_ingest_group_ids(
    group_ids: list[str],
    *,
    settings: Settings | None = None,
) -> list[str]:
    """Return group_ids for episode ingest (all scopes or primary only)."""
    settings = settings or get_settings()
    if not group_ids:
        return []
    if settings.tm_ingest_all_group_ids:
        return list(group_ids)
    return [group_ids[0]]
