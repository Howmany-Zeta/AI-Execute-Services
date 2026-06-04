"""Tests for temporal memory ingest queue refcount lifecycle."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from aiecs.infrastructure.temporal_memory.ingest_queue import TemporalMemoryIngestQueue


@pytest.mark.unit
@pytest.mark.asyncio
async def test_release_shuts_down_only_when_last_holder() -> None:
    queue = TemporalMemoryIngestQueue()

    await queue.acquire()
    await queue.acquire()
    assert queue.running
    assert queue.holder_count == 2

    await queue.release()
    assert queue.running
    assert queue.holder_count == 1

    await queue.release()
    assert not queue.running
    assert queue.holder_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enqueue_updates_ingest_queue_depth_metric() -> None:
    queue = TemporalMemoryIngestQueue()
    mock_metrics = MagicMock()

    with patch(
        "aiecs.infrastructure.temporal_memory.metrics.get_temporal_memory_metrics",
        return_value=mock_metrics,
    ):
        await queue.acquire()

        async def noop() -> None:
            return None

        await queue.enqueue(noop)
        mock_metrics.set_ingest_queue_depth.assert_called()

        await queue.release()

    assert not queue.running


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enqueue_runs_work_before_shutdown() -> None:
    queue = TemporalMemoryIngestQueue()
    done = asyncio.Event()

    async def work() -> None:
        done.set()

    await queue.acquire()
    await queue.enqueue(work)
    await asyncio.wait_for(done.wait(), timeout=2.0)
    await queue.release()
    assert not queue.running


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_wide_acquire_release_refcount() -> None:
    import aiecs.infrastructure.temporal_memory.ingest_queue as mod
    from aiecs.infrastructure.temporal_memory.ingest_queue import (
        acquire_temporal_memory_ingest_queue,
        get_temporal_memory_ingest_queue,
        release_temporal_memory_ingest_queue,
    )

    mod._queue = None
    try:
        await acquire_temporal_memory_ingest_queue()
        await acquire_temporal_memory_ingest_queue()
        queue = get_temporal_memory_ingest_queue()
        assert queue.holder_count == 2
        assert queue.running

        await release_temporal_memory_ingest_queue()
        assert queue.running
        assert queue.holder_count == 1

        await release_temporal_memory_ingest_queue()
        assert not queue.running
        assert queue.holder_count == 0
    finally:
        mod._queue = None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_worker_swallows_job_failures_and_continues() -> None:
    queue = TemporalMemoryIngestQueue()
    ok = asyncio.Event()

    async def bad() -> None:
        raise RuntimeError("ingest boom")

    async def good() -> None:
        ok.set()

    await queue.acquire()
    await queue.enqueue(bad)
    await queue.enqueue(good)
    await asyncio.wait_for(ok.wait(), timeout=2.0)
    assert queue.running
    await queue.release()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_timeout_cancels_stuck_worker() -> None:
    queue = TemporalMemoryIngestQueue()
    started = asyncio.Event()

    async def block_forever() -> None:
        started.set()
        await asyncio.Event().wait()

    await queue.acquire()
    await queue.enqueue(block_forever)
    await asyncio.wait_for(started.wait(), timeout=2.0)

    with patch.object(asyncio, "wait_for", side_effect=asyncio.TimeoutError):
        await queue.shutdown()

    assert not queue.running
    assert queue.holder_count == 1
    await queue.release()
    assert queue.holder_count == 0
