# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""LLM adapter for prompt/agent hook execution.

By default wraps the agent's main ``llm_client``. Hook calls share inference quota,
latency, and billing unless Host injects ``hook_api_client`` on HookPlugin options.
See ``docs/developer/DOMAIN_AGENT/HOOKS.md`` (Prompt/agent hooks and LLM client).
"""

from __future__ import annotations

from typing import Any

from aiecs.domain.agent.plugins.hooks.executor import SupportsHookPrompt
from aiecs.llm.clients.base_client import LLMMessage


class AgentLLMHookPromptClient:
    """Adapts an agent ``llm_client`` to ``SupportsHookPrompt``."""

    def __init__(
        self,
        llm_client: Any,
        *,
        default_model: str = "",
        llm_call_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._default_model = default_model
        self._llm_call_kwargs = llm_call_kwargs or {}

    async def complete_hook_prompt(
        self,
        *,
        prompt: str,
        model: str | None,
        max_tokens: int,
    ) -> str:
        response = await self._llm_client.generate_text(
            messages=[LLMMessage(role="user", content=prompt)],
            model=model or self._default_model or None,
            max_tokens=max_tokens,
            temperature=0.0,
            **self._llm_call_kwargs,
        )
        if isinstance(response, str):
            return response
        content = getattr(response, "content", None)
        if content is not None:
            return str(content)
        return str(response)


def resolve_hook_prompt_client(
    agent: Any,
    *,
    default_model: str = "",
    explicit_client: SupportsHookPrompt | None = None,
) -> SupportsHookPrompt | None:
    """Resolve prompt/agent hook LLM client from plugin options or the agent."""
    if explicit_client is not None:
        return explicit_client

    llm_client = getattr(agent, "llm_client", None) or getattr(agent, "_llm_client", None)
    if llm_client is None or not callable(getattr(llm_client, "generate_text", None)):
        return None

    config = getattr(agent, "_config", None) or getattr(agent, "config", None)
    extra: dict[str, Any] = {}
    agent_model = ""
    if config is not None:
        if hasattr(config, "get_llm_call_kwargs"):
            extra = dict(config.get_llm_call_kwargs())
        llm_model = getattr(config, "llm_model", None)
        if llm_model:
            agent_model = str(llm_model)

    return AgentLLMHookPromptClient(
        llm_client,
        default_model=default_model or agent_model,
        llm_call_kwargs=extra,
    )
