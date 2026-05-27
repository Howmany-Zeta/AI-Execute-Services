# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Plugin dependency references for manifest files (§9.1).

``version_constraint`` is a placeholder for future semver / range resolution (P3-06+).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from aiecs.domain.agent.plugins.errors import raise_plugin_config_error


class DependencyRef(BaseModel):
    """Reference to another plugin required by a manifest."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version_constraint: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_be_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("dependency name must be non-empty")
        return value.strip()

    @classmethod
    def from_value(cls, value: str | dict[str, object]) -> DependencyRef:
        """Parse a dependency entry from manifest YAML/JSON."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(name=value.strip())
        if isinstance(value, dict):
            return cls.model_validate(value)
        raise_plugin_config_error(
            f"invalid dependency entry: expected str or object, got {type(value).__name__}",
            details={"value": repr(value)},
        )
