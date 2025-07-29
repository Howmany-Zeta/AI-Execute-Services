"""
Task Repository Implementation

Implements task-specific data repository operations for the multi-task service.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from ...core.interfaces.data_repository import ITaskRepository
from ...core.models.execution_models import ExecutionModel, ExecutionResult, ExecutionContext, ExecutionStatus
from ...core.exceptions.data_exceptions import DataRepositoryError, DataNotFoundError
from app.infrastructure.persistence.file_storage import get_file_storage
from app.infrastructure.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class TaskRepository(ITaskRepository):
    """
    Task repository implementation using hybrid storage (database + file storage).

    Strategy:
    - Metadata and indexes stored in database for fast queries
    - Large execution data stored in file storage
    - Results cached for performance
    """

    def __init__(self, db_manager: DatabaseManager, storage_config: Optional[Dict[str, Any]] = None):
        self.db_manager = db_manager
        self.file_storage = get_file_storage(storage_config)
        self._initialized = False

    async def initialize(self):
        """Initialize the repository."""
        if not self._initialized:
            await self.file_storage.initialize()
            await self._create_tables()
            self._initialized = True
            logger.info("TaskRepository initialized successfully")

    async def _create_tables(self):
        """Create database tables for task metadata."""
        if not self.db_manager._initialized:
            await self.db_manager.init_database_schema()

        # Create additional tables for task repository
        if self.db_manager.connection_pool:
            async with self.db_manager.connection_pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS task_executions (
                        execution_id TEXT PRIMARY KEY,
                        task_id TEXT,
                        user_id TEXT,
                        session_id TEXT,
                        execution_type TEXT,
                        status TEXT,
                        progress REAL DEFAULT 0.0,
                        created_at TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        file_storage_key TEXT,
                        metadata JSONB
                    );
                    CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON task_executions (task_id);
                    CREATE INDEX IF NOT EXISTS idx_task_executions_user_id ON task_executions (user_id);
                    CREATE INDEX IF NOT EXISTS idx_task_executions_status ON task_executions (status);
                    CREATE INDEX IF NOT EXISTS idx_task_executions_created_at ON task_executions (created_at);

                    CREATE TABLE IF NOT EXISTS execution_results (
                        result_id TEXT PRIMARY KEY,
                        execution_id TEXT,
                        step_id TEXT,
                        status TEXT,
                        quality_score REAL,
                        confidence_score REAL,
                        created_at TIMESTAMP,
                        file_storage_key TEXT,
                        metadata JSONB
                    );
                    CREATE INDEX IF NOT EXISTS idx_execution_results_execution_id ON execution_results (execution_id);
                    CREATE INDEX IF NOT EXISTS idx_execution_results_quality_score ON execution_results (quality_score);
                    CREATE INDEX IF NOT EXISTS idx_execution_results_created_at ON execution_results (created_at);
                ''')

    # IDataRepository implementation

    async def save(self, entity: Any, context: Optional[ExecutionContext] = None) -> str:
        """Save an entity to the repository."""
        if isinstance(entity, ExecutionModel):
            return await self.save_task_execution(entity)
        elif isinstance(entity, ExecutionResult):
            if not context:
                raise DataRepositoryError("ExecutionContext required for saving ExecutionResult")
            return await self.save_execution_result(entity, context)
        else:
            raise DataRepositoryError(f"Unsupported entity type: {type(entity)}")

    async def get_by_id(self, entity_id: str, entity_type: str) -> Optional[Any]:
        """Retrieve an entity by its unique identifier."""
        if entity_type == "execution":
            return await self.get_execution_by_id(entity_id)
        elif entity_type == "result":
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
                    # Check if it's an execution or result
                    execution_record = await conn.fetchrow(
                        'SELECT execution_id FROM task_executions WHERE execution_id = $1',
                        entity_id
                    )

                    if execution_record:
                        # Update execution
                        set_clauses = []
                        values = []
                        param_count = 1

                        for key, value in updates.items():
                            if key in ['status', 'progress', 'completed_at', 'metadata']:
                                set_clauses.append(f"{key} = ${param_count}")
                                values.append(value if key != 'metadata' else json.dumps(value))
                                param_count += 1

                        if set_clauses:
                            values.append(entity_id)
                            query = f"UPDATE task_executions SET {', '.join(set_clauses)} WHERE execution_id = ${param_count}"
                            await conn.execute(query, *values)
                            return True
                    else:
                        # Check if it's a result
                        result_record = await conn.fetchrow(
                            'SELECT result_id FROM execution_results WHERE result_id = $1',
                            entity_id
                        )

                        if result_record:
                            # Update result
                            set_clauses = []
                            values = []
                            param_count = 1

                            for key, value in updates.items():
                                if key in ['status', 'quality_score', 'confidence_score', 'metadata']:
                                    set_clauses.append(f"{key} = ${param_count}")
                                    values.append(value if key != 'metadata' else json.dumps(value))
                                    param_count += 1

                            if set_clauses:
                                values.append(entity_id)
                                query = f"UPDATE execution_results SET {', '.join(set_clauses)} WHERE result_id = ${param_count}"
                                await conn.execute(query, *values)
                                return True

            return False

        except Exception as e:
            logger.error(f"Failed to update entity {entity_id}: {e}")
            raise DataRepositoryError(f"Update failed: {e}")

    async def delete(self, entity_id: str, entity_type: str) -> bool:
        """Delete an entity from the repository."""
        try:
            if not self._initialized:
                await self.initialize()

            if entity_type == "execution":
                return await self.delete_execution(entity_id)
            elif entity_type == "result":
                return await self.delete_result(entity_id)
            else:
                raise DataRepositoryError(f"Unsupported entity type: {entity_type}")

        except Exception as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            raise DataRepositoryError(f"Deletion failed: {e}")

    async def find(self, criteria: Dict[str, Any], entity_type: str, limit: Optional[int] = None) -> List[Any]:
        """Find entities matching the given criteria."""
        try:
            if not self._initialized:
                await self.initialize()

            if entity_type == "execution":
                return await self.find_executions(criteria, limit)
            elif entity_type == "result":
                return await self.find_results(criteria, limit)
            else:
                raise DataRepositoryError(f"Unsupported entity type: {entity_type}")

        except Exception as e:
            logger.error(f"Failed to find entities: {e}")
            raise DataRepositoryError(f"Find operation failed: {e}")

    async def count(self, criteria: Dict[str, Any], entity_type: str) -> int:
        """Count entities matching the given criteria."""
        try:
            if not self._initialized:
                await self.initialize()

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    if entity_type == "execution":
                        where_clauses, values = self._build_where_clause(criteria)
                        query = f"SELECT COUNT(*) FROM task_executions {where_clauses}"
                        result = await conn.fetchval(query, *values)
                        return result
                    elif entity_type == "result":
                        where_clauses, values = self._build_where_clause(criteria, table="execution_results")
                        query = f"SELECT COUNT(*) FROM execution_results {where_clauses}"
                        result = await conn.fetchval(query, *values)
                        return result

            return 0

        except Exception as e:
            logger.error(f"Failed to count entities: {e}")
            raise DataRepositoryError(f"Count operation failed: {e}")

    # ITaskRepository implementation

    async def save_task_execution(self, execution: ExecutionModel) -> str:
        """Save a task execution record."""
        try:
            if not self._initialized:
                await self.initialize()

            status_value = execution.status.value if hasattr(execution.status, 'value') else execution.status

            # Store execution data in file storage
            storage_key = f"executions/{execution.execution_id}.json"
            execution_data = execution.dict()

            await self.file_storage.store(storage_key, execution_data)

            # Store metadata in database
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO task_executions
                        (execution_id, task_id, user_id, session_id, execution_type, status, progress,
                         created_at, started_at, completed_at, file_storage_key, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (execution_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        progress = EXCLUDED.progress,
                        completed_at = EXCLUDED.completed_at,
                        metadata = EXCLUDED.metadata
                    ''',
                        execution.execution_id,
                        execution.context.task_id,
                        execution.context.user_id,
                        execution.context.session_id,
                        execution.execution_type,
                        status_value,
                        execution.progress,
                        execution.created_at,
                        execution.started_at,
                        execution.completed_at,
                        storage_key,
                        json.dumps(execution.metadata)
                    )
            else:
                logger.warning(f"Database connection pool not available for execution: {execution.execution_id}")
            return execution.execution_id

        except Exception as e:
            logger.error(f"Failed to save task execution {execution.execution_id}: {e}", exc_info=True)
            raise DataRepositoryError(f"Save execution failed: {e}")

    async def get_task_history(self, task_id: str, user_id: Optional[str] = None) -> List[ExecutionResult]:
        """Get the execution history for a task."""
        try:
            if not self._initialized:
                await self.initialize()

            results = []

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    # Build query
                    query = '''
                        SELECT er.result_id, er.execution_id, er.file_storage_key
                        FROM execution_results er
                        JOIN task_executions te ON er.execution_id = te.execution_id
                        WHERE te.task_id = $1
                    '''
                    params = [task_id]

                    if user_id:
                        query += ' AND te.user_id = $2'
                        params.append(user_id)

                    query += ' ORDER BY er.created_at ASC'

                    records = await conn.fetch(query, *params)

                    # Load results from file storage
                    for record in records:
                        if record['file_storage_key']:
                            result_data = await self.file_storage.retrieve(record['file_storage_key'])
                            if result_data:
                                result = ExecutionResult(**result_data)
                                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to get task history for {task_id}: {e}")
            raise DataRepositoryError(f"Get task history failed: {e}")

    async def get_active_executions(self, user_id: Optional[str] = None) -> List[ExecutionModel]:
        """Get currently active executions."""
        try:
            if not self._initialized:
                await self.initialize()

            executions = []

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    query = '''
                        SELECT execution_id, file_storage_key
                        FROM task_executions
                        WHERE status IN ('pending', 'running')
                    '''
                    params = []

                    if user_id:
                        query += ' AND user_id = $1'
                        params.append(user_id)

                    query += ' ORDER BY created_at DESC'

                    records = await conn.fetch(query, *params)

                    # Load executions from file storage
                    for record in records:
                        if record['file_storage_key']:
                            execution_data = await self.file_storage.retrieve(record['file_storage_key'])
                            if execution_data:
                                execution = ExecutionModel(**execution_data)
                                executions.append(execution)

            return executions

        except Exception as e:
            logger.error(f"Failed to get active executions: {e}")
            raise DataRepositoryError(f"Get active executions failed: {e}")

    async def update_execution_status(self, execution_id: str, status: str, result: Optional[ExecutionResult] = None) -> bool:
        """Update the status of an execution."""
        try:
            updates = {
                'status': status,
                'completed_at': datetime.utcnow() if status in ['completed', 'failed', 'cancelled'] else None
            }

            if result:
                # Save the result
                await self.save_execution_result(result, ExecutionContext(
                    execution_id=execution_id,
                    user_id="system",  # Will be updated with actual context
                ))

            return await self.update(execution_id, updates)

        except Exception as e:
            logger.error(f"Failed to update execution status: {e}")
            raise DataRepositoryError(f"Update execution status failed: {e}")

    # Helper methods

    async def save_execution_result(self, result: ExecutionResult, context: ExecutionContext) -> str:
        """Save an execution result."""
        try:
            if not self._initialized:
                await self.initialize()

            result_id = str(uuid.uuid4())

            status_value = result.status.value if hasattr(result.status, 'value') else result.status

            # Store result data in file storage
            storage_key = f"results/{result_id}.json"
            result_data = result.dict()

            await self.file_storage.store(storage_key, result_data)

            # Store metadata in database
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO execution_results
                        (result_id, execution_id, step_id, status, quality_score, confidence_score,
                         created_at, file_storage_key, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ''',
                        result_id,
                        result.execution_id,
                        result.step_id,
                        status_value,
                        result.quality_score,
                        result.confidence_score,
                        datetime.utcnow(),
                        storage_key,
                        json.dumps(result.metadata)
                    )
            else:
                logger.warning(f"Database connection pool not available for result: {result_id}")
            return result_id

        except Exception as e:
            logger.error(f"Failed to save execution result for execution {result.execution_id}: {e}", exc_info=True)
            raise DataRepositoryError(f"Save execution result failed: {e}")

    async def get_execution_by_id(self, execution_id: str) -> Optional[ExecutionModel]:
        """Get an execution by ID."""
        try:
            if not self._initialized:
                await self.initialize()

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    record = await conn.fetchrow(
                        'SELECT file_storage_key FROM task_executions WHERE execution_id = $1',
                        execution_id
                    )

                    if record and record['file_storage_key']:
                        execution_data = await self.file_storage.retrieve(record['file_storage_key'])
                        if execution_data:
                            return ExecutionModel(**execution_data)

            return None

        except Exception as e:
            logger.error(f"Failed to get execution {execution_id}: {e}")
            raise DataRepositoryError(f"Get execution failed: {e}")

    async def get_result_by_id(self, result_id: str) -> Optional[ExecutionResult]:
        """Get a result by ID."""
        try:
            if not self._initialized:
                await self.initialize()

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    record = await conn.fetchrow(
                        'SELECT file_storage_key FROM execution_results WHERE result_id = $1',
                        result_id
                    )

                    if record and record['file_storage_key']:
                        result_data = await self.file_storage.retrieve(record['file_storage_key'])
                        if result_data:
                            return ExecutionResult(**result_data)

            return None

        except Exception as e:
            logger.error(f"Failed to get result {result_id}: {e}")
            raise DataRepositoryError(f"Get result failed: {e}")

    async def delete_execution(self, execution_id: str) -> bool:
        """Delete an execution."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    # Get storage key
                    record = await conn.fetchrow(
                        'SELECT file_storage_key FROM task_executions WHERE execution_id = $1',
                        execution_id
                    )

                    # Delete from database
                    await conn.execute(
                        'DELETE FROM task_executions WHERE execution_id = $1',
                        execution_id
                    )

                    # Delete from file storage
                    if record and record['file_storage_key']:
                        await self.file_storage.delete(record['file_storage_key'])

                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete execution {execution_id}: {e}")
            return False

    async def delete_result(self, result_id: str) -> bool:
        """Delete a result."""
        try:
            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    # Get storage key
                    record = await conn.fetchrow(
                        'SELECT file_storage_key FROM execution_results WHERE result_id = $1',
                        result_id
                    )

                    # Delete from database
                    await conn.execute(
                        'DELETE FROM execution_results WHERE result_id = $1',
                        result_id
                    )

                    # Delete from file storage
                    if record and record['file_storage_key']:
                        await self.file_storage.delete(record['file_storage_key'])

                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete result {result_id}: {e}")
            return False

    async def find_executions(self, criteria: Dict[str, Any], limit: Optional[int] = None) -> List[ExecutionModel]:
        """Find executions matching criteria."""
        try:
            executions = []

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    where_clauses, values = self._build_where_clause(criteria)
                    query = f"SELECT execution_id, file_storage_key FROM task_executions {where_clauses} ORDER BY created_at DESC"

                    if limit:
                        query += f" LIMIT {limit}"

                    records = await conn.fetch(query, *values)

                    # Load executions from file storage
                    for record in records:
                        if record['file_storage_key']:
                            execution_data = await self.file_storage.retrieve(record['file_storage_key'])
                            if execution_data:
                                execution = ExecutionModel(**execution_data)
                                executions.append(execution)

            return executions

        except Exception as e:
            logger.error(f"Failed to find executions: {e}")
            raise DataRepositoryError(f"Find executions failed: {e}")

    async def find_results(self, criteria: Dict[str, Any], limit: Optional[int] = None) -> List[ExecutionResult]:
        """Find results matching criteria."""
        try:
            results = []

            if self.db_manager.connection_pool:
                async with self.db_manager.connection_pool.acquire() as conn:
                    where_clauses, values = self._build_where_clause(criteria, table="execution_results")
                    query = f"SELECT result_id, file_storage_key FROM execution_results {where_clauses} ORDER BY created_at DESC"

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

    def _build_where_clause(self, criteria: Dict[str, Any], table: str = "task_executions") -> tuple:
        """Build WHERE clause from criteria."""
        where_clauses = []
        values = []
        param_count = 1

        for key, value in criteria.items():
            if key in ['user_id', 'task_id', 'status', 'execution_id', 'execution_type']:
                where_clauses.append(f"{key} = ${param_count}")
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

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        return where_clause, values
