"""Tests for temporal memory store factory."""

from __future__ import annotations

import builtins
import logging
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from aiecs.config.config import Settings
from aiecs.infrastructure.temporal_memory import (
    NoOpTemporalMemoryStore,
    create_temporal_memory_store,
    resolve_temporal_memory_backend,
)


class _FakeGraphitiStore:
    store_id = "graphiti-fake"

    def __init__(self, settings: Settings | None = None) -> None:
        _ = settings


class _FakePostgresStore:
    store_id = "postgres-fake"

    def __init__(self, settings: Settings | None = None) -> None:
        _ = settings


def test_resolve_backend_none_when_disabled() -> None:
    settings = Settings(TM_ENABLED=False, TM_BACKEND="graphiti")
    assert resolve_temporal_memory_backend(settings) == "none"


def test_resolve_backend_graphiti_when_enabled() -> None:
    settings = Settings(TM_ENABLED=True, TM_BACKEND="graphiti")
    assert resolve_temporal_memory_backend(settings) == "graphiti"


def test_create_store_returns_noop_when_disabled() -> None:
    settings = Settings(TM_ENABLED=False)
    store = create_temporal_memory_store(settings)
    assert isinstance(store, NoOpTemporalMemoryStore)


def test_create_store_graphiti_import_error_returns_noop(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = Settings(TM_ENABLED=True, TM_BACKEND="graphiti")
    real_import = builtins.__import__

    def _import_raises(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiecs.infrastructure.temporal_memory.graphiti.store":
            raise ImportError("no graphiti_core")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=_import_raises):
        with caplog.at_level(logging.WARNING):
            store = create_temporal_memory_store(settings)

    assert isinstance(store, NoOpTemporalMemoryStore)
    assert any("graphiti-core" in r.message for r in caplog.records)


def test_create_store_graphiti_success_returns_graphiti_store() -> None:
    settings = Settings(TM_ENABLED=True, TM_BACKEND="graphiti")
    fake_module = SimpleNamespace(GraphitiTemporalMemoryStore=_FakeGraphitiStore)

    with patch.dict(
        "sys.modules",
        {"aiecs.infrastructure.temporal_memory.graphiti.store": fake_module},
    ):
        store = create_temporal_memory_store(settings)

    assert isinstance(store, _FakeGraphitiStore)


def test_create_store_postgres_returns_postgres_store() -> None:
    settings = Settings(
        TM_ENABLED=True,
        TM_BACKEND="postgres",
        TM_POSTGRES_URL="postgresql://user:pass@localhost/testdb",
    )
    fake_module = SimpleNamespace(PostgresTemporalMemoryStore=_FakePostgresStore)

    with patch.dict(
        "sys.modules",
        {"aiecs.infrastructure.temporal_memory.postgres.store": fake_module},
    ):
        store = create_temporal_memory_store(settings)

    assert isinstance(store, _FakePostgresStore)


def test_no_graphiti_import_on_noop_path() -> None:
    for name in list(sys.modules):
        if name == "graphiti_core" or name.startswith("graphiti_core."):
            del sys.modules[name]

    settings = Settings(TM_ENABLED=False)
    store = create_temporal_memory_store(settings)
    assert isinstance(store, NoOpTemporalMemoryStore)
    assert "graphiti_core" not in sys.modules
