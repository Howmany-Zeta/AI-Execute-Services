# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""GVR-aware compaction preservation (A-10)."""

from __future__ import annotations

_GVR_PROTECT_MARKERS: tuple[str, ...] = (
    "deliverable_refs",
    "acceptance_criteria",
    "criterion_id",
    "success_criteria",
    '"gvr_protected": true',
    '"gvr_protected":true',
)


def is_gvr_protected_tool_content(content: str) -> bool:
    """Return True when tool result content must survive microcompact clearing."""
    if not content or content.strip() == "":
        return False
    lower = content.lower()
    return any(marker in lower for marker in _GVR_PROTECT_MARKERS)
