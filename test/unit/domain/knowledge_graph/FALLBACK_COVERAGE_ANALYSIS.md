# Section 2 Fallback Path Coverage Analysis

## Fallback Paths in `_validate_property_in_schema()`

The implementation has **4 fallback paths**:

### Fallback Path 1: Schema without `get_entity_type` method
**Location**: Line 593-594
```python
if not hasattr(schema, "get_entity_type"):
    return errors  # Skip validation gracefully
```
**Tested**: ✅ `test_property_validation_schema_without_get_entity_type`

### Fallback Path 2: Entity type doesn't exist
**Location**: Line 598-600
```python
if entity_schema is None:
    # Entity type doesn't exist - error already reported by FindNode
    return errors  # Skip property validation
```
**Tested**: ✅ `test_property_validation_invalid_entity_type`

### Fallback Path 3: Entity schema without `get_property` method
**Location**: Line 607-608
```python
if not hasattr(entity_schema, "get_property"):
    return errors  # Skip property validation
```
**Tested**: ❌ **NOT TESTED**

### Fallback Path 4: Alternative way to get available properties
**Location**: Line 614-617
```python
if hasattr(entity_schema, "properties"):
    available_props = list(entity_schema.properties.keys())
elif hasattr(entity_schema, "get_property_names"):
    available_props = entity_schema.get_property_names()  # Fallback
```
**Tested**: ❌ **NOT TESTED** (only tests `properties` attribute path)

## Additional Fallback: No entity_type parameter
**Location**: Line 555-556 in `validate()` method
```python
# Validate property exists in schema (if entity_type provided)
if entity_type:
    errors.extend(self._validate_property_in_schema(schema, entity_type))
```
**Tested**: ✅ `test_property_validation_without_entity_type`

## Summary

**Fallback Paths Tested**: 3 out of 5 (60%)
- ✅ Schema without `get_entity_type` method
- ✅ Entity type doesn't exist
- ✅ No entity_type parameter provided
- ❌ Entity schema without `get_property` method
- ❌ Alternative `get_property_names()` method for available properties

## Recommendation

To achieve complete fallback coverage, add tests for:
1. Entity schema without `get_property` method
2. Entity schema using `get_property_names()` instead of `properties` attribute
