# StructuredDataPipeline Usage Guide

This guide explains how to use the `StructuredDataPipeline` to import structured data (CSV, JSON, SPSS, Excel) into knowledge graphs.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [CSV Import](#csv-import)
4. [JSON Import](#json-import)
5. [SPSS Import](#spss-import)
6. [Excel Import](#excel-import)
7. [Automatic Schema Inference](#automatic-schema-inference)
8. [Data Reshaping](#data-reshaping)
9. [Statistical Aggregation](#statistical-aggregation)
10. [Data Quality Validation](#data-quality-validation)
11. [Batch Processing](#batch-processing)
12. [Error Handling](#error-handling)
13. [Advanced Features](#advanced-features)
14. [Performance Tips](#performance-tips)

## Quick Start

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping
)
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

# 1. Create schema mapping
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["id", "name"],
            entity_type="Person",
            property_mapping={"id": "id", "name": "name"},
            id_column="id"
        )
    ]
)

# 2. Initialize graph store
store = InMemoryGraphStore()
await store.initialize()

# 3. Create pipeline
pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)

# 4. Import CSV
result = await pipeline.import_from_csv("data.csv")
print(f"Added {result.entities_added} entities, {result.relations_added} relations")
```

## Basic Usage

### Step 1: Define Schema Mapping

First, define how your data maps to the knowledge graph:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping
)

mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["id", "name", "email"],
            entity_type="Person",
            property_mapping={"id": "id", "name": "name", "email": "email"},
            id_column="id"
        )
    ],
    relation_mappings=[
        RelationMapping(
            source_columns=["person_id", "company_id"],
            relation_type="WORKS_FOR",
            source_entity_column="person_id",
            target_entity_column="company_id"
        )
    ]
)
```

### Step 2: Initialize Graph Store

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

store = InMemoryGraphStore()
await store.initialize()
```

### Step 3: Create Pipeline

```python
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=100,  # Optional: process in batches
    skip_errors=True  # Optional: continue on errors
)
```

### Step 4: Import Data

```python
# Import CSV
result = await pipeline.import_from_csv("data.csv")

# Or import JSON
result = await pipeline.import_from_json("data.json")
```

### Step 5: Check Results

```python
print(f"Entities added: {result.entities_added}")
print(f"Relations added: {result.relations_added}")
print(f"Rows processed: {result.rows_processed}")
print(f"Errors: {len(result.errors)}")
print(f"Warnings: {len(result.warnings)}")

# Check for errors
if result.errors:
    for error in result.errors:
        print(f"Error: {error}")
```

## CSV Import

### Basic CSV Import

```python
result = await pipeline.import_from_csv(
    file_path="employees.csv",
    delimiter=",",  # Optional: default is ","
    encoding="utf-8"  # Optional: default is "utf-8"
)
```

### CSV with Custom Delimiter

```python
# Tab-separated values
result = await pipeline.import_from_csv(
    file_path="data.tsv",
    delimiter="\t"
)

# Semicolon-separated values
result = await pipeline.import_from_csv(
    file_path="data.csv",
    delimiter=";"
)
```

### CSV with Headers

The pipeline automatically detects headers. If your CSV doesn't have headers, specify column names:

```python
# CSV without headers
result = await pipeline.import_from_csv(
    file_path="data_no_headers.csv",
    has_headers=False,
    column_names=["id", "name", "email"]  # Specify column names
)
```

### CSV with Different Encoding

```python
# Handle non-UTF-8 files
result = await pipeline.import_from_csv(
    file_path="data_latin1.csv",
    encoding="latin-1"
)
```

## SPSS Import

### Basic SPSS Import

Import data directly from SPSS (.sav) files:

```python
result = await pipeline.import_from_spss("survey_data.sav")
print(f"Added {result.entities_added} entities")
```

### SPSS Import with Schema Mapping

```python
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["respondent_id", "age", "gender"],
            entity_type="Respondent",
            property_mapping={
                "respondent_id": "id",
                "age": "age",
                "gender": "gender"
            },
            id_column="respondent_id"
        )
    ]
)

pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)
result = await pipeline.import_from_spss("survey_data.sav")
```

### SPSS Metadata Preservation

SPSS files contain variable labels and value labels that are automatically preserved:

```python
result = await pipeline.import_from_spss("survey_data.sav")

# Variable labels are stored in entity properties as "_spss_variable_labels"
# Value labels are stored as "_spss_value_labels"
entity = await store.get_entity("respondent_001")
print(entity.properties.get("_spss_variable_labels", {}))
```

### Auto-detect File Format

Use `import_from_file()` to automatically detect and import any supported format:

```python
# Automatically detects format from extension
result = await pipeline.import_from_file("data.sav")  # SPSS
result = await pipeline.import_from_file("data.xlsx")  # Excel
result = await pipeline.import_from_file("data.csv")  # CSV
result = await pipeline.import_from_file("data.json")  # JSON
```

## Excel Import

### Basic Excel Import

Import data from Excel files:

```python
result = await pipeline.import_from_excel("employees.xlsx")
print(f"Added {result.entities_added} entities")
```

### Excel Import with Specific Sheet

```python
# Import from specific sheet
result = await pipeline.import_from_excel(
    "workbook.xlsx",
    sheet_name="Sheet1"
)
```

### Excel Import with Multiple Sheets

```python
# Import from all sheets
result = await pipeline.import_from_excel(
    "workbook.xlsx",
    sheet_name=None  # None = all sheets
)

# Or import sheets sequentially
for sheet in ["Sheet1", "Sheet2", "Sheet3"]:
    result = await pipeline.import_from_excel(
        "workbook.xlsx",
        sheet_name=sheet
    )
    print(f"{sheet}: {result.entities_added} entities")
```

### Excel Data Types

Excel data types (dates, numbers, text) are automatically handled:

```python
# Dates are converted to ISO format strings
# Numbers are preserved as numeric types
# Text is preserved as strings
result = await pipeline.import_from_excel("data.xlsx")
```

## Automatic Schema Inference

### Infer Schema from Data

Automatically generate schema mappings from data structure:

```python
from aiecs.application.knowledge_graph.builder.schema_inference import SchemaInference

# Infer schema from CSV
inference = SchemaInference()
inferred = inference.infer_from_csv("data.csv")

# Review inferred schema
print(f"Inferred {len(inferred.entity_mappings)} entity types")
print(f"Inferred {len(inferred.relation_mappings)} relation types")
print(f"Confidence scores: {inferred.confidence_scores}")

# Use inferred schema
mapping = inferred.to_schema_mapping()
pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)
result = await pipeline.import_from_csv("data.csv")
```

### Infer Schema from SPSS

SPSS files provide rich metadata for better inference:

```python
inference = SchemaInference()
inferred = inference.infer_from_spss("survey_data.sav")

# SPSS variable labels are used as property names
# SPSS value labels are preserved for categorical data
mapping = inferred.to_schema_mapping()
```

### Partial Schema Inference

Provide some mappings and let the system infer the rest:

```python
# User provides partial mapping
user_mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["id", "name"],
            entity_type="Person",
            property_mapping={"id": "id", "name": "name"},
            id_column="id"
        )
    ]
)

# Infer remaining mappings
inference = SchemaInference()
inferred = inference.infer_from_csv("data.csv")

# Merge user-provided and inferred mappings
merged = inference.merge_with_user_mapping(inferred, user_mapping)
```

### Import with Auto-Inference

Use `create_with_auto_inference()` for one-step import:

```python
pipeline = await StructuredDataPipeline.create_with_auto_inference(
    file_path="data.csv",
    graph_store=store,
    entity_type_hint="Employee"  # Optional hint
)

result = await pipeline.import_from_file("data.csv")
```

## Data Reshaping

### Wide-to-Long Conversion for Normalized Structures

Convert wide format data (many columns) to normalized graph structure:

```python
from aiecs.application.knowledge_graph.builder.data_reshaping import DataReshaping

# Wide format: 1000 rows × 200 columns
# Convert to normalized: Sample entities + Option entities + HAS_VALUE relations

reshaping = DataReshaping()
reshape_result = reshaping.melt_wide_to_long(
    df=df_wide,
    id_vars=["sample_id"],
    value_vars=[f"option_{i:03d}" for i in range(1, 201)],
    var_name="option_id",
    value_name="value"
)

# Generate normalized schema mapping
mapping = reshaping.generate_normalized_mapping(
    id_column="sample_id",
    entity_type="Sample",
    variable_type="Option",
    relation_type="HAS_VALUE"
)

# Import normalized data
pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)
result = await pipeline.import_from_dataframe(reshape_result.data)
```

### Automatic Reshaping During Import

Detect and reshape wide format data automatically:

```python
# Pipeline automatically detects wide format and suggests normalization
pipeline = await StructuredDataPipeline.create_with_auto_reshape(
    file_path="wide_data.csv",
    graph_store=store,
    reshape_threshold=50  # Threshold for wide format detection
)

result = await pipeline.import_from_file("wide_data.csv")
```

### Reshape and Import in One Step

```python
# Reshape wide format and import with normalized structure
result = await pipeline.reshape_and_import(
    file_path="wide_data.csv",
    id_vars=["sample_id"],
    value_vars=option_columns,
    entity_type="Sample",
    variable_type="Option",
    relation_type="HAS_VALUE"
)
```

## Statistical Aggregation

### Compute Statistics During Import

Compute mean, standard deviation, and other statistics during import:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import AggregationConfig

mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["sample_id"] + [f"option_{i}" for i in range(1, 201)],
            entity_type="Sample",
            property_mapping={"sample_id": "id"},
            id_column="sample_id"
        )
    ],
    aggregations={
        "Sample": {
            "option_values": {
                "mean": "avg_value",
                "std": "std_value",
                "min": "min_value",
                "max": "max_value"
            }
        }
    }
)

pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)
result = await pipeline.import_from_csv("data.csv")

# Aggregated values are stored as entity properties
sample = await store.get_entity("sample_001")
print(f"Average: {sample.properties['avg_value']}")
print(f"Std Dev: {sample.properties['std_value']}")
```

### Grouped Aggregation

Compute statistics per group:

```python
mapping = SchemaMapping(
    aggregations={
        "Employee": {
            "salary": {
                "mean": "avg_salary",
                "std": "std_salary"
            }
        }
    },
    group_by="department"  # Group by department
)

# Aggregated values are stored on group entities
```

## Data Quality Validation

### Range Validation

Validate numeric values are within specified ranges:

```python
from aiecs.application.knowledge_graph.builder.data_quality import (
    DataQualityValidator,
    ValidationConfig,
    RangeRule
)

validation_config = ValidationConfig(
    rules={
        "Sample": {
            "option_1": RangeRule(min=0.0, max=1.0),
            "option_2": RangeRule(min=-10.0, max=10.0)
        }
    },
    fail_on_violations=False  # Continue import, log violations
)

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    validation_config=validation_config
)

result = await pipeline.import_from_csv("data.csv")

# Check quality report
if result.quality_report:
    print(f"Range violations: {result.quality_report.range_violations}")
    print(f"Completeness: {result.quality_report.completeness}")
```

### Outlier Detection

Detect and flag outliers:

```python
validation_config = ValidationConfig(
    outlier_detection={
        "Sample": {
            "option_1": {"method": "zscore", "threshold": 3.0}
        }
    },
    exclude_outliers=False  # Flag but don't exclude
)

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    validation_config=validation_config
)

result = await pipeline.import_from_csv("data.csv")

# Check outliers
if result.quality_report:
    print(f"Outliers detected: {len(result.quality_report.outliers)}")
```

### Completeness Checks

Check for missing values:

```python
validation_config = ValidationConfig(
    required_properties={
        "Sample": ["sample_id", "option_1", "option_2"]
    }
)

result = await pipeline.import_from_csv("data.csv")

# Check completeness
if result.quality_report:
    completeness = result.quality_report.completeness
    for prop, pct in completeness.items():
        print(f"{prop}: {pct:.1f}% complete")
```

## JSON Import

### JSON Array Import

Import from a JSON array:

```json
[
  {"id": "1", "name": "Alice", "email": "alice@example.com"},
  {"id": "2", "name": "Bob", "email": "bob@example.com"}
]
```

```python
result = await pipeline.import_from_json("data.json")
```

### JSON Lines (NDJSON) Import

Import from newline-delimited JSON:

```jsonl
{"id": "1", "name": "Alice"}
{"id": "2", "name": "Bob"}
```

```python
result = await pipeline.import_from_json(
    file_path="data.jsonl",
    json_format="jsonl"  # Specify format
)
```

### JSON Object with Array Property

Import from a JSON object containing an array:

```json
{
  "employees": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

```python
result = await pipeline.import_from_json(
    file_path="data.json",
    json_format="object_array",
    array_key="employees"  # Key containing the array
)
```

### JSON from String

Import directly from a JSON string:

```python
json_string = '[{"id": "1", "name": "Alice"}]'
result = await pipeline.import_from_json(
    file_path=None,
    json_data=json_string
)
```

## Batch Processing

For large files, process in batches to manage memory:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=1000  # Process 1000 rows at a time
)

result = await pipeline.import_from_csv("large_file.csv")
```

**Benefits:**
- Lower memory usage
- Progress tracking
- Better error recovery

## Error Handling

### Skip Errors (Default)

By default, the pipeline skips rows with errors and continues:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    skip_errors=True  # Default
)

result = await pipeline.import_from_csv("data.csv")

# Check errors
if result.errors:
    print(f"Skipped {len(result.errors)} rows with errors")
    for error in result.errors[:5]:  # Show first 5
        print(f"  - {error}")
```

### Fail on First Error

Stop processing on first error:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    skip_errors=False  # Stop on first error
)

try:
    result = await pipeline.import_from_csv("data.csv")
except Exception as e:
    print(f"Import failed: {e}")
```

### Validate Before Import

Validate mapping and data before importing:

```python
# Validate mapping
mapping_errors = mapping.validate()
if mapping_errors:
    print(f"Mapping errors: {mapping_errors}")
    return

# Validate CSV columns
import pandas as pd
df = pd.read_csv("data.csv", nrows=1)  # Read first row only
required_columns = set()
for entity_mapping in mapping.entity_mappings:
    required_columns.update(entity_mapping.source_columns)

missing = required_columns - set(df.columns)
if missing:
    print(f"Missing columns: {missing}")
    return

# Safe to import
result = await pipeline.import_from_csv("data.csv")
```

## Advanced Features

### Progress Callback

Track import progress:

```python
async def progress_callback(current: int, total: int):
    percentage = (current / total) * 100
    print(f"Progress: {current}/{total} ({percentage:.1f}%)")

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    progress_callback=progress_callback
)

result = await pipeline.import_from_csv("large_file.csv")
```

### Custom Metadata

Add metadata to imported entities and relations:

```python
# Metadata is automatically added:
# {
#     "source": "structured_data_import",
#     "imported_at": "2024-01-15T10:30:00"
# }

# You can add custom metadata by modifying the pipeline
# (requires extending StructuredDataPipeline)
```

### Multiple Imports

Import multiple files:

```python
files = ["employees.csv", "departments.csv", "projects.csv"]

for file_path in files:
    result = await pipeline.import_from_csv(file_path)
    print(f"{file_path}: {result.entities_added} entities, {result.relations_added} relations")
```

### Incremental Import

Add new data without duplicates:

```python
# First import
result1 = await pipeline.import_from_csv("initial_data.csv")
print(f"Initial: {result1.entities_added} entities")

# Later, import updates (duplicates are handled by GraphStore)
result2 = await pipeline.import_from_csv("updates.csv")
print(f"Updates: {result2.entities_added} entities")
```

## Performance Optimization

### Parallel Processing

Enable parallel batch processing for faster imports:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    enable_parallel=True,  # Enable parallel processing
    max_workers=4  # Number of worker processes (default: CPU count - 1)
)

result = await pipeline.import_from_csv("large_file.csv")
print(f"Throughput: {result.performance_metrics.rows_per_second:.0f} rows/sec")
```

**When to use**:
- Large datasets (>10,000 rows)
- Multi-core systems
- CPU-bound transformations

**Performance**: 2-3x speedup on multi-core systems

### Bulk Write Operations

Use bulk writes for faster storage:

```python
# Bulk writes are automatically used when available
# No code changes needed - works transparently

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=1000  # Larger batches = better bulk write performance
)

result = await pipeline.import_from_csv("large_file.csv")
```

**Performance**: 80%+ overhead reduction for bulk operations

### Streaming Import for Large Files

Import files larger than available memory:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    streaming=True  # Enable streaming mode
)

# Works with files >1GB without loading entire file into memory
result = await pipeline.import_from_csv("very_large_file.csv")
```

### Batch Size Auto-Tuning

Let the system automatically optimize batch size:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    auto_tune_batch_size=True  # Auto-tune based on memory and schema
)

result = await pipeline.import_from_csv("data.csv")
print(f"Used batch size: {result.performance_metrics.optimal_batch_size}")
```

### Performance Metrics

Track import performance:

```python
result = await pipeline.import_from_csv("data.csv")

if result.performance_metrics:
    metrics = result.performance_metrics
    print(f"Total time: {metrics.total_time:.2f}s")
    print(f"Read time: {metrics.read_time:.2f}s")
    print(f"Transform time: {metrics.transform_time:.2f}s")
    print(f"Write time: {metrics.write_time:.2f}s")
    print(f"Throughput: {metrics.rows_per_second:.0f} rows/sec")
    print(f"Peak memory: {metrics.peak_memory_mb:.1f} MB")
```

## Performance Tips

### 1. Use Batch Processing

```python
# ✅ Good: Process in batches
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=1000
)

# ❌ Avoid: Process entire file at once (for large files)
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=None  # Processes entire file
)
```

### 2. Optimize Schema Mapping

```python
# ✅ Good: Only include needed columns
EntityMapping(
    source_columns=["id", "name"],  # Only needed columns
    entity_type="Person",
    ...
)

# ❌ Avoid: Include unnecessary columns
EntityMapping(
    source_columns=["id", "name", "unused1", "unused2"],  # Extra columns
    entity_type="Person",
    ...
)
```

### 3. Use Appropriate Storage Backend

```python
# ✅ For development/testing: InMemoryGraphStore
store = InMemoryGraphStore()

# ✅ For production: SQLiteGraphStore or PostgreSQLGraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
store = SQLiteGraphStore(db_path="kg.db")
await store.initialize()
```

### 4. Pre-process Large Files

For very large files, consider preprocessing:

```python
# Split large CSV into smaller files
import pandas as pd

df = pd.read_csv("large_file.csv")
chunk_size = 10000

for i, chunk in enumerate(pd.read_csv("large_file.csv", chunksize=chunk_size)):
    chunk_file = f"chunk_{i}.csv"
    chunk.to_csv(chunk_file, index=False)
    
    result = await pipeline.import_from_csv(chunk_file)
    print(f"Chunk {i}: {result.entities_added} entities")
```

### 5. Validate Before Import

Validate data structure before importing:

```python
# Quick validation
import pandas as pd

df = pd.read_csv("data.csv", nrows=10)  # Sample first 10 rows
print(f"Columns: {df.columns.tolist()}")
print(f"Sample data:\n{df.head()}")

# Check for required columns
required = ["id", "name"]
missing = set(required) - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {missing}")

# Now import full file
result = await pipeline.import_from_csv("data.csv")
```

## Complete Example

```python
import asyncio
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping,
    PropertyTransformation,
    TransformationType
)
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

async def main():
    # 1. Define mapping
    mapping = SchemaMapping(
        entity_mappings=[
            EntityMapping(
                source_columns=["emp_id", "name", "email", "salary"],
                entity_type="Employee",
                property_mapping={"emp_id": "id", "name": "name", "email": "email"},
                transformations=[
                    PropertyTransformation(
                        transformation_type=TransformationType.TYPE_CAST,
                        source_column="salary",
                        target_property="salary",
                        target_type=PropertyType.INTEGER
                    )
                ],
                id_column="emp_id"
            ),
            EntityMapping(
                source_columns=["dept_id", "dept_name"],
                entity_type="Department",
                property_mapping={"dept_id": "id", "dept_name": "name"},
                id_column="dept_id"
            )
        ],
        relation_mappings=[
            RelationMapping(
                source_columns=["emp_id", "dept_id"],
                relation_type="WORKS_IN",
                source_entity_column="emp_id",
                target_entity_column="dept_id"
            )
        ]
    )
    
    # 2. Initialize store
    store = InMemoryGraphStore()
    await store.initialize()
    
    # 3. Create pipeline
    pipeline = StructuredDataPipeline(
        mapping=mapping,
        graph_store=store,
        batch_size=100
    )
    
    # 4. Import CSV
    result = await pipeline.import_from_csv("employees.csv")
    
    # 5. Check results
    print(f"✅ Import complete!")
    print(f"   Entities added: {result.entities_added}")
    print(f"   Relations added: {result.relations_added}")
    print(f"   Rows processed: {result.rows_processed}")
    
    if result.errors:
        print(f"⚠️  Errors: {len(result.errors)}")
        for error in result.errors[:5]:
            print(f"   - {error}")
    
    if result.warnings:
        print(f"⚠️  Warnings: {len(result.warnings)}")
        for warning in result.warnings[:5]:
            print(f"   - {warning}")
    
    # 6. Query graph
    employees = await store.get_entities_by_type("Employee")
    print(f"\n📊 Found {len(employees)} employees in graph")
    
    await store.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- See [Schema Mapping Guide](./SCHEMA_MAPPING_GUIDE.md) for detailed mapping configuration
- See [CSV-to-Graph Tutorial](./examples/csv_to_graph_tutorial.md) for complete CSV example
- See [JSON-to-Graph Tutorial](./examples/json_to_graph_tutorial.md) for complete JSON example
- See [Example Scripts](./examples/) for complete working examples:
  - `18_spss_import_with_inference.py` - SPSS import with automatic schema inference
  - `19_wide_format_normalization.py` - Reshape wide format to normalized structure
  - `20_statistical_aggregation.py` - Statistical aggregation during import
  - `21_data_quality_validation.py` - Data quality validation

