#!/usr/bin/env python3
"""CC-093: L3 compression E2E soak — large tool output stays under context window.

Run from repo root::

    poetry run python scripts/validate_l3_compression_e2e.py

Uses HybridAgent with mocked LLM/tools (no external API). Exit 0 = pass.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure repo root on path when invoked as script
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


async def _run_soak() -> None:
    from aiecs.domain.agent import AgentConfiguration, HybridAgent
    from aiecs.domain.context.compression.constants import TOOL_OUTPUT_TRUNCATED_HEADER
    from aiecs.domain.context.compression.tokens import estimate_message_tokens
    from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

    class SoakLLM(BaseLLMClient):
        def __init__(self) -> None:
            super().__init__(provider_name="openai")
            self.calls: list[list[LLMMessage]] = []

        async def generate_text(self, messages, **kwargs: Any) -> LLMResponse:
            self.calls.append(list(messages))
            if len(self.calls) == 1:
                resp = LLMResponse(
                    content="read",
                    provider="openai",
                    model="mock",
                    tokens_used=10,
                )
                setattr(
                    resp,
                    "tool_calls",
                    [
                        {
                            "id": "read_files_1",
                            "type": "function",
                            "function": {
                                "name": "read_files",
                                "arguments": '{"paths":["large.md"]}',
                            },
                        }
                    ],
                )
                return resp
            return LLMResponse(
                content="summary after large read",
                provider="openai",
                model="mock",
                tokens_used=10,
            )

        async def stream_text(self, *args: Any, **kwargs: Any):
            raise NotImplementedError

        async def close(self) -> None:
            return None

    mock_tool = MagicMock()
    mock_tool.name = "read_files"
    mock_tool.description = "read files"
    mock_tool._schemas = {"run": MagicMock()}
    mock_tool.run_async = AsyncMock(
        return_value=("file-content-" + "Z" * 50_000)
    )

    os.environ["AIECS_TOOL_OUTPUT_INLINE_CHARS"] = "4096"
    context_window = 20_000

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        config = AgentConfiguration(
            llm_model="mock",
            system_prompt="Soak",
            enable_context_compression=True,
            context_window_limit=context_window,
        )
        client = SoakLLM()
        agent = HybridAgent(
            agent_id="l3_soak",
            name="L3Soak",
            llm_client=client,
            tools=["read_files"],
            config=config,
            max_iterations=4,
        )
        await agent.initialize()
        result = await agent._tool_loop("read large file", {"session_id": "soak-1"})

    assert result.get("final_response"), "tool loop should complete"
    assert len(client.calls) >= 2, "expected tool call + follow-up LLM"

    second_call = client.calls[1]
    tool_msgs = [m for m in second_call if m.role == "tool"]
    assert tool_msgs, "tool result must be present"
    assert tool_msgs[0].content.startswith(TOOL_OUTPUT_TRUNCATED_HEADER)

    tokens = estimate_message_tokens(second_call)
    threshold = int(context_window * 0.95)
    assert tokens < threshold, (
        f"L3 soak failed: estimated tokens {tokens} >= {threshold} "
        f"(context_window={context_window})"
    )

    print(f"OK: L3 soak — tool output offloaded, pre-LLM tokens={tokens} < {threshold}")


def main() -> int:
    try:
        asyncio.run(_run_soak())
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
