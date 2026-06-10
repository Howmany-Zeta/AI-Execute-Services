"""Tests for temporal memory group_id resolution."""

from __future__ import annotations

import re

import pytest

from aiecs.config.config import Settings
from aiecs.domain.temporal_memory.group_id import build_group_ids, is_graphiti_safe_group_id

_GRAPHITI_SAFE = re.compile(r"^[A-Za-z0-9_-]+$")


def test_build_group_ids_session_only() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="aiecs")
    ids = build_group_ids("agent-1", "sess-42", settings=settings)
    assert ids == ["aiecs_agent-1_sess-42"]


def test_build_group_ids_with_tenant() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="aiecs")
    ids = build_group_ids("agent-1", "sess-42", "tenant-9", settings=settings)
    assert ids == ["aiecs_agent-1_sess-42", "aiecs_tenant_tenant-9"]


def test_build_group_ids_empty_tenant_omits_tenant_scope() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="aiecs")
    ids = build_group_ids("agent-1", "sess-42", None, settings=settings)
    assert len(ids) == 1
    assert "tenant" not in ids[0]


def test_build_group_ids_sanitizes_unsafe_characters() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="aiecs")
    ids = build_group_ids("agent@1", "sess space", settings=settings)
    assert ids[0] == "aiecs_agent_1_sess_space"


def test_build_group_ids_graphiti_safe() -> None:
    settings = Settings(TM_GROUP_ID_PREFIX="middleware")
    ids = build_group_ids("master_controller", "session-1", "tenant-a", settings=settings)
    for group_id in ids:
        assert _GRAPHITI_SAFE.match(group_id)
        assert is_graphiti_safe_group_id(group_id)


def test_is_graphiti_safe_group_id_rejects_colons() -> None:
    assert not is_graphiti_safe_group_id("middleware:agent:session")
