"""
Graph Storage Migration Utilities

Provides tools to migrate graph data between different storage backends,
particularly from SQLite to PostgreSQL.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from tqdm import tqdm

from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore

logger = logging.getLogger(__name__)


class GraphStorageMigrator:
    """
    Migrates graph data from one storage backend to another

    Example:
        ```python
        # Migrate from SQLite to PostgreSQL
        source = SQLiteGraphStore("old_graph.db")
        target = PostgresGraphStore(host="localhost", database="new_graph")

        migrator = GraphStorageMigrator(source, target)
        await migrator.migrate(batch_size=1000, show_progress=True)
        ```
    """

    def __init__(self, source: GraphStore, target: GraphStore):
        """
        Initialize migrator

        Args:
            source: Source graph store to migrate from
            target: Target graph store to migrate to
        """
        self.source = source
        self.target = target

    async def migrate(
        self,
        batch_size: int = 1000,
        show_progress: bool = True,
        verify: bool = True,
    ) -> Dict[str, Any]:
        """
        Migrate all graph data from source to target

        Args:
            batch_size: Number of entities/relations to migrate per batch
            show_progress: Show progress bar
            verify: Verify migration integrity after completion

        Returns:
            Migration statistics dictionary
        """
        logger.info(f"Starting migration from {type(self.source).__name__} to {type(self.target).__name__}")

        stats: Dict[str, Any] = {
            "entities_migrated": 0,
            "relations_migrated": 0,
            "errors": [],
            "duration_seconds": 0,
        }

        import time

        start_time = time.time()

        try:
            # Initialize both stores
            if not getattr(self.source, "_is_initialized", False):
                await self.source.initialize()
            if not getattr(self.target, "_is_initialized", False):
                await self.target.initialize()

            # Migrate entities
            logger.info("Migrating entities...")
            stats["entities_migrated"] = await self._migrate_entities(batch_size, show_progress)

            # Migrate relations
            logger.info("Migrating relations...")
            stats["relations_migrated"] = await self._migrate_relations(batch_size, show_progress)

            # Verify if requested
            if verify:
                logger.info("Verifying migration...")
                verification = await self._verify_migration()
                stats["verification"] = verification

                if not verification["success"]:
                    logger.warning(f"Migration verification found issues: {verification}")

            stats["duration_seconds"] = time.time() - start_time
            logger.info(f"Migration completed in {stats['duration_seconds']:.2f}s")
            logger.info(f"Migrated {stats['entities_migrated']} entities and {stats['relations_migrated']} relations")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            if isinstance(stats, dict) and "errors" in stats:
                stats["errors"].append(str(e))
            raise

        return stats

    async def _migrate_entities(self, batch_size: int, show_progress: bool) -> int:
        """Migrate all entities from source to target"""
        # Get all entities from source (available via PaginationMixinProtocol)
        entities = await self.source.get_all_entities()  # type: ignore[attr-defined]
        total = len(entities)

        if total == 0:
            logger.warning("No entities to migrate")
            return 0

        # Use tqdm for progress if requested
        iterator = tqdm(entities, desc="Entities", disable=not show_progress) if show_progress else entities

        migrated = 0
        errors = []

        # Migrate in batches using transactions
        for i in range(0, total, batch_size):
            batch = entities[i : i + batch_size]

            try:
                # transaction() available via TransactionMixinProtocol
                async with self.target.transaction():  # type: ignore[attr-defined]
                    for entity in batch:
                        try:
                            await self.target.add_entity(entity)
                            migrated += 1
                            if show_progress:
                                iterator.update(1)
                        except Exception as e:
                            error_msg = f"Failed to migrate entity {entity.id}: {e}"
                            logger.error(error_msg)
                            errors.append(error_msg)
            except Exception as e:
                logger.error(f"Batch transaction failed: {e}")
                # Continue with next batch

        if errors:
            logger.warning(f"Entity migration completed with {len(errors)} errors")

        return migrated

    async def _migrate_relations(self, batch_size: int, show_progress: bool) -> int:
        """Migrate all relations from source to target"""
        # Get all relations by getting all entities and their neighbors
        # This is a workaround since we don't have a direct get_all_relations
        # method (available via PaginationMixinProtocol)
        all_entities = await self.source.get_all_entities()  # type: ignore[attr-defined]
        relations = []

        # Collect all unique relations
        for entity in all_entities:
            # This is an approximation - we'd need a better way to get all relations
            # For now, we'll use a simpler approach
            pass

        # Alternative: If the store has a direct way to get relations, use it
        # For SQLite and Postgres, we can query the relations table directly
        if hasattr(self.source, "conn") or hasattr(self.source, "pool"):
            relations = await self._get_all_relations_direct(self.source)
        else:
            logger.warning("Cannot directly access relations, migration may be incomplete")
            return 0

        total = len(relations)

        if total == 0:
            logger.warning("No relations to migrate")
            return 0

        iterator = tqdm(relations, desc="Relations", disable=not show_progress) if show_progress else relations

        migrated = 0
        errors = []

        # Migrate in batches
        for i in range(0, total, batch_size):
            batch = relations[i : i + batch_size]

            try:
                # transaction() available via TransactionMixinProtocol
                async with self.target.transaction():  # type: ignore[attr-defined]
                    for relation in batch:
                        try:
                            await self.target.add_relation(relation)
                            migrated += 1
                            if show_progress and hasattr(iterator, "update"):
                                iterator.update(1)
                        except Exception as e:
                            error_msg = f"Failed to migrate relation {relation.id}: {e}"
                            logger.error(error_msg)
                            errors.append(error_msg)
            except Exception as e:
                logger.error(f"Batch transaction failed: {e}")

        if errors:
            logger.warning(f"Relation migration completed with {len(errors)} errors")

        return migrated

    async def _get_all_relations_direct(self, store: GraphStore) -> list:
        """Get all relations directly from database"""
        from aiecs.domain.knowledge_graph.models.relation import Relation

        relations = []

        if isinstance(store, SQLiteGraphStore):
            # SQLite direct query
            if store.conn is None:
                raise RuntimeError("SQLite connection not initialized")
            cursor = await store.conn.execute("SELECT id, relation_type, source_id, target_id, properties, weight FROM relations")
            rows = await cursor.fetchall()

            for row in rows:
                import json

                relations.append(
                    Relation(
                        id=row[0],
                        relation_type=row[1],
                        source_id=row[2],
                        target_id=row[3],
                        properties=json.loads(row[4]) if row[4] else {},
                        weight=row[5] if row[5] else 1.0,
                    )
                )

        elif isinstance(store, PostgresGraphStore):
            # PostgreSQL direct query
            if store.pool is None:
                raise RuntimeError("PostgreSQL connection pool not initialized")
            async with store.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, relation_type, source_id, target_id, properties, weight
                    FROM graph_relations
                """
                )

                for row in rows:
                    relations.append(
                        Relation(
                            id=row["id"],
                            relation_type=row["relation_type"],
                            source_id=row["source_id"],
                            target_id=row["target_id"],
                            properties=(row["properties"] if isinstance(row["properties"], dict) else {}),
                            weight=(float(row["weight"]) if row["weight"] else 1.0),
                        )
                    )

        return relations

    async def _verify_migration(self) -> Dict[str, Any]:
        """Verify migration integrity"""
        try:
            # Get counts from both stores (available via StatsMixinProtocol)
            source_stats = await self.source.get_stats()  # type: ignore[attr-defined]
            target_stats = await self.target.get_stats()  # type: ignore[attr-defined]

            entity_match = source_stats["entity_count"] == target_stats["entity_count"]
            relation_match = source_stats["relation_count"] == target_stats["relation_count"]

            return {
                "success": entity_match and relation_match,
                "source_entities": source_stats["entity_count"],
                "target_entities": target_stats["entity_count"],
                "source_relations": source_stats["relation_count"],
                "target_relations": target_stats["relation_count"],
                "entity_match": entity_match,
                "relation_match": relation_match,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


async def migrate_sqlite_to_postgres(
    sqlite_path: str,
    postgres_config: Optional[Dict[str, Any]] = None,
    batch_size: int = 1000,
    show_progress: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to migrate from SQLite to PostgreSQL

    Args:
        sqlite_path: Path to SQLite database file
        postgres_config: PostgreSQL connection config (or None to use defaults)
        batch_size: Batch size for migration
        show_progress: Show progress bars

    Returns:
        Migration statistics

    Example:
        ```python
        stats = await migrate_sqlite_to_postgres(
            "knowledge_graph.db",
            postgres_config={
                "host": "localhost",
                "database": "production_kg"
            }
        )
        print(f"Migrated {stats['entities_migrated']} entities")
        ```
    """
    # Create stores
    source = SQLiteGraphStore(sqlite_path)

    if postgres_config:
        target = PostgresGraphStore(**postgres_config)
    else:
        target = PostgresGraphStore()  # Use defaults from config

    # Migrate
    migrator = GraphStorageMigrator(source, target)

    try:
        stats = await migrator.migrate(batch_size=batch_size, show_progress=show_progress)
        return stats
    finally:
        await source.close()
        await target.close()


# CLI support
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Migrate graph storage between backends")
    parser.add_argument("--source-sqlite", help="Source SQLite database path")
    parser.add_argument("--target-pg-host", default="localhost", help="Target PostgreSQL host")
    parser.add_argument(
        "--target-pg-port",
        type=int,
        default=5432,
        help="Target PostgreSQL port",
    )
    parser.add_argument(
        "--target-pg-database",
        required=True,
        help="Target PostgreSQL database",
    )
    parser.add_argument("--target-pg-user", default="postgres", help="Target PostgreSQL user")
    parser.add_argument("--target-pg-password", help="Target PostgreSQL password")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress bars")

    args = parser.parse_args()

    if not args.source_sqlite:
        print("Error: --source-sqlite is required")
        sys.exit(1)

    async def run():
        stats = await migrate_sqlite_to_postgres(
            sqlite_path=args.source_sqlite,
            postgres_config={
                "host": args.target_pg_host,
                "port": args.target_pg_port,
                "database": args.target_pg_database,
                "user": args.target_pg_user,
                "password": args.target_pg_password,
            },
            batch_size=args.batch_size,
            show_progress=not args.no_progress,
        )

        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"Entities migrated: {stats['entities_migrated']}")
        print(f"Relations migrated: {stats['relations_migrated']}")
        print(f"Duration: {stats['duration_seconds']:.2f}s")

        if stats.get("verification"):
            ver = stats["verification"]
            if ver["success"]:
                print("✅ Verification: PASSED")
            else:
                print("❌ Verification: FAILED")
                print(f"   Source entities: {ver['source_entities']}, Target: {ver['target_entities']}")
                print(f"   Source relations: {ver['source_relations']}, Target: {ver['target_relations']}")

        if stats["errors"]:
            print(f"\n⚠️  Errors encountered: {len(stats['errors'])}")

    asyncio.run(run())
