"""
PostgreSQL Index Optimization

Provides index analysis, recommendations, and automated index creation
based on query patterns and workload analysis.
"""

import logging
import asyncpg  # type: ignore[import-untyped]
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IndexRecommendation:
    """Index creation recommendation"""

    table_name: str
    columns: List[str]
    index_type: str  # btree, gin, gist, ivfflat
    reason: str
    estimated_benefit: str  # "high", "medium", "low"
    create_sql: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "table": self.table_name,
            "columns": self.columns,
            "type": self.index_type,
            "reason": self.reason,
            "benefit": self.estimated_benefit,
            "sql": self.create_sql,
        }


@dataclass
class IndexInfo:
    """Information about an existing index"""

    index_name: str
    table_name: str
    columns: List[str]
    index_type: str
    is_unique: bool
    size_bytes: int
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.index_name,
            "table": self.table_name,
            "columns": self.columns,
            "type": self.index_type,
            "unique": self.is_unique,
            "size_mb": round(self.size_bytes / (1024 * 1024), 2),
            "usage_count": self.usage_count,
        }


class IndexOptimizer:
    """
    Analyze and optimize PostgreSQL indexes for graph storage

    Provides:
    - Index analysis and usage statistics
    - Query pattern analysis
    - Index recommendations
    - Automated index creation

    Example:
        ```python
        optimizer = IndexOptimizer(conn)

        # Analyze existing indexes
        indexes = await optimizer.analyze_indexes()

        # Get recommendations
        recommendations = await optimizer.get_recommendations()
        for rec in recommendations:
            print(rec.create_sql)

        # Apply recommendations
        await optimizer.apply_recommendations(recommendations)
        ```
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize index optimizer

        Args:
            pool: PostgreSQL connection pool
        """
        self.pool = pool

    async def analyze_indexes(self) -> List[IndexInfo]:
        """
        Analyze all indexes on graph tables

        Returns:
            List of IndexInfo with usage statistics
        """
        async with self.pool.acquire() as conn:
            # Query index information
            query = """
                SELECT
                    i.indexrelid::regclass AS index_name,
                    i.indrelid::regclass AS table_name,
                    array_agg(a.attname ORDER BY x.n) AS columns,
                    am.amname AS index_type,
                    i.indisunique AS is_unique,
                    pg_relation_size(i.indexrelid) AS size_bytes,
                    COALESCE(s.idx_scan, 0) AS usage_count
                FROM
                    pg_index i
                    JOIN pg_class c ON c.oid = i.indrelid
                    JOIN pg_am am ON am.oid = c.relam
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS x(attnum, n)
                    LEFT JOIN pg_stat_user_indexes s ON s.indexrelid = i.indexrelid
                WHERE
                    c.relname IN ('graph_entities', 'graph_relations')
                    AND a.attnum = x.attnum
                GROUP BY
                    i.indexrelid, i.indrelid, am.amname, i.indisunique, s.idx_scan
                ORDER BY
                    table_name, index_name
            """

            rows = await conn.fetch(query)

            indexes = []
            for row in rows:
                indexes.append(
                    IndexInfo(
                        index_name=str(row["index_name"]),
                        table_name=str(row["table_name"]),
                        columns=list(row["columns"]),
                        index_type=row["index_type"],
                        is_unique=row["is_unique"],
                        size_bytes=row["size_bytes"],
                        usage_count=row["usage_count"],
                    )
                )

            return indexes

    async def get_unused_indexes(self, min_usage_threshold: int = 10) -> List[IndexInfo]:
        """
        Find indexes that are rarely or never used

        Args:
            min_usage_threshold: Minimum usage count to consider index used

        Returns:
            List of unused indexes
        """
        indexes = await self.analyze_indexes()
        unused = [idx for idx in indexes if idx.usage_count < min_usage_threshold]
        return unused

    async def get_missing_index_recommendations(
        self,
    ) -> List[IndexRecommendation]:
        """
        Analyze query patterns and recommend missing indexes

        Returns:
            List of index recommendations
        """
        recommendations = []

        async with self.pool.acquire() as conn:
            # Check for missing indexes based on common query patterns

            # 1. Check if composite index on (entity_type, properties) would be beneficial
            # This is useful for queries filtering by type and JSONB properties
            entity_type_props_exists = await self._index_exists(conn, "graph_entities", ["entity_type", "properties"])
            if not entity_type_props_exists:
                recommendations.append(
                    IndexRecommendation(
                        table_name="graph_entities",
                        columns=["entity_type", "properties"],
                        index_type="gin",
                        reason="Queries often filter by entity_type and search properties",
                        estimated_benefit="medium",
                        create_sql=("CREATE INDEX CONCURRENTLY idx_graph_entities_type_props " "ON graph_entities (entity_type, properties jsonb_path_ops)"),
                    )
                )

            # 2. Check for relation composite indexes
            source_type_exists = await self._index_exists(conn, "graph_relations", ["source_id", "relation_type"])
            if not source_type_exists:
                recommendations.append(
                    IndexRecommendation(
                        table_name="graph_relations",
                        columns=["source_id", "relation_type"],
                        index_type="btree",
                        reason="Queries often filter relations by source and type",
                        estimated_benefit="high",
                        create_sql=("CREATE INDEX CONCURRENTLY idx_graph_relations_source_type " "ON graph_relations (source_id, relation_type)"),
                    )
                )

            target_type_exists = await self._index_exists(conn, "graph_relations", ["target_id", "relation_type"])
            if not target_type_exists:
                recommendations.append(
                    IndexRecommendation(
                        table_name="graph_relations",
                        columns=["target_id", "relation_type"],
                        index_type="btree",
                        reason="Queries often filter incoming relations by target and type",
                        estimated_benefit="high",
                        create_sql=("CREATE INDEX CONCURRENTLY idx_graph_relations_target_type " "ON graph_relations (target_id, relation_type)"),
                    )
                )

            # 3. Check for weight index (useful for weighted path finding)
            weight_exists = await self._index_exists(conn, "graph_relations", ["weight"])
            if not weight_exists:
                recommendations.append(
                    IndexRecommendation(
                        table_name="graph_relations",
                        columns=["weight"],
                        index_type="btree",
                        reason="Weight-based path finding and sorting",
                        estimated_benefit="low",
                        create_sql=("CREATE INDEX CONCURRENTLY idx_graph_relations_weight " "ON graph_relations (weight)"),
                    )
                )

            # 4. Check for timestamp indexes (useful for temporal queries)
            entity_created_exists = await self._index_exists(conn, "graph_entities", ["created_at"])
            if not entity_created_exists:
                recommendations.append(
                    IndexRecommendation(
                        table_name="graph_entities",
                        columns=["created_at"],
                        index_type="btree",
                        reason="Temporal queries (recently created entities)",
                        estimated_benefit="low",
                        create_sql=("CREATE INDEX CONCURRENTLY idx_graph_entities_created " "ON graph_entities (created_at)"),
                    )
                )

        return recommendations

    async def _index_exists(self, conn: asyncpg.Connection, table_name: str, columns: List[str]) -> bool:
        """Check if an index exists on specified columns"""
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM pg_index i
                JOIN pg_class c ON c.oid = i.indrelid
                JOIN pg_attribute a ON a.attrelid = i.indrelid
                WHERE c.relname = $1
                AND array_agg(a.attname) @> $2::text[]
                GROUP BY i.indexrelid
            )
        """
        result = await conn.fetchval(query, table_name, columns)
        return result or False

    async def apply_recommendations(self, recommendations: List[IndexRecommendation], dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply index recommendations

        Args:
            recommendations: List of recommendations to apply
            dry_run: If True, only show what would be done

        Returns:
            Dictionary with results
        """
        results: Dict[str, List[Dict[str, Any]]] = {
            "applied": [],
            "failed": [],
            "skipped": [],
        }

        for rec in recommendations:
            try:
                if dry_run:
                    logger.info(f"[DRY RUN] Would create index: {rec.create_sql}")
                    results["skipped"].append({"recommendation": rec.to_dict(), "reason": "dry_run"})
                    continue

                # Create index
                async with self.pool.acquire() as conn:
                    logger.info(f"Creating index: {rec.create_sql}")
                    await conn.execute(rec.create_sql)
                    results["applied"].append(rec.to_dict())
                    logger.info(f"Successfully created index on {rec.table_name}({', '.join(rec.columns)})")

            except Exception as e:
                logger.error(f"Failed to create index: {e}")
                results["failed"].append({"recommendation": rec.to_dict(), "error": str(e)})

        return results

    async def analyze_table_stats(self) -> Dict[str, Any]:
        """
        Get table statistics for optimization decisions

        Returns:
            Dictionary with table statistics
        """
        async with self.pool.acquire() as conn:
            stats_query = """
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                    pg_stat_get_live_tuples(schemaname||'.'||tablename::regclass) AS row_count,
                    pg_stat_get_dead_tuples(schemaname||'.'||tablename::regclass) AS dead_tuples,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE tablename IN ('graph_entities', 'graph_relations')
            """

            rows = await conn.fetch(stats_query)

            stats = {}
            for row in rows:
                stats[row["tablename"]] = {
                    "total_size": row["total_size"],
                    "row_count": row["row_count"],
                    "dead_tuples": row["dead_tuples"],
                    "last_vacuum": (row["last_vacuum"].isoformat() if row["last_vacuum"] else None),
                    "last_autovacuum": (row["last_autovacuum"].isoformat() if row["last_autovacuum"] else None),
                    "last_analyze": (row["last_analyze"].isoformat() if row["last_analyze"] else None),
                    "last_autoanalyze": (row["last_autoanalyze"].isoformat() if row["last_autoanalyze"] else None),
                }

            return stats

    async def vacuum_analyze(self, table_name: Optional[str] = None) -> None:
        """
        Run VACUUM ANALYZE on graph tables

        Args:
            table_name: Specific table to analyze (None for all graph tables)
        """
        tables = [table_name] if table_name else ["graph_entities", "graph_relations"]

        async with self.pool.acquire() as conn:
            for table in tables:
                logger.info(f"Running VACUUM ANALYZE on {table}")
                await conn.execute(f"VACUUM ANALYZE {table}")
                logger.info(f"Completed VACUUM ANALYZE on {table}")

    async def get_optimization_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive optimization report

        Returns:
            Dictionary with optimization recommendations and statistics
        """
        # Get all information
        indexes = await self.analyze_indexes()
        unused_indexes = await self.get_unused_indexes()
        recommendations = await self.get_missing_index_recommendations()
        table_stats = await self.analyze_table_stats()

        # Calculate totals
        total_index_size = sum(idx.size_bytes for idx in indexes)
        unused_index_size = sum(idx.size_bytes for idx in unused_indexes)

        report = {
            "indexes": {
                "total_count": len(indexes),
                "total_size_mb": round(total_index_size / (1024 * 1024), 2),
                "unused_count": len(unused_indexes),
                "unused_size_mb": round(unused_index_size / (1024 * 1024), 2),
                "details": [idx.to_dict() for idx in indexes],
            },
            "unused_indexes": [idx.to_dict() for idx in unused_indexes],
            "recommendations": [rec.to_dict() for rec in recommendations],
            "table_stats": table_stats,
            "summary": {
                "total_recommendations": len(recommendations),
                "high_priority": len([r for r in recommendations if r.estimated_benefit == "high"]),
                "medium_priority": len([r for r in recommendations if r.estimated_benefit == "medium"]),
                "low_priority": len([r for r in recommendations if r.estimated_benefit == "low"]),
                "potential_space_savings_mb": round(unused_index_size / (1024 * 1024), 2),
            },
        }

        return report


# Pre-defined optimal index set for graph storage
OPTIMAL_INDEXES = [
    {
        "name": "idx_graph_entities_type",
        "table": "graph_entities",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_entities_type ON graph_entities(entity_type)",
    },
    {
        "name": "idx_graph_entities_properties",
        "table": "graph_entities",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_entities_properties ON graph_entities USING GIN(properties)",
    },
    {
        "name": "idx_graph_relations_type",
        "table": "graph_relations",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_relations_type ON graph_relations(relation_type)",
    },
    {
        "name": "idx_graph_relations_source",
        "table": "graph_relations",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_relations_source ON graph_relations(source_id)",
    },
    {
        "name": "idx_graph_relations_target",
        "table": "graph_relations",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_relations_target ON graph_relations(target_id)",
    },
    {
        "name": "idx_graph_relations_source_target",
        "table": "graph_relations",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_relations_source_target ON graph_relations(source_id, target_id)",
    },
    {
        "name": "idx_graph_relations_properties",
        "table": "graph_relations",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_relations_properties ON graph_relations USING GIN(properties)",
    },
    {
        "name": "idx_graph_relations_source_type",
        "table": "graph_relations",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_relations_source_type ON graph_relations(source_id, relation_type)",
    },
    {
        "name": "idx_graph_relations_target_type",
        "table": "graph_relations",
        "sql": "CREATE INDEX IF NOT EXISTS idx_graph_relations_target_type ON graph_relations(target_id, relation_type)",
    },
]
