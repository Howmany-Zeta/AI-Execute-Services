"""
Test fixtures for configuration integration tests.
"""

import os
import tempfile
from pathlib import Path
import pytest
import yaml
from aiecs.config.tool_config import ToolConfigLoader


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()
        tools_dir = config_dir / "tools"
        tools_dir.mkdir()
        
        # Set config path
        loader = ToolConfigLoader()
        loader.set_config_path(config_dir)
        
        yield config_dir
        
        # Cleanup
        loader.set_config_path(None)
        loader._cached_config_dir = None


@pytest.fixture
def env_file_fixture(temp_config_dir):
    """Create .env file fixture"""
    base_dir = temp_config_dir.parent
    env_file = base_dir / ".env"
    
    env_content = """# Test .env file
TEST_TOOL_API_KEY=test-api-key
TEST_TOOL_TIMEOUT=45
TEST_TOOL_MAX_RETRIES=5
"""
    env_file.write_text(env_content)
    
    yield env_file
    
    # Cleanup environment variables
    for key in ["TEST_TOOL_API_KEY", "TEST_TOOL_TIMEOUT", "TEST_TOOL_MAX_RETRIES"]:
        os.environ.pop(key, None)


@pytest.fixture
def env_local_file_fixture(temp_config_dir):
    """Create .env.local file fixture"""
    base_dir = temp_config_dir.parent
    env_local_file = base_dir / ".env.local"
    
    env_local_content = """# Test .env.local file (overrides .env)
TEST_TOOL_TIMEOUT=60
"""
    env_local_file.write_text(env_local_content)
    
    yield env_local_file


@pytest.fixture
def yaml_tool_config_fixture(temp_config_dir):
    """Create tool-specific YAML config fixture"""
    tools_dir = temp_config_dir / "tools"
    tool_yaml = tools_dir / "TestTool.yaml"
    
    yaml_content = {
        "timeout": 60,
        "max_retries": 5,
        "enable_cache": True,
        "cache_ttl": 3600
    }
    
    with open(tool_yaml, "w") as f:
        yaml.dump(yaml_content, f)
    
    yield tool_yaml


@pytest.fixture
def yaml_global_config_fixture(temp_config_dir):
    """Create global YAML config fixture"""
    global_yaml = temp_config_dir / "tools.yaml"
    
    yaml_content = {
        "timeout": 30,
        "max_retries": 3,
        "default_timeout": 30
    }
    
    with open(global_yaml, "w") as f:
        yaml.dump(yaml_content, f)
    
    yield global_yaml


@pytest.fixture
def invalid_yaml_fixture(temp_config_dir):
    """Create invalid YAML file fixture"""
    tools_dir = temp_config_dir / "tools"
    invalid_yaml = tools_dir / "InvalidTool.yaml"
    
    invalid_content = "invalid: yaml: content: [\n"
    invalid_yaml.write_text(invalid_content)
    
    yield invalid_yaml


@pytest.fixture
def complete_config_setup(temp_config_dir):
    """Create complete configuration setup with all files"""
    base_dir = temp_config_dir.parent
    tools_dir = temp_config_dir / "tools"
    
    # Create .env file
    env_file = base_dir / ".env"
    env_file.write_text("TEST_TOOL_API_KEY=env-key\n")
    
    # Create .env.local file
    env_local_file = base_dir / ".env.local"
    env_local_file.write_text("TEST_TOOL_TIMEOUT=45\n")
    
    # Create global YAML
    global_yaml = temp_config_dir / "tools.yaml"
    global_yaml.write_text("max_retries: 3\n")
    
    # Create tool-specific YAML
    tool_yaml = tools_dir / "TestTool.yaml"
    tool_yaml.write_text("timeout: 60\n")
    
    yield {
        "config_dir": temp_config_dir,
        "env_file": env_file,
        "env_local_file": env_local_file,
        "global_yaml": global_yaml,
        "tool_yaml": tool_yaml
    }
    
    # Cleanup
    for key in ["TEST_TOOL_API_KEY", "TEST_TOOL_TIMEOUT"]:
        os.environ.pop(key, None)

