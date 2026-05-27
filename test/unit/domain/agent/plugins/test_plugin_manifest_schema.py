"""
Unit tests for plugin manifest schema (§9.1, P3-05).
"""

from __future__ import annotations

import json

import pytest
import yaml
from pydantic import ValidationError

from aiecs.domain.agent.plugins.errors import PluginConfigErrorException
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.schema import (
    DependencyRef,
    PluginManifest,
    parse_manifest_dict,
    parse_manifest_json,
    parse_manifest_yaml,
    validate_options_against_schema,
    validate_plugin_config_options,
)

_VALID_YAML = """
name: audit-plugin
version: "1.0.0"
description: Audit trail plugin for agent tasks
dependencies:
  - memory@builtin
  - name: tool@builtin
    version_constraint: ">=1.0"
phases:
  - pre_task
  - post_task
options_schema:
  type: object
  properties:
    log_level:
      type: string
    max_entries:
      type: integer
  required:
    - log_level
future_field: ignored
"""

_VALID_JSON = json.dumps(
    {
        "name": "fmt-plugin",
        "version": "0.2.0",
        "dependencies": ["skill@builtin"],
        "phases": ["build_messages"],
    }
)


@pytest.mark.unit
class TestDependencyRef:
    def test_from_string(self) -> None:
        ref = DependencyRef.from_value("memory@builtin")
        assert ref.name == "memory@builtin"
        assert ref.version_constraint is None

    def test_from_object(self) -> None:
        ref = DependencyRef.from_value({"name": "tool@registry", "version_constraint": "^2"})
        assert ref.name == "tool@registry"
        assert ref.version_constraint == "^2"

    def test_rejects_unknown_nested_fields(self) -> None:
        with pytest.raises(ValidationError):
            DependencyRef.model_validate({"name": "x", "extra": True})


@pytest.mark.unit
class TestPluginManifestParsing:
    def test_parse_valid_yaml(self) -> None:
        manifest = parse_manifest_yaml(_VALID_YAML)
        assert manifest.name == "audit-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == "Audit trail plugin for agent tasks"
        assert [dep.name for dep in manifest.dependencies] == [
            "memory@builtin",
            "tool@builtin",
        ]
        assert manifest.dependencies[1].version_constraint == ">=1.0"
        assert manifest.phases == [PluginPhase.PRE_TASK, PluginPhase.POST_TASK]
        assert manifest.options_schema is not None
        assert "log_level" in manifest.options_schema["properties"]

    def test_parse_valid_json(self) -> None:
        manifest = parse_manifest_json(_VALID_JSON)
        assert manifest.name == "fmt-plugin"
        assert manifest.version == "0.2.0"
        assert manifest.dependencies == [DependencyRef(name="skill@builtin")]
        assert manifest.phases == [PluginPhase.BUILD_MESSAGES]

    def test_parse_dict_strips_unknown_top_level_fields(self) -> None:
        manifest = parse_manifest_dict(
            {
                "name": "sample",
                "author": "should be stripped",
                "commands": ["/foo"],
            }
        )
        assert manifest.name == "sample"
        assert not hasattr(manifest, "author")
        assert "author" not in manifest.model_dump()

    def test_minimal_manifest(self) -> None:
        manifest = parse_manifest_dict({"name": "minimal"})
        assert manifest.name == "minimal"
        assert manifest.dependencies == []
        assert manifest.phases == []
        assert manifest.options_schema is None

    def test_rejects_missing_name(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            parse_manifest_dict({"version": "1.0.0"})
        assert "name" in str(exc_info.value).lower()

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            parse_manifest_dict({"name": "   "})

    def test_rejects_invalid_phase(self) -> None:
        with pytest.raises(ValidationError):
            parse_manifest_dict({"name": "bad-phases", "phases": ["not_a_phase"]})

    def test_rejects_invalid_dependencies_type(self) -> None:
        with pytest.raises(ValidationError):
            parse_manifest_dict({"name": "bad-deps", "dependencies": "memory@builtin"})

    def test_rejects_non_mapping_yaml_root(self) -> None:
        with pytest.raises(ValueError, match="mapping"):
            parse_manifest_yaml("- just a list")

    def test_rejects_non_mapping_json_root(self) -> None:
        with pytest.raises(ValueError, match="mapping"):
            parse_manifest_json('["not", "a", "dict"]')


@pytest.mark.unit
class TestOptionsSchemaValidation:
    _SCHEMA = {
        "type": "object",
        "properties": {
            "log_level": {"type": "string"},
            "max_entries": {"type": "integer"},
        },
        "required": ["log_level"],
    }

    def test_valid_options_pass(self) -> None:
        validate_options_against_schema(
            {"log_level": "info", "max_entries": 10},
            self._SCHEMA,
        )

    def test_missing_required_raises(self) -> None:
        with pytest.raises(PluginConfigErrorException, match="missing required option"):
            validate_options_against_schema({}, self._SCHEMA, plugin_id="audit-plugin")

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(PluginConfigErrorException, match="expected type integer"):
            validate_options_against_schema(
                {"log_level": "info", "max_entries": "ten"},
                self._SCHEMA,
            )

    def test_strict_rejects_unknown_keys(self) -> None:
        with pytest.raises(PluginConfigErrorException, match="unknown option key"):
            validate_options_against_schema(
                {"log_level": "info", "extra": True},
                self._SCHEMA,
                strict=True,
            )

    def test_non_strict_allows_unknown_keys(self) -> None:
        validate_options_against_schema(
            {"log_level": "info", "extra": True},
            self._SCHEMA,
            strict=False,
        )

    def test_none_schema_is_noop(self) -> None:
        validate_options_against_schema({"anything": 1}, None)

    def test_manifest_validate_options(self) -> None:
        manifest = parse_manifest_yaml(_VALID_YAML)
        manifest.validate_options({"log_level": "debug"})
        with pytest.raises(PluginConfigErrorException):
            manifest.validate_options({}, strict=True)

    def test_validate_plugin_config_options(self) -> None:
        manifest = parse_manifest_yaml(_VALID_YAML)
        config = PluginConfig(name="audit-plugin", options={"log_level": "warn"})
        manifest.validate_plugin_config(config)
        validate_plugin_config_options(config, manifest.options_schema)

    def test_validate_plugin_config_name_mismatch(self) -> None:
        manifest = parse_manifest_yaml(_VALID_YAML)
        config = PluginConfig(name="other-plugin", options={"log_level": "warn"})
        with pytest.raises(ValueError, match="does not match manifest"):
            manifest.validate_plugin_config(config)


@pytest.mark.unit
class TestManifestRoundTrip:
    def test_model_dump_matches_parsed_yaml(self) -> None:
        manifest = parse_manifest_yaml(_VALID_YAML)
        dumped = yaml.safe_load(
            yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False)
        )
        reparsed = parse_manifest_dict(dumped)
        assert reparsed.name == manifest.name
        assert reparsed.dependencies == manifest.dependencies
        assert reparsed.phases == manifest.phases
