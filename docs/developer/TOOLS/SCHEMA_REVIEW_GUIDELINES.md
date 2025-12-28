# Schema Review Guidelines for Code Reviews

## Overview

This document provides guidelines for reviewing schema implementations during code reviews. These guidelines ensure consistency, quality, and maintainability of schemas across all tools.

## Review Checklist

### 1. Schema Coverage

**Check:**
- [ ] Does every public method have a schema?
- [ ] Is schema coverage ≥ 90%?
- [ ] Are missing schemas justified (e.g., no-parameter methods)?

**Commands:**
```bash
# Check coverage
aiecs tools schema-coverage tool_name

# Validate schemas
aiecs tools validate-schemas tool_name
```

**Approval Criteria:**
- ✅ Coverage ≥ 90%
- ✅ Missing schemas are justified

**Request Changes If:**
- ❌ Coverage < 90% without justification
- ❌ Public methods missing schemas

### 2. Schema Naming and Structure

**Check:**
- [ ] Schema name follows `{MethodName}Schema` pattern?
- [ ] Schema is defined as inner class (preferred) or module-level?
- [ ] Schema class has descriptive docstring?

**Examples:**

**✅ Good:**
```python
class FilterSchema(BaseModel):
    """Schema for filter operation"""
    # ...
```

**❌ Bad:**
```python
class Filter(BaseModel):  # Missing "Schema" suffix
    # ...
```

**Approval Criteria:**
- ✅ Naming follows convention
- ✅ Structure is appropriate
- ✅ Docstring present

### 3. Field Quality

**Check:**
- [ ] All fields have descriptions?
- [ ] Descriptions are specific (not generic like "Parameter X")?
- [ ] Optional fields use `Optional[T]`?
- [ ] Default values are appropriate?
- [ ] Constraints are specified where needed?

**Examples:**

**❌ Bad:**
```python
class SearchSchema(BaseModel):
    query: str  # No description
    num_results: int = 10  # No description, no constraints
```

**✅ Good:**
```python
class SearchSchema(BaseModel):
    """Schema for search operation"""
    
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
```

**Approval Criteria:**
- ✅ All fields have meaningful descriptions
- ✅ Constraints are appropriate
- ✅ Default values are sensible

**Request Changes If:**
- ❌ Generic descriptions ("Parameter X", "Data")
- ❌ Missing constraints for bounded values
- ❌ Inappropriate default values

### 4. Type Annotations

**Check:**
- [ ] Field types match method parameter types?
- [ ] Generic types are properly specified (e.g., `List[Dict[str, Any]]`)?
- [ ] Complex types are handled appropriately?

**Examples:**

**❌ Bad:**
```python
class ProcessSchema(BaseModel):
    records: List[Dict]  # Incomplete generic type
    data: Any  # Too generic
```

**✅ Good:**
```python
class ProcessSchema(BaseModel):
    """Schema for process operation"""
    
    records: List[Dict[str, Any]] = Field(
        description="List of records (dictionaries) to process"
    )
    data: Dict[str, Any] = Field(
        description="Data dictionary with string keys"
    )
```

**Approval Criteria:**
- ✅ Types match method signatures
- ✅ Generic types fully specified
- ✅ Types are appropriate

**Request Changes If:**
- ❌ Type mismatches
- ❌ Incomplete generic types
- ❌ Overuse of `Any`

### 5. Validation

**Check:**
- [ ] Custom validators present for complex validation?
- [ ] Validation errors are clear and helpful?
- [ ] Constraints (min/max, length) are appropriate?

**Examples:**

**✅ Good:**
```python
class SearchSchema(BaseModel):
    """Schema for search operation"""
    
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

**Approval Criteria:**
- ✅ Complex validation has validators
- ✅ Error messages are helpful
- ✅ Constraints are reasonable

**Request Changes If:**
- ❌ Missing validation for constrained fields
- ❌ Unclear error messages
- ❌ Overly restrictive constraints

### 6. Documentation

**Check:**
- [ ] Schema docstring is clear and helpful?
- [ ] Field descriptions include examples where needed?
- [ ] Behavior of optional parameters is explained?

**Examples:**

**❌ Bad:**
```python
class DescribeSchema(BaseModel):
    records: List[Dict]
    columns: Optional[List[str]] = None  # No description of None behavior
```

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

**Approval Criteria:**
- ✅ Clear documentation
- ✅ Examples where helpful
- ✅ Optional behavior explained

**Request Changes If:**
- ❌ Unclear documentation
- ❌ Missing examples for complex fields
- ❌ Unexplained optional behavior

## Review Comments Template

### For Missing Schemas

```
❌ Missing schema for method `method_name`

Please add a schema following the `{MethodName}Schema` pattern.
If auto-generation is sufficient, ensure method has complete type annotations and docstring.
Otherwise, create a manual schema as an inner class.

See: docs/developer/TOOLS/TOOL_SCHEMA_GUIDELINES.md
```

### For Poor Descriptions

```
⚠️ Field `field_name` has generic description: "Parameter field_name"

Please provide a specific description explaining what this parameter does.
Example: "List of records (dictionaries) representing the DataFrame to filter"

See: docs/developer/TOOLS/TOOL_SCHEMA_GUIDELINES.md#best-practices-for-schema-field-descriptions
```

### For Missing Constraints

```
⚠️ Field `num_results` lacks validation constraints

Consider adding `ge=1, le=100` to prevent invalid values.
Example:
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results to return (1-100, default: 10)"
    )
```

### For Type Issues

```
❌ Field type `List[Dict]` should be `List[Dict[str, Any]]`

Please specify generic type parameters for better type safety.
Example:
    records: List[Dict[str, Any]] = Field(
        description="List of records (dictionaries) to process"
    )
```

### For Missing Validation

```
⚠️ Field `safe_search` accepts any string but should only accept specific values

Please add a field validator:
    @field_validator("safe_search")
    @classmethod
    def validate_safe_search(cls, v: str) -> str:
        allowed = ["off", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"safe_search must be one of {allowed}")
        return v
```

## Approval Criteria Summary

**Approve if:**
- ✅ Schema coverage ≥ 90%
- ✅ All fields have meaningful descriptions
- ✅ Type annotations are complete and correct
- ✅ Constraints are appropriate
- ✅ Documentation is clear
- ✅ Validation is present where needed

**Request Changes if:**
- ❌ Schema coverage < 90%
- ❌ Generic or missing field descriptions
- ❌ Missing type annotations
- ❌ Missing validation for constrained fields
- ❌ Unclear documentation
- ❌ Type mismatches

## Automated Checks

Before requesting review, run:

```bash
# Check type annotations
aiecs tools check-annotations tool_name

# Validate schemas
aiecs tools validate-schemas tool_name --verbose

# Check coverage
aiecs tools schema-coverage tool_name --min-coverage 90
```

## Review Process

1. **Author:** Run validation commands before requesting review
2. **Reviewer:** Check coverage and quality metrics
3. **Reviewer:** Review schema structure and naming
4. **Reviewer:** Check field descriptions and types
5. **Reviewer:** Verify validation and constraints
6. **Reviewer:** Check documentation quality
7. **Reviewer:** Approve or request changes with specific comments

## Related Documents

- [Schema Development Guidelines](./TOOL_SCHEMA_GUIDELINES.md)
- [Tool Creation Workflow](./TOOL_CREATION_WORKFLOW.md)
- [Schema Coverage Pre-commit Hook](./SCHEMA_COVERAGE_PRE_COMMIT.md)

---

**Last Updated:** 2025-01-XX  
**Maintainer:** AIECS Tools Team

