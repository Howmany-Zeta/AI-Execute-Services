"""
Result Repository Implementation

Implements result-specific data repository operations for the multi-task service.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid

from ...core.interfaces.data_repository import IResultRepository
from ...core.models.execution_models import ExecutionResult, ExecutionContext
from ...core.exceptions.data_exceptions import DataRepositoryError, DataNotFoundError
from app.infrastructure.persistence.file_storage import get_file_storage
from app.infrastructure.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ResultRepository(IResultRepository):
    """
    Result repository implementation using hybrid storage (database + file storage).

    Strategy:
    - Result metadata and indexes stored in database for fast queries
    - Large result data stored in file storage
    - Results cached for performance
    - Automatic cleanup of old results
    """

    def __init__(self, db_manager: DatabaseManager, storage_config: Optional[Dict[str, Any]] = None):
        self.db_manager = db_manager
        self.file_storage = get_file_storage(storage_config)
        self._initialized = False
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 300  # 5 minutes

    async def initialize(self):
        """Initialize the repository."""
        if not self._initialized:
            await self.file_storage.initialize()
            await self._create_tables()
            self._initialized = True
            logger.info("ResultRepository initialized successfully")

    async def _create_tables(self):
        """Create database tables for result metadata."""
        if not self.db_manager._initialized:
            await self.db_manager.init_database_schema()

        # Create additional tables for result repository
        if self.db_manager.connection_pool:
            async with self.db_manager.connection_pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS execution_results_metadata (
                        result_id TEXT PRIMARY KEY,
                        execution_id TEXT,
                        step_id TEXT,
                        task_type TEXT,
                        status TEXT,
                        quality_score REAL,
                        confidence_score REAL,
                        processing_time REAL,
                        data_size INTEGER,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        file_storage_key TEXT,
                        tags JSONB,
                        metadata JSONB
                    );
                    CREATE INDEX IF NOT EXISTS idx_results_execution_id ON execution_results_metadata (execution_id);
                    CREATE INDEX IF NOT EXISTS idx_results_step_id ON execution_results_metadata (step_id);
                    CREATE INDEX IF NOT EXISTS idx_results_task_type ON execution_results_metadata (task_type);
                    CREATE INDEX IF NOT EXISTS idx_results_status ON execution_results_metadata (status);
                    CREATE INDEX IF NOT EXISTS idx_results_quality_score ON execution_results_metadata (quality_score);
                    CREATE INDEX IF NOT EXISTS idx_results_created_at ON execution_results_metadata (created_at);
                    CREATE INDEX IF NOT EXISTS idx_results_expires_at ON execution_results_metadata (expires_at);

                    CREATE TABLE IF NOT EXISTS result_analytics (
                        analytics_id TEXT PRIMARY KEY,
                        result_id TEXT,
                        metric_name TEXT,
                        metric_value REAL,
                        metric_type TEXT,
                        recorded_at TIMESTAMP,
                        metadata JSONB
                    );
                    CREATE INDEX IF NOT EXISTS idx_analytics_result_id ON result_analytics (result_id);
                    CREATE INDEX IF NOT EXISTS idx_analytics_metric_name ON result_analytics (metric_name);
                    CREATE INDEX IF NOT EXISTS idx_analytics_recorded_at ON result_analytics (recorded_at);
                ''')

    # IDataRepository implementation

    async def save(self, entity: Any, context: Optional[ExecutionContext] = None) -> str:
        """Save an entity to the repository."""
        if isinstance(entity, ExecutionResult):
            return await self.save_result(entity, context)
        else:
            raise DataRepositoryError(f"Unsupported entity type: {type(entity)}")

    async def get_by_id(self, entity_id: str, entity_type: str = "result") -> Optional[Any]:
        """Retrieve an entity by its unique identifier."""
        if entity_type == "result":
            return await self.get_result_by_id(entity_id)
        else:
            raise DataRepositoryError(f"Unsupported entity type: {entity_type}")

    async def update(self, entity_id: str, updates: Dict[str, Any], context: Optional[ExecutionContext] = None) -> bool:
        """Update an existing entity."""
        try:
            if not self._initialized:
                await self.initialize()

            # Update in database
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    set_clauses = []
                    values = []
                    param_count = 1

                    for key, value in updates.items():
                        if key in ['status', 'quality_score', 'confidence_score', 'processing_time',
                                 'data_size', 'updated_at', 'expires_at', 'tags', 'metadata']:
                            set_clauses.append(f"{key} = ${param_count}")
                            if key in ['tags', 'metadata']:
                                values.append(json.dumps(value))
                            else:
                                values.append(value)
                            param_count += 1

                    if set_clauses:
                        values.append(entity_id)
                        query = f"UPDATE execution_results_metadata SET {', '.join(set_clauses)} WHERE result_id = ${param_count}"
                        result = await conn.execute(query, *values)

                        # Clear cache
                        self._cache.pop(entity_id, None)

                        return result != "UPDATE 0"

            return False

        except Exception as e:
            logger.error(f"Failed to update result {entity_id}: {e}")
            raise DataRepositoryError(f"Update failed: {e}")

    async def delete(self, entity_id: str, entity_type: str = "result") -> bool:
        """Delete an entity from the repository."""
        try:
            if not self._initialized:
                await self.initialize()

            if entity_type == "result":
                return await self.delete_result(entity_id)
            else:
                raise DataRepositoryError(f"Unsupported entity type: {entity_type}")

        except Exception as e:
            logger.error(f"Failed to delete result {entity_id}: {e}")
            raise DataRepositoryError(f"Deletion failed: {e}")

    async def find(self, criteria: Dict[str, Any], entity_type: str = "result", limit: Optional[int] = None) -> List[Any]:
        """Find entities matching the given criteria."""
        try:
            if not self._initialized:
                await self.initialize()

            if entity_type == "result":
                return await self.find_results(criteria, limit)
            else:
                raise DataRepositoryError(f"Unsupported entity type: {entity_type}")

        except Exception as e:
            logger.error(f"Failed to find results: {e}")
            raise DataRepositoryError(f"Find operation failed: {e}")

    async def count(self, criteria: Dict[str, Any], entity_type: str = "result") -> int:
        """Count entities matching the given criteria."""
        try:
            if not self._initialized:
                await self.initialize()

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    where_clauses, values = self._build_where_clause(criteria)
                    query = f"SELECT COUNT(*) FROM execution_results_metadata {where_clauses}"
                    result = await conn.fetchval(query, *values)
                    return result

            return 0

        except Exception as e:
            logger.error(f"Failed to count results: {e}")
            raise DataRepositoryError(f"Count operation failed: {e}")

    # IResultRepository implementation

    async def save_execution_result(self, result: ExecutionResult, context: ExecutionContext) -> str:
        """Save an execution result (IResultRepository interface method)."""
        return await self.save_result(result, context)

    async def get_results_by_quality_score(self, min_score: float, max_score: float = 1.0) -> List[ExecutionResult]:
        """Get results within a quality score range."""
        try:
            if not self._initialized:
                await self.initialize()

            results = []

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    query = '''
                        SELECT result_id, file_storage_key
                        FROM execution_results_metadata
                        WHERE quality_score >= $1 AND quality_score <= $2
                        ORDER BY quality_score DESC, created_at DESC
                    '''

                    records = await conn.fetch(query, min_score, max_score)

                    # Load results from file storage
                    for record in records:
                        if record['file_storage_key']:
                            result_data = await self.file_storage.retrieve(record['file_storage_key'])
                            if result_data:
                                result = ExecutionResult(**result_data)
                                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to get results by quality score: {e}")
            raise DataRepositoryError(f"Get results by quality score failed: {e}")

    async def aggregate_results(self, criteria: Dict[str, Any], aggregation_type: str) -> Dict[str, Any]:
        """Aggregate results based on criteria."""
        try:
            if not self._initialized:
                await self.initialize()

            aggregation = {}

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    where_clauses, values = self._build_where_clause(criteria)

                    if aggregation_type.lower() == "count":
                        query = f"SELECT COUNT(*) as count FROM execution_results_metadata {where_clauses}"
                        result = await conn.fetchval(query, *values)
                        aggregation['count'] = result

                    elif aggregation_type.lower() == "avg":
                        query = f"""
                            SELECT
                                AVG(quality_score) as avg_quality,
                                AVG(confidence_score) as avg_confidence,
                                AVG(processing_time) as avg_processing_time
                            FROM execution_results_metadata {where_clauses}
                        """
                        record = await conn.fetchrow(query, *values)
                        if record:
                            aggregation.update({
                                'avg_quality_score': float(record['avg_quality']) if record['avg_quality'] else 0.0,
                                'avg_confidence_score': float(record['avg_confidence']) if record['avg_confidence'] else 0.0,
                                'avg_processing_time': float(record['avg_processing_time']) if record['avg_processing_time'] else 0.0
                            })

                    elif aggregation_type.lower() == "sum":
                        query = f"""
                            SELECT
                                SUM(data_size) as total_data_size,
                                SUM(processing_time) as total_processing_time
                            FROM execution_results_metadata {where_clauses}
                        """
                        record = await conn.fetchrow(query, *values)
                        if record:
                            aggregation.update({
                                'total_data_size': int(record['total_data_size']) if record['total_data_size'] else 0,
                                'total_processing_time': float(record['total_processing_time']) if record['total_processing_time'] else 0.0
                            })

                    elif aggregation_type.lower() == "min_max":
                        query = f"""
                            SELECT
                                MIN(quality_score) as min_quality,
                                MAX(quality_score) as max_quality,
                                MIN(created_at) as earliest_result,
                                MAX(created_at) as latest_result
                            FROM execution_results_metadata {where_clauses}
                        """
                        record = await conn.fetchrow(query, *values)
                        if record:
                            aggregation.update({
                                'min_quality_score': float(record['min_quality']) if record['min_quality'] else 0.0,
                                'max_quality_score': float(record['max_quality']) if record['max_quality'] else 0.0,
                                'earliest_result': record['earliest_result'],
                                'latest_result': record['latest_result']
                            })

            return aggregation

        except Exception as e:
            logger.error(f"Failed to aggregate results: {e}")
            raise DataRepositoryError(f"Aggregate results failed: {e}")

    async def save_result(self, result: ExecutionResult, context: Optional[ExecutionContext] = None) -> str:
        """Save an execution result."""
        try:
            if not self._initialized:
                await self.initialize()

            result_id = result.result_id or str(uuid.uuid4())

            status_value = result.status.value if hasattr(result.status, 'value') else result.status

            # Store result data in file storage
            storage_key = f"results/{result.execution_id}/{result_id}.json"
            result_data = result.dict()

            await self.file_storage.store(storage_key, result_data)

            # Calculate data size
            data_size = len(json.dumps(result_data).encode('utf-8'))

            # Store metadata in database
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO execution_results_metadata
                        (result_id, execution_id, step_id, task_type, status, quality_score, confidence_score,
                         processing_time, data_size, created_at, updated_at, expires_at, file_storage_key, tags, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        ON CONFLICT (result_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        quality_score = EXCLUDED.quality_score,
                        confidence_score = EXCLUDED.confidence_score,
                        processing_time = EXCLUDED.processing_time,
                        data_size = EXCLUDED.data_size,
                        updated_at = EXCLUDED.updated_at,
                        expires_at = EXCLUDED.expires_at,
                        tags = EXCLUDED.tags,
                        metadata = EXCLUDED.metadata
                    ''',
                        result_id,
                        result.execution_id,
                        result.step_id,
                        result.metadata.get('task_type', 'unknown'),
                        status_value,
                        result.quality_score,
                        result.confidence_score,
                        result.execution_time_seconds,
                        data_size,
                        result.started_at or datetime.utcnow(),
                        datetime.utcnow(),
                        (result.started_at or datetime.utcnow()) + timedelta(days=30),  # Default 30-day expiration
                        storage_key,
                        json.dumps(result.metadata.get('tags', [])),
                        json.dumps(result.metadata)
                    )
            else:
                logger.warning(f"Database connection pool not available for result: {result_id}")

            # Clear cache
            self._cache.pop(result_id, None)
            return result_id

        except Exception as e:
            logger.error(f"Failed to save execution result {result_id} for execution {result.execution_id}: {e}", exc_info=True)
            raise DataRepositoryError(f"Save result failed: {e}")

    async def get_result_by_id(self, result_id: str) -> Optional[ExecutionResult]:
        """Get a result by ID with caching."""
        try:
            if not self._initialized:
                await self.initialize()

            # Check cache first
            cache_key = f"result_{result_id}"
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if datetime.utcnow().timestamp() - timestamp < self._cache_ttl:
                    return ExecutionResult(**cached_data)
                else:
                    # Cache expired
                    del self._cache[cache_key]

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    record = await conn.fetchrow(
                        'SELECT file_storage_key FROM execution_results_metadata WHERE result_id = $1',
                        result_id
                    )

                    if record and record['file_storage_key']:
                        result_data = await self.file_storage.retrieve(record['file_storage_key'])
                        if result_data:
                            # Cache the result
                            self._cache[cache_key] = (result_data, datetime.utcnow().timestamp())
                            return ExecutionResult(**result_data)

            return None

        except Exception as e:
            logger.error(f"Failed to get result {result_id}: {e}")
            raise DataRepositoryError(f"Get result failed: {e}")

    async def get_results_by_execution(self, execution_id: str) -> List[ExecutionResult]:
        """Get all results for an execution."""
        try:
            if not self._initialized:
                await self.initialize()

            results = []

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    records = await conn.fetch(
                        '''SELECT result_id, file_storage_key
                           FROM execution_results_metadata
                           WHERE execution_id = $1
                           ORDER BY created_at ASC''',
                        execution_id
                    )

                    # Load results from file storage
                    for record in records:
                        if record['file_storage_key']:
                            result_data = await self.file_storage.retrieve(record['file_storage_key'])
                            if result_data:
                                result = ExecutionResult(**result_data)
                                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to get results for execution {execution_id}: {e}")
            raise DataRepositoryError(f"Get results by execution failed: {e}")

    async def get_results_by_quality(self, min_quality: float, limit: Optional[int] = None) -> List[ExecutionResult]:
        """Get results with quality score above threshold."""
        try:
            if not self._initialized:
                await self.initialize()

            results = []

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    query = '''
                        SELECT result_id, file_storage_key
                        FROM execution_results_metadata
                        WHERE quality_score >= $1
                        ORDER BY quality_score DESC, created_at DESC
                    '''

                    if limit:
                        query += f" LIMIT {limit}"

                    records = await conn.fetch(query, min_quality)

                    # Load results from file storage
                    for record in records:
                        if record['file_storage_key']:
                            result_data = await self.file_storage.retrieve(record['file_storage_key'])
                            if result_data:
                                result = ExecutionResult(**result_data)
                                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to get results by quality: {e}")
            raise DataRepositoryError(f"Get results by quality failed: {e}")

    async def delete_result(self, result_id: str) -> bool:
        """Delete a result."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    # Get storage key
                    record = await conn.fetchrow(
                        'SELECT file_storage_key FROM execution_results_metadata WHERE result_id = $1',
                        result_id
                    )

                    # Delete from database
                    await conn.execute(
                        'DELETE FROM execution_results_metadata WHERE result_id = $1',
                        result_id
                    )

                    # Delete analytics
                    await conn.execute(
                        'DELETE FROM result_analytics WHERE result_id = $1',
                        result_id
                    )

                    # Delete from file storage
                    if record and record['file_storage_key']:
                        await self.file_storage.delete(record['file_storage_key'])

                    # Clear cache
                    cache_key = f"result_{result_id}"
                    self._cache.pop(cache_key, None)

                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete result {result_id}: {e}")
            return False

    async def cleanup_expired_results(self) -> int:
        """Clean up expired results."""
        try:
            if not self._initialized:
                await self.initialize()

            deleted_count = 0

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    # Get expired results
                    records = await conn.fetch(
                        '''SELECT result_id, file_storage_key
                           FROM execution_results_metadata
                           WHERE expires_at < $1''',
                        datetime.utcnow()
                    )

                    for record in records:
                        # Delete from file storage
                        if record['file_storage_key']:
                            await self.file_storage.delete(record['file_storage_key'])

                        # Clear cache
                        cache_key = f"result_{record['result_id']}"
                        self._cache.pop(cache_key, None)

                        deleted_count += 1

                    # Delete from database
                    await conn.execute(
                        'DELETE FROM execution_results_metadata WHERE expires_at < $1',
                        datetime.utcnow()
                    )

                    # Delete related analytics
                    await conn.execute(
                        '''DELETE FROM result_analytics
                           WHERE result_id NOT IN (
                               SELECT result_id FROM execution_results_metadata
                           )'''
                    )

            logger.info(f"Cleaned up {deleted_count} expired results")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired results: {e}")
            raise DataRepositoryError(f"Cleanup failed: {e}")

    async def get_result_analytics(self, result_id: str) -> Dict[str, Any]:
        """Get analytics for a result."""
        try:
            if not self._initialized:
                await self.initialize()

            analytics = {}

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    records = await conn.fetch(
                        '''SELECT metric_name, metric_value, metric_type, recorded_at, metadata
                           FROM result_analytics
                           WHERE result_id = $1
                           ORDER BY recorded_at DESC''',
                        result_id
                    )

                    for record in records:
                        metric_name = record['metric_name']
                        if metric_name not in analytics:
                            analytics[metric_name] = []

                        analytics[metric_name].append({
                            'value': record['metric_value'],
                            'type': record['metric_type'],
                            'recorded_at': record['recorded_at'],
                            'metadata': json.loads(record['metadata']) if record['metadata'] else {}
                        })

            return analytics

        except Exception as e:
            logger.error(f"Failed to get analytics for result {result_id}: {e}")
            raise DataRepositoryError(f"Get analytics failed: {e}")

    async def record_result_analytics(self, result_id: str, metric_name: str, metric_value: float,
                                    metric_type: str = "gauge", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record analytics for a result."""
        try:
            if not self._initialized:
                await self.initialize()

            analytics_id = str(uuid.uuid4())

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO result_analytics
                        (analytics_id, result_id, metric_name, metric_value, metric_type, recorded_at, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ''',
                        analytics_id,
                        result_id,
                        metric_name,
                        metric_value,
                        metric_type,
                        datetime.utcnow(),
                        json.dumps(metadata or {})
                    )

            return analytics_id

        except Exception as e:
            logger.error(f"Failed to record analytics: {e}")
            raise DataRepositoryError(f"Record analytics failed: {e}")

    async def find_results(self, criteria: Dict[str, Any], limit: Optional[int] = None) -> List[ExecutionResult]:
        """Find results matching criteria."""
        try:
            results = []

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    where_clauses, values = self._build_where_clause(criteria)
                    query = f"SELECT result_id, file_storage_key FROM execution_results_metadata {where_clauses} ORDER BY created_at DESC"

                    if limit:
                        query += f" LIMIT {limit}"

                    records = await conn.fetch(query, *values)

                    # Load results from file storage
                    for record in records:
                        if record['file_storage_key']:
                            result_data = await self.file_storage.retrieve(record['file_storage_key'])
                            if result_data:
                                result = ExecutionResult(**result_data)
                                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to find results: {e}")
            raise DataRepositoryError(f"Find results failed: {e}")

    def _build_where_clause(self, criteria: Dict[str, Any]) -> tuple:
        """Build WHERE clause from criteria."""
        where_clauses = []
        values = []
        param_count = 1

        for key, value in criteria.items():
            if key in ['execution_id', 'step_id', 'task_type', 'status', 'result_id']:
                where_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1
            elif key == 'min_quality_score':
                where_clauses.append(f"quality_score >= ${param_count}")
                values.append(value)
                param_count += 1
            elif key == 'max_quality_score':
                where_clauses.append(f"quality_score <= ${param_count}")
                values.append(value)
                param_count += 1
            elif key == 'min_confidence_score':
                where_clauses.append(f"confidence_score >= ${param_count}")
                values.append(value)
                param_count += 1
            elif key == 'created_after':
                where_clauses.append(f"created_at > ${param_count}")
                values.append(value)
                param_count += 1
            elif key == 'created_before':
                where_clauses.append(f"created_at < ${param_count}")
                values.append(value)
                param_count += 1
            elif key == 'has_tag':
                where_clauses.append(f"tags @> ${param_count}")
                values.append(json.dumps([value]))
                param_count += 1

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        return where_clause, values
