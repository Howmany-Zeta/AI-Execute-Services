"""
Unit tests for ToolConfigLoader.

Tests cover:
- Singleton pattern
- Config directory discovery
- Custom config path setting
- Config merging precedence
- Dotenv loading
- YAML loading
- Config directory caching
- Error handling
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import yaml
from pydantic import BaseModel, Field
from pydantic import ValidationError

from aiecs.config.tool_config import ToolConfigLoader, get_tool_config_loader


class TestToolConfig(BaseModel):
    """Test configuration schema"""

    api_key: str = Field(default="")
    timeout: int = Field(default=30)
    max_retries: int = Field(default=3)


class TestToolConfigLoaderSingleton:
    """Test singleton pattern"""

    def test_singleton_pattern(self):
        """Test that get_tool_config_loader returns the same instance"""
        loader1 = get_tool_config_loader()
        loader2 = get_tool_config_loader()
        loader3 = ToolConfigLoader()

        assert loader1 is loader2
        assert loader1 is loader3
        assert loader2 is loader3

    def test_singleton_thread_safety(self):
        """Test that singleton is thread-safe"""
        import threading

        instances = []

        def get_instance():
            instances.append(get_tool_config_loader())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert all(instance is instances[0] for instance in instances)


class TestConfigDirectoryDiscovery:
    """Test config directory discovery"""

    def test_find_config_directory_walking_up_tree(self):
        """Test that find_config_directory walks up directory tree"""
        loader = ToolConfigLoader()
        loader._cached_config_dir = None  # Clear cache

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            nested_dir = Path(tmpdir) / "level1" / "level2" / "level3"
            nested_dir.mkdir(parents=True)
            config_dir = Path(tmpdir) / "level1" / "config"
            config_dir.mkdir(parents=True)

            # Change to nested directory
            original_cwd = os.getcwd()
            try:
                os.chdir(nested_dir)
                found_dir = loader.find_config_directory()
                assert found_dir is not None
                assert found_dir.exists()
                assert found_dir.name == "config"
            finally:
                os.chdir(original_cwd)

    def test_find_config_directory_env_var_override(self):
        """Test that TOOL_CONFIG_PATH environment variable overrides discovery"""
        loader = ToolConfigLoader()
        loader._cached_config_dir = None  # Clear cache

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "custom_config"
            config_dir.mkdir()

            with patch.dict(os.environ, {"TOOL_CONFIG_PATH": str(config_dir)}):
                found_dir = loader.find_config_directory()
                assert found_dir == config_dir

    def test_find_config_directory_custom_path(self):
        """Test that set_config_path sets custom path"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "my_config"
            custom_path.mkdir()

            loader.set_config_path(custom_path)
            found_dir = loader.find_config_directory()
            assert found_dir == custom_path

    def test_find_config_directory_caching(self):
        """Test that config directory is cached"""
        loader = ToolConfigLoader()
        loader._cached_config_dir = None  # Clear cache

        with tempfile.TemporaryDirectory() as tmpdir:
            # Config directory discovery
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # First call should discover and cache
                found_dir1 = loader.find_config_directory()
                cached_dir = loader._cached_config_dir

                # Second call should use cache
                found_dir2 = loader.find_config_directory()
                assert found_dir1 == found_dir2
                assert loader._cached_config_dir == cached_dir
            finally:
                os.chdir(original_cwd)

    def test_get_config_path(self):
        """Test get_config_path returns set path"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "my_config"
            custom_path.mkdir()

            loader.set_config_path(custom_path)
            assert loader.get_config_path() == custom_path


class TestDotenvLoading:
    """Test dotenv loading"""

    def test_load_env_config_loads_env_files(self):
        """Test that load_env_config loads .env files"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create .env file
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("TEST_API_KEY=test_value_123\nTEST_TIMEOUT=60\n")

            # Load env config
            loader.load_env_config()

            # Check that environment variables were loaded
            assert os.environ.get("TEST_API_KEY") == "test_value_123"
            assert os.environ.get("TEST_TIMEOUT") == "60"

            # Cleanup
            if "TEST_API_KEY" in os.environ:
                del os.environ["TEST_API_KEY"]
            if "TEST_TIMEOUT" in os.environ:
                del os.environ["TEST_TIMEOUT"]

    def test_load_env_config_multiple_files(self):
        """Test that load_env_config loads multiple .env files in order"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create base .env file
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("TEST_VALUE=base\n")

            # Create .env.local file
            env_local_file = Path(tmpdir) / ".env.local"
            env_local_file.write_text("TEST_VALUE=local\n")

            # Load env config
            loader.load_env_config()

            # .env.local should override .env
            assert os.environ.get("TEST_VALUE") == "local"

            # Cleanup
            if "TEST_VALUE" in os.environ:
                del os.environ["TEST_VALUE"]


class TestYamlLoading:
    """Test YAML configuration loading"""

    def test_load_yaml_config_tool_specific(self):
        """Test loading tool-specific YAML config"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create tool-specific config
            tool_config_file = tools_dir / "TestTool.yaml"
            tool_config_file.write_text("timeout: 60\nmax_retries: 5\n")

            config = loader.load_yaml_config("TestTool")
            assert config["timeout"] == 60
            assert config["max_retries"] == 5

    def test_load_yaml_config_global(self):
        """Test loading global YAML config"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create global config
            global_config_file = config_dir / "tools.yaml"
            global_config_file.write_text("timeout: 30\nmax_retries: 3\n")

            config = loader.load_yaml_config("TestTool")
            assert config["timeout"] == 30
            assert config["max_retries"] == 3

    def test_load_yaml_config_precedence(self):
        """Test that tool-specific config overrides global config"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create global config
            global_config_file = config_dir / "tools.yaml"
            global_config_file.write_text("timeout: 30\nmax_retries: 3\n")

            # Create tool-specific config
            tool_config_file = tools_dir / "TestTool.yaml"
            tool_config_file.write_text("timeout: 60\n")

            config = loader.load_yaml_config("TestTool")
            # Tool-specific timeout should override global
            assert config["timeout"] == 60
            # Global max_retries should still be present
            assert config["max_retries"] == 3

    def test_load_yaml_config_missing_files(self):
        """Test that missing YAML files are handled gracefully"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # No config files exist
            config = loader.load_yaml_config("NonExistentTool")
            assert config == {}

    def test_load_yaml_config_invalid_yaml(self):
        """Test that invalid YAML files are handled gracefully"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create invalid YAML file
            invalid_config_file = config_dir / "tools.yaml"
            invalid_config_file.write_text("invalid: yaml: content: [\n")

            # Should not raise exception, just log warning
            config = loader.load_yaml_config("TestTool")
            assert config == {}  # Should return empty dict on error


class TestConfigMerging:
    """Test configuration merging"""

    def test_merge_config_precedence(self):
        """Test that config merging follows correct precedence order"""
        loader = ToolConfigLoader()

        defaults = {"timeout": 10, "max_retries": 1}
        yaml_config = {"timeout": 30, "max_retries": 3}
        explicit_config = {"timeout": 60}

        merged = loader.merge_config(
            explicit_config=explicit_config,
            yaml_config=yaml_config,
            defaults=defaults,
        )

        # Explicit config should have highest priority
        assert merged["timeout"] == 60
        # YAML config should override defaults
        assert merged["max_retries"] == 3

    def test_merge_config_explicit_overrides_all(self):
        """Test that explicit config overrides everything"""
        loader = ToolConfigLoader()

        defaults = {"timeout": 10, "max_retries": 1, "api_key": "default"}
        yaml_config = {"timeout": 30, "max_retries": 3}
        explicit_config = {"timeout": 60, "max_retries": 5, "api_key": "explicit"}

        merged = loader.merge_config(
            explicit_config=explicit_config,
            yaml_config=yaml_config,
            defaults=defaults,
        )

        assert merged["timeout"] == 60
        assert merged["max_retries"] == 5
        assert merged["api_key"] == "explicit"


class TestConfigValidation:
    """Test configuration validation"""

    def test_validate_config_valid(self):
        """Test validation with valid config"""
        loader = ToolConfigLoader()

        config_dict = {"api_key": "test_key", "timeout": 30, "max_retries": 3}
        validated = loader.validate_config(config_dict, TestToolConfig)

        assert validated["api_key"] == "test_key"
        assert validated["timeout"] == 30
        assert validated["max_retries"] == 3

    def test_validate_config_invalid(self):
        """Test validation with invalid config"""
        loader = ToolConfigLoader()

        # Invalid type for timeout (should be int)
        config_dict = {"api_key": "test_key", "timeout": "not_an_int", "max_retries": 3}

        with pytest.raises(ValidationError):
            loader.validate_config(config_dict, TestToolConfig)

    def test_validate_config_with_defaults(self):
        """Test validation uses defaults from schema"""
        loader = ToolConfigLoader()

        # Only provide api_key, others should use defaults
        config_dict = {"api_key": "test_key"}
        validated = loader.validate_config(config_dict, TestToolConfig)

        assert validated["api_key"] == "test_key"
        assert validated["timeout"] == 30  # Default from schema
        assert validated["max_retries"] == 3  # Default from schema


class TestLoadToolConfig:
    """Test main load_tool_config method"""

    def test_load_tool_config_basic(self):
        """Test basic tool config loading"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create YAML config
            tool_config_file = config_dir / "tools" / "TestTool.yaml"
            tool_config_file.parent.mkdir()
            tool_config_file.write_text("timeout: 60\nmax_retries: 5\n")

            config = loader.load_tool_config("TestTool", config_schema=TestToolConfig)
            assert config["timeout"] == 60
            assert config["max_retries"] == 5

    def test_load_tool_config_with_explicit(self):
        """Test tool config loading with explicit config override"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create YAML config
            tool_config_file = config_dir / "tools" / "TestTool.yaml"
            tool_config_file.parent.mkdir()
            tool_config_file.write_text("timeout: 60\nmax_retries: 5\n")

            explicit_config = {"timeout": 120}
            config = loader.load_tool_config(
                "TestTool", config_schema=TestToolConfig, explicit_config=explicit_config
            )

            # Explicit config should override YAML
            assert config["timeout"] == 120
            # YAML config should still be present
            assert config["max_retries"] == 5

    def test_load_tool_config_without_schema(self):
        """Test tool config loading without schema validation"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create YAML config
            tool_config_file = config_dir / "tools" / "TestTool.yaml"
            tool_config_file.parent.mkdir()
            tool_config_file.write_text("timeout: 60\nmax_retries: 5\n")

            config = loader.load_tool_config("TestTool", config_schema=None)
            assert config["timeout"] == 60
            assert config["max_retries"] == 5

    def test_load_tool_config_validation_error(self):
        """Test that validation errors are raised properly"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create invalid YAML config
            tool_config_file = config_dir / "tools" / "TestTool.yaml"
            tool_config_file.parent.mkdir()
            tool_config_file.write_text("timeout: not_an_int\nmax_retries: 5\n")

            with pytest.raises(ValidationError):
                loader.load_tool_config("TestTool", config_schema=TestToolConfig)


class TestErrorHandling:
    """Test error handling"""

    def test_yaml_parse_error_handling(self):
        """Test that YAML parse errors are handled gracefully"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # Create invalid YAML file
            invalid_config_file = config_dir / "tools.yaml"
            invalid_config_file.write_text("invalid: yaml: content: [\n")

            # Should not raise exception
            config = loader.load_yaml_config("TestTool")
            assert isinstance(config, dict)

    def test_missing_config_files_handled(self):
        """Test that missing config files are handled gracefully"""
        loader = ToolConfigLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)

            # No config files exist
            config = loader.load_tool_config("NonExistentTool", config_schema=None)
            assert isinstance(config, dict)

    def test_invalid_schema_validation_error(self):
        """Test that invalid schema validation provides clear error messages"""
        loader = ToolConfigLoader()

        config_dict = {"timeout": "not_an_int"}

        with pytest.raises(ValidationError) as exc_info:
            loader.validate_config(config_dict, TestToolConfig)

        # Check that error message is clear
        assert "timeout" in str(exc_info.value).lower() or "validation" in str(exc_info.value).lower()

