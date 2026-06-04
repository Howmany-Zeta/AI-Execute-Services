# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Factory for optional private L2 graph store (ADR-003)."""

from __future__ import annotations

import importlib
import logging
from typing import Any

from aiecs.config.config import Settings, get_settings
from aiecs.infrastructure.knowledge.noop_graph_store import NoOpGraphStore

logger = logging.getLogger(__name__)


def resolve_kg_enabled(settings: Settings | None = None) -> bool:
    """True when ``Settings.kg_enabled`` (``KG_ENABLED`` env) is set."""
    settings = settings or get_settings()
    return bool(settings.kg_enabled)


def create_graph_store(settings: Settings | None = None) -> Any:
    """
    Resolve the active graph store for L2 integration.

    - ``KG_ENABLED=false`` → :class:`NoOpGraphStore`
    - ``KG_ENABLED=true`` + backend import failure → ``NoOpGraphStore`` + warning
    - ``KG_ENABLED=true`` + backend present → ``module.create_graph_store(settings)``
    """
    settings = settings or get_settings()

    if not resolve_kg_enabled(settings):
        return NoOpGraphStore()

    module_name = settings.kg_backend_module
    try:
        backend = importlib.import_module(module_name)
    except ImportError as exc:
        logger.warning(
            "KG_ENABLED=true but backend module %r is not installed (%s); using NoOpGraphStore",
            module_name,
            exc,
        )
        return NoOpGraphStore()

    factory = getattr(backend, "create_graph_store", None)
    if factory is None:
        logger.warning(
            "KG_ENABLED=true but %r has no create_graph_store(); using NoOpGraphStore",
            module_name,
        )
        return NoOpGraphStore()

    try:
        store = factory(settings)
    except Exception as exc:
        logger.warning(
            "create_graph_store() from %r failed (%s); using NoOpGraphStore",
            module_name,
            exc,
        )
        return NoOpGraphStore()

    if isinstance(store, NoOpGraphStore):
        return store
    return store
