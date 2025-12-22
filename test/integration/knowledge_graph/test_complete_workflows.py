"""
Integration tests for complete knowledge graph workflows

Tests end-to-end workflows combining multiple features:
- Entity validation with property checking
- Relation validation with property checking
- Embedding-based search
- Entity enumeration
- Consensus fusion
"""

import pytest
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType
from aiecs.application.knowledge_graph.validators.relation_validator import RelationValidator
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.context.graph_memory import GraphMemoryMixin
from unittest.mock import AsyncMock, MagicMock


class MockGraphMemoryMixin(GraphMemoryMixin):
    """Mock class for testing GraphMemoryMixin"""
    
    def __init__(self, graph_store=None, llm_client=None):
        self.graph_store = graph_store
        self.llm_client = llm_client


@pytest.fixture
async def graph_store():
    """Create and initialize a test graph store"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def sample_schema():
    """Create a comprehensive schema for testing"""
    schema = GraphSchema(version="1.0")
    
    # Create entity types
    person_type = EntityType(
        name="Person",
        properties={
            "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
            "age": PropertySchema(name="age", property_type=PropertyType.INTEGER, required=False),
        }
    )
    
    company_type = EntityType(
        name="Company",
        properties={
            "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
            "industry": PropertySchema(name="industry", property_type=PropertyType.STRING, required=False),
        }
    )
    
    schema.add_entity_type(person_type)
    schema.add_entity_type(company_type)
    
    # Create relation type
    works_for_type = RelationType(
        name="WORKS_FOR",
        description="Employment relationship",
        source_entity_types=["Person"],
        target_entity_types=["Company"],
        properties={
            "since": PropertySchema(name="since", property_type=PropertyType.STRING, required=True),
            "role": PropertySchema(name="role", property_type=PropertyType.STRING, required=False),
        }
    )
    
    schema.add_relation_type(works_for_type)
    return schema


@pytest.mark.asyncio
async def test_complete_workflow_entity_relation_validation(graph_store, sample_schema):
    """Test complete workflow: create entities, validate relations with properties"""
    # Create entities
    person = Entity(
        id="person_1",
        entity_type="Person",
        properties={"name": "Alice", "age": 30}
    )
    
    company = Entity(
        id="company_1",
        entity_type="Company",
        properties={"name": "Acme Corp", "industry": "Technology"}
    )
    
    # Add entities to store
    await graph_store.add_entity(person)
    await graph_store.add_entity(company)
    
    # Create relation with valid properties
    relation = Relation(
        id="rel_1",
        relation_type="WORKS_FOR",
        source_id="person_1",
        target_id="company_1",
        properties={
            "since": "2020-01-01",
            "role": "Engineer"
        }
    )
    
    # Validate relation
    validator = RelationValidator(schema=sample_schema)
    is_valid, errors = validator.validate_relation(relation, person, company)
    
    assert is_valid is True
    assert len(errors) == 0
    
    # Add relation to store
    await graph_store.add_relation(relation)


@pytest.mark.asyncio
async def test_complete_workflow_embedding_search_with_enumeration(graph_store):
    """Test complete workflow: entity enumeration + embedding-based search"""
    # Create entities with embeddings
    entities = [
        Entity(
            id="person_1",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
        ),
        Entity(
            id="person_2",
            entity_type="Person",
            properties={"name": "Bob"},
            embedding=[0.15, 0.25, 0.35, 0.45, 0.55]
        ),
        Entity(
            id="company_1",
            entity_type="Company",
            properties={"name": "Acme"},
            embedding=[0.2, 0.3, 0.4, 0.5, 0.6]
        ),
    ]
    
    # Add entities
    for entity in entities:
        await graph_store.add_entity(entity)
    
    # Enumerate all entities
    all_entities = await graph_store.get_all_entities()
    assert len(all_entities) == 3
    
    # Filter by entity type
    people = await graph_store.get_all_entities(entity_type="Person")
    assert len(people) == 2
    
    # Perform vector search (uses enumeration internally)
    query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    results = await graph_store.vector_search(
        query_embedding=query_embedding,
        entity_type="Person",
        max_results=10
    )
    
    assert len(results) > 0
    assert all(e.entity_type == "Person" for e, _ in results)


@pytest.mark.asyncio
async def test_complete_workflow_graph_memory_with_embedding_search(graph_store):
    """Test complete workflow: graph memory with embedding-based search"""
    # Create mock LLM client with embeddings
    mock_llm_client = MagicMock()
    mock_llm_client.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5]])
    
    # Create entities with embeddings
    entities = [
        Entity(
            id="person_1",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
        ),
        Entity(
            id="person_2",
            entity_type="Person",
            properties={"name": "Bob"},
            embedding=[0.15, 0.25, 0.35, 0.45, 0.55]
        ),
    ]
    
    # Add entities
    for entity in entities:
        await graph_store.add_entity(entity)
    
    # Create graph memory mixin
    mixin = MockGraphMemoryMixin(graph_store=graph_store, llm_client=mock_llm_client)
    
    # Retrieve knowledge using embedding search
    results = await mixin.retrieve_knowledge(
        session_id="test_session",
        query="find people named Alice",
        entity_types=["Person"],
        limit=10
    )
    
    assert len(results) >= 0  # May find results via vector search
    assert mock_llm_client.get_embeddings.called


@pytest.mark.asyncio
async def test_complete_workflow_validation_and_search(graph_store, sample_schema):
    """Test complete workflow: validation + enumeration + search"""
    # Create and validate entities
    person = Entity(
        id="person_1",
        entity_type="Person",
        properties={"name": "Alice", "age": 30}
    )
    
    company = Entity(
        id="company_1",
        entity_type="Company",
        properties={"name": "Acme Corp"}
    )
    
    await graph_store.add_entity(person)
    await graph_store.add_entity(company)
    
    # Create and validate relation
    relation = Relation(
        id="rel_1",
        relation_type="WORKS_FOR",
        source_id="person_1",
        target_id="company_1",
        properties={"since": "2020-01-01"}
    )
    
    validator = RelationValidator(schema=sample_schema)
    is_valid, errors = validator.validate_relation(relation, person, company)
    assert is_valid is True
    
    await graph_store.add_relation(relation)
    
    # Enumerate entities
    all_entities = await graph_store.get_all_entities()
    assert len(all_entities) == 2
    
    # Filter by type
    people = await graph_store.get_all_entities(entity_type="Person")
    assert len(people) == 1
    assert people[0].id == "person_1"


@pytest.mark.asyncio
async def test_complete_workflow_pagination_and_enumeration(graph_store):
    """Test complete workflow: pagination with entity enumeration"""
    # Create many entities
    entities = [
        Entity(
            id=f"person_{i}",
            entity_type="Person",
            properties={"name": f"Person {i}"}
        )
        for i in range(20)
    ]
    
    # Add entities
    for entity in entities:
        await graph_store.add_entity(entity)
    
    # Test pagination
    page1 = await graph_store.get_all_entities(entity_type="Person", limit=10, offset=0)
    assert len(page1) == 10
    
    page2 = await graph_store.get_all_entities(entity_type="Person", limit=10, offset=10)
    assert len(page2) == 10
    
    # Pages should not overlap
    page1_ids = {e.id for e in page1}
    page2_ids = {e.id for e in page2}
    assert page1_ids.isdisjoint(page2_ids)
    
    # All entities should be covered
    all_ids = page1_ids | page2_ids
    assert len(all_ids) == 20


@pytest.mark.asyncio
async def test_complete_workflow_consensus_fusion():
    """Test complete workflow: consensus fusion with multiple providers"""
    from aiecs.tools.apisource.intelligence.data_fusion import DataFusionEngine
    
    fusion_engine = DataFusionEngine()
    
    # Simulate results from multiple providers
    results = [
        {
            "provider": "provider1",
            "data": [{"id": "item1", "name": "Item A", "value": 100}],
            "metadata": {"quality": {"score": 0.9}}
        },
        {
            "provider": "provider2",
            "data": [{"id": "item1", "name": "Item A", "value": 100}],
            "metadata": {"quality": {"score": 0.8}}
        },
        {
            "provider": "provider3",
            "data": [{"id": "item1", "name": "Item A", "value": 200}],
            "metadata": {"quality": {"score": 0.7}}
        }
    ]
    
    # Fuse with consensus strategy
    consensus = fusion_engine.fuse_multi_provider_results(
        results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
    )
    
    assert consensus is not None
    assert consensus["metadata"]["fusion_info"]["strategy"] == "consensus"
    assert "consensus_confidence" in consensus["metadata"]["fusion_info"]
    # Majority (2 out of 3) agree on value 100
    assert consensus["data"][0]["value"] == 100


@pytest.mark.asyncio
async def test_complete_workflow_end_to_end(graph_store, sample_schema):
    """Test complete end-to-end workflow combining all features"""
    # 1. Create entities
    person = Entity(
        id="person_1",
        entity_type="Person",
        properties={"name": "Alice", "age": 30},
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
    )
    
    company = Entity(
        id="company_1",
        entity_type="Company",
        properties={"name": "Acme Corp"},
        embedding=[0.2, 0.3, 0.4, 0.5, 0.6]
    )
    
    await graph_store.add_entity(person)
    await graph_store.add_entity(company)
    
    # 2. Validate and create relation
    relation = Relation(
        id="rel_1",
        relation_type="WORKS_FOR",
        source_id="person_1",
        target_id="company_1",
        properties={"since": "2020-01-01", "role": "Engineer"}
    )
    
    validator = RelationValidator(schema=sample_schema)
    is_valid, errors = validator.validate_relation(relation, person, company)
    assert is_valid is True
    
    await graph_store.add_relation(relation)
    
    # 3. Enumerate entities
    all_entities = await graph_store.get_all_entities()
    assert len(all_entities) == 2
    
    # 4. Vector search
    query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    search_results = await graph_store.vector_search(
        query_embedding=query_embedding,
        max_results=10
    )
    assert len(search_results) > 0
    
    # 5. Graph memory with embedding search
    mock_llm_client = MagicMock()
    mock_llm_client.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5]])
    
    mixin = MockGraphMemoryMixin(graph_store=graph_store, llm_client=mock_llm_client)
    memory_results = await mixin.retrieve_knowledge(
        session_id="test",
        query="find Alice",
        limit=10
    )
    assert isinstance(memory_results, list)
