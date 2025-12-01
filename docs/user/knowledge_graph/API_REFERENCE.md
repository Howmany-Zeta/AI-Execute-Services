# Knowledge Graph API Reference

## Overview

This document provides a comprehensive API reference for all AIECS knowledge graph features, including domain models, storage interfaces, application services, and tools.

## Table of Contents

1. [Domain Models](#domain-models)
   - [Entity](#entity)
   - [Relation](#relation)
   - [Path](#path)
   - [GraphQuery and GraphResult](#graphquery-and-graphresult)
   - [Evidence and ReasoningResult](#evidence-and-reasoningresult)
   - [InferenceRule](#inferencerule)
2. [Schema Management](#schema-management)
   - [SchemaManager](#schemamanager)
   - [EntityType and RelationType](#entitytype-and-relationtype)
   - [PropertySchema](#propertyschema)
3. [Storage Interfaces](#storage-interfaces)
   - [GraphStore (Two-Tier Interface)](#graphstore-two-tier-interface)
   - [InMemoryGraphStore](#inmemorygraphstore)
   - [SQLiteGraphStore](#sqlitegraphstore)
   - [PostgreSQLGraphStore](#postgresqlgraphstore)
4. [Runnable Pattern](#runnable-pattern)
5. [Knowledge Fusion](#knowledge-fusion)
6. [Result Reranking](#result-reranking)
7. [Logical Query Parsing](#logical-query-parsing)
8. [Schema Caching](#schema-caching)
9. [Query Optimization](#query-optimization)
10. [Structured Data Pipeline](#structured-data-pipeline)
11. [Tools](#tools)

---

## Domain Models

### Entity

Represents a node in the knowledge graph.

**Module**: `aiecs.domain.knowledge_graph.models.entity`

```python
from aiecs.domain.knowledge_graph.models.entity import Entity

entity = Entity(
    id="person_1",
    entity_type="Person",
    properties={
        "name": "Alice Smith",
        "age": 30,
        "email": "alice@example.com"
    },
    metadata={
        "source": "document_1",
        "confidence": 0.95,
        "created_at": "2025-11-15T10:00:00Z"
    }
)
```

**Fields**:
- `id` (str): Unique identifier for the entity
- `entity_type` (str): Type of entity (e.g., "Person", "Company", "Product")
- `properties` (Dict[str, Any]): Entity attributes and values
- `metadata` (Optional[Dict[str, Any]]): Additional metadata (source, confidence, timestamps)

**Methods**:
- `get_property(key: str, default: Any = None) -> Any`: Get property value with default
- `set_property(key: str, value: Any) -> None`: Set property value
- `has_property(key: str) -> bool`: Check if property exists

### Relation

Represents an edge connecting two entities in the knowledge graph.

**Module**: `aiecs.domain.knowledge_graph.models.relation`

```python
from aiecs.domain.knowledge_graph.models.relation import Relation

relation = Relation(
    id="rel_1",
    relation_type="WORKS_FOR",
    source_id="person_1",
    target_id="company_1",
    properties={
        "role": "Engineer",
        "start_date": "2020-01-01",
        "department": "Engineering"
    },
    metadata={
        "source": "document_1",
        "confidence": 0.90
    }
)
```

**Fields**:
- `id` (str): Unique identifier for the relation
- `relation_type` (str): Type of relation (e.g., "WORKS_FOR", "KNOWS", "LOCATED_IN")
- `source_id` (str): ID of the source entity
- `target_id` (str): ID of the target entity
- `properties` (Dict[str, Any]): Relation attributes
- `metadata` (Optional[Dict[str, Any]]): Additional metadata

**Methods**:
- `reverse() -> Relation`: Create a reversed relation (swap source and target)
- `get_property(key: str, default: Any = None) -> Any`: Get property value

### Path

Represents a sequence of entities and relations forming a path in the graph.

**Module**: `aiecs.domain.knowledge_graph.models.path`

```python
from aiecs.domain.knowledge_graph.models.path import Path

path = Path(
    entities=[entity1, entity2, entity3],
    relations=[relation1, relation2],
    score=0.85,
    metadata={"reasoning": "multi-hop inference"}
)
```

**Fields**:
- `entities` (List[Entity]): Ordered list of entities in the path
- `relations` (List[Relation]): Ordered list of relations connecting entities
- `score` (Optional[float]): Path relevance or confidence score
- `metadata` (Optional[Dict[str, Any]]): Additional path metadata

**Methods**:
- `length() -> int`: Get path length (number of hops)
- `get_entity_ids() -> List[str]`: Get list of entity IDs in path
- `contains_entity(entity_id: str) -> bool`: Check if entity is in path
- `reverse() -> Path`: Create reversed path

### GraphQuery and GraphResult

Query specification and result container for graph operations.

**Module**: `aiecs.domain.knowledge_graph.models.query`

```python
from aiecs.domain.knowledge_graph.models.query import (
    GraphQuery,
    GraphResult,
    QueryType
)

# Create query
query = GraphQuery(
    query_type=QueryType.HYBRID,
    parameters={
        "query_text": "machine learning experts",
        "entity_types": ["Person"],
        "top_k": 10
    },
    filters={
        "properties.experience": {"$gte": 5}
    }
)

# Result
result = GraphResult(
    entities=[entity1, entity2],
    relations=[relation1],
    paths=[path1, path2],
    metadata={
        "query_time_ms": 45,
        "total_results": 2
    }
)
```

**GraphQuery Fields**:
- `query_type` (QueryType): Type of query (VECTOR, TRAVERSE, HYBRID, SUBGRAPH)
- `parameters` (Dict[str, Any]): Query-specific parameters
- `filters` (Optional[Dict[str, Any]]): Filter conditions

**GraphResult Fields**:
- `entities` (List[Entity]): Entities matching the query
- `relations` (List[Relation]): Relations in the result
- `paths` (List[Path]): Paths found (for traversal queries)
- `metadata` (Optional[Dict[str, Any]]): Query execution metadata

### Evidence and ReasoningResult

Evidence-based reasoning support.

**Module**: `aiecs.domain.knowledge_graph.models.evidence`

```python
from aiecs.domain.knowledge_graph.models.evidence import (
    Evidence,
    EvidenceType,
    ReasoningResult
)

evidence = Evidence(
    evidence_type=EvidenceType.PATH,
    content=path,
    confidence=0.85,
    source="graph_traversal",
    metadata={"hops": 2}
)

result = ReasoningResult(
    answer="Alice works for Tech Corp",
    evidence=[evidence1, evidence2],
    confidence=0.90,
    reasoning_steps=["Step 1: ...", "Step 2: ..."]
)
```

**Evidence Fields**:
- `evidence_type` (EvidenceType): Type of evidence (PATH, ENTITY, RELATION, INFERENCE)
- `content` (Any): Evidence content (Path, Entity, Relation, etc.)
- `confidence` (float): Confidence score (0.0-1.0)
- `source` (str): Source of evidence
- `metadata` (Optional[Dict[str, Any]]): Additional metadata

**ReasoningResult Fields**:
- `answer` (str): Final answer or conclusion
- `evidence` (List[Evidence]): Supporting evidence
- `confidence` (float): Overall confidence score
- `reasoning_steps` (List[str]): Step-by-step reasoning trace

### InferenceRule

Logical inference rules for knowledge graph reasoning.

**Module**: `aiecs.domain.knowledge_graph.models.inference_rule`

```python
from aiecs.domain.knowledge_graph.models.inference_rule import (
    InferenceRule,
    RuleType
)

rule = InferenceRule(
    rule_id="transitivity_works_for",
    rule_type=RuleType.TRANSITIVE,
    name="Company Hierarchy",
    description="If A works for B and B is subsidiary of C, then A works for C",
    conditions=[
        {"relation_type": "WORKS_FOR"},
        {"relation_type": "SUBSIDIARY_OF"}
    ],
    conclusion={
        "relation_type": "WORKS_FOR",
        "properties": {"inferred": True}
    },
    confidence=0.80
)
```

**Fields**:
- `rule_id` (str): Unique rule identifier
- `rule_type` (RuleType): Type of rule (TRANSITIVE, SYMMETRIC, INVERSE, CUSTOM)
- `name` (str): Human-readable rule name
- `description` (str): Rule description
- `conditions` (List[Dict[str, Any]]): Conditions that must be met
- `conclusion` (Dict[str, Any]): Inferred conclusion
- `confidence` (float): Rule confidence score

---

## Schema Management

### SchemaManager

Manages entity types, relation types, and property schemas with validation.

**Module**: `aiecs.domain.knowledge_graph.schema.schema_manager`

```python
from aiecs.domain.knowledge_graph.schema import (
    SchemaManager,
    EntityType,
    RelationType,
    PropertySchema,
    PropertyType
)

manager = SchemaManager()

# Define entity type
person_type = EntityType(
    name="Person",
    description="A person entity",
    properties={
        "name": PropertySchema(
            name="name",
            property_type=PropertyType.STRING,
            required=True
        ),
        "age": PropertySchema(
            name="age",
            property_type=PropertyType.INTEGER,
            min_value=0,
            max_value=150
        )
    }
)
manager.create_entity_type(person_type)

# Validate entity
is_valid = manager.validate_entity("Person", {"name": "Alice", "age": 30})
```

**Methods**:
- `create_entity_type(entity_type: EntityType) -> None`: Register entity type
- `get_entity_type(name: str) -> Optional[EntityType]`: Get entity type by name
- `create_relation_type(relation_type: RelationType) -> None`: Register relation type
- `get_relation_type(name: str) -> Optional[RelationType]`: Get relation type by name
- `validate_entity(entity_type: str, properties: Dict) -> bool`: Validate entity properties
- `validate_relation(relation_type: str, source_type: str, target_type: str) -> bool`: Validate relation
- `list_entity_types() -> List[str]`: List all entity type names
- `list_relation_types() -> List[str]`: List all relation type names

### EntityType and RelationType

Schema definitions for entities and relations.

**Module**: `aiecs.domain.knowledge_graph.schema.types`

```python
from aiecs.domain.knowledge_graph.schema import EntityType, RelationType

# Entity type
entity_type = EntityType(
    name="Company",
    description="A business organization",
    properties={...},
    metadata={"version": "1.0"}
)

# Relation type
relation_type = RelationType(
    name="WORKS_FOR",
    description="Employment relationship",
    source_entity_types=["Person"],
    target_entity_types=["Company"],
    properties={...}
)
```

### PropertySchema

Property definition with validation rules.

**Module**: `aiecs.domain.knowledge_graph.schema.property_schema`

```python
from aiecs.domain.knowledge_graph.schema import PropertySchema, PropertyType

property_schema = PropertySchema(
    name="salary",
    property_type=PropertyType.FLOAT,
    required=False,
    min_value=0.0,
    max_value=1000000.0,
    description="Annual salary in USD"
)
```

**PropertyType Enum**:
- `STRING`: Text values
- `INTEGER`: Whole numbers
- `FLOAT`: Decimal numbers
- `BOOLEAN`: True/False values
- `DATE`: Date values
- `DATETIME`: Date and time values
- `LIST`: List of values
- `DICT`: Dictionary/object values

---

## Storage Interfaces

### GraphStore (Two-Tier Interface)

Abstract base class for all graph storage backends.

**Module**: `aiecs.infrastructure.graph_storage.base`

```python
from aiecs.infrastructure.graph_storage.base import GraphStore

class CustomGraphStore(GraphStore):
    # Implement Tier 1 methods (required)
    async def initialize(self) -> None: ...
    async def close(self) -> None: ...
    async def add_entity(self, entity: Entity) -> None: ...
    async def get_entity(self, entity_id: str) -> Optional[Entity]: ...
    async def add_relation(self, relation: Relation) -> None: ...
    async def get_relation(self, relation_id: str) -> Optional[Relation]: ...
    async def get_neighbors(self, entity_id: str, ...) -> List[Entity]: ...

    # Tier 2 methods work automatically with defaults!
    # Optionally override for performance optimization
```

**Tier 1 Methods (Required)**:
- `initialize() -> None`: Initialize storage backend
- `close() -> None`: Close connections and cleanup
- `add_entity(entity: Entity) -> None`: Add entity to graph
- `get_entity(entity_id: str) -> Optional[Entity]`: Retrieve entity by ID
- `add_relation(relation: Relation) -> None`: Add relation to graph
- `get_relation(relation_id: str) -> Optional[Relation]`: Retrieve relation by ID
- `get_neighbors(entity_id: str, direction: str, relation_types: Optional[List[str]]) -> List[Entity]`: Get neighboring entities

**Tier 2 Methods (Has Defaults, Can Optimize)**:
- `traverse(start_entity_id: str, ...) -> List[Path]`: Multi-hop graph traversal
- `find_paths(start_id: str, end_id: str, ...) -> List[Path]`: Find paths between entities
- `subgraph_query(center_id: str, radius: int, ...) -> GraphResult`: Extract subgraph
- `vector_search(embedding: List[float], top_k: int, ...) -> List[Entity]`: Semantic search
- `execute_query(query: GraphQuery) -> GraphResult`: Execute generic query

### InMemoryGraphStore

Fast, networkx-based in-memory storage for development and testing.

**Module**: `aiecs.infrastructure.graph_storage.in_memory`

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

store = InMemoryGraphStore()
await store.initialize()

# Use all GraphStore methods
await store.add_entity(entity)
neighbors = await store.get_neighbors("entity_1")
paths = await store.traverse("entity_1", max_depth=3)

await store.close()
```

**Use Cases**:
- Development and testing
- Small graphs (< 100K nodes)
- Prototyping
- Temporary knowledge

**Performance**: Very fast for small graphs, all operations in-memory

### SQLiteGraphStore

File-based persistent storage for single-user applications.

**Module**: `aiecs.infrastructure.graph_storage.sqlite`

```python
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore

store = SQLiteGraphStore(db_path="knowledge.db")
await store.initialize()

# Optimized Tier 2 methods using SQL
paths = await store.traverse("entity_1", max_depth=5)  # Uses recursive CTE

await store.close()
```

**Use Cases**:
- Production applications
- Persistent storage
- Medium-sized graphs (< 1M nodes)
- Single-process applications

**Performance**: Optimized Tier 2 methods using SQL recursive CTEs

### PostgreSQLGraphStore

Production-grade storage with pgvector support for large-scale applications.

**Module**: `aiecs.infrastructure.graph_storage.postgresql`

```python
from aiecs.infrastructure.graph_storage.postgresql import PostgreSQLGraphStore

store = PostgreSQLGraphStore(
    connection_string="postgresql://user:pass@localhost/db"
)
await store.initialize()

# Optimized for scale
results = await store.vector_search(embedding, top_k=100)  # Uses pgvector
paths = await store.traverse("entity_1", max_depth=10)  # Optimized CTE

await store.close()
```

**Use Cases**:
- Production deployments
- Large graphs (10M+ nodes)
- Multi-user applications
- Concurrent access

**Performance**:
- pgvector for fast semantic search
- Optimized recursive CTEs for traversal
- Connection pooling
- Concurrent query support

---

## Runnable Pattern

### GraphRunnable

Base class for composable graph operations.

```python
from aiecs.application.knowledge_graph.runnable import GraphRunnable

class MyOperation(GraphRunnable):
    async def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your operation logic
        return result
```

**Methods:**
- `invoke(input_data)` - Execute the operation
- `pipe(other)` - Chain operations
- `batch(inputs)` - Process multiple inputs
- `stream(input_data)` - Stream results

**Example:**
```python
# Chain operations
pipeline = operation1.pipe(operation2).pipe(operation3)
result = await pipeline.invoke(data)

# Batch processing
results = await operation.batch([data1, data2, data3])
```

## Knowledge Fusion

### KnowledgeFusion

Merge duplicate entities across documents.

```python
from aiecs.application.knowledge_graph.fusion import KnowledgeFusion

fusion = KnowledgeFusion(
    graph_store: GraphStore,
    similarity_threshold: float = 0.85,
    conflict_resolution_strategy: str = "most_complete"
)
```

**Parameters:**
- `graph_store` - Graph storage backend
- `similarity_threshold` - Similarity threshold for merging (0.0-1.0)
- `conflict_resolution_strategy` - Strategy for resolving conflicts:
  - `"most_complete"` - Prefer non-empty, longer values (default)
  - `"most_recent"` - Prefer most recent timestamp
  - `"most_confident"` - Prefer most confident source
  - `"longest"` - Prefer longest string value
  - `"keep_all"` - Keep all conflicting values

**Methods:**

#### `fuse_cross_document_entities(entity_types=None)`

Merge duplicate entities across documents.

**Parameters:**
- `entity_types` (Optional[List[str]]) - Filter by entity types

**Returns:**
```python
{
    "success": bool,
    "entities_analyzed": int,
    "entities_merged": int,
    "merge_groups": int,
    "conflicts_resolved": int
}
```

**Example:**
```python
fusion = KnowledgeFusion(store, similarity_threshold=0.85)
stats = await fusion.fuse_cross_document_entities(entity_types=["Person"])
print(f"Merged {stats['entities_merged']} entities")
```

#### `track_entity_provenance(entity_id)`

Get provenance information for an entity.

**Returns:** List of source document IDs

## Result Reranking

### ResultReranker

Rerank search results for improved relevance.

```python
from aiecs.application.knowledge_graph.search.reranker import ResultReranker
from aiecs.application.knowledge_graph.search.reranker_strategies import (
    TextSimilarityReranker,
    SemanticReranker,
    StructuralReranker,
    HybridReranker
)

reranker = ResultReranker(strategies=[
    TextSimilarityReranker(),
    SemanticReranker(),
    StructuralReranker()
])
```

**Methods:**

#### `rerank(query, entities, top_k)`

Rerank entities by relevance.

**Parameters:**
- `query` (str) - Search query
- `entities` (List[Entity]) - Entities to rerank
- `top_k` (int) - Number of results to return

**Returns:** List[Entity] - Reranked entities

**Example:**
```python
reranker = ResultReranker(strategies=[HybridReranker()])
results = await reranker.rerank(
    query="machine learning",
    entities=search_results,
    top_k=20
)
```

### Reranking Strategies

#### TextSimilarityReranker

BM25-based text similarity reranking.

```python
strategy = TextSimilarityReranker()
```

**Performance:** 50-100ms latency

#### SemanticReranker

Deep semantic similarity using embeddings.

```python
strategy = SemanticReranker()
```

**Performance:** 100-200ms latency

#### StructuralReranker

Graph structure importance (centrality, PageRank).

```python
strategy = StructuralReranker()
```

**Performance:** 80-150ms latency

#### HybridReranker

Combines all signals for best results.

```python
strategy = HybridReranker(
    text_weight=0.4,
    semantic_weight=0.4,
    structural_weight=0.2
)
```

**Performance:** 150-300ms latency

## Logical Query Parsing

### LogicFormParser

Convert natural language to structured logical queries.

```python
from aiecs.application.knowledge_graph.reasoning.logic_form_parser import LogicFormParser

parser = LogicFormParser()
logical_query = parser.parse("Find all people who work for companies in San Francisco")
```

**Returns:**
```python
LogicalQuery(
    query_type=QueryType.FIND,
    variables=[Variable(name="?person"), Variable(name="?company")],
    predicates=[
        Predicate(name="WORKS_FOR", arguments=["?person", "?company"]),
        Predicate(name="LOCATED_IN", arguments=["?company", "San Francisco"])
    ],
    constraints=[...]
)
```

**Methods:**
- `to_dict()` - Convert to dictionary representation

## Schema Caching

### SchemaCache

High-performance caching for schema operations.

```python
from aiecs.domain.knowledge_graph.schema.schema_cache import SchemaCache

cache = SchemaCache(
    ttl_seconds=3600,  # 1 hour
    max_size=1000
)
```

**Methods:**
- `get(key)` - Get cached value
- `set(key, value)` - Set cached value
- `invalidate(key)` - Invalidate cache entry
- `clear()` - Clear all cache
- `get_metrics()` - Get cache metrics

**Metrics:**
```python
{
    "hits": int,
    "misses": int,
    "total_requests": int,
    "hit_rate": float,
    "size": int
}
```

**Performance:** 3-5x speedup, 70-95% hit rate

## Query Optimization

### QueryOptimizer

Cost-based query optimization.

```python
from aiecs.application.knowledge_graph.reasoning.query_optimizer import QueryOptimizer

optimizer = QueryOptimizer(strategy="balanced")
optimized_plan = optimizer.optimize(query_plan)
```

**Strategies:**
- `"cost"` - Minimize computational cost
- `"latency"` - Minimize query latency
- `"balanced"` - Balance cost and latency (default)

**Performance:** 40-70% faster query execution

## Structured Data Pipeline

### StructuredDataPipeline

Import CSV, JSON, SPSS, and Excel data into knowledge graphs with automatic schema inference, data reshaping, statistical aggregation, and quality validation.

```python
from aiecs.application.knowledge_graph.builder.structured_pipeline import (
    StructuredDataPipeline,
    ImportResult,
    PerformanceMetrics
)
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping
)

pipeline = StructuredDataPipeline(
    mapping=schema_mapping,
    graph_store=store,
    batch_size=100,
    skip_errors=True,
    enable_parallel=False,  # Enable parallel processing
    validation_config=None,  # Data quality validation
    auto_tune_batch_size=False  # Auto-tune batch size
)
```

**Parameters:**
- `mapping` (SchemaMapping): Schema mapping configuration (optional if using inference)
- `graph_store` (GraphStore): Graph storage backend
- `batch_size` (int): Number of rows per batch (default: 100)
- `skip_errors` (bool): Continue on errors (default: True)
- `enable_parallel` (bool): Enable parallel batch processing (default: False)
- `max_workers` (int): Number of worker processes (default: CPU count - 1)
- `validation_config` (ValidationConfig): Data quality validation rules
- `auto_tune_batch_size` (bool): Auto-tune batch size (default: False)
- `streaming` (bool): Enable streaming mode for large files (default: False)

**Methods:**

#### `import_from_csv(file_path, encoding="utf-8", delimiter=",", header=True) -> ImportResult`

Import data from CSV file.

**Example:**
```python
result = await pipeline.import_from_csv("data.csv")
print(f"Added {result.entities_added} entities")
```

#### `import_from_json(file_path, encoding="utf-8", array_key=None) -> ImportResult`

Import data from JSON file.

**Example:**
```python
result = await pipeline.import_from_json("data.json")
```

#### `import_from_spss(file_path) -> ImportResult`

Import data from SPSS (.sav, .por) file.

**Example:**
```python
result = await pipeline.import_from_spss("survey_data.sav")
# SPSS metadata (variable labels, value labels) are automatically preserved
```

#### `import_from_excel(file_path, sheet_name=None) -> ImportResult`

Import data from Excel (.xlsx, .xls) file.

**Example:**
```python
# Import from specific sheet
result = await pipeline.import_from_excel("workbook.xlsx", sheet_name="Sheet1")

# Import from all sheets
result = await pipeline.import_from_excel("workbook.xlsx", sheet_name=None)
```

#### `import_from_file(file_path, **kwargs) -> ImportResult`

Auto-detect file format and import.

**Example:**
```python
# Automatically detects format from extension
result = await pipeline.import_from_file("data.sav")  # SPSS
result = await pipeline.import_from_file("data.xlsx")  # Excel
result = await pipeline.import_from_file("data.csv")  # CSV
```

#### `import_from_dataframe(df) -> ImportResult`

Import data from pandas DataFrame.

**Example:**
```python
import pandas as pd
df = pd.read_csv("data.csv")
result = await pipeline.import_from_dataframe(df)
```

#### `create_with_auto_inference(file_path, graph_store, entity_type_hint=None, **kwargs) -> StructuredDataPipeline`

Create pipeline with automatic schema inference.

**Example:**
```python
pipeline = await StructuredDataPipeline.create_with_auto_inference(
    file_path="data.csv",
    graph_store=store,
    entity_type_hint="Employee"
)
result = await pipeline.import_from_file("data.csv")
```

#### `create_with_auto_reshape(file_path, graph_store, entity_type_hint=None, reshape_threshold=50, **kwargs) -> StructuredDataPipeline`

Create pipeline with automatic wide format detection and reshaping suggestion.

**Example:**
```python
pipeline = await StructuredDataPipeline.create_with_auto_reshape(
    file_path="wide_data.csv",
    graph_store=store,
    reshape_threshold=50
)
```

#### `reshape_and_import(file_path, id_vars, value_vars, entity_type, variable_type, relation_type, **kwargs) -> ImportResult`

Reshape wide format data and import with normalized structure.

**Example:**
```python
result = await pipeline.reshape_and_import(
    file_path="wide_data.csv",
    id_vars=["sample_id"],
    value_vars=[f"option_{i}" for i in range(1, 201)],
    entity_type="Sample",
    variable_type="Option",
    relation_type="HAS_VALUE"
)
```

**Returns:** `ImportResult` with:
- `success` (bool): Whether import completed successfully
- `entities_added` (int): Number of entities added
- `relations_added` (int): Number of relations added
- `rows_processed` (int): Number of rows processed
- `rows_failed` (int): Number of rows that failed
- `errors` (List[str]): List of errors
- `warnings` (List[str]): List of warnings
- `quality_report` (QualityReport): Data quality validation report (if enabled)
- `performance_metrics` (PerformanceMetrics): Performance metrics (if enabled)
- `duration_seconds` (float): Total duration

### SchemaInference

Automatically infer schema mappings from data structure.

**Module**: `aiecs.application.knowledge_graph.builder.schema_inference`

```python
from aiecs.application.knowledge_graph.builder.schema_inference import SchemaInference

inference = SchemaInference(sample_size=1000)
```

**Methods:**

#### `infer_from_csv(file_path) -> InferredSchema`

Infer schema from CSV file.

**Example:**
```python
inferred = inference.infer_from_csv("data.csv")
mapping = inferred.to_schema_mapping()
```

#### `infer_from_spss(file_path) -> InferredSchema`

Infer schema from SPSS file (uses variable labels and value labels).

**Example:**
```python
inferred = inference.infer_from_spss("survey_data.sav")
# Uses SPSS variable labels as property names
# Uses SPSS value labels for categorical data
```

#### `infer_from_excel(file_path, sheet_name=None) -> InferredSchema`

Infer schema from Excel file.

**Example:**
```python
inferred = inference.infer_from_excel("workbook.xlsx", sheet_name="Sheet1")
```

#### `infer_from_dataframe(df, entity_type_hint=None, metadata=None) -> InferredSchema`

Infer schema from pandas DataFrame.

**Example:**
```python
import pandas as pd
df = pd.read_csv("data.csv")
inferred = inference.infer_from_dataframe(df, entity_type_hint="Employee")
```

#### `merge_with_user_mapping(inferred, user_mapping) -> SchemaMapping`

Merge inferred schema with user-provided mappings.

**Example:**
```python
user_mapping = SchemaMapping(entity_mappings=[...])
merged = inference.merge_with_user_mapping(inferred, user_mapping)
```

**Returns:** `InferredSchema` with:
- `entity_mappings` (List[EntityMapping]): Inferred entity mappings
- `relation_mappings` (List[RelationMapping]): Inferred relation mappings
- `confidence_scores` (Dict[str, float]): Confidence scores (0-1)
- `warnings` (List[str]): Warnings about inference
- `to_schema_mapping()`: Convert to SchemaMapping

### DataReshaping

Reshape data between wide and long formats for normalized graph structures.

**Module**: `aiecs.application.knowledge_graph.builder.data_reshaping`

```python
from aiecs.application.knowledge_graph.builder.data_reshaping import DataReshaping

reshaping = DataReshaping()
```

**Methods:**

#### `melt_wide_to_long(df, id_vars, value_vars, var_name="variable", value_name="value") -> ReshapeResult`

Convert wide format to long format.

**Example:**
```python
result = reshaping.melt_wide_to_long(
    df=df_wide,
    id_vars=["sample_id"],
    value_vars=[f"option_{i}" for i in range(1, 201)],
    var_name="option_id",
    value_name="value"
)
```

#### `pivot_long_to_wide(df, index, columns, values) -> ReshapeResult`

Convert long format to wide format.

**Example:**
```python
result = reshaping.pivot_long_to_wide(
    df=df_long,
    index="sample_id",
    columns="option_id",
    values="value"
)
```

#### `detect_wide_format(df, threshold_columns=50) -> bool`

Detect if DataFrame is in wide format.

**Example:**
```python
is_wide = reshaping.detect_wide_format(df, threshold_columns=50)
```

#### `generate_normalized_mapping(id_column, entity_type, variable_type, relation_type) -> SchemaMapping`

Generate schema mapping for normalized structure.

**Example:**
```python
mapping = reshaping.generate_normalized_mapping(
    id_column="sample_id",
    entity_type="Sample",
    variable_type="Option",
    relation_type="HAS_VALUE"
)
```

**Returns:** `ReshapeResult` with:
- `data` (DataFrame): Reshaped DataFrame
- `original_shape` (tuple): Original (rows, cols) shape
- `new_shape` (tuple): New (rows, cols) shape
- `id_columns` (List[str]): ID columns used
- `variable_column` (str): Variable column name (for melt)
- `value_column` (str): Value column name (for melt)
- `warnings` (List[str]): Warnings

### DataQualityValidator

Validate data quality during import.

**Module**: `aiecs.application.knowledge_graph.builder.data_quality`

```python
from aiecs.application.knowledge_graph.builder.data_quality import (
    DataQualityValidator,
    ValidationConfig,
    RangeRule,
    OutlierRule,
    QualityReport
)
```

**ValidationConfig:**

```python
validation_config = ValidationConfig(
    rules={
        "EntityType": {
            "property_name": RangeRule(min=0.0, max=1.0)
        }
    },
    outlier_detection={
        "EntityType": {
            "property_name": OutlierRule(method="zscore", threshold=3.0)
        }
    },
    required_properties={
        "EntityType": ["property1", "property2"]
    },
    fail_on_violations=False
)
```

**Methods:**

#### `validate_row(row, row_idx) -> bool`

Validate a single row.

**Example:**
```python
validator = DataQualityValidator(validation_config)
is_valid = validator.validate_row(row, row_idx=0)
```

#### `validate_dataframe(df) -> QualityReport`

Validate entire DataFrame.

**Example:**
```python
report = validator.validate_dataframe(df)
print(f"Violations: {len(report.range_violations)}")
print(f"Completeness: {report.completeness}")
```

**Returns:** `QualityReport` with:
- `range_violations` (List[QualityViolation]): Range validation violations
- `outliers` (List[Outlier]): Detected outliers
- `completeness` (Dict[str, float]): Completeness percentage per property
- `summary` (Dict[str, Any]): Summary statistics

### PerformanceMetrics

Track import performance metrics.

**Module**: `aiecs.application.knowledge_graph.builder.import_optimizer`

```python
from aiecs.application.knowledge_graph.builder.import_optimizer import PerformanceMetrics

metrics = result.performance_metrics
```

**Attributes:**
- `total_time` (float): Total import time in seconds
- `read_time` (float): File reading time
- `transform_time` (float): Data transformation time
- `write_time` (float): Graph store write time
- `rows_per_second` (float): Import throughput
- `peak_memory_mb` (float): Peak memory usage in MB
- `optimal_batch_size` (int): Optimal batch size used

**Example:**
```python
if result.performance_metrics:
    metrics = result.performance_metrics
    print(f"Throughput: {metrics.rows_per_second:.0f} rows/sec")
    print(f"Peak memory: {metrics.peak_memory_mb:.1f} MB")
```

**Methods:**

#### `import_from_csv(file_path)`

Import data from CSV file.

**Returns:**
```python
ImportResult(
    success=bool,
    entities_added=int,
    relations_added=int,
    rows_processed=int,
    rows_failed=int,
    duration_seconds=float,
    errors=List[str],
    warnings=List[str]
)
```

**Performance:** 100-300 rows/second

#### `import_from_json(file_path)`

Import data from JSON file.

**Performance:** 100-250 records/second

## Tools

### KnowledgeGraphBuilderTool

Build knowledge graphs from various sources.

```python
from aiecs.tools.knowledge_graph import KnowledgeGraphBuilderTool

builder = KnowledgeGraphBuilderTool()
await builder._initialize()
```

**Actions:**
- `build_from_text` - Extract from text
- `build_from_document` - Process documents
- `build_from_structured_data` - Import CSV/JSON
- `get_stats` - Get graph statistics

See [Graph Builder Tool](./tools/GRAPH_BUILDER_TOOL.md) for details.

### GraphSearchTool

Search knowledge graphs with reranking.

```python
from aiecs.tools.knowledge_graph import GraphSearchTool

tool = GraphSearchTool()
await tool._initialize()
```

**Modes:**
- `vector` - Vector similarity search
- `graph` - Graph traversal search
- `hybrid` - Combined search

**Reranking:**
- `enable_reranking` - Enable/disable reranking
- `rerank_strategy` - text, semantic, structural, hybrid

See [Graph Search Tool](./tools/GRAPH_SEARCH_TOOL.md) for details.

### GraphReasoningTool

Logical reasoning and query parsing.

```python
from aiecs.tools.knowledge_graph import GraphReasoningTool

tool = GraphReasoningTool()
await tool._initialize()
```

**Modes:**
- `query_plan` - Plan query execution
- `multi_hop` - Multi-hop reasoning
- `inference` - Logical inference
- `logical_query` - Parse to logical form
- `full_reasoning` - Complete pipeline

See [Graph Reasoning Tool](./tools/GRAPH_REASONING_TOOL.md) for details.

## See Also

- [Configuration Guide](./CONFIGURATION_GUIDE.md)
- [Performance Guide](./PERFORMANCE_GUIDE.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

