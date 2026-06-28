"""
F3 CompressionPolicyResolver tests.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.context.compression.metadata import LAYER_L2, LAYER_L3
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.policy_resolver import resolve_layer_compression_policy


@pytest.mark.unit
class TestCompressionPolicyResolver:
    @pytest.mark.asyncio
    async def test_no_resolver_returns_base(self) -> None:
        config = AgentConfiguration(agent_id="a1", enable_context_compression=True)
        base = CompressionPolicy(enabled=True, chain=("microcompact", "llm"))
        resolved = await resolve_layer_compression_policy(
            LAYER_L3,
            context={},
            config=config,
            base_policy=base,
        )
        assert resolved.chain == base.chain

    @pytest.mark.asyncio
    async def test_context_resolver_l2_llm_only(self) -> None:
        config = AgentConfiguration(agent_id="a1")

        def resolver(*, layer: str, context, base_policy: CompressionPolicy) -> CompressionPolicy:
            if layer == LAYER_L2:
                return replace(base_policy, chain=("llm",))
            return base_policy

        base = CompressionPolicy(enabled=True, chain=("microcompact", "llm", "collapse"))
        resolved_l2 = await resolve_layer_compression_policy(
            LAYER_L2,
            context={"compression_policy_resolver": resolver},
            config=config,
            base_policy=base,
        )
        resolved_l3 = await resolve_layer_compression_policy(
            LAYER_L3,
            context={"compression_policy_resolver": resolver},
            config=config,
            base_policy=base,
        )
        assert resolved_l2.chain == ("llm",)
        assert resolved_l3.chain == ("microcompact", "llm", "collapse")

    @pytest.mark.asyncio
    async def test_config_resolver(self) -> None:
        def resolver(*, layer: str, context, base_policy: CompressionPolicy) -> CompressionPolicy:
            if layer == LAYER_L3:
                return replace(base_policy, chain=("llm",))
            return base_policy

        config = AgentConfiguration(
            agent_id="a1",
            compression_policy_resolver=resolver,
        )
        base = CompressionPolicy(enabled=True, chain=("microcompact", "llm"))
        resolved = await resolve_layer_compression_policy(
            LAYER_L3,
            context={},
            config=config,
            base_policy=base,
        )
        assert resolved.chain == ("llm",)
