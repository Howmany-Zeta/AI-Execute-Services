# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Plugin identifier parsing and formatting (name@origin, §9.2).
"""

from dataclasses import dataclass
from enum import Enum

from aiecs.domain.agent.plugins.errors import raise_plugin_config_error

_PLUGIN_ID_SEPARATOR = "@"


class PluginOrigin(str, Enum):
    """Source of a plugin registration."""

    BUILTIN = "builtin"
    CONFIG = "config"
    REGISTRY = "registry"
    SESSION = "session"


DEFAULT_PLUGIN_ORIGIN = PluginOrigin.REGISTRY


@dataclass(frozen=True)
class PluginIdentifier:
    """Parsed plugin ID: short name plus origin."""

    name: str
    origin: PluginOrigin = DEFAULT_PLUGIN_ORIGIN

    def format(self) -> str:
        """Return the canonical plugin ID string."""
        return format_plugin_id(self.name, self.origin)


def format_plugin_id(name: str, origin: PluginOrigin | str = DEFAULT_PLUGIN_ORIGIN) -> str:
    """
    Build a canonical plugin ID ``{name}@{origin}``.

    Args:
        name: Short plugin name (e.g. ``skill``).
        origin: Registration source; defaults to ``registry``.

    Returns:
        Formatted ID such as ``skill@builtin``.

    Raises:
        PluginConfigErrorException: If name or origin is empty or invalid.
    """
    if not name or not name.strip():
        raise_plugin_config_error("plugin name must be non-empty")
    origin_value = _coerce_origin(origin)
    return f"{name.strip()}{_PLUGIN_ID_SEPARATOR}{origin_value.value}"


def parse_plugin_identifier(plugin_id: str) -> PluginIdentifier:
    """
    Parse a short name or full ``name@origin`` plugin ID.

    Short names (no ``@``) default to origin ``registry``.

    Args:
        plugin_id: ``audit`` or ``skill@builtin``.

    Returns:
        Parsed :class:`PluginIdentifier`.

    Raises:
        PluginConfigErrorException: On malformed IDs or unknown origins.
    """
    if plugin_id is None or not str(plugin_id).strip():
        raise_plugin_config_error("plugin_id must be non-empty", plugin_id=str(plugin_id))

    value = str(plugin_id).strip()
    if _PLUGIN_ID_SEPARATOR not in value:
        return PluginIdentifier(name=_validate_name(value), origin=DEFAULT_PLUGIN_ORIGIN)

    if value.count(_PLUGIN_ID_SEPARATOR) != 1:
        raise_plugin_config_error(
            f"invalid plugin_id format: {plugin_id!r}",
            plugin_id=value,
        )

    name_part, origin_part = value.split(_PLUGIN_ID_SEPARATOR, 1)
    return PluginIdentifier(
        name=_validate_name(name_part, plugin_id=value),
        origin=_coerce_origin(origin_part, plugin_id=value),
    )


def _validate_name(name: str, plugin_id: str | None = None) -> str:
    if not name or not name.strip():
        raise_plugin_config_error("plugin name must be non-empty", plugin_id=plugin_id)
    return name.strip()


def _coerce_origin(origin: PluginOrigin | str, plugin_id: str | None = None) -> PluginOrigin:
    if isinstance(origin, PluginOrigin):
        return origin
    if not origin or not str(origin).strip():
        raise_plugin_config_error("plugin origin must be non-empty", plugin_id=plugin_id)
    origin_str = str(origin).strip()
    try:
        return PluginOrigin(origin_str)
    except ValueError:
        raise_plugin_config_error(
            f"unknown plugin origin: {origin_str!r}; " f"expected one of {[o.value for o in PluginOrigin]}",
            plugin_id=plugin_id,
        )
