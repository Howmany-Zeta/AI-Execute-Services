"""
Example: Logical Inference Over Knowledge Graphs

Demonstrates how to use the inference engine to discover implicit knowledge
through logical inference rules.
"""

import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.inference_rule import InferenceRule, RuleType
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.reasoning import InferenceEngine
from aiecs.tools.knowledge_graph import GraphReasoningTool
from aiecs.tools.knowledge_graph.graph_reasoning_tool import GraphReasoningInput


async def build_social_network():
    """Build a social network graph"""
    graph = InMemoryGraphStore()
    await graph.initialize()
    
    # Create people
    people = [
        Entity(id="alice", entity_type="Person", properties={"name": "Alice"}),
        Entity(id="bob", entity_type="Person", properties={"name": "Bob"}),
        Entity(id="charlie", entity_type="Person", properties={"name": "Charlie"}),
        Entity(id="diana", entity_type="Person", properties={"name": "Diana"}),
        Entity(id="eve", entity_type="Person", properties={"name": "Eve"}),
        Entity(id="frank", entity_type="Person", properties={"name": "Frank"}),
    ]
    
    for person in people:
        await graph.add_entity(person)
    
    # Create KNOWS relations (directed)
    knows_relations = [
        ("alice", "bob"),
        ("bob", "charlie"),
        ("charlie", "diana"),
        ("diana", "eve"),
        ("eve", "frank"),
        ("alice", "charlie"),  # Direct connection
        ("bob", "diana"),      # Direct connection
    ]
    
    for i, (source, target) in enumerate(knows_relations, 1):
        await graph.add_relation(Relation(
            id=f"knows_{i}",
            source_id=source,
            target_id=target,
            relation_type="KNOWS",
            properties={}
        ))
    
    # Create FRIEND_OF relations (should be symmetric)
    friend_relations = [
        ("alice", "bob"),
        ("charlie", "diana"),
        ("eve", "frank"),
    ]
    
    for i, (source, target) in enumerate(friend_relations, 1):
        await graph.add_relation(Relation(
            id=f"friend_{i}",
            source_id=source,
            target_id=target,
            relation_type="FRIEND_OF",
            properties={}
        ))
    
    return graph


async def example_1_transitive_inference():
    """Example 1: Transitive inference (A→B, B→C ⇒ A→C)"""
    print("=" * 80)
    print("Example 1: Transitive Inference")
    print("=" * 80)
    
    graph = await build_social_network()
    engine = InferenceEngine(graph)
    
    # Add transitive rule for KNOWS relation
    transitive_rule = InferenceRule(
        rule_id="transitive_knows",
        rule_type=RuleType.TRANSITIVE,
        relation_type="KNOWS",
        description="If A knows B and B knows C, then A knows C (transitively)",
        confidence_decay=0.1,  # 10% decay per hop
        enabled=True
    )
    
    engine.add_rule(transitive_rule)
    
    print("\nOriginal KNOWS relations:")
    print("  - Alice → Bob")
    print("  - Bob → Charlie")
    print("  - Charlie → Diana")
    print("  - Diana → Eve")
    print("  - Eve → Frank")
    print("  - Alice → Charlie (direct)")
    print("  - Bob → Diana (direct)")
    
    print("\nApplying transitive inference...")
    
    result = await engine.infer_relations(
        relation_type="KNOWS",
        max_steps=5,
        use_cache=True
    )
    
    print(f"\nInferred {len(result.inferred_relations)} new relations:")
    for rel in result.inferred_relations[:10]:  # Show first 10
        print(f"  - {rel.source_id} → {rel.target_id}")
    
    print(f"\nOverall confidence: {result.confidence:.3f}")
    print(f"Total inference steps: {result.total_steps}")
    
    # Show inference trace
    print("\nInference trace (first 5):")
    trace = engine.get_inference_trace(result)
    for line in trace[:5]:
        print(f"  {line}")
    
    await graph.close()


async def example_2_symmetric_inference():
    """Example 2: Symmetric inference (A→B ⇒ B→A)"""
    print("\n\n" + "=" * 80)
    print("Example 2: Symmetric Inference")
    print("=" * 80)
    
    graph = await build_social_network()
    engine = InferenceEngine(graph)
    
    # Add symmetric rule for FRIEND_OF relation
    symmetric_rule = InferenceRule(
        rule_id="symmetric_friend",
        rule_type=RuleType.SYMMETRIC,
        relation_type="FRIEND_OF",
        description="Friendship is symmetric: if A is friend of B, then B is friend of A",
        confidence_decay=0.05,  # 5% decay for symmetry
        enabled=True
    )
    
    engine.add_rule(symmetric_rule)
    
    print("\nOriginal FRIEND_OF relations:")
    print("  - Alice → Bob")
    print("  - Charlie → Diana")
    print("  - Eve → Frank")
    
    print("\nApplying symmetric inference...")
    
    result = await engine.infer_relations(
        relation_type="FRIEND_OF",
        max_steps=1,  # Symmetry only needs 1 step
        use_cache=True
    )
    
    print(f"\nInferred {len(result.inferred_relations)} new relations:")
    for rel in result.inferred_relations:
        print(f"  - {rel.source_id} → {rel.target_id}")
    
    print(f"\nOverall confidence: {result.confidence:.3f}")
    
    # Show inference trace
    print("\nInference trace:")
    trace = engine.get_inference_trace(result)
    for line in trace:
        print(f"  {line}")
    
    await graph.close()


async def example_3_combined_inference():
    """Example 3: Combining multiple inference rules"""
    print("\n\n" + "=" * 80)
    print("Example 3: Combined Inference Rules")
    print("=" * 80)
    
    graph = await build_social_network()
    engine = InferenceEngine(graph)
    
    # Add both transitive and symmetric rules
    engine.add_rule(InferenceRule(
        rule_id="transitive_knows",
        rule_type=RuleType.TRANSITIVE,
        relation_type="KNOWS",
        description="Transitive closure for KNOWS",
        confidence_decay=0.1,
        enabled=True
    ))
    
    engine.add_rule(InferenceRule(
        rule_id="symmetric_friend",
        rule_type=RuleType.SYMMETRIC,
        relation_type="FRIEND_OF",
        description="Symmetric friendship",
        confidence_decay=0.05,
        enabled=True
    ))
    
    print("\nApplying both transitive and symmetric inference...")
    
    # Infer KNOWS relations
    knows_result = await engine.infer_relations("KNOWS", max_steps=3)
    print(f"\nInferred KNOWS relations: {len(knows_result.inferred_relations)}")
    print(f"Confidence: {knows_result.confidence:.3f}")
    
    # Infer FRIEND_OF relations
    friend_result = await engine.infer_relations("FRIEND_OF", max_steps=1)
    print(f"\nInferred FRIEND_OF relations: {len(friend_result.inferred_relations)}")
    print(f"Confidence: {friend_result.confidence:.3f}")
    
    print(f"\nTotal inferred: {len(knows_result.inferred_relations) + len(friend_result.inferred_relations)} relations")
    
    await graph.close()


async def example_4_inference_with_caching():
    """Example 4: Using inference cache for performance"""
    print("\n\n" + "=" * 80)
    print("Example 4: Inference with Caching")
    print("=" * 80)
    
    graph = await build_social_network()
    engine = InferenceEngine(graph)
    
    # Add transitive rule
    engine.add_rule(InferenceRule(
        rule_id="transitive_knows",
        rule_type=RuleType.TRANSITIVE,
        relation_type="KNOWS",
        description="Transitive closure",
        confidence_decay=0.1,
        enabled=True
    ))
    
    import time
    
    # First call - no cache
    print("\nFirst inference (no cache):")
    start = time.time()
    result1 = await engine.infer_relations("KNOWS", max_steps=3, use_cache=True)
    time1 = (time.time() - start) * 1000
    print(f"  Inferred: {len(result1.inferred_relations)} relations")
    print(f"  Time: {time1:.1f}ms")
    
    # Second call - with cache
    print("\nSecond inference (with cache):")
    start = time.time()
    result2 = await engine.infer_relations("KNOWS", max_steps=3, use_cache=True)
    time2 = (time.time() - start) * 1000
    print(f"  Inferred: {len(result2.inferred_relations)} relations")
    print(f"  Time: {time2:.1f}ms")
    
    print(f"\nSpeedup: {time1/time2:.1f}x faster with cache")
    
    # Check cache stats
    cache_stats = engine.cache.get_stats()
    print(f"\nCache stats:")
    print(f"  Size: {cache_stats['size']}/{cache_stats['max_size']}")
    print(f"  TTL: {cache_stats['ttl_seconds']}s")
    
    await graph.close()


async def example_5_inference_via_reasoning_tool():
    """Example 5: Using GraphReasoningTool for inference"""
    print("\n\n" + "=" * 80)
    print("Example 5: Inference via GraphReasoningTool")
    print("=" * 80)
    
    graph = await build_social_network()
    tool = GraphReasoningTool(graph)
    
    print("\nUsing GraphReasoningTool for transitive inference...")
    
    input_data = GraphReasoningInput(
        mode="inference",
        query="Infer all transitive KNOWS relations",
        apply_inference=True,
        inference_relation_type="KNOWS",
        inference_max_steps=5
    )
    
    result = await tool._execute(input_data)
    
    print(f"\nMode: {result['mode']}")
    print(f"Relation type: {result['relation_type']}")
    print(f"Inferred count: {result['inferred_count']}")
    print(f"Confidence: {result['confidence']:.3f}")
    print(f"Total steps: {result['total_steps']}")
    
    print("\nInferred relations (first 10):")
    for rel in result['inferred_relations'][:10]:
        print(f"  - {rel['source_id']} → {rel['target_id']}")
    
    print("\nInference trace (first 5):")
    for line in result['inference_trace'][:5]:
        print(f"  {line}")
    
    await graph.close()


async def example_6_explainability():
    """Example 6: Inference explainability"""
    print("\n\n" + "=" * 80)
    print("Example 6: Inference Explainability")
    print("=" * 80)
    
    graph = await build_social_network()
    engine = InferenceEngine(graph)
    
    # Add transitive rule
    engine.add_rule(InferenceRule(
        rule_id="transitive_knows",
        rule_type=RuleType.TRANSITIVE,
        relation_type="KNOWS",
        description="Transitive closure for KNOWS",
        confidence_decay=0.1,
        enabled=True
    ))
    
    result = await engine.infer_relations("KNOWS", max_steps=3)
    
    print(f"\nInferred {len(result.inferred_relations)} relations")
    
    # Get detailed trace for explainability
    trace = engine.get_inference_trace(result)
    
    print("\nDetailed inference trace:")
    for line in trace[:15]:  # Show first 15 steps
        print(f"  {line}")
    
    # Show step-by-step explanations
    print("\nStep-by-step explanations:")
    for i, step in enumerate(result.inference_steps[:5], 1):
        print(f"\nStep {i}:")
        print(f"  Explanation: {step.explanation}")
        print(f"  Confidence: {step.confidence:.3f}")
        print(f"  Rule: {step.rule.rule_id}")
        print(f"  Source relations: {len(step.source_relations)}")
    
    await graph.close()


async def example_7_knowledge_graph_completion():
    """Example 7: Using inference for knowledge graph completion"""
    print("\n\n" + "=" * 80)
    print("Example 7: Knowledge Graph Completion")
    print("=" * 80)
    
    graph = await build_social_network()
    
    # Count original relations
    original_count = {}
    for rel_type in ["KNOWS", "FRIEND_OF"]:
        # Get approximate count by trying to find entities
        entities = await graph.get_entity("alice")  # Just to ensure graph is ready
        original_count[rel_type] = 0
    
    print("\nOriginal graph:")
    print(f"  Entities: 6 people")
    print(f"  KNOWS relations: 7 (explicit)")
    print(f"  FRIEND_OF relations: 3 (explicit)")
    
    # Apply inference to complete the graph
    engine = InferenceEngine(graph)
    
    # Add rules
    engine.add_rule(InferenceRule(
        rule_id="transitive_knows",
        rule_type=RuleType.TRANSITIVE,
        relation_type="KNOWS",
        confidence_decay=0.1,
        enabled=True
    ))
    
    engine.add_rule(InferenceRule(
        rule_id="symmetric_friend",
        rule_type=RuleType.SYMMETRIC,
        relation_type="FRIEND_OF",
        confidence_decay=0.05,
        enabled=True
    ))
    
    # Infer missing relations
    knows_result = await engine.infer_relations("KNOWS", max_steps=4)
    friend_result = await engine.infer_relations("FRIEND_OF", max_steps=1)
    
    print("\nCompleted graph:")
    print(f"  Entities: 6 people")
    print(f"  KNOWS relations: {7 + len(knows_result.inferred_relations)} (7 explicit + {len(knows_result.inferred_relations)} inferred)")
    print(f"  FRIEND_OF relations: {3 + len(friend_result.inferred_relations)} (3 explicit + {len(friend_result.inferred_relations)} inferred)")
    
    print(f"\nGraph completion:")
    print(f"  Added {len(knows_result.inferred_relations) + len(friend_result.inferred_relations)} relations")
    print(f"  Completion confidence: {(knows_result.confidence + friend_result.confidence) / 2:.3f}")
    
    await graph.close()


async def main():
    """Run all examples"""
    await example_1_transitive_inference()
    await example_2_symmetric_inference()
    await example_3_combined_inference()
    await example_4_inference_with_caching()
    await example_5_inference_via_reasoning_tool()
    await example_6_explainability()
    await example_7_knowledge_graph_completion()
    
    print("\n\n" + "=" * 80)
    print("All Logical Inference Examples Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

