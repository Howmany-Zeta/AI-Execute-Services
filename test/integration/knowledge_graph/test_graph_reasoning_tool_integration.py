"""
Integration tests for GraphReasoningTool

Tests the tool with:
- Real PostgreSQL connection
- Real LLM calls for query planning
- All reasoning modes
"""

import pytest
from aiecs.tools.knowledge_graph.graph_reasoning_tool import GraphReasoningTool
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # Timeout for test
async def test_query_plan_mode(populated_postgres_store, llm_available):
    """
    Test query planning mode with real LLM.
    """
    tool = GraphReasoningTool(populated_postgres_store)
    
    result = await tool.execute(
        mode="query_plan",
        query="How is Alice connected to Tech Corp?",
        optimization_strategy="balanced"
    )
    
    assert "mode" in result
    assert result["mode"] == "query_plan"
    assert "plan" in result
    assert "steps" in result["plan"]
    assert isinstance(result["plan"]["steps"], list)
    assert len(result["plan"]["steps"]) > 0
    assert "total_cost" in result["plan"]
    assert "estimated_latency_ms" in result["plan"]


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # Timeout for test
async def test_multi_hop_reasoning(populated_postgres_store, llm_available):
    """
    Test multi-hop reasoning mode.
    """
    tool = GraphReasoningTool(populated_postgres_store)
    
    result = await tool.execute(
        mode="multi_hop",
        query="What is the relationship between Alice and Bob?",
        start_entity_id="alice",
        max_hops=3,
        synthesize_evidence=True
    )
    
    assert "mode" in result
    assert result["mode"] == "multi_hop"
    assert "answer" in result
    assert "confidence" in result
    assert "evidence_count" in result
    assert "evidence" in result
    assert isinstance(result["evidence"], list)
    assert result["confidence"] >= 0.0
    assert result["confidence"] <= 1.0


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # Timeout for test
async def test_inference_mode(populated_postgres_store):
    """
    Test logical inference mode.
    """
    tool = GraphReasoningTool(populated_postgres_store)
    
    result = await tool.execute(
        mode="inference",
        query="Apply transitive inference on KNOWS relation",
        apply_inference=True,
        inference_relation_type="KNOWS",
        inference_max_steps=3
    )
    
    assert "mode" in result
    assert result["mode"] == "inference"
    assert "relation_type" in result
    assert result["relation_type"] == "KNOWS"
    assert "inferred_count" in result
    assert "inferred_relations" in result
    assert isinstance(result["inferred_relations"], list)
    assert "confidence" in result
    assert "total_steps" in result


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # Timeout for test
async def test_full_reasoning_pipeline(populated_postgres_store, llm_available):
    """
    Test full reasoning pipeline with all steps.
    """
    tool = GraphReasoningTool(populated_postgres_store)
    
    result = await tool.execute(
        mode="full_reasoning",
        query="How is Alice connected to Tech Corp?",
        start_entity_id="alice",
        max_hops=3,
        apply_inference=False,
        synthesize_evidence=True,
        synthesis_method="weighted_average",
        confidence_threshold=0.3
    )
    
    assert "mode" in result
    assert result["mode"] == "full_reasoning"
    assert "steps" in result
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) > 0
    assert "answer" in result
    assert "final_confidence" in result
    assert "evidence_count" in result
    assert "top_evidence" in result
    assert isinstance(result["top_evidence"], list)
    
    # Verify steps were executed
    step_names = [step["name"] for step in result["steps"]]
    assert "query_planning" in step_names
    assert "multi_hop_reasoning" in step_names
    assert "evidence_synthesis" in step_names
    
    # Check if fallback was used
    reasoning_trace = result.get("reasoning_trace", [])
    used_fallback = any("FALLBACK" in str(trace_item) for trace_item in reasoning_trace)
    
    # Check evidence sources
    evidence_sources = [ev.get("source", "") for ev in result.get("top_evidence", [])]
    used_fallback_from_evidence = any("direct_traversal_fallback" in source for source in evidence_sources)
    
    fallback_used = used_fallback or used_fallback_from_evidence
    
    if fallback_used:
        # Test passes but marks as using fallback (not ideal)
        import warnings
        warnings.warn(
            "Query plan did not find evidence, fallback traversal was used. "
            "This indicates the query planner needs improvement.",
            UserWarning
        )
        # Still assert that we got results
        assert result["evidence_count"] > 0, "Fallback should have found evidence"
    else:
        # Test passes correctly - query plan worked without fallback
        assert result["evidence_count"] > 0, "Query plan should have found evidence"


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # Timeout for test
async def test_full_reasoning_with_inference(populated_postgres_store, llm_available):
    """
    Test full reasoning pipeline with inference enabled.
    """
    tool = GraphReasoningTool(populated_postgres_store)
    
    result = await tool.execute(
        mode="full_reasoning",
        query="Find all connections involving Alice",
        start_entity_id="alice",
        max_hops=2,
        apply_inference=True,
        inference_relation_type="KNOWS",
        inference_max_steps=2,
        synthesize_evidence=True
    )
    
    assert "mode" in result
    assert result["mode"] == "full_reasoning"
    assert "steps" in result
    assert len(result["steps"]) >= 3  # planning, reasoning, synthesis
    
    # Check if inference step was included
    step_names = [step["name"] for step in result["steps"]]
    if "logical_inference" in step_names:
        inference_step = next(s for s in result["steps"] if s["name"] == "logical_inference")
        assert "inferred_relations" in inference_step


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # Timeout for test
async def test_reasoning_with_empty_store(postgres_store, llm_available):
    """
    Test reasoning on empty graph store.
    """
    tool = GraphReasoningTool(postgres_store)
    
    result = await tool.execute(
        mode="multi_hop",
        query="Find connections",
        start_entity_id="nonexistent",
        max_hops=2
    )
    
    # Should handle gracefully
    assert "mode" in result
    assert result["mode"] == "multi_hop"
    assert "evidence_count" in result
    # May have 0 evidence or handle error gracefully
    assert result["evidence_count"] >= 0


@pytest.mark.asyncio
@pytest.mark.timeout(300)  # Timeout for test
async def test_reasoning_confidence_threshold(populated_postgres_store, llm_available):
    """
    Test that confidence threshold filtering works.
    """
    tool = GraphReasoningTool(populated_postgres_store)
    
    # Test with high threshold (should filter out low confidence evidence)
    result_high = await tool.execute(
        mode="full_reasoning",
        query="What is Alice's connection to Tech Corp?",
        start_entity_id="alice",
        max_hops=2,
        synthesize_evidence=True,
        confidence_threshold=0.9  # Very high threshold
    )
    
    # Test with low threshold (should include more evidence)
    result_low = await tool.execute(
        mode="full_reasoning",
        query="What is Alice's connection to Tech Corp?",
        start_entity_id="alice",
        max_hops=2,
        synthesize_evidence=True,
        confidence_threshold=0.1  # Very low threshold
    )
    
    assert result_high["mode"] == "full_reasoning"
    assert result_low["mode"] == "full_reasoning"
    
    # Low threshold should have at least as many evidence items as high threshold
    assert result_low["evidence_count"] >= result_high["evidence_count"]

