"""
Unit tests for GraphSearchTool

Tests the knowledge graph search tool with multiple search modes.
"""

import pytest
from aiecs.tools.knowledge_graph.graph_search_tool import GraphSearchTool, SearchModeEnum
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


@pytest.fixture
async def search_tool_with_data():
    """Fixture with GraphSearchTool and sample data"""
    tool = GraphSearchTool()
    await tool._initialize()
    
    # Add sample entities
    entities = [
        Entity(
            id="alice",
            entity_type="Person",
            properties={"name": "Alice", "role": "Engineer", "level": "Senior"},
            embedding=[0.9, 0.1, 0.1]
        ),
        Entity(
            id="bob",
            entity_type="Person",
            properties={"name": "Bob", "role": "Manager", "level": "Mid"},
            embedding=[0.8, 0.2, 0.1]
        ),
        Entity(
            id="carol",
            entity_type="Person",
            properties={"name": "Carol", "role": "Engineer", "level": "Junior"},
            embedding=[0.85, 0.15, 0.1]
        ),
        Entity(
            id="tech_corp",
            entity_type="Company",
            properties={"name": "Tech Corp", "industry": "Technology"},
            embedding=[0.5, 0.5, 0.5]
        ),
    ]
    
    for entity in entities:
        await tool.graph_store.add_entity(entity)
    
    # Add relations
    relations = [
        Relation(id="r1", relation_type="WORKS_FOR", source_id="alice", target_id="tech_corp"),
        Relation(id="r2", relation_type="WORKS_FOR", source_id="bob", target_id="tech_corp"),
        Relation(id="r3", relation_type="MANAGES", source_id="bob", target_id="alice"),
        Relation(id="r4", relation_type="COLLABORATES", source_id="alice", target_id="carol"),
    ]
    
    for relation in relations:
        await tool.graph_store.add_relation(relation)
    
    yield tool
    await tool.graph_store.close()


class TestGraphSearchToolInitialization:
    """Test tool initialization"""
    
    @pytest.mark.asyncio
    async def test_tool_initialization(self):
        """Test that tool initializes properly"""
        tool = GraphSearchTool()
        
        assert tool.name == "graph_search"
        assert tool.description is not None
        assert not tool._initialized
        
        await tool._initialize()
        
        assert tool._initialized
        assert tool.graph_store is not None
        assert tool.hybrid_search is not None
        assert tool.pagerank is not None
        
        await tool.graph_store.close()


class TestVectorSearch:
    """Test vector search mode"""
    
    @pytest.mark.asyncio
    async def test_vector_search_basic(self, search_tool_with_data):
        """Test basic vector search"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.VECTOR,
            query_embedding=[0.9, 0.1, 0.1],
            max_results=3
        )
        
        assert result["success"] is True
        assert result["mode"] == SearchModeEnum.VECTOR
        assert len(result["results"]) > 0
        
        # Results should have required fields
        for item in result["results"]:
            assert "entity_id" in item
            assert "entity_type" in item
            assert "properties" in item
            assert "score" in item
    
    @pytest.mark.asyncio
    async def test_vector_search_with_entity_type_filter(self, search_tool_with_data):
        """Test vector search with entity type filter"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.VECTOR,
            query_embedding=[0.8, 0.2, 0.1],
            entity_type="Person",
            max_results=5
        )
        
        assert result["success"] is True
        
        # All results should be Person type
        for item in result["results"]:
            assert item["entity_type"] == "Person"
    
    @pytest.mark.asyncio
    async def test_vector_search_with_threshold(self, search_tool_with_data):
        """Test vector search with similarity threshold"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.VECTOR,
            query_embedding=[0.9, 0.1, 0.1],
            vector_threshold=0.95,
            max_results=10
        )
        
        assert result["success"] is True
        
        # All results should meet threshold
        for item in result["results"]:
            assert item["score"] >= 0.95


class TestGraphSearch:
    """Test graph search mode"""
    
    @pytest.mark.asyncio
    async def test_graph_search_basic(self, search_tool_with_data):
        """Test basic graph search"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.GRAPH,
            seed_entity_ids=["alice"],
            max_depth=2,
            max_results=5
        )
        
        assert result["success"] is True
        assert result["mode"] == SearchModeEnum.GRAPH
        assert len(result["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_graph_search_multiple_seeds(self, search_tool_with_data):
        """Test graph search with multiple seeds"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.GRAPH,
            seed_entity_ids=["alice", "bob"],
            max_depth=1,
            max_results=10
        )
        
        assert result["success"] is True
        assert len(result["results"]) > 0


class TestHybridSearch:
    """Test hybrid search mode"""
    
    @pytest.mark.asyncio
    async def test_hybrid_search_basic(self, search_tool_with_data):
        """Test basic hybrid search"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.HYBRID,
            query_embedding=[0.85, 0.15, 0.1],
            seed_entity_ids=["alice"],
            vector_weight=0.6,
            graph_weight=0.4,
            max_results=5
        )
        
        assert result["success"] is True
        assert result["mode"] == SearchModeEnum.HYBRID
        assert len(result["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_hybrid_search_weight_balance(self, search_tool_with_data):
        """Test hybrid search with different weight configurations"""
        # Vector-heavy
        result1 = await search_tool_with_data._execute(
            mode=SearchModeEnum.HYBRID,
            query_embedding=[0.9, 0.1, 0.1],
            vector_weight=0.9,
            graph_weight=0.1,
            max_results=3
        )
        
        # Graph-heavy
        result2 = await search_tool_with_data._execute(
            mode=SearchModeEnum.HYBRID,
            query_embedding=[0.9, 0.1, 0.1],
            seed_entity_ids=["tech_corp"],
            vector_weight=0.1,
            graph_weight=0.9,
            max_results=3
        )
        
        assert result1["success"] is True
        assert result2["success"] is True


class TestPageRankSearch:
    """Test PageRank search mode"""
    
    @pytest.mark.asyncio
    async def test_pagerank_search_basic(self, search_tool_with_data):
        """Test basic PageRank search"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.PAGERANK,
            seed_entity_ids=["alice"],
            max_results=5
        )
        
        assert result["success"] is True
        assert result["mode"] == SearchModeEnum.PAGERANK
        assert len(result["results"]) > 0
        
        # Results should have pagerank score type
        for item in result["results"]:
            assert item["score_type"] == "pagerank"


class TestMultiHopSearch:
    """Test multi-hop search mode"""
    
    @pytest.mark.asyncio
    async def test_multihop_search_basic(self, search_tool_with_data):
        """Test basic multi-hop search"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.MULTIHOP,
            seed_entity_ids=["alice"],
            max_depth=2,
            max_results=5
        )
        
        assert result["success"] is True
        assert result["mode"] == SearchModeEnum.MULTIHOP
        assert len(result["results"]) > 0
        
        # Results should have hop_distance score type
        for item in result["results"]:
            assert item["score_type"] == "hop_distance"


class TestFilteredSearch:
    """Test filtered search mode"""
    
    @pytest.mark.asyncio
    async def test_filtered_search_by_type(self, search_tool_with_data):
        """Test filtered search by entity type"""
        # Add embeddings for filtering to work
        for entity_id in ["alice", "bob", "carol", "tech_corp"]:
            entity = await search_tool_with_data.graph_store.get_entity(entity_id)
            if entity:
                search_tool_with_data.graph_store.entities[entity_id] = entity
        
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.FILTERED,
            entity_type="Person",
            max_results=10
        )
        
        assert result["success"] is True
        
        # All results should be Person type
        for item in result["results"]:
            assert item["entity_type"] == "Person"
    
    @pytest.mark.asyncio
    async def test_filtered_search_by_properties(self, search_tool_with_data):
        """Test filtered search by properties"""
        # Add embeddings
        for entity_id in ["alice", "bob", "carol"]:
            entity = await search_tool_with_data.graph_store.get_entity(entity_id)
            if entity:
                search_tool_with_data.graph_store.entities[entity_id] = entity
        
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.FILTERED,
            entity_type="Person",
            property_filters={"role": "Engineer"},
            max_results=10
        )
        
        assert result["success"] is True
        
        # All results should match filter
        for item in result["results"]:
            assert item["properties"]["role"] == "Engineer"


class TestTraverseSearch:
    """Test traverse search mode"""
    
    @pytest.mark.asyncio
    async def test_traverse_search_basic(self, search_tool_with_data):
        """Test basic traverse search"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.TRAVERSE,
            seed_entity_ids=["alice"],
            max_depth=2,
            max_results=5
        )
        
        assert result["success"] is True
        assert result["mode"] == SearchModeEnum.TRAVERSE
        assert len(result["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_traverse_search_with_relation_filter(self, search_tool_with_data):
        """Test traverse search with relation type filter"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.TRAVERSE,
            seed_entity_ids=["alice"],
            relation_types=["WORKS_FOR"],
            max_depth=1,
            max_results=5
        )
        
        assert result["success"] is True


class TestToolErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_mode(self, search_tool_with_data):
        """Test handling of invalid search mode"""
        result = await search_tool_with_data._execute(
            mode="invalid_mode",
            max_results=5
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_missing_required_params_vector(self, search_tool_with_data):
        """Test vector search without embedding"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.VECTOR,
            max_results=5
        )
        
        # Should handle gracefully (empty results or error)
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_missing_required_params_graph(self, search_tool_with_data):
        """Test graph search without seeds"""
        result = await search_tool_with_data._execute(
            mode=SearchModeEnum.GRAPH,
            max_depth=2,
            max_results=5
        )
        
        # Should return success with empty results
        assert result["success"] is True
        assert result["num_results"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

