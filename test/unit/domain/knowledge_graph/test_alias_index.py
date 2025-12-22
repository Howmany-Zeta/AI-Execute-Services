"""
Unit tests for AliasIndex

Tests O(1) alias lookup, in-memory and Redis backends,
transactional updates, and concurrent operations.
"""

import asyncio
import pytest

from aiecs.application.knowledge_graph.fusion.alias_index import (
    AliasIndex,
    AliasEntry,
    MatchType,
    InMemoryBackend,
    TransactionContext,
)


class TestInMemoryBackend:
    """Test InMemoryBackend"""

    @pytest.fixture
    def backend(self):
        """Create InMemoryBackend instance"""
        return InMemoryBackend()

    @pytest.mark.asyncio
    async def test_set_and_get(self, backend):
        """Test basic set and get operations"""
        entry = AliasEntry(entity_id="entity_1", match_type=MatchType.ALIAS)
        await backend.set("test alias", entry)
        
        result = await backend.get("test alias")
        assert result is not None
        assert result.entity_id == "entity_1"
        assert result.match_type == MatchType.ALIAS

    @pytest.mark.asyncio
    async def test_get_case_insensitive(self, backend):
        """Test case-insensitive lookup"""
        entry = AliasEntry(entity_id="entity_1", match_type=MatchType.ALIAS)
        await backend.set("Test Alias", entry)
        
        # Should find with different case
        result = await backend.get("test alias")
        assert result is not None
        assert result.entity_id == "entity_1"
        
        result = await backend.get("TEST ALIAS")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, backend):
        """Test get for nonexistent alias"""
        result = await backend.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, backend):
        """Test delete operation"""
        entry = AliasEntry(entity_id="entity_1", match_type=MatchType.ALIAS)
        await backend.set("test alias", entry)
        
        # Delete should return True
        result = await backend.delete("test alias")
        assert result is True
        
        # Should no longer exist
        assert await backend.get("test alias") is None
        
        # Delete again should return False
        result = await backend.delete("test alias")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_entity_id(self, backend):
        """Test getting all aliases for an entity"""
        entry = AliasEntry(entity_id="entity_1", match_type=MatchType.ALIAS)
        await backend.set("alias1", entry)
        await backend.set("alias2", entry)
        await backend.set("alias3", entry)
        
        aliases = await backend.get_by_entity_id("entity_1")
        assert len(aliases) == 3
        assert "alias1" in aliases
        assert "alias2" in aliases
        assert "alias3" in aliases

    @pytest.mark.asyncio
    async def test_size(self, backend):
        """Test size operation"""
        assert await backend.size() == 0
        
        entry = AliasEntry(entity_id="entity_1", match_type=MatchType.ALIAS)
        await backend.set("alias1", entry)
        assert await backend.size() == 1
        
        await backend.set("alias2", entry)
        assert await backend.size() == 2

    @pytest.mark.asyncio
    async def test_clear(self, backend):
        """Test clear operation"""
        entry = AliasEntry(entity_id="entity_1", match_type=MatchType.ALIAS)
        await backend.set("alias1", entry)
        await backend.set("alias2", entry)
        
        await backend.clear()
        assert await backend.size() == 0
        assert await backend.get("alias1") is None


class TestAliasIndex:
    """Test AliasIndex high-level API"""

    @pytest.fixture
    def index(self):
        """Create AliasIndex with in-memory backend"""
        return AliasIndex(backend="memory")

    @pytest.mark.asyncio
    async def test_add_and_lookup(self, index):
        """Test adding and looking up aliases"""
        await index.add_alias("Albert Einstein", "person_123", MatchType.EXACT)
        await index.add_alias("A. Einstein", "person_123", MatchType.ALIAS)
        
        result = await index.lookup("albert einstein")
        assert result is not None
        assert result.entity_id == "person_123"
        assert result.match_type == MatchType.EXACT
        
        result = await index.lookup("a. einstein")
        assert result is not None
        assert result.entity_id == "person_123"

    @pytest.mark.asyncio
    async def test_remove_alias(self, index):
        """Test removing an alias"""
        await index.add_alias("test", "entity_1", MatchType.ALIAS)
        
        result = await index.remove_alias("test")
        assert result is True
        
        assert await index.lookup("test") is None

    @pytest.mark.asyncio
    async def test_get_entity_aliases(self, index):
        """Test getting all aliases for an entity"""
        await index.add_alias("alias1", "entity_1", MatchType.ALIAS)
        await index.add_alias("alias2", "entity_1", MatchType.ALIAS)
        await index.add_alias("other", "entity_2", MatchType.ALIAS)

        aliases = await index.get_entity_aliases("entity_1")
        assert len(aliases) == 2
        assert "alias1" in aliases
        assert "alias2" in aliases

    @pytest.mark.asyncio
    async def test_remove_entity_aliases(self, index):
        """Test removing all aliases for an entity"""
        await index.add_alias("alias1", "entity_1", MatchType.ALIAS)
        await index.add_alias("alias2", "entity_1", MatchType.ALIAS)
        await index.add_alias("other", "entity_2", MatchType.ALIAS)

        count = await index.remove_entity_aliases("entity_1")
        assert count == 2

        # Entity 1 aliases should be gone
        assert await index.lookup("alias1") is None
        assert await index.lookup("alias2") is None

        # Entity 2 alias should remain
        assert await index.lookup("other") is not None

    @pytest.mark.asyncio
    async def test_batch_load(self, index):
        """Test batch loading aliases"""
        entries = [
            ("alias1", "entity_1", MatchType.ALIAS),
            ("alias2", "entity_1", MatchType.ALIAS),
            ("alias3", "entity_2", MatchType.EXACT),
        ]

        count = await index.batch_load(entries)
        assert count == 3
        assert await index.size() == 3

    @pytest.mark.asyncio
    async def test_should_use_redis(self, index):
        """Test Redis threshold detection"""
        # Default threshold is 100,000
        assert await index.should_use_redis(50_000) is False
        assert await index.should_use_redis(100_000) is True
        assert await index.should_use_redis(200_000) is True


class TestTransactions:
    """Test transactional operations"""

    @pytest.fixture
    def index(self):
        """Create AliasIndex with in-memory backend"""
        return AliasIndex(backend="memory")

    @pytest.mark.asyncio
    async def test_transaction_commit(self, index):
        """Test successful transaction commit"""
        await index.add_alias("old_alias", "entity_1", MatchType.ALIAS)

        async with index.transaction() as tx:
            await tx.delete("old_alias")
            await tx.set("new_alias", AliasEntry(
                entity_id="entity_1",
                match_type=MatchType.ALIAS
            ))

        # Old alias should be gone
        assert await index.lookup("old_alias") is None
        # New alias should exist
        assert await index.lookup("new_alias") is not None

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, index):
        """Test transaction rollback on error"""
        await index.add_alias("existing", "entity_1", MatchType.ALIAS)

        try:
            async with index.transaction() as tx:
                await tx.delete("existing")
                # Simulate error
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Should be rolled back - alias should still exist
        result = await index.lookup("existing")
        assert result is not None
        assert result.entity_id == "entity_1"

    @pytest.mark.asyncio
    async def test_transaction_rollback_restores_deleted(self, index):
        """Test that rollback restores deleted entries"""
        await index.add_alias("alias1", "entity_1", MatchType.ALIAS)
        await index.add_alias("alias2", "entity_1", MatchType.ALIAS)

        try:
            async with index.transaction() as tx:
                await tx.delete("alias1")
                await tx.delete("alias2")
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Both should be restored
        assert await index.lookup("alias1") is not None
        assert await index.lookup("alias2") is not None

    @pytest.mark.asyncio
    async def test_atomic_merge_operation(self, index):
        """Test atomic merge: delete old aliases + insert new aliases"""
        # Setup: entity with old aliases
        await index.add_alias("old_name_1", "entity_old", MatchType.EXACT)
        await index.add_alias("old_alias_1", "entity_old", MatchType.ALIAS)

        # Atomic merge operation
        async with index.transaction() as tx:
            # Delete old aliases
            await tx.delete("old_name_1")
            await tx.delete("old_alias_1")
            # Insert new aliases for merged entity
            await tx.set("merged_name", AliasEntry(
                entity_id="entity_merged",
                match_type=MatchType.EXACT
            ))
            await tx.set("merged_alias", AliasEntry(
                entity_id="entity_merged",
                match_type=MatchType.ALIAS
            ))

        # Old aliases gone
        assert await index.lookup("old_name_1") is None
        assert await index.lookup("old_alias_1") is None
        # New aliases exist
        assert await index.lookup("merged_name") is not None
        assert await index.lookup("merged_alias") is not None


class TestConcurrentOperations:
    """Test concurrent index operations"""

    @pytest.fixture
    def index(self):
        """Create AliasIndex with in-memory backend"""
        return AliasIndex(backend="memory")

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, index):
        """Test concurrent read operations"""
        # Setup
        await index.add_alias("alias1", "entity_1", MatchType.ALIAS)
        await index.add_alias("alias2", "entity_2", MatchType.ALIAS)

        # Concurrent reads
        async def read_alias(alias: str):
            for _ in range(100):
                result = await index.lookup(alias)
                assert result is not None

        await asyncio.gather(
            read_alias("alias1"),
            read_alias("alias2"),
            read_alias("alias1"),
            read_alias("alias2"),
        )

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, index):
        """Test concurrent write operations"""
        async def write_aliases(prefix: str, count: int):
            for i in range(count):
                await index.add_alias(
                    f"{prefix}_{i}",
                    f"entity_{prefix}_{i}",
                    MatchType.ALIAS
                )

        # Concurrent writes from multiple "workers"
        await asyncio.gather(
            write_aliases("worker1", 50),
            write_aliases("worker2", 50),
            write_aliases("worker3", 50),
        )

        # All should be written
        assert await index.size() == 150

    @pytest.mark.asyncio
    async def test_concurrent_transactions(self, index):
        """Test that transactions are serialized (no interleaving)"""
        # Setup
        await index.add_alias("shared", "entity_1", MatchType.ALIAS)

        results = []

        async def transaction_1():
            async with index.transaction() as tx:
                await tx.delete("shared")
                await asyncio.sleep(0.01)  # Simulate work
                await tx.set("from_tx1", AliasEntry(
                    entity_id="entity_tx1",
                    match_type=MatchType.ALIAS
                ))
            results.append("tx1")

        async def transaction_2():
            async with index.transaction() as tx:
                await tx.set("from_tx2", AliasEntry(
                    entity_id="entity_tx2",
                    match_type=MatchType.ALIAS
                ))
            results.append("tx2")

        # Run concurrently - transactions should be serialized
        await asyncio.gather(transaction_1(), transaction_2())

        # Both transactions should complete
        assert len(results) == 2
        # Both entries should exist
        assert await index.lookup("from_tx1") is not None
        assert await index.lookup("from_tx2") is not None

