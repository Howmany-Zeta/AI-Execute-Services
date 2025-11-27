"""
Graceful Degradation for Graph Storage

Provides automatic fallback to in-memory storage when primary backend fails,
ensuring service continuity even during backend outages.
"""

import logging
from typing import Optional, Any, Dict
from dataclasses import dataclass
from enum import Enum

from aiecs.infrastructure.graph_storage import InMemoryGraphStore, GraphStore
from aiecs.infrastructure.graph_storage.error_handling import (
    GraphStoreConnectionError,
    GraphStoreError,
    ErrorHandler,
    ErrorContext,
    ErrorSeverity,
)

logger = logging.getLogger(__name__)


class DegradationMode(str, Enum):
    """Degradation mode"""

    NORMAL = "normal"  # Using primary backend
    DEGRADED = "degraded"  # Using fallback
    FAILED = "failed"  # Both backends failed


@dataclass
class DegradationStatus:
    """Status of graceful degradation"""

    mode: DegradationMode
    primary_available: bool
    fallback_available: bool
    last_failure: Optional[str] = None
    failure_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "mode": self.mode.value,
            "primary_available": self.primary_available,
            "fallback_available": self.fallback_available,
            "last_failure": self.last_failure,
            "failure_count": self.failure_count,
        }


class GracefulDegradationStore:
    """
    Graph store with graceful degradation support

    Automatically falls back to in-memory storage when primary backend fails.

    Example:
        ```python
        primary = PostgresGraphStore(...)
        store = GracefulDegradationStore(primary)
        await store.initialize()

        # If PostgreSQL fails, automatically uses in-memory fallback
        entity = await store.get_entity("entity_1")
        ```
    """

    def __init__(
        self,
        primary_store: GraphStore,
        enable_fallback: bool = True,
        max_failures: int = 3,
    ):
        """
        Initialize graceful degradation store

        Args:
            primary_store: Primary graph store backend
            enable_fallback: Enable automatic fallback
            max_failures: Max failures before switching to fallback
        """
        self.primary_store = primary_store
        self.enable_fallback = enable_fallback
        self.max_failures = max_failures

        self.fallback_store: Optional[InMemoryGraphStore] = None
        self.status = DegradationStatus(
            mode=DegradationMode.NORMAL,
            primary_available=True,
            fallback_available=False,
        )
        self.failure_count = 0
        self.error_handler = ErrorHandler()

    async def initialize(self) -> None:
        """Initialize both primary and fallback stores"""
        # Initialize primary
        try:
            await self.primary_store.initialize()
            self.status.primary_available = True
            logger.info("Primary store initialized successfully")
        except Exception as e:
            self.status.primary_available = False
            self.status.last_failure = str(e)
            logger.error(f"Primary store initialization failed: {e}")

            if self.enable_fallback:
                await self._initialize_fallback()

        # Initialize fallback if enabled
        if self.enable_fallback and not self.fallback_store:
            await self._initialize_fallback()

    async def _initialize_fallback(self) -> None:
        """Initialize fallback in-memory store"""
        try:
            self.fallback_store = InMemoryGraphStore()
            await self.fallback_store.initialize()
            self.status.fallback_available = True
            self.status.mode = DegradationMode.DEGRADED
            logger.warning("Using fallback in-memory store")
        except Exception as e:
            self.status.fallback_available = False
            self.status.mode = DegradationMode.FAILED
            logger.critical(f"Fallback store initialization failed: {e}")

    async def close(self) -> None:
        """Close both stores"""
        if self.primary_store:
            try:
                await self.primary_store.close()
            except Exception as e:
                logger.warning(f"Error closing primary store: {e}")

        if self.fallback_store:
            try:
                await self.fallback_store.close()
            except Exception as e:
                logger.warning(f"Error closing fallback store: {e}")

    def _get_active_store(self) -> GraphStore:
        """
        Get the currently active store (primary or fallback)

        Returns:
            Active graph store

        Raises:
            GraphStoreError: If no store is available
        """
        if self.status.primary_available:
            return self.primary_store
        elif self.status.fallback_available and self.fallback_store:
            return self.fallback_store
        else:
            raise GraphStoreError("No graph store available (primary and fallback both failed)")

    async def _execute_with_fallback(self, operation: str, func, *args, **kwargs):
        """
        Execute operation with automatic fallback

        Args:
            operation: Operation name for error context
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        # Try primary first
        if self.status.primary_available:
            try:
                result = await func(self.primary_store, *args, **kwargs)

                # Reset failure count on success
                if self.failure_count > 0:
                    logger.info("Primary store recovered, switching back")
                    self.failure_count = 0
                    self.status.primary_available = True
                    self.status.mode = DegradationMode.NORMAL

                return result

            except (GraphStoreConnectionError, Exception) as e:
                self.failure_count += 1
                self.status.last_failure = str(e)

                # Log error
                self.error_handler.handle_error(
                    e,
                    ErrorContext(operation=operation, severity=ErrorSeverity.HIGH),
                    reraise=False,
                )

                # Switch to fallback if threshold reached
                if self.failure_count >= self.max_failures:
                    logger.warning(f"Primary store failed {self.failure_count} times, " f"switching to fallback")
                    self.status.primary_available = False
                    self.status.mode = DegradationMode.DEGRADED

                # Try fallback if available
                if self.status.fallback_available and self.fallback_store:
                    try:
                        return await func(self.fallback_store, *args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback store also failed: {fallback_error}")
                        self.status.fallback_available = False
                        self.status.mode = DegradationMode.FAILED
                        raise GraphStoreError(f"Both primary and fallback stores failed. " f"Primary: {e}, Fallback: {fallback_error}")
                else:
                    # No fallback available, raise original error
                    raise

        # Use fallback if primary unavailable
        elif self.status.fallback_available and self.fallback_store:
            try:
                return await func(self.fallback_store, *args, **kwargs)
            except Exception as e:
                logger.error(f"Fallback store failed: {e}")
                self.status.fallback_available = False
                self.status.mode = DegradationMode.FAILED
                raise GraphStoreError(f"Fallback store failed: {e}")

        else:
            raise GraphStoreError("No graph store available")

    # Delegate all GraphStore methods with fallback
    async def add_entity(self, entity):
        """Add entity with fallback"""
        return await self._execute_with_fallback("add_entity", lambda store, e: store.add_entity(e), entity)

    async def get_entity(self, entity_id: str):
        """Get entity with fallback"""
        return await self._execute_with_fallback("get_entity", lambda store, eid: store.get_entity(eid), entity_id)

    async def add_relation(self, relation):
        """Add relation with fallback"""
        return await self._execute_with_fallback("add_relation", lambda store, r: store.add_relation(r), relation)

    async def get_relation(self, relation_id: str):
        """Get relation with fallback"""
        return await self._execute_with_fallback(
            "get_relation",
            lambda store, rid: store.get_relation(rid),
            relation_id,
        )

    async def get_neighbors(self, entity_id: str, **kwargs):
        """Get neighbors with fallback"""
        return await self._execute_with_fallback(
            "get_neighbors",
            lambda store, eid, **kw: store.get_neighbors(eid, **kw),
            entity_id,
            **kwargs,
        )

    async def get_stats(self):
        """Get stats with fallback"""
        return await self._execute_with_fallback("get_stats", lambda store: store.get_stats())

    def get_degradation_status(self) -> DegradationStatus:
        """Get current degradation status"""
        return self.status

    async def try_recover_primary(self) -> bool:
        """
        Attempt to recover primary store

        Returns:
            True if recovery successful, False otherwise
        """
        if self.status.primary_available:
            return True

        try:
            # Try to reinitialize primary
            await self.primary_store.initialize()

            # Test with a simple operation (available via StatsMixinProtocol)
            await self.primary_store.get_stats()  # type: ignore[attr-defined]

            self.status.primary_available = True
            self.status.mode = DegradationMode.NORMAL
            self.failure_count = 0
            logger.info("Primary store recovered successfully")
            return True

        except Exception as e:
            logger.warning(f"Primary store recovery failed: {e}")
            return False
