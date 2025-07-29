"""
Data Layer Service

Provides a unified interface for data operations in the multi-task service,
integrating with existing summarizer patterns and infrastructure.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid

from ..core.interfaces.data_repository import IDataRepository, ITaskRepository, IResultRepository, IStorageProvider
from ..core.models.execution_models import ExecutionModel, ExecutionResult, ExecutionContext, ExecutionStatus
from ..core.models.data_models import StorageMetadata, StorageConfig, DataRecord
from ..core.exceptions.data_exceptions import DataLayerError, DataRepositoryError, StorageError
from .repositories.task_repository import TaskRepository
from .repositories.result_repository import ResultRepository
from .storage.storage_manager import StorageManager
from .serializers.data_serializer import DataSerializer, DataFormat, CompressionType
from app.infrastructure.persistence.database_manager import DatabaseManager
from app.infrastructure.persistence.redis_client import RedisClient

logger = logging.getLogger(__name__)


class DataLayerService:
    """
    Unified data layer service that provides high-level data operations
    for the multi-task service, compatible with existing summarizer patterns.

    Features:
    - Unified data access interface
    - Automatic storage optimization
    - Integration with existing infrastructure
    - Performance monitoring
    - Data lifecycle management
    """

    def __init__(self,
                 db_manager: DatabaseManager,
                 redis_client: Optional[RedisClient] = None,
                 storage_config: Optional[Dict[str, Any]] = None):
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.storage_config = storage_config or {}

        # Initialize components
        self.storage_manager = StorageManager(db_manager, redis_client, storage_config)
        self.task_repository = TaskRepository(db_manager, storage_config)
        self.result_repository = ResultRepository(db_manager, storage_config)
        self.serializer = DataSerializer()

        self._initialized = False
        self._performance_metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_response_time': 0.0,
            'last_operation_time': None
        }

    async def initialize(self):
        """Initialize the data layer service."""
        if not self._initialized:
            await self.storage_manager.initialize()
            await self.task_repository.initialize()
            await self.result_repository.initialize()
            await self._create_additional_tables()
            self._initialized = True
            logger.info("DataLayerService initialized successfully")

    async def _create_additional_tables(self):
        """Create additional tables for data layer operations."""
        if self.db_manager.connection_pool:
            async with self.db_manager.connection_pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS storage_data (
                        key TEXT PRIMARY KEY,
                        data BYTEA,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_storage_data_expires_at ON storage_data (expires_at);

                    CREATE TABLE IF NOT EXISTS storage_operations (
                        operation_id TEXT PRIMARY KEY,
                        operation_type TEXT,
                        key TEXT,
                        timestamp TIMESTAMP,
                        success BOOLEAN,
                        metadata JSONB
                    );
                    CREATE INDEX IF NOT EXISTS idx_storage_operations_timestamp ON storage_operations (timestamp);
                    CREATE INDEX IF NOT EXISTS idx_storage_operations_type ON storage_operations (operation_type);
                ''')

    # High-level data operations

    async def save_execution_data(self, execution: ExecutionModel,
                                context: Optional[ExecutionContext] = None) -> str:
        """
        Save execution data using optimized storage strategy.
        Compatible with existing summarizer patterns.
        """
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            # Save execution using task repository
            execution_id = await self.task_repository.save_task_execution(execution)

            # Update performance metrics
            await self._update_metrics(start_time, True)

            logger.debug(f"Saved execution data: {execution_id}")
            return execution_id

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to save execution data: {e}")
            raise DataLayerError(f"Save execution failed: {e}")

    async def save_result_data(self, result: ExecutionResult,
                             context: ExecutionContext) -> str:
        """
        Save result data using optimized storage strategy.
        """
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            # Save result using result repository
            result_id = await self.result_repository.save_result(result, context)

            # Record analytics if available
            if result.quality_score is not None:
                await self.result_repository.record_result_analytics(
                    result_id, "quality_score", result.quality_score, "gauge"
                )

            if result.confidence_score is not None:
                await self.result_repository.record_result_analytics(
                    result_id, "confidence_score", result.confidence_score, "gauge"
                )

            # Update performance metrics
            await self._update_metrics(start_time, True)

            logger.debug(f"Saved result data: {result_id}")
            return result_id

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to save result data: {e}")
            raise DataLayerError(f"Save result failed: {e}")

    async def get_execution_data(self, execution_id: str) -> Optional[ExecutionModel]:
        """Get execution data by ID."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            execution = await self.task_repository.get_execution_by_id(execution_id)

            await self._update_metrics(start_time, True)
            return execution

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to get execution data: {e}")
            raise DataLayerError(f"Get execution failed: {e}")

    async def get_result_data(self, result_id: str) -> Optional[ExecutionResult]:
        """Get result data by ID."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            result = await self.result_repository.get_result_by_id(result_id)

            await self._update_metrics(start_time, True)
            return result

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to get result data: {e}")
            raise DataLayerError(f"Get result failed: {e}")

    async def get_task_execution_history(self, task_id: str,
                                       user_id: Optional[str] = None) -> List[ExecutionResult]:
        """
        Get execution history for a task.
        Compatible with summarizer's history tracking.
        """
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            history = await self.task_repository.get_task_history(task_id, user_id)

            await self._update_metrics(start_time, True)
            return history

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to get task history: {e}")
            raise DataLayerError(f"Get task history failed: {e}")

    async def get_active_executions(self, user_id: Optional[str] = None) -> List[ExecutionModel]:
        """Get currently active executions."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            executions = await self.task_repository.get_active_executions(user_id)

            await self._update_metrics(start_time, True)
            return executions

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to get active executions: {e}")
            raise DataLayerError(f"Get active executions failed: {e}")

    async def update_execution_status(self, execution_id: str, status: ExecutionStatus,
                                    result: Optional[ExecutionResult] = None) -> bool:
        """Update execution status and optionally add result."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            success = await self.task_repository.update_execution_status(
                execution_id, status.value, result
            )

            await self._update_metrics(start_time, True)
            return success

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to update execution status: {e}")
            raise DataLayerError(f"Update execution status failed: {e}")

    # Summarizer-compatible methods

    async def store_summarizer_data(self, key: str, data: Any,
                                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data using the same patterns as the existing summarizer.
        Provides backward compatibility.
        """
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            # Create storage metadata
            storage_metadata = StorageMetadata(
                key=key,
                created_at=datetime.utcnow(),
                metadata=metadata or {},
                format=DataFormat.JSON,
                compression=CompressionType.GZIP if len(str(data)) > 1024 else CompressionType.NONE
            )

            success = await self.storage_manager.store(key, data, storage_metadata)

            await self._update_metrics(start_time, True)
            return success

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to store summarizer data: {e}")
            raise DataLayerError(f"Store summarizer data failed: {e}")

    async def retrieve_summarizer_data(self, key: str) -> Optional[Any]:
        """
        Retrieve data using the same patterns as the existing summarizer.
        Provides backward compatibility.
        """
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            data = await self.storage_manager.retrieve(key)

            await self._update_metrics(start_time, True)
            return data

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to retrieve summarizer data: {e}")
            raise DataLayerError(f"Retrieve summarizer data failed: {e}")

    async def delete_summarizer_data(self, key: str) -> bool:
        """Delete data using summarizer patterns."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            success = await self.storage_manager.delete(key)

            await self._update_metrics(start_time, True)
            return success

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to delete summarizer data: {e}")
            raise DataLayerError(f"Delete summarizer data failed: {e}")

    # Search and analytics methods

    async def search_executions(self, criteria: Dict[str, Any],
                              limit: Optional[int] = None) -> List[ExecutionModel]:
        """Search executions by criteria."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            executions = await self.task_repository.find(criteria, "execution", limit)

            await self._update_metrics(start_time, True)
            return executions

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to search executions: {e}")
            raise DataLayerError(f"Search executions failed: {e}")

    async def search_results(self, criteria: Dict[str, Any],
                           limit: Optional[int] = None) -> List[ExecutionResult]:
        """Search results by criteria."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            results = await self.result_repository.find(criteria, "result", limit)

            await self._update_metrics(start_time, True)
            return results

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to search results: {e}")
            raise DataLayerError(f"Search results failed: {e}")

    async def get_quality_results(self, min_quality: float,
                                limit: Optional[int] = None) -> List[ExecutionResult]:
        """Get results with quality score above threshold."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            results = await self.result_repository.get_results_by_quality(min_quality, limit)

            await self._update_metrics(start_time, True)
            return results

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to get quality results: {e}")
            raise DataLayerError(f"Get quality results failed: {e}")

    async def get_result_analytics(self, result_id: str) -> Dict[str, Any]:
        """Get analytics for a specific result."""
        try:
            start_time = datetime.utcnow()

            if not self._initialized:
                await self.initialize()

            analytics = await self.result_repository.get_result_analytics(result_id)

            await self._update_metrics(start_time, True)
            return analytics

        except Exception as e:
            await self._update_metrics(start_time, False)
            logger.error(f"Failed to get result analytics: {e}")
            raise DataLayerError(f"Get result analytics failed: {e}")

    # Maintenance and optimization

    async def optimize_storage(self) -> Dict[str, Any]:
        """Optimize storage by cleaning up old data."""
        try:
            if not self._initialized:
                await self.initialize()

            return await self.storage_manager.optimize_storage()

        except Exception as e:
            logger.error(f"Storage optimization failed: {e}")
            raise DataLayerError(f"Storage optimization failed: {e}")

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get data layer performance metrics."""
        try:
            storage_metrics = await self.storage_manager.get_storage_metrics()

            return {
                'data_layer': self._performance_metrics,
                'storage': storage_metrics
            }

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on data layer components."""
        try:
            health = {
                'status': 'healthy',
                'components': {},
                'timestamp': datetime.utcnow().isoformat()
            }

            # Check database connection
            try:
                if self.db_manager.connection_pool:
                    async with self.db_manager.connection_pool.acquire() as conn:
                        await conn.fetchval('SELECT 1')
                    health['components']['database'] = 'healthy'
                else:
                    health['components']['database'] = 'unavailable'
            except Exception as e:
                health['components']['database'] = f'unhealthy: {e}'
                health['status'] = 'degraded'

            # Check Redis connection
            try:
                if self.redis_client:
                    await self.redis_client.ping()
                    health['components']['redis'] = 'healthy'
                else:
                    health['components']['redis'] = 'unavailable'
            except Exception as e:
                health['components']['redis'] = f'unhealthy: {e}'
                health['status'] = 'degraded'

            # Check file storage
            try:
                test_key = f"health_check_{uuid.uuid4()}"
                await self.storage_manager.file_storage.store(test_key, b"test")
                await self.storage_manager.file_storage.delete(test_key)
                health['components']['file_storage'] = 'healthy'
            except Exception as e:
                health['components']['file_storage'] = f'unhealthy: {e}'
                health['status'] = 'degraded'

            return health

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    # Private helper methods

    async def _update_metrics(self, start_time: datetime, success: bool):
        """Update performance metrics."""
        try:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()

            self._performance_metrics['total_operations'] += 1
            if success:
                self._performance_metrics['successful_operations'] += 1
            else:
                self._performance_metrics['failed_operations'] += 1

            # Update average response time
            total_ops = self._performance_metrics['total_operations']
            current_avg = self._performance_metrics['average_response_time']
            self._performance_metrics['average_response_time'] = (
                (current_avg * (total_ops - 1) + response_time) / total_ops
            )

            self._performance_metrics['last_operation_time'] = end_time.isoformat()

        except Exception as e:
            logger.warning(f"Failed to update metrics: {e}")


# Factory function
def create_data_layer_service(db_manager: DatabaseManager,
                            redis_client: Optional[RedisClient] = None,
                            storage_config: Optional[Dict[str, Any]] = None) -> DataLayerService:
    """Create a data layer service with the specified configuration."""
    return DataLayerService(db_manager, redis_client, storage_config)
