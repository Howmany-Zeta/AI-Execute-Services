# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""In-process asyncio queue for non-blocking temporal memory POST_TASK ingest."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_SHUTDOWN = object()
IngestWork = Callable[[], Awaitable[None]]


class TemporalMemoryIngestQueue:
    """
    Background worker for temporal memory ingest jobs.

    POST_TASK enqueues work only; failures are logged and never propagate to the agent.
    Use :meth:`acquire` / :meth:`release` for multi-agent lifecycle (refcounted shutdown).
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None
        self._holders: int = 0

    @property
    def running(self) -> bool:
        return self._worker is not None and not self._worker.done()

    @property
    def holder_count(self) -> int:
        return self._holders

    async def acquire(self) -> None:
        """Register an agent; start the worker on first acquire."""
        self._holders += 1
        await self.start()

    async def release(self) -> None:
        """Unregister an agent; shutdown the worker when the last holder releases."""
        if self._holders <= 0:
            return
        self._holders -= 1
        if self._holders == 0:
            await self.shutdown()

    async def start(self) -> None:
        if self.running:
            return
        self._worker = asyncio.create_task(self._run_worker(), name="temporal-memory-ingest")

    def _sync_ingest_queue_depth_metric(self) -> None:
        try:
            from aiecs.infrastructure.temporal_memory.metrics import get_temporal_memory_metrics

            get_temporal_memory_metrics().set_ingest_queue_depth(self._queue.qsize())
        except Exception:
            pass

    async def enqueue(self, work: IngestWork) -> None:
        await self.start()
        await self._queue.put(work)
        self._sync_ingest_queue_depth_metric()

    async def shutdown(self) -> None:
        if not self.running:
            return
        await self._queue.put(_SHUTDOWN)
        assert self._worker is not None
        try:
            await asyncio.wait_for(self._worker, timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("Temporal memory ingest queue shutdown timed out; cancelling worker")
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
        self._worker = None

    async def _run_worker(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                if item is _SHUTDOWN:
                    break
                await item()
            except Exception as exc:
                logger.warning("Temporal memory ingest queue job failed: %s", exc, exc_info=True)
            finally:
                self._queue.task_done()
                self._sync_ingest_queue_depth_metric()


_queue: TemporalMemoryIngestQueue | None = None


def get_temporal_memory_ingest_queue() -> TemporalMemoryIngestQueue:
    """Process-wide ingest queue (single worker shared across agents)."""
    global _queue
    if _queue is None:
        _queue = TemporalMemoryIngestQueue()
    return _queue


async def acquire_temporal_memory_ingest_queue() -> None:
    """Hold a refcount on the process-wide queue (call from plugin ``on_agent_init``)."""
    await get_temporal_memory_ingest_queue().acquire()


async def release_temporal_memory_ingest_queue() -> None:
    """Release a refcount; stops the worker when no agents hold the queue."""
    await get_temporal_memory_ingest_queue().release()
