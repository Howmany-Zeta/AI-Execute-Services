# Tool Creation Workflow

## Overview

This document provides a step-by-step guide for creating new tools in the AIECS system, including schema development requirements and best practices.

## Quick Start

```python
from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any

@register_tool("my_tool")
class MyTool(BaseTool):
    """My tool description"""
    
    # Schema definitions
    class MyOperationSchema(BaseModel):
        """Schema for my_operation"""
        param1: str = Field(description="Parameter 1 description")
        param2: int = Field(default=10, description="Parameter 2 description")
    
    def my_operation(self, param1: str, param2: int = 10) -> Dict[str, Any]:
        """My operation description"""
        # Implementation...
        return {"result": "success"}
```

## Step-by-Step Workflow

### Step 1: Plan Your Tool

- [ ] Define tool purpose and scope
- [ ] Identify required operations/methods
- [ ] Determine input/output types
- [ ] Consider configuration needs
- [ ] Review similar tools for consistency

### Step 2: Create Tool Class Structure

```python
from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

@register_tool("tool_name")
class ToolNameTool(BaseTool):
    """
    Tool description explaining what this tool does.
    """
    
    # Configuration schema (if needed)
    class Config(BaseSettings):
        """Configuration for ToolNameTool"""
        model_config = SettingsConfigDict(env_prefix="TOOL_NAME_")
        
        setting1: str = Field(default="default", description="Setting 1")
        setting2: int = Field(default=100, description="Setting 2")
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize tool with configuration"""
        super().__init__(config, **kwargs)
        # Additional initialization
    
    # Method implementations...
```

### Step 3: Implement Methods with Type Annotations

**Critical:** All methods must have complete type annotations for schema auto-generation.

```python
def operation_name(
    self,
    param1: str,
    param2: int,
    param3: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Operation description.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        param3: Optional description of param3
    
    Returns:
        Description of return value
    """
    # Implementation...
    pass
```

### Step 4: Schema Development

#### Option A: Auto-Generation (Recommended for Simple Cases)

**Requirements:**
- ✅ Complete type annotations
- ✅ Well-documented docstrings (Google/NumPy style)
- ✅ No complex validation needed

**Result:** Schema is automatically generated from method signature and docstring.

#### Option B: Manual Schema (Required for Complex Cases)

**When to use:**
- Complex validation rules
- Field constraints (min/max, length)
- Custom validators
- Enum types

**Implementation:**
```python
class OperationNameSchema(BaseModel):
    """Schema for operation_name operation"""
    
    param1: str = Field(
        description="Description of param1",
        min_length=1,
        max_length=100
    )
    param2: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Description of param2 (1-100, default: 10)"
    )
    param3: Optional[List[str]] = Field(
        default=None,
        description="Optional description of param3"
    )
    
    @field_validator("param1")
    @classmethod
    def validate_param1(cls, v: str) -> str:
        """Custom validation"""
        if not v.strip():
            raise ValueError("param1 cannot be empty")
        return v
```

**See:** [Schema Development Guidelines](./TOOL_SCHEMA_GUIDELINES.md) for detailed guidance.

### Step 5: Schema Development Checklist

Use this checklist for each method:

- [ ] **Method has complete type annotations**
  - All parameters have types
  - Return type is specified
  - Generic types are fully specified (e.g., `List[Dict[str, Any]]`)

- [ ] **Method has well-documented docstring**
  - Google or NumPy style
  - Args section with parameter descriptions
  - Returns section with return value description

- [ ] **Schema decision made**
  - Auto-generation sufficient? → Ensure type annotations and docstrings are complete
  - Manual schema needed? → Create schema following naming convention

- [ ] **If manual schema:**
  - [ ] Schema name follows `{MethodName}Schema` pattern
  - [ ] Schema is inner class
  - [ ] Schema has docstring
  - [ ] All fields have `Field()` with descriptions
  - [ ] Constraints are specified where needed
  - [ ] Custom validators added if needed

- [ ] **Schema quality verified**
  - Run `aiecs tools validate-schemas tool_name`
  - Check coverage ≥ 90%
  - Check description quality ≥ 80%
  - Verify schema works with LangChain adapter

### Step 6: Testing

```python
# Test tool initialization
tool = ToolNameTool()

# Test operations
result = tool.run("operation_name", param1="value", param2=10)

# Test schema validation
from pydantic import ValidationError
try:
    tool.run("operation_name", param1="", param2=-1)  # Should fail
except ValidationError as e:
    print("Validation works!")
```

### Step 7: Documentation

- [ ] Tool class has docstring
- [ ] Each method has docstring
- [ ] Configuration options documented
- [ ] Usage examples provided
- [ ] Error cases documented

### Step 8: Validation and Quality Checks

Run validation commands:

```bash
# Check type annotations
aiecs tools check-annotations tool_name

# Validate schemas
aiecs tools validate-schemas tool_name

# Check schema coverage
aiecs tools schema-coverage tool_name
```

**Target Metrics:**
- Schema coverage: ≥ 90%
- Description quality: ≥ 80%
- Type coverage: 100%

### Step 9: Code Review

Ensure your code review includes:

- [ ] Schema coverage check
- [ ] Schema quality review
- [ ] Type annotation completeness
- [ ] Documentation quality
- [ ] Test coverage

**See:** [Schema Review Guidelines](./TOOL_SCHEMA_GUIDELINES.md#code-review-guidelines)

### Step 10: Integration Testing

- [ ] Test with LangChain adapter
- [ ] Test with Tool Calling Agent
- [ ] Test error handling
- [ ] Test edge cases
- [ ] Performance testing (if applicable)

## Complete Example

```python
from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Any, Optional

@register_tool("example")
class ExampleTool(BaseTool):
    """
    Example tool demonstrating best practices.
    
    This tool provides example operations for demonstration purposes.
    """
    
    # Configuration
    class Config(BaseSettings):
        """Configuration for ExampleTool"""
        model_config = SettingsConfigDict(env_prefix="EXAMPLE_TOOL_")
        
        max_items: int = Field(default=100, description="Maximum items to process")
        timeout: int = Field(default=30, description="Operation timeout in seconds")
    
    # Schema definitions
    class ProcessItemsSchema(BaseModel):
        """Schema for process_items operation"""
        
        items: List[str] = Field(
            description="List of items to process",
            min_length=1
        )
        max_items: Optional[int] = Field(
            default=None,
            ge=1,
            le=1000,
            description="Maximum number of items to process (1-1000). If None, uses tool config default."
        )
        filter_pattern: Optional[str] = Field(
            default=None,
            description="Optional regex pattern to filter items"
        )
        
        @field_validator("items")
        @classmethod
        def validate_items(cls, v: List[str]) -> List[str]:
            """Validate items list"""
            if not v:
                raise ValueError("items list cannot be empty")
            return [item.strip() for item in v if item.strip()]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize ExampleTool"""
        super().__init__(config, **kwargs)
        self.config = self._config_obj if self._config_obj else self.Config()
    
    def process_items(
        self,
        items: List[str],
        max_items: Optional[int] = None,
        filter_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a list of items with optional filtering.
        
        Args:
            items: List of items to process (non-empty)
            max_items: Maximum number of items to process (1-1000). 
                      If None, uses tool configuration default.
            filter_pattern: Optional regex pattern to filter items
        
        Returns:
            Dictionary with processing results:
            - processed: Number of items processed
            - filtered: Number of items filtered (if pattern provided)
            - results: List of processed items
        """
        # Use config default if not provided
        limit = max_items or self.config.max_items
        
        # Filter if pattern provided
        if filter_pattern:
            import re
            pattern = re.compile(filter_pattern)
            filtered_items = [item for item in items if pattern.search(item)]
        else:
            filtered_items = items
        
        # Process items
        processed = filtered_items[:limit]
        
        return {
            "processed": len(processed),
            "filtered": len(items) - len(filtered_items) if filter_pattern else 0,
            "results": processed
        }
```

## Common Patterns

### Pattern 1: File Operations

```python
class ReadFileSchema(BaseModel):
    """Schema for read_file operation"""
    
    file_path: str = Field(description="Path to the file to read")
    encoding: str = Field(default="utf-8", description="File encoding")
    max_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum file size to read in bytes"
    )
```

### Pattern 2: Data Processing

```python
class ProcessDataSchema(BaseModel):
    """Schema for process_data operation"""
    
    data: List[Dict[str, Any]] = Field(
        description="List of records (dictionaries) to process"
    )
    operation: str = Field(
        description="Operation to perform: 'filter', 'transform', or 'aggregate'"
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional operation-specific options"
    )
```

### Pattern 3: API Calls

```python
class FetchDataSchema(BaseModel):
    """Schema for fetch_data operation"""
    
    url: str = Field(description="URL to fetch data from")
    method: str = Field(default="GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional HTTP headers"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds (1-300)"
    )
```

## Troubleshooting

### Schema Not Found

**Problem:** Schema not discovered for method

**Solutions:**
1. Check schema naming: `{MethodName}Schema`
2. Ensure schema is inner class
3. Verify schema inherits from `BaseModel`
4. Check method name matches schema name (case-insensitive, underscores preserved)

### Auto-Generation Not Working

**Problem:** Schema not auto-generated

**Solutions:**
1. Ensure method has complete type annotations
2. Check docstring format (Google or NumPy style)
3. Verify method is public (not starting with `_`)
4. Run `aiecs tools check-annotations` to verify

### Validation Errors

**Problem:** Schema validation fails unexpectedly

**Solutions:**
1. Check field types match method parameter types
2. Verify constraints are appropriate
3. Test with `aiecs tools validate-schemas --verbose`
4. Review validation error messages

## Additional Resources

- [Schema Development Guidelines](./TOOL_SCHEMA_GUIDELINES.md)
- [BaseTool Documentation](./TOOLS_BASE_TOOL.md)
- [Schema Generator Documentation](./TOOLS_SCHEMA_GENERATOR.md)
- [Schema Coverage Pre-commit Hook](./SCHEMA_COVERAGE_PRE_COMMIT.md)

---

**Last Updated:** 2025-01-XX  
**Maintainer:** AIECS Tools Team

