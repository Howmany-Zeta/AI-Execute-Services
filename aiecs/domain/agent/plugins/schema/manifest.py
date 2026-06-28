# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
External plugin manifest schema (§9.1).

Loaded from ``aiecs-plugin.yaml`` / ``plugin.json`` in P3-06; this module provides
Pydantic models and parse helpers only.
"""

from __future__ import annotations

import json
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.schema.dependency import DependencyRef
from aiecs.domain.agent.plugins.schema.validation import (
    validate_options_against_schema,
    validate_plugin_config_options,
)

_MANIFEST_TOP_LEVEL_KEYS = frozenset(
    {
        "name",
        "version",
        "description",
        "dependencies",
        "phases",
        "options_schema",
        "hooks",
    }
)


class PluginManifest(BaseModel):
    """
    External plugin manifest (§9.1).

    Top-level unknown fields are silently stripped (Claude Code aligned). Nested
    dependency objects use strict validation via :class:`DependencyRef`.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    version: str | None = None
    description: str | None = None
    dependencies: list[DependencyRef] = Field(default_factory=list)
    phases: list[PluginPhase] = Field(default_factory=list)
    options_schema: dict[str, Any] | None = None
    hooks: str | dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def strip_unknown_top_level_fields(cls, data: Any) -> Any:
        """Silently drop unknown top-level manifest keys (§9.1)."""
        if not isinstance(data, dict):
            return data
        return {key: value for key, value in data.items() if key in _MANIFEST_TOP_LEVEL_KEYS}

    @field_validator("name")
    @classmethod
    def name_must_be_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("name must be non-empty")
        return value.strip()

    @field_validator("dependencies", mode="before")
    @classmethod
    def normalize_dependencies(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("dependencies must be a list")
        return [DependencyRef.from_value(item) for item in value]

    @field_validator("phases", mode="before")
    @classmethod
    def normalize_phases(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("phases must be a list")
        return value

    def validate_options(
        self,
        options: dict[str, Any],
        *,
        strict: bool = False,
    ) -> None:
        """Validate runtime options against this manifest's ``options_schema``."""
        validate_options_against_schema(
            options,
            self.options_schema,
            strict=strict,
            plugin_id=self.name,
        )

    def validate_plugin_config(
        self,
        config: PluginConfig,
        *,
        strict: bool = False,
    ) -> None:
        """Validate :class:`PluginConfig` name match and options schema."""
        if config.name != self.name:
            raise ValueError(f"PluginConfig name {config.name!r} does not match manifest {self.name!r}")
        validate_plugin_config_options(config, self.options_schema, strict=strict)


def parse_manifest_dict(data: dict[str, Any]) -> PluginManifest:
    """Parse a manifest mapping into :class:`PluginManifest`."""
    return PluginManifest.model_validate(data)


def parse_manifest_yaml(text: str) -> PluginManifest:
    """Parse manifest YAML text."""
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError("manifest YAML root must be a mapping")
    return parse_manifest_dict(loaded)


def parse_manifest_json(text: str) -> PluginManifest:
    """Parse manifest JSON text."""
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError("manifest JSON root must be a mapping")
    return parse_manifest_dict(loaded)
