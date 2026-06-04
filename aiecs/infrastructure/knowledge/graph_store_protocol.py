# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Minimal GraphStore port for L2 KnowledgePlugin (ADR-003)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GraphStoreProtocol(Protocol):
    """Subset of graph store operations consumed by KnowledgePlugin / L2 shell."""

    async def search(self, query: str, *, limit: int = 10, **kwargs: Any) -> list[Any]:
        """Search entities for a query string."""
        ...

    async def add_entity(self, entity: Any, **kwargs: Any) -> None:
        """Persist an entity (no-op acceptable for stubs)."""
        ...
