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
from aiecs.infrastructure.temporal_memory.postgres.store import PostgresTemporalMemoryStore


def test_tm_defaults() -> None:
    settings = Settings()
    assert settings.tm_enabled is False
    assert settings.tm_backend == "none"
    assert settings.tm_graph_backend == "falkordb"
    assert settings.tm_search_limit == 10
    assert settings.tm_group_id_prefix == "aiecs"
    assert settings.tm_search_primary_group_only is False
    assert settings.tm_ingest_all_group_ids is False
    assert settings.tm_search_cache_enabled is True
    assert settings.tm_search_cache_ttl_seconds == 30.0
    assert settings.tm_search_cache_max_size == 256
    assert settings.tm_episode_body_max_chars == 4000


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


def test_tm_postgres_requires_dsn_when_enabled() -> None:
    with pytest.raises(ValidationError, match="TM_POSTGRES_URL or POSTGRES_URL"):
        Settings(TM_BACKEND="postgres", TM_ENABLED=True, TM_POSTGRES_URL="")


def test_tm_postgres_allowed_when_enabled_with_dsn() -> None:
    settings = Settings(
        TM_BACKEND="postgres",
        TM_ENABLED=True,
        TM_POSTGRES_URL="postgresql://user:pass@localhost/testdb",
    )
    assert settings.tm_backend == "postgres"
    assert resolve_temporal_memory_backend(settings) == "postgres"
    store = create_temporal_memory_store(settings)
    assert isinstance(store, PostgresTemporalMemoryStore)


def test_tm_postgres_falls_back_to_postgres_url() -> None:
    settings = Settings(
        TM_BACKEND="postgres",
        TM_ENABLED=True,
        TM_POSTGRES_URL="",
        POSTGRES_URL="postgresql://user:pass@localhost/appdb",
    )
    store = create_temporal_memory_store(settings)
    assert isinstance(store, PostgresTemporalMemoryStore)


def test_tm_disabled_forces_none_backend_resolution() -> None:
    settings = Settings(TM_ENABLED=False, TM_BACKEND="graphiti")
    assert resolve_temporal_memory_backend(settings) == "none"
    assert isinstance(create_temporal_memory_store(settings), NoOpTemporalMemoryStore)


def test_tm_invalid_graph_backend_raises() -> None:
    with pytest.raises(ValidationError):
        Settings(TM_GRAPH_BACKEND="mysql")
