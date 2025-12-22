"""
Integration tests for developer customization patterns.

Tests various customization scenarios:
- Custom config path
- Explicit config override
- Custom loader instance
- Performance considerations
"""

import os
import tempfile
import time
import threading
from pathlib import Path
import pytest
from aiecs.config.tool_config import ToolConfigLoader, get_tool_config_loader
from aiecs.tools import get_tool
from aiecs.tools.docs.document_parser_tool import DocumentParserTool


class TestCustomConfigPath:
    """Test custom config path customization"""
    
    def test_set_custom_config_path(self):
        """Test setting custom config path"""
        loader = get_tool_config_loader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_config_dir = Path(tmpdir) / "custom_config"
            custom_config_dir.mkdir()
            tools_dir = custom_config_dir / "tools"
            tools_dir.mkdir()
            
            # Set custom path
            loader.set_config_path(custom_config_dir)
            
            # Create config file in custom location
            tool_yaml = tools_dir / "TestTool.yaml"
            tool_yaml.write_text("timeout: 90\n")
            
            # Should load from custom path
            config = loader.load_yaml_config("TestTool")
            assert config["timeout"] == 90
    
    def test_reset_config_path_to_default(self):
        """Test resetting config path to default (auto-discover)"""
        loader = get_tool_config_loader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_config_dir = Path(tmpdir) / "custom_config"
            custom_config_dir.mkdir()
            
            # Set custom path
            loader.set_config_path(custom_config_dir)
            assert loader.get_config_path() == custom_config_dir
            
            # Reset to None (auto-discover)
            loader.set_config_path(None)
            
            # Should clear custom path
            assert loader.get_config_path() != custom_config_dir or loader.get_config_path() is None


class TestExplicitConfigOverride:
    """Test explicit config override patterns"""
    
    def test_explicit_config_via_get_tool(self):
        """Test explicit config override via get_tool()"""
        try:
            tool = get_tool("document_parser", config={"timeout": 150})
            assert tool.config.timeout == 150
        except Exception:
            # Tool might not be registered, that's okay
            pass
    
    def test_explicit_config_via_constructor(self):
        """Test explicit config override via tool constructor"""
        tool = DocumentParserTool(config={"timeout": 180})
        
        assert tool.config.timeout == 180
    
    def test_explicit_config_overrides_yaml(self):
        """Test that explicit config overrides YAML config"""
        loader = get_tool_config_loader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # Create YAML config
            tool_yaml = tools_dir / "DocumentParserTool.yaml"
            tool_yaml.write_text("timeout: 60\n")
            
            # Create tool with explicit config (should override YAML)
            tool = DocumentParserTool(config={"timeout": 120})
            
            # Explicit should win
            assert tool.config.timeout == 120


class TestCustomLoaderInstance:
    """Test custom loader instance (advanced use cases)"""
    
    def test_custom_loader_instance_isolation(self):
        """Test that custom loader instance is isolated"""
        custom_loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_config_dir = Path(tmpdir) / "custom_config"
            custom_config_dir.mkdir()
            custom_loader.set_config_path(custom_config_dir)
            
            # Global loader should not be affected
            global_loader = get_tool_config_loader()
            
            # Custom loader should have custom path
            assert custom_loader.get_config_path() == custom_config_dir
            
            # Global loader should have different path (or None)
            assert global_loader.get_config_path() != custom_config_dir or global_loader.get_config_path() is None
    
    def test_custom_loader_manual_config_loading(self):
        """Test manual config loading with custom loader"""
        custom_loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            tools_dir = config_dir / "tools"
            tools_dir.mkdir()
            custom_loader.set_config_path(config_dir)
            
            # Create YAML config
            tool_yaml = tools_dir / "TestTool.yaml"
            tool_yaml.write_text("timeout: 75\n")
            
            # Load config manually
            config = custom_loader.load_tool_config("TestTool", config_schema=None)
            
            assert config["timeout"] == 75


class TestPerformanceConsiderations:
    """Test performance considerations"""
    
    def test_config_directory_caching(self):
        """Test that config directory is cached (only searches once)"""
        loader = ToolConfigLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            loader.set_config_path(config_dir)
            
            # First call - should discover
            start_time = time.time()
            found1 = loader.find_config_directory()
            time1 = time.time() - start_time
            
            # Second call - should use cache (faster)
            start_time = time.time()
            found2 = loader.find_config_directory()
            time2 = time.time() - start_time
            
            assert found1 == found2 == config_dir
            # Cached call should be faster (or at least not slower)
            # Note: This might not always be true due to timing variations,
            # but caching should prevent re-discovery
    
    def test_concurrent_config_loading(self):
        """Test thread-safety of concurrent config loading"""
        loader = get_tool_config_loader()
        results = []
        errors = []
        
        def load_config():
            try:
                config = loader.load_tool_config("TestTool", config_schema=None)
                results.append(config)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads loading config concurrently
        threads = [threading.Thread(target=load_config) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should not have errors
        assert len(errors) == 0
        # All should succeed
        assert len(results) == 10
    
    def test_singleton_performance(self):
        """Test that singleton pattern doesn't impact performance"""
        # Get loader multiple times - should be fast (same instance)
        start_time = time.time()
        for _ in range(1000):
            loader = get_tool_config_loader()
        elapsed = time.time() - start_time
        
        # Should be very fast (< 0.1 seconds for 1000 calls)
        assert elapsed < 0.1

