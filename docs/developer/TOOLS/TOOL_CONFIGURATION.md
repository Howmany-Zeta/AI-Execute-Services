# Tool Configuration Developer Guide

This guide explains how to implement tool configuration for developers creating new tools or modifying existing ones.

## Overview

The AIECS framework provides a standardized configuration system that:
- Automatically loads configuration from multiple sources
- Validates configuration against Pydantic schemas
- Separates sensitive credentials from runtime settings
- Provides a consistent pattern across all tools

## Creating Tool Config Classes

### Using BaseSettings (Recommended)

`BaseSettings` is recommended for tool configuration because it automatically loads from environment variables:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class MyTool(BaseTool):
    class Config(BaseSettings):
        """Configuration for MyTool"""
        
        model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
        
        timeout: int = Field(default=30, description="Request timeout in seconds")
        max_retries: int = Field(default=3, description="Maximum retry attempts")
        api_key: Optional[str] = Field(default=None, description="API key")
```

**Benefits:**
- Automatic environment variable loading (via `env_prefix`)
- Works seamlessly with `.env` files (loaded via dotenv)
- Type validation and conversion
- Default values support

### Using BaseModel (Also Supported)

`BaseModel` is also supported, but requires manual environment variable handling:

```python
from pydantic import BaseModel, ConfigDict, Field

class MyTool(BaseTool):
    class Config(BaseModel):
        """Configuration for MyTool"""
        
        model_config = ConfigDict(env_prefix="MY_TOOL_")
        
        timeout: int = Field(default=30)
        max_retries: int = Field(default=3)
```

**Note:** With `BaseModel`, the `ToolConfigLoader` handles all configuration loading, but environment variables won't be automatically loaded into the Config instance. Use `BaseSettings` for automatic env var support.

## BaseSettings vs BaseModel

### When to Use BaseSettings

Use `BaseSettings` when:
- You want automatic environment variable loading
- Your tool needs credentials or API keys (sensitive data)
- You want the convenience of automatic `.env` file support
- You're creating a new tool

**Example:**
```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
    api_key: str  # Automatically loaded from MY_TOOL_API_KEY env var
```

### When to Use BaseModel

Use `BaseModel` when:
- You're migrating an existing tool that already uses BaseModel
- You don't need environment variable support
- You want explicit control over configuration loading
- You're using BaseModel for input validation schemas (separate from Config)

**Example:**
```python
# Config class (for tool configuration)
class Config(BaseModel):
    model_config = ConfigDict(env_prefix="MY_TOOL_")
    timeout: int = 30

# Input validation schema (separate from Config)
class ReadSchema(BaseModel):
    path: str
    encoding: str = "utf-8"
```

## Sensitive vs Runtime Configuration

### Sensitive Configuration (`.env` Files)

Sensitive configuration includes:
- API keys and authentication tokens
- Passwords and secrets
- Database connection strings
- Service URLs with credentials

**Pattern:**
```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
    
    # Sensitive fields - loaded from .env files
    api_key: str = Field(description="API key for external service")
    database_url: str = Field(description="Database connection string")
```

**`.env` file:**
```bash
MY_TOOL_API_KEY=your-api-key-here
MY_TOOL_DATABASE_URL=postgresql://user:pass@host/db
```

### Runtime Configuration (YAML Files)

Runtime configuration includes:
- Timeouts and retry limits
- Feature flags
- Processing limits
- Cache settings
- Logging levels

**Pattern:**
```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
    
    # Runtime fields - can be in YAML or env vars
    timeout: int = Field(default=30, description="Request timeout")
    max_retries: int = Field(default=3, description="Max retry attempts")
    enable_cache: bool = Field(default=True, description="Enable caching")
```

**YAML file (`config/tools/my_tool.yaml`):**
```yaml
timeout: 60
max_retries: 5
enable_cache: true
```

## Schema Validation

The `ToolConfigLoader` automatically validates configuration against your tool's Config schema:

```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
    
    timeout: int = Field(ge=1, le=300, description="Timeout between 1-300 seconds")
    max_retries: int = Field(ge=0, le=10, description="Retries between 0-10")
```

If invalid configuration is provided, a `ValidationError` is raised with clear error messages:

```python
# Invalid config
tool = get_tool("my_tool", config={"timeout": -1})
# Raises: ValidationError: timeout: ensure this value is greater than or equal to 1
```

## Integration with BaseTool

### Automatic Configuration Loading

`BaseTool` automatically handles configuration loading:

```python
class MyTool(BaseTool):
    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
        timeout: int = Field(default=30)
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)  # BaseTool loads config automatically
        
        # Configuration is available via self._config_obj
        self.config = self._config_obj if self._config_obj else self.Config()
```

### Config Class Detection

`BaseTool` automatically detects your Config class using introspection:

```python
def _detect_config_class(self) -> Optional[Type[BaseModel]]:
    """Detect Config class in tool class hierarchy"""
    # Checks self.__class__ and parent classes for Config class
    # Returns Config class if found, None otherwise
```

### Tool Name Resolution

The tool name is used for YAML file discovery:
- Registered name: `get_tool("my_tool")` → looks for `config/tools/my_tool.yaml`
- Class name: `MyTool()` → looks for `config/tools/MyTool.yaml`

## Best Practices

### 1. Use Descriptive Field Names

```python
# Good
timeout: int = Field(default=30, description="HTTP request timeout in seconds")

# Bad
t: int = Field(default=30)
```

### 2. Provide Default Values

```python
# Good - always has a value
timeout: int = Field(default=30)

# Bad - might be None
timeout: Optional[int] = Field(default=None)
```

### 3. Use Field Descriptions

```python
# Good - clear documentation
api_key: str = Field(description="API key for external service")

# Bad - no description
api_key: str
```

### 4. Validate Input Ranges

```python
# Good - validates range
timeout: int = Field(default=30, ge=1, le=300)

# Bad - no validation
timeout: int = Field(default=30)
```

### 5. Separate Sensitive and Runtime Config

```python
# Sensitive config → .env files
api_key: str = Field(description="API key")

# Runtime config → YAML files (but can also be in .env)
timeout: int = Field(default=30, description="Timeout")
```

### 6. Use Appropriate Types

```python
# Good - specific types
timeout: int = Field(default=30)
enable_cache: bool = Field(default=True)
max_items: int = Field(default=100)

# Bad - all strings
timeout: str = Field(default="30")
enable_cache: str = Field(default="true")
```

## Example: Complete Tool Configuration

```python
from typing import Optional, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool

@register_tool("my_tool")
class MyTool(BaseTool):
    """Example tool with complete configuration"""
    
    class Config(BaseSettings):
        """Configuration for MyTool
        
        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/my_tool.yaml)
        3. Environment variables (from .env files)
        4. Tool defaults (lowest priority)
        """
        
        model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
        
        # Sensitive configuration (from .env)
        api_key: str = Field(description="API key for external service")
        database_url: Optional[str] = Field(
            default=None,
            description="Database connection URL"
        )
        
        # Runtime configuration (from YAML or .env)
        timeout: int = Field(
            default=30,
            ge=1,
            le=300,
            description="Request timeout in seconds"
        )
        max_retries: int = Field(
            default=3,
            ge=0,
            le=10,
            description="Maximum retry attempts"
        )
        enable_cache: bool = Field(
            default=True,
            description="Enable response caching"
        )
        cache_ttl: int = Field(
            default=3600,
            ge=0,
            description="Cache TTL in seconds"
        )
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize MyTool with configuration"""
        super().__init__(config)
        
        # Configuration is automatically loaded by BaseTool
        self.config = self._config_obj if self._config_obj else self.Config()
        
        # Initialize tool with config
        self._initialize()
    
    def _initialize(self):
        """Initialize tool components"""
        # Use self.config values
        self.timeout = self.config.timeout
        self.max_retries = self.config.max_retries
        # ... rest of initialization
```

## Configuration File Examples

### YAML Configuration (`config/tools/my_tool.yaml`)

```yaml
# Runtime configuration for MyTool
timeout: 60
max_retries: 5
enable_cache: true
cache_ttl: 7200
```

### Environment Variables (`.env`)

```bash
# Sensitive configuration
MY_TOOL_API_KEY=your-api-key-here
MY_TOOL_DATABASE_URL=postgresql://user:pass@host/db

# Runtime configuration (can override YAML)
MY_TOOL_TIMEOUT=45
MY_TOOL_ENABLE_CACHE=false
```

## Error Handling

### Validation Errors

Configuration validation errors are raised as `ValidationError`:

```python
from pydantic import ValidationError

try:
    tool = get_tool("my_tool", config={"timeout": -1})
except ValidationError as e:
    print(f"Configuration error: {e}")
    # Output: Configuration error: timeout: ensure this value is greater than or equal to 1
```

### Missing Configuration

Missing required fields raise validation errors:

```python
# If api_key is required but not provided
try:
    tool = get_tool("my_tool")
except ValidationError as e:
    print(f"Missing required configuration: {e}")
```

### Invalid YAML

Invalid YAML files are logged as warnings and skipped:

```yaml
# Invalid YAML (missing colon)
timeout 60
```

The loader logs a warning and continues with defaults or other sources.

## Testing Configuration

### Unit Testing

```python
def test_tool_configuration():
    """Test tool configuration loading"""
    # Test with explicit config
    tool = MyTool(config={"timeout": 60})
    assert tool.config.timeout == 60
    
    # Test with environment variable
    import os
    os.environ["MY_TOOL_TIMEOUT"] = "45"
    tool = MyTool()
    assert tool.config.timeout == 45
    os.environ.pop("MY_TOOL_TIMEOUT", None)
```

### Integration Testing

```python
def test_yaml_configuration():
    """Test YAML configuration loading"""
    # Create test YAML file
    yaml_path = Path("config/tools/my_tool.yaml")
    yaml_path.write_text("timeout: 90\n")
    
    # Load tool
    tool = MyTool()
    assert tool.config.timeout == 90
    
    # Cleanup
    yaml_path.unlink()
```

## Related Documentation

- [User Tool Configuration Guide](../../user/TOOLS/TOOL_CONFIGURATION.md) - User-facing guide
- [Tool Configuration Examples](./TOOL_CONFIGURATION_EXAMPLES.md) - Complete code examples
- [Migrating Tool Configuration](./MIGRATING_TOOL_CONFIG.md) - Migration guide

