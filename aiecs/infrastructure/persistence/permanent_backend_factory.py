# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Factory for ContextEngine permanent storage backends (dual-write cold archive).

Selection via environment variables:

    CONTEXT_PERMANENT_BACKEND=postgres|clickhouse|none

Backward compatibility:
    CLICKHOUSE_ENABLED=true  (when CONTEXT_PERMANENT_BACKEND is unset) -> clickhouse

PostgreSQL connection (backend=postgres):
    CONTEXT_PG_URL  or  POSTGRES_URL  or  main DB settings from Settings

ClickHouse connection (backend=clickhouse):
    CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from aiecs.core.interface.storage_interface import IPermanentStorageBackend

logger = logging.getLogger(__name__)

PermanentBackendKind = Literal["none", "clickhouse", "postgres"]


def resolve_permanent_backend_kind() -> PermanentBackendKind:
    """Resolve configured permanent backend kind from environment."""
    explicit = os.getenv("CONTEXT_PERMANENT_BACKEND", "").strip().lower()
    if explicit:
        if explicit in ("none", "off", "false", "disabled", "0"):
            return "none"
        if explicit in ("clickhouse", "ch"):
            return "clickhouse"
        if explicit in ("postgres", "postgresql", "pg"):
            return "postgres"
        logger.warning(
            "Unknown CONTEXT_PERMANENT_BACKEND=%r; dual-write disabled. " "Use: postgres, clickhouse, or none.",
            explicit,
        )
        return "none"

    if os.getenv("CLICKHOUSE_ENABLED", "").lower() in ("true", "1", "yes"):
        return "clickhouse"

    return "none"


def create_permanent_backend() -> IPermanentStorageBackend | None:
    """Create permanent storage backend instance from environment, or None if disabled."""
    kind = resolve_permanent_backend_kind()
    if kind == "none":
        return None

    if kind == "clickhouse":
        try:
            from .clickhouse_permanent_backend import ClickHousePermanentBackend

            logger.info("ContextEngine permanent backend: clickhouse")
            return ClickHousePermanentBackend()
        except ImportError as e:
            logger.warning(f"ClickHouse permanent backend not available: {e}")
            return None

    if kind == "postgres":
        try:
            from .postgres_permanent_backend import PostgresPermanentBackend

            logger.info("ContextEngine permanent backend: postgres")
            return PostgresPermanentBackend()
        except ImportError as e:
            logger.warning(f"Postgres permanent backend not available: {e}")
            return None

    return None
