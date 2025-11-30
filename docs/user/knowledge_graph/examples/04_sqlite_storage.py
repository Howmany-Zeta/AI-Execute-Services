"""
Example: SQLite Persistent Storage

This example demonstrates using SQLite for persistent graph storage.
"""

import asyncio
from pathlib import Path
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


async def main():
    print("━" * 80)
    print("Knowledge Graph Example: SQLite Persistent Storage")
    print("━" * 80)
    
    # Create database file
    db_path = "example_graph.db"
    
    # Step 1: Initialize SQLite store
    print(f"\n🔧 Creating SQLite graph store: {db_path}")
    store = SQLiteGraphStore(db_path)
    await store.initialize()
    
    # Step 2: Add entities
    print("\n📝 Adding entities...")
    
    alice = Entity(
        id="person_alice",
        entity_type="Person",
        properties={"name": "Alice Johnson", "age": 30, "occupation": "Software Engineer"}
    )
    await store.add_entity(alice)
    
    tech_corp = Entity(
        id="company_techcorp",
        entity_type="Company",
        properties={"name": "Tech Corp", "founded": 2015, "industry": "AI"}
    )
    await store.add_entity(tech_corp)
    
    san_francisco = Entity(
        id="location_sf",
        entity_type="Location",
        properties={"name": "San Francisco", "country": "USA"}
    )
    await store.add_entity(san_francisco)
    
    print(f"  ✅ Added {3} entities")
    
    # Step 3: Add relations
    print("\n🔗 Adding relations...")
    
    works_for = Relation(
        id="rel_alice_techcorp",
        relation_type="WORKS_FOR",
        source_id="person_alice",
        target_id="company_techcorp",
        properties={"since": "2020", "role": "Senior Engineer"}
    )
    await store.add_relation(works_for)
    
    located_in = Relation(
        id="rel_techcorp_sf",
        relation_type="LOCATED_IN",
        source_id="company_techcorp",
        target_id="location_sf"
    )
    await store.add_relation(located_in)
    
    print(f"  ✅ Added {2} relations")
    
    # Step 4: Query the graph
    print("\n🔍 Querying graph...")
    
    # Get entity
    retrieved_alice = await store.get_entity("person_alice")
    print(f"  Retrieved entity: {retrieved_alice.properties['name']}")
    
    # Get neighbors
    neighbors = await store.get_neighbors("person_alice", direction="outgoing")
    print(f"  Alice's neighbors: {len(neighbors)}")
    for entity in neighbors:
        print(f"    - {entity.entity_type}: {entity.properties['name']}")
    
    # Traverse graph
    print("\n🗺️  Traversing graph from Alice...")
    paths = await store.traverse(
        start_entity_id="person_alice",
        max_depth=2,
        max_results=10
    )
    print(f"  Found {len(paths)} paths in traversal")
    # Extract unique entities from paths
    entities_found = set()
    for path in paths:
        for entity in path.nodes:
            entities_found.add((entity.entity_type, entity.properties.get('name', entity.id)))
    
    print(f"  Unique entities: {len(entities_found)}")
    for entity_type, name in entities_found:
        print(f"    - {entity_type}: {name}")
    
    # Step 5: Get statistics
    print("\n" + "━" * 80)
    print("📊 STORAGE STATISTICS")
    print("━" * 80)
    
    stats = await store.get_stats()
    print(f"Storage type: {stats['storage_type']}")
    print(f"Database path: {stats['db_path']}")
    print(f"Database size: {stats['db_size_bytes']} bytes")
    print(f"Total entities: {stats['entity_count']}")
    print(f"Total relations: {stats['relation_count']}")
    
    # Step 6: Close and reopen to demonstrate persistence
    print("\n" + "━" * 80)
    print("🔄 TESTING PERSISTENCE")
    print("━" * 80)
    
    print("Closing database...")
    await store.close()
    
    print("Reopening database...")
    store2 = SQLiteGraphStore(db_path)
    await store2.initialize()
    
    # Verify data persisted
    alice_persisted = await store2.get_entity("person_alice")
    print(f"✅ Data persisted! Retrieved: {alice_persisted.properties['name']}")
    
    stats2 = await store2.get_stats()
    print(f"  Entities in reopened DB: {stats2['entity_count']}")
    print(f"  Relations in reopened DB: {stats2['relation_count']}")
    
    # Cleanup
    await store2.close()
    
    # Optional: delete database file
    Path(db_path).unlink()
    print(f"\n🗑️  Cleaned up database file: {db_path}")
    
    print("\n✅ Example complete!")
    print("━" * 80)


if __name__ == "__main__":
    asyncio.run(main())

