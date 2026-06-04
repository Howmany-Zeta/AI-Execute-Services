# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""No-op graph store when KG is disabled or private backend is unavailable."""

from __future__ import annotations

from typing import Any


class NoOpGraphStore:
    """Stub GraphStore: safe defaults, no I/O."""

    store_id: str = "noop"

    async def search(self, query: str, *, limit: int = 10, **kwargs: Any) -> list[Any]:
        _ = query, limit, kwargs
        return []

    async def add_entity(self, entity: Any, **kwargs: Any) -> None:
        _ = entity, kwargs
        return None

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None
