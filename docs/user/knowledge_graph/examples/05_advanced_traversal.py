"""
Advanced Graph Traversal Examples

Demonstrates PathPattern, PathScorer, EnhancedTraversal, and cycle detection.
"""

import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern, TraversalDirection
from aiecs.application.knowledge_graph.traversal.path_scorer import PathScorer
from aiecs.application.knowledge_graph.traversal.enhanced_traversal import EnhancedTraversal
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


async def setup_sample_graph():
    """Create a sample knowledge graph for demonstration"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create a social network graph
    # Alice -> Bob -> Carol -> Dave
    #   |              ^        ^
    #   +-> CompanyX --+        |
    #   +----------------------+
    
    # People
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "role": "Engineer"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob", "role": "Manager"})
    carol = Entity(id="carol", entity_type="Person", properties={"name": "Carol", "role": "Director"})
    dave = Entity(id="dave", entity_type="Person", properties={"name": "Dave", "role": "CEO"})
    
    # Company
    company = Entity(id="company_x", entity_type="Company", properties={"name": "CompanyX"})
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(carol)
    await store.add_entity(dave)
    await store.add_entity(company)
    
    # Relations
    await store.add_relation(Relation(
        id="r1", relation_type="KNOWS", source_id="alice", target_id="bob", weight=0.9
    ))
    await store.add_relation(Relation(
        id="r2", relation_type="KNOWS", source_id="bob", target_id="carol", weight=0.8
    ))
    await store.add_relation(Relation(
        id="r3", relation_type="REPORTS_TO", source_id="carol", target_id="dave", weight=1.0
    ))
    await store.add_relation(Relation(
        id="r4", relation_type="WORKS_FOR", source_id="alice", target_id="company_x", weight=1.0
    ))
    await store.add_relation(Relation(
        id="r5", relation_type="LOCATED_IN", source_id="company_x", target_id="carol", weight=0.7
    ))
    await store.add_relation(Relation(
        id="r6", relation_type="KNOWS", source_id="alice", target_id="dave", weight=0.5
    ))
    
    return store


async def example_1_basic_path_pattern():
    """Example 1: Using PathPattern for constrained traversal"""
    print("=" * 60)
    print("Example 1: Basic PathPattern Usage")
    print("=" * 60)
    
    store = await setup_sample_graph()
    traversal = EnhancedTraversal(store)
    
    # Define a pattern: only follow KNOWS relations, max depth 2
    pattern = PathPattern(
        relation_types=["KNOWS"],
        max_depth=2,
        allow_cycles=False
    )
    
    print(f"\nPattern: {pattern}")
    print("\nTraversing from Alice...")
    
    paths = await traversal.traverse_with_pattern(
        start_entity_id="alice",
        pattern=pattern,
        max_results=10
    )
    
    print(f"\nFound {len(paths)} paths:")
    for i, path in enumerate(paths, 1):
        print(f"{i}. {path}")
    
    await store.close()


async def example_2_required_sequence():
    """Example 2: PathPattern with required relation sequence"""
    print("\n" + "=" * 60)
    print("Example 2: Required Relation Sequence")
    print("=" * 60)
    
    store = await setup_sample_graph()
    traversal = EnhancedTraversal(store)
    
    # Define a pattern: must follow WORKS_FOR -> LOCATED_IN
    pattern = PathPattern(
        required_relation_sequence=["WORKS_FOR", "LOCATED_IN"],
        max_depth=2,
        allow_cycles=False
    )
    
    print(f"\nPattern: {pattern}")
    print("\nTraversing from Alice (WORKS_FOR -> LOCATED_IN)...")
    
    paths = await traversal.traverse_with_pattern(
        start_entity_id="alice",
        pattern=pattern,
        max_results=10
    )
    
    print(f"\nFound {len(paths)} paths:")
    for i, path in enumerate(paths, 1):
        relations = " -> ".join(path.get_relation_types())
        print(f"{i}. {path.start_entity.id} -{relations}-> {path.end_entity.id}")
    
    await store.close()


async def example_3_path_scoring():
    """Example 3: Path scoring and ranking"""
    print("\n" + "=" * 60)
    print("Example 3: Path Scoring and Ranking")
    print("=" * 60)
    
    store = await setup_sample_graph()
    
    # Get some paths using basic traversal
    paths = await store.traverse(
        start_entity_id="alice",
        max_depth=2,
        max_results=10
    )
    
    print(f"\nFound {len(paths)} paths from Alice")
    
    scorer = PathScorer()
    
    # Score by length (prefer shorter paths)
    print("\n--- Scoring by Length (prefer shorter) ---")
    scored_by_length = scorer.score_by_length(paths, prefer_shorter=True)
    ranked = scorer.rank_paths(scored_by_length, top_k=3)
    
    for i, path in enumerate(ranked, 1):
        print(f"{i}. Length={path.length}, Score={path.score:.3f}: {path}")
    
    # Score by relation weights
    print("\n--- Scoring by Relation Weights ---")
    scored_by_weights = scorer.score_by_weights(paths, aggregation="mean")
    ranked = scorer.rank_paths(scored_by_weights, top_k=3)
    
    for i, path in enumerate(ranked, 1):
        print(f"{i}. Score={path.score:.3f}: {path}")
    
    # Score by preferred relation types
    print("\n--- Scoring by Preferred Relation Types ---")
    scored_by_types = scorer.score_by_relation_types(
        paths,
        preferred_types=["KNOWS", "REPORTS_TO"],
        penalty=0.3
    )
    ranked = scorer.rank_paths(scored_by_types, top_k=3)
    
    for i, path in enumerate(ranked, 1):
        print(f"{i}. Score={path.score:.3f}: {path}")
    
    await store.close()


async def example_4_combined_scoring():
    """Example 4: Combining multiple scoring methods"""
    print("\n" + "=" * 60)
    print("Example 4: Combined Scoring")
    print("=" * 60)
    
    store = await setup_sample_graph()
    
    # Get paths
    paths = await store.traverse(
        start_entity_id="alice",
        max_depth=2,
        max_results=10
    )
    
    print(f"\nFound {len(paths)} paths from Alice")
    
    scorer = PathScorer()
    
    # Apply multiple scoring methods
    scored_by_length = scorer.score_by_length(paths, prefer_shorter=True)
    scored_by_weights = scorer.score_by_weights(paths, aggregation="mean")
    scored_by_types = scorer.score_by_relation_types(
        paths,
        preferred_types=["KNOWS"],
        penalty=0.5
    )
    
    # Combine scores with weights
    print("\n--- Combining Scores (40% length, 30% weights, 30% types) ---")
    combined = scorer.combine_scores(
        [scored_by_length, scored_by_weights, scored_by_types],
        weights=[0.4, 0.3, 0.3]
    )
    
    ranked = scorer.rank_paths(combined, top_k=5)
    
    for i, path in enumerate(ranked, 1):
        print(f"{i}. Combined Score={path.score:.3f}: {path}")
    
    await store.close()


async def example_5_cycle_detection():
    """Example 5: Cycle detection"""
    print("\n" + "=" * 60)
    print("Example 5: Cycle Detection")
    print("=" * 60)
    
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create a cyclic graph: A -> B -> C -> A
    a = Entity(id="a", entity_type="Node", properties={"name": "A"})
    b = Entity(id="b", entity_type="Node", properties={"name": "B"})
    c = Entity(id="c", entity_type="Node", properties={"name": "C"})
    
    await store.add_entity(a)
    await store.add_entity(b)
    await store.add_entity(c)
    
    await store.add_relation(Relation(id="r1", relation_type="LINKS", source_id="a", target_id="b"))
    await store.add_relation(Relation(id="r2", relation_type="LINKS", source_id="b", target_id="c"))
    await store.add_relation(Relation(id="r3", relation_type="LINKS", source_id="c", target_id="a"))
    
    traversal = EnhancedTraversal(store)
    
    # Traverse with cycles allowed
    print("\n--- Traversal with cycles ALLOWED ---")
    pattern_with_cycles = PathPattern(
        max_depth=4,
        allow_cycles=True
    )
    
    paths_with_cycles = await traversal.traverse_with_pattern(
        start_entity_id="a",
        pattern=pattern_with_cycles,
        max_results=10
    )
    
    print(f"Found {len(paths_with_cycles)} paths")
    for path in paths_with_cycles:
        has_cycle = traversal.detect_cycles(path)
        cycle_str = " [HAS CYCLE]" if has_cycle else ""
        print(f"  {path}{cycle_str}")
    
    # Traverse without cycles
    print("\n--- Traversal with cycles NOT ALLOWED ---")
    pattern_no_cycles = PathPattern(
        max_depth=4,
        allow_cycles=False
    )
    
    paths_no_cycles = await traversal.traverse_with_pattern(
        start_entity_id="a",
        pattern=pattern_no_cycles,
        max_results=10
    )
    
    print(f"Found {len(paths_no_cycles)} paths")
    for path in paths_no_cycles:
        print(f"  {path}")
    
    # Filter cycles from results
    print("\n--- Filtering cycles from paths ---")
    filtered = traversal.filter_paths_without_cycles(paths_with_cycles)
    print(f"After filtering: {len(filtered)} paths without cycles")
    
    await store.close()


async def example_6_custom_scoring():
    """Example 6: Custom scoring function"""
    print("\n" + "=" * 60)
    print("Example 6: Custom Scoring Function")
    print("=" * 60)
    
    store = await setup_sample_graph()
    
    paths = await store.traverse(
        start_entity_id="alice",
        max_depth=2,
        max_results=10
    )
    
    scorer = PathScorer()
    
    # Custom scoring: penalize paths through companies
    def avoid_companies(path):
        """Score higher if path avoids Company entities"""
        company_count = sum(1 for node in path.nodes if node.entity_type == "Company")
        return 1.0 - (company_count * 0.3)  # 30% penalty per company
    
    print("\n--- Custom Scoring (avoid companies) ---")
    scored = scorer.score_custom(paths, avoid_companies)
    ranked = scorer.rank_paths(scored, top_k=5)
    
    for i, path in enumerate(ranked, 1):
        entity_types = [n.entity_type for n in path.nodes]
        print(f"{i}. Score={path.score:.3f}, Types={entity_types}")
        print(f"   {path}")
    
    await store.close()


async def main():
    """Run all examples"""
    await example_1_basic_path_pattern()
    await example_2_required_sequence()
    await example_3_path_scoring()
    await example_4_combined_scoring()
    await example_5_cycle_detection()
    await example_6_custom_scoring()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

