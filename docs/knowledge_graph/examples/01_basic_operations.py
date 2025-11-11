"""
Example: Basic Knowledge Graph Operations

This example demonstrates basic operations with the knowledge graph:
- Creating entities and relations
- Querying neighbors
- Graph traversal
"""

import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


async def main():
    """Run basic knowledge graph operations"""
    
    # Initialize the graph store
    print("=== Initializing Graph Store ===")
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities
    print("\n=== Creating Entities ===")
    
    alice = Entity(
        id="alice",
        entity_type="Person",
        properties={
            "name": "Alice",
            "age": 30,
            "occupation": "Data Scientist"
        }
    )
    await store.add_entity(alice)
    print(f"Created: {alice}")
    
    bob = Entity(
        id="bob",
        entity_type="Person",
        properties={
            "name": "Bob",
            "age": 28,
            "occupation": "Software Engineer"
        }
    )
    await store.add_entity(bob)
    print(f"Created: {bob}")
    
    charlie = Entity(
        id="charlie",
        entity_type="Person",
        properties={
            "name": "Charlie",
            "age": 35,
            "occupation": "Product Manager"
        }
    )
    await store.add_entity(charlie)
    print(f"Created: {charlie}")
    
    company = Entity(
        id="tech_corp",
        entity_type="Company",
        properties={
            "name": "Tech Corp",
            "industry": "Technology"
        }
    )
    await store.add_entity(company)
    print(f"Created: {company}")
    
    # Create relations
    print("\n=== Creating Relations ===")
    
    await store.add_relation(Relation(
        id="r1",
        relation_type="KNOWS",
        source_id="alice",
        target_id="bob",
        properties={"since": "2020"}
    ))
    print("Created: Alice KNOWS Bob")
    
    await store.add_relation(Relation(
        id="r2",
        relation_type="KNOWS",
        source_id="bob",
        target_id="charlie",
        properties={"since": "2019"}
    ))
    print("Created: Bob KNOWS Charlie")
    
    await store.add_relation(Relation(
        id="r3",
        relation_type="WORKS_FOR",
        source_id="alice",
        target_id="tech_corp",
        properties={"role": "Data Scientist", "since": "2021"}
    ))
    print("Created: Alice WORKS_FOR Tech Corp")
    
    await store.add_relation(Relation(
        id="r4",
        relation_type="WORKS_FOR",
        source_id="bob",
        target_id="tech_corp",
        properties={"role": "Engineer", "since": "2020"}
    ))
    print("Created: Bob WORKS_FOR Tech Corp")
    
    # Query operations
    print("\n=== Querying Graph ===")
    
    # Get entity
    retrieved_alice = await store.get_entity("alice")
    print(f"Retrieved: {retrieved_alice.properties['name']}, age {retrieved_alice.properties['age']}")
    
    # Get neighbors
    alice_colleagues = await store.get_neighbors("alice", direction="outgoing")
    print(f"\nAlice's connections (outgoing): {[e.properties['name'] for e in alice_colleagues]}")
    
    # Get specific relation type
    alice_coworkers = await store.get_neighbors("alice", relation_type="WORKS_FOR", direction="outgoing")
    print(f"Alice works for: {[e.properties['name'] for e in alice_coworkers]}")
    
    # Tier 2 operations (work automatically!)
    print("\n=== Advanced Operations (Tier 2) ===")
    
    # Graph traversal
    paths = await store.traverse("alice", max_depth=2)
    print(f"\nFound {len(paths)} paths from Alice (depth <= 2)")
    
    # Path finding
    paths_to_charlie = await store.find_paths("alice", "charlie", max_depth=5)
    print(f"\nFound {len(paths_to_charlie)} path(s) from Alice to Charlie")
    for path in paths_to_charlie:
        print(f"  Path: {' -> '.join(path.get_entity_ids())}")
    
    # Statistics
    print("\n=== Graph Statistics ===")
    stats = store.get_stats()
    print(f"Total entities: {stats['entities']}")
    print(f"Total relations: {stats['relations']}")
    
    # Cleanup
    print("\n=== Cleanup ===")
    await store.close()
    print("Graph store closed")


if __name__ == "__main__":
    asyncio.run(main())

