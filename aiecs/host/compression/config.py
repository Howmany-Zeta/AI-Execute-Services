# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Host feature flags for aiecs compression migration (CC-095)."""

from __future__ import annotations

import os


def use_aiecs_compression(default: bool = False) -> bool:
    """Return True when host should route L2/L3 through aiecs compression kernel.

    Reads ``USE_AIECS_COMPRESSION`` (``1``/``true``/``yes``/on). Host keeps L1
    warn-only and L2 boundary *policy*; this flag only selects the adapter path.
    """
    raw = os.environ.get("USE_AIECS_COMPRESSION", "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}
