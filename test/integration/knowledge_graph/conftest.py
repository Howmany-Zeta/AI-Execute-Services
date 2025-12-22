"""
Test configuration for knowledge graph integration tests

Provides fixtures for:
- PostgreSQL graph store with real connection
- LLM clients for real API calls
- Test data setup
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env.test file before importing any aiecs modules
env_test_path = Path(__file__).parent.parent.parent.parent / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
    print(f"Loaded environment from {env_test_path}")
else:
    print(f"Warning: .env.test not found at {env_test_path}")

from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore
from aiecs.config.config import get_settings
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.llm import AIProvider


@pytest.fixture
def setup_kg_builder_tool_with_store():
    """Fixture factory to set up KnowledgeGraphBuilderTool with a custom graph store"""
    def _setup(graph_store):
        from aiecs.tools.knowledge_graph.kg_builder_tool import KnowledgeGraphBuilderTool
        from aiecs.application.knowledge_graph.extractors.llm_entity_extractor import LLMEntityExtractor
        from aiecs.application.knowledge_graph.extractors.llm_relation_extractor import LLMRelationExtractor
        from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder
        from aiecs.application.knowledge_graph.builder.document_builder import DocumentGraphBuilder
        
        tool = KnowledgeGraphBuilderTool()
        tool.graph_store = graph_store
        tool._initialized = True
        
        # Use XAI provider if XAI_API_KEY is set, otherwise use default
        # Check which API keys are available
        settings = get_settings()
        if settings.xai_api_key:
            provider = AIProvider.XAI
        elif settings.openai_api_key:
            provider = AIProvider.OPENAI
        elif settings.googleai_api_key:
            provider = AIProvider.GOOGLEAI
        elif settings.vertex_project_id:
            provider = AIProvider.VERTEX
        else:
            provider = None  # Will use default
        
        entity_extractor = LLMEntityExtractor(provider=provider)
        relation_extractor = LLMRelationExtractor(provider=provider)
        
        tool.graph_builder = GraphBuilder(
            graph_store=tool.graph_store,
            entity_extractor=entity_extractor,
            relation_extractor=relation_extractor,
            enable_deduplication=True,
            enable_linking=True
        )
        
        tool.document_builder = DocumentGraphBuilder(
            graph_builder=tool.graph_builder,
            chunk_size=2000,
            enable_chunking=True
        )
        
        return tool
    return _setup


@pytest.fixture
def setup_graph_search_tool_with_store():
    """Fixture factory to set up GraphSearchTool with a custom graph store"""
    def _setup(graph_store):
        from aiecs.tools.knowledge_graph.graph_search_tool import GraphSearchTool
        from aiecs.application.knowledge_graph.search.hybrid_search import HybridSearchStrategy
        from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
            PersonalizedPageRank,
            MultiHopRetrieval,
            FilteredRetrieval,
            RetrievalCache
        )
        from aiecs.application.knowledge_graph.traversal.enhanced_traversal import EnhancedTraversal
        
        tool = GraphSearchTool()
        tool.graph_store = graph_store
        tool._initialized = True
        
        # Use correct attribute names with _strategy suffix
        tool.hybrid_search_strategy = HybridSearchStrategy(tool.graph_store)
        tool.pagerank_strategy = PersonalizedPageRank(tool.graph_store)
        tool.multihop_strategy = MultiHopRetrieval(tool.graph_store)
        tool.filtered_strategy = FilteredRetrieval(tool.graph_store)
        tool.traversal_strategy = EnhancedTraversal(tool.graph_store)
        tool.cache = RetrievalCache(max_size=100, ttl=300)
        
        return tool
    return _setup


@pytest.fixture(scope="function")
async def postgres_store():
    """
    Fixture providing initialized PostgreSQL graph store with real connection.
    Uses configuration from .env.test file.
    Skips test if PostgreSQL is not available.
    """
    import asyncpg
    
    settings = get_settings()
    
    # Try to create store with settings from .env.test
    try:
        store = PostgresGraphStore(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            min_pool_size=2,
            max_pool_size=5
        )
        
        await store.initialize()
    except (asyncpg.exceptions.InvalidPasswordError, 
            asyncpg.exceptions.ConnectionDoesNotExistError,
            OSError,
            Exception) as e:
        pytest.skip(f"PostgreSQL not available or connection failed: {e}")
    
    # Clean up any existing test data
    try:
        async with store.pool.acquire() as conn:
            await conn.execute("DELETE FROM graph_relations")
            await conn.execute("DELETE FROM graph_entities")
    except Exception as e:
        print(f"Warning: Could not clean test data: {e}")
    
    yield store
    
    # Cleanup after test
    try:
        async with store.pool.acquire() as conn:
            await conn.execute("DELETE FROM graph_relations")
            await conn.execute("DELETE FROM graph_entities")
    except Exception as e:
        print(f"Warning: Could not clean test data: {e}")
    
    try:
        await store.close()
    except Exception as e:
        print(f"Warning: Error closing store: {e}")


@pytest.fixture(scope="function")
async def populated_postgres_store(postgres_store):
    """
    Fixture providing PostgreSQL store with test data populated.
    """
    store = postgres_store
    
    # Add test entities with embeddings for vector search support
    # Using simple embeddings (128 dimensions) for testing
    alice = Entity(
        id="alice",
        entity_type="Person",
        properties={"name": "Alice", "age": 30, "role": "Engineer"},
        embedding=[0.1] * 128  # Simple embedding for vector search
    )
    bob = Entity(
        id="bob",
        entity_type="Person",
        properties={"name": "Bob", "age": 35, "role": "Manager"},
        embedding=[0.2] * 128  # Simple embedding for vector search
    )
    company = Entity(
        id="tech_corp",
        entity_type="Company",
        properties={"name": "Tech Corp", "industry": "Technology"},
        embedding=[0.3] * 128  # Simple embedding for vector search
    )
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(company)
    
    # Add test relations
    works_for = Relation(
        id="r1",
        relation_type="WORKS_FOR",
        source_id="alice",
        target_id="tech_corp"
    )
    knows = Relation(
        id="r2",
        relation_type="KNOWS",
        source_id="alice",
        target_id="bob"
    )
    
    await store.add_relation(works_for)
    await store.add_relation(knows)
    
    yield store


@pytest.fixture(scope="session")
def llm_available():
    """
    Check if LLM API keys are available for real API calls.
    """
    settings = get_settings()
    
    # Check for any available LLM provider
    has_openai = bool(settings.openai_api_key)
    has_googleai = bool(settings.googleai_api_key)
    has_vertex = bool(settings.vertex_project_id)
    has_xai = bool(settings.xai_api_key)
    
    available = has_openai or has_googleai or has_vertex or has_xai
    
    if not available:
        pytest.skip("No LLM API keys configured in .env.test. Skipping tests requiring LLM.")
    
    return available

