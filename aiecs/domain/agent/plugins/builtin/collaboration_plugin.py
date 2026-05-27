# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
CollaborationPlugin — peer registry context injection (§4.3, E-08).

``AGENT_INIT`` writes ``plugin_state["collaboration.peers"]`` from ``agent_registry`` or
plugin options. ``BUILD_MESSAGES`` may append an optional system hint when collaboration
is enabled.

This plugin does **not** implement ``delegate_task``, cross-agent RPC, or orchestration.
Multi-agent scheduling belongs in ``aiecs.domain.community.community_integration``.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.identifier import format_plugin_id
from aiecs.domain.agent.plugins.models import PluginMetadata
from aiecs.llm import LLMMessage

logger = logging.getLogger(__name__)

PLUGIN_STATE_PEERS_KEY = "collaboration.peers"
COLLABORATION_SYSTEM_MESSAGE_PREFIX = "Available collaborating agents:\n"
PLUGIN_ID = format_plugin_id("collaboration", "builtin")


def resolve_collaboration_peers(agent: Any, options: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build a serializable peer list from plugin options or ``agent._agent_registry``.

    Options may supply an explicit ``peers`` list; otherwise registry keys become
    ``agent_id`` entries with ``name`` and ``capabilities`` when present on the peer agent.
    """
    explicit = options.get("peers")
    if isinstance(explicit, list):
        peers = [_normalize_peer_entry(entry) for entry in explicit if isinstance(entry, dict)]
        return sorted(peers, key=lambda peer: peer["agent_id"])

    registry = getattr(agent, "_agent_registry", None) or {}
    self_id = getattr(agent, "agent_id", None)
    registry_peers: list[dict[str, Any]] = []
    for peer_id, peer_agent in registry.items():
        if peer_id == self_id:
            continue
        registry_peers.append(
            {
                "agent_id": str(peer_id),
                "name": str(getattr(peer_agent, "name", peer_id)),
                "capabilities": _normalize_capabilities(getattr(peer_agent, "capabilities", None)),
            }
        )
    return sorted(registry_peers, key=lambda peer: peer["agent_id"])


def _normalize_capabilities(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw]
    return [str(raw)]


def _normalize_peer_entry(entry: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(entry.get("agent_id") or entry.get("id") or "")
    return {
        "agent_id": agent_id,
        "name": str(entry.get("name") or agent_id),
        "capabilities": _normalize_capabilities(entry.get("capabilities")),
    }


def format_collaboration_system_hint(peers: list[dict[str, Any]]) -> str:
    """Format BUILD_MESSAGES system hint for available collaborating agents."""
    lines: list[str] = []
    for peer in peers:
        caps = peer.get("capabilities") or []
        caps_suffix = f" (capabilities: {', '.join(caps)})" if caps else ""
        lines.append(f"- {peer['agent_id']}: {peer['name']}{caps_suffix}")
    return COLLABORATION_SYSTEM_MESSAGE_PREFIX + "\n".join(lines)


def _collaboration_active(agent: Any) -> bool:
    return bool(getattr(agent, "_collaboration_enabled", False))


class CollaborationPlugin(BaseAgentPlugin):
    """Builtin collaboration plugin: peer registry context only (no orchestration)."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="collaboration",
        version="1.0.0",
        description="Collaboration peer registry context plugin",
        priority=80,
        default_enabled=False,
    )

    def __init__(self, config, agent) -> None:
        super().__init__(config, agent)
        self._peers: list[dict[str, Any]] = []

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        if not _collaboration_active(self._agent):
            self._peers = []
            return None

        self._peers = resolve_collaboration_peers(self._agent, dict(self._config.options))
        ctx.plugin_state[PLUGIN_STATE_PEERS_KEY] = list(self._peers)
        logger.debug(
            "CollaborationPlugin registered %s peer(s) for agent %s",
            len(self._peers),
            getattr(self._agent, "agent_id", "?"),
        )
        return None

    async def on_build_messages(
        self,
        ctx: AgentPluginContext,
        messages: list[LLMMessage],
    ) -> list[LLMMessage]:
        if not _collaboration_active(self._agent):
            return messages

        inject_hint = self._config.options.get("inject_system_hint", True)
        if not inject_hint:
            return messages

        peers = self._peers or resolve_collaboration_peers(self._agent, dict(self._config.options))
        if not peers:
            return messages

        ctx.plugin_state[PLUGIN_STATE_PEERS_KEY] = list(peers)
        return [
            *messages,
            LLMMessage(
                role="system",
                content=format_collaboration_system_hint(peers),
            ),
        ]

    async def on_agent_shutdown(self, ctx: AgentPluginContext) -> None:
        self._peers = []
        return None
