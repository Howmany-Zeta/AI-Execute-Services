# Knowledge Graph Builder Tool

**Tool Name**: `kg_builder`  
**Category**: Knowledge Graph Construction  
**Status**: ✅ Complete

## Overview

The `KnowledgeGraphBuilderTool` provides comprehensive knowledge graph construction capabilities for AIECS agents. It supports building graphs from unstructured text, documents, and structured data (CSV/JSON).

## Features

- **Text-to-Graph**: Extract entities and relations from natural language text
- **Document-to-Graph**: Process documents with chunking and batch extraction
- **Structured Data Import**: Import from CSV and JSON files with schema mapping
- **Statistics**: Get knowledge graph statistics and metrics

## Tool Registration

The tool is automatically registered with the AIECS tool registry:

```python
from aiecs.tools.knowledge_graph import KnowledgeGraphBuilderTool

# Tool is registered as "kg_builder"
```

## Input Schema

### KnowledgeGraphBuilderInput

```python
{
    "action": str,  # Required: "build_from_text", "build_from_document", "build_from_structured_data", "get_stats"
    "text": str,  # Optional: Text to process (for build_from_text)
    "document_path": str,  # Optional: Document path (for build_from_document)
    "data_path": str,  # Optional: Data file path (for build_from_structured_data)
    "schema_mapping": dict,  # Optional: Schema mapping (for build_from_structured_data)
    "source": str,  # Optional: Source identifier (default: "unknown")
    "entity_types": List[str],  # Optional: Entity types to extract
    "chunk_size": int,  # Optional: Chunk size for documents (default: 1000)
    "chunk_overlap": int  # Optional: Chunk overlap (default: 200)
}
```

## Actions

### 1. Build from Text

**Action**: `"build_from_text"`

Extract entities and relations from natural language text.

**Example**:
```python
result = await tool.run(
    op="kg_builder",
    action="build_from_text",
    text="Alice works at Tech Corp in San Francisco. Bob is her colleague.",
    source="example_doc",
    entity_types=["Person", "Company", "Location"]
)
```

**Response**:
```python
{
    "success": True,
    "source": "example_doc",
    "entities_added": 4,
    "relations_added": 3,
    "entities": [
        {
            "id": "entity_1",
            "type": "Person",
            "properties": {"name": "Alice"}
        },
        {
            "id": "entity_2",
            "type": "Company",
            "properties": {"name": "Tech Corp"}
        },
        {
            "id": "entity_3",
            "type": "Location",
            "properties": {"name": "San Francisco"}
        },
        {
            "id": "entity_4",
            "type": "Person",
            "properties": {"name": "Bob"}
        }
    ],
    "relations": [
        {
            "source_id": "entity_1",
            "target_id": "entity_2",
            "relation_type": "WORKS_FOR"
        },
        {
            "source_id": "entity_2",
            "target_id": "entity_3",
            "relation_type": "LOCATED_IN"
        },
        {
            "source_id": "entity_4",
            "target_id": "entity_1",
            "relation_type": "COLLEAGUE_OF"
        }
    ]
}
```

### 2. Build from Document

**Action**: `"build_from_document"`

Process documents with automatic chunking and batch extraction.

**Example**:
```python
result = await tool.run(
    op="kg_builder",
    action="build_from_document",
    document_path="/path/to/document.txt",
    source="research_paper",
    chunk_size=1000,
    chunk_overlap=200,
    entity_types=["Person", "Organization", "Technology"]
)
```

**Response**:
```python
{
    "success": True,
    "document_path": "/path/to/document.txt",
    "source": "research_paper",
    "total_chunks": 15,
    "chunks_processed": 15,
    "total_entities_added": 87,
    "total_relations_added": 124,
    "errors": []
}
```

### 3. Build from Structured Data (NEW)

**Action**: `"build_from_structured_data"`

Import entities and relations from CSV or JSON files using schema mapping.

**Example**:
```python
# Define schema mapping
schema_mapping = {
    "entity_mappings": [
        {
            "entity_type": "Person",
            "id_column": "person_id",
            "property_mappings": {
                "name": "full_name",
                "age": "age",
                "role": "job_title"
            }
        },
        {
            "entity_type": "Company",
            "id_column": "company_id",
            "property_mappings": {
                "name": "company_name",
                "industry": "sector"
            }
        }
    ],
    "relation_mappings": [
        {
            "relation_type": "WORKS_FOR",
            "source_column": "person_id",
            "target_column": "company_id",
            "source_type": "Person",
            "target_type": "Company"
        }
    ]
}

result = await tool.run(
    op="kg_builder",
    action="build_from_structured_data",
    data_path="/path/to/employees.csv",
    schema_mapping=schema_mapping
)
```

**Response**:
```python
{
    "success": True,
    "data_path": "/path/to/employees.csv",
    "entities_added": 250,
    "relations_added": 250,
    "rows_processed": 250,
    "rows_failed": 0,
    "duration_seconds": 2.5,
    "errors": [],
    "warnings": []
}
```

**Supported File Formats:**
- **CSV**: Comma-separated values with header row
- **JSON**: Array of objects or newline-delimited JSON

**Schema Mapping Structure:**

```python
{
    "entity_mappings": [
        {
            "entity_type": str,  # Entity type name
            "id_column": str,  # Column containing entity ID
            "property_mappings": {
                "property_name": "column_name",  # Map properties to columns
                ...
            }
        }
    ],
    "relation_mappings": [
        {
            "relation_type": str,  # Relation type name
            "source_column": str,  # Column containing source entity ID
            "target_column": str,  # Column containing target entity ID
            "source_type": str,  # Source entity type
            "target_type": str,  # Target entity type
            "property_mappings": {  # Optional relation properties
                "property_name": "column_name",
                ...
            }
        }
    ]
}
```

**Use Cases:**
- Importing existing databases into knowledge graphs
- Migrating from relational to graph databases
- Bulk data loading
- ETL pipelines

### 4. Get Statistics

**Action**: `"get_stats"`

Get knowledge graph statistics and metrics.

**Example**:
```python
result = await tool.run(
    op="kg_builder",
    action="get_stats"
)
```

**Response**:
```python
{
    "success": True,
    "stats": {
        "num_entities": 341,
        "num_relations": 478,
        "entity_types": {
            "Person": 150,
            "Company": 75,
            "Location": 50,
            "Technology": 66
        },
        "relation_types": {
            "WORKS_FOR": 150,
            "LOCATED_IN": 125,
            "USES": 100,
            "COLLEAGUE_OF": 103
        }
    }
}
```

## Advanced Usage

### Combining Actions

Build a comprehensive knowledge graph from multiple sources:

```python
# Step 1: Import structured data
result1 = await tool.run(
    op="kg_builder",
    action="build_from_structured_data",
    data_path="employees.csv",
    schema_mapping=employee_schema
)

# Step 2: Add unstructured text
result2 = await tool.run(
    op="kg_builder",
    action="build_from_text",
    text="Alice recently led the AI initiative at Tech Corp...",
    source="news_article"
)

# Step 3: Process documents
result3 = await tool.run(
    op="kg_builder",
    action="build_from_document",
    document_path="company_report.pdf",
    source="annual_report"
)

# Step 4: Get final statistics
stats = await tool.run(
    op="kg_builder",
    action="get_stats"
)
```

### Error Handling

```python
result = await tool.run(
    op="kg_builder",
    action="build_from_structured_data",
    data_path="data.csv",
    schema_mapping=schema
)

if not result["success"]:
    print(f"Error: {result['error']}")
else:
    print(f"Imported {result['entities_added']} entities")
    if result.get("warnings"):
        print(f"Warnings: {result['warnings']}")
```

## Best Practices

### 1. Choose the Right Action

- **build_from_text**: For short text snippets, chat messages, or single paragraphs
- **build_from_document**: For long documents, articles, or reports
- **build_from_structured_data**: For existing databases, CSV exports, or JSON data

### 2. Schema Mapping Tips

- Use meaningful entity and relation type names
- Map all relevant properties for rich graph data
- Include ID columns for entity deduplication
- Test with small datasets first

### 3. Performance Optimization

- Use batch processing for large documents (build_from_document)
- Adjust chunk_size and chunk_overlap for optimal extraction
- Enable error skipping for robust imports (skip_errors=True in pipeline)
- Monitor statistics to track growth

### 4. Data Quality

- Validate schema mappings before large imports
- Check for duplicate entities using entity IDs
- Review extraction results for accuracy
- Use entity types to filter and organize data

## See Also

- [Structured Data Pipeline Guide](../STRUCTURED_DATA_PIPELINE.md)
- [Schema Mapping Guide](../SCHEMA_MAPPING_GUIDE.md)
- [CSV to Graph Tutorial](../examples/csv_to_graph_tutorial.md)
- [JSON to Graph Tutorial](../examples/json_to_graph_tutorial.md)


