"""Tests for temporal memory group_id resolution."""

from __future__ import annotations

from aiecs.config.config import Settings
from aiecs.domain.temporal_memory.group_id import build_group_ids


def test_build_group_ids_session_only() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="aiecs")
    ids = build_group_ids("agent-1", "sess-42", settings=settings)
    assert ids == ["aiecs:agent-1:sess-42"]


def test_build_group_ids_with_tenant() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="aiecs")
    ids = build_group_ids("agent-1", "sess-42", "tenant-9", settings=settings)
    assert ids == ["aiecs:agent-1:sess-42", "aiecs:tenant:tenant-9"]


def test_build_group_ids_empty_tenant_omits_tenant_scope() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="aiecs")
    ids = build_group_ids("agent-1", "sess-42", None, settings=settings)
    assert len(ids) == 1
    assert "tenant" not in ids[0]


def test_build_group_ids_sanitizes_unsafe_characters() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="aiecs")
    ids = build_group_ids("agent@1", "sess space", settings=settings)
    assert ids[0] == "aiecs:agent_1:sess_space"
