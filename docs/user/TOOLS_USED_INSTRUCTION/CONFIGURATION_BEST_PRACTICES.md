# Tool Configuration Best Practices

## Use BaseSettings Instead of BaseModel

### Problem Background

AIECS tools use Pydantic for configuration management. In configuration classes, you must use `BaseSettings` instead of `BaseModel`:

**❌ Wrong (will not automatically read environment variables):**
```python
from pydantic import BaseModel, Field, ConfigDict

class Config(BaseModel):
    model_config = ConfigDict(env_prefix="DOC_PARSER_")
    
    gcs_project_id: Optional[str] = Field(default=None)
```

**✅ Correct (automatically reads environment variables):**
```python
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    model_config = ConfigDict(env_prefix="DOC_PARSER_")
    
    gcs_project_id: Optional[str] = Field(default=None)
```

### Key Differences

| Feature | BaseModel | BaseSettings |
|---------|-----------|--------------|
| Source Package | `pydantic` | `pydantic_settings` |
| Environment Variable Reading | ❌ Not Supported | ✅ Automatically Supported |
| Purpose | Data Validation | Configuration Management |
| `.env` File Support | ❌ None | ✅ Yes |

### Why It Matters

When using `get_tool()`, if the configuration class uses `BaseModel`:
- Environment variable `DOC_PARSER_GCS_PROJECT_ID` **will not be read**
- Will use default value `None`
- Causes "GCS project ID not provided" error

When using `BaseSettings`:
- Automatically reads from environment variables
- Supports `.env` files
- Correct configuration priority: code config > environment variables > default values

## Configuration Priority

When using `BaseSettings`, configuration values are resolved in the following priority order (from highest to lowest):

1. **Explicitly passed parameters** (highest priority)
   ```python
   tool = DocumentParserTool(config={'gcs_project_id': 'my-project'})
   ```

2. **Environment Variables**
   ```bash
   export DOC_PARSER_GCS_PROJECT_ID=my-project
   ```

3. **`.env` File**
   ```bash
   # .env
   DOC_PARSER_GCS_PROJECT_ID=my-project
   ```

4. **Default Values** (lowest priority)
   ```python
   gcs_project_id: Optional[str] = Field(default=None)
   ```

## Usage Examples

### Method 1: Using Environment Variables (Recommended)

```python
from dotenv import load_dotenv
load_dotenv()  # Must be called before importing tools

from aiecs.tools import get_tool

# Automatically reads DOC_PARSER_GCS_PROJECT_ID from environment variables
tool = get_tool("document_parser")
print(tool.config.gcs_project_id)  # Output: your-project-id
```

### Method 2: Explicitly Passing Configuration

```python
from aiecs.tools.docs.document_parser_tool import DocumentParserTool

tool = DocumentParserTool(config={
    'gcs_project_id': 'my-project',
    'gcs_bucket_name': 'my-bucket'
})
```

### Method 3: Mixed Usage

```python
# .env file
DOC_PARSER_GCS_BUCKET_NAME=default-bucket

# Code
from dotenv import load_dotenv
load_dotenv()

from aiecs.tools.docs.document_parser_tool import DocumentParserTool

# gcs_bucket_name read from environment variables
# gcs_project_id passed from code (higher priority)
tool = DocumentParserTool(config={
    'gcs_project_id': 'override-project'
})
```

## Dependencies

Ensure `pydantic-settings` is installed:

```bash
pip install pydantic pydantic-settings python-dotenv
```

## Verify Configuration

```python
from dotenv import load_dotenv
load_dotenv()

from aiecs.tools import get_tool

tool = get_tool("document_parser")

# Check if configuration is loaded correctly
print(f"GCS Project ID: {tool.config.gcs_project_id}")
print(f"GCS Bucket: {tool.config.gcs_bucket_name}")
print(f"Enable Cloud Storage: {tool.config.enable_cloud_storage}")
```

## Common Questions

### Q: Why don't environment variables work after using get_tool()?

**A:** Confirm that the configuration class inherits from `BaseSettings` instead of `BaseModel`.

### Q: Variables in .env file are not being read?

**A:** Ensure `load_dotenv()` is called **before** importing tools:

```python
# ✅ Correct order
from dotenv import load_dotenv
load_dotenv()
from aiecs.tools import get_tool

# ❌ Wrong order
from aiecs.tools import get_tool
from dotenv import load_dotenv
load_dotenv()  # Too late!
```

### Q: How to check if a tool uses BaseSettings?

**A:** Check the Config class definition in the tool source code:

```python
# Look in tool file
class Config(BaseSettings):  # ✅ Correct
    ...

class Config(BaseModel):  # ❌ Wrong
    ...
```

## Fixed Tools

The following tools have been updated to use `BaseSettings`:

- ✅ DocumentParserTool
- ✅ DocumentWriterTool  
- ✅ AIDocumentWriterOrchestrator

## Related Documentation

- [Document Parser Tool Configuration](DOCUMENT_PARSER_TOOL_CONFIGURATION.md)
- [Document Writer Tool Configuration](DOCUMENT_WRITER_TOOL_CONFIGURATION.md)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

**Last Updated**: 2025-11-05  
**Maintainer**: AIECS Tools Team
