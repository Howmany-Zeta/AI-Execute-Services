"""
Integration tests for ToolConfigLoader.

Tests end-to-end configuration loading scenarios:
- Singleton pattern and thread-safety
- Loading from .env files (multiple files)
- Loading from YAML files (tool-specific and global)
- Configuration precedence
- Config directory discovery
- Configuration validation
- Error handling
"""

import os
import tempfile
import shutil
import threading
from pathlib import Path
from unittest.mock import patch
import pytest
import yaml
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.config.tool_config import ToolConfigLoader, get_tool_config_loader


class TestConfigSchema(BaseSettings):
    """Test configuration schema"""
    model_config = SettingsConfigDict(env_prefix="TEST_TOOL_")
    
    api_key: str = Field(default="", description="API key")
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout")
    max_retries: int = Field(default=3, ge=0, le=10, description="Max retries")
    enable_cache: bool = Field(default=True, description="Enable cache")


class TestToolConfigLoaderIntegration:
    """Integration tests for ToolConfigLoader"""
    
    def test_singleton_pattern(self):
        """Test that singleton pattern works correctly"""
        loader1 = get_tool_config_loader()
        loader2 = get_tool_config_loader()
        loader3 = ToolConfigLoader()
        
        assert loader1 is loader2
        assert loader1 is loader3
        assert loader2 is loader3
    
    def test_singleton_thread_safety(self):
        """Test that singleton is thread-safe"""
        loaders = []
        
        def get_loader():
            loaders.append(get_tool_config_loader())
        
        threads = [threading.Thread(target=get_loader) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All should be the same instance
        assert all(loader is loaders[0] for loader in loaders)
    
    def test_load_from_env_files(self):
        """Test loading from .env files"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create .env file
            env_file = config_dir.parent / ".env"
            env_file.write_text("TEST_TOOL_API_KEY=test-key-from-env\nTEST_TOOL_TIMEOUT=45\n")
            
            # Load config
            config = loader.load_tool_config("TestTool", config_schema=TestConfigSchema)
            
            # Verify env vars are loaded (via BaseSettings)
            assert config.get("api_key") == "test-key-from-env" or os.environ.get("TEST_TOOL_API_KEY") == "test-key-from-env"
    
    def test_load_from_multiple_env_files(self):
        """Test loading from multiple .env files (.env, .env.local)"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)
            
            base_dir = config_dir.parent
            
            # Create .env file
            env_file = base_dir / ".env"
            env_file.write_text("TEST_TOOL_API_KEY=base-key\nTEST_TOOL_TIMEOUT=30\n")
            
            # Create .env.local file (should override .env)
            env_local_file = base_dir / ".env.local"
            env_local_file.write_text("TEST_TOOL_TIMEOUT=60\n")
            
            # Load config
            loader.load_env_config()
            
            # Verify .env.local overrides .env
            # Note: dotenv loads into os.environ, so we check there
            assert os.environ.get("TEST_TOOL_TIMEOUT") == "60"
            
            # Cleanup
            os.environ.pop("TEST_TOOL_API_KEY", None)
            os.environ.pop("TEST_TOOL_TIMEOUT", None)
    
    def test_load_from_yaml_tool_specific(self):
        """Test loading from tool-specific YAML file"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create tool-specific YAML
            tool_yaml = tools_dir / "TestTool.yaml"
            tool_yaml.write_text("timeout: 60\nmax_retries: 5\nenable_cache: false\n")
            
            # Load config
            config = loader.load_yaml_config("TestTool")
            
            assert config["timeout"] == 60
            assert config["max_retries"] == 5
            assert config["enable_cache"] is False
    
    def test_load_from_yaml_global(self):
        """Test loading from global YAML file"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create global YAML
            global_yaml = config_dir / "tools.yaml"
            global_yaml.write_text("timeout: 45\nmax_retries: 3\n")
            
            # Load config
            config = loader.load_yaml_config("TestTool")
            
            assert config["timeout"] == 45
            assert config["max_retries"] == 3
    
    def test_yaml_precedence_tool_over_global(self):
        """Test that tool-specific YAML overrides global YAML"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create global YAML
            global_yaml = config_dir / "tools.yaml"
            global_yaml.write_text("timeout: 30\nmax_retries: 3\n")
            
            # Create tool-specific YAML (should override global)
            tool_yaml = tools_dir / "TestTool.yaml"
            tool_yaml.write_text("timeout: 60\n")
            
            # Load config
            config = loader.load_yaml_config("TestTool")
            
            assert config["timeout"] == 60  # Tool-specific wins
            assert config["max_retries"] == 3  # From global
    
    def test_missing_yaml_files_handled_gracefully(self):
        """Test that missing YAML files are handled gracefully"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # No YAML files exist
            config = loader.load_yaml_config("NonExistentTool")
            
            assert isinstance(config, dict)
            assert len(config) == 0
    
    def test_config_precedence_explicit_over_yaml(self):
        """Test configuration precedence: explicit > YAML > env > defaults"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create YAML config
            tool_yaml = tools_dir / "TestTool.yaml"
            tool_yaml.write_text("timeout: 60\nmax_retries: 5\n")
            
            # Set environment variable
            os.environ["TEST_TOOL_TIMEOUT"] = "45"
            
            # Load with explicit config (should win)
            config = loader.load_tool_config(
                "TestTool",
                config_schema=TestConfigSchema,
                explicit_config={"timeout": 120}
            )
            
            # Explicit config should win
            assert config["timeout"] == 120
            
            # Cleanup
            os.environ.pop("TEST_TOOL_TIMEOUT", None)
    
    def test_config_precedence_yaml_over_env(self):
        """Test that YAML config overrides environment variables"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create YAML config
            tool_yaml = tools_dir / "TestTool.yaml"
            tool_yaml.write_text("timeout: 60\n")
            
            # Set environment variable
            os.environ["TEST_TOOL_TIMEOUT"] = "45"
            
            # Load config (YAML should win over env)
            config = loader.load_tool_config(
                "TestTool",
                config_schema=TestConfigSchema
            )
            
            # YAML should win
            assert config["timeout"] == 60
            
            # Cleanup
            os.environ.pop("TEST_TOOL_TIMEOUT", None)
    
    def test_config_directory_discovery_walk_up_tree(self):
        """Test config directory discovery by walking up directory tree"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            nested_dir = Path(tmpdir) / "level1" / "level2" / "level3"
            nested_dir.mkdir(parents=True)
            
            # Create config directory at root
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            
            # Change to nested directory
            original_cwd = os.getcwd()
            try:
                os.chdir(str(nested_dir))
                
                # Should find config directory by walking up
                found_dir = loader.find_config_directory()
                
                assert found_dir == config_dir
            finally:
                os.chdir(original_cwd)
    
    def test_config_directory_discovery_env_var_override(self):
        """Test config directory discovery with TOOL_CONFIG_PATH env var"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_config_dir = Path(tmpdir) / "custom_config"
            custom_config_dir.mkdir()
            
            # Set environment variable
            os.environ["TOOL_CONFIG_PATH"] = str(custom_config_dir)
            
            try:
                # Should use env var
                found_dir = loader.find_config_directory()
                
                assert found_dir == custom_config_dir
            finally:
                os.environ.pop("TOOL_CONFIG_PATH", None)
                # Clear cached directory
                loader._cached_config_dir = None
    
    def test_config_directory_caching(self):
        """Test that config directory is cached after first discovery"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # First call - should discover
            found1 = loader.find_config_directory()
            
            # Second call - should use cache
            found2 = loader.find_config_directory()
            
            assert found1 == found2 == config_dir
    
    def test_custom_config_path_setting(self):
        """Test setting custom config path"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_config_dir = Path(tmpdir) / "custom_config"
            custom_config_dir.mkdir()
            
            # Set custom path
            loader.set_config_path(custom_config_dir)
            
            # Should use custom path
            found_dir = loader.find_config_directory()
            assert found_dir == custom_config_dir
            
            # Get config path should return custom path
            assert loader.get_config_path() == custom_config_dir
    
    def test_config_validation_valid_config(self):
        """Test that valid config passes schema validation"""
        loader = ToolConfigLoader()
        
        config_dict = {
            "api_key": "test-key",
            "timeout": 60,
            "max_retries": 5,
            "enable_cache": True
        }
        
        validated = loader.validate_config(config_dict, TestConfigSchema)
        
        assert validated["timeout"] == 60
        assert validated["max_retries"] == 5
        assert validated["api_key"] == "test-key"
    
    def test_config_validation_invalid_config(self):
        """Test that invalid config provides clear error messages"""
        loader = ToolConfigLoader()
        
        # Invalid: timeout out of range
        config_dict = {"timeout": 500}  # > 300
        
        with pytest.raises(ValidationError) as exc_info:
            loader.validate_config(config_dict, TestConfigSchema)
        
        # Check error message mentions timeout
        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "validation" in error_msg
    
    def test_config_validation_missing_required_fields(self):
        """Test handling of missing required fields"""
        loader = ToolConfigLoader()
        
        # Empty config - should use defaults
        config_dict = {}
        
        # Should not raise error (uses defaults)
        validated = loader.validate_config(config_dict, TestConfigSchema)
        
        assert validated["timeout"] == 30  # Default
        assert validated["max_retries"] == 3  # Default
    
    def test_yaml_parse_error_handling(self):
        """Test that YAML parse errors are handled gracefully"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create invalid YAML file
            invalid_yaml = tools_dir / "TestTool.yaml"
            invalid_yaml.write_text("invalid: yaml: content: [\n")
            
            # Should not raise exception, should return empty dict or log warning
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
            loader.validate_config(config_dict, TestConfigSchema)
        
        # Check that error message is clear
        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "validation" in error_msg
    
    def test_end_to_end_config_loading(self):
        """Test end-to-end configuration loading with all sources"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            base_dir = config_dir.parent
            
            # Create .env file
            env_file = base_dir / ".env"
            env_file.write_text("TEST_TOOL_API_KEY=env-key\n")
            
            # Create global YAML
            global_yaml = config_dir / "tools.yaml"
            global_yaml.write_text("max_retries: 3\n")
            
            # Create tool-specific YAML
            tool_yaml = tools_dir / "TestTool.yaml"
            tool_yaml.write_text("timeout: 60\n")
            
            # Load config with explicit override
            config = loader.load_tool_config(
                "TestTool",
                config_schema=TestConfigSchema,
                explicit_config={"enable_cache": False}
            )
            
            # Verify precedence: explicit > YAML > env > defaults
            assert config["enable_cache"] is False  # Explicit
            assert config["timeout"] == 60  # YAML
            assert config["max_retries"] == 3  # Global YAML
            # API key from env (via BaseSettings)
            
            # Cleanup
            os.environ.pop("TEST_TOOL_API_KEY", None)

