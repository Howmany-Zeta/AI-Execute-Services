# Migrating Tool Configuration

This guide explains how to migrate existing tools to use the standardized configuration system.

## Migration Overview

The migration process involves:
1. Migrating from `BaseModel` to `BaseSettings` (Category 2 tools)
2. Adding Config classes to tools without them (Category 3 tools)
3. Moving hardcoded values to YAML files
4. Replacing `os.getenv()` calls with BaseSettings
5. Ensuring backward compatibility

## Migration Categories

### Category 1: Already Using BaseSettings ✅

Tools already using `BaseSettings` correctly need no changes. They automatically benefit from the new configuration system.

**Example:**
```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOL_")
    timeout: int = Field(default=30)
```

**Action:** None required - already correct!

### Category 2: Using BaseModel with env_prefix ⚠️

Tools using `BaseModel` with `env_prefix` need to migrate to `BaseSettings` for automatic environment variable loading.

**Before:**
```python
from pydantic import BaseModel, ConfigDict

class Config(BaseModel):
    model_config = ConfigDict(env_prefix="TOOL_")
    timeout: int = Field(default=30)
    
    def __init__(self, **kwargs):
        # Manual env var loading needed
        super().__init__(**kwargs)
```

**After:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOL_")
    timeout: int = Field(default=30)
    # Automatic env var loading - no manual code needed!
```

**Migration Steps:**
1. Change import: `from pydantic import BaseModel, ConfigDict` → `from pydantic_settings import BaseSettings, SettingsConfigDict`
2. Change class: `class Config(BaseModel):` → `class Config(BaseSettings):`
3. Change config: `ConfigDict(env_prefix="...")` → `SettingsConfigDict(env_prefix="...")`
4. Remove manual env var loading code from `__init__`
5. Update tool `__init__` to use `self._config_obj` from BaseTool

### Category 3: No Config Class ❌

Tools without a Config class need to add one.

**Before:**
```python
class MyTool(BaseTool):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # Hardcoded defaults
        self.timeout = 30
        self.max_retries = 3
```

**After:**
```python
class MyTool(BaseTool):
    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
        timeout: int = Field(default=30)
        max_retries: int = Field(default=3)
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.config = self._config_obj if self._config_obj else self.Config()
        # Use self.config.timeout instead of hardcoded value
```

**Migration Steps:**
1. Create Config class inheriting from `BaseSettings`
2. Define configuration fields with appropriate types and defaults
3. Use `SettingsConfigDict(env_prefix="TOOL_NAME_")` for environment variable support
4. Update tool `__init__` to use `self.config` values

### Category 4: Direct os.getenv() Usage 🔴

Tools using direct `os.getenv()` calls need to migrate to BaseSettings.

**Before:**
```python
import os

def __init__(self):
    api_key = os.getenv("MY_TOOL_API_KEY")
    timeout = int(os.getenv("MY_TOOL_TIMEOUT", "30"))
```

**After:**
```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
    api_key: str = Field(description="API key")
    timeout: int = Field(default=30)

def __init__(self, config: Optional[Dict] = None):
    super().__init__(config)
    self.config = self._config_obj if self._config_obj else self.Config()
    # Use self.config.api_key instead of os.getenv()
```

**Migration Steps:**
1. Identify all `os.getenv()` calls
2. Add corresponding fields to Config class
3. Replace `os.getenv()` calls with `self.config.field_name`
4. Ensure sensitive values use `.env` files

## Step-by-Step Migration Examples

### Example 1: Migrating BaseModel to BaseSettings

**Original Code:**
```python
from pydantic import BaseModel, ConfigDict, Field
from aiecs.tools.base_tool import BaseTool

class MyTool(BaseTool):
    class Config(BaseModel):
        model_config = ConfigDict(env_prefix="MY_TOOL_")
        timeout: int = Field(default=30)
        max_retries: int = Field(default=3)
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # Manual config parsing
        if config:
            self.config = self.Config(**config)
        else:
            # Manual env var loading needed
            import os
            env_config = {}
            for key, value in os.environ.items():
                if key.startswith("MY_TOOL_"):
                    field_name = key.replace("MY_TOOL_", "").lower()
                    env_config[field_name] = value
            self.config = self.Config(**env_config)
```

**Migrated Code:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from aiecs.tools.base_tool import BaseTool

class MyTool(BaseTool):
    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
        timeout: int = Field(default=30)
        max_retries: int = Field(default=3)
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)  # BaseTool handles everything!
        
        # Configuration is automatically loaded by BaseTool
        self.config = self._config_obj if self._config_obj else self.Config()
```

**Changes:**
1. ✅ Changed import to `pydantic_settings`
2. ✅ Changed `BaseModel` to `BaseSettings`
3. ✅ Changed `ConfigDict` to `SettingsConfigDict`
4. ✅ Removed manual env var loading code
5. ✅ Simplified `__init__` to use `self._config_obj`

### Example 2: Adding Config Class to Tool Without One

**Original Code:**
```python
class MyTool(BaseTool):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # Hardcoded configuration
        self.timeout = 30
        self.max_retries = 3
        self.api_key = None  # No way to configure
```

**Migrated Code:**
```python
class MyTool(BaseTool):
    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
        timeout: int = Field(default=30, description="Request timeout")
        max_retries: int = Field(default=3, description="Max retries")
        api_key: Optional[str] = Field(default=None, description="API key")
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        # Configuration is automatically loaded
        self.config = self._config_obj if self._config_obj else self.Config()
        
        # Use config values instead of hardcoded
        self.timeout = self.config.timeout
        self.max_retries = self.config.max_retries
        self.api_key = self.config.api_key
```

**Changes:**
1. ✅ Added Config class with BaseSettings
2. ✅ Defined all configuration fields
3. ✅ Updated `__init__` to use `self.config` values
4. ✅ Removed hardcoded defaults

### Example 3: Replacing os.getenv() Calls

**Original Code:**
```python
import os

class MyTool(BaseTool):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # Direct os.getenv() calls
        self.api_key = os.getenv("MY_TOOL_API_KEY")
        self.timeout = int(os.getenv("MY_TOOL_TIMEOUT", "30"))
```

**Migrated Code:**
```python
class MyTool(BaseTool):
    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
        api_key: Optional[str] = Field(default=None, description="API key")
        timeout: int = Field(default=30, description="Request timeout")
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        # Configuration loaded automatically from .env files
        self.config = self._config_obj if self._config_obj else self.Config()
        
        # Use config values instead of os.getenv()
        self.api_key = self.config.api_key
        self.timeout = self.config.timeout
```

**Changes:**
1. ✅ Added Config class with fields for all env vars
2. ✅ Replaced `os.getenv()` calls with `self.config.field_name`
3. ✅ Environment variables now loaded from `.env` files automatically

## Moving Hardcoded Values to YAML

### Before: Hardcoded Values

```python
class MyTool(BaseTool):
    def __init__(self):
        self.timeout = 30  # Hardcoded
        self.max_items = 100  # Hardcoded
```

### After: YAML Configuration

**Code:**
```python
class MyTool(BaseTool):
    class Config(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="MY_TOOL_")
        timeout: int = Field(default=30)  # Default, can be overridden
        max_items: int = Field(default=100)  # Default, can be overridden
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.config = self._config_obj if self._config_obj else self.Config()
        self.timeout = self.config.timeout
        self.max_items = self.config.max_items
```

**YAML (`config/tools/my_tool.yaml`):**
```yaml
timeout: 60  # Override default
max_items: 200  # Override default
```

## Backward Compatibility Considerations

### Existing Configuration Patterns

The new system maintains backward compatibility with:
- `TOOL_CONFIGS` dictionary (explicit config passed to `get_tool()`)
- Tools without Config classes (uses defaults)
- Direct tool instantiation (works as before)

### Migration Strategy

1. **Phase 1**: Add Config class without breaking existing code
2. **Phase 2**: Migrate to BaseSettings gradually
3. **Phase 3**: Move hardcoded values to YAML
4. **Phase 4**: Remove deprecated patterns

### Testing Backward Compatibility

```python
# Old way still works
tool = MyTool(config={"timeout": 60})

# New way also works
tool = get_tool("my_tool", config={"timeout": 60})

# YAML config works
# config/tools/my_tool.yaml: timeout: 60
tool = get_tool("my_tool")
assert tool.config.timeout == 60
```

## Common Migration Issues

### Issue 1: Environment Variables Not Loading

**Problem:** Environment variables aren't being loaded after migration.

**Solution:** Ensure you're using `BaseSettings` (not `BaseModel`) and that `.env` files are in the correct location.

```python
# Wrong - BaseModel doesn't auto-load env vars
class Config(BaseModel):
    model_config = ConfigDict(env_prefix="TOOL_")

# Correct - BaseSettings auto-loads env vars
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOL_")
```

### Issue 2: Config Validation Errors

**Problem:** Getting validation errors after migration.

**Solution:** Ensure all required fields have defaults or are provided in config:

```python
# Wrong - required field without default
api_key: str

# Correct - optional with default
api_key: Optional[str] = Field(default=None)

# Or provide default
api_key: str = Field(default="")
```

### Issue 3: YAML Config Not Loading

**Problem:** YAML configuration isn't being loaded.

**Solution:** Check that:
1. `config/tools/` directory exists
2. YAML file name matches tool name exactly
3. YAML syntax is valid
4. Config directory is discoverable (check `loader.find_config_directory()`)

## Migration Checklist

Use this checklist when migrating a tool:

- [ ] Identify tool category (1, 2, 3, or 4)
- [ ] Update imports (`pydantic_settings` for BaseSettings)
- [ ] Change Config class (BaseModel → BaseSettings if needed)
- [ ] Update ConfigDict → SettingsConfigDict
- [ ] Remove manual env var loading code
- [ ] Update tool `__init__` to use `self._config_obj`
- [ ] Replace `os.getenv()` calls with Config fields
- [ ] Move hardcoded values to Config class defaults
- [ ] Create YAML config file (if needed)
- [ ] Update `.env.example` file (if needed)
- [ ] Test with explicit config
- [ ] Test with YAML config
- [ ] Test with environment variables
- [ ] Test backward compatibility
- [ ] Update documentation

## Related Documentation

- [Developer Tool Configuration Guide](./TOOL_CONFIGURATION.md) - Complete developer guide
- [Tool Configuration Examples](./TOOL_CONFIGURATION_EXAMPLES.md) - Code examples
- [User Tool Configuration Guide](../../user/TOOLS/TOOL_CONFIGURATION.md) - User-facing guide

