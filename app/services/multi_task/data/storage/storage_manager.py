"""
Storage Manager Implementation

Manages data storage operations for the multi-task service, integrating with
existing infrastructure and providing optimized storage strategies.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import uuid

from ...core.interfaces.data_repository import IStorageProvider
from ...core.models.data_models import StorageMetadata, StorageConfig, DataRecord, StorageOperation, StorageType
from ...core.models.execution_models import ExecutionModel, ExecutionResult, ExecutionContext
from ...core.exceptions.data_exceptions import StorageError, DataNotFoundError
from ..repositories.task_repository import TaskRepository
from ..repositories.result_repository import ResultRepository
from ..serializers.data_serializer import DataSerializer, DataFormat, CompressionType
from app.infrastructure.persistence.file_storage import get_file_storage
from app.infrastructure.persistence.database_manager import DatabaseManager
from app.infrastructure.persistence.redis_client import RedisClient

logger = logging.getLogger(__name__)


class StorageManager(IStorageProvider):
    """
    Unified storage manager that coordinates between different storage backends.

    Features:
    - Multi-tier storage (cache, database, file storage)
    - Automatic data lifecycle management
    - Performance optimization
    - Integration with existing summarizer patterns
    - Backup and recovery
    """

    def __init__(self,
                 db_manager: DatabaseManager,
                 redis_client: Optional[RedisClient] = None,
                 storage_config: Optional[Dict[str, Any]] = None):
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.file_storage = get_file_storage(storage_config)
        self.serializer = DataSerializer()

        # Initialize repositories
        self.task_repository = TaskRepository(db_manager, storage_config)
        self.result_repository = ResultRepository(db_manager, storage_config)

        # Storage configuration
        self.config = StorageConfig(**(storage_config or {}))
        self._initialized = False

        # Performance metrics
        self._metrics = {
            'operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'storage_operations': 0,
            'errors': 0
        }

    async def initialize(self):
        """Initialize the storage manager."""
        if not self._initialized:
            await self.file_storage.initialize()
            await self.task_repository.initialize()
            await self.result_repository.initialize()
            self._initialized = True
            logger.info("StorageManager initialized successfully")

    # IStorageProvider implementation

    async def store(self, key: str, data: Any, metadata: Optional[StorageMetadata] = None) -> bool:
        """Store data with automatic tier selection."""
        try:
            if not self._initialized:
                await self.initialize()

            self._metrics['operations'] += 1

            # Create metadata if not provided
            if not metadata:
                metadata = StorageMetadata(
                    key=key,
                    storage_type=self._determine_storage_type(data),
                    created_at=datetime.utcnow(),
                    size=len(str(data).encode('utf-8'))
                )

            # Serialize data
            serialized_data = self.serializer.serialize_with_metadata(
                data,
                metadata.dict(),
                format_type=metadata.data_format,
                compress=metadata.compression_type
            )

            # Store in appropriate tier based on data characteristics
            success = await self._store_with_strategy(key, serialized_data, metadata)

            if success:
                # Update cache if available
                if self.redis_client and metadata.cache_ttl and metadata.cache_ttl > 0:
                    await self._cache_data(key, serialized_data, metadata.cache_ttl)

                # Record operation
                await self._record_operation(StorageOperation(
                    operation_id=str(uuid.uuid4()),
                    operation_type="store",
                    storage_key=key,
                    storage_type=StorageType.CLOUD_STORAGE,
                    status="completed",
                    success=True,
                    started_at=datetime.utcnow()
                ))

            self._metrics['storage_operations'] += 1
            return success

        except Exception as e:
            self._metrics['errors'] += 1
            logger.error(f"Failed to store data for key {key}: {e}")
            raise StorageError(f"Store operation failed: {e}")

    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data with automatic tier fallback."""
        try:
            if not self._initialized:
                await self.initialize()

            self._metrics['operations'] += 1

            # Try cache first
            if self.redis_client:
                cached_data = await self._get_cached_data(key)
                if cached_data:
                    self._metrics['cache_hits'] += 1
                    data, metadata = self.serializer.deserialize_with_metadata(cached_data)
                    return data
                else:
                    self._metrics['cache_misses'] += 1

            # Try file storage
            file_data = await self.file_storage.retrieve(key)
            if file_data:
                if isinstance(file_data, bytes):
                    data, metadata = self.serializer.deserialize_with_metadata(file_data)
                else:
                    data = file_data

                # Update cache for future requests
                if self.redis_client:
                    serialized = self.serializer.serialize_with_metadata(data, metadata)
                    await self._cache_data(key, serialized, 3600)  # 1 hour default

                return data

            # Try database as last resort
            db_data = await self._retrieve_from_database(key)
            if db_data:
                return db_data

            return None

        except Exception as e:
            self._metrics['errors'] += 1
            logger.error(f"Failed to retrieve data for key {key}: {e}")
            raise StorageError(f"Retrieve operation failed: {e}")

    async def delete(self, key: str) -> bool:
        """Delete data from all storage tiers."""
        try:
            if not self._initialized:
                await self.initialize()

            self._metrics['operations'] += 1
            success = True

            # Delete from cache
            if self.redis_client:
                try:
                    await self.redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Failed to delete from cache: {e}")

            # Delete from file storage
            try:
                await self.file_storage.delete(key)
            except Exception as e:
                logger.warning(f"Failed to delete from file storage: {e}")
                success = False

            # Delete from database
            try:
                await self._delete_from_database(key)
            except Exception as e:
                logger.warning(f"Failed to delete from database: {e}")
                success = False

            # Record operation
            await self._record_operation(StorageOperation(
                operation_id=str(uuid.uuid4()),
                operation_type="delete",
                storage_key=key,
                storage_type=StorageType.CLOUD_STORAGE,
                status="completed" if success else "failed",
                success=success,
                started_at=datetime.utcnow()
            ))

            return success

        except Exception as e:
            self._metrics['errors'] += 1
            logger.error(f"Failed to delete data for key {key}: {e}")
            raise StorageError(f"Delete operation failed: {e}")

    async def exists(self, key: str) -> bool:
        """Check if data exists in any storage tier."""
        try:
            if not self._initialized:
                await self.initialize()

            # Check cache first
            if self.redis_client:
                if await self.redis_client.exists(key):
                    return True

            # Check file storage
            if await self.file_storage.exists(key):
                return True

            # Check database
            return await self._exists_in_database(key)

        except Exception as e:
            logger.error(f"Failed to check existence for key {key}: {e}")
            return False

    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys with optional prefix filter."""
        try:
            if not self._initialized:
                await self.initialize()

            keys = set()

            # Get keys from file storage
            file_keys = await self.file_storage.list_keys(prefix)
            keys.update(file_keys)

            # Get keys from database
            db_keys = await self._list_database_keys(prefix)
            keys.update(db_keys)

            return sorted(list(keys))

        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            raise StorageError(f"List keys operation failed: {e}")

    # Multi-task specific methods

    async def store_execution(self, execution: ExecutionModel) -> str:
        """Store execution data using optimized strategy."""
        try:
            # Use task repository for execution storage
            return await self.task_repository.save_task_execution(execution)

        except Exception as e:
            logger.error(f"Failed to store execution: {e}")
            raise StorageError(f"Store execution failed: {e}")

    async def store_result(self, result: ExecutionResult, context: ExecutionContext) -> str:
        """Store result data using optimized strategy."""
        try:
            # Use result repository for result storage
            return await self.result_repository.save_result(result, context)

        except Exception as e:
            logger.error(f"Failed to store result: {e}")
            raise StorageError(f"Store result failed: {e}")

    async def get_execution_history(self, task_id: str, user_id: Optional[str] = None) -> List[ExecutionResult]:
        """Get execution history for a task."""
        try:
            return await self.task_repository.get_task_history(task_id, user_id)

        except Exception as e:
            logger.error(f"Failed to get execution history: {e}")
            raise StorageError(f"Get execution history failed: {e}")

    async def get_active_executions(self, user_id: Optional[str] = None) -> List[ExecutionModel]:
        """Get currently active executions."""
        try:
            return await self.task_repository.get_active_executions(user_id)

        except Exception as e:
            logger.error(f"Failed to get active executions: {e}")
            raise StorageError(f"Get active executions failed: {e}")

    async def get_results_by_quality(self, min_quality: float, limit: Optional[int] = None) -> List[ExecutionResult]:
        """Get results with quality score above threshold."""
        try:
            return await self.result_repository.get_results_by_quality(min_quality, limit)

        except Exception as e:
            logger.error(f"Failed to get results by quality: {e}")
            raise StorageError(f"Get results by quality failed: {e}")

    # Storage optimization methods

    async def optimize_storage(self) -> Dict[str, Any]:
        """Optimize storage by cleaning up old data and reorganizing."""
        try:
            optimization_results = {
                'cleaned_results': 0,
                'compressed_files': 0,
                'moved_to_archive': 0,
                'errors': []
            }

            # Clean up expired results
            try:
                cleaned_count = await self.result_repository.cleanup_expired_results()
                optimization_results['cleaned_results'] = cleaned_count
            except Exception as e:
                optimization_results['errors'].append(f"Result cleanup failed: {e}")

            # Compress old files
            try:
                compressed_count = await self._compress_old_files()
                optimization_results['compressed_files'] = compressed_count
            except Exception as e:
                optimization_results['errors'].append(f"File compression failed: {e}")

            # Archive old executions
            try:
                archived_count = await self._archive_old_executions()
                optimization_results['moved_to_archive'] = archived_count
            except Exception as e:
                optimization_results['errors'].append(f"Archiving failed: {e}")

            logger.info(f"Storage optimization completed: {optimization_results}")
            return optimization_results

        except Exception as e:
            logger.error(f"Storage optimization failed: {e}")
            raise StorageError(f"Storage optimization failed: {e}")

    async def get_storage_metrics(self) -> Dict[str, Any]:
        """Get storage performance metrics."""
        try:
            # Calculate cache hit ratio
            total_cache_ops = self._metrics['cache_hits'] + self._metrics['cache_misses']
            cache_hit_ratio = self._metrics['cache_hits'] / total_cache_ops if total_cache_ops > 0 else 0

            # Get storage usage
            storage_usage = await self._get_storage_usage()

            return {
                'operations': self._metrics['operations'],
                'cache_hit_ratio': cache_hit_ratio,
                'cache_hits': self._metrics['cache_hits'],
                'cache_misses': self._metrics['cache_misses'],
                'storage_operations': self._metrics['storage_operations'],
                'errors': self._metrics['errors'],
                'storage_usage': storage_usage
            }

        except Exception as e:
            logger.error(f"Failed to get storage metrics: {e}")
            return {}

    # Private helper methods

    def _determine_storage_type(self, data: Any) -> StorageType:
        """Determine the best storage type for data."""
        data_size = len(str(data).encode('utf-8'))

        if data_size < 1024:  # < 1KB
            return StorageType.MEMORY
        elif data_size < 1024 * 1024:  # < 1MB
            return StorageType.DATABASE
        else:  # >= 1MB
            return StorageType.FILE_SYSTEM

    async def _store_with_strategy(self, key: str, data: bytes, metadata: StorageMetadata) -> bool:
        """Store data using the appropriate strategy based on metadata."""
        try:
            if metadata.storage_type == StorageType.MEMORY:
                # Store in cache only
                if self.redis_client:
                    return await self._cache_data(key, data, metadata.cache_ttl or 3600)
                else:
                    # Fallback to file storage
                    return await self.file_storage.store(key, data)

            elif metadata.storage_type == StorageType.DATABASE:
                # Store in database with cache
                success = await self._store_in_database(key, data, metadata)
                if success and self.redis_client and metadata.cache_ttl:
                    await self._cache_data(key, data, metadata.cache_ttl)
                return success

            else:  # FILE_SYSTEM
                # Store in file storage
                return await self.file_storage.store(key, data)

        except Exception as e:
            logger.error(f"Storage strategy failed for key {key}: {e}")
            return False

    async def _cache_data(self, key: str, data: bytes, ttl: int) -> bool:
        """Cache data in Redis."""
        try:
            if self.redis_client:
                await self.redis_client.set(key, data, ex=ttl)
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to cache data for key {key}: {e}")
            return False

    async def _get_cached_data(self, key: str) -> Optional[bytes]:
        """Get data from Redis cache."""
        try:
            if self.redis_client:
                return await self.redis_client.get(key)
            return None
        except Exception as e:
            logger.warning(f"Failed to get cached data for key {key}: {e}")
            return None

    async def _store_in_database(self, key: str, data: bytes, metadata: StorageMetadata) -> bool:
        """Store data in database."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO storage_data (key, data, metadata, created_at, expires_at)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (key) DO UPDATE SET
                        data = EXCLUDED.data,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    ''',
                        key,
                        data,
                        metadata.json(),
                        datetime.utcnow(),
                        datetime.utcnow() + timedelta(seconds=metadata.cache_ttl) if metadata.cache_ttl else None
                    )
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to store in database: {e}")
            return False

    async def _retrieve_from_database(self, key: str) -> Optional[Any]:
        """Retrieve data from database."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    record = await conn.fetchrow(
                        'SELECT data FROM storage_data WHERE key = $1 AND (expires_at IS NULL OR expires_at > $2)',
                        key, datetime.utcnow()
                    )
                    if record:
                        data, metadata = self.serializer.deserialize_with_metadata(record['data'])
                        return data
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve from database: {e}")
            return None

    async def _delete_from_database(self, key: str) -> bool:
        """Delete data from database."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    result = await conn.execute('DELETE FROM storage_data WHERE key = $1', key)
                    return result != "DELETE 0"
            return False
        except Exception as e:
            logger.error(f"Failed to delete from database: {e}")
            return False

    async def _exists_in_database(self, key: str) -> bool:
        """Check if data exists in database."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    result = await conn.fetchval(
                        'SELECT 1 FROM storage_data WHERE key = $1 AND (expires_at IS NULL OR expires_at > $2)',
                        key, datetime.utcnow()
                    )
                    return result is not None
            return False
        except Exception as e:
            logger.error(f"Failed to check existence in database: {e}")
            return False

    async def _list_database_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List keys from database."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    if prefix:
                        records = await conn.fetch(
                            'SELECT key FROM storage_data WHERE key LIKE $1 AND (expires_at IS NULL OR expires_at > $2)',
                            f"{prefix}%", datetime.utcnow()
                        )
                    else:
                        records = await conn.fetch(
                            'SELECT key FROM storage_data WHERE expires_at IS NULL OR expires_at > $1',
                            datetime.utcnow()
                        )
                    return [record['key'] for record in records]
            return []
        except Exception as e:
            logger.error(f"Failed to list database keys: {e}")
            return []

    async def _record_operation(self, operation: StorageOperation):
        """Record storage operation for auditing."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO storage_operations
                        (operation_id, operation_type, key, timestamp, success, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    ''',
                        operation.operation_id,
                        operation.operation_type,
                        operation.storage_key,
                        operation.started_at,
                        operation.success,
                        json.dumps({})  # Default empty metadata since StorageOperation doesn't have metadata field
                    )
        except Exception as e:
            logger.warning(f"Failed to record operation: {e}")

    async def _compress_old_files(self) -> int:
        """Compress old files to save space."""
        # Implementation would depend on specific requirements
        return 0

    async def _archive_old_executions(self) -> int:
        """Archive old executions to long-term storage."""
        # Implementation would depend on specific requirements
        return 0

    async def _get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage statistics."""
        try:
            usage = {
                'file_storage': 0,
                'database': 0,
                'cache': 0
            }

            # Get file storage usage
            if hasattr(self.file_storage, 'get_usage'):
                usage['file_storage'] = await self.file_storage.get_usage()

            # Get database usage
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    result = await conn.fetchval(
                        'SELECT pg_total_relation_size(\'storage_data\') + pg_total_relation_size(\'task_executions\') + pg_total_relation_size(\'execution_results_metadata\')'
                    )
                    usage['database'] = result or 0

            # Get cache usage
            if self.redis_client:
                info = await self.redis_client.info('memory')
                usage['cache'] = info.get('used_memory', 0)

            return usage

        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return {}


# Factory function
def create_storage_manager(db_manager: DatabaseManager,
                         redis_client: Optional[RedisClient] = None,
                         storage_config: Optional[Dict[str, Any]] = None) -> StorageManager:
    """Create a storage manager with the specified configuration."""
    return StorageManager(db_manager, redis_client, storage_config)
