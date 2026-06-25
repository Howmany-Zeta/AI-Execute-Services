# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""O7: CompactProgressEvent emission via callback and async iterator."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

COMPACT_PROGRESS_PHASES: tuple[str, ...] = (
    "hooks_start",
    "microcompact_start",
    "microcompact_done",
    "context_collapse_start",
    "context_collapse_done",
    "session_memory_start",
    "session_memory_done",
    "compact_start",
    "compact_done",
    "compact_failed",
)


@dataclass
class CompactProgressEvent:
    """Progress checkpoint emitted during compaction (host maps to SSE/UI)."""

    phase: str
    checkpoint: str | None = None
    pre_tokens: int | None = None
    post_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


ProgressCallback = Callable[[CompactProgressEvent], None]


class CompactProgressEmitter:
    """Deliver progress via optional callback and/or async iterator."""

    def __init__(self, on_progress: ProgressCallback | None = None) -> None:
        self._on_progress = on_progress
        self._queue: asyncio.Queue[CompactProgressEvent | None] | None = None
        self._history: list[CompactProgressEvent] = []

    @property
    def history(self) -> tuple[CompactProgressEvent, ...]:
        return tuple(self._history)

    def emit(
        self,
        phase: str,
        *,
        checkpoint: str | None = None,
        pre_tokens: int | None = None,
        post_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CompactProgressEvent:
        event = CompactProgressEvent(
            phase=phase,
            checkpoint=checkpoint,
            pre_tokens=pre_tokens,
            post_tokens=post_tokens,
            metadata=dict(metadata or {}),
        )
        self._history.append(event)
        if self._on_progress is not None:
            self._on_progress(event)
        if self._queue is not None:
            self._queue.put_nowait(event)
        return event

    def start_stream(self) -> None:
        if self._queue is None:
            self._queue = asyncio.Queue()

    async def iter_compact_progress(self) -> AsyncIterator[CompactProgressEvent]:
        """Async iterator over progress events for the current compact operation."""
        self.start_stream()
        assert self._queue is not None
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield event

    def finish_stream(self) -> None:
        if self._queue is not None:
            self._queue.put_nowait(None)
