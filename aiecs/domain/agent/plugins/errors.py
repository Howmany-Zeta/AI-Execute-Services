# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Typed plugin errors (§9.5).

Pydantic models carry discriminated ``type`` fields for metrics and streaming.
Use :class:`PluginErrorException` to raise typed errors from control-flow paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NoReturn

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.models import PluginPhase


class PluginError(BaseModel):
    """Base plugin error record."""

    type: str
    plugin_id: str | None = None
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class PluginInitError(PluginError):
    """Plugin failed during initialization."""

    type: Literal["plugin_init_error"] = "plugin_init_error"


class PluginConfigError(PluginError):
    """Invalid plugin configuration or identifier."""

    type: Literal["plugin_config_error"] = "plugin_config_error"


class PluginHookError(PluginError):
    """Plugin hook execution failed."""

    type: Literal["plugin_hook_error"] = "plugin_hook_error"
    phase: PluginPhase

    @field_validator("phase", mode="before")
    @classmethod
    def _coerce_phase(cls, value: Any) -> PluginPhase:
        from aiecs.domain.agent.plugins.models import PluginPhase as Phase

        if isinstance(value, Phase):
            return value
        return Phase(value)


class PluginDependencyError(PluginError):
    """Plugin dependency could not be resolved."""

    type: Literal["plugin_dependency_error"] = "plugin_dependency_error"


class PluginReloadError(PluginError):
    """Plugin reload rejected (e.g. agent busy or task in flight, §9.7)."""

    type: Literal["plugin_reload_error"] = "plugin_reload_error"


class PluginErrorException(Exception):
    """
    Control-flow exception wrapping a typed :class:`PluginError` record.

    ``raise PluginConfigError(...)`` in call sites refers to raising this
    exception via :func:`raise_plugin_config_error` or the subclass helpers below.
    """

    def __init__(self, error: PluginError) -> None:
        self.error = error
        super().__init__(get_plugin_error_message(error))


class PluginConfigErrorException(PluginErrorException):
    """Raised when plugin configuration or ID parsing fails."""

    def __init__(
        self,
        message: str,
        plugin_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            PluginConfigError(
                message=message,
                plugin_id=plugin_id,
                details=details or {},
            )
        )


class PluginReloadErrorException(PluginErrorException):
    """Raised when ``reload_plugins()`` is not allowed (§8.1, §9.7)."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            PluginReloadError(
                message=message,
                details=details or {},
            )
        )


class PluginDependencyErrorException(PluginErrorException):
    """Raised when a manifest dependency cannot be resolved."""

    def __init__(
        self,
        message: str,
        plugin_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            PluginDependencyError(
                message=message,
                plugin_id=plugin_id,
                details=details or {},
            )
        )


def raise_plugin_config_error(
    message: str,
    plugin_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> NoReturn:
    """Raise :class:`PluginConfigErrorException` with a typed error payload."""
    raise PluginConfigErrorException(message=message, plugin_id=plugin_id, details=details)


def raise_plugin_reload_error(
    message: str,
    details: dict[str, Any] | None = None,
) -> NoReturn:
    """Raise :class:`PluginReloadErrorException` when reload is rejected."""
    raise PluginReloadErrorException(message=message, details=details)


def raise_plugin_dependency_error(
    message: str,
    plugin_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> NoReturn:
    """Raise :class:`PluginDependencyErrorException` for unresolved manifest dependencies."""
    raise PluginDependencyErrorException(
        message=message,
        plugin_id=plugin_id,
        details=details,
    )


def get_plugin_error_message(error: PluginError) -> str:
    """Human-readable message for logs and UI (§9.5)."""
    parts: list[str] = [error.message]
    if error.plugin_id:
        parts.append(f"plugin_id={error.plugin_id}")
    if error.type:
        parts.append(f"type={error.type}")
    return " | ".join(parts)
