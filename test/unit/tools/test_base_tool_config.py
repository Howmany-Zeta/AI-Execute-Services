"""
Unit tests for BaseTool configuration loading integration.

Tests cover:
- Automatic config loading (zero config needed)
- Explicit config dict override
- Tools without Config class (backward compatibility)
- Tools with Config class using BaseSettings
- Tools with Config class using BaseModel
- Config validation errors
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.config.tool_config import get_tool_config_loader


class TestToolWithoutConfig(BaseTool):
    """Test tool without Config class - backward compatibility"""

    def test_operation(self, value: str):
        return f"Result: {value}"


class TestToolWithBaseModelConfig(BaseTool):
    """Test tool with BaseModel Config class"""

    class Config(BaseModel):
        timeout: int = Field(default=30)
        max_retries: int = Field(default=3)

    def test_operation(self, value: str):
        return f"Result: {value}"


class TestToolWithBaseSettingsConfig(BaseTool):
    """Test tool with BaseSettings Config class"""

    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="TEST_TOOL_")

        api_key: str = Field(default="")
        timeout: int = Field(default=30)
        max_retries: int = Field(default=3)

    def test_operation(self, value: str):
        return f"Result: {value}"


class TestToolWithRequiredConfig(BaseTool):
    """Test tool with required Config fields"""

    class Config(BaseModel):
        required_field: str
        optional_field: int = Field(default=10)

    def test_operation(self, value: str):
        return f"Result: {value}"


class TestBaseToolAutomaticConfigLoading:
    """Test automatic configuration loading"""

    def test_tool_without_config_class(self):
        """Test that tools without Config class work (backward compatibility)"""
        tool = TestToolWithoutConfig()
        assert tool._config == {}
        assert tool._config_obj is None

    def test_tool_with_config_class_zero_config(self):
        """Test that tools with Config class work with zero config (uses defaults)"""
        tool = TestToolWithBaseModelConfig()
        assert tool._config_obj is not None
        assert tool._config_obj.timeout == 30  # Default value
        assert tool._config_obj.max_retries == 3  # Default value

    def test_tool_with_config_class_explicit_config(self):
        """Test that explicit config overrides defaults"""
        tool = TestToolWithBaseModelConfig(config={"timeout": 60, "max_retries": 5})
        assert tool._config_obj is not None
        assert tool._config_obj.timeout == 60
        assert tool._config_obj.max_retries == 5

    def test_tool_name_passed_to_loader(self):
        """Test that tool name is passed to loader for config file discovery"""
        with patch.object(get_tool_config_loader(), "load_tool_config") as mock_load:
            mock_load.return_value = {"timeout": 45}
            tool = TestToolWithBaseModelConfig(tool_name="custom_tool_name")
            mock_load.assert_called_once()
            # Check that tool_name was passed
            call_args = mock_load.call_args
            assert call_args.kwargs["tool_name"] == "custom_tool_name"

    def test_tool_name_defaults_to_class_name(self):
        """Test that tool name defaults to class name if not provided"""
        with patch.object(get_tool_config_loader(), "load_tool_config") as mock_load:
            mock_load.return_value = {"timeout": 45}
            tool = TestToolWithBaseModelConfig()
            mock_load.assert_called_once()
            # Check that tool_name defaults to class name
            call_args = mock_load.call_args
            assert call_args.kwargs["tool_name"] == "TestToolWithBaseModelConfig"


class TestBaseToolExplicitConfigOverride:
    """Test explicit config override"""

    def test_explicit_config_overrides_yaml(self):
        """Test that explicit config takes highest precedence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config" / "tools"
            config_dir.mkdir(parents=True)
            loader = get_tool_config_loader()
            loader.set_config_path(config_dir.parent)

            # Create YAML config
            yaml_file = config_dir / "TestToolWithBaseModelConfig.yaml"
            yaml_file.write_text("timeout: 60\nmax_retries: 5\n")

            # Explicit config should override YAML
            tool = TestToolWithBaseModelConfig(config={"timeout": 120})
            assert tool._config_obj.timeout == 120  # Explicit overrides YAML
            assert tool._config_obj.max_retries == 5  # YAML value used

    def test_explicit_config_overrides_env_vars(self):
        """Test that explicit config overrides environment variables"""
        # Set environment variable
        os.environ["TEST_TOOL_TIMEOUT"] = "90"
        os.environ["TEST_TOOL_MAX_RETRIES"] = "7"

        try:
            # Explicit config should override env vars
            tool = TestToolWithBaseSettingsConfig(config={"timeout": 100})
            assert tool._config_obj.timeout == 100  # Explicit overrides env
            assert tool._config_obj.max_retries == 7  # Env var used
        finally:
            # Cleanup
            if "TEST_TOOL_TIMEOUT" in os.environ:
                del os.environ["TEST_TOOL_TIMEOUT"]
            if "TEST_TOOL_MAX_RETRIES" in os.environ:
                del os.environ["TEST_TOOL_MAX_RETRIES"]


class TestBaseToolBackwardCompatibility:
    """Test backward compatibility"""

    def test_tool_without_config_class_still_works(self):
        """Test that tools without Config class continue to work"""
        tool = TestToolWithoutConfig(config={"custom_key": "custom_value"})
        assert tool._config == {"custom_key": "custom_value"}
        assert tool._config_obj is None

    def test_tool_without_config_class_empty_config(self):
        """Test that tools without Config class work with empty config"""
        tool = TestToolWithoutConfig()
        assert tool._config == {}
        assert tool._config_obj is None

    def test_tool_without_config_class_yaml_loading(self):
        """Test that tools without Config class can still load from YAML"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config" / "tools"
            config_dir.mkdir(parents=True)
            loader = get_tool_config_loader()
            loader.set_config_path(config_dir.parent)

            # Create YAML config
            yaml_file = config_dir / "TestToolWithoutConfig.yaml"
            yaml_file.write_text("custom_setting: yaml_value\n")

            tool = TestToolWithoutConfig()
            # Should attempt to load from YAML even without Config class
            assert isinstance(tool._config, dict)


class TestBaseToolConfigClassDetection:
    """Test Config class detection"""

    def test_detect_base_model_config(self):
        """Test detection of BaseModel Config class"""
        tool = TestToolWithBaseModelConfig()
        config_class = tool._detect_config_class()
        assert config_class is not None
        assert config_class == TestToolWithBaseModelConfig.Config

    def test_detect_base_settings_config(self):
        """Test detection of BaseSettings Config class"""
        tool = TestToolWithBaseSettingsConfig()
        config_class = tool._detect_config_class()
        assert config_class is not None
        assert config_class == TestToolWithBaseSettingsConfig.Config

    def test_detect_no_config_class(self):
        """Test detection when no Config class exists"""
        tool = TestToolWithoutConfig()
        config_class = tool._detect_config_class()
        assert config_class is None


class TestBaseToolBaseSettingsIntegration:
    """Test BaseSettings integration"""

    def test_base_settings_automatic_env_var_loading(self):
        """Test that BaseSettings Config classes automatically load env vars"""
        # Set environment variables
        os.environ["TEST_TOOL_API_KEY"] = "test_api_key_123"
        os.environ["TEST_TOOL_TIMEOUT"] = "45"

        try:
            tool = TestToolWithBaseSettingsConfig()
            # BaseSettings should automatically load from env vars
            assert tool._config_obj.api_key == "test_api_key_123"
            assert tool._config_obj.timeout == 45
        finally:
            # Cleanup
            if "TEST_TOOL_API_KEY" in os.environ:
                del os.environ["TEST_TOOL_API_KEY"]
            if "TEST_TOOL_TIMEOUT" in os.environ:
                del os.environ["TEST_TOOL_TIMEOUT"]

    def test_base_settings_explicit_overrides_env(self):
        """Test that explicit config overrides BaseSettings env vars"""
        os.environ["TEST_TOOL_TIMEOUT"] = "45"

        try:
            tool = TestToolWithBaseSettingsConfig(config={"timeout": 60})
            # Explicit should override env var
            assert tool._config_obj.timeout == 60
        finally:
            if "TEST_TOOL_TIMEOUT" in os.environ:
                del os.environ["TEST_TOOL_TIMEOUT"]


class TestBaseToolConfigValidation:
    """Test configuration validation"""

    def test_valid_config_passes_validation(self):
        """Test that valid config passes validation"""
        tool = TestToolWithBaseModelConfig(config={"timeout": 60, "max_retries": 5})
        assert tool._config_obj is not None
        assert tool._config_obj.timeout == 60
        assert tool._config_obj.max_retries == 5

    def test_invalid_config_raises_validation_error(self):
        """Test that invalid config raises ValidationError"""
        # Invalid type for timeout (should be int)
        with pytest.raises(ValidationError):
            TestToolWithBaseModelConfig(config={"timeout": "not_an_int"})

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError):
            TestToolWithRequiredConfig()

    def test_required_field_provided_passes(self):
        """Test that providing required field passes validation"""
        tool = TestToolWithRequiredConfig(config={"required_field": "value"})
        assert tool._config_obj.required_field == "value"
        assert tool._config_obj.optional_field == 10  # Default value

    def test_validation_error_has_clear_message(self):
        """Test that validation errors provide clear error messages"""
        with pytest.raises(ValidationError) as exc_info:
            TestToolWithBaseModelConfig(config={"timeout": "invalid"})

        # Check that error message is informative
        error_str = str(exc_info.value)
        assert "timeout" in error_str.lower() or "validation" in error_str.lower()


class TestBaseToolErrorHandling:
    """Test error handling"""

    def test_config_loading_error_graceful_fallback(self):
        """Test that config loading errors are handled gracefully"""
        # Mock loader to raise an exception
        with patch.object(get_tool_config_loader(), "load_tool_config") as mock_load:
            mock_load.side_effect = Exception("Config loading failed")

            # Should fallback to defaults or empty config
            tool = TestToolWithBaseModelConfig()
            # Should still work, using defaults
            assert tool._config_obj is not None
            assert tool._config_obj.timeout == 30  # Default value

    def test_yaml_parse_error_graceful_fallback(self):
        """Test that YAML parse errors are handled gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config" / "tools"
            config_dir.mkdir(parents=True)
            loader = get_tool_config_loader()
            loader.set_config_path(config_dir.parent)

            # Create invalid YAML file
            yaml_file = config_dir / "TestToolWithBaseModelConfig.yaml"
            yaml_file.write_text("invalid: yaml: content: [\n")

            # Should not raise exception, should use defaults
            tool = TestToolWithBaseModelConfig()
            assert tool._config_obj is not None
            assert tool._config_obj.timeout == 30  # Default value

