# Tool Configuration Examples

This document provides practical examples of using the standardized tool configuration system.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Configuration Files](#configuration-files)
3. [Environment Variables](#environment-variables)
4. [Explicit Configuration Overrides](#explicit-configuration-overrides)
5. [Custom Configuration Path](#custom-configuration-path)
6. [Configuration Precedence](#configuration-precedence)

## Basic Usage

The simplest way to use tools is with automatic configuration (zero config needed):

```python
from aiecs.tools import get_tool

# Configuration is automatically loaded from:
# 1. YAML config files (config/tools/{tool_name}.yaml)
# 2. Environment variables (from .env files)
# 3. Tool defaults

tool = get_tool("document_parser")
# Tool is configured and ready to use
```

## Configuration Files

### YAML Configuration (Runtime Settings)

Create a YAML file at `config/tools/document_parser_tool.yaml` (or use `examples/config/tools/document_parser_tool.yaml` as a template):

```yaml
# Runtime configuration for DocumentParserTool
timeout: 60  # HTTP request timeout in seconds
user_agent: "DocumentParser/2.0"
max_file_size: 104857600  # 100MB
max_pages: 2000
default_encoding: "utf-8"
temp_dir: "/tmp/document_parser"
enable_cloud_storage: true
gcs_bucket_name: "my-documents-bucket"
# Note: Sensitive values like API keys should be in .env files, not YAML
```

### Environment Variables (Sensitive Settings)

Create a `.env` file in your project root:

```bash
# Document Parser Tool Configuration
# All environment variables use the DOC_PARSER_ prefix
DOC_PARSER_GCS_PROJECT_ID=your-gcs-project-id-here
DOC_PARSER_TEMP_DIR=/custom/temp/path

# Other tool examples:
# SEARCH_TOOL_GOOGLE_API_KEY=your-google-api-key
# APISOURCE_TOOL_FRED_API_KEY=your-fred-api-key
```

**Important**: Never commit actual `.env` files to version control! Use `.env.example` as a template.

## Environment Variables

### Setting Environment Variables

Environment variables are automatically loaded from `.env` files via `python-dotenv`. The configuration loader supports multiple `.env` files:

- `.env` - Base configuration
- `.env.local` - Local development overrides (not committed)
- `.env.production` - Production overrides (loaded when `NODE_ENV=production`)

### Environment Variable Naming

Each tool uses a prefix defined in its `Config` class:

- DocumentParserTool: `DOC_PARSER_` prefix
- SearchTool: `SEARCH_TOOL_` prefix
- APISourceTool: `APISOURCE_TOOL_` prefix

The prefix is automatically stripped when loading into the Config object. For example:
- `DOC_PARSER_TIMEOUT` → `timeout` field
- `DOC_PARSER_GCS_PROJECT_ID` → `gcs_project_id` field

## Explicit Configuration Overrides

You can override configuration at runtime by passing an explicit config dict:

```python
from aiecs.tools import get_tool

# Explicit config takes highest precedence
tool = get_tool(
    "document_parser",
    config={
        "timeout": 120,  # Override timeout
        "max_file_size": 200 * 1024 * 1024,  # Override max file size
        "enable_cloud_storage": False,  # Disable cloud storage
    }
)
```

## Custom Configuration Path

Use a custom directory for configuration files:

```python
from aiecs.config.tool_config import get_tool_config_loader
from aiecs.tools import get_tool

# Set custom config path
loader = get_tool_config_loader()
loader.set_config_path("/custom/config/path")

# Now tools will load config from /custom/config/path/tools/
tool = get_tool("document_parser")

# Reset to default (auto-discover)
loader.set_config_path(None)
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

## Advanced: Custom Loader Instance

For advanced scenarios, you can create a custom `ToolConfigLoader` instance:

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

## Complete Example

See `examples/tool_configuration_examples.py` for a complete working example demonstrating all configuration patterns.

## Migration Guide

For migrating existing tools to use the standardized configuration system, see:
- `docs/developer/TOOLS/MIGRATING_TOOL_CONFIG.md` (to be created)

