"""
Tests for Shared Context Manager

Tests for context versioning, conflict resolution, and streaming.
"""

import pytest
import logging
import asyncio

from aiecs.domain.community.shared_context_manager import ContextScope, ConflictResolutionStrategy

logger = logging.getLogger(__name__)


class TestContextCreation:
    """Tests for context creation and management."""
    
    @pytest.mark.asyncio
    async def test_create_context(self, context_manager):
        """Test creating a shared context."""
        logger.info("Testing context creation")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner_agent",
            scope_id="community_1",
            initial_data={"key": "value", "number": 42}
        )
        
        assert context_id is not None
        assert context_id in context_manager.contexts
        
        context = context_manager.contexts[context_id]
        assert context.scope == ContextScope.COMMUNITY
        assert context.owner_id == "owner_agent"
        assert context.data["key"] == "value"
        assert context.current_version == 1
        
        logger.debug(f"Created context: {context_id}")
    
    @pytest.mark.asyncio
    async def test_create_contexts_different_scopes(self, context_manager):
        """Test creating contexts with different scopes."""
        logger.info("Testing different context scopes")
        
        scopes = [
            (ContextScope.COMMUNITY, "community_1"),
            (ContextScope.SESSION, "session_1"),
            (ContextScope.TASK, "task_1"),
            (ContextScope.AGENT, "agent_1")
        ]
        
        for scope, scope_id in scopes:
            context_id = await context_manager.create_context(
                scope=scope,
                owner_id="owner",
                scope_id=scope_id,
                initial_data={"scope": scope.value}
            )
            
            context = context_manager.contexts[context_id]
            assert context.scope == scope
            
            logger.debug(f"Created {scope.value} context: {context_id}")


class TestContextAccess:
    """Tests for context access and permissions."""
    
    @pytest.mark.asyncio
    async def test_get_context_with_permission(self, context_manager):
        """Test getting context with proper permission."""
        logger.info("Testing context access with permission")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"data": "test"}
        )
        
        # Owner can access
        data = await context_manager.get_context(context_id, "owner")
        assert data is not None
        assert data["data"] == "test"
        
        logger.debug("Owner accessed context successfully")
    
    @pytest.mark.asyncio
    async def test_get_context_without_permission(self, context_manager):
        """Test getting context without permission."""
        logger.info("Testing context access without permission")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"secret": "data"}
        )
        
        # Non-owner cannot access
        data = await context_manager.get_context(context_id, "other_agent")
        assert data is None
        
        logger.debug("Access denied as expected")
    
    @pytest.mark.asyncio
    async def test_grant_and_revoke_access(self, context_manager):
        """Test granting and revoking access."""
        logger.info("Testing grant and revoke access")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"data": "shared"}
        )
        
        # Grant access
        success = await context_manager.grant_access(
            context_id=context_id,
            granter_id="owner",
            grantee_id="collaborator"
        )
        assert success is True
        
        # Collaborator can now access
        data = await context_manager.get_context(context_id, "collaborator")
        assert data is not None
        
        # Revoke access
        success = await context_manager.revoke_access(
            context_id=context_id,
            revoker_id="owner",
            revokee_id="collaborator"
        )
        assert success is True
        
        # Collaborator can no longer access
        data = await context_manager.get_context(context_id, "collaborator")
        assert data is None
        
        logger.debug("Grant and revoke successful")


class TestContextVersioning:
    """Tests for context versioning."""
    
    @pytest.mark.asyncio
    async def test_update_creates_version(self, context_manager):
        """Test that updates create new versions."""
        logger.info("Testing version creation on update")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"version": 1}
        )
        
        context = context_manager.contexts[context_id]
        initial_version = context.current_version
        
        # Update
        await context_manager.update_context(
            context_id=context_id,
            updater_id="owner",
            updates={"version": 2},
            create_version=True
        )
        
        assert context.current_version == initial_version + 1
        assert context.data["version"] == 2
        
        logger.debug(f"Version incremented to {context.current_version}")
    
    @pytest.mark.asyncio
    async def test_get_specific_version(self, context_manager):
        """Test retrieving specific versions."""
        logger.info("Testing get specific version")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"value": "v1"}
        )
        
        # Create multiple versions
        await context_manager.update_context(context_id, "owner", {"value": "v2"})
        await context_manager.update_context(context_id, "owner", {"value": "v3"})
        
        # Get version 1
        data_v1 = await context_manager.get_context(context_id, "owner", version=1)
        assert data_v1["value"] == "v1"
        
        # Get version 2
        data_v2 = await context_manager.get_context(context_id, "owner", version=2)
        assert data_v2["value"] == "v2"
        
        # Get current (version 3)
        data_current = await context_manager.get_context(context_id, "owner")
        assert data_current["value"] == "v3"
        
        logger.debug("Retrieved all versions correctly")
    
    @pytest.mark.asyncio
    async def test_version_history(self, context_manager):
        """Test getting version history."""
        logger.info("Testing version history")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"count": 0}
        )
        
        # Make multiple updates
        for i in range(5):
            await context_manager.update_context(
                context_id, "owner", {"count": i + 1}
            )
        
        history = await context_manager.get_version_history(context_id, "owner")
        
        assert history is not None
        assert len(history) == 6  # Initial + 5 updates
        
        logger.debug(f"Version history has {len(history)} versions")
    
    @pytest.mark.asyncio
    async def test_rollback_to_version(self, context_manager):
        """Test rolling back to previous version."""
        logger.info("Testing rollback to version")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"state": "initial"}
        )
        
        # Make updates
        await context_manager.update_context(context_id, "owner", {"state": "modified"})
        await context_manager.update_context(context_id, "owner", {"state": "broken"})
        
        # Rollback to version 1 (initial)
        success = await context_manager.rollback_to_version(
            context_id=context_id,
            requester_id="owner",
            target_version=1
        )
        
        assert success is True
        
        # Verify rolled back
        data = await context_manager.get_context(context_id, "owner")
        assert data["state"] == "initial"
        
        logger.debug("Rolled back successfully")


class TestConflictResolution:
    """Tests for conflict resolution strategies."""
    
    @pytest.mark.asyncio
    async def test_last_write_wins(self, context_manager):
        """Test last write wins conflict resolution."""
        logger.info("Testing last write wins")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"key": "original"}
        )
        
        await context_manager.grant_access(context_id, "owner", "agent_1")
        
        # Update with last write wins
        await context_manager.update_context(
            context_id=context_id,
            updater_id="agent_1",
            updates={"key": "updated"},
            conflict_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS
        )
        
        data = await context_manager.get_context(context_id, "owner")
        assert data["key"] == "updated"
        
        logger.debug("Last write wins applied")
    
    @pytest.mark.asyncio
    async def test_merge_strategy(self, context_manager):
        """Test merge conflict resolution."""
        logger.info("Testing merge strategy")
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"list": [1, 2], "dict": {"a": 1}}
        )
        
        await context_manager.grant_access(context_id, "owner", "agent_1")
        
        # Update with merge
        await context_manager.update_context(
            context_id=context_id,
            updater_id="agent_1",
            updates={"list": [3, 4], "dict": {"b": 2}},
            conflict_strategy=ConflictResolutionStrategy.MERGE
        )
        
        data = await context_manager.get_context(context_id, "owner")
        
        # List should be merged
        assert 1 in data["list"] and 3 in data["list"]
        
        # Dict should be merged
        assert "a" in data["dict"] and "b" in data["dict"]
        
        logger.debug("Merge strategy applied")


class TestContextStreaming:
    """Tests for context streaming."""
    
    @pytest.mark.asyncio
    async def test_subscribe_to_context_updates(self, context_manager):
        """Test subscribing to context updates."""
        logger.info("Testing context update subscription")
        
        received_updates = []
        
        async def update_callback(notification):
            received_updates.append(notification)
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"value": 0}
        )
        
        # Subscribe
        success = await context_manager.subscribe_to_context(
            context_id=context_id,
            subscriber_id="owner",
            callback=update_callback
        )
        assert success is True
        
        # Update
        await context_manager.update_context(
            context_id, "owner", {"value": 1}
        )
        
        await asyncio.sleep(0.1)
        
        assert len(received_updates) == 1
        assert received_updates[0]["data"]["value"] == 1
        
        logger.debug("Context update streamed successfully")
    
    @pytest.mark.asyncio
    async def test_unsubscribe_from_context(self, context_manager):
        """Test unsubscribing from context updates."""
        logger.info("Testing context unsubscribe")
        
        received_updates = []
        
        async def callback(notification):
            received_updates.append(notification)
        
        context_id = await context_manager.create_context(
            scope=ContextScope.COMMUNITY,
            owner_id="owner",
            scope_id="comm_1",
            initial_data={"count": 0}
        )
        
        await context_manager.subscribe_to_context(context_id, "owner", callback)
        
        # Update (should receive)
        await context_manager.update_context(context_id, "owner", {"count": 1})
        await asyncio.sleep(0.1)
        assert len(received_updates) == 1
        
        # Unsubscribe
        success = await context_manager.unsubscribe_from_context(
            context_id, "owner", callback
        )
        assert success is True
        
        # Update again (should not receive)
        await context_manager.update_context(context_id, "owner", {"count": 2})
        await asyncio.sleep(0.1)
        assert len(received_updates) == 1  # Still 1
        
        logger.debug("Unsubscribe successful")


class TestContextStatistics:
    """Tests for context statistics."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, context_manager):
        """Test getting context manager statistics."""
        logger.info("Testing context statistics")
        
        # Create contexts in different scopes
        await context_manager.create_context(
            ContextScope.COMMUNITY, "owner", "comm_1", {"data": 1}
        )
        await context_manager.create_context(
            ContextScope.SESSION, "owner", "sess_1", {"data": 2}
        )
        await context_manager.create_context(
            ContextScope.TASK, "owner", "task_1", {"data": 3}
        )
        
        stats = context_manager.get_statistics()
        
        assert stats["total_contexts"] >= 3
        assert stats["community_contexts"] >= 1
        assert stats["session_contexts"] >= 1
        assert stats["task_contexts"] >= 1
        
        logger.debug(f"Statistics: {stats}")


