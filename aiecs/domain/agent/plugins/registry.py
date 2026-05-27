# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Plugin registry for agent plugin factories (§5.5, §6.3.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Type

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.errors import (
    PluginErrorException,
    PluginInitError,
    raise_plugin_config_error,
)
from aiecs.domain.agent.plugins.identifier import (
    PluginIdentifier,
    PluginOrigin,
    format_plugin_id,
)
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata
from aiecs.domain.agent.plugins.schema.manifest import PluginManifest

if TYPE_CHECKING:
    from aiecs.domain.agent.base_agent import BaseAIAgent


@dataclass(frozen=True)
class RegistryEntry:
    """Registered plugin factory and metadata."""

    factory: Type[BaseAgentPlugin]
    metadata: PluginMetadata
    origin: PluginOrigin
    manifest: PluginManifest | None = None


class PluginRegistry:
    """
    In-process plugin factory registry.

    ``register()`` records factories only; it does **not** enable plugins.
    Loading is driven by ``derive_plugin_configs()`` and ``PluginManager`` (§6.3.5).

    Duplicate ``register()`` calls for the same short ``name`` overwrite the prior entry.
    """

    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}

    @classmethod
    def default(cls) -> PluginRegistry:
        """
        Registry with builtin Skill, Memory, and Tool plugins (§9.8).

        Builtin entries use ``origin="builtin"`` and ``metadata.default_enabled=True``.
        Registration does not enable plugins; see ``derive_plugin_configs()`` (§6.3.5).
        """
        from aiecs.domain.agent.plugins.builtin import (
            CollaborationPlugin,
            KnowledgePlugin,
            MemoryPlugin,
            SkillPlugin,
            ToolPlugin,
        )

        registry = cls()
        for plugin_class in (SkillPlugin, MemoryPlugin, ToolPlugin):
            class_metadata = plugin_class.metadata
            registry.register(
                class_metadata.name,
                plugin_class,
                metadata=PluginMetadata(
                    name=class_metadata.name,
                    version=class_metadata.version,
                    description=class_metadata.description,
                    priority=class_metadata.priority,
                    default_enabled=True,
                ),
                origin=PluginOrigin.BUILTIN,
            )

        knowledge_metadata = KnowledgePlugin.metadata
        registry.register(
            knowledge_metadata.name,
            KnowledgePlugin,
            metadata=PluginMetadata(
                name=knowledge_metadata.name,
                version=knowledge_metadata.version,
                description=knowledge_metadata.description,
                priority=knowledge_metadata.priority,
                default_enabled=False,
            ),
            origin=PluginOrigin.BUILTIN,
        )

        collaboration_metadata = CollaborationPlugin.metadata
        registry.register(
            collaboration_metadata.name,
            CollaborationPlugin,
            metadata=PluginMetadata(
                name=collaboration_metadata.name,
                version=collaboration_metadata.version,
                description=collaboration_metadata.description,
                priority=collaboration_metadata.priority,
                default_enabled=False,
            ),
            origin=PluginOrigin.BUILTIN,
        )
        return registry

    def register(
        self,
        name: str,
        plugin_class: Type[BaseAgentPlugin],
        metadata: PluginMetadata | None = None,
        origin: str | PluginOrigin = PluginOrigin.REGISTRY,
    ) -> None:
        """
        Register a plugin class under a short name.

        Args:
            name: Registry key and expected ``PluginConfig.name``.
            plugin_class: ``BaseAgentPlugin`` subclass; constructed as ``plugin_class(config, agent)``.
            metadata: Optional override; defaults to ``plugin_class.metadata``.
            origin: Registration source for ``plugin_id`` formatting (default ``registry``).

        Note:
            Re-registering the same ``name`` overwrites the previous entry.
        """
        origin_value = _coerce_origin(origin)
        resolved_metadata = metadata or getattr(plugin_class, "metadata", None)
        if not isinstance(resolved_metadata, PluginMetadata):
            raise_plugin_config_error(
                f"plugin class {plugin_class.__name__!r} has no metadata",
                plugin_id=format_plugin_id(name, origin_value),
            )

        self._entries[name] = RegistryEntry(
            factory=plugin_class,
            metadata=resolved_metadata,
            origin=origin_value,
        )

    def register_from_manifest(
        self,
        manifest: PluginManifest,
        plugin_class: Type[BaseAgentPlugin],
        *,
        origin: str | PluginOrigin = PluginOrigin.CONFIG,
    ) -> None:
        """
        Register a plugin from an external manifest (§6.3.5, §9.1).

        Manifest-registered plugins use ``default_enabled=False``; they are loaded
        only when explicitly enabled in ``AgentConfiguration.plugins`` or task/context.
        """
        origin_value = _coerce_origin(origin)
        class_metadata = getattr(plugin_class, "metadata", None)
        if not isinstance(class_metadata, PluginMetadata):
            raise_plugin_config_error(
                f"plugin class {plugin_class.__name__!r} has no metadata",
                plugin_id=format_plugin_id(manifest.name, origin_value),
            )

        metadata = PluginMetadata(
            name=manifest.name,
            version=manifest.version or class_metadata.version,
            description=manifest.description or class_metadata.description,
            priority=class_metadata.priority,
            default_enabled=False,
        )
        self._entries[manifest.name] = RegistryEntry(
            factory=plugin_class,
            metadata=metadata,
            origin=origin_value,
            manifest=manifest,
        )

    def get_manifest(self, name: str) -> PluginManifest | None:
        """Return the manifest attached to a registered plugin, if any."""
        entry = self._entries.get(name)
        return entry.manifest if entry is not None else None

    def get_entry(self, name: str) -> RegistryEntry | None:
        """Return the registry entry for a short plugin name, if registered."""
        return self._entries.get(name)

    def create(self, config: PluginConfig, agent: BaseAIAgent) -> BaseAgentPlugin:
        """
        Instantiate a plugin from a resolved ``PluginConfig``.

        Raises:
            PluginConfigErrorException: Unknown plugin name.
            PluginErrorException: Construction failed (wraps :class:`PluginInitError`).
        """
        if config.name not in self._entries:
            raise_plugin_config_error(
                f"unknown plugin name: {config.name!r}",
                plugin_id=format_plugin_id(config.name, PluginOrigin.REGISTRY),
            )

        entry = self._entries[config.name]
        plugin_id = format_plugin_id(config.name, entry.origin)
        try:
            return entry.factory(config, agent)
        except Exception as exc:
            raise PluginErrorException(
                PluginInitError(
                    message=f"failed to create plugin {config.name!r}: {exc}",
                    plugin_id=plugin_id,
                    details={"error_type": type(exc).__name__},
                )
            ) from exc

    def list_registered(self) -> list[PluginIdentifier]:
        """Return registered plugins as ``PluginIdentifier`` (sorted by name)."""
        return [PluginIdentifier(name=name, origin=entry.origin) for name, entry in sorted(self._entries.items())]


def _coerce_origin(origin: str | PluginOrigin) -> PluginOrigin:
    if isinstance(origin, PluginOrigin):
        return origin
    return PluginOrigin(str(origin).strip())
