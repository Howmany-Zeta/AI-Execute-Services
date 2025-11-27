import asyncpg  # type: ignore[import-untyped]
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from aiecs.domain.execution.model import TaskStatus, TaskStepResult
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Specialized handler for database connections, operations, and task history management
    """

    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        if db_config is None:
            settings = get_settings()
            self.db_config = settings.database_config
        else:
            self.db_config = db_config
        self.connection_pool = None
        self._initialized = False

    async def connect(self, min_size: int = 10, max_size: int = 20):
        """Connect to database and initialize connection pool"""
        if self._initialized:
            logger.info("Database already connected")
            return

        try:
            await self.init_connection_pool(min_size, max_size)
            await self.init_database_schema()
            self._initialized = True
            logger.info("Database connection and schema initialization completed")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def init_connection_pool(self, min_size: int = 10, max_size: int = 20):
        """Initialize database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(**self.db_config, min_size=min_size, max_size=max_size)
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise

    async def _get_connection(self):
        """Get database connection"""
        if self.connection_pool:
            return self.connection_pool.acquire()
        else:
            return asyncpg.connect(**self.db_config)

    async def init_database_schema(self):
        """Initialize database table structure"""
        try:
            if self.connection_pool:
                async with self.connection_pool.acquire() as conn:
                    await self._create_tables(conn)
            else:
                conn = await asyncpg.connect(**self.db_config)
                try:
                    await self._create_tables(conn)
                finally:
                    await conn.close()

            self._initialized = True
            logger.info("Database schema initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return False

    async def _create_tables(self, conn):
        """Create database tables"""
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_history (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                result JSONB NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE INDEX IF NOT EXISTS idx_task_history_user_id ON task_history (user_id);
            CREATE INDEX IF NOT EXISTS idx_task_history_task_id ON task_history (task_id);
            CREATE INDEX IF NOT EXISTS idx_task_history_status ON task_history (status);
            CREATE INDEX IF NOT EXISTS idx_task_history_timestamp ON task_history (timestamp);
        """
        )

    async def save_task_history(
        self,
        user_id: str,
        task_id: str,
        step: int,
        step_result: TaskStepResult,
    ):
        """Save task execution history"""
        if not self._initialized:
            await self.init_database_schema()

        try:
            if self.connection_pool:
                async with self.connection_pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO task_history (user_id, task_id, step, result, timestamp, status) VALUES ($1, $2, $3, $4, $5, $6)",
                        user_id,
                        task_id,
                        step,
                        json.dumps(step_result.dict()),
                        datetime.now(),
                        step_result.status,
                    )
            else:
                conn = await asyncpg.connect(**self.db_config)
                try:
                    await conn.execute(
                        "INSERT INTO task_history (user_id, task_id, step, result, timestamp, status) VALUES ($1, $2, $3, $4, $5, $6)",
                        user_id,
                        task_id,
                        step,
                        json.dumps(step_result.dict()),
                        datetime.now(),
                        step_result.status,
                    )
                finally:
                    await conn.close()

            logger.debug(f"Saved task history for user {user_id}, task {task_id}, step {step}")
            return True
        except Exception as e:
            logger.error(f"Database error saving task history: {e}")
            raise Exception(f"Database error: {e}")

    async def load_task_history(self, user_id: str, task_id: str) -> List[Dict]:
        """Load task execution history"""
        if not self._initialized:
            await self.init_database_schema()

        try:
            if self.connection_pool:
                async with self.connection_pool.acquire() as conn:
                    records = await conn.fetch(
                        "SELECT step, result, timestamp, status FROM task_history WHERE user_id = $1 AND task_id = $2 ORDER BY step ASC",
                        user_id,
                        task_id,
                    )
            else:
                conn = await asyncpg.connect(**self.db_config)
                try:
                    records = await conn.fetch(
                        "SELECT step, result, timestamp, status FROM task_history WHERE user_id = $1 AND task_id = $2 ORDER BY step ASC",
                        user_id,
                        task_id,
                    )
                finally:
                    await conn.close()

            return [
                {
                    "step": r["step"],
                    "result": json.loads(r["result"]),
                    "timestamp": r["timestamp"].isoformat(),
                    "status": r["status"],
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"Database error loading task history: {e}")
            raise Exception(f"Database error: {e}")

    async def mark_task_as_cancelled(self, user_id: str, task_id: str):
        """Mark task as cancelled"""
        if not self._initialized:
            await self.init_database_schema()

        try:
            if self.connection_pool:
                async with self.connection_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE task_history SET status = $1 WHERE user_id = $2 AND task_id = $3",
                        TaskStatus.CANCELLED.value,
                        user_id,
                        task_id,
                    )
            else:
                conn = await asyncpg.connect(**self.db_config)
                try:
                    await conn.execute(
                        "UPDATE task_history SET status = $1 WHERE user_id = $2 AND task_id = $3",
                        TaskStatus.CANCELLED.value,
                        user_id,
                        task_id,
                    )
                finally:
                    await conn.close()

            logger.info(f"Marked task {task_id} as cancelled for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Database error marking task as cancelled: {e}")
            raise Exception(f"Database error: {e}")

    async def check_task_status(self, user_id: str, task_id: str) -> TaskStatus:
        """Check task status"""
        if not self._initialized:
            await self.init_database_schema()

        try:
            if self.connection_pool:
                async with self.connection_pool.acquire() as conn:
                    record = await conn.fetchrow(
                        "SELECT status FROM task_history WHERE user_id = $1 AND task_id = $2 ORDER BY step DESC LIMIT 1",
                        user_id,
                        task_id,
                    )
            else:
                conn = await asyncpg.connect(**self.db_config)
                try:
                    record = await conn.fetchrow(
                        "SELECT status FROM task_history WHERE user_id = $1 AND task_id = $2 ORDER BY step DESC LIMIT 1",
                        user_id,
                        task_id,
                    )
                finally:
                    await conn.close()

            return TaskStatus(record["status"]) if record else TaskStatus.PENDING
        except Exception as e:
            logger.error(f"Database error checking task status: {e}")
            raise Exception(f"Database error: {e}")

    async def get_user_tasks(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get user task list"""
        if not self._initialized:
            await self.init_database_schema()

        try:
            if self.connection_pool:
                async with self.connection_pool.acquire() as conn:
                    records = await conn.fetch(
                        """SELECT DISTINCT task_id,
                           MAX(timestamp) as last_updated,
                           (SELECT status FROM task_history th2
                            WHERE th2.user_id = $1 AND th2.task_id = th1.task_id
                            ORDER BY step DESC LIMIT 1) as status
                           FROM task_history th1
                           WHERE user_id = $1
                           GROUP BY task_id
                           ORDER BY last_updated DESC
                           LIMIT $2""",
                        user_id,
                        limit,
                    )
            else:
                conn = await asyncpg.connect(**self.db_config)
                try:
                    records = await conn.fetch(
                        """SELECT DISTINCT task_id,
                           MAX(timestamp) as last_updated,
                           (SELECT status FROM task_history th2
                            WHERE th2.user_id = $1 AND th2.task_id = th1.task_id
                            ORDER BY step DESC LIMIT 1) as status
                           FROM task_history th1
                           WHERE user_id = $1
                           GROUP BY task_id
                           ORDER BY last_updated DESC
                           LIMIT $2""",
                        user_id,
                        limit,
                    )
                finally:
                    await conn.close()

            return [
                {
                    "task_id": r["task_id"],
                    "last_updated": r["last_updated"].isoformat(),
                    "status": r["status"],
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"Database error getting user tasks: {e}")
            raise Exception(f"Database error: {e}")

    async def cleanup_old_tasks(self, days_old: int = 30):
        """Clean up old task records"""
        if not self._initialized:
            await self.init_database_schema()

        try:
            if self.connection_pool:
                async with self.connection_pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM task_history WHERE timestamp < NOW() - INTERVAL %s DAY",
                        days_old,
                    )
            else:
                conn = await asyncpg.connect(**self.db_config)
                try:
                    result = await conn.execute(
                        "DELETE FROM task_history WHERE timestamp < NOW() - INTERVAL %s DAY",
                        days_old,
                    )
                finally:
                    await conn.close()

            logger.info(f"Cleaned up old task records: {result}")
            return True
        except Exception as e:
            logger.error(f"Database error during cleanup: {e}")
            return False

    async def disconnect(self):
        """Disconnect from database and close connection pool"""
        await self.close()
        self._initialized = False
        logger.info("Database disconnected")

    async def close(self):
        """Close database connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database connection pool closed")
