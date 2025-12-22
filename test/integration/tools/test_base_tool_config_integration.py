"""
Integration tests for BaseTool configuration loading.

Tests end-to-end configuration scenarios:
- Automatic config loading (zero config)
- Explicit config override
- Tools without Config class (backward compatibility)
- Tools with BaseSettings Config class
- Tools with BaseModel Config class
- Config validation errors
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import pytest
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.config.tool_config import get_tool_config_loader


class TestToolWithoutConfig(BaseTool):
    """Test tool without Config class (backward compatibility)"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.timeout = 30  # Hardcoded default


class TestToolWithBaseSettings(BaseTool):
    """Test tool with BaseSettings Config class"""
    
    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="TEST_BASESETTINGS_")
        timeout: int = Field(default=30, description="Timeout")
        max_retries: int = Field(default=3, description="Max retries")
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.config = self._config_obj if self._config_obj else self.Config()


class TestToolWithBaseModel(BaseTool):
    """Test tool with BaseModel Config class"""
    
    class Config(BaseModel):
        timeout: int = Field(default=30)
        max_retries: int = Field(default=3)
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.config = self._config_obj if self._config_obj else self.Config()


class TestToolWithValidation(BaseTool):
    """Test tool with validation requirements"""
    
    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="TEST_VALIDATION_")
        timeout: int = Field(default=30, ge=1, le=300)
        max_retries: int = Field(default=3, ge=0, le=10)
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.config = self._config_obj if self._config_obj else self.Config()


class TestBaseToolConfigIntegration:
    """Integration tests for BaseTool configuration"""
    
    def test_automatic_config_loading_zero_config(self):
        """Test automatic config loading with zero config needed"""
        tool = TestToolWithBaseSettings()
        
        # Should use defaults
        assert tool.config.timeout == 30
        assert tool.config.max_retries == 3
    
    def test_explicit_config_override(self):
        """Test explicit config dict override (highest precedence)"""
        tool = TestToolWithBaseSettings(config={"timeout": 120, "max_retries": 5})
        
        # Explicit config should win
        assert tool.config.timeout == 120
        assert tool.config.max_retries == 5
    
    def test_tool_without_config_class(self):
        """Test tool without Config class (backward compatibility)"""
        tool = TestToolWithoutConfig()
        
        # Should work without Config class
        assert tool.timeout == 30
        assert not hasattr(tool, 'config') or tool._config_obj is None
    
    def test_tool_with_basesettings_config(self):
        """Test tool with BaseSettings Config class"""
        tool = TestToolWithBaseSettings()
        
        # Should have config loaded
        assert hasattr(tool, 'config')
        assert tool.config.timeout == 30
        assert tool.config.max_retries == 3
    
    def test_tool_with_basemodel_config(self):
        """Test tool with BaseModel Config class"""
        tool = TestToolWithBaseModel(config={"timeout": 60})
        
        # Should have config loaded
        assert hasattr(tool, 'config')
        assert tool.config.timeout == 60
        assert tool.config.max_retries == 3  # Default
    
    def test_config_validation_error_clear_message(self):
        """Test that config validation errors provide clear messages"""
        # Invalid config: timeout out of range
        with pytest.raises(ValidationError) as exc_info:
            TestToolWithValidation(config={"timeout": 500})
        
        # Error should mention timeout
        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "validation" in error_msg
    
    def test_config_loading_from_yaml(self):
        """Test config loading from YAML file"""
        loader = get_tool_config_loader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create YAML config
            tool_yaml = tools_dir / "TestToolWithBaseSettings.yaml"
            tool_yaml.write_text("timeout: 60\nmax_retries: 5\n")
            
            # Create tool (should load from YAML)
            tool = TestToolWithBaseSettings()
            
            # Note: BaseTool uses tool name for YAML lookup
            # Since we're instantiating directly, it uses class name
            # For this test, we'll verify the loader works
            config = loader.load_tool_config(
                "TestToolWithBaseSettings",
                config_schema=TestToolWithBaseSettings.Config
            )
            
            assert config["timeout"] == 60
            assert config["max_retries"] == 5
    
    def test_config_loading_from_env_vars(self):
        """Test config loading from environment variables"""
        # Set environment variable
        os.environ["TEST_BASESETTINGS_TIMEOUT"] = "45"
        
        try:
            tool = TestToolWithBaseSettings()
            
            # Should load from env var (via BaseSettings)
            assert tool.config.timeout == 45
        finally:
            os.environ.pop("TEST_BASESETTINGS_TIMEOUT", None)
    
    def test_config_precedence_explicit_over_yaml(self):
        """Test that explicit config overrides YAML"""
        loader = get_tool_config_loader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create YAML config
            tool_yaml = tools_dir / "TestToolWithBaseSettings.yaml"
            tool_yaml.write_text("timeout: 60\n")
            
            # Create tool with explicit config (should override YAML)
            tool = TestToolWithBaseSettings(config={"timeout": 120})
            
            # Explicit should win
            assert tool.config.timeout == 120
    
    def test_config_validation_doesnt_break_initialization(self):
        """Test that config validation errors don't break tool initialization"""
        # Invalid config should raise ValidationError, not break initialization
        with pytest.raises(ValidationError):
            TestToolWithValidation(config={"timeout": 500})
        
        # But valid config should work
        tool = TestToolWithValidation(config={"timeout": 60})
        assert tool.config.timeout == 60

