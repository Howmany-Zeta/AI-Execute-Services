"""Unit tests for permanent backend factory resolution."""

import os

import pytest

from aiecs.infrastructure.persistence.permanent_backend_factory import (
    create_permanent_backend,
    resolve_permanent_backend_kind,
)


@pytest.fixture(autouse=True)
def _clear_backend_env(monkeypatch):
    monkeypatch.delenv("CONTEXT_PERMANENT_BACKEND", raising=False)
    monkeypatch.delenv("CLICKHOUSE_ENABLED", raising=False)


def test_resolve_none_by_default():
    assert resolve_permanent_backend_kind() == "none"
    assert create_permanent_backend() is None


def test_resolve_clickhouse_via_explicit_env(monkeypatch):
    monkeypatch.setenv("CONTEXT_PERMANENT_BACKEND", "clickhouse")
    assert resolve_permanent_backend_kind() == "clickhouse"


def test_resolve_postgres_aliases(monkeypatch):
    for value in ("postgres", "postgresql", "pg"):
        monkeypatch.setenv("CONTEXT_PERMANENT_BACKEND", value)
        assert resolve_permanent_backend_kind() == "postgres"


def test_resolve_clickhouse_legacy_env(monkeypatch):
    monkeypatch.setenv("CLICKHOUSE_ENABLED", "true")
    assert resolve_permanent_backend_kind() == "clickhouse"


def test_explicit_backend_overrides_legacy_clickhouse(monkeypatch):
    monkeypatch.setenv("CLICKHOUSE_ENABLED", "true")
    monkeypatch.setenv("CONTEXT_PERMANENT_BACKEND", "postgres")
    assert resolve_permanent_backend_kind() == "postgres"


def test_resolve_none_explicit_values(monkeypatch):
    for value in ("none", "off", "false", "disabled"):
        monkeypatch.setenv("CONTEXT_PERMANENT_BACKEND", value)
        assert resolve_permanent_backend_kind() == "none"


def test_unknown_backend_disables_dual_write(monkeypatch):
    monkeypatch.setenv("CONTEXT_PERMANENT_BACKEND", "mysql")
    assert resolve_permanent_backend_kind() == "none"
