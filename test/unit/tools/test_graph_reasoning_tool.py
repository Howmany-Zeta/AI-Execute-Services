"""
Unit tests for GraphReasoningTool

Tests for the knowledge graph reasoning tool.
"""

import pytest
from aiecs.tools.knowledge_graph.graph_reasoning_tool import (
    GraphReasoningTool,
    ReasoningModeEnum,
    GraphReasoningInput
)
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


@pytest.fixture
async def reasoning_graph():
    """Create a test graph for reasoning"""
    graph = InMemoryGraphStore()
    await graph.initialize()
    
    # Create entities
    entities = [
        Entity(id="alice", entity_type="Person", properties={"name": "Alice"}),
        Entity(id="bob", entity_type="Person", properties={"name": "Bob"}),
        Entity(id="charlie", entity_type="Person", properties={"name": "Charlie"}),
        Entity(id="company_x", entity_type="Company", properties={"name": "Company X"})
    ]
    
    for entity in entities:
        await graph.add_entity(entity)
    
    # Create relations
    relations = [
        Relation(id="r1", source_id="alice", target_id="bob", relation_type="KNOWS", properties={}),
        Relation(id="r2", source_id="bob", target_id="charlie", relation_type="KNOWS", properties={}),
        Relation(id="r3", source_id="charlie", target_id="company_x", relation_type="WORKS_FOR", properties={})
    ]
    
    for relation in relations:
        await graph.add_relation(relation)
    
    return graph


class TestGraphReasoningTool:
    """Test GraphReasoningTool"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, reasoning_graph):
        """Test tool initialization"""
        tool = GraphReasoningTool(reasoning_graph)
        
        assert tool.name == "graph_reasoning"
        assert "reasoning" in tool.description.lower()
        assert tool.input_schema is not None
    
    @pytest.mark.asyncio
    async def test_query_plan_mode(self, reasoning_graph):
        """Test query planning mode"""
        tool = GraphReasoningTool(reasoning_graph)
        
        input_data = GraphReasoningInput(
            mode="query_plan",
            query="Find connections between Alice and Company X",
            optimization_strategy="balanced"
        )
        result = await tool._execute(input_data)
        
        assert result["mode"] == "query_plan"
        assert "plan" in result
        assert "steps" in result["plan"]
        assert result["plan"]["optimization_strategy"] in ["cost", "latency", "balanced"]
    
    @pytest.mark.asyncio
    async def test_multi_hop_mode(self, reasoning_graph):
        """Test multi-hop reasoning mode"""
        tool = GraphReasoningTool(reasoning_graph)
        
        input_data = GraphReasoningInput(
            mode="multi_hop",
            query="How is Alice connected to Company X?",
            start_entity_id="alice",
            target_entity_id="company_x",
            max_hops=3,
            synthesize_evidence=True
        )
        result = await tool._execute(input_data)
        
        assert result["mode"] == "multi_hop"
        assert result["query"] == "How is Alice connected to Company X?"
        assert "answer" in result
        assert "confidence" in result
        assert result["confidence"] >= 0.0
        assert "evidence_count" in result
    
    @pytest.mark.asyncio
    async def test_inference_mode(self, reasoning_graph):
        """Test logical inference mode"""
        tool = GraphReasoningTool(reasoning_graph)
        
        input_data = GraphReasoningInput(
            mode="inference",
            query="Infer transitive KNOWS relations",
            apply_inference=True,
            inference_relation_type="KNOWS",
            inference_max_steps=3
        )
        result = await tool._execute(input_data)
        
        assert result["mode"] == "inference"
        assert result["relation_type"] == "KNOWS"
        assert "inferred_count" in result
        assert "confidence" in result
        assert "inference_trace" in result
    
    @pytest.mark.asyncio
    async def test_evidence_synthesis_mode(self, reasoning_graph):
        """Test evidence synthesis mode"""
        tool = GraphReasoningTool(reasoning_graph)
        
        input_data = GraphReasoningInput(
            mode="evidence_synthesis",
            query="Synthesize evidence",
            synthesis_method="weighted_average",
            confidence_threshold=0.7
        )
        result = await tool._execute(input_data)
        
        assert result["mode"] == "evidence_synthesis"
        assert "message" in result
    
    @pytest.mark.asyncio
    async def test_full_reasoning_mode(self, reasoning_graph):
        """Test full reasoning pipeline"""
        tool = GraphReasoningTool(reasoning_graph)
        
        input_data = GraphReasoningInput(
            mode="full_reasoning",
            query="How is Alice connected to Company X?",
            start_entity_id="alice",
            target_entity_id="company_x",
            max_hops=3,
            apply_inference=False,
            synthesize_evidence=True,
            confidence_threshold=0.5
        )
        result = await tool._execute(input_data)
        
        assert result["mode"] == "full_reasoning"
        assert "steps" in result
        assert len(result["steps"]) >= 2  # At least planning and reasoning
        assert "answer" in result
        assert "final_confidence" in result
        assert "evidence_count" in result
        assert "top_evidence" in result
        assert "reasoning_trace" in result
    
    @pytest.mark.asyncio
    async def test_full_reasoning_with_inference(self, reasoning_graph):
        """Test full reasoning with inference enabled"""
        tool = GraphReasoningTool(reasoning_graph)
        
        input_data = GraphReasoningInput(
            mode="full_reasoning",
            query="How is Alice connected to Charlie?",
            start_entity_id="alice",
            target_entity_id="charlie",
            max_hops=3,
            apply_inference=True,
            inference_relation_type="KNOWS",
            inference_max_steps=3,
            synthesize_evidence=True
        )
        result = await tool._execute(input_data)
        
        assert result["mode"] == "full_reasoning"
        # Should have planning, reasoning, inference, and synthesis steps
        step_names = [step["name"] for step in result["steps"]]
        assert "query_planning" in step_names
        assert "multi_hop_reasoning" in step_names
        assert "logical_inference" in step_names
        # Evidence synthesis is only added if there's evidence to synthesize
        # It may not appear if no evidence was collected
        if result.get("evidence_count", 0) > 0:
            assert "evidence_synthesis" in step_names
    
    @pytest.mark.asyncio
    async def test_missing_required_params(self, reasoning_graph):
        """Test error handling for missing required parameters"""
        tool = GraphReasoningTool(reasoning_graph)
        
        # Multi-hop without start_entity_id
        with pytest.raises(ValueError, match="start_entity_id"):
            input_data = GraphReasoningInput(
                mode="multi_hop",
                query="test",
                max_hops=2
            )
            await tool._execute(input_data)
        
        # Inference without relation_type
        with pytest.raises(ValueError, match="inference_relation_type"):
            input_data = GraphReasoningInput(
                mode="inference",
                query="test",
                apply_inference=True
            )
            await tool._execute(input_data)
    
    @pytest.mark.asyncio
    async def test_optimization_strategies(self, reasoning_graph):
        """Test different optimization strategies"""
        tool = GraphReasoningTool(reasoning_graph)
        
        strategies = ["cost", "latency", "balanced"]
        
        for strategy in strategies:
            input_data = GraphReasoningInput(
                mode="query_plan",
                query="test query",
                optimization_strategy=strategy
            )
            result = await tool._execute(input_data)
            
            # Strategy enum values are like "minimize_cost", "minimize_latency", "balanced"
            expected = {
                "cost": "minimize_cost",
                "latency": "minimize_latency",
                "balanced": "balanced"
            }
            assert result["plan"]["optimization_strategy"] == expected[strategy]
    
    @pytest.mark.asyncio
    async def test_synthesis_methods(self, reasoning_graph):
        """Test different synthesis methods"""
        tool = GraphReasoningTool(reasoning_graph)
        
        methods = ["weighted_average", "max", "voting"]
        
        for method in methods:
            input_data = GraphReasoningInput(
                mode="multi_hop",
                query="test",
                start_entity_id="alice",
                max_hops=2,
                synthesize_evidence=True,
                synthesis_method=method
            )
            result = await tool._execute(input_data)
            
            assert result["mode"] == "multi_hop"
            # Synthesis method was applied internally
    
    @pytest.mark.asyncio
    async def test_confidence_threshold(self, reasoning_graph):
        """Test confidence threshold filtering"""
        tool = GraphReasoningTool(reasoning_graph)
        
        input_data = GraphReasoningInput(
            mode="multi_hop",
            query="test",
            start_entity_id="alice",
            max_hops=2,
            synthesize_evidence=True,
            confidence_threshold=0.8
        )
        result = await tool._execute(input_data)
        
        # All evidence should meet threshold
        for ev in result.get("evidence", []):
            assert ev["confidence"] >= 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

