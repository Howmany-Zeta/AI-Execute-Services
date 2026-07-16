# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Optional async→sync bridge for **custom** grounding backends only (M-D.5 §3.4).

Built-in Gemini / Grok / Google CSE backends are synchronous and **must not**
import or call this module. Consumers with async-only HTTP clients (e.g. Exa)
may use ``run_async_from_sync`` inside their ``GroundingSearchBackend.search()``.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def run_async_from_sync(coro: Coroutine[Any, Any, T], *, timeout: float) -> T:
    """
    Run a coroutine from a sync ``search()`` implementation safely.

    * No running loop → ``asyncio.run(wait_for(...))``.
    * Running loop present → isolate in a worker thread (never nest ``asyncio.run``
      on the caller's loop).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(asyncio.wait_for(coro, timeout=timeout))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lambda: asyncio.run(asyncio.wait_for(coro, timeout=timeout)))
        return future.result()
