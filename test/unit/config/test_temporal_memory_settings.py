"""Tests for L1 temporal memory Settings (TM_*)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aiecs.config.config import Settings
from aiecs.infrastructure.temporal_memory import (
    NoOpTemporalMemoryStore,
    create_temporal_memory_store,
    resolve_temporal_memory_backend,
)


def test_tm_defaults() -> None:
    settings = Settings()
    assert settings.tm_enabled is False
    assert settings.tm_backend == "none"
    assert settings.tm_graph_backend == "falkordb"
    assert settings.tm_search_limit == 10
    assert settings.tm_group_id_prefix == "aiecs"


def test_tm_enabled_graphiti_backend() -> None:
    settings = Settings(TM_ENABLED=True, TM_BACKEND="graphiti")
    assert settings.tm_enabled is True
    assert settings.tm_backend == "graphiti"
    assert resolve_temporal_memory_backend(settings) == "graphiti"


def test_tm_backend_normalized_to_lowercase() -> None:
    settings = Settings(TM_BACKEND="Graphiti", TM_ENABLED=True)
    assert settings.tm_backend == "graphiti"


def test_tm_invalid_backend_raises() -> None:
    with pytest.raises(ValidationError):
        Settings(TM_BACKEND="invalid")


def test_tm_postgres_requires_enabled() -> None:
    with pytest.raises(ValidationError, match="postgres requires TM_ENABLED"):
        Settings(TM_BACKEND="postgres", TM_ENABLED=False)


def test_tm_postgres_allowed_when_enabled() -> None:
    settings = Settings(TM_BACKEND="postgres", TM_ENABLED=True)
    assert settings.tm_backend == "postgres"
    store = create_temporal_memory_store(settings)
    assert isinstance(store, NoOpTemporalMemoryStore)


def test_tm_disabled_forces_none_backend_resolution() -> None:
    settings = Settings(TM_ENABLED=False, TM_BACKEND="graphiti")
    assert resolve_temporal_memory_backend(settings) == "none"
    assert isinstance(create_temporal_memory_store(settings), NoOpTemporalMemoryStore)


def test_tm_invalid_graph_backend_raises() -> None:
    with pytest.raises(ValidationError):
        Settings(TM_GRAPH_BACKEND="mysql")
