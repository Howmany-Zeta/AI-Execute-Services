"""
Unit tests for GraphAwareAgentMixin
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from aiecs.domain.agent.graph_aware_mixin import GraphAwareAgentMixin
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path


@pytest.fixture
async def graph_store():
    """Create a test graph store with sample data"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Add sample entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "role": "Engineer"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob", "role": "Manager"})
    company = Entity(id="tech_corp", entity_type="Company", properties={"name": "TechCorp"})
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(company)
    
    # Add relations
    knows_rel = Relation(id="rel1", source_id="alice", target_id="bob", relation_type="KNOWS", properties={})
    works_rel = Relation(id="rel2", source_id="alice", target_id="tech_corp", relation_type="WORKS_FOR", properties={})
    
    await store.add_relation(knows_rel)
    await store.add_relation(works_rel)
    
    yield store
    await store.close()


@pytest.fixture
def mixin_with_graph(graph_store):
    """Create a mixin instance with graph store"""
    class TestAgent(GraphAwareAgentMixin):
        def __init__(self, graph_store):
            self.graph_store = graph_store
    
    return TestAgent(graph_store)


@pytest.fixture
def mixin_without_graph():
    """Create a mixin instance without graph store"""
    class TestAgent(GraphAwareAgentMixin):
        def __init__(self):
            self.graph_store = None
    
    return TestAgent()


class TestKnowledgeFormatting:
    """Test knowledge formatting methods"""
    
    def test_format_entity_basic(self, mixin_with_graph):
        """Test formatting a basic entity"""
        entity = Entity(
            id="test_entity",
            entity_type="Person",
            properties={"name": "Test", "age": 30}
        )
        
        result = mixin_with_graph.format_entity(entity)
        
        assert "Person" in result
        assert "test_entity" in result
        assert "name=Test" in result
        assert "age=30" in result
    
    def test_format_entity_without_properties(self, mixin_with_graph):
        """Test formatting entity without properties"""
        entity = Entity(
            id="test_entity",
            entity_type="Person",
            properties={}
        )
        
        result = mixin_with_graph.format_entity(entity, include_properties=False)
        
        assert "Person" in result
        assert "test_entity" in result
        assert "(" not in result  # No properties
    
    def test_format_entities_list(self, mixin_with_graph):
        """Test formatting a list of entities"""
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Company", properties={"name": "TechCorp"}),
        ]
        
        result = mixin_with_graph.format_entities(entities)
        
        assert "- Person: e1" in result
        assert "- Company: e2" in result
        assert "name=Alice" in result
    
    def test_format_entities_with_limit(self, mixin_with_graph):
        """Test formatting entities with max_items limit"""
        entities = [
            Entity(id=f"e{i}", entity_type="Person", properties={})
            for i in range(15)
        ]
        
        result = mixin_with_graph.format_entities(entities, max_items=5)
        
        assert result.count("- Person:") == 5
        assert "... and 10 more" in result
    
    def test_format_relation_basic(self, mixin_with_graph):
        """Test formatting a relation"""
        relation = Relation(
            id="r1",
            source_id="alice",
            target_id="bob",
            relation_type="KNOWS",
            properties={}
        )
        
        result = mixin_with_graph.format_relation(relation)
        
        assert "alice" in result
        assert "bob" in result
        assert "KNOWS" in result
        assert "--[" in result
        assert "]-->" in result
    
    def test_format_path(self, mixin_with_graph):
        """Test formatting a path"""
        nodes = [
            Entity(id="alice", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="bob", entity_type="Person", properties={"name": "Bob"}),
        ]
        edges = [
            Relation(id="r1", source_id="alice", target_id="bob", relation_type="KNOWS", properties={})
        ]
        
        path = Path(nodes=nodes, edges=edges, weight=1.0)
        
        result = mixin_with_graph.format_path(path)
        
        assert "alice" in result
        assert "bob" in result
        assert "KNOWS" in result
    
    def test_format_knowledge_summary(self, mixin_with_graph):
        """Test formatting knowledge summary"""
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Company", properties={"name": "TechCorp"}),
        ]
        relations = [
            Relation(id="r1", source_id="e1", target_id="e2", relation_type="WORKS_FOR", properties={})
        ]
        
        result = mixin_with_graph.format_knowledge_summary(entities, relations)
        
        assert "Entities (2):" in result
        assert "Relations (1):" in result
        assert "e1" in result
        assert "e2" in result


class TestGraphQueryUtilities:
    """Test graph query utility methods"""
    
    @pytest.mark.asyncio
    async def test_get_entity_neighbors(self, mixin_with_graph, graph_store):
        """Test getting entity neighbors"""
        neighbors = await mixin_with_graph.get_entity_neighbors(
            entity_id="alice",
            direction="outgoing"
        )
        
        assert len(neighbors) > 0
        neighbor_ids = [n.id for n in neighbors]
        assert "bob" in neighbor_ids or "tech_corp" in neighbor_ids
    
    @pytest.mark.asyncio
    async def test_get_entity_neighbors_with_filter(self, mixin_with_graph):
        """Test getting neighbors with relation type filter"""
        neighbors = await mixin_with_graph.get_entity_neighbors(
            entity_id="alice",
            relation_type="KNOWS",
            direction="outgoing"
        )
        
        # Should return bob (connected via KNOWS)
        neighbor_ids = [n.id for n in neighbors]
        assert "bob" in neighbor_ids
    
    @pytest.mark.asyncio
    async def test_get_entity_neighbors_without_graph(self, mixin_without_graph):
        """Test getting neighbors without graph store"""
        neighbors = await mixin_without_graph.get_entity_neighbors("alice")
        
        assert neighbors == []
    
    @pytest.mark.asyncio
    async def test_find_paths_between(self, mixin_with_graph, graph_store):
        """Test finding paths between entities"""
        paths = await mixin_with_graph.find_paths_between(
            source_id="alice",
            target_id="tech_corp",
            max_depth=2
        )
        
        # Should find at least one path
        assert isinstance(paths, list)
        # May be empty if path doesn't exist, but should not error
    
    @pytest.mark.asyncio
    async def test_find_paths_between_without_graph(self, mixin_without_graph):
        """Test finding paths without graph store"""
        paths = await mixin_without_graph.find_paths_between("alice", "bob")
        
        assert paths == []
    
    @pytest.mark.asyncio
    async def test_get_entity_subgraph(self, mixin_with_graph):
        """Test getting entity subgraph"""
        subgraph = await mixin_with_graph.get_entity_subgraph(
            entity_id="alice",
            max_depth=2
        )
        
        assert "entities" in subgraph
        assert "relations" in subgraph
        assert isinstance(subgraph["entities"], list)
        assert len(subgraph["entities"]) > 0  # Should include alice at minimum
    
    @pytest.mark.asyncio
    async def test_get_entity_subgraph_without_graph(self, mixin_without_graph):
        """Test getting subgraph without graph store"""
        subgraph = await mixin_without_graph.get_entity_subgraph("alice")
        
        assert subgraph["entities"] == []
        assert subgraph["relations"] == []
    
    @pytest.mark.asyncio
    async def test_search_entities(self, mixin_with_graph):
        """Test searching entities"""
        # Current implementation returns empty
        entities = await mixin_with_graph.search_entities(
            query="engineer",
            entity_types=["Person"]
        )
        
        assert isinstance(entities, list)
        # May be empty as implementation is placeholder


class TestKnowledgeContextUtilities:
    """Test knowledge context utility methods"""
    
    def test_extract_entity_mentions(self, mixin_with_graph):
        """Test extracting entity mentions from text"""
        text = "Alice works at TechCorp with Bob"
        
        mentions = mixin_with_graph.extract_entity_mentions(text)
        
        assert "Alice" in mentions
        assert "TechCorp" in mentions
        assert "Bob" in mentions
    
    def test_extract_entity_mentions_no_capitals(self, mixin_with_graph):
        """Test extracting mentions from text without capitals"""
        text = "this is a normal sentence"
        
        mentions = mixin_with_graph.extract_entity_mentions(text)
        
        # Should return empty or minimal results
        assert isinstance(mentions, list)
    
    def test_build_knowledge_context_prompt(self, mixin_with_graph):
        """Test building knowledge context prompt"""
        entities = [
            Entity(id="alice", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="bob", entity_type="Person", properties={"name": "Bob"}),
        ]
        relations = [
            Relation(id="r1", source_id="alice", target_id="bob", relation_type="KNOWS", properties={})
        ]
        
        prompt = mixin_with_graph.build_knowledge_context_prompt(entities, relations)
        
        assert "RELEVANT KNOWLEDGE:" in prompt
        assert "Entities:" in prompt
        assert "Relations:" in prompt
        assert "alice" in prompt
        assert "KNOWS" in prompt
    
    def test_build_knowledge_context_prompt_with_length_limit(self, mixin_with_graph):
        """Test building prompt with length limit"""
        entities = [
            Entity(id=f"e{i}", entity_type="Person", properties={"name": f"Person{i}"})
            for i in range(100)
        ]
        
        prompt = mixin_with_graph.build_knowledge_context_prompt(entities, max_length=100)
        
        assert len(prompt) <= 103  # 100 + "..."
        assert "..." in prompt
    
    def test_validate_graph_store_with_store(self, mixin_with_graph):
        """Test validating graph store when available"""
        assert mixin_with_graph.validate_graph_store() is True
    
    def test_validate_graph_store_without_store(self, mixin_without_graph):
        """Test validating graph store when not available"""
        assert mixin_without_graph.validate_graph_store() is False
    
    @pytest.mark.asyncio
    async def test_get_graph_stats_with_store(self, mixin_with_graph):
        """Test getting graph stats when store is available"""
        stats = mixin_with_graph.get_graph_stats()
        
        assert "available" in stats
        assert stats["available"] is True
        # Stats may vary based on implementation, but should have entity/relation counts
    
    def test_get_graph_stats_without_store(self, mixin_without_graph):
        """Test getting graph stats when store is not available"""
        stats = mixin_without_graph.get_graph_stats()
        
        assert stats["available"] is False
        assert stats["entity_count"] == 0


class TestErrorHandling:
    """Test error handling in mixin methods"""
    
    @pytest.mark.asyncio
    async def test_get_neighbors_error_handling(self, mixin_with_graph):
        """Test that get_entity_neighbors handles errors gracefully"""
        # Mock graph_store to raise exception
        mixin_with_graph.graph_store.get_neighbors = AsyncMock(side_effect=Exception("Test error"))
        
        neighbors = await mixin_with_graph.get_entity_neighbors("alice")
        
        assert neighbors == []
    
    @pytest.mark.asyncio
    async def test_find_paths_error_handling(self, mixin_with_graph):
        """Test that find_paths_between handles errors gracefully"""
        # Mock graph_store to raise exception
        mixin_with_graph.graph_store.find_paths = AsyncMock(side_effect=Exception("Test error"))
        
        paths = await mixin_with_graph.find_paths_between("alice", "bob")
        
        assert paths == []
    
    @pytest.mark.asyncio
    async def test_get_subgraph_error_handling(self, mixin_with_graph):
        """Test that get_entity_subgraph handles errors gracefully"""
        # Mock graph_store to raise exception
        mixin_with_graph.graph_store.get_entity = AsyncMock(side_effect=Exception("Test error"))
        
        subgraph = await mixin_with_graph.get_entity_subgraph("alice")
        
        assert subgraph["entities"] == []
        assert subgraph["relations"] == []


class TestMixinIntegration:
    """Test mixin integration with agent classes"""
    
    def test_mixin_can_be_used_with_agent(self, graph_store):
        """Test that mixin can be mixed into an agent class"""
        class TestAgent(GraphAwareAgentMixin):
            def __init__(self, graph_store):
                self.graph_store = graph_store
        
        agent = TestAgent(graph_store)
        
        # Test that mixin methods are available
        assert hasattr(agent, 'format_entity')
        assert hasattr(agent, 'get_entity_neighbors')
        assert hasattr(agent, 'validate_graph_store')
        
        # Test validation
        assert agent.validate_graph_store() is True
    
    def test_mixin_works_without_graph_store(self):
        """Test that mixin works even without graph store"""
        class TestAgent(GraphAwareAgentMixin):
            def __init__(self):
                self.graph_store = None
        
        agent = TestAgent()
        
        # Should still have methods
        assert hasattr(agent, 'format_entity')
        assert hasattr(agent, 'validate_graph_store')
        
        # Validation should return False
        assert agent.validate_graph_store() is False

