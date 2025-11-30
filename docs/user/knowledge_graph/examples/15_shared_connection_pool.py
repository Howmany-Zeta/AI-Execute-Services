"""
Example: Sharing Connection Pool Between DatabaseManager and PostgresGraphStore

Demonstrates how to reuse AIECS's DatabaseManager connection pool
for graph storage, avoiding duplicate pools.
"""

import asyncio
from aiecs.infrastructure.persistence import DatabaseManager
from aiecs.infrastructure.graph_storage import PostgresGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


async def main():
    """Main example function"""
    
    print("=" * 60)
    print("Example: Shared Connection Pool")
    print("=" * 60)
    
    # 1. Create DatabaseManager (AIECS's standard way)
    print("\n1. Creating DatabaseManager...")
    db_manager = DatabaseManager()
    await db_manager.connect(min_size=5, max_size=15)
    print(f"   DatabaseManager connected with pool size: 5-15")
    
    # 2. Create PostgresGraphStore reusing DatabaseManager's pool
    print("\n2. Creating PostgresGraphStore (reusing pool)...")
    
    # Option A: Pass database_manager instance
    graph_store = PostgresGraphStore(
        database_manager=db_manager,
        enable_pgvector=False
    )
    
    # Option B (alternative): Pass pool directly
    # graph_store = PostgresGraphStore(
    #     pool=db_manager.connection_pool,
    #     enable_pgvector=False
    # )
    
    await graph_store.initialize()
    print("   PostgresGraphStore initialized with shared pool")
    
    # 3. Use both components with same connection pool
    print("\n3. Using shared connection pool...")
    
    # Graph store operations
    entity = Entity(
        id="shared_e1",
        entity_type="Person",
        properties={"name": "Shared Pool User"}
    )
    await graph_store.add_entity(entity)
    print("   Added entity via graph store")
    
    # Retrieve entity
    retrieved = await graph_store.get_entity("shared_e1")
    print(f"   Retrieved entity: {retrieved.properties['name']}")
    
    # 4. Show pool statistics
    print("\n4. Pool statistics:")
    pool = db_manager.connection_pool
    print(f"   Pool size: {pool.get_size()}")
    print(f"   Free connections: {pool.get_idle_size()}")
    print(f"   Pool shared by: DatabaseManager + PostgresGraphStore")
    
    # 5. Cleanup
    print("\n5. Cleaning up...")
    await graph_store.close()  # Won't close the pool (doesn't own it)
    print("   PostgresGraphStore detached from pool")
    
    await db_manager.close()  # This actually closes the pool
    print("   DatabaseManager closed pool")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)
    print("\nBenefit: Only one connection pool used for both systems!")


async def comparison_example():
    """Show the difference between shared and separate pools"""
    
    print("\n" + "=" * 60)
    print("Comparison: Shared vs Separate Pools")
    print("=" * 60)
    
    # Separate pools (old way - WASTEFUL)
    print("\n❌ Separate Pools (Wasteful):")
    db_manager = DatabaseManager()
    await db_manager.connect(min_size=10, max_size=20)
    
    graph_store = PostgresGraphStore()  # Creates its own pool
    await graph_store.initialize()
    
    print("   - DatabaseManager pool: 10-20 connections")
    print("   - GraphStore pool: 5-20 connections")
    print("   - Total: 15-40 connections (WASTEFUL!)")
    
    await graph_store.close()
    await db_manager.close()
    
    # Shared pool (new way - EFFICIENT)
    print("\n✅ Shared Pool (Efficient):")
    db_manager = DatabaseManager()
    await db_manager.connect(min_size=10, max_size=20)
    
    graph_store = PostgresGraphStore(database_manager=db_manager)
    await graph_store.initialize()
    
    print("   - Shared pool: 10-20 connections")
    print("   - Total: 10-20 connections (EFFICIENT!)")
    print("   - Savings: Up to 20 connections")
    
    await graph_store.close()
    await db_manager.close()


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())
    
    # Run comparison
    asyncio.run(comparison_example())

