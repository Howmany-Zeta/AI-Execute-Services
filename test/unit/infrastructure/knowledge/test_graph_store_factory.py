"""Tests for graph store factory (W-048)."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from aiecs.config.config import Settings
from aiecs.infrastructure.knowledge import NoOpGraphStore, create_graph_store, resolve_kg_enabled


class _FakeBackendStore:
    store_id = "fake"


def _fake_backend_create_graph_store(_settings: Settings) -> _FakeBackendStore:
    return _FakeBackendStore()


def test_resolve_kg_enabled_false_by_default() -> None:
    settings = Settings(KG_ENABLED=False)
    assert resolve_kg_enabled(settings) is False


def test_kg_disabled_returns_noop() -> None:
    settings = Settings(KG_ENABLED=False, KG_BACKEND_MODULE="aiecs_kg")
    store = create_graph_store(settings)
    assert isinstance(store, NoOpGraphStore)


def test_kg_enabled_import_error_returns_noop_and_warning(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(KG_ENABLED=True, KG_BACKEND_MODULE="missing_kg_backend_pkg")
    with patch(
        "aiecs.infrastructure.knowledge.graph_store_factory.importlib.import_module",
        side_effect=ImportError("no module"),
    ):
        with caplog.at_level(logging.WARNING):
            store = create_graph_store(settings)
    assert isinstance(store, NoOpGraphStore)
    assert any("not installed" in record.message for record in caplog.records)


def test_kg_enabled_mock_backend_returns_non_noop() -> None:
    settings = Settings(KG_ENABLED=True, KG_BACKEND_MODULE="fake_aiecs_kg")
    fake_module = SimpleNamespace(create_graph_store=_fake_backend_create_graph_store)
    with patch(
        "aiecs.infrastructure.knowledge.graph_store_factory.importlib.import_module",
        return_value=fake_module,
    ):
        store = create_graph_store(settings)
    assert not isinstance(store, NoOpGraphStore)
    assert isinstance(store, _FakeBackendStore)
