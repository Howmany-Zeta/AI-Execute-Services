# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Map aiecs CompactProgressEvent → host SSE payload (CC-094).

Emits the host event name ``context_compact_progress``; SSE transport stays in
python-middleware (``app/services/multi_task/``).
"""

from __future__ import annotations

from typing import Any

from aiecs.domain.context.compression.progress import CompactProgressEvent


def compact_progress_event_to_sse_payload(
    event: CompactProgressEvent,
    *,
    session_id: str = "",
    task_id: str = "",
) -> dict[str, Any]:
    """Build a dict suitable for host SSE ``context_compact_progress``."""
    return {
        "event": "context_compact_progress",
        "session_id": session_id,
        "task_id": task_id,
        "phase": event.phase,
        "checkpoint": event.checkpoint,
        "pre_tokens": event.pre_tokens,
        "post_tokens": event.post_tokens,
        "metadata": dict(event.metadata),
    }
