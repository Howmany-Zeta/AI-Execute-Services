# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""O4: Auto-compact state tracking across turns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AutoCompactState:
    """Mutable state persisted across tool-loop / query turns (O4)."""

    consecutive_failures: int = 0
    last_trigger: str | None = None
    reactive_compact_used: bool = False
    proactive_compact_used_this_iteration: bool = False
