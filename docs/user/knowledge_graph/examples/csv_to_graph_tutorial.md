# CSV-to-Graph Tutorial

This tutorial walks you through importing CSV data into a knowledge graph step by step.

## Scenario

You have employee data in CSV format and want to import it into a knowledge graph to enable graph-based queries and reasoning.

## Sample Data

**employees.csv:**
```csv
emp_id,name,email,department,salary,hire_date
E001,Alice Smith,alice@example.com,Engineering,100000,2020-01-15
E002,Bob Jones,bob@example.com,Engineering,120000,2019-03-20
E003,Carol White,carol@example.com,Marketing,95000,2021-06-10
E004,David Brown,david@example.com,Sales,110000,2020-11-05
E005,Eve Davis,eve@example.com,Engineering,105000,2021-02-28
```

## Step 1: Install Dependencies

```bash
# Already included in AIECS
# No additional installation needed
```

## Step 2: Create Schema Mapping

Define how CSV columns map to knowledge graph entities and relations:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    PropertyTransformation,
    TransformationType
)
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

# Define mapping
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["emp_id", "name", "email", "department", "salary", "hire_date"],
            entity_type="Employee",
            property_mapping={
                "emp_id": "id",
                "name": "name",
                "email": "email",
                "department": "department",
                "hire_date": "hire_date"
            },
            transformations=[
                # Cast salary from string to integer
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="salary",
                    target_property="salary",
                    target_type=PropertyType.INTEGER
                )
            ],
            id_column="emp_id"
        )
    ],
    description="Employee data import"
)
```

## Step 3: Initialize Graph Store

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

store = InMemoryGraphStore()
await store.initialize()
```

## Step 4: Create Pipeline

```python
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=100  # Process in batches
)
```

## Step 5: Import CSV

```python
result = await pipeline.import_from_csv("employees.csv")

print(f"✅ Import complete!")
print(f"   Entities added: {result.entities_added}")
print(f"   Rows processed: {result.rows_processed}")
```

## Step 6: Query the Graph

```python
# Get all employees
employees = await store.get_entities_by_type("Employee")
print(f"Total employees: {len(employees)}")

# Get specific employee
alice = await store.get_entity("E001")
print(f"Alice's salary: {alice.properties['salary']}")

# Search by property
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType

query = GraphQuery(
    query_type=QueryType.ENTITY_LOOKUP,
    entity_type="Employee",
    properties={"department": "Engineering"}
)
results = await store.query(query)
print(f"Engineering employees: {len(results)}")
```

## Complete Example

```python
import asyncio
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    PropertyTransformation,
    TransformationType
)
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

async def main():
    # Step 1: Define mapping
    mapping = SchemaMapping(
        entity_mappings=[
            EntityMapping(
                source_columns=["emp_id", "name", "email", "department", "salary", "hire_date"],
                entity_type="Employee",
                property_mapping={
                    "emp_id": "id",
                    "name": "name",
                    "email": "email",
                    "department": "department",
                    "hire_date": "hire_date"
                },
                transformations=[
                    PropertyTransformation(
                        transformation_type=TransformationType.TYPE_CAST,
                        source_column="salary",
                        target_property="salary",
                        target_type=PropertyType.INTEGER
                    )
                ],
                id_column="emp_id"
            )
        ]
    )
    
    # Step 2: Initialize store
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Step 3: Create pipeline
    pipeline = StructuredDataPipeline(
        mapping=mapping,
        graph_store=store
    )
    
    # Step 4: Import CSV
    print("📥 Importing CSV...")
    result = await pipeline.import_from_csv("employees.csv")
    
    print(f"\n✅ Import complete!")
    print(f"   Entities added: {result.entities_added}")
    print(f"   Rows processed: {result.rows_processed}")
    
    # Step 5: Query graph
    print("\n📊 Querying graph...")
    employees = await store.get_entities_by_type("Employee")
    print(f"Total employees: {len(employees)}")
    
    for emp in employees[:3]:  # Show first 3
        print(f"  - {emp.properties['name']} ({emp.properties['department']})")
    
    await store.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced: Multiple Entity Types

If your CSV contains multiple entity types:

**employees_with_depts.csv:**
```csv
emp_id,name,email,dept_id,dept_name,salary
E001,Alice Smith,alice@example.com,D001,Engineering,100000
E002,Bob Jones,bob@example.com,D001,Engineering,120000
E003,Carol White,carol@example.com,D002,Marketing,95000
```

**Mapping:**
```python
mapping = SchemaMapping(
    entity_mappings=[
        # Employee entity
        EntityMapping(
            source_columns=["emp_id", "name", "email", "salary"],
            entity_type="Employee",
            property_mapping={
                "emp_id": "id",
                "name": "name",
                "email": "email"
            },
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
        # Department entity
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
```

## Advanced: Relations

Create relations between entities:

**employees_relations.csv:**
```csv
emp_id,name,manager_id
E001,Alice Smith,E002
E002,Bob Jones,
E003,Carol White,E002
```

**Mapping:**
```python
from aiecs.application.knowledge_graph.builder.schema_mapping import RelationMapping

mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["emp_id", "name"],
            entity_type="Employee",
            property_mapping={"emp_id": "id", "name": "name"},
            id_column="emp_id"
        )
    ],
    relation_mappings=[
        RelationMapping(
            source_columns=["emp_id", "manager_id"],
            relation_type="REPORTS_TO",
            source_entity_column="emp_id",
            target_entity_column="manager_id"
        )
    ]
)
```

## Troubleshooting

### Issue: "Column not found"

**Solution:** Check column names match exactly (case-sensitive):

```python
# Check CSV columns
import pandas as pd
df = pd.read_csv("employees.csv", nrows=1)
print(f"CSV columns: {df.columns.tolist()}")

# Verify mapping uses correct column names
```

### Issue: Type casting fails

**Solution:** Ensure values are in correct format:

```python
# Check data types
df = pd.read_csv("employees.csv")
print(df.dtypes)
print(df["salary"].head())  # Should be numeric strings like "100000"
```

### Issue: Entities not created

**Solution:** Verify ID column exists and has unique values:

```python
# Check for duplicates
df = pd.read_csv("employees.csv")
duplicates = df["emp_id"].duplicated()
if duplicates.any():
    print(f"Duplicate IDs: {df[df['emp_id'].duplicated()]['emp_id'].tolist()}")
```

## Next Steps

- See [Schema Mapping Guide](../SCHEMA_MAPPING_GUIDE.md) for detailed mapping options
- See [StructuredDataPipeline Guide](../STRUCTURED_DATA_PIPELINE.md) for advanced usage
- See [JSON-to-Graph Tutorial](./json_to_graph_tutorial.md) for JSON import

