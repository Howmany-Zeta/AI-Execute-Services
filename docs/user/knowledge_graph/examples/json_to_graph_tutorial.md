# JSON-to-Graph Tutorial

This tutorial walks you through importing JSON data into a knowledge graph step by step.

## Scenario

You have product catalog data in JSON format and want to import it into a knowledge graph to enable graph-based queries and recommendations.

## Sample Data Formats

### Format 1: JSON Array

**products.json:**
```json
[
  {
    "product_id": "P001",
    "name": "Laptop",
    "category": "Electronics",
    "price": "999.99",
    "in_stock": "true",
    "tags": ["computers", "portable"]
  },
  {
    "product_id": "P002",
    "name": "Mouse",
    "category": "Electronics",
    "price": "29.99",
    "in_stock": "true",
    "tags": ["accessories", "input"]
  }
]
```

### Format 2: JSON Lines (NDJSON)

**products.jsonl:**
```jsonl
{"product_id": "P001", "name": "Laptop", "category": "Electronics", "price": "999.99"}
{"product_id": "P002", "name": "Mouse", "category": "Electronics", "price": "29.99"}
```

### Format 3: Object with Array Property

**products_wrapped.json:**
```json
{
  "products": [
    {"product_id": "P001", "name": "Laptop", "category": "Electronics"},
    {"product_id": "P002", "name": "Mouse", "category": "Electronics"}
  ]
}
```

## Step 1: Create Schema Mapping

Define how JSON fields map to knowledge graph entities:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    PropertyTransformation,
    TransformationType
)
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["product_id", "name", "category", "price", "in_stock", "tags"],
            entity_type="Product",
            property_mapping={
                "product_id": "id",
                "name": "name",
                "category": "category",
                "tags": "tags"
            },
            transformations=[
                # Cast price to float
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="price",
                    target_property="price",
                    target_type=PropertyType.FLOAT
                ),
                # Cast in_stock to boolean
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="in_stock",
                    target_property="available",
                    target_type=PropertyType.BOOLEAN
                ),
                # Parse tags JSON string to list
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="tags",
                    target_property="tags",
                    target_type=PropertyType.LIST
                )
            ],
            id_column="product_id"
        )
    ]
)
```

## Step 2: Initialize Graph Store

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

store = InMemoryGraphStore()
await store.initialize()
```

## Step 3: Create Pipeline

```python
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store
)
```

## Step 4: Import JSON

### Import JSON Array

```python
result = await pipeline.import_from_json("products.json")
print(f"Added {result.entities_added} products")
```

### Import JSON Lines

```python
result = await pipeline.import_from_json(
    file_path="products.jsonl",
    json_format="jsonl"
)
```

### Import Object with Array Property

```python
result = await pipeline.import_from_json(
    file_path="products_wrapped.json",
    json_format="object_array",
    array_key="products"
)
```

### Import from String

```python
json_string = '[{"product_id": "P001", "name": "Laptop"}]'
result = await pipeline.import_from_json(
    file_path=None,
    json_data=json_string
)
```

## Complete Example: JSON Array

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
                source_columns=["product_id", "name", "category", "price", "in_stock"],
                entity_type="Product",
                property_mapping={
                    "product_id": "id",
                    "name": "name",
                    "category": "category"
                },
                transformations=[
                    PropertyTransformation(
                        transformation_type=TransformationType.TYPE_CAST,
                        source_column="price",
                        target_property="price",
                        target_type=PropertyType.FLOAT
                    ),
                    PropertyTransformation(
                        transformation_type=TransformationType.TYPE_CAST,
                        source_column="in_stock",
                        target_property="available",
                        target_type=PropertyType.BOOLEAN
                    )
                ],
                id_column="product_id"
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
    
    # Step 4: Import JSON
    print("📥 Importing JSON...")
    result = await pipeline.import_from_json("products.json")
    
    print(f"\n✅ Import complete!")
    print(f"   Products added: {result.entities_added}")
    print(f"   Items processed: {result.rows_processed}")
    
    # Step 5: Query graph
    print("\n📊 Querying graph...")
    products = await store.get_entities_by_type("Product")
    print(f"Total products: {len(products)}")
    
    for product in products[:3]:  # Show first 3
        print(f"  - {product.properties['name']} (${product.properties['price']})")
    
    await store.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced: Nested JSON Structures

For nested JSON, flatten first or use multiple mappings:

**products_nested.json:**
```json
[
  {
    "product": {
      "id": "P001",
      "name": "Laptop"
    },
    "category": {
      "id": "C001",
      "name": "Electronics"
    }
  }
]
```

**Option 1: Flatten in Preprocessing**

```python
import json

# Load and flatten
with open("products_nested.json") as f:
    data = json.load(f)

flattened = []
for item in data:
    flattened.append({
        "product_id": item["product"]["id"],
        "product_name": item["product"]["name"],
        "category_id": item["category"]["id"],
        "category_name": item["category"]["name"]
    })

# Save flattened JSON
with open("products_flat.json", "w") as f:
    json.dump(flattened, f)

# Now import flattened JSON
result = await pipeline.import_from_json("products_flat.json")
```

**Option 2: Multiple Mappings**

```python
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["product_id", "product_name"],
            entity_type="Product",
            property_mapping={"product_id": "id", "product_name": "name"},
            id_column="product_id"
        ),
        EntityMapping(
            source_columns=["category_id", "category_name"],
            entity_type="Category",
            property_mapping={"category_id": "id", "category_name": "name"},
            id_column="category_id"
        )
    ],
    relation_mappings=[
        RelationMapping(
            source_columns=["product_id", "category_id"],
            relation_type="BELONGS_TO",
            source_entity_column="product_id",
            target_entity_column="category_id"
        )
    ]
)
```

## Advanced: Relations from JSON

**products_with_relations.json:**
```json
[
  {
    "product_id": "P001",
    "name": "Laptop",
    "category_id": "C001",
    "related_products": ["P002", "P003"]
  }
]
```

**Mapping with Relations:**
```python
from aiecs.application.knowledge_graph.builder.schema_mapping import RelationMapping

mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["product_id", "name", "category_id"],
            entity_type="Product",
            property_mapping={"product_id": "id", "name": "name"},
            id_column="product_id"
        ),
        EntityMapping(
            source_columns=["category_id"],
            entity_type="Category",
            property_mapping={"category_id": "id"},
            id_column="category_id"
        )
    ],
    relation_mappings=[
        # Product to Category
        RelationMapping(
            source_columns=["product_id", "category_id"],
            relation_type="BELONGS_TO",
            source_entity_column="product_id",
            target_entity_column="category_id"
        )
    ]
)

# Note: For related_products array, you'd need to:
# 1. Expand array into multiple rows, OR
# 2. Process relations separately after import
```

## Handling Complex JSON Types

### Arrays

If a field contains a JSON array string:

```json
{
  "product_id": "P001",
  "tags": "[\"electronics\", \"computers\"]"
}
```

Use `PropertyType.LIST`:

```python
PropertyTransformation(
    transformation_type=TransformationType.TYPE_CAST,
    source_column="tags",
    target_property="tags",
    target_type=PropertyType.LIST
)
```

### Objects

If a field contains a JSON object string:

```json
{
  "product_id": "P001",
  "metadata": "{\"source\": \"api\", \"version\": 1}"
}
```

Use `PropertyType.DICT`:

```python
PropertyTransformation(
    transformation_type=TransformationType.TYPE_CAST,
    source_column="metadata",
    target_property="metadata",
    target_type=PropertyType.DICT
)
```

## Troubleshooting

### Issue: "JSON decode error"

**Solution:** Validate JSON format:

```python
import json

# Validate JSON
with open("products.json") as f:
    try:
        data = json.load(f)
        print(f"✅ Valid JSON with {len(data)} items")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
```

### Issue: "Array key not found"

**Solution:** Check array key matches:

```python
# Check structure
with open("products_wrapped.json") as f:
    data = json.load(f)
    print(f"Top-level keys: {data.keys()}")
    # Should contain the array_key you specified
```

### Issue: "Field not found"

**Solution:** Check field names match:

```python
# Check first item structure
with open("products.json") as f:
    data = json.load(f)
    if data:
        print(f"Fields in first item: {data[0].keys()}")
```

## Performance Tips

### 1. Use JSON Lines for Large Files

JSON Lines (NDJSON) is more memory-efficient for large datasets:

```python
# ✅ Good: JSON Lines
result = await pipeline.import_from_json(
    file_path="large_file.jsonl",
    json_format="jsonl"
)

# ⚠️  Less efficient: JSON Array (loads entire file)
result = await pipeline.import_from_json("large_file.json")
```

### 2. Batch Processing

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=1000  # Process in batches
)
```

### 3. Validate Before Import

```python
import json

# Quick validation
with open("products.json") as f:
    data = json.load(f)
    print(f"Items: {len(data)}")
    if data:
        print(f"Sample fields: {list(data[0].keys())}")
```

## Next Steps

- See [Schema Mapping Guide](../SCHEMA_MAPPING_GUIDE.md) for detailed mapping options
- See [StructuredDataPipeline Guide](../STRUCTURED_DATA_PIPELINE.md) for advanced usage
- See [CSV-to-Graph Tutorial](./csv_to_graph_tutorial.md) for CSV import

