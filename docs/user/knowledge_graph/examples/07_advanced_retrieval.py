"""
Advanced Retrieval Strategies Examples

Demonstrates Personalized PageRank, multi-hop retrieval, filtered retrieval,
and query caching.
"""

import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    PersonalizedPageRank,
    MultiHopRetrieval,
    FilteredRetrieval,
    RetrievalCache
)
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


async def setup_research_network():
    """Create a research collaboration network"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Researchers and their collaborations
    researchers = [
        Entity(id="alice", entity_type="Researcher", properties={
            "name": "Alice Smith", "field": "AI", "h_index": 45, "institution": "MIT"
        }),
        Entity(id="bob", entity_type="Researcher", properties={
            "name": "Bob Johnson", "field": "AI", "h_index": 38, "institution": "Stanford"
        }),
        Entity(id="carol", entity_type="Researcher", properties={
            "name": "Carol White", "field": "ML", "h_index": 52, "institution": "MIT"
        }),
        Entity(id="dave", entity_type="Researcher", properties={
            "name": "Dave Brown", "field": "NLP", "h_index": 41, "institution": "CMU"
        }),
        Entity(id="eve", entity_type="Researcher", properties={
            "name": "Eve Davis", "field": "CV", "h_index": 35, "institution": "Stanford"
        }),
        Entity(id="frank", entity_type="Researcher", properties={
            "name": "Frank Miller", "field": "RL", "h_index": 29, "institution": "Berkeley"
        }),
    ]
    
    # Papers
    papers = [
        Entity(id="paper1", entity_type="Paper", properties={
            "title": "Deep Learning Survey", "year": 2023, "citations": 150
        }),
        Entity(id="paper2", entity_type="Paper", properties={
            "title": "Transformers for NLP", "year": 2022, "citations": 320
        }),
    ]
    
    for entity in researchers + papers:
        await store.add_entity(entity)
    
    # Collaboration network
    relations = [
        # Direct collaborations
        Relation(id="r1", relation_type="COLLABORATES_WITH", source_id="alice", target_id="bob", weight=0.9),
        Relation(id="r2", relation_type="COLLABORATES_WITH", source_id="bob", target_id="carol", weight=0.8),
        Relation(id="r3", relation_type="COLLABORATES_WITH", source_id="carol", target_id="dave", weight=0.85),
        Relation(id="r4", relation_type="COLLABORATES_WITH", source_id="alice", target_id="eve", weight=0.7),
        Relation(id="r5", relation_type="COLLABORATES_WITH", source_id="eve", target_id="frank", weight=0.75),
        Relation(id="r6", relation_type="COLLABORATES_WITH", source_id="bob", target_id="dave", weight=0.8),
        
        # Paper authorship
        Relation(id="r7", relation_type="AUTHORED", source_id="alice", target_id="paper1", weight=1.0),
        Relation(id="r8", relation_type="AUTHORED", source_id="carol", target_id="paper1", weight=1.0),
        Relation(id="r9", relation_type="AUTHORED", source_id="dave", target_id="paper2", weight=1.0),
        Relation(id="r10", relation_type="AUTHORED", source_id="bob", target_id="paper2", weight=1.0),
    ]
    
    for relation in relations:
        await store.add_relation(relation)
    
    return store


async def example_1_personalized_pagerank():
    """Example 1: Personalized PageRank retrieval"""
    print("=" * 70)
    print("Example 1: Personalized PageRank Retrieval")
    print("=" * 70)
    
    store = await setup_research_network()
    ppr = PersonalizedPageRank(store)
    
    print("\nFinding important researchers starting from Alice...")
    
    results = await ppr.retrieve(
        seed_entity_ids=["alice"],
        max_results=5,
        alpha=0.15,  # 15% restart probability
        max_iterations=50
    )
    
    print(f"\nFound {len(results)} important entities:")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        if entity.entity_type == "Researcher":
            print(f"{i}. {props.get('name')} ({entity.entity_type})")
            print(f"   Field: {props.get('field')}, H-index: {props.get('h_index')}")
            print(f"   PageRank Score: {score:.4f}")
        else:
            print(f"{i}. {props.get('title')} ({entity.entity_type})")
            print(f"   PageRank Score: {score:.4f}")
    
    await store.close()


async def example_2_multihop_retrieval():
    """Example 2: Multi-hop neighbor retrieval"""
    print("\n" + "=" * 70)
    print("Example 2: Multi-Hop Neighbor Retrieval")
    print("=" * 70)
    
    store = await setup_research_network()
    retrieval = MultiHopRetrieval(store)
    
    print("\nFinding researchers within 2 hops of Alice...")
    
    results = await retrieval.retrieve(
        seed_entity_ids=["alice"],
        max_hops=2,
        max_results=10,
        score_decay=0.5,
        include_seeds=True
    )
    
    print(f"\nFound {len(results)} entities:")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        if entity.entity_type == "Researcher":
            # Infer hop distance from score
            if score == 1.0:
                hop = 0
            elif score == 0.5:
                hop = 1
            elif score == 0.25:
                hop = 2
            else:
                hop = "?"
            
            print(f"{i}. {props.get('name')} (Hop {hop})")
            print(f"   Institution: {props.get('institution')}, Score: {score:.2f}")
    
    await store.close()


async def example_3_filtered_retrieval():
    """Example 3: Filtered retrieval"""
    print("\n" + "=" * 70)
    print("Example 3: Filtered Retrieval")
    print("=" * 70)
    
    store = await setup_research_network()
    retrieval = FilteredRetrieval(store)
    
    # Add embeddings for vector search to work
    print("\nSetting up embeddings for filtering...")
    for entity_id in ["alice", "bob", "carol", "dave", "eve", "frank"]:
        entity = await store.get_entity(entity_id)
        if entity:
            updated = Entity(
                id=entity.id,
                entity_type=entity.entity_type,
                properties=entity.properties,
                embedding=[0.1] * 128
            )
            store.entities[entity_id] = updated
    
    # Filter 1: By entity type and property
    print("\n--- Filter 1: AI Researchers ---")
    results = await retrieval.retrieve(
        entity_type="Researcher",
        property_filters={"field": "AI"},
        max_results=10
    )
    
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {props.get('name')} - {props.get('field')}")
        print(f"   H-index: {props.get('h_index')}, Institution: {props.get('institution')}")
    
    # Filter 2: Custom filter function
    print("\n--- Filter 2: Senior Researchers (H-index > 40) ---")
    
    def senior_researcher_filter(entity: Entity) -> bool:
        return entity.properties.get("h_index", 0) > 40
    
    results = await retrieval.retrieve(
        entity_type="Researcher",
        filter_fn=senior_researcher_filter,
        max_results=10
    )
    
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {props.get('name')} - H-index: {props.get('h_index')}")
    
    # Filter 3: Multiple criteria
    print("\n--- Filter 3: MIT Researchers in ML ---")
    results = await retrieval.retrieve(
        entity_type="Researcher",
        property_filters={"institution": "MIT", "field": "ML"},
        max_results=10
    )
    
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {props.get('name')} - {props.get('field')} at {props.get('institution')}")
    
    await store.close()


async def example_4_retrieval_cache():
    """Example 4: Query caching"""
    print("\n" + "=" * 70)
    print("Example 4: Retrieval Caching")
    print("=" * 70)
    
    store = await setup_research_network()
    retrieval = MultiHopRetrieval(store)
    cache = RetrievalCache(max_size=100, ttl=300)  # 5 minutes TTL
    
    print("\nPerforming retrieval with caching...")
    
    # First call - cache miss
    print("\n1. First call (cache miss):")
    
    async def expensive_retrieval():
        return await retrieval.retrieve(
            seed_entity_ids=["alice"],
            max_hops=2,
            max_results=5
        )
    
    results1 = await cache.get_or_compute(
        cache_key="alice_2hop",
        compute_fn=expensive_retrieval
    )
    
    stats = cache.get_stats()
    print(f"   Results: {len(results1)} entities")
    print(f"   Cache hits: {stats['hits']}, misses: {stats['misses']}")
    print(f"   Hit rate: {stats['hit_rate']:.1%}")
    
    # Second call - cache hit
    print("\n2. Second call (cache hit):")
    
    results2 = await cache.get_or_compute(
        cache_key="alice_2hop",
        compute_fn=expensive_retrieval
    )
    
    stats = cache.get_stats()
    print(f"   Results: {len(results2)} entities")
    print(f"   Cache hits: {stats['hits']}, misses: {stats['misses']}")
    print(f"   Hit rate: {stats['hit_rate']:.1%}")
    
    # Third call with different key - cache miss
    print("\n3. Different query (cache miss):")
    
    async def different_retrieval():
        return await retrieval.retrieve(
            seed_entity_ids=["bob"],
            max_hops=1,
            max_results=5
        )
    
    results3 = await cache.get_or_compute(
        cache_key="bob_1hop",
        compute_fn=different_retrieval
    )
    
    stats = cache.get_stats()
    print(f"   Results: {len(results3)} entities")
    print(f"   Cache hits: {stats['hits']}, misses: {stats['misses']}")
    print(f"   Hit rate: {stats['hit_rate']:.1%}")
    
    # Final statistics
    print("\n--- Final Cache Statistics ---")
    final_stats = cache.get_stats()
    print(f"Total requests: {final_stats['total_requests']}")
    print(f"Cache hits: {final_stats['hits']}")
    print(f"Cache misses: {final_stats['misses']}")
    print(f"Hit rate: {final_stats['hit_rate']:.1%}")
    print(f"Cache size: {final_stats['cache_size']}/{final_stats['max_size']}")
    
    await store.close()


async def example_5_combined_strategies():
    """Example 5: Combining multiple strategies"""
    print("\n" + "=" * 70)
    print("Example 5: Combining Multiple Strategies")
    print("=" * 70)
    
    store = await setup_research_network()
    
    print("\nScenario: Find highly connected AI researchers")
    print("Strategy: PageRank + Filtered Retrieval")
    
    # Step 1: Use PageRank to find important nodes
    ppr = PersonalizedPageRank(store)
    pagerank_results = await ppr.retrieve(
        seed_entity_ids=["alice", "bob"],
        max_results=10,
        alpha=0.15
    )
    
    print(f"\n1. PageRank found {len(pagerank_results)} important entities")
    
    # Step 2: Filter for high h-index researchers
    # Extract researcher IDs
    researcher_ids = [
        entity.id for entity, _ in pagerank_results
        if entity.entity_type == "Researcher"
    ]
    
    print(f"2. Filtering {len(researcher_ids)} researchers...")
    
    # Get researchers with high h-index
    high_impact = []
    for entity_id in researcher_ids:
        entity = await store.get_entity(entity_id)
        if entity and entity.properties.get("h_index", 0) > 35:
            # Find their score from PageRank
            pr_score = next(
                (score for e, score in pagerank_results if e.id == entity_id),
                0.0
            )
            high_impact.append((entity, pr_score))
    
    # Sort by PageRank score
    high_impact.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n3. Found {len(high_impact)} high-impact AI researchers:")
    for i, (entity, pr_score) in enumerate(high_impact, 1):
        props = entity.properties
        print(f"{i}. {props.get('name')}")
        print(f"   Field: {props.get('field')}, H-index: {props.get('h_index')}")
        print(f"   Institution: {props.get('institution')}")
        print(f"   PageRank Score: {pr_score:.4f}")
    
    await store.close()


async def main():
    """Run all examples"""
    await example_1_personalized_pagerank()
    await example_2_multihop_retrieval()
    await example_3_filtered_retrieval()
    await example_4_retrieval_cache()
    await example_5_combined_strategies()
    
    print("\n" + "=" * 70)
    print("All Advanced Retrieval Examples Completed!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("1. PageRank finds influential entities in the graph")
    print("2. Multi-hop retrieval explores local neighborhoods")
    print("3. Filtered retrieval enables precise entity selection")
    print("4. Caching significantly improves performance for repeated queries")
    print("5. Strategies can be combined for sophisticated retrieval")


if __name__ == "__main__":
    asyncio.run(main())

