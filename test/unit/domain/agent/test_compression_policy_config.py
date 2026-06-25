"""ADR-007 compression policy resolution tests."""

from __future__ import annotations

from aiecs.domain.agent.models import AgentConfiguration, resolve_compression_policy
from aiecs.domain.context.compression.constants import AUTOCOMPACT_BUFFER_TOKENS
from aiecs.domain.context.compression.policy import CompressionPolicy


def test_resolve_compression_policy_defaults_from_config() -> None:
    config = AgentConfiguration(
        enable_context_compression=True,
        context_window_limit=42_000,
    )
    policy = resolve_compression_policy(config)
    assert policy.enabled is True
    assert policy.context_window_tokens == 42_000
    assert policy.buffer_tokens == AUTOCOMPACT_BUFFER_TOKENS
    assert policy.preserve_recent == 12


def test_resolve_compression_policy_honours_disabled_flag() -> None:
    config = AgentConfiguration(enable_context_compression=False)
    policy = resolve_compression_policy(config)
    assert policy.enabled is False


def test_resolve_compression_policy_explicit_override() -> None:
    override = CompressionPolicy(
        enabled=True,
        context_window_tokens=100_000,
        preserve_recent=6,
        buffer_tokens=5_000,
    )
    config = AgentConfiguration(
        enable_context_compression=False,
        context_window_limit=10_000,
        compression_policy=override,
    )
    policy = resolve_compression_policy(config)
    assert policy is override
    assert policy.context_window_tokens == 100_000
    assert policy.preserve_recent == 6
