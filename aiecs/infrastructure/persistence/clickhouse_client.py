"""
ClickHouse client for permanent storage of context data.

Provides async wrapper around clickhouse-connect for non-blocking writes.
Used by ClickHousePermanentBackend in dual-write architecture with Redis.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import clickhouse_connect

    CLICKHOUSE_AVAILABLE = True
except ImportError:
    clickhouse_connect = None  # type: ignore[assignment]
    CLICKHOUSE_AVAILABLE = False


class ClickHouseClient:
    """
    Async-friendly ClickHouse client wrapper.

    Uses asyncio.to_thread() for non-blocking sync operations.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "default",
    ) -> None:
        self._client: Any = None
        self._host = host or os.getenv("CLICKHOUSE_HOST", "localhost")
        self._port = port or int(os.getenv("CLICKHOUSE_PORT", "8123"))
        self._username = username or os.getenv("CLICKHOUSE_USER", "default")
        self._password = password or os.getenv("CLICKHOUSE_PASSWORD", "")
        self._database = database or os.getenv("CLICKHOUSE_DATABASE", "default")

    async def initialize(self) -> bool:
        """Initialize ClickHouse connection."""
        if not CLICKHOUSE_AVAILABLE:
            logger.warning("clickhouse-connect not installed, permanent storage disabled")
            return False

        try:
            self._client = await asyncio.to_thread(
                clickhouse_connect.get_client,
                host=self._host,
                port=self._port,
                username=self._username,
                password=self._password if self._password else None,
                database=self._database,
            )
            # Test connection
            await asyncio.to_thread(self._client.command, "SELECT 1")
            logger.info(
                f"ClickHouse client initialized: {self._host}:{self._port}/{self._database}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            self._client = None
            return False

    async def close(self) -> None:
        """Close ClickHouse connection."""
        if self._client:
            try:
                await asyncio.to_thread(self._client.close)
            except Exception as e:
                logger.warning(f"Error closing ClickHouse client: {e}")
            self._client = None
            logger.info("ClickHouse client closed")

    async def insert(
        self,
        table: str,
        data: List[Dict[str, Any]],
        column_names: Optional[List[str]] = None,
    ) -> bool:
        """
        Insert rows into table. Runs in thread pool to avoid blocking.

        Args:
            table: Table name
            data: List of dicts, each dict is a row
            column_names: Optional column order (uses dict keys if not provided)

        Returns:
            True on success, False on failure (logs error)
        """
        if not self._client:
            return False

        try:
            if not data:
                return True

            if column_names:
                columns = column_names
                rows = [[row.get(c) for c in columns] for row in data]
            else:
                columns = list(data[0].keys())
                rows = [[row[c] for c in columns] for row in data]

            await asyncio.to_thread(
                self._client.insert,
                table,
                rows,
                column_names=columns,
            )
            return True
        except Exception as e:
            logger.error(f"ClickHouse insert failed for table {table}: {e}")
            return False

    async def command(self, sql: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute SQL command (e.g. CREATE TABLE). Runs in thread pool.

        Returns:
            True on success, False on failure
        """
        if not self._client:
            return False

        try:
            await asyncio.to_thread(
                self._client.command,
                sql,
                parameters=parameters or {},
            )
            return True
        except Exception as e:
            logger.error(f"ClickHouse command failed: {e}")
            return False

    async def query(self, sql: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute query and return result. Runs in thread pool."""
        if not self._client:
            return None

        try:
            return await asyncio.to_thread(
                self._client.query,
                sql,
                parameters=parameters or {},
            )
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            return None

    @property
    def is_available(self) -> bool:
        """Check if client is connected."""
        return self._client is not None


# Global singleton for shared use (like Redis client)
_clickhouse_client: Optional[ClickHouseClient] = None


async def initialize_clickhouse_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
) -> bool:
    """
    Create and initialize global ClickHouse client at application startup.

    Call from lifespan or startup. Uses env vars (CLICKHOUSE_HOST, etc.) if args not provided.
    Returns True if connected, False if clickhouse-connect not installed or connection failed.
    """
    global _clickhouse_client
    if _clickhouse_client is not None:
        return _clickhouse_client.is_available
    _clickhouse_client = ClickHouseClient(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database or "default",
    )
    return await _clickhouse_client.initialize()


async def close_clickhouse_client() -> None:
    """Close global ClickHouse client at application shutdown."""
    global _clickhouse_client
    if _clickhouse_client:
        await _clickhouse_client.close()
        _clickhouse_client = None
        logger.info("ClickHouse client closed")


async def get_clickhouse_client() -> ClickHouseClient:
    """
    Get global ClickHouse client instance.

    Raises:
        RuntimeError: If client not initialized. Call initialize_clickhouse_client() first.
    """
    if _clickhouse_client is None:
        raise RuntimeError(
            "ClickHouse client not initialized. Call initialize_clickhouse_client() first."
        )
    return _clickhouse_client
