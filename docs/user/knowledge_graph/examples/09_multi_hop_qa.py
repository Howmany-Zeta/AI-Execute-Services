"""
Example: Multi-Hop Question Answering

Demonstrates how to use the reasoning engine for multi-hop question answering
over a knowledge graph.
"""

import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.reasoning import ReasoningEngine, QueryPlanner
from aiecs.tools.knowledge_graph import GraphReasoningTool
from aiecs.tools.knowledge_graph.graph_reasoning_tool import GraphReasoningInput


async def build_knowledge_graph():
    """Build a sample knowledge graph about people, companies, and locations"""
    graph = InMemoryGraphStore()
    await graph.initialize()
    
    # Create entities: People
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "role": "Engineer"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob", "role": "Manager"})
    charlie = Entity(id="charlie", entity_type="Person", properties={"name": "Charlie", "role": "CEO"})
    diana = Entity(id="diana", entity_type="Person", properties={"name": "Diana", "role": "Engineer"})
    
    # Create entities: Companies
    tech_corp = Entity(id="tech_corp", entity_type="Company", properties={"name": "TechCorp", "industry": "Technology"})
    data_inc = Entity(id="data_inc", entity_type="Company", properties={"name": "DataInc", "industry": "Data Science"})
    
    # Create entities: Locations
    sf = Entity(id="san_francisco", entity_type="Location", properties={"name": "San Francisco", "country": "USA"})
    ny = Entity(id="new_york", entity_type="Location", properties={"name": "New York", "country": "USA"})
    
    # Add entities
    for entity in [alice, bob, charlie, diana, tech_corp, data_inc, sf, ny]:
        await graph.add_entity(entity)
    
    # Create relations: Social connections
    await graph.add_relation(Relation(id="r1", source_id="alice", target_id="bob", relation_type="KNOWS", properties={}))
    await graph.add_relation(Relation(id="r2", source_id="bob", target_id="charlie", relation_type="KNOWS", properties={}))
    await graph.add_relation(Relation(id="r3", source_id="charlie", target_id="diana", relation_type="KNOWS", properties={}))
    
    # Create relations: Employment
    await graph.add_relation(Relation(id="r4", source_id="alice", target_id="tech_corp", relation_type="WORKS_FOR", properties={}))
    await graph.add_relation(Relation(id="r5", source_id="bob", target_id="tech_corp", relation_type="WORKS_FOR", properties={}))
    await graph.add_relation(Relation(id="r6", source_id="charlie", target_id="data_inc", relation_type="WORKS_FOR", properties={}))
    await graph.add_relation(Relation(id="r7", source_id="diana", target_id="data_inc", relation_type="WORKS_FOR", properties={}))
    
    # Create relations: Location
    await graph.add_relation(Relation(id="r8", source_id="tech_corp", target_id="sf", relation_type="LOCATED_IN", properties={}))
    await graph.add_relation(Relation(id="r9", source_id="data_inc", target_id="ny", relation_type="LOCATED_IN", properties={}))
    
    return graph


async def example_1_basic_multi_hop():
    """Example 1: Basic multi-hop reasoning"""
    print("=" * 80)
    print("Example 1: Basic Multi-Hop Reasoning")
    print("=" * 80)
    
    graph = await build_knowledge_graph()
    engine = ReasoningEngine(graph)
    
    # Question: How is Alice connected to Diana?
    print("\nQuestion: How is Alice connected to Diana?")
    print("-" * 80)
    
    result = await engine.reason(
        query="How is Alice connected to Diana?",
        context={
            "start_entity_id": "alice",
            "target_entity_id": "diana"
        },
        max_hops=4
    )
    
    print(f"\nAnswer: {result.answer}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"\nEvidence collected: {result.evidence_count} pieces")
    
    print("\nReasoning trace:")
    for step in result.reasoning_trace[:10]:  # Show first 10 steps
        print(f"  - {step}")
    
    print(f"\nExecution time: {result.execution_time_ms:.1f}ms")
    
    await graph.close()


async def example_2_multi_hop_with_constraints():
    """Example 2: Multi-hop reasoning with relation type constraints"""
    print("\n\n" + "=" * 80)
    print("Example 2: Multi-Hop Reasoning with Relation Constraints")
    print("=" * 80)
    
    graph = await build_knowledge_graph()
    engine = ReasoningEngine(graph)
    
    # Question: How is Alice connected to New York through work relationships?
    print("\nQuestion: How is Alice connected to New York through work relationships?")
    print("-" * 80)
    
    result = await engine.reason(
        query="How is Alice connected to New York through work relationships?",
        context={
            "start_entity_id": "alice",
            "target_entity_id": "new_york",
            "relation_types": ["WORKS_FOR", "LOCATED_IN"]  # Only these relation types
        },
        max_hops=3
    )
    
    print(f"\nAnswer: {result.answer}")
    print(f"Confidence: {result.confidence:.2f}")
    
    print("\nTop evidence:")
    for i, ev in enumerate(result.get_top_evidence(3), 1):
        print(f"{i}. {ev.explanation}")
        print(f"   Confidence: {ev.confidence:.2f}, Relevance: {ev.relevance_score:.2f}")
    
    await graph.close()


async def example_3_using_reasoning_tool():
    """Example 3: Using GraphReasoningTool for multi-hop QA"""
    print("\n\n" + "=" * 80)
    print("Example 3: Using GraphReasoningTool")
    print("=" * 80)
    
    graph = await build_knowledge_graph()
    tool = GraphReasoningTool(graph)
    
    # Question: Who works at companies that Alice's connections work at?
    print("\nQuestion: Who works at companies that Alice's connections work at?")
    print("-" * 80)
    
    input_data = GraphReasoningInput(
        mode="multi_hop",
        query="Who works at companies that Alice's connections work at?",
        start_entity_id="alice",
        max_hops=4,
        synthesize_evidence=True,
        confidence_threshold=0.5
    )
    
    result = await tool._execute(input_data)
    
    print(f"\nAnswer: {result['answer']}")
    print(f"Final confidence: {result['confidence']:.2f}")
    print(f"\nEvidence count: {result['evidence_count']}")
    
    print("\nTop evidence:")
    for ev in result['evidence'][:3]:
        print(f"  - {ev['explanation']}")
        print(f"    Type: {ev['type']}, Confidence: {ev['confidence']:.2f}")
    
    print(f"\nExecution time: {result['execution_time_ms']:.1f}ms")
    
    await graph.close()


async def example_4_complex_query_with_planning():
    """Example 4: Complex query with query planning"""
    print("\n\n" + "=" * 80)
    print("Example 4: Complex Query with Query Planning")
    print("=" * 80)
    
    graph = await build_knowledge_graph()
    planner = QueryPlanner(graph)
    engine = ReasoningEngine(graph)
    
    # Complex question requiring multiple steps
    query = "What is the relationship between people working in Technology companies and Data Science companies?"
    print(f"\nQuestion: {query}")
    print("-" * 80)
    
    # First, plan the query
    plan = planner.plan_query(query)
    
    print(f"\nQuery Plan ({len(plan.steps)} steps):")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. {step.description}")
        print(f"   Operation: {step.operation.value}, Cost: {step.estimated_cost:.2f}")
    
    # Then execute reasoning
    result = await engine.reason(query, max_hops=5)
    
    print(f"\nAnswer: {result.answer}")
    print(f"Confidence: {result.confidence:.2f}")
    
    await graph.close()


async def example_5_full_reasoning_pipeline():
    """Example 5: Full reasoning pipeline with all components"""
    print("\n\n" + "=" * 80)
    print("Example 5: Full Reasoning Pipeline")
    print("=" * 80)
    
    graph = await build_knowledge_graph()
    tool = GraphReasoningTool(graph)
    
    # Use full reasoning mode
    print("\nQuestion: How are Alice and Diana connected through their work?")
    print("-" * 80)
    
    input_data = GraphReasoningInput(
        mode="full_reasoning",
        query="How are Alice and Diana connected through their work?",
        start_entity_id="alice",
        target_entity_id="diana",
        max_hops=4,
        apply_inference=False,  # No inference needed for this query
        synthesize_evidence=True,
        synthesis_method="weighted_average",
        confidence_threshold=0.6,
        optimization_strategy="balanced"
    )
    
    result = await tool._execute(input_data)
    
    print("\nReasoning Pipeline Steps:")
    for step in result['steps']:
        print(f"  - {step['name']}")
        if 'evidence_collected' in step:
            print(f"    Evidence collected: {step['evidence_collected']}")
        if 'estimated_cost' in step:
            print(f"    Estimated cost: {step['estimated_cost']:.2f}")
    
    print(f"\nFinal Answer: {result['answer']}")
    print(f"Final Confidence: {result['final_confidence']:.2f}")
    
    print("\nTop Evidence:")
    for i, ev in enumerate(result['top_evidence'], 1):
        print(f"{i}. {ev['explanation']}")
        print(f"   Confidence: {ev['confidence']:.2f}, Relevance: {ev['relevance_score']:.2f}")
    
    print("\nReasoning Trace (first 10 steps):")
    for step in result['reasoning_trace'][:10]:
        print(f"  - {step}")
    
    await graph.close()


async def main():
    """Run all examples"""
    await example_1_basic_multi_hop()
    await example_2_multi_hop_with_constraints()
    await example_3_using_reasoning_tool()
    await example_4_complex_query_with_planning()
    await example_5_full_reasoning_pipeline()
    
    print("\n\n" + "=" * 80)
    print("All Multi-Hop QA Examples Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

