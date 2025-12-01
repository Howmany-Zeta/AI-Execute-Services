# Tool Configuration Guide

This guide explains how to configure tools in the AIECS framework. The configuration system works automatically out-of-the-box, requiring zero configuration for basic use cases.

## Overview

The AIECS framework provides a unified configuration system for all tools that:

- **Works automatically** - No configuration needed for basic usage
- **Supports multiple sources** - YAML files, environment variables, and explicit overrides
- **Separates concerns** - Sensitive credentials in `.env` files, runtime settings in YAML
- **Follows precedence rules** - Clear order of configuration priority
- **Validates automatically** - Schema validation ensures correct configuration

The configuration system is similar to the existing `LLMConfigLoader` pattern, providing consistency across the framework.

## Quick Start

The simplest way to use tools is with automatic configuration:

```python
from aiecs.tools import get_tool

# Configuration is automatically loaded - no code needed!
tool = get_tool("document_parser")

# Tool is ready to use
result = tool.parse_document("https://example.com/document.pdf")
```

That's it! The tool automatically loads configuration from:
1. YAML config files (`examples/config/tools/document_parser_tool.yaml` - example)
2. Environment variables (from `.env` files)
3. Tool defaults (defined in the tool's Config class)

## Framework-Provided Utilities

The framework provides a singleton configuration loader accessible via:

```python
from aiecs.config.tool_config import get_tool_config_loader

loader = get_tool_config_loader()
```

The loader follows a singleton pattern, ensuring consistent configuration loading across your application.

## Configuration File Structure

### Sensitive Configuration: `.env` Files

Sensitive configuration (API keys, passwords, credentials) should be stored in `.env` files:

```bash
# .env file
DOC_PARSER_GCS_PROJECT_ID=your-project-id
SEARCH_TOOL_GOOGLE_API_KEY=your-api-key
APISOURCE_TOOL_FRED_API_KEY=your-fred-key
```

**Important**: Never commit `.env` files to version control! Use `.env.example` as a template.

The configuration loader supports multiple `.env` files:
- `.env` - Base configuration
- `.env.local` - Local development overrides (not committed)
- `.env.production` - Production overrides (loaded when `NODE_ENV=production`)

Later files override earlier ones.

### Runtime Configuration: YAML Files

Runtime configuration (timeouts, limits, feature flags) should be stored in YAML files:

**Tool-specific**: `config/tools/{tool_name}.yaml`
```yaml
# examples/config/tools/document_parser_tool.yaml (example)
timeout: 60
max_file_size: 104857600
max_pages: 2000
enable_cloud_storage: true
```

**Global**: `config/tools.yaml` (applies to all tools)
```yaml
# config/tools.yaml
default_timeout: 30
default_max_file_size: 52428800
```

## Configuration Precedence

Configuration values are loaded in this order (highest to lowest priority):

1. **Explicit config dict** - Passed to `get_tool()` or tool constructor
2. **Tool-specific YAML** - `config/tools/{tool_name}.yaml`
3. **Global YAML** - `config/tools.yaml`
4. **Environment variables** - From `.env` files (loaded via dotenv)
5. **Tool defaults** - Defined in Config class `Field` defaults

### Example: Precedence Demonstration

```python
# Assume:
# - YAML file has timeout: 60
# - Environment variable DOC_PARSER_TIMEOUT=45
# - Tool default timeout: 30

# Case 1: Explicit config wins
tool1 = get_tool("document_parser", config={"timeout": 120})
print(tool1.config.timeout)  # Output: 120 (explicit wins)

# Case 2: YAML wins over env vars and defaults
tool2 = get_tool("document_parser")
print(tool2.config.timeout)  # Output: 60 (YAML wins)
```

## Config Directory Discovery

The configuration loader automatically discovers the `config/` directory by:

1. **Custom path** - Set via `get_tool_config_loader().set_config_path()`
2. **Settings** - From `aiecs.config.config` settings (if `tool_config_path` is set)
3. **Environment variable** - `TOOL_CONFIG_PATH` environment variable
4. **Walking up directory tree** - Starting from current working directory
5. **Fallback** - Checks `aiecs/config/` directory

The discovered directory is cached for performance (only searches once).

## Optional Customization

### Custom Config Path

Use a custom directory for configuration files:

```python
from aiecs.config.tool_config import get_tool_config_loader
from aiecs.tools import get_tool

# Set custom config path
loader = get_tool_config_loader()
loader.set_config_path("/custom/config/path")

# Now tools load config from /custom/config/path/tools/
tool = get_tool("document_parser")

# Reset to default (auto-discover)
loader.set_config_path(None)
```

### Explicit Config Override

Override configuration at runtime:

```python
from aiecs.tools import get_tool

# Explicit config takes highest precedence
tool = get_tool(
    "document_parser",
    config={
        "timeout": 120,
        "max_file_size": 200 * 1024 * 1024,
        "enable_cloud_storage": False,
    }
)
```

### Custom Loader Instance (Advanced)

For advanced scenarios, create a custom loader instance:

```python
from aiecs.config.tool_config import ToolConfigLoader

# Create custom loader
custom_loader = ToolConfigLoader()
custom_loader.set_config_path("/custom/path")

# Load config manually
config = custom_loader.load_tool_config(
    tool_name="document_parser",
    config_schema=None,  # Pass Config class if validating
    explicit_config={"timeout": 90}
)
```

## Environment Variables

### Naming Convention

Each tool uses a prefix defined in its `Config` class:

- DocumentParserTool: `DOC_PARSER_` prefix
- SearchTool: `SEARCH_TOOL_` prefix
- APISourceTool: `APISOURCE_TOOL_` prefix

The prefix is automatically stripped when loading into the Config object:

- `DOC_PARSER_TIMEOUT` → `timeout` field
- `DOC_PARSER_GCS_PROJECT_ID` → `gcs_project_id` field

### Setting Environment Variables

Environment variables are automatically loaded from `.env` files via `python-dotenv`. You can also set them directly:

```python
import os

# Set environment variable
os.environ["DOC_PARSER_TIMEOUT"] = "45"

# Get tool - will use environment variable
tool = get_tool("document_parser")
```

## Examples

### Basic Usage (Automatic Configuration)

```python
from aiecs.tools import get_tool

# Zero configuration needed - works out-of-the-box!
tool = get_tool("document_parser")
result = tool.parse_document("document.pdf")
```

### With YAML Configuration

Create `config/tools/document_parser_tool.yaml` (or use `examples/config/tools/document_parser_tool.yaml` as a template):
```yaml
timeout: 60
max_file_size: 104857600
```

Use the tool:
```python
from aiecs.tools import get_tool

# Automatically loads from YAML
tool = get_tool("document_parser")
print(tool.config.timeout)  # Output: 60
```

### With Environment Variables

Create `.env` file:
```bash
DOC_PARSER_GCS_PROJECT_ID=my-project-id
DOC_PARSER_TIMEOUT=45
```

Use the tool:
```python
from aiecs.tools import get_tool

# Automatically loads from .env
tool = get_tool("document_parser")
print(tool.config.gcs_project_id)  # Output: my-project-id
```

### With Explicit Override

```python
from aiecs.tools import get_tool

# Explicit config overrides everything
tool = get_tool(
    "document_parser",
    config={"timeout": 120}
)
print(tool.config.timeout)  # Output: 120
```

## Best Practices

1. **Sensitive data in `.env`** - Never put API keys or passwords in YAML files
2. **Runtime settings in YAML** - Use YAML for timeouts, limits, feature flags
3. **Use `.env.example`** - Provide a template for other developers
4. **Don't commit `.env`** - Add `.env` to `.gitignore`
5. **Use explicit config sparingly** - Prefer YAML/env vars for maintainability
6. **Document your config** - Add comments in YAML files explaining settings

## Troubleshooting

### Configuration Not Loading

If configuration isn't loading as expected:

1. **Check config directory** - Verify `config/tools/` directory exists
2. **Check file names** - Ensure YAML files match tool names exactly
3. **Check environment variables** - Verify `.env` file is in the right location
4. **Check precedence** - Remember explicit config overrides everything

### Debug Configuration Loading

```python
from aiecs.config.tool_config import get_tool_config_loader

loader = get_tool_config_loader()
config_dir = loader.find_config_directory()
print(f"Config directory: {config_dir}")

# Load config manually to see what's loaded
config = loader.load_tool_config("document_parser")
print(f"Loaded config: {config}")
```

## Related Documentation

- [Developer Tool Configuration Guide](../developer/TOOLS/TOOL_CONFIGURATION.md) - Advanced usage and implementation details
- [Tool Configuration Examples](../developer/TOOLS/TOOL_CONFIGURATION_EXAMPLES.md) - Complete code examples
- [Migrating Tool Configuration](../developer/TOOLS/MIGRATING_TOOL_CONFIG.md) - Migration guide for existing tools

