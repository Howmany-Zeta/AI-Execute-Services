"""
Integration tests for GraphSearchTool

Tests the tool with:
- Real PostgreSQL connection
- All search modes
- End-to-end functionality
"""

import pytest


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Timeout for test
async def test_vector_search_with_postgres(populated_postgres_store, setup_graph_search_tool_with_store):
    """
    Test vector search mode with PostgreSQL backend.
    """
    tool = setup_graph_search_tool_with_store(populated_postgres_store)
    
    # Create a query embedding (dummy for now, real implementation would use embedding model)
    query_embedding = [0.1] * 128
    
    result = await tool.execute(
        mode="vector",
        query_embedding=query_embedding,
        max_results=5
    )
    
    assert result["success"] is True
    assert "results" in result
    assert isinstance(result["results"], list)
    assert result["num_results"] >= 0


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Timeout for test
async def test_graph_search_with_postgres(populated_postgres_store, setup_graph_search_tool_with_store):
    """
    Test graph structure search mode.
    """
    tool = setup_graph_search_tool_with_store(populated_postgres_store)
    
    result = await tool.execute(
        mode="graph",
        seed_entity_ids=["alice"],
        max_depth=2,
        max_results=10
    )
    
    assert result["success"] is True
    assert "results" in result
    assert isinstance(result["results"], list)
    # Should find at least bob (direct neighbor) and tech_corp (via relation)
    assert result["num_results"] >= 1


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Timeout for test
async def test_hybrid_search_with_postgres(populated_postgres_store, setup_graph_search_tool_with_store):
    """
    Test hybrid search combining vector and graph.
    """
    tool = setup_graph_search_tool_with_store(populated_postgres_store)
    
    query_embedding = [0.1] * 128
    
    result = await tool.execute(
        mode="hybrid",
        query_embedding=query_embedding,
        seed_entity_ids=["alice"],
        max_depth=2,
        max_results=10,
        vector_weight=0.6,
        graph_weight=0.4
    )
    
    assert result["success"] is True
    assert "results" in result
    assert isinstance(result["results"], list)


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Timeout for test
async def test_pagerank_search_with_postgres(populated_postgres_store, setup_graph_search_tool_with_store):
    """
    Test Personalized PageRank search mode.
    """
    tool = setup_graph_search_tool_with_store(populated_postgres_store)
    
    result = await tool.execute(
        mode="pagerank",
        seed_entity_ids=["alice"],
        max_results=10
    )
    
    assert result["success"] is True
    assert "results" in result
    assert isinstance(result["results"], list)
    # PageRank should return results with scores
    if result["num_results"] > 0:
        assert "score" in result["results"][0]
        assert "score_type" in result["results"][0]
        assert result["results"][0]["score_type"] == "pagerank"


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Timeout for test
async def test_multihop_search_with_postgres(populated_postgres_store, setup_graph_search_tool_with_store):
    """
    Test multi-hop neighbor search.
    """
    tool = setup_graph_search_tool_with_store(populated_postgres_store)
    
    result = await tool.execute(
        mode="multihop",
        seed_entity_ids=["alice"],
        max_depth=2,
        max_results=10
    )
    
    assert result["success"] is True
    assert "results" in result
    assert isinstance(result["results"], list)
    # Should find entities within 2 hops
    if result["num_results"] > 0:
        assert "score_type" in result["results"][0]
        assert result["results"][0]["score_type"] == "hop_distance"


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Timeout for test
async def test_filtered_search_with_postgres(populated_postgres_store, setup_graph_search_tool_with_store):
    """
    Test filtered search by entity type and properties.
    """
    tool = setup_graph_search_tool_with_store(populated_postgres_store)
    
    # Filter by entity type
    result = await tool.execute(
        mode="filtered",
        entity_type="Person",
        max_results=10
    )
    
    assert result["success"] is True
    assert "results" in result
    assert isinstance(result["results"], list)
    # All results should be Person type
    for item in result["results"]:
        assert item["entity_type"] == "Person"
    
    # Filter by properties
    result2 = await tool.execute(
        mode="filtered",
        entity_type="Person",
        property_filters={"role": "Engineer"},
        max_results=10
    )
    
    assert result2["success"] is True
    assert "results" in result2
    # All results should have role=Engineer
    for item in result2["results"]:
        assert item["properties"].get("role") == "Engineer"


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Timeout for test
async def test_traverse_search_with_postgres(populated_postgres_store, setup_graph_search_tool_with_store):
    """
    Test pattern-based traversal search.
    """
    tool = setup_graph_search_tool_with_store(populated_postgres_store)
    
    result = await tool.execute(
        mode="traverse",
        seed_entity_ids=["alice"],
        relation_types=["WORKS_FOR", "KNOWS"],
        max_depth=2,
        max_results=10
    )
    
    assert result["success"] is True
    assert "results" in result
    assert isinstance(result["results"], list)
    if result["num_results"] > 0:
        assert "score_type" in result["results"][0]
        assert result["results"][0]["score_type"] == "path_length"


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Timeout for test
async def test_search_with_empty_store(postgres_store, setup_graph_search_tool_with_store):
    """
    Test search operations on empty graph store.
    """
    tool = setup_graph_search_tool_with_store(postgres_store)
    
    # All search modes should handle empty store gracefully
    query_embedding = [0.1] * 128
    
    modes = ["vector", "graph", "hybrid", "pagerank", "multihop", "filtered", "traverse"]
    
    for mode in modes:
        if mode == "vector":
            result = await tool.execute(mode=mode, query_embedding=query_embedding, max_results=5)
        elif mode in ["graph", "pagerank", "multihop", "traverse"]:
            result = await tool.execute(mode=mode, seed_entity_ids=["nonexistent"], max_results=5)
        elif mode == "hybrid":
            result = await tool.execute(
                mode=mode,
                query_embedding=query_embedding,
                seed_entity_ids=["nonexistent"],
                max_results=5
            )
        elif mode == "filtered":
            result = await tool.execute(mode=mode, entity_type="Person", max_results=5)
        
        assert result["success"] is True
        assert result["num_results"] == 0
        assert result["results"] == []

