# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Optional strict validation of :class:`PluginConfig` options against manifest schema (§9.1).
"""

from __future__ import annotations

from typing import Any

from aiecs.domain.agent.plugins.errors import raise_plugin_config_error
from aiecs.domain.agent.plugins.models import PluginConfig

_JSON_TYPE_CHECKS: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def validate_options_against_schema(
    options: dict[str, Any],
    options_schema: dict[str, Any] | None,
    *,
    strict: bool = False,
    plugin_id: str | None = None,
) -> None:
    """
    Validate ``options`` against a JSON-Schema-like ``options_schema``.

    When ``strict`` is True, unknown option keys are rejected. When False, only
    declared properties are type-checked; extra keys are allowed.
    """
    if not options_schema:
        return

    schema_type = options_schema.get("type")
    if schema_type not in (None, "object"):
        raise_plugin_config_error(
            f"options_schema type must be 'object', got {schema_type!r}",
            plugin_id=plugin_id,
        )

    properties = options_schema.get("properties")
    if properties is not None and not isinstance(properties, dict):
        raise_plugin_config_error(
            "options_schema.properties must be an object",
            plugin_id=plugin_id,
        )

    required = options_schema.get("required", [])
    if required and not isinstance(required, list):
        raise_plugin_config_error(
            "options_schema.required must be a list",
            plugin_id=plugin_id,
        )

    props: dict[str, Any] = properties if isinstance(properties, dict) else {}

    for key in required:
        if key not in options:
            raise_plugin_config_error(
                f"missing required option: {key}",
                plugin_id=plugin_id,
                details={"field": key},
            )

    for key, value in options.items():
        if key not in props:
            if strict:
                raise_plugin_config_error(
                    f"unknown option key: {key}",
                    plugin_id=plugin_id,
                    details={"field": key},
                )
            continue

        prop_schema = props[key]
        if not isinstance(prop_schema, dict):
            continue

        expected_type = prop_schema.get("type")
        if expected_type is None:
            continue

        allowed = _JSON_TYPE_CHECKS.get(str(expected_type))
        if allowed is None:
            raise_plugin_config_error(
                f"unsupported options_schema type for '{key}': {expected_type!r}",
                plugin_id=plugin_id,
                details={"field": key},
            )

        if not isinstance(value, allowed):
            raise_plugin_config_error(
                f"option '{key}' expected type {expected_type}, got {type(value).__name__}",
                plugin_id=plugin_id,
                details={"field": key, "expected_type": expected_type},
            )


def validate_plugin_config_options(
    config: PluginConfig,
    options_schema: dict[str, Any] | None,
    *,
    strict: bool = False,
) -> None:
    """Validate :class:`PluginConfig.options` against a manifest ``options_schema``."""
    validate_options_against_schema(
        config.options,
        options_schema,
        strict=strict,
        plugin_id=config.name,
    )
