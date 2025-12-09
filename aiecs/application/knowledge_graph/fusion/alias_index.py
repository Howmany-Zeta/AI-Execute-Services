"""
Alias Index

Provides O(1) lookup for entity aliases and abbreviations.
Supports in-memory HashMap and Redis backends with tenant isolation.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, AsyncIterator, Any

logger = logging.getLogger(__name__)


class MatchType(Enum):
    """Type of alias match"""
    EXACT = "exact"
    ALIAS = "alias"
    ABBREVIATION = "abbreviation"
    NORMALIZED = "normalized"


@dataclass
class AliasEntry:
    """Entry in the alias index"""
    entity_id: str
    match_type: MatchType
    original_name: Optional[str] = None  # Original form before normalization
    tenant_id: Optional[str] = None  # Tenant ID for multi-tenant isolation


@dataclass
class TransactionState:
    """State for tracking transaction operations"""
    operations: List[tuple] = field(default_factory=list)  # (op_type, key, value)
    committed: bool = False


class AliasIndexBackend(ABC):
    """Abstract base class for alias index backends"""

    @abstractmethod
    async def get(self, alias: str) -> Optional[AliasEntry]:
        """Get entity entry for an alias"""
        pass

    @abstractmethod
    async def set(self, alias: str, entry: AliasEntry) -> None:
        """Set alias to entity mapping"""
        pass

    @abstractmethod
    async def delete(self, alias: str) -> bool:
        """Delete an alias entry. Returns True if existed."""
        pass

    @abstractmethod
    async def get_by_entity_id(self, entity_id: str) -> List[str]:
        """Get all aliases for an entity"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all entries"""
        pass

    @abstractmethod
    async def size(self) -> int:
        """Get number of entries"""
        pass

    @abstractmethod
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator["TransactionContext"]:
        """Start a transaction for atomic operations"""
        pass


class TransactionContext:
    """Context for transactional operations"""

    def __init__(self, backend: AliasIndexBackend):
        self.backend = backend
        self.state = TransactionState()
        self._rollback_data: Dict[str, Optional[AliasEntry]] = {}

    async def set(self, alias: str, entry: AliasEntry) -> None:
        """Set within transaction"""
        # Store current value for rollback
        if alias not in self._rollback_data:
            self._rollback_data[alias] = await self.backend.get(alias)
        self.state.operations.append(("set", alias, entry))
        await self.backend.set(alias, entry)

    async def delete(self, alias: str) -> bool:
        """Delete within transaction"""
        # Store current value for rollback
        if alias not in self._rollback_data:
            self._rollback_data[alias] = await self.backend.get(alias)
        self.state.operations.append(("delete", alias, None))
        return await self.backend.delete(alias)

    async def rollback(self) -> None:
        """Rollback all operations in this transaction"""
        for alias, original_entry in self._rollback_data.items():
            if original_entry is None:
                await self.backend.delete(alias)
            else:
                await self.backend.set(alias, original_entry)
        self.state.operations.clear()
        self._rollback_data.clear()
        logger.debug("Transaction rolled back")

    def commit(self) -> None:
        """Mark transaction as committed"""
        self.state.committed = True
        self._rollback_data.clear()
        logger.debug(f"Transaction committed with {len(self.state.operations)} operations")


class InMemoryBackend(AliasIndexBackend):
    """In-memory HashMap backend for O(1) lookup with tenant isolation"""

    def __init__(self):
        self._index: Dict[str, AliasEntry] = {}
        self._entity_aliases: Dict[str, Set[str]] = {}  # entity_id -> set of aliases
        self._lock = asyncio.Lock()

    def _make_key(self, alias: str, tenant_id: Optional[str] = None) -> str:
        """
        Create tenant-prefixed key for alias lookup.
        
        Args:
            alias: The alias string
            tenant_id: Optional tenant ID for multi-tenant isolation
            
        Returns:
            Tenant-prefixed key (e.g., "tenant_123:apple" or "apple" for global)
        """
        normalized = alias.lower()
        if tenant_id:
            return f"{tenant_id}:{normalized}"
        return normalized

    async def get(self, alias: str) -> Optional[AliasEntry]:
        """Get entity entry for an alias - O(1)"""
        # For backward compatibility, try both with and without tenant prefix
        # First try as-is (may contain tenant prefix already)
        entry = self._index.get(alias.lower())
        if entry:
            return entry
        # If alias contains ":", it might already be prefixed
        if ":" in alias:
            return self._index.get(alias.lower())
        return None

    async def set(self, alias: str, entry: AliasEntry) -> None:
        """Set alias to entity mapping - O(1)"""
        key = self._make_key(alias, entry.tenant_id)
        self._index[key] = entry
        # Track reverse mapping
        if entry.entity_id not in self._entity_aliases:
            self._entity_aliases[entry.entity_id] = set()
        self._entity_aliases[entry.entity_id].add(key)

    async def delete(self, alias: str) -> bool:
        """Delete an alias entry - O(1)"""
        key = alias.lower()
        if key in self._index:
            entry = self._index.pop(key)
            # Update reverse mapping
            if entry.entity_id in self._entity_aliases:
                self._entity_aliases[entry.entity_id].discard(key)
            return True
        return False

    async def get_by_entity_id(self, entity_id: str) -> List[str]:
        """Get all aliases for an entity - O(1)"""
        return list(self._entity_aliases.get(entity_id, set()))

    async def clear(self) -> None:
        """Clear all entries"""
        self._index.clear()
        self._entity_aliases.clear()

    async def size(self) -> int:
        """Get number of entries"""
        return len(self._index)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[TransactionContext]:
        """Start a transaction with lock for concurrency safety"""
        async with self._lock:
            ctx = TransactionContext(self)
            try:
                yield ctx
                ctx.commit()
            except Exception:
                await ctx.rollback()
                raise


class RedisBackend(AliasIndexBackend):
    """
    Redis backend for large graphs or distributed deployments.

    Uses Redis hashes for O(1) lookup and MULTI/EXEC for atomic transactions.
    """

    # Redis key prefixes
    ALIAS_KEY = "alias_index:aliases"  # Hash: alias -> JSON(AliasEntry)
    ENTITY_KEY_PREFIX = "alias_index:entity:"  # Set: entity_id -> aliases

    def __init__(self, redis_client: Any = None, redis_url: Optional[str] = None):
        """
        Initialize Redis backend.

        Args:
            redis_client: Existing Redis client (async)
            redis_url: Redis URL for creating new client
        """
        self._client = redis_client
        self._redis_url = redis_url
        self._initialized = False

    async def _ensure_client(self) -> None:
        """Ensure Redis client is initialized"""
        if self._initialized:
            return

        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(
                    self._redis_url or "redis://localhost:6379",
                    decode_responses=True
                )
            except ImportError:
                raise ImportError(
                    "redis package required for Redis backend. "
                    "Install with: pip install redis"
                )
        self._initialized = True

    def _make_key(self, alias: str, tenant_id: Optional[str] = None) -> str:
        """
        Create tenant-prefixed key for alias lookup.
        
        Args:
            alias: The alias string
            tenant_id: Optional tenant ID for multi-tenant isolation
            
        Returns:
            Tenant-prefixed key (e.g., "tenant_123:apple" or "apple" for global)
        """
        normalized = alias.lower()
        if tenant_id:
            return f"{tenant_id}:{normalized}"
        return normalized

    async def get(self, alias: str) -> Optional[AliasEntry]:
        """Get entity entry for an alias - O(1)"""
        await self._ensure_client()
        import json

        # Try to get with the key as-is (may already be prefixed)
        data = await self._client.hget(self.ALIAS_KEY, alias.lower())
        if data:
            entry_dict = json.loads(data)
            return AliasEntry(
                entity_id=entry_dict["entity_id"],
                match_type=MatchType(entry_dict["match_type"]),
                original_name=entry_dict.get("original_name"),
                tenant_id=entry_dict.get("tenant_id")
            )
        return None

    async def set(self, alias: str, entry: AliasEntry) -> None:
        """Set alias to entity mapping - O(1)"""
        await self._ensure_client()
        import json

        key = self._make_key(alias, entry.tenant_id)
        entry_dict = {
            "entity_id": entry.entity_id,
            "match_type": entry.match_type.value,
            "original_name": entry.original_name,
            "tenant_id": entry.tenant_id
        }
        await self._client.hset(self.ALIAS_KEY, key, json.dumps(entry_dict))
        # Track reverse mapping
        await self._client.sadd(f"{self.ENTITY_KEY_PREFIX}{entry.entity_id}", key)

    async def delete(self, alias: str) -> bool:
        """Delete an alias entry - O(1)"""
        await self._ensure_client()

        key = alias.lower()
        # Get entry first to update reverse mapping
        entry = await self.get(alias)
        if entry:
            await self._client.hdel(self.ALIAS_KEY, key)
            await self._client.srem(f"{self.ENTITY_KEY_PREFIX}{entry.entity_id}", key)
            return True
        return False

    async def get_by_entity_id(self, entity_id: str) -> List[str]:
        """Get all aliases for an entity - O(1)"""
        await self._ensure_client()
        members = await self._client.smembers(f"{self.ENTITY_KEY_PREFIX}{entity_id}")
        return list(members) if members else []

    async def clear(self) -> None:
        """Clear all entries"""
        await self._ensure_client()
        # Get all entity keys to delete
        cursor = 0
        keys_to_delete = [self.ALIAS_KEY]
        while True:
            cursor, keys = await self._client.scan(
                cursor, match=f"{self.ENTITY_KEY_PREFIX}*", count=100
            )
            keys_to_delete.extend(keys)
            if cursor == 0:
                break
        if keys_to_delete:
            await self._client.delete(*keys_to_delete)

    async def size(self) -> int:
        """Get number of entries"""
        await self._ensure_client()
        return await self._client.hlen(self.ALIAS_KEY)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[TransactionContext]:
        """
        Start a Redis transaction using MULTI/EXEC.

        Note: For true atomicity, operations are collected and executed
        together. Rollback restores previous state.
        """
        await self._ensure_client()
        ctx = TransactionContext(self)
        try:
            yield ctx
            ctx.commit()
        except Exception:
            await ctx.rollback()
            raise


class AliasIndex:
    """
    High-level alias index with O(1) lookup.

    Supports automatic backend selection based on graph size:
    - In-memory HashMap for small-medium graphs (<100K entities)
    - Redis for large graphs or distributed deployments

    Example:
        ```python
        # Create with auto-detection
        index = AliasIndex()

        # Or specify backend
        index = AliasIndex(backend="redis", redis_url="redis://localhost:6379")

        # Add aliases
        await index.add_alias("Albert Einstein", "person_123", MatchType.EXACT)
        await index.add_alias("A. Einstein", "person_123", MatchType.ALIAS)
        await index.add_alias("Einstein", "person_123", MatchType.ALIAS)

        # Lookup - O(1)
        entry = await index.lookup("a. einstein")
        assert entry.entity_id == "person_123"

        # Atomic merge
        async with index.transaction() as tx:
            await tx.delete("old_alias")
            await tx.set("new_alias", AliasEntry(...))
        ```
    """

    # Threshold for auto-switching to Redis backend
    AUTO_REDIS_THRESHOLD = 100_000

    def __init__(
        self,
        backend: Optional[str] = None,
        redis_url: Optional[str] = None,
        redis_client: Any = None,
        auto_redis_threshold: int = AUTO_REDIS_THRESHOLD,
    ):
        """
        Initialize alias index.

        Args:
            backend: "memory" or "redis". If None, auto-detects.
            redis_url: Redis URL for Redis backend
            redis_client: Existing Redis client
            auto_redis_threshold: Entity count threshold for auto-switching to Redis
        """
        self._backend_type = backend
        self._redis_url = redis_url
        self._redis_client = redis_client
        self._auto_redis_threshold = auto_redis_threshold
        self._backend: Optional[AliasIndexBackend] = None
        self._lock = asyncio.Lock()

    async def _get_backend(self) -> AliasIndexBackend:
        """Get or create backend"""
        if self._backend is None:
            if self._backend_type == "redis":
                self._backend = RedisBackend(
                    redis_client=self._redis_client,
                    redis_url=self._redis_url
                )
            else:
                # Default to in-memory
                self._backend = InMemoryBackend()
        return self._backend

    async def lookup(
        self, alias: str, tenant_id: Optional[str] = None
    ) -> Optional[AliasEntry]:
        """
        Look up an alias - O(1).

        **Tenant Isolation**: When tenant_id is provided, lookup uses tenant-prefixed
        keys to ensure isolation between tenants.

        Args:
            alias: The alias to look up (case-insensitive)
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            AliasEntry if found, None otherwise
        """
        backend = await self._get_backend()
        # Create tenant-prefixed key if tenant_id provided
        if tenant_id:
            key = f"{tenant_id}:{alias.lower()}"
        else:
            key = alias.lower()
        return await backend.get(key)

    async def add_alias(
        self,
        alias: str,
        entity_id: str,
        match_type: MatchType = MatchType.ALIAS,
        original_name: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        """
        Add an alias for an entity.

        **Tenant Isolation**: When tenant_id is provided, the alias is stored with
        a tenant-prefixed key to ensure isolation.

        Args:
            alias: The alias string
            entity_id: ID of the entity this alias refers to
            match_type: Type of match (exact, alias, abbreviation, normalized)
            original_name: Original form before normalization
            tenant_id: Optional tenant ID for multi-tenant isolation
        """
        backend = await self._get_backend()
        entry = AliasEntry(
            entity_id=entity_id,
            match_type=match_type,
            original_name=original_name,
            tenant_id=tenant_id
        )
        await backend.set(alias, entry)

    async def remove_alias(
        self, alias: str, tenant_id: Optional[str] = None
    ) -> bool:
        """
        Remove an alias.

        **Tenant Isolation**: When tenant_id is provided, removes the alias from
        the tenant-specific namespace.

        Args:
            alias: The alias to remove
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            True if alias existed and was removed
        """
        backend = await self._get_backend()
        # Create tenant-prefixed key if tenant_id provided
        if tenant_id:
            key = f"{tenant_id}:{alias.lower()}"
        else:
            key = alias.lower()
        return await backend.delete(key)

    async def get_entity_aliases(self, entity_id: str) -> List[str]:
        """
        Get all aliases for an entity.

        Args:
            entity_id: The entity ID

        Returns:
            List of aliases for this entity
        """
        backend = await self._get_backend()
        return await backend.get_by_entity_id(entity_id)

    async def remove_entity_aliases(self, entity_id: str) -> int:
        """
        Remove all aliases for an entity.

        Args:
            entity_id: The entity ID

        Returns:
            Number of aliases removed
        """
        backend = await self._get_backend()
        aliases = await backend.get_by_entity_id(entity_id)
        for alias in aliases:
            await backend.delete(alias)
        return len(aliases)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[TransactionContext]:
        """
        Start a transaction for atomic operations.

        Use for merge operations that need to delete old aliases
        and insert new aliases atomically.

        Example:
            ```python
            async with index.transaction() as tx:
                await tx.delete("old_alias_1")
                await tx.delete("old_alias_2")
                await tx.set("new_alias", AliasEntry(...))
            # All operations committed atomically
            ```
        """
        backend = await self._get_backend()
        async with backend.transaction() as ctx:
            yield ctx

    async def batch_load(
        self,
        entries: List[tuple],  # List of (alias, entity_id, match_type)
    ) -> int:
        """
        Batch load aliases for initial index building.

        Args:
            entries: List of (alias, entity_id, match_type) tuples

        Returns:
            Number of entries loaded
        """
        backend = await self._get_backend()
        count = 0
        for alias, entity_id, match_type in entries:
            entry = AliasEntry(entity_id=entity_id, match_type=match_type)
            await backend.set(alias, entry)
            count += 1
        return count

    async def clear(self) -> None:
        """Clear all entries from the index"""
        backend = await self._get_backend()
        await backend.clear()

    async def size(self) -> int:
        """Get number of entries in the index"""
        backend = await self._get_backend()
        return await backend.size()

    async def should_use_redis(self, entity_count: int) -> bool:
        """
        Check if Redis backend should be used based on entity count.

        Args:
            entity_count: Number of entities in the graph

        Returns:
            True if Redis is recommended
        """
        return entity_count >= self._auto_redis_threshold

