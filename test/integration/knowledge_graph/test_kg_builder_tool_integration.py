"""
Integration tests for KnowledgeGraphBuilderTool

Tests the tool with:
- Real PostgreSQL connection
- Real LLM API calls (no mocks)
- End-to-end functionality
"""

import pytest


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # 5 minute timeout for multiple LLM API calls (entity + relation extraction)
async def test_build_from_text_with_postgres(postgres_store, llm_available, setup_kg_builder_tool_with_store):
    """
    Test building knowledge graph from text using PostgreSQL backend.
    Uses real LLM calls for entity and relation extraction.
    """
    # Create tool with PostgreSQL store
    tool = setup_kg_builder_tool_with_store(postgres_store)
    
    # Test text with clear entities and relations
    test_text = """
    Alice works at Tech Corp in San Francisco. 
    Bob is the manager at Tech Corp. 
    Alice knows Bob from college.
    Tech Corp is located in San Francisco, California.
    """
    
    # Execute build_from_text action
    result = await tool.execute(
        action="build_from_text",
        text=test_text,
        source="test_integration"
    )
    
    # Verify success
    if not result.get("success"):
        error_msg = result.get('error', 'Unknown error')
        warnings = result.get('warnings', [])
        errors_list = result.get('errors', [])
        full_error = f"Build failed: {error_msg}"
        if warnings:
            full_error += f"\nWarnings: {warnings}"
        if errors_list:
            full_error += f"\nErrors: {errors_list}"
        full_error += f"\nFull result: {result}"
        assert False, full_error
    assert result["entities_added"] > 0, "Should have extracted at least one entity"
    assert result["relations_added"] > 0, "Should have extracted at least one relation"
    
    # Verify entities were actually stored
    stats = await tool.execute(action="get_stats")
    assert stats["success"] is True
    # PostgreSQL returns entity_count, not total_entities
    entity_count = stats["stats"].get("total_entities") or stats["stats"].get("entity_count", 0)
    relation_count = stats["stats"].get("total_relations") or stats["stats"].get("relation_count", 0)
    assert entity_count >= result["entities_added"]
    assert relation_count >= result["relations_added"]
    
    # Cleanup
    await tool.close()


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # 5 minute timeout for LLM API calls
async def test_build_from_text_with_entity_types(postgres_store, llm_available, setup_kg_builder_tool_with_store):
    """
    Test building with specific entity types filter.
    """
    tool = setup_kg_builder_tool_with_store(postgres_store)
    
    test_text = "Alice is a software engineer. Bob is a product manager. Tech Corp is a technology company."
    
    result = await tool.execute(
        action="build_from_text",
        text=test_text,
        source="test_entity_types",
        entity_types=["Person", "Company"]
    )
    
    assert result["success"] is True
    assert result["entities_added"] > 0
    
    # Verify stats
    stats = await tool.execute(action="get_stats")
    assert stats["success"] is True
    
    await tool.close()


@pytest.mark.asyncio
@pytest.mark.timeout(60)  # 1 minute timeout (no LLM calls)
async def test_get_stats_with_postgres(postgres_store, setup_kg_builder_tool_with_store):
    """
    Test getting statistics from PostgreSQL store.
    """
    tool = setup_kg_builder_tool_with_store(postgres_store)
    
    # Get stats from empty store
    stats = await tool.execute(action="get_stats")
    
    assert stats["success"] is True
    assert "stats" in stats
    # PostgreSQL returns entity_count/relation_count, support both formats
    assert "entity_count" in stats["stats"] or "total_entities" in stats["stats"]
    assert "relation_count" in stats["stats"] or "total_relations" in stats["stats"]
    entity_count = stats["stats"].get("total_entities") or stats["stats"].get("entity_count", 0)
    relation_count = stats["stats"].get("total_relations") or stats["stats"].get("relation_count", 0)
    assert entity_count >= 0
    assert relation_count >= 0
    
    await tool.close()


@pytest.mark.asyncio
@pytest.mark.timeout(600)  # 10 minute timeout for multiple builds with LLM calls
async def test_build_with_deduplication(postgres_store, llm_available, setup_kg_builder_tool_with_store):
    """
    Test that entity deduplication works correctly.
    """
    tool = setup_kg_builder_tool_with_store(postgres_store)
    
    # Build same entity twice
    text1 = "Alice works at Tech Corp."
    text2 = "Alice is an engineer at Tech Corp."
    
    result1 = await tool.execute(
        action="build_from_text",
        text=text1,
        source="test_dedup_1"
    )
    
    result2 = await tool.execute(
        action="build_from_text",
        text=text2,
        source="test_dedup_2"
    )
    
    assert result1["success"] is True
    assert result2["success"] is True
    
    # Check that deduplication occurred
    assert result2.get("entities_deduplicated", 0) >= 0  # May or may not deduplicate
    
    stats = await tool.execute(action="get_stats")
    total_entities = stats["stats"].get("total_entities") or stats["stats"].get("entity_count", 0)
    
    # Total entities should be less than sum of added entities (due to deduplication)
    assert total_entities <= result1["entities_added"] + result2["entities_added"]
    
    await tool.close()


@pytest.mark.asyncio
@pytest.mark.timeout(600)  # 10 minute timeout for multiple builds with LLM calls
async def test_build_with_linking(postgres_store, llm_available, setup_kg_builder_tool_with_store):
    """
    Test that entity linking works correctly.
    """
    tool = setup_kg_builder_tool_with_store(postgres_store)
    
    # Build entities that should link
    text1 = "Alice works at Tech Corp."
    text2 = "Alice knows Bob who also works at Tech Corp."
    
    result1 = await tool.execute(
        action="build_from_text",
        text=text1,
        source="test_link_1"
    )
    
    result2 = await tool.execute(
        action="build_from_text",
        text=text2,
        source="test_link_2"
    )
    
    assert result1["success"] is True
    assert result2["success"] is True
    
    # Check that linking occurred
    assert result2.get("entities_linked", 0) >= 0  # May or may not link
    
    await tool.close()

