"""
Example code demonstrating tool configuration patterns.

This module shows how to use the standardized tool configuration system
with various customization options.
"""

from aiecs.tools import get_tool
from aiecs.config.tool_config import get_tool_config_loader


def example_basic_usage():
    """
    Example 1: Basic usage with automatic configuration (zero config needed).
    
    The tool automatically loads configuration from:
    1. YAML config files (config/tools/document_parser_tool.yaml - see examples/config/tools/ for examples)
    2. Environment variables (from .env files)
    3. Tool defaults
    
    No code changes needed - works out-of-the-box!
    """
    print("=== Example 1: Basic Usage (Automatic Configuration) ===")
    
    # Simply get the tool - configuration is loaded automatically
    tool = get_tool("document_parser")
    
    # Tool is configured and ready to use
    print(f"Tool configured with timeout: {tool.config.timeout}")
    print(f"Tool configured with max_file_size: {tool.config.max_file_size}")
    print()


def example_explicit_config_override():
    """
    Example 2: Explicit config override (highest priority).
    
    Explicit config dict passed to get_tool() takes precedence over
    all other configuration sources (YAML, env vars, defaults).
    """
    print("=== Example 2: Explicit Config Override ===")
    
    # Override specific configuration values
    tool = get_tool(
        "document_parser",
        config={
            "timeout": 120,  # Override timeout to 120 seconds
            "max_file_size": 200 * 1024 * 1024,  # Override max file size to 200MB
            "enable_cloud_storage": False,  # Disable cloud storage
        }
    )
    
    print(f"Tool configured with timeout: {tool.config.timeout} (overridden)")
    print(f"Tool configured with max_file_size: {tool.config.max_file_size} (overridden)")
    print(f"Cloud storage enabled: {tool.config.enable_cloud_storage} (overridden)")
    print()


def example_custom_config_path():
    """
    Example 3: Custom config path.
    
    Use a custom directory for configuration files instead of the
    default config/ directory discovery.
    """
    print("=== Example 3: Custom Config Path ===")
    
    # Set custom config path before getting tools
    loader = get_tool_config_loader()
    loader.set_config_path("/custom/config/path")
    
    # Now tools will load config from /custom/config/path/tools/
    tool = get_tool("document_parser")
    
    print(f"Config path set to: {loader.get_config_path()}")
    print(f"Tool loaded with custom config path")
    print()
    
    # Reset to default (None = auto-discover)
    loader.set_config_path(None)


def example_custom_loader_instance():
    """
    Example 4: Custom loader instance (advanced use case).
    
    Create a custom ToolConfigLoader instance for advanced scenarios
    where you need isolated configuration loading.
    """
    print("=== Example 4: Custom Loader Instance (Advanced) ===")
    
    from aiecs.config.tool_config import ToolConfigLoader
    
    # Create a custom loader instance
    custom_loader = ToolConfigLoader()
    custom_loader.set_config_path("/custom/config/path")
    
    # Use the custom loader to load config manually
    config = custom_loader.load_tool_config(
        tool_name="document_parser",
        config_schema=None,  # Would pass Config class if validating
        explicit_config={"timeout": 90}
    )
    
    print(f"Loaded config: {config}")
    print()


def example_configuration_precedence():
    """
    Example 5: Demonstrating configuration precedence.
    
    Shows how different configuration sources interact and which
    takes precedence.
    """
    print("=== Example 5: Configuration Precedence ===")
    
    # Configuration precedence (highest to lowest):
    # 1. Explicit config dict (passed to get_tool())
    # 2. Tool-specific YAML (config/tools/document_parser_tool.yaml - see examples/config/tools/ for examples)
    # 3. Global YAML (config/tools.yaml)
    # 4. Environment variables (from .env files)
    # 5. Tool defaults (defined in Config class)
    
    # Example: Explicit config overrides everything
    tool1 = get_tool("document_parser", config={"timeout": 999})
    print(f"With explicit config: timeout = {tool1.config.timeout} (explicit wins)")
    
    # Example: YAML config overrides env vars and defaults
    # (Assuming config/tools/document_parser_tool.yaml has timeout: 60 - see examples/config/tools/ for examples)
    tool2 = get_tool("document_parser")
    print(f"Without explicit config: timeout = {tool2.config.timeout} (YAML or default)")
    print()


def example_environment_variables():
    """
    Example 6: Using environment variables.
    
    Shows how to set configuration via environment variables.
    Environment variables are loaded from .env files via dotenv.
    """
    print("=== Example 6: Environment Variables ===")
    
    import os
    
    # Set environment variable (in practice, this would be in .env file)
    # Note: The prefix DOC_PARSER_ is automatically handled by BaseSettings
    os.environ["DOC_PARSER_TIMEOUT"] = "45"
    os.environ["DOC_PARSER_MAX_FILE_SIZE"] = "150000000"  # 150MB
    
    # Get tool - will use environment variables
    tool = get_tool("document_parser")
    
    print(f"Tool configured with timeout from env: {tool.config.timeout}")
    print(f"Tool configured with max_file_size from env: {tool.config.max_file_size}")
    print()
    
    # Clean up
    os.environ.pop("DOC_PARSER_TIMEOUT", None)
    os.environ.pop("DOC_PARSER_MAX_FILE_SIZE", None)


def example_yaml_configuration():
    """
    Example 7: YAML configuration file structure.
    
    Shows what a YAML configuration file looks like and how it's loaded.
    """
    print("=== Example 7: YAML Configuration ===")
    
    # YAML files are automatically discovered in config/tools/ directory
    # Tool-specific: config/tools/document_parser_tool.yaml (see examples/config/tools/ for examples)
    # Global: config/tools.yaml
    
    # The loader walks up the directory tree to find config/ directory
    loader = get_tool_config_loader()
    config_dir = loader.find_config_directory()
    
    print(f"Config directory found at: {config_dir}")
    
    # Load YAML config for a tool
    yaml_config = loader.load_yaml_config("document_parser")
    print(f"YAML config loaded: {yaml_config}")
    print()


if __name__ == "__main__":
    """
    Run all examples to demonstrate tool configuration patterns.
    """
    print("Tool Configuration Examples")
    print("=" * 60)
    print()
    
    try:
        example_basic_usage()
        example_explicit_config_override()
        example_custom_config_path()
        example_custom_loader_instance()
        example_configuration_precedence()
        example_environment_variables()
        example_yaml_configuration()
        
        print("=" * 60)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()

