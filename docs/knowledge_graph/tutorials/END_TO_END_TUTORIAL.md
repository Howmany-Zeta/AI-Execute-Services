# End-to-End Knowledge Graph Tutorial

## Overview

This tutorial demonstrates a complete workflow using the AIECS Knowledge Graph system, from data import to advanced search and reasoning.

## Scenario

We'll build a knowledge graph of employees, companies, and projects, then perform various operations:

1. Import structured data from CSV
2. Add unstructured text data
3. Merge duplicate entities
4. Search with reranking
5. Parse logical queries
6. Optimize performance

## Prerequisites

```bash
pip install aiecs
```

## Step 1: Prepare Your Data

### employees.csv

```csv
person_id,full_name,age,role,company_id,company_name,city
1,Alice Smith,30,Engineer,100,Tech Corp,San Francisco
2,Bob Jones,25,Designer,100,Tech Corp,San Francisco
3,Charlie Brown,35,Manager,101,Data Inc,New York
4,Diana Prince,28,Analyst,101,Data Inc,New York
5,Eve Wilson,32,Engineer,100,Tech Corp,San Francisco
```

### projects.json

```json
[
  {
    "project_id": "p1",
    "name": "AI Platform",
    "lead_id": "1",
    "company_id": "100"
  },
  {
    "project_id": "p2",
    "name": "Data Pipeline",
    "lead_id": "3",
    "company_id": "101"
  }
]
```

## Step 2: Initialize the System

```python
import asyncio
from aiecs.tools.knowledge_graph import (
    KnowledgeGraphBuilderTool,
    GraphSearchTool,
    GraphReasoningTool
)
from aiecs.application.knowledge_graph.fusion import KnowledgeFusion
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

async def main():
    # Initialize graph store
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Initialize tools
    builder = KnowledgeGraphBuilderTool()
    await builder._initialize()
    
    search_tool = GraphSearchTool()
    await search_tool._initialize()
    
    reasoning_tool = GraphReasoningTool()
    await reasoning_tool._initialize()
    
    return store, builder, search_tool, reasoning_tool

# Run
store, builder, search_tool, reasoning_tool = await main()
```

## Step 3: Import CSV Data

```python
# Define schema mapping
employee_schema = {
    "entity_mappings": [
        {
            "entity_type": "Person",
            "id_column": "person_id",
            "property_mappings": {
                "name": "full_name",
                "age": "age",
                "role": "role"
            }
        },
        {
            "entity_type": "Company",
            "id_column": "company_id",
            "property_mappings": {
                "name": "company_name",
                "location": "city"
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

# Import CSV
result = await builder.run(
    op="kg_builder",
    action="build_from_structured_data",
    data_path="employees.csv",
    schema_mapping=employee_schema
)

print(f"✓ Imported {result['entities_added']} entities")
print(f"✓ Created {result['relations_added']} relations")
print(f"✓ Processed {result['rows_processed']} rows in {result['duration_seconds']:.2f}s")
# Output:
# ✓ Imported 7 entities (5 people + 2 companies)
# ✓ Created 5 relations
# ✓ Processed 5 rows in 0.15s
```

## Step 4: Import JSON Data

```python
project_schema = {
    "entity_mappings": [
        {
            "entity_type": "Project",
            "id_column": "project_id",
            "property_mappings": {
                "name": "name"
            }
        }
    ],
    "relation_mappings": [
        {
            "relation_type": "LEADS",
            "source_column": "lead_id",
            "target_column": "project_id",
            "source_type": "Person",
            "target_type": "Project"
        },
        {
            "relation_type": "BELONGS_TO",
            "source_column": "project_id",
            "target_column": "company_id",
            "source_type": "Project",
            "target_type": "Company"
        }
    ]
}

result = await builder.run(
    op="kg_builder",
    action="build_from_structured_data",
    data_path="projects.json",
    schema_mapping=project_schema
)

print(f"✓ Imported {result['entities_added']} projects")
# Output: ✓ Imported 2 projects
```

## Step 5: Add Unstructured Text

```python
# Add information from text
text = """
Alice Smith is a senior engineer at Tech Corp, specializing in machine learning.
She recently led the AI Platform project, which uses deep learning for natural language processing.
Bob Jones, a talented designer, collaborated with Alice on the user interface.
"""

result = await builder.run(
    op="kg_builder",
    action="build_from_text",
    text=text,
    source="company_blog",
    entity_types=["Person", "Technology", "Skill"]
)

print(f"✓ Extracted {result['entities_added']} entities from text")
print(f"✓ Found {result['relations_added']} relations")
# Output:
# ✓ Extracted 6 entities from text
# ✓ Found 8 relations
```

## Step 6: Merge Duplicate Entities

```python
# Alice Smith appears in both CSV and text - let's merge duplicates
fusion = KnowledgeFusion(
    graph_store=store,
    similarity_threshold=0.85,
    conflict_resolution_strategy="most_complete"
)

stats = await fusion.fuse_cross_document_entities(entity_types=["Person"])

print(f"✓ Analyzed {stats['entities_analyzed']} entities")
print(f"✓ Merged {stats['entities_merged']} duplicates")
print(f"✓ Resolved {stats['conflicts_resolved']} conflicts")
# Output:
# ✓ Analyzed 7 entities
# ✓ Merged 2 duplicates (Alice from CSV and text)
# ✓ Resolved 3 conflicts
```

## Step 7: Search with Reranking

```python
# Search for machine learning experts
result = await search_tool.run(
    op="graph_search",
    mode="hybrid",
    query="machine learning engineer",
    max_results=10,
    enable_reranking=True,
    rerank_strategy="hybrid"
)

print(f"✓ Found {len(result['entities'])} relevant entities")
for entity in result['entities'][:3]:
    print(f"  - {entity['properties']['name']}: {entity['entity_type']}")
# Output:
# ✓ Found 5 relevant entities
#   - Alice Smith: Person
#   - AI Platform: Project
#   - machine learning: Skill
```

## Step 8: Parse Logical Queries

```python
# Convert natural language to logical query
result = await reasoning_tool.run(
    op="graph_reasoning",
    mode="logical_query",
    query="Find all engineers who work for companies in San Francisco"
)

print(f"✓ Query type: {result['query_type']}")
print(f"✓ Variables: {result['variables']}")
print(f"✓ Predicates: {len(result['predicates'])}")
# Output:
# ✓ Query type: FIND
# ✓ Variables: ['?person', '?company']
# ✓ Predicates: 2
```

## Step 9: Get Statistics

```python
stats = await builder.run(op="kg_builder", action="get_stats")

print(f"\n=== Knowledge Graph Statistics ===")
print(f"Total entities: {stats['num_entities']}")
print(f"Total relations: {stats['num_relations']}")
print(f"\nEntity types:")
for entity_type, count in stats['entity_types'].items():
    print(f"  {entity_type}: {count}")
print(f"\nRelation types:")
for relation_type, count in stats['relation_types'].items():
    print(f"  {relation_type}: {count}")
# Output:
# === Knowledge Graph Statistics ===
# Total entities: 15
# Total relations: 18
# 
# Entity types:
#   Person: 5
#   Company: 2
#   Project: 2
#   Technology: 3
#   Skill: 3
# 
# Relation types:
#   WORKS_FOR: 5
#   LEADS: 2
#   BELONGS_TO: 2
#   SPECIALIZES_IN: 4
#   USES: 5
```

## Step 10: Cleanup

```python
await store.close()
```

## Complete Example

See [complete_example.py](./examples/complete_example.py) for the full code.

## Next Steps

- [Configuration Guide](../CONFIGURATION_GUIDE.md) - Optimize performance
- [Performance Guide](../PERFORMANCE_GUIDE.md) - Benchmark and tune
- [API Reference](../API_REFERENCE.md) - Detailed API documentation
- [Troubleshooting](../TROUBLESHOOTING.md) - Common issues and solutions

## Performance Tips

1. **Batch Size**: Use 100-500 for large imports
2. **Reranking**: Use "text" for speed, "hybrid" for precision
3. **Caching**: Enable schema caching in production
4. **Fusion**: Run periodically, not on every update
5. **Storage**: Use PostgreSQL for >1M entities

See [Performance Guide](../PERFORMANCE_GUIDE.md) for details.

