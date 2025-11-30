"""
Hybrid Search Examples

Demonstrates combining vector similarity search with graph structure traversal.
"""

import asyncio
import numpy as np
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
    HybridSearchConfig,
    SearchMode
)
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


async def setup_knowledge_graph():
    """Create a sample knowledge graph about AI topics"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities about AI/ML topics with embeddings
    # Note: In real scenarios, embeddings would come from a model like BERT
    
    # Deep Learning cluster (high similarity in embedding space)
    entities = [
        Entity(
            id="deep_learning",
            entity_type="Topic",
            properties={"name": "Deep Learning", "domain": "AI", "level": "Advanced"},
            embedding=[0.9, 0.85, 0.1, 0.15, 0.2]
        ),
        Entity(
            id="neural_networks",
            entity_type="Topic",
            properties={"name": "Neural Networks", "domain": "AI", "level": "Intermediate"},
            embedding=[0.88, 0.82, 0.12, 0.18, 0.22]
        ),
        Entity(
            id="cnn",
            entity_type="Algorithm",
            properties={"name": "Convolutional Neural Networks", "domain": "AI"},
            embedding=[0.85, 0.8, 0.15, 0.2, 0.25]
        ),
        Entity(
            id="rnn",
            entity_type="Algorithm",
            properties={"name": "Recurrent Neural Networks", "domain": "AI"},
            embedding=[0.83, 0.78, 0.17, 0.22, 0.27]
        ),
        
        # Machine Learning cluster (different embedding region)
        Entity(
            id="machine_learning",
            entity_type="Topic",
            properties={"name": "Machine Learning", "domain": "AI", "level": "Intermediate"},
            embedding=[0.3, 0.4, 0.85, 0.75, 0.6]
        ),
        Entity(
            id="supervised_learning",
            entity_type="Topic",
            properties={"name": "Supervised Learning", "domain": "AI", "level": "Beginner"},
            embedding=[0.32, 0.42, 0.82, 0.72, 0.58]
        ),
        Entity(
            id="decision_trees",
            entity_type="Algorithm",
            properties={"name": "Decision Trees", "domain": "AI"},
            embedding=[0.35, 0.45, 0.8, 0.7, 0.55]
        ),
        
        # Related topics
        Entity(
            id="data_science",
            entity_type="Topic",
            properties={"name": "Data Science", "domain": "Analytics", "level": "Intermediate"},
            embedding=[0.5, 0.6, 0.65, 0.55, 0.5]
        ),
        Entity(
            id="statistics",
            entity_type="Topic",
            properties={"name": "Statistics", "domain": "Math", "level": "Beginner"},
            embedding=[0.4, 0.5, 0.6, 0.5, 0.45]
        ),
    ]
    
    for entity in entities:
        await store.add_entity(entity)
    
    # Create graph structure (relationships)
    relations = [
        # Deep Learning hierarchy
        Relation(id="r1", relation_type="INCLUDES", source_id="deep_learning", target_id="neural_networks", weight=0.95),
        Relation(id="r2", relation_type="INCLUDES", source_id="neural_networks", target_id="cnn", weight=0.9),
        Relation(id="r3", relation_type="INCLUDES", source_id="neural_networks", target_id="rnn", weight=0.9),
        
        # Machine Learning hierarchy
        Relation(id="r4", relation_type="INCLUDES", source_id="machine_learning", target_id="supervised_learning", weight=0.9),
        Relation(id="r5", relation_type="INCLUDES", source_id="supervised_learning", target_id="decision_trees", weight=0.85),
        
        # Cross-domain connections
        Relation(id="r6", relation_type="SPECIALIZES", source_id="deep_learning", target_id="machine_learning", weight=0.8),
        Relation(id="r7", relation_type="REQUIRES", source_id="machine_learning", target_id="statistics", weight=0.75),
        Relation(id="r8", relation_type="APPLIES", source_id="data_science", target_id="machine_learning", weight=0.85),
        Relation(id="r9", relation_type="APPLIES", source_id="data_science", target_id="statistics", weight=0.8),
    ]
    
    for relation in relations:
        await store.add_relation(relation)
    
    return store


async def example_1_vector_only_search():
    """Example 1: Pure vector similarity search"""
    print("=" * 70)
    print("Example 1: Vector-Only Search")
    print("=" * 70)
    
    store = await setup_knowledge_graph()
    strategy = HybridSearchStrategy(store)
    
    # Query: looking for something similar to "deep learning"
    query_embedding = [0.9, 0.85, 0.1, 0.15, 0.2]
    
    config = HybridSearchConfig(
        mode=SearchMode.VECTOR_ONLY,
        max_results=5,
        vector_threshold=0.7
    )
    
    print(f"\nSearch Mode: {config.mode}")
    print(f"Query embedding: {query_embedding[:3]}...")
    print(f"Vector threshold: {config.vector_threshold}")
    
    results = await strategy.search(query_embedding, config)
    
    print(f"\nFound {len(results)} results:")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {entity.id} ({entity.entity_type})")
        print(f"   Name: {props.get('name')}")
        print(f"   Similarity Score: {score:.4f}")
    
    await store.close()


async def example_2_graph_only_search():
    """Example 2: Pure graph structure search"""
    print("\n" + "=" * 70)
    print("Example 2: Graph-Only Search")
    print("=" * 70)
    
    store = await setup_knowledge_graph()
    strategy = HybridSearchStrategy(store)
    
    # Placeholder query (not used in graph-only mode)
    query_embedding = [0.0] * 5
    
    config = HybridSearchConfig(
        mode=SearchMode.GRAPH_ONLY,
        max_graph_depth=2,
        max_results=10
    )
    
    # Start from specific seed entities
    seed_entities = ["deep_learning"]
    
    print(f"\nSearch Mode: {config.mode}")
    print(f"Seed entities: {seed_entities}")
    print(f"Max depth: {config.max_graph_depth}")
    
    results = await strategy.search(query_embedding, config, seed_entity_ids=seed_entities)
    
    print(f"\nFound {len(results)} results:")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {entity.id} ({entity.entity_type})")
        print(f"   Name: {props.get('name')}")
        print(f"   Graph Score: {score:.4f} (depth-based)")
    
    await store.close()


async def example_3_hybrid_search_balanced():
    """Example 3: Hybrid search with balanced weights"""
    print("\n" + "=" * 70)
    print("Example 3: Hybrid Search (Balanced)")
    print("=" * 70)
    
    store = await setup_knowledge_graph()
    strategy = HybridSearchStrategy(store)
    
    # Query similar to neural networks
    query_embedding = [0.88, 0.82, 0.12, 0.18, 0.22]
    
    config = HybridSearchConfig(
        mode=SearchMode.HYBRID,
        vector_weight=0.5,
        graph_weight=0.5,
        max_results=6,
        expand_results=True
    )
    
    print(f"\nSearch Mode: {config.mode}")
    print(f"Vector weight: {config.vector_weight}")
    print(f"Graph weight: {config.graph_weight}")
    print(f"Expand results: {config.expand_results}")
    
    results = await strategy.search(query_embedding, config)
    
    print(f"\nFound {len(results)} results:")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {entity.id} ({entity.entity_type})")
        print(f"   Name: {props.get('name')}")
        print(f"   Combined Score: {score:.4f}")
    
    await store.close()


async def example_4_hybrid_search_vector_heavy():
    """Example 4: Hybrid search favoring vector similarity"""
    print("\n" + "=" * 70)
    print("Example 4: Hybrid Search (Vector-Heavy)")
    print("=" * 70)
    
    store = await setup_knowledge_graph()
    strategy = HybridSearchStrategy(store)
    
    # Query similar to machine learning
    query_embedding = [0.3, 0.4, 0.85, 0.75, 0.6]
    
    config = HybridSearchConfig(
        mode=SearchMode.HYBRID,
        vector_weight=0.8,
        graph_weight=0.2,
        max_results=5,
        expand_results=True
    )
    
    print(f"\nSearch Mode: {config.mode}")
    print(f"Vector weight: {config.vector_weight} (HIGH)")
    print(f"Graph weight: {config.graph_weight} (LOW)")
    
    results = await strategy.search(query_embedding, config)
    
    print(f"\nFound {len(results)} results:")
    print("(Results favor vector similarity over graph structure)")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {entity.id}")
        print(f"   Name: {props.get('name')}")
        print(f"   Combined Score: {score:.4f}")
    
    await store.close()


async def example_5_hybrid_search_graph_heavy():
    """Example 5: Hybrid search favoring graph structure"""
    print("\n" + "=" * 70)
    print("Example 5: Hybrid Search (Graph-Heavy)")
    print("=" * 70)
    
    store = await setup_knowledge_graph()
    strategy = HybridSearchStrategy(store)
    
    # Query similar to deep learning
    query_embedding = [0.9, 0.85, 0.1, 0.15, 0.2]
    
    config = HybridSearchConfig(
        mode=SearchMode.HYBRID,
        vector_weight=0.2,
        graph_weight=0.8,
        max_results=5,
        max_graph_depth=2,
        expand_results=True
    )
    
    print(f"\nSearch Mode: {config.mode}")
    print(f"Vector weight: {config.vector_weight} (LOW)")
    print(f"Graph weight: {config.graph_weight} (HIGH)")
    print(f"Max graph depth: {config.max_graph_depth}")
    
    results = await strategy.search(query_embedding, config)
    
    print(f"\nFound {len(results)} results:")
    print("(Results favor graph connections over vector similarity)")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {entity.id}")
        print(f"   Name: {props.get('name')}")
        print(f"   Combined Score: {score:.4f}")
    
    await store.close()


async def example_6_search_with_paths():
    """Example 6: Hybrid search with path tracking"""
    print("\n" + "=" * 70)
    print("Example 6: Hybrid Search with Path Tracking")
    print("=" * 70)
    
    store = await setup_knowledge_graph()
    strategy = HybridSearchStrategy(store)
    
    # Query for ML topics
    query_embedding = [0.5, 0.5, 0.5, 0.5, 0.5]
    
    config = HybridSearchConfig(
        mode=SearchMode.HYBRID,
        vector_weight=0.5,
        graph_weight=0.5,
        max_results=5,
        max_graph_depth=2,
        expand_results=True
    )
    
    print(f"\nSearch with path tracking enabled")
    
    results, paths = await strategy.search_with_expansion(
        query_embedding,
        config,
        include_paths=True
    )
    
    print(f"\nFound {len(results)} results:")
    for i, (entity, score) in enumerate(results[:3], 1):  # Show top 3
        props = entity.properties
        print(f"{i}. {entity.id}: {props.get('name')} (score: {score:.4f})")
    
    if paths:
        print(f"\nFound {len(paths)} paths connecting results:")
        for i, path in enumerate(paths[:3], 1):  # Show top 3 paths
            print(f"{i}. {path}")
    else:
        print("\nNo paths found between results")
    
    await store.close()


async def example_7_filtered_search():
    """Example 7: Hybrid search with entity type filter"""
    print("\n" + "=" * 70)
    print("Example 7: Hybrid Search with Entity Type Filter")
    print("=" * 70)
    
    store = await setup_knowledge_graph()
    strategy = HybridSearchStrategy(store)
    
    # Query for algorithms
    query_embedding = [0.7, 0.7, 0.3, 0.3, 0.3]
    
    config = HybridSearchConfig(
        mode=SearchMode.HYBRID,
        vector_weight=0.6,
        graph_weight=0.4,
        max_results=10,
        entity_type_filter="Algorithm",  # Only return Algorithm entities
        expand_results=True
    )
    
    print(f"\nSearch Mode: {config.mode}")
    print(f"Entity type filter: {config.entity_type_filter}")
    
    results = await strategy.search(query_embedding, config)
    
    print(f"\nFound {len(results)} Algorithm entities:")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {entity.id} ({entity.entity_type})")
        print(f"   Name: {props.get('name')}")
        print(f"   Score: {score:.4f}")
    
    await store.close()


async def example_8_threshold_filtering():
    """Example 8: Hybrid search with score threshold"""
    print("\n" + "=" * 70)
    print("Example 8: Hybrid Search with Score Threshold")
    print("=" * 70)
    
    store = await setup_knowledge_graph()
    strategy = HybridSearchStrategy(store)
    
    query_embedding = [0.85, 0.8, 0.15, 0.2, 0.25]
    
    config = HybridSearchConfig(
        mode=SearchMode.HYBRID,
        vector_weight=0.7,
        graph_weight=0.3,
        max_results=10,
        vector_threshold=0.8,  # High vector similarity threshold
        min_combined_score=0.5,  # Minimum combined score
        expand_results=True
    )
    
    print(f"\nSearch Mode: {config.mode}")
    print(f"Vector threshold: {config.vector_threshold}")
    print(f"Min combined score: {config.min_combined_score}")
    
    results = await strategy.search(query_embedding, config)
    
    print(f"\nFound {len(results)} high-quality results:")
    for i, (entity, score) in enumerate(results, 1):
        props = entity.properties
        print(f"{i}. {entity.id}")
        print(f"   Name: {props.get('name')}")
        print(f"   Score: {score:.4f}")
    
    await store.close()


async def main():
    """Run all examples"""
    await example_1_vector_only_search()
    await example_2_graph_only_search()
    await example_3_hybrid_search_balanced()
    await example_4_hybrid_search_vector_heavy()
    await example_5_hybrid_search_graph_heavy()
    await example_6_search_with_paths()
    await example_7_filtered_search()
    await example_8_threshold_filtering()
    
    print("\n" + "=" * 70)
    print("All Hybrid Search Examples Completed!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("1. Vector search finds semantically similar entities")
    print("2. Graph search explores structural relationships")
    print("3. Hybrid search combines both for better results")
    print("4. Adjust weights to favor similarity vs. structure")
    print("5. Use filters and thresholds for precision")


if __name__ == "__main__":
    asyncio.run(main())

