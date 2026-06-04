# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Minimal HybridAgent + temporal_memory plugin (L1).

Set TM_* env vars before run — see examples/temporal_memory/README.md.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, AsyncGenerator

from aiecs.domain.agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.llm import BaseLLMClient, LLMResponse


class _DemoLLMClient(BaseLLMClient):
    """Minimal concrete client for local wiring demos (no external API)."""

    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, *args: Any, **kwargs: Any) -> LLMResponse:
        _ = args, kwargs
        return LLMResponse(
            content="Demo response (temporal memory example).",
            provider="openai",
            model="demo",
            tokens_used=1,
        )

    def stream_text(self, *args: Any, **kwargs: Any) -> AsyncGenerator[str, None]:
        _ = args, kwargs

        async def _gen() -> AsyncGenerator[str, None]:
            yield "Demo response (temporal memory example)."

        return _gen()

    async def close(self) -> None:
        return None


async def main() -> None:
    tm_backend = os.environ.get("TM_BACKEND", "none")
    tm_enabled = os.environ.get("TM_ENABLED", "false").lower() in ("1", "true", "yes")
    print(f"TM_ENABLED={tm_enabled} TM_BACKEND={tm_backend}")

    config = AgentConfiguration(
        goal="Temporal memory minimal example",
        llm_model="demo",
        system_prompt="You are a helpful assistant.",
        memory_enabled=True,
        temporal_memory_enabled=True,
        plugins=[
            PluginConfig(name="memory", enabled=True),
            PluginConfig(
                name="temporal_memory",
                enabled=True,
                options={"inject_facts": True, "facts_limit": 5},
            ),
        ],
    )

    agent = HybridAgent(
        agent_id="temporal-memory-demo",
        name="Temporal Memory Demo",
        llm_client=_DemoLLMClient(),
        tools=[],
        config=config,
        max_iterations=1,
    )
    await agent.initialize()

    active = getattr(agent, "temporal_memory_enabled", False)
    has_engine = getattr(agent, "temporal_memory_engine", None) is not None
    print(f"temporal_memory_enabled={active} engine_wired={has_engine}")

    result = await agent.execute_task(
        {"description": "Remember: the launch window opens at 09:00 UTC."},
        {"session_id": "demo-session-1"},
    )
    print(f"execute_task success={result.get('success')} output={result.get('output')!r}")

    await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
