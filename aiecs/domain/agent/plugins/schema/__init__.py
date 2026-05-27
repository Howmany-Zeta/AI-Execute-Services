# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Pydantic schemas for external plugin manifests (§9.1, Phase 3).
"""

from aiecs.domain.agent.plugins.schema.dependency import DependencyRef
from aiecs.domain.agent.plugins.schema.manifest import (
    PluginManifest,
    parse_manifest_dict,
    parse_manifest_json,
    parse_manifest_yaml,
)
from aiecs.domain.agent.plugins.schema.validation import (
    validate_options_against_schema,
    validate_plugin_config_options,
)

__all__ = [
    "DependencyRef",
    "PluginManifest",
    "parse_manifest_dict",
    "parse_manifest_json",
    "parse_manifest_yaml",
    "validate_options_against_schema",
    "validate_plugin_config_options",
]
