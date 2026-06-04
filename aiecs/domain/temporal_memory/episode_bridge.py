# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Episode bridge helpers — L1 ingest pointers into L0 Context metadata (one-way, TM-078/079).

POST_TASK runs **memory (80) before temporal_memory (85)**, so ``MemoryPlugin.on_post_task``
cannot see L1 ingest ids yet. When ``temporal_memory_enabled=true``:

1. ``MemoryPlugin`` defers the assistant turn in ``plugin_state['memory.pending_assistant']``.
2. ``TemporalMemoryPlugin`` ingests, writes ``temporal_memory.*`` plugin_state keys, then calls
   ``flush_pending_assistant_turn`` with :func:`build_l0_temporal_metadata`.

When L1 is off, assistant is written immediately (Phase 0–2 behavior).

**Custom plugin chains** must call ``flush_pending_assistant_turn`` after L1 ingest or on
shutdown; standard Hybrid + builtin plugins do this automatically. See ``DOMAIN_CONTEXT.md``.
"""

from __future__ import annotations

from typing import Any

from aiecs.domain.temporal_memory.constants import (
    METADATA_TEMPORAL_EPISODE_ID,
    METADATA_TEMPORAL_GROUP_ID,
    METADATA_TEMPORAL_INGEST_JOB_ID,
    build_l0_temporal_metadata,
)

__all__ = [
    "METADATA_TEMPORAL_EPISODE_ID",
    "METADATA_TEMPORAL_GROUP_ID",
    "METADATA_TEMPORAL_INGEST_JOB_ID",
    "build_l0_temporal_metadata",
    "has_temporal_metadata",
]


def has_temporal_metadata(metadata: dict[str, Any] | None) -> bool:
    """True when L0 message metadata contains any temporal bridge key."""
    if not metadata:
        return False
    return any(
        key in metadata
        for key in (
            METADATA_TEMPORAL_EPISODE_ID,
            METADATA_TEMPORAL_GROUP_ID,
            METADATA_TEMPORAL_INGEST_JOB_ID,
        )
    )
