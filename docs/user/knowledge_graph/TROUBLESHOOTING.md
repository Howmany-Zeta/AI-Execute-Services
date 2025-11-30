# Knowledge Graph Troubleshooting Guide

## Common Issues and Solutions

### Import Issues

#### Problem: CSV Import Fails with "Missing Column" Error

**Symptoms:**
```
Error: Column 'name' not found in CSV file
```

**Solution:**
1. Check that column names in schema mapping match CSV headers exactly
2. Verify CSV file has a header row
3. Check for extra spaces in column names

**Example:**
```python
# ❌ Wrong - column name doesn't match
property_mappings={"name": "full_name"}  # CSV has "fullname" not "full_name"

# ✅ Correct
property_mappings={"name": "fullname"}
```

#### Problem: Import is Very Slow

**Symptoms:**
- Import takes >10 seconds for 1000 rows
- Throughput <50 rows/second

**Solutions:**
1. Increase batch size:
```python
pipeline = StructuredDataPipeline(
    mapping=schema_mapping,
    graph_store=store,
    batch_size=500  # Increase from default 50
)
```

2. Use PostgreSQL for large datasets:
```python
# Switch from InMemory to PostgreSQL
from aiecs.infrastructure.graph_storage.postgresql import PostgreSQLGraphStore
store = PostgreSQLGraphStore(connection_string="postgresql://...")
```

3. Enable skip_errors for faster processing:
```python
pipeline = StructuredDataPipeline(
    mapping=schema_mapping,
    graph_store=store,
    skip_errors=True  # Skip malformed rows
)
```

#### Problem: JSON Import Fails with "Invalid JSON"

**Symptoms:**
```
Error: Expecting value: line 1 column 1 (char 0)
```

**Solutions:**
1. Validate JSON format:
```bash
python -m json.tool data.json
```

2. Check for:
   - Missing commas between objects
   - Trailing commas
   - Single quotes instead of double quotes
   - Unescaped special characters

3. Use newline-delimited JSON for large files:
```json
{"id": "1", "name": "Alice"}
{"id": "2", "name": "Bob"}
```

### Search and Reranking Issues

#### Problem: Search Returns No Results

**Symptoms:**
- Query returns empty list
- Expected entities not found

**Solutions:**
1. Check entity properties match query:
```python
# Verify entities have searchable text
entity = await store.get_entity("e1")
print(entity.properties)  # Should have text fields
```

2. Try different search modes:
```python
# Try vector search
result = await tool.run(mode="vector", query="...")

# Try graph search
result = await tool.run(mode="graph", seed_entity_ids=["e1"])

# Try hybrid
result = await tool.run(mode="hybrid", query="...")
```

3. Check embeddings are present:
```python
entity = await store.get_entity("e1")
print(entity.embedding)  # Should not be None
```

#### Problem: Reranking is Too Slow

**Symptoms:**
- Search takes >1 second
- Latency >500ms

**Solutions:**
1. Use faster reranking strategy:
```python
# ❌ Slow - hybrid reranking
rerank_strategy="hybrid"  # 150-300ms

# ✅ Fast - text reranking
rerank_strategy="text"  # 50-100ms
```

2. Reduce top_k:
```python
# ❌ Slow - reranking 200 results
top_k=200

# ✅ Fast - reranking 20 results
top_k=20
```

3. Disable reranking for simple queries:
```python
result = await tool.run(
    query="...",
    enable_reranking=False  # Skip reranking
)
```

### Knowledge Fusion Issues

#### Problem: Too Many Entities Being Merged

**Symptoms:**
- Unrelated entities are merged
- Merge count is unexpectedly high

**Solutions:**
1. Increase similarity threshold:
```python
# ❌ Too lenient - merges too many
fusion = KnowledgeFusion(store, similarity_threshold=0.70)

# ✅ More strict - fewer merges
fusion = KnowledgeFusion(store, similarity_threshold=0.90)
```

2. Filter by entity type:
```python
# Only merge specific types
stats = await fusion.fuse_cross_document_entities(
    entity_types=["Person"]  # Don't merge other types
)
```

3. Review merge results:
```python
# Check what was merged
provenance = await fusion.track_entity_provenance("e1")
print(f"Entity came from: {provenance}")
```

#### Problem: Fusion is Too Slow

**Symptoms:**
- Fusion takes >30 seconds for 200 entities
- Throughput <10 entities/second

**Solutions:**
1. Increase similarity threshold (fewer comparisons):
```python
fusion = KnowledgeFusion(store, similarity_threshold=0.90)
```

2. Run fusion periodically, not on every update:
```python
# ❌ Slow - fusion after every import
await pipeline.import_from_csv("data.csv")
await fusion.fuse_cross_document_entities()

# ✅ Fast - fusion once at the end
await pipeline.import_from_csv("data1.csv")
await pipeline.import_from_csv("data2.csv")
await pipeline.import_from_csv("data3.csv")
await fusion.fuse_cross_document_entities()  # Once
```

3. Use faster conflict resolution:
```python
# ❌ Slower
conflict_resolution_strategy="most_confident"

# ✅ Faster
conflict_resolution_strategy="most_complete"
```

### Performance Issues

#### Problem: High Memory Usage

**Symptoms:**
- Application using >2GB RAM
- Out of memory errors

**Solutions:**
1. Switch to SQLite or PostgreSQL:
```python
# ❌ High memory - InMemory
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
store = InMemoryGraphStore()

# ✅ Low memory - SQLite
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
store = SQLiteGraphStore(db_path="graph.db")
```

2. Reduce cache sizes:
```python
# Reduce schema cache
schema_manager = SchemaManager(
    cache_size=100,  # Reduce from 1000
    ttl_seconds=300
)
```

3. Process data in batches:
```python
# Process large files in chunks
for chunk in pd.read_csv("large.csv", chunksize=1000):
    await pipeline.import_from_dataframe(chunk)
```

#### Problem: Slow Query Performance

**Symptoms:**
- Queries take >500ms
- Search is slow

**Solutions:**
1. Enable query optimization:
```python
# Enable in configuration
KG_ENABLE_QUERY_OPTIMIZATION=true
KG_QUERY_OPTIMIZATION_STRATEGY=balanced
```

2. Enable schema caching:
```python
KG_ENABLE_SCHEMA_CACHE=true
KG_SCHEMA_CACHE_TTL_SECONDS=3600
```

3. Use PostgreSQL with pgvector:
```python
KG_STORAGE_BACKEND=postgresql
KG_ENABLE_PGVECTOR=true
```

4. Add indexes (PostgreSQL):
```sql
CREATE INDEX idx_entity_type ON entities(entity_type);
CREATE INDEX idx_relation_type ON relations(relation_type);
```

### Configuration Issues

#### Problem: Configuration Not Loading

**Symptoms:**
- Settings not applied
- Using default values

**Solutions:**
1. Check .env file location:
```bash
# Should be in project root
ls -la .env
```

2. Verify environment variables:
```bash
# Check if variables are set
env | grep KG_
```

3. Use explicit configuration:
```python
from aiecs.config import Settings

settings = Settings(
    kg_storage_backend="postgresql",
    kg_enable_reranking=True
)
```

### Tool Issues

#### Problem: Tool Returns "Unsupported Operation" Error

**Symptoms:**
```
Error: Unsupported operation: kg_builder
```

**Solutions:**
1. Use correct operation name:
```python
# ❌ Wrong operation name
await tool.run(op="kg_builder", ...)

# ✅ Correct - use tool's registered operations
await tool.run(op="build_from_text", ...)
```

2. Check available operations:
```python
print(tool.input_schema())  # Shows available operations
```

## Getting Help

If you're still experiencing issues:

1. Check the [API Reference](./API_REFERENCE.md)
2. Review [Configuration Guide](./CONFIGURATION_GUIDE.md)
3. See [Performance Guide](./PERFORMANCE_GUIDE.md)
4. Open an issue on GitHub with:
   - Error message
   - Minimal reproduction code
   - Environment details (Python version, OS)
   - Configuration settings

## Performance Benchmarks

Expected performance for reference:

- **CSV Import**: 100-300 rows/second
- **JSON Import**: 100-250 records/second
- **Text Reranking**: 50-100ms
- **Hybrid Reranking**: 150-300ms
- **Schema Cache Hit**: <1ms
- **Query Optimization**: 40-70% improvement
- **Knowledge Fusion**: 10-40 entities/second

If your performance is significantly worse, review the solutions above.

