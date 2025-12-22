"""
Unit tests for tool registry configuration loading integration.

Tests cover:
- Tool registration doesn't trigger config loading (lazy loading)
- Tool instantiation triggers config loading (via BaseTool)
- Config caching (only loads once per tool instance)
- Tool name resolution (correct tool name passed to loader)
- TOOL_CONFIGS dictionary integration
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from pydantic import BaseModel, Field

from aiecs.tools import register_tool, get_tool, TOOL_CONFIGS, TOOL_CLASSES, TOOL_REGISTRY
from aiecs.tools.base_tool import BaseTool
from aiecs.config.tool_config import get_tool_config_loader


class TestRegistryTool(BaseTool):
    """Test tool for registry testing"""

    class Config(BaseModel):
        timeout: int = Field(default=30)
        max_retries: int = Field(default=3)

    def test_operation(self, value: str):
        return f"Result: {value}"


class TestRegistryToolWithoutConfig(BaseTool):
    """Test tool without Config class"""

    def test_operation(self, value: str):
        return f"Result: {value}"


class TestToolRegistryLazyLoading:
    """Test lazy loading behavior"""

    def test_register_tool_does_not_trigger_config_loading(self):
        """Test that registering a tool doesn't trigger config loading"""
        # Clear registry
        test_tool_name = "test_lazy_tool"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]

        # Mock the loader to track calls
        with patch.object(get_tool_config_loader(), "load_tool_config") as mock_load:
            # Register tool
            @register_tool(test_tool_name)
            class TestLazyTool(BaseTool):
                class Config(BaseModel):
                    timeout: int = Field(default=30)

            # Config loading should not have been called
            mock_load.assert_not_called()
            # Tool class should be registered
            assert test_tool_name in TOOL_CLASSES
            # Tool should not be instantiated yet
            assert test_tool_name not in TOOL_REGISTRY or TOOL_REGISTRY[test_tool_name].is_placeholder

    def test_get_tool_triggers_config_loading(self):
        """Test that getting a tool triggers config loading"""
        # Clear registry
        test_tool_name = "test_get_tool"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]

        # Register tool
        @register_tool(test_tool_name)
        class TestGetTool(BaseTool):
            class Config(BaseModel):
                timeout: int = Field(default=30)

        # Mock the loader
        with patch.object(get_tool_config_loader(), "load_tool_config") as mock_load:
            mock_load.return_value = {"timeout": 45}

            # Get tool - should trigger config loading
            tool = get_tool(test_tool_name)

            # Config loading should have been called
            mock_load.assert_called_once()
            # Tool should be instantiated
            assert test_tool_name in TOOL_REGISTRY
            assert tool is not None

    def test_tool_instantiation_only_once(self):
        """Test that tool is only instantiated once (caching)"""
        # Clear registry
        test_tool_name = "test_cached_tool"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]

        # Register tool
        @register_tool(test_tool_name)
        class TestCachedTool(BaseTool):
            class Config(BaseModel):
                timeout: int = Field(default=30)

        # Mock the loader
        with patch.object(get_tool_config_loader(), "load_tool_config") as mock_load:
            mock_load.return_value = {"timeout": 45}

            # Get tool twice
            tool1 = get_tool(test_tool_name)
            tool2 = get_tool(test_tool_name)

            # Should be the same instance
            assert tool1 is tool2
            # Config loading should only be called once (during first get_tool)
            assert mock_load.call_count == 1


class TestToolRegistryNameResolution:
    """Test tool name resolution"""

    def test_tool_name_passed_to_loader(self):
        """Test that registered tool name is passed to loader"""
        # Clear registry
        test_tool_name = "custom_registered_name"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]

        # Register tool with custom name
        @register_tool(test_tool_name)
        class TestNamedTool(BaseTool):
            class Config(BaseModel):
                timeout: int = Field(default=30)

        # Mock the loader
        with patch.object(get_tool_config_loader(), "load_tool_config") as mock_load:
            mock_load.return_value = {"timeout": 45}

            # Get tool
            get_tool(test_tool_name)

            # Check that tool name was passed to loader
            call_args = mock_load.call_args
            assert call_args.kwargs["tool_name"] == test_tool_name

    def test_tool_name_used_for_yaml_discovery(self):
        """Test that tool name is used for YAML config file discovery"""
        test_tool_name = "test_yaml_tool"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]

        # Register tool
        @register_tool(test_tool_name)
        class TestYAMLTool(BaseTool):
            class Config(BaseModel):
                timeout: int = Field(default=30)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config" / "tools"
            config_dir.mkdir(parents=True)
            loader = get_tool_config_loader()
            loader.set_config_path(config_dir.parent)

            # Create YAML config file with tool name
            yaml_file = config_dir / f"{test_tool_name}.yaml"
            yaml_file.write_text("timeout: 60\nmax_retries: 5\n")

            # Get tool - should load from YAML
            tool = get_tool(test_tool_name)
            assert tool._config_obj.timeout == 60
            assert tool._config_obj.max_retries == 5


class TestToolRegistryTOOL_CONFIGSIntegration:
    """Test TOOL_CONFIGS dictionary integration"""

    def test_tool_configs_takes_highest_precedence(self):
        """Test that TOOL_CONFIGS values take highest precedence"""
        test_tool_name = "test_precedence_tool"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]
        if test_tool_name in TOOL_CONFIGS:
            del TOOL_CONFIGS[test_tool_name]

        # Register tool
        @register_tool(test_tool_name)
        class TestPrecedenceTool(BaseTool):
            class Config(BaseModel):
                timeout: int = Field(default=30)
                max_retries: int = Field(default=3)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config" / "tools"
            config_dir.mkdir(parents=True)
            loader = get_tool_config_loader()
            loader.set_config_path(config_dir.parent)

            # Create YAML config
            yaml_file = config_dir / f"{test_tool_name}.yaml"
            yaml_file.write_text("timeout: 60\nmax_retries: 5\n")

            # Set TOOL_CONFIGS (should override YAML)
            TOOL_CONFIGS[test_tool_name] = {"timeout": 120}

            try:
                # Get tool
                tool = get_tool(test_tool_name)

                # TOOL_CONFIGS should override YAML
                assert tool._config_obj.timeout == 120  # From TOOL_CONFIGS
                assert tool._config_obj.max_retries == 5  # From YAML
            finally:
                # Cleanup
                if test_tool_name in TOOL_CONFIGS:
                    del TOOL_CONFIGS[test_tool_name]

    def test_tool_configs_empty_dict_uses_yaml(self):
        """Test that empty TOOL_CONFIGS dict still allows YAML loading"""
        test_tool_name = "test_empty_configs_tool"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]
        if test_tool_name in TOOL_CONFIGS:
            del TOOL_CONFIGS[test_tool_name]

        # Register tool
        @register_tool(test_tool_name)
        class TestEmptyConfigsTool(BaseTool):
            class Config(BaseModel):
                timeout: int = Field(default=30)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config" / "tools"
            config_dir.mkdir(parents=True)
            loader = get_tool_config_loader()
            loader.set_config_path(config_dir.parent)

            # Create YAML config
            yaml_file = config_dir / f"{test_tool_name}.yaml"
            yaml_file.write_text("timeout: 60\n")

            # Set empty TOOL_CONFIGS
            TOOL_CONFIGS[test_tool_name] = {}

            try:
                # Get tool - should load from YAML
                tool = get_tool(test_tool_name)
                assert tool._config_obj.timeout == 60  # From YAML
            finally:
                # Cleanup
                if test_tool_name in TOOL_CONFIGS:
                    del TOOL_CONFIGS[test_tool_name]

    def test_tool_configs_none_uses_yaml(self):
        """Test that None TOOL_CONFIGS (not set) still allows YAML loading"""
        test_tool_name = "test_none_configs_tool"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]
        if test_tool_name in TOOL_CONFIGS:
            del TOOL_CONFIGS[test_tool_name]

        # Register tool
        @register_tool(test_tool_name)
        class TestNoneConfigsTool(BaseTool):
            class Config(BaseModel):
                timeout: int = Field(default=30)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config" / "tools"
            config_dir.mkdir(parents=True)
            loader = get_tool_config_loader()
            loader.set_config_path(config_dir.parent)

            # Create YAML config
            yaml_file = config_dir / f"{test_tool_name}.yaml"
            yaml_file.write_text("timeout: 60\n")

            # Don't set TOOL_CONFIGS (should default to {})

            # Get tool - should load from YAML
            tool = get_tool(test_tool_name)
            assert tool._config_obj.timeout == 60  # From YAML


class TestToolRegistryBackwardCompatibility:
    """Test backward compatibility"""

    def test_tool_without_config_class_still_works(self):
        """Test that tools without Config class work through registry"""
        test_tool_name = "test_no_config_tool"
        if test_tool_name in TOOL_CLASSES:
            del TOOL_CLASSES[test_tool_name]
        if test_tool_name in TOOL_REGISTRY:
            del TOOL_REGISTRY[test_tool_name]

        # Register tool without Config class
        @register_tool(test_tool_name)
        class TestNoConfigTool(BaseTool):
            def test_operation(self, value: str):
                return f"Result: {value}"

        # Get tool - should work
        tool = get_tool(test_tool_name)
        assert tool is not None
        assert tool._config_obj is None
        assert tool._config == {}

