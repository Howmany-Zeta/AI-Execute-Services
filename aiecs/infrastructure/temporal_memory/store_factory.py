# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Factory for optional L1 temporal memory store (symmetric to create_graph_store)."""

from __future__ import annotations

import logging
from typing import Literal

from aiecs.config.config import Settings, get_settings
from aiecs.domain.temporal_memory.ports import TemporalMemoryStore
from aiecs.infrastructure.temporal_memory.noop_store import NoOpTemporalMemoryStore

logger = logging.getLogger(__name__)

TemporalMemoryBackend = Literal["none", "graphiti", "postgres"]


def resolve_temporal_memory_backend(settings: Settings | None = None) -> TemporalMemoryBackend:
    """Resolve backend from ``TM_ENABLED`` / ``TM_BACKEND``."""
    settings = settings or get_settings()
    if not settings.tm_enabled:
        return "none"
    backend = (settings.tm_backend or "none").strip().lower()
    if backend in ("none", "graphiti", "postgres"):
        return backend  # type: ignore[return-value]
    logger.warning("Unknown TM_BACKEND=%r; using none", settings.tm_backend)
    return "none"


def create_temporal_memory_store(settings: Settings | None = None) -> TemporalMemoryStore:
    """
    Resolve the active temporal memory store.

    - ``TM_ENABLED=false`` or ``TM_BACKEND=none`` → :class:`NoOpTemporalMemoryStore`
    - ``TM_BACKEND=graphiti`` + graphiti-core installed → :class:`GraphitiTemporalMemoryStore`
    - ``ImportError`` for missing graphiti-core → :class:`NoOpTemporalMemoryStore` + warning
    - Runtime connection / ``initialize()`` failures are **not** converted here (TM-069);
      :class:`TemporalMemoryPlugin` disables the plugin and calls ``store.close()`` (best-effort)
    """
    settings = settings or get_settings()
    backend = resolve_temporal_memory_backend(settings)

    if backend == "none":
        return NoOpTemporalMemoryStore()

    if backend == "graphiti":
        try:
            from aiecs.infrastructure.temporal_memory.graphiti.store import (
                GraphitiTemporalMemoryStore,
            )

            return GraphitiTemporalMemoryStore(settings=settings)
        except ImportError as exc:
            logger.warning(
                "TM_BACKEND=graphiti but graphiti-core is not installed (%s); using NoOpTemporalMemoryStore",
                exc,
            )
            return NoOpTemporalMemoryStore()

    if backend == "postgres":
        logger.warning("TM_BACKEND=postgres is not implemented (Phase 5); using NoOpTemporalMemoryStore")
        return NoOpTemporalMemoryStore()

    return NoOpTemporalMemoryStore()
