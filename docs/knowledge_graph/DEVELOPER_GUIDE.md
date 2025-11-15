# AIECS Knowledge Graph Developer Guide

## Introduction

This guide is for developers who want to extend the AIECS Knowledge Graph system with custom components. Whether you're adding a new storage backend, creating custom extractors, or implementing specialized reasoning algorithms, this guide will help you understand the architecture and extension points.

## Architecture Overview

AIECS Knowledge Graph follows clean architecture principles with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                         Tools Layer                          │
│  (KnowledgeGraphBuilderTool, GraphSearchTool, etc.)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  (GraphBuilder, ReasoningEngine, KnowledgeFusion, etc.)     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       Domain Layer                           │
│  (Entity, Relation, Path, SchemaManager, etc.)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                       │
│  (GraphStore implementations: InMemory, SQLite, PostgreSQL) │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Domain Independence**: Domain models have no external dependencies
2. **Interface Segregation**: Small, focused interfaces
3. **Dependency Inversion**: Depend on abstractions, not implementations
4. **Two-Tier Design**: Minimal required interface + optional optimizations

## Extension Points

### 1. Custom Storage Backends

The most common extension is adding a new storage backend (Neo4j, ArangoDB, etc.).

**See**: [Custom Backend Guide](./backend/CUSTOM_BACKEND_GUIDE.md) for detailed instructions.

**Quick Example**:

```python
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from typing import Optional, List

class Neo4jGraphStore(GraphStore):
    """Neo4j storage backend"""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None

    # Implement Tier 1 methods (required)
    async def initialize(self) -> None:
        from neo4j import AsyncGraphDatabase
        self.driver = AsyncGraphDatabase.driver(
            self.uri, auth=(self.user, self.password)
        )

    async def close(self) -> None:
        if self.driver:
            await self.driver.close()

    async def add_entity(self, entity: Entity) -> None:
        async with self.driver.session() as session:
            await session.run(
                "CREATE (n:Entity {id: $id, type: $type, properties: $props})",
                id=entity.id,
                type=entity.entity_type,
                props=entity.properties
            )

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n:Entity {id: $id}) RETURN n",
                id=entity_id
            )
            record = await result.single()
            if record:
                node = record["n"]
                return Entity(
                    id=node["id"],
                    entity_type=node["type"],
                    properties=node["properties"]
                )
            return None

    # ... implement other Tier 1 methods

    # Optionally override Tier 2 for performance
    async def traverse(self, start_entity_id: str, **kwargs) -> List[Path]:
        # Use Cypher for optimized traversal
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH path = (start:Entity {id: $id})-[*1..3]->()
                RETURN path
                """,
                id=start_entity_id
            )
            # Convert Cypher paths to Path objects
            paths = []
            async for record in result:
                # ... convert to Path
                pass
            return paths
```

**Testing Your Backend**:

```python
import pytest
from your_module import Neo4jGraphStore

@pytest.mark.asyncio
async def test_neo4j_backend():
    store = Neo4jGraphStore("bolt://localhost:7687", "neo4j", "password")
    await store.initialize()

    # Test Tier 1 methods
    entity = Entity(id="test", entity_type="Person", properties={"name": "Alice"})
    await store.add_entity(entity)

    retrieved = await store.get_entity("test")
    assert retrieved.id == "test"
    assert retrieved.properties["name"] == "Alice"

    # Test Tier 2 methods work
    paths = await store.traverse("test", max_depth=2)
    assert isinstance(paths, list)

    await store.close()
```

### 2. Custom Entity Extractors

Create custom extractors for domain-specific entity recognition.


**Example: Domain-Specific Extractor**:

```python
import re
from aiecs.application.knowledge_graph.extractors.base_extractor import BaseExtractor

class MedicalEntityExtractor(BaseExtractor):
    """Extract medical entities (diseases, symptoms, medications)"""

    def __init__(self):
        # Load medical terminology dictionaries
        self.diseases = self._load_disease_dict()
        self.medications = self._load_medication_dict()

    async def extract_entities(self, text: str, entity_types: Optional[List[str]] = None) -> List[Entity]:
        entities = []

        # Extract diseases
        if not entity_types or "Disease" in entity_types:
            for disease in self.diseases:
                if disease.lower() in text.lower():
                    entities.append(Entity(
                        id=f"disease_{disease.lower().replace(' ', '_')}",
                        entity_type="Disease",
                        properties={"name": disease},
                        metadata={"source": "medical_dict", "confidence": 0.9}
                    ))

        # Extract medications
        if not entity_types or "Medication" in entity_types:
            for med in self.medications:
                if med.lower() in text.lower():
                    entities.append(Entity(
                        id=f"med_{med.lower().replace(' ', '_')}",
                        entity_type="Medication",
                        properties={"name": med},
                        metadata={"source": "medical_dict", "confidence": 0.9}
                    ))

        return entities

    def _load_disease_dict(self) -> List[str]:
        # Load from file or database
        return ["diabetes", "hypertension", "asthma", ...]

    def _load_medication_dict(self) -> List[str]:
        return ["aspirin", "metformin", "lisinopril", ...]
```

**Using Your Custom Extractor**:

```python
from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder

# Create builder with custom extractor
extractor = MedicalEntityExtractor()
builder = GraphBuilder(
    graph_store=store,
    entity_extractor=extractor,
    relation_extractor=relation_extractor
)

# Extract from medical text
text = "Patient diagnosed with diabetes and prescribed metformin."
result = await builder.build_from_text(text)
```

### 3. Custom Relation Extractors

Extract domain-specific relationships between entities.

**Base Class**: `aiecs.application.knowledge_graph.extractors.base_extractor.BaseExtractor`

```python
from aiecs.application.knowledge_graph.extractors.base_extractor import BaseExtractor
from aiecs.domain.knowledge_graph.models.relation import Relation
from typing import List

class CustomRelationExtractor(BaseExtractor):
    """Extract relations using custom logic"""

    async def extract_relations(
        self,
        text: str,
        entities: List[Entity],
        relation_types: Optional[List[str]] = None
    ) -> List[Relation]:
        """
        Extract relations from text given entities

        Args:
            text: Input text
            entities: Entities found in text
            relation_types: Optional filter for relation types

        Returns:
            List of extracted relations
        """
        relations = []

        # Your custom relation extraction logic
        # Example: Pattern matching, dependency parsing, or ML models

        return relations
```

**Example: Pattern-Based Relation Extractor**:

```python
import re

class PatternRelationExtractor(BaseExtractor):
    """Extract relations using regex patterns"""

    def __init__(self):
        self.patterns = {
            "WORKS_FOR": [
                r"(\w+)\s+works\s+(?:for|at)\s+(\w+)",
                r"(\w+)\s+is\s+employed\s+by\s+(\w+)",
            ],
            "LOCATED_IN": [
                r"(\w+)\s+is\s+located\s+in\s+(\w+)",
                r"(\w+)\s+in\s+(\w+)",
            ]
        }

    async def extract_relations(
        self,
        text: str,
        entities: List[Entity],
        relation_types: Optional[List[str]] = None
    ) -> List[Relation]:
        relations = []
        entity_map = {e.properties.get("name", ""): e for e in entities}

        for rel_type, patterns in self.patterns.items():
            if relation_types and rel_type not in relation_types:
                continue

            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    source_name = match.group(1)
                    target_name = match.group(2)

                    if source_name in entity_map and target_name in entity_map:
                        relations.append(Relation(
                            id=f"rel_{len(relations)}",
                            relation_type=rel_type,
                            source_id=entity_map[source_name].id,
                            target_id=entity_map[target_name].id,
                            metadata={"source": "pattern_match", "confidence": 0.8}
                        ))

        return relations
```

### 4. Custom Retrieval Strategies

Implement specialized retrieval algorithms for your use case.

**Base Class**: `aiecs.application.knowledge_graph.retrieval.base_retrieval.BaseRetrieval`

```python
from aiecs.application.knowledge_graph.retrieval.base_retrieval import BaseRetrieval
from aiecs.domain.knowledge_graph.models.entity import Entity
from typing import List

class CustomRetrievalStrategy(BaseRetrieval):
    """Custom retrieval strategy"""

    def __init__(self, graph_store, **kwargs):
        self.graph_store = graph_store
        self.config = kwargs

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        **kwargs
    ) -> List[Entity]:
        """
        Retrieve entities using custom strategy

        Args:
            query: Query string
            top_k: Number of results to return
            **kwargs: Additional parameters

        Returns:
            List of retrieved entities
        """
        # Your custom retrieval logic
        results = []

        return results[:top_k]
```

**Example: Time-Aware Retrieval**:

```python
from datetime import datetime, timedelta

class TimeAwareRetrieval(BaseRetrieval):
    """Retrieve entities with time-based relevance decay"""

    async def retrieve(self, query: str, top_k: int = 10, **kwargs) -> List[Entity]:
        # Get all entities matching query
        all_entities = await self._get_matching_entities(query)

        # Score by recency
        now = datetime.now()
        scored_entities = []

        for entity in all_entities:
            created_at = entity.metadata.get("created_at")
            if created_at:
                age_days = (now - datetime.fromisoformat(created_at)).days
                # Exponential decay: score = base_score * e^(-decay_rate * age)
                decay_rate = 0.01
                time_score = math.exp(-decay_rate * age_days)

                base_score = entity.metadata.get("relevance_score", 0.5)
                final_score = base_score * time_score

                scored_entities.append((entity, final_score))

        # Sort by score and return top_k
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return [e for e, _ in scored_entities[:top_k]]
```

### 5. Custom Reasoning Algorithms

Implement specialized reasoning logic for your domain.

**Example: Custom Inference Rule**:

```python
from aiecs.domain.knowledge_graph.models.inference_rule import InferenceRule, RuleType
from aiecs.application.knowledge_graph.reasoning.inference_engine import InferenceEngine

class CustomInferenceEngine(InferenceEngine):
    """Inference engine with custom rules"""

    def __init__(self, graph_store):
        super().__init__(graph_store)
        self._register_custom_rules()

    def _register_custom_rules(self):
        # Add domain-specific inference rules

        # Rule: If A manages B and B manages C, then A indirectly manages C
        self.add_rule(InferenceRule(
            rule_id="transitive_management",
            rule_type=RuleType.TRANSITIVE,
            name="Transitive Management",
            description="Management hierarchy is transitive",
            conditions=[
                {"relation_type": "MANAGES"},
                {"relation_type": "MANAGES"}
            ],
            conclusion={
                "relation_type": "INDIRECTLY_MANAGES",
                "properties": {"inferred": True}
            },
            confidence=0.9
        ))

        # Rule: If A works_for B and B is_subsidiary_of C, then A works_for C
        self.add_rule(InferenceRule(
            rule_id="subsidiary_employment",
            rule_type=RuleType.CUSTOM,
            name="Subsidiary Employment",
            description="Employees of subsidiaries work for parent company",
            conditions=[
                {"relation_type": "WORKS_FOR"},
                {"relation_type": "SUBSIDIARY_OF"}
            ],
            conclusion={
                "relation_type": "WORKS_FOR",
                "properties": {"indirect": True, "inferred": True}
            },
            confidence=0.85
        ))
```

### 6. Custom Tools

Create custom tools that expose your knowledge graph capabilities to agents.

**Base Class**: `aiecs.tools.base_tool.BaseTool`

```python
from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool
from typing import Dict, Any

@register_tool("custom_kg_tool")
class CustomKnowledgeGraphTool(BaseTool):
    """Custom knowledge graph tool"""

    name = "custom_kg_tool"
    description = "Custom knowledge graph operations"

    def __init__(self, graph_store=None):
        super().__init__()
        self.graph_store = graph_store

    async def _initialize(self):
        """Initialize tool resources"""
        if not self.graph_store:
            from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
            self.graph_store = InMemoryGraphStore()
            await self.graph_store.initialize()

    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool operation

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Operation result
        """
        operation = kwargs.get("operation")

        if operation == "custom_search":
            return await self._custom_search(**kwargs)
        elif operation == "custom_analysis":
            return await self._custom_analysis(**kwargs)
        else:
            return {"error": f"Unknown operation: {operation}"}

    async def _custom_search(self, **kwargs) -> Dict[str, Any]:
        """Custom search logic"""
        query = kwargs.get("query")
        # Your custom search implementation
        results = []
        return {"results": results}

    async def _custom_analysis(self, **kwargs) -> Dict[str, Any]:
        """Custom analysis logic"""
        # Your custom analysis implementation
        return {"analysis": "..."}
```

## Best Practices

### 1. Follow Clean Architecture

- **Domain Layer**: Pure business logic, no external dependencies
- **Application Layer**: Use cases and services, orchestrate domain objects
- **Infrastructure Layer**: External integrations, database adapters
- **Tools Layer**: Agent-facing interfaces

### 2. Use Type Hints

Always use type hints for better IDE support and type safety:

```python
from typing import List, Optional, Dict, Any
from aiecs.domain.knowledge_graph.models.entity import Entity

async def my_function(
    entities: List[Entity],
    config: Optional[Dict[str, Any]] = None
) -> List[Entity]:
    ...
```

### 3. Add Comprehensive Tests

Test all extension points:

```python
import pytest
from your_module import CustomExtractor

@pytest.mark.asyncio
async def test_custom_extractor():
    extractor = CustomExtractor()

    text = "Test input"
    entities = await extractor.extract_entities(text)

    assert len(entities) > 0
    assert all(isinstance(e, Entity) for e in entities)
```

### 4. Document Your Extensions

Add docstrings and examples:

```python
class CustomBackend(GraphStore):
    """
    Custom graph storage backend for XYZ database.

    This backend provides optimized storage for large-scale graphs
    using XYZ's native graph capabilities.

    Example:
        ```python
        store = CustomBackend(connection_string="...")
        await store.initialize()

        await store.add_entity(entity)
        neighbors = await store.get_neighbors("entity_1")
        ```

    Args:
        connection_string: Database connection string
        pool_size: Connection pool size (default: 10)
    """
    ...
```

### 5. Handle Errors Gracefully

```python
from aiecs.domain.knowledge_graph.exceptions import GraphStoreError

async def my_operation(self, entity_id: str) -> Entity:
    try:
        entity = await self.graph_store.get_entity(entity_id)
        if not entity:
            raise GraphStoreError(f"Entity not found: {entity_id}")
        return entity
    except Exception as e:
        logger.error(f"Error retrieving entity: {e}")
        raise
```

## Testing Your Extensions

### Unit Tests

Test individual components in isolation:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_custom_extractor():
    extractor = CustomExtractor()

    # Test with mock data
    text = "Alice works at Tech Corp"
    entities = await extractor.extract_entities(text)

    assert len(entities) == 2
    assert entities[0].entity_type == "Person"
    assert entities[1].entity_type == "Company"
```

### Integration Tests

Test components working together:

```python
@pytest.mark.asyncio
async def test_custom_backend_integration():
    store = CustomBackend("test_connection")
    await store.initialize()

    # Test full workflow
    entity = Entity(id="test", entity_type="Person", properties={"name": "Alice"})
    await store.add_entity(entity)

    retrieved = await store.get_entity("test")
    assert retrieved.id == "test"

    # Test Tier 2 methods
    paths = await store.traverse("test", max_depth=2)
    assert isinstance(paths, list)

    await store.close()
```

### Performance Tests

Benchmark your extensions:

```python
import time

@pytest.mark.asyncio
async def test_custom_backend_performance():
    store = CustomBackend()
    await store.initialize()

    # Benchmark entity insertion
    start = time.time()
    for i in range(1000):
        await store.add_entity(Entity(
            id=f"entity_{i}",
            entity_type="Test",
            properties={"index": i}
        ))
    duration = time.time() - start

    print(f"Inserted 1000 entities in {duration:.2f}s")
    assert duration < 10.0  # Should complete in < 10 seconds

    await store.close()
```

## Resources

- **API Reference**: [API_REFERENCE.md](./API_REFERENCE.md)
- **Custom Backend Guide**: [backend/CUSTOM_BACKEND_GUIDE.md](./backend/CUSTOM_BACKEND_GUIDE.md)
- **Examples**: [examples/](./examples/)
- **Source Code**: `aiecs/domain/knowledge_graph/`, `aiecs/application/knowledge_graph/`, `aiecs/infrastructure/graph_storage/`

## Getting Help

- **Documentation**: Browse the [docs/knowledge_graph/](.) directory
- **Examples**: Study the examples in [examples/](./examples/)
- **Source Code**: Read the implementation in `aiecs/`
- **Issues**: Report bugs or request features on GitHub

Happy extending! 🚀



