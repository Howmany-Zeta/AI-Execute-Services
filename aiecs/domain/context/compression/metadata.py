# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""F2 compact layer metadata contract (Epic 3)."""

from __future__ import annotations

from typing import Any

LAYER_L2 = "L2"
LAYER_L3 = "L3"

KEY_LAYER = "layer"
KEY_FORMATTED_TRANSCRIPT = "formatted_transcript"
KEY_SESSION_ID = "session_id"
KEY_AGENT_ID = "agent_id"
KEY_CHECKPOINT = "checkpoint"
KEY_ESTIMATED_TOKENS = "estimated_tokens"


def build_pre_compact_metadata(
    *,
    layer: str,
    session_id: str = "",
    agent_id: str = "",
    formatted_transcript: bool = False,
    estimated_tokens: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Standard PreCompactContext.metadata keys (F2-01)."""
    metadata: dict[str, Any] = {
        KEY_LAYER: layer,
        KEY_FORMATTED_TRANSCRIPT: formatted_transcript,
    }
    if session_id:
        metadata[KEY_SESSION_ID] = session_id
    if agent_id:
        metadata[KEY_AGENT_ID] = agent_id
    if estimated_tokens is not None:
        metadata[KEY_ESTIMATED_TOKENS] = estimated_tokens
    if extra:
        metadata.update(extra)
    return metadata


def build_post_compact_metadata(
    *,
    layer: str,
    checkpoint: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Standard PostCompactContext.metadata keys (F2-02)."""
    metadata: dict[str, Any] = {KEY_LAYER: layer}
    if checkpoint:
        metadata[KEY_CHECKPOINT] = checkpoint
    if extra:
        metadata.update(extra)
    return metadata


def merge_pre_compact_metadata(base: dict[str, Any] | None, overlay: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base or {})
    if overlay:
        merged.update(overlay)
    return merged
