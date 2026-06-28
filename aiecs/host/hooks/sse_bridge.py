# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Map agent hook observability events → host SSE payload (H4-02).

HybridAgent streaming sets ``plugin_ctx.event_sink``; ``dispatch_agent_hook`` emits
``type="agent_hook"`` dicts. Host owns Socket.IO/SSE transport — aiecs only shapes payloads.
"""

from __future__ import annotations

from typing import Any


def agent_hook_event_to_sse_payload(
    event: dict[str, Any],
    *,
    session_id: str = "",
    task_id: str = "",
) -> dict[str, Any]:
    """Build host SSE payload for ``agent_hook`` streaming events."""
    return {
        "event": "agent_hook",
        "session_id": session_id,
        "task_id": task_id or event.get("task_id"),
        "hook_event": event.get("event"),
        "blocked": event.get("blocked", False),
        "hook_count": event.get("hook_count", 0),
        "duration_ms": event.get("duration_ms"),
    }
