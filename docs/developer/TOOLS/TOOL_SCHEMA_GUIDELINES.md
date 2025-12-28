# Tool Schema Development Guidelines

## Overview

This document provides comprehensive guidelines for developing schemas for AIECS tools. Schemas are Pydantic models that define the input validation, type safety, and documentation for tool methods. Following these guidelines ensures consistency, quality, and maintainability across all tools.

## Table of Contents

1. [When to Use Manual Schemas vs Auto-Generation](#when-to-use-manual-schemas-vs-auto-generation)
2. [Schema Naming Conventions](#schema-naming-conventions)
3. [Best Practices for Schema Field Descriptions](#best-practices-for-schema-field-descriptions)
4. [Type Annotation Requirements for Auto-Generation](#type-annotation-requirements-for-auto-generation)
5. [Examples of Good vs Bad Schemas](#examples-of-good-vs-bad-schemas)
6. [Schema Development Checklist](#schema-development-checklist)
7. [Code Review Guidelines](#code-review-guidelines)

---

## When to Use Manual Schemas vs Auto-Generation

### Auto-Generation (Recommended Default)

**Use auto-generation when:**
- ✅ Method has complete type annotations
- ✅ Method has well-documented docstrings (Google or NumPy style)
- ✅ Parameters are straightforward (no complex validation rules)
- ✅ Default values are simple (primitives, None)
- ✅ No custom field validators needed

**Advantages:**
- Zero maintenance overhead
- Automatic synchronization with method signature
- Consistent with code changes
- Fast development

**Example:**
```python
def filter(self, records: List[Dict[str, Any]], condition: str) -> List[Dict[str, Any]]:
    """
    Filter DataFrame based on a condition.
    
    Args:
        records: List of records to filter
        condition: Filter condition using pandas query syntax (e.g., 'age > 30')
    
    Returns:
        Filtered list of records
    """
    # Implementation...
```

This will automatically generate `FilterSchema` with proper field types and descriptions.

### Manual Schemas (Required for Complex Cases)

**Use manual schemas when:**
- ❌ Complex validation rules (e.g., regex patterns, custom validators)
- ❌ Field constraints (min/max values, string length limits)
- ❌ Complex default values (computed defaults, factory functions)
- ❌ Cross-field validation (one field depends on another)
- ❌ Union types with specific constraints
- ❌ Enum types with specific values
- ❌ Custom field serialization/deserialization

**Example:**
```python
class SearchWebSchema(BaseModel):
    """Schema for search_web operation"""
    
    query: str = Field(
        description="Search query string",
        min_length=1,
        max_length=500
    )
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results to return (1-100)"
    )
    safe_search: str = Field(
        default="medium",
        description="Safe search level: 'off', 'medium', or 'high'"
    )
    
    @field_validator("safe_search")
    @classmethod
    def validate_safe_search(cls, v: str) -> str:
        """Validate safe search level"""
        allowed = ["off", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"safe_search must be one of {allowed}")
        return v
```

### Decision Flowchart

```
Start
  │
  ├─ Has complex validation? ──YES──> Use Manual Schema
  │
  ├─ Has field constraints? ──YES──> Use Manual Schema
  │
  ├─ Has complete type annotations? ──NO──> Add type annotations first
  │
  ├─ Has good docstrings? ──NO──> Improve docstrings first
  │
  └─ All simple? ──YES──> Use Auto-Generation ✅
```

---

## Schema Naming Conventions

### Pattern: `{MethodName}Schema`

**Rule:** Schema class name = Method name (PascalCase) + "Schema"

**Examples:**
- Method: `read_csv` → Schema: `Read_csvSchema`
- Method: `filter_data` → Schema: `Filter_dataSchema`
- Method: `group_by` → Schema: `Group_bySchema`

**Important:** Preserve underscores in method names to maintain consistency with method discovery.

### Location: Inner Classes

**Best Practice:** Define schemas as inner classes within the tool class.

```python
@register_tool("pandas")
class PandasTool(BaseTool):
    # Schema definitions
    class Read_csvSchema(BaseModel):
        """Schema for read_csv operation"""
        csv_str: str = Field(description="CSV string content to read")
    
    class FilterSchema(BaseModel):
        """Schema for filter operation"""
        records: List[Dict[str, Any]] = Field(description="List of records to filter")
        condition: str = Field(description="Filter condition")
    
    def read_csv(self, csv_str: str) -> List[Dict[str, Any]]:
        """Read CSV string into DataFrame"""
        # Implementation...
    
    def filter(self, records: List[Dict[str, Any]], condition: str) -> List[Dict[str, Any]]:
        """Filter DataFrame based on condition"""
        # Implementation...
```

### Why Inner Classes?

1. **Namespace Organization**: Keeps schemas close to their methods
2. **Automatic Discovery**: BaseTool automatically discovers inner Schema classes
3. **Clear Ownership**: Makes it obvious which schema belongs to which tool
4. **Avoid Conflicts**: Prevents naming conflicts across tools

### Alternative: Module-Level Schemas (Legacy)

For tools with many schemas, you can define them in a separate `schemas.py` file:

```python
# search_tool/schemas.py
class SearchWebSchema(BaseModel):
    """Schema for search_web operation"""
    query: str = Field(description="Search query string")
    # ...

# search_tool/core.py
from .schemas import SearchWebSchema

@register_tool("search")
class SearchTool(BaseTool):
    def search_web(self, query: str) -> Dict[str, Any]:
        # Implementation...
```

**Note:** Inner classes are preferred for new tools. Module-level schemas are acceptable for existing tools.

---

## Best Practices for Schema Field Descriptions

### 1. Be Specific and Actionable

**❌ Bad:**
```python
records: List[Dict[str, Any]] = Field(description="Records")
condition: str = Field(description="Condition")
```

**✅ Good:**
```python
records: List[Dict[str, Any]] = Field(
    description="List of records (dictionaries) representing the DataFrame to filter"
)
condition: str = Field(
    description="Filter condition using pandas query syntax (e.g., 'age > 30', 'name == \"John\"')"
)
```

### 2. Include Examples When Helpful

**✅ Good:**
```python
file_type: str = Field(
    default="csv",
    description="Type of file: 'csv', 'excel', or 'json'"
)

date_restrict: Optional[str] = Field(
    default=None,
    description="Date restriction (e.g., 'd7' for last 7 days, 'm3' for last 3 months)"
)
```

### 3. Explain Constraints and Defaults

**✅ Good:**
```python
num_results: int = Field(
    default=10,
    ge=1,
    le=100,
    description="Number of results to return (1-100, default: 10)"
)

max_length: int = Field(
    default=150,
    ge=1,
    description="Maximum length of the summary in words (minimum: 1, default: 150)"
)
```

### 4. Document Optional Parameters Clearly

**✅ Good:**
```python
columns: Optional[List[str]] = Field(
    default=None,
    description="Optional list of column names to describe. If None, describes all columns"
)

language: Optional[str] = Field(
    default=None,
    description="Optional language code for the text (e.g., 'en', 'zh-CN'). If None, uses the default spaCy model language"
)
```

### 5. Use Consistent Terminology

**✅ Good:**
- Use "List of records (dictionaries)" consistently for DataFrame representations
- Use "Path to the file" for file paths
- Use "Optional" prefix for optional parameters
- Use "Default: X" format for default values

### 6. Avoid Generic Descriptions

**❌ Bad:**
```python
data: str = Field(description="Data")
param: int = Field(description="Parameter")
value: Any = Field(description="Value")
```

**✅ Good:**
```python
data: str = Field(description="CSV string content to read into a DataFrame")
param: int = Field(description="Maximum number of results to return")
value: Any = Field(description="Value to search for in the dataset")
```

### 7. Include Format Specifications

**✅ Good:**
```python
observation_start: str = Field(
    description="Start date for observations in YYYY-MM-DD format (e.g., '2020-01-01')"
)

series_id: str = Field(
    description="FRED series ID (uppercase alphanumeric, e.g., 'GDP', 'UNRATE', 'CPIAUCSL')"
)
```

---

## Type Annotation Requirements for Auto-Generation

### Required Annotations

**All parameters must have type annotations for auto-generation to work:**

```python
# ✅ Good - Complete type annotations
def filter(
    self,
    records: List[Dict[str, Any]],
    condition: str,
    case_sensitive: bool = True
) -> List[Dict[str, Any]]:
    pass

# ❌ Bad - Missing type annotations
def filter(self, records, condition, case_sensitive=True):
    pass
```

### Supported Types

**Primitive Types:**
- `str`, `int`, `float`, `bool`
- `None` (for Optional)

**Collection Types:**
- `List[T]` - Lists
- `Dict[K, V]` - Dictionaries
- `Tuple[T, ...]` - Tuples
- `Set[T]` - Sets

**Optional Types:**
- `Optional[T]` - Equivalent to `Union[T, None]`
- `T | None` (Python 3.10+)

**Union Types:**
- `Union[T1, T2]` - Multiple possible types
- `T1 | T2` (Python 3.10+)

**Special Types:**
- `Any` - Any type (use sparingly)
- `Literal["value1", "value2"]` - Specific values

### Complex Types Handling

**Pandas Types:**
```python
# Auto-generator will convert to Any
def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
    # Schema will have: df: Any
    pass
```

**Custom Classes:**
```python
# Auto-generator will use the type as-is if Pydantic-compatible
from pydantic import BaseModel

class MyData(BaseModel):
    value: int

def process(self, data: MyData) -> MyData:
    # Schema will use MyData type
    pass
```

### Default Values

**Default values are automatically handled:**
```python
def search(
    self,
    query: str,
    num_results: int = 10,  # ✅ Default value preserved
    language: Optional[str] = None  # ✅ Optional with None default
) -> Dict[str, Any]:
    pass
```

### Docstring Requirements

**For best auto-generation results, use Google or NumPy style docstrings:**

```python
def filter(
    self,
    records: List[Dict[str, Any]],
    condition: str
) -> List[Dict[str, Any]]:
    """
    Filter DataFrame based on a condition.
    
    Args:
        records: List of records (dictionaries) to filter
        condition: Filter condition using pandas query syntax
    
    Returns:
        Filtered list of records
    """
    pass
```

**Supported Formats:**
- Google style: `Args:` section
- NumPy style: `Parameters:` section

---

## Examples of Good vs Bad Schemas

### Example 1: Simple Schema

**❌ Bad:**
```python
class FilterSchema(BaseModel):
    records: List[Dict]
    condition: str
```

**Issues:**
- No field descriptions
- Generic type `List[Dict]` instead of `List[Dict[str, Any]]`
- No docstring for the schema class

**✅ Good:**
```python
class FilterSchema(BaseModel):
    """Schema for filter operation"""
    
    records: List[Dict[str, Any]] = Field(
        description="List of records (dictionaries) representing the DataFrame to filter"
    )
    condition: str = Field(
        description="Filter condition using pandas query syntax (e.g., 'age > 30')"
    )
```

### Example 2: Schema with Constraints

**❌ Bad:**
```python
class SearchSchema(BaseModel):
    query: str
    num_results: int = 10
    safe_search: str = "medium"
```

**Issues:**
- No validation for constraints
- No description of allowed values
- No bounds checking

**✅ Good:**
```python
class SearchWebSchema(BaseModel):
    """Schema for search_web operation"""
    
    query: str = Field(
        description="Search query string",
        min_length=1,
        max_length=500
    )
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results to return (1-100, default: 10)"
    )
    safe_search: str = Field(
        default="medium",
        description="Safe search level: 'off', 'medium', or 'high'"
    )
    
    @field_validator("safe_search")
    @classmethod
    def validate_safe_search(cls, v: str) -> str:
        """Validate safe search level"""
        allowed = ["off", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"safe_search must be one of {allowed}")
        return v
```

### Example 3: Optional Parameters

**❌ Bad:**
```python
class DescribeSchema(BaseModel):
    records: List[Dict]
    columns: List[str] = None
```

**Issues:**
- `None` default without `Optional` type
- No description of what happens when None
- Generic type annotation

**✅ Good:**
```python
class DescribeSchema(BaseModel):
    """Schema for describe operation"""
    
    records: List[Dict[str, Any]] = Field(
        description="List of records (dictionaries) representing the DataFrame"
    )
    columns: Optional[List[str]] = Field(
        default=None,
        description="Optional list of column names to describe. If None, describes all columns"
    )
```

### Example 4: Complex Schema with Examples

**❌ Bad:**
```python
class ReadFileSchema(BaseModel):
    file_path: str
    file_type: str = "csv"
    encoding: str = "utf-8"
```

**Issues:**
- No description of allowed file types
- No examples
- No validation

**✅ Good:**
```python
class Read_fileSchema(BaseModel):
    """Schema for read_file operation"""
    
    file_path: str = Field(
        description="Path to the file to read"
    )
    file_type: str = Field(
        default="csv",
        description="Type of file: 'csv', 'excel', or 'json' (default: 'csv')"
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding (default: 'utf-8'). Common values: 'utf-8', 'latin-1', 'ascii'"
    )
    
    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        """Validate file type"""
        allowed = ["csv", "excel", "json"]
        if v not in allowed:
            raise ValueError(f"file_type must be one of {allowed}")
        return v
```

### Example 5: Auto-Generated Schema (Good Practice)

**✅ Excellent (for simple cases):**
```python
def group_by(
    self,
    records: List[Dict[str, Any]],
    by: List[str],
    agg: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Group DataFrame by specified columns and apply aggregation functions.
    
    Args:
        records: List of records (dictionaries) representing the DataFrame
        by: List of column names to group by
        agg: Optional dictionary mapping column names to aggregation functions
            (e.g., {'age': 'mean', 'salary': 'sum'}). If None, returns count for each group.
    
    Returns:
        Aggregated results as list of dictionaries
    """
    # Implementation...
    pass
```

**This automatically generates:**
```python
# Auto-generated Group_bySchema
class Group_bySchema(BaseModel):
    """Group DataFrame by specified columns and apply aggregation functions."""
    
    records: List[Dict[str, Any]] = Field(
        description="List of records (dictionaries) representing the DataFrame"
    )
    by: List[str] = Field(
        description="List of column names to group by"
    )
    agg: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional dictionary mapping column names to aggregation functions (e.g., {'age': 'mean', 'salary': 'sum'}). If None, returns count for each group."
    )
```

---

## Schema Development Checklist

Use this checklist when creating or reviewing schemas:

### Pre-Development

- [ ] Determine if manual schema is needed (complex validation, constraints, etc.)
- [ ] Ensure method has complete type annotations
- [ ] Ensure method has well-documented docstring (Google/NumPy style)
- [ ] Review existing schemas in the tool for consistency

### Schema Definition

- [ ] Schema class name follows `{MethodName}Schema` pattern
- [ ] Schema is defined as inner class (or module-level if legacy)
- [ ] Schema class has descriptive docstring
- [ ] All fields have `Field()` with description
- [ ] Field descriptions are specific and actionable
- [ ] Optional parameters use `Optional[T]` type
- [ ] Default values are properly set
- [ ] Constraints (min/max, length) are specified where applicable
- [ ] Custom validators are added for complex validation
- [ ] Examples are included for complex or ambiguous fields

### Quality Checks

- [ ] Run `aiecs tools validate-schemas <tool_name>` to check quality
- [ ] Verify schema coverage is ≥ 90%
- [ ] Check that description quality is ≥ 80%
- [ ] Ensure type coverage is 100%
- [ ] Test schema with valid inputs
- [ ] Test schema with invalid inputs (validation errors)
- [ ] Verify schema works with LangChain adapter

### Documentation

- [ ] Schema docstring explains the operation
- [ ] Field descriptions include examples where helpful
- [ ] Constraints and defaults are clearly documented
- [ ] Optional parameters explain behavior when None

---

## Code Review Guidelines

### Schema Review Checklist

When reviewing tool code, check:

#### 1. Schema Coverage
- [ ] Does every public method have a schema?
- [ ] Is schema coverage ≥ 90%?
- [ ] Are missing schemas justified (e.g., no-parameter methods)?

#### 2. Naming and Structure
- [ ] Schema name follows `{MethodName}Schema` pattern?
- [ ] Schema is defined as inner class?
- [ ] Schema class has docstring?

#### 3. Field Quality
- [ ] All fields have descriptions?
- [ ] Descriptions are specific (not generic like "Parameter X")?
- [ ] Optional fields use `Optional[T]`?
- [ ] Default values are appropriate?
- [ ] Constraints are specified where needed?

#### 4. Type Annotations
- [ ] Field types match method parameter types?
- [ ] Generic types are properly specified (e.g., `List[Dict[str, Any]]`)?
- [ ] Complex types are handled appropriately?

#### 5. Validation
- [ ] Custom validators are present for complex validation?
- [ ] Validation errors are clear and helpful?
- [ ] Constraints (min/max, length) are appropriate?

#### 6. Documentation
- [ ] Schema docstring is clear and helpful?
- [ ] Field descriptions include examples where needed?
- [ ] Behavior of optional parameters is explained?

### Review Comments Template

**For Missing Schemas:**
```
❌ Missing schema for method `method_name`
Please add a schema following the `{MethodName}Schema` pattern.
If auto-generation is sufficient, ensure method has complete type annotations and docstring.
```

**For Poor Descriptions:**
```
⚠️ Field `field_name` has generic description: "Parameter field_name"
Please provide a specific description explaining what this parameter does.
Example: "List of records (dictionaries) representing the DataFrame to filter"
```

**For Missing Constraints:**
```
⚠️ Field `num_results` lacks validation constraints
Consider adding `ge=1, le=100` to prevent invalid values.
```

**For Type Issues:**
```
❌ Field type `List[Dict]` should be `List[Dict[str, Any]]`
Please specify generic type parameters for better type safety.
```

### Approval Criteria

**Approve if:**
- ✅ Schema coverage ≥ 90%
- ✅ All fields have meaningful descriptions
- ✅ Type annotations are complete and correct
- ✅ Constraints are appropriate
- ✅ Documentation is clear

**Request Changes if:**
- ❌ Schema coverage < 90%
- ❌ Generic or missing field descriptions
- ❌ Missing type annotations
- ❌ Missing validation for constrained fields
- ❌ Unclear documentation

---

## Additional Resources

- [Schema Generator Documentation](./TOOLS_SCHEMA_GENERATOR.md)
- [BaseTool Documentation](./TOOLS_BASE_TOOL.md)
- [Schema Coverage Pre-commit Hook](./SCHEMA_COVERAGE_PRE_COMMIT.md)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

---

**Last Updated:** 2025-01-XX  
**Maintainer:** AIECS Tools Team

