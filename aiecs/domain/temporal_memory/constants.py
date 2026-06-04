# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Temporal memory plugin_state and L0 metadata key constants (episode_bridge, TM-078)."""

from __future__ import annotations

from typing import Any

# Written by TemporalMemoryPlugin (POST_TASK)
PLUGIN_STATE_INGEST_JOB_ID = "temporal_memory.ingest_job_id"
PLUGIN_STATE_EPISODE_ID = "temporal_memory.episode_id"
PLUGIN_STATE_GROUP_ID = "temporal_memory.group_id"
PLUGIN_STATE_FACTS_KEY = "temporal_memory.facts"

# Written by MemoryPlugin into ContextEngine message metadata (TM-079)
METADATA_TEMPORAL_EPISODE_ID = "temporal_episode_id"
METADATA_TEMPORAL_GROUP_ID = "temporal_group_id"
METADATA_TEMPORAL_INGEST_JOB_ID = "temporal_ingest_job_id"

# Internal: deferred assistant write when L1 runs after memory on POST_TASK
PLUGIN_STATE_PENDING_ASSISTANT = "memory.pending_assistant"


def build_l0_temporal_metadata(plugin_state: dict[str, Any]) -> dict[str, str]:
    """
    Map temporal_memory plugin_state keys to L0 conversation message metadata.

    Returns only keys with non-empty values (no temporal keys when L1 inactive).

    **Async ingest (``TM_INGEST_ASYNC``):** ``ingest_job_id`` is set before the worker runs;
    ``episode_id`` / ``group_id`` appear after ingest completes. Consumers that need the
    episode UUID must wait for flush (assistant metadata) or read ``episode_id`` after ingest,
    not rely on ``job_id`` alone as a surrogate for ``episode_id``.
    """
    meta: dict[str, str] = {}
    episode_id = plugin_state.get(PLUGIN_STATE_EPISODE_ID)
    group_id = plugin_state.get(PLUGIN_STATE_GROUP_ID)
    job_id = plugin_state.get(PLUGIN_STATE_INGEST_JOB_ID)
    if episode_id:
        meta[METADATA_TEMPORAL_EPISODE_ID] = str(episode_id)
    if group_id:
        meta[METADATA_TEMPORAL_GROUP_ID] = str(group_id)
    if job_id:
        meta[METADATA_TEMPORAL_INGEST_JOB_ID] = str(job_id)
    return meta
