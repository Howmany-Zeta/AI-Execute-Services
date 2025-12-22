"""
Tests for Persistent Storage and Lifecycle Hooks

Comprehensive tests for community manager's persistent storage
and advanced member lifecycle hooks features.
"""

import pytest
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from aiecs.domain.community.community_manager import CommunityManager, MemberLifecycleHooks
from aiecs.domain.community.models.community_models import (
    CommunityMember, GovernanceType, CommunityRole, ResourceType
)

logger = logging.getLogger(__name__)


# Mock storage engine for testing
class MockStorageEngine:
    """Mock storage engine implementing various interfaces."""
    
    def __init__(self):
        self.storage: Dict[str, Any] = {}
        self.get_calls = 0
        self.set_calls = 0
    
    async def get_context(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data by key (context engine style)."""
        self.get_calls += 1
        return self.storage.get(key)
    
    async def set_context(self, key: str, data: Dict[str, Any]) -> None:
        """Set data by key (context engine style)."""
        self.set_calls += 1
        self.storage[key] = data
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data by key (simple style)."""
        self.get_calls += 1
        return self.storage.get(key)
    
    async def set(self, key: str, data: Dict[str, Any]) -> None:
        """Set data by key (simple style)."""
        self.set_calls += 1
        self.storage[key] = data


# Mock lifecycle hook for testing
class MockLifecycleHook(MemberLifecycleHooks):
    """Mock lifecycle hook for testing."""
    
    def __init__(self):
        self.join_calls = []
        self.exit_calls = []
        self.update_calls = []
        self.inactive_calls = []
    
    async def on_member_join(self, community_id: str, member_id: str, member: CommunityMember) -> None:
        """Track member join events."""
        self.join_calls.append({
            "community_id": community_id,
            "member_id": member_id,
            "agent_id": member.agent_id
        })
        logger.info(f"Hook: Member {member_id} joined community {community_id}")
    
    async def on_member_exit(
        self, 
        community_id: str, 
        member_id: str, 
        member: CommunityMember,
        reason: Optional[str] = None
    ) -> None:
        """Track member exit events."""
        self.exit_calls.append({
            "community_id": community_id,
            "member_id": member_id,
            "agent_id": member.agent_id,
            "reason": reason
        })
        logger.info(f"Hook: Member {member_id} exited community {community_id}, reason: {reason}")
    
    async def on_member_update(
        self, 
        community_id: str, 
        member_id: str, 
        member: CommunityMember,
        changes: Dict[str, Any]
    ) -> None:
        """Track member update events."""
        self.update_calls.append({
            "community_id": community_id,
            "member_id": member_id,
            "changes": changes
        })
        logger.info(f"Hook: Member {member_id} updated in community {community_id}")
    
    async def on_member_inactive(
        self, 
        member_id: str, 
        member: CommunityMember,
        reason: Optional[str] = None
    ) -> None:
        """Track member inactive events."""
        self.inactive_calls.append({
            "member_id": member_id,
            "agent_id": member.agent_id,
            "reason": reason
        })
        logger.info(f"Hook: Member {member_id} became inactive, reason: {reason}")


class TestPersistentStorage:
    """Test persistent storage functionality."""
    
    @pytest.mark.asyncio
    async def test_initialization_with_storage(self):
        """Test manager initialization with storage engine."""
        logger.info("Testing initialization with storage")
        
        storage = MockStorageEngine()
        manager = CommunityManager(context_engine=storage)
        
        assert manager.context_engine is storage
        assert manager._initialized is False
        
        await manager.initialize()
        
        assert manager._initialized is True
    
    @pytest.mark.asyncio
    async def test_save_community_to_storage(self):
        """Test saving community data to storage."""
        logger.info("Testing save community to storage")
        
        storage = MockStorageEngine()
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        # Create a community
        community_id = await manager.create_community(
            name="Test Community",
            description="Test storage",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        # Verify data was saved
        assert storage.set_calls > 0
        assert "communities" in storage.storage
        
        saved_communities = storage.storage["communities"]
        assert community_id in saved_communities
        assert saved_communities[community_id]["name"] == "Test Community"
    
    @pytest.mark.asyncio
    async def test_save_member_to_storage(self):
        """Test saving member data to storage."""
        logger.info("Testing save member to storage")
        
        storage = MockStorageEngine()
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        community_id = await manager.create_community(
            name="Test Community",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        # Add a member
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-123",
            community_role=CommunityRole.CONTRIBUTOR
        )
        
        # Verify member was saved
        assert "community_members" in storage.storage
        saved_members = storage.storage["community_members"]
        assert member_id in saved_members
        assert saved_members[member_id]["agent_id"] == "agent-123"
    
    @pytest.mark.asyncio
    async def test_save_resource_to_storage(self):
        """Test saving resource data to storage."""
        logger.info("Testing save resource to storage")
        
        storage = MockStorageEngine()
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        community_id = await manager.create_community(
            name="Test Community",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-123"
        )
        
        # Create a resource
        resource_id = await manager.create_community_resource(
            community_id=community_id,
            owner_member_id=member_id,
            name="Test Resource",
            resource_type=ResourceType.KNOWLEDGE,
            content={"data": "test"}
        )
        
        # Verify resource was saved
        assert "community_resources" in storage.storage
        saved_resources = storage.storage["community_resources"]
        assert resource_id in saved_resources
        assert saved_resources[resource_id]["name"] == "Test Resource"
    
    @pytest.mark.asyncio
    async def test_save_decision_to_storage(self):
        """Test saving decision data to storage."""
        logger.info("Testing save decision to storage")
        
        storage = MockStorageEngine()
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        community_id = await manager.create_community(
            name="Test Community",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-123"
        )
        
        # Propose a decision
        decision_id = await manager.propose_decision(
            community_id=community_id,
            proposer_member_id=member_id,
            title="Test Decision",
            description="Test storage",
            decision_type="policy"
        )
        
        # Verify decision was saved
        assert "community_decisions" in storage.storage
        saved_decisions = storage.storage["community_decisions"]
        assert decision_id in saved_decisions
        assert saved_decisions[decision_id]["title"] == "Test Decision"
    
    @pytest.mark.asyncio
    async def test_load_communities_from_storage(self):
        """Test loading community data from storage."""
        logger.info("Testing load communities from storage")
        
        storage = MockStorageEngine()
        
        # Pre-populate storage with community data
        community_id = "test-community-123"
        storage.storage["communities"] = {
            community_id: {
                "community_id": community_id,
                "name": "Loaded Community",
                "description": "From storage",
                "governance_type": "democratic",
                "governance_rules": {},
                "members": [],
                "max_members": None,
                "membership_criteria": {},
                "leaders": [],
                "coordinators": [],
                "shared_resources": [],
                "collective_capabilities": [],
                "knowledge_base": {},
                "activity_level": "active",
                "collaboration_score": 0.0,
                "decision_count": 0,
                "resource_count": 0,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": None,
                "metadata": {}
            }
        }
        
        # Create manager and initialize (should load data)
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        # Verify community was loaded
        assert community_id in manager.communities
        loaded_community = manager.communities[community_id]
        assert loaded_community.name == "Loaded Community"
        assert loaded_community.description == "From storage"
    
    @pytest.mark.asyncio
    async def test_load_members_from_storage(self):
        """Test loading member data from storage."""
        logger.info("Testing load members from storage")
        
        storage = MockStorageEngine()
        
        # Pre-populate storage
        member_id = "test-member-123"
        community_id = "test-community-123"
        
        storage.storage["communities"] = {
            community_id: {
                "community_id": community_id,
                "name": "Test",
                "description": None,
                "governance_type": "democratic",
                "governance_rules": {},
                "members": [member_id],
                "max_members": None,
                "membership_criteria": {},
                "leaders": [],
                "coordinators": [],
                "shared_resources": [],
                "collective_capabilities": [],
                "knowledge_base": {},
                "activity_level": "active",
                "collaboration_score": 0.0,
                "decision_count": 0,
                "resource_count": 0,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": None,
                "metadata": {}
            }
        }
        
        storage.storage["community_members"] = {
            member_id: {
                "member_id": member_id,
                "agent_id": "agent-loaded",
                "agent_role": "researcher",
                "community_role": "contributor",
                "specializations": ["AI"],
                "reputation_score": 0.0,
                "contribution_count": 0,
                "participation_level": "active",
                "is_active": True,
                "joined_at": datetime.utcnow().isoformat(),
                "last_active_at": datetime.utcnow().isoformat(),
                "metadata": {}
            }
        }
        
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        # Verify member was loaded
        assert member_id in manager.members
        loaded_member = manager.members[member_id]
        assert loaded_member.agent_id == "agent-loaded"
        assert loaded_member.agent_role == "researcher"
    
    @pytest.mark.asyncio
    async def test_load_relationships_from_storage(self):
        """Test rebuilding member-community relationships from storage."""
        logger.info("Testing load relationships from storage")
        
        storage = MockStorageEngine()
        member_id = "test-member-123"
        community_id = "test-community-123"
        agent_id = "agent-456"
        
        # Pre-populate with related data
        storage.storage["communities"] = {
            community_id: {
                "community_id": community_id,
                "name": "Test",
                "description": None,
                "governance_type": "democratic",
                "governance_rules": {},
                "members": [member_id],
                "max_members": None,
                "membership_criteria": {},
                "leaders": [],
                "coordinators": [],
                "shared_resources": [],
                "collective_capabilities": [],
                "knowledge_base": {},
                "activity_level": "active",
                "collaboration_score": 0.0,
                "decision_count": 0,
                "resource_count": 0,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": None,
                "metadata": {}
            }
        }
        
        storage.storage["community_members"] = {
            member_id: {
                "member_id": member_id,
                "agent_id": agent_id,
                "agent_role": "researcher",
                "community_role": "contributor",
                "specializations": [],
                "reputation_score": 0.0,
                "contribution_count": 0,
                "participation_level": "active",
                "is_active": True,
                "joined_at": datetime.utcnow().isoformat(),
                "last_active_at": datetime.utcnow().isoformat(),
                "metadata": {}
            }
        }
        
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        # Verify relationships were rebuilt
        assert agent_id in manager.member_communities
        assert community_id in manager.member_communities[agent_id]
        assert community_id in manager.community_members
        assert member_id in manager.community_members[community_id]
    
    @pytest.mark.asyncio
    async def test_storage_engine_with_simple_interface(self):
        """Test storage engine using get/set interface."""
        logger.info("Testing storage with simple get/set interface")
        
        class SimpleStorage:
            def __init__(self):
                self.data = {}
            
            async def get(self, key: str):
                return self.data.get(key)
            
            async def set(self, key: str, value: Any):
                self.data[key] = value
        
        storage = SimpleStorage()
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        community_id = await manager.create_community(
            name="Simple Storage Test",
            governance_type=GovernanceType.CONSENSUS
        )
        
        # Verify data was saved using simple interface
        assert "communities" in storage.data
        assert community_id in storage.data["communities"]


class TestLifecycleHooks:
    """Test advanced member lifecycle hooks."""
    
    @pytest.mark.asyncio
    async def test_register_lifecycle_hook(self):
        """Test registering a lifecycle hook."""
        logger.info("Testing lifecycle hook registration")
        
        manager = CommunityManager()
        hook = MockLifecycleHook()
        
        manager.register_lifecycle_hook(hook)
        
        assert hook in manager.lifecycle_hooks
        assert len(manager.lifecycle_hooks) == 1
    
    @pytest.mark.asyncio
    async def test_unregister_lifecycle_hook(self):
        """Test unregistering a lifecycle hook."""
        logger.info("Testing lifecycle hook unregistration")
        
        manager = CommunityManager()
        hook = MockLifecycleHook()
        
        manager.register_lifecycle_hook(hook)
        assert hook in manager.lifecycle_hooks
        
        result = manager.unregister_lifecycle_hook(hook)
        
        assert result is True
        assert hook not in manager.lifecycle_hooks
        assert len(manager.lifecycle_hooks) == 0
    
    @pytest.mark.asyncio
    async def test_unregister_nonexistent_hook(self):
        """Test unregistering a hook that wasn't registered."""
        logger.info("Testing unregister nonexistent hook")
        
        manager = CommunityManager()
        hook = MockLifecycleHook()
        
        result = manager.unregister_lifecycle_hook(hook)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_on_member_join_hook_triggered(self):
        """Test that on_member_join hook is triggered when adding a member."""
        logger.info("Testing on_member_join hook trigger")
        
        manager = CommunityManager()
        hook = MockLifecycleHook()
        manager.register_lifecycle_hook(hook)
        
        community_id = await manager.create_community(
            name="Hook Test Community",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        # Add a member (should trigger hook)
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-hook-test",
            community_role=CommunityRole.CONTRIBUTOR
        )
        
        # Verify hook was called
        assert len(hook.join_calls) == 1
        join_event = hook.join_calls[0]
        assert join_event["community_id"] == community_id
        assert join_event["member_id"] == member_id
        assert join_event["agent_id"] == "agent-hook-test"
    
    @pytest.mark.asyncio
    async def test_on_member_exit_hook_triggered(self):
        """Test that on_member_exit hook is triggered when removing a member."""
        logger.info("Testing on_member_exit hook trigger")
        
        manager = CommunityManager()
        hook = MockLifecycleHook()
        manager.register_lifecycle_hook(hook)
        
        community_id = await manager.create_community(
            name="Exit Hook Test",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-exit-test"
        )
        
        # Clear join calls
        hook.join_calls.clear()
        
        # Remove member (should trigger exit hook)
        await manager.remove_member_from_community(
            community_id=community_id,
            member_id=member_id
        )
        
        # Verify exit hook was called
        assert len(hook.exit_calls) == 1
        exit_event = hook.exit_calls[0]
        assert exit_event["community_id"] == community_id
        assert exit_event["member_id"] == member_id
        assert exit_event["reason"] == "removed"
    
    @pytest.mark.asyncio
    async def test_on_member_inactive_hook_triggered(self):
        """Test that on_member_inactive hook is triggered when deactivating a member."""
        logger.info("Testing on_member_inactive hook trigger")
        
        manager = CommunityManager()
        hook = MockLifecycleHook()
        manager.register_lifecycle_hook(hook)
        
        community_id = await manager.create_community(
            name="Inactive Hook Test",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-inactive-test"
        )
        
        # Deactivate member (should trigger inactive hook)
        await manager.deactivate_member(
            member_id=member_id,
            reason="on leave"
        )
        
        # Verify inactive hook was called
        assert len(hook.inactive_calls) == 1
        inactive_event = hook.inactive_calls[0]
        assert inactive_event["member_id"] == member_id
        assert inactive_event["reason"] == "on leave"
    
    @pytest.mark.asyncio
    async def test_multiple_hooks_execution(self):
        """Test that multiple hooks are all executed."""
        logger.info("Testing multiple hooks execution")
        
        manager = CommunityManager()
        hook1 = MockLifecycleHook()
        hook2 = MockLifecycleHook()
        
        manager.register_lifecycle_hook(hook1)
        manager.register_lifecycle_hook(hook2)
        
        community_id = await manager.create_community(
            name="Multiple Hooks Test",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-multi-hook"
        )
        
        # Both hooks should be called
        assert len(hook1.join_calls) == 1
        assert len(hook2.join_calls) == 1
        assert hook1.join_calls[0]["member_id"] == member_id
        assert hook2.join_calls[0]["member_id"] == member_id
    
    @pytest.mark.asyncio
    async def test_hook_execution_with_exception(self, caplog):
        """Test that hook exceptions don't break the main flow."""
        logger.info("Testing hook execution with exception")
        
        class FailingHook(MemberLifecycleHooks):
            async def on_member_join(self, community_id, member_id, member):
                raise Exception("Hook failed!")
        
        manager = CommunityManager()
        failing_hook = FailingHook()
        normal_hook = MockLifecycleHook()
        
        manager.register_lifecycle_hook(failing_hook)
        manager.register_lifecycle_hook(normal_hook)
        
        with caplog.at_level(logging.ERROR):
            community_id = await manager.create_community(
                name="Exception Test",
                governance_type=GovernanceType.DEMOCRATIC
            )
            
            # Add member - first hook fails, second should still run
            member_id = await manager.add_member_to_community(
                community_id=community_id,
                agent_id="agent-exception-test"
            )
            
            # Verify error was logged
            assert "Error executing lifecycle hook" in caplog.text
            
            # Verify second hook still executed
            assert len(normal_hook.join_calls) == 1
            
            # Verify member was still added
            assert member_id in manager.members
    
    @pytest.mark.asyncio
    async def test_hook_with_additional_parameters(self):
        """Test hooks receiving additional parameters."""
        logger.info("Testing hooks with additional parameters")
        
        manager = CommunityManager()
        hook = MockLifecycleHook()
        manager.register_lifecycle_hook(hook)
        
        community_id = await manager.create_community(
            name="Params Test",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-params-test"
        )
        
        # Remove with specific reason
        await manager.remove_member_from_community(
            community_id=community_id,
            member_id=member_id
        )
        
        # Verify reason was passed to hook
        assert len(hook.exit_calls) == 1
        assert hook.exit_calls[0]["reason"] == "removed"
    
    @pytest.mark.asyncio
    async def test_hook_order_preserved(self):
        """Test that hooks are executed in registration order."""
        logger.info("Testing hook execution order")
        
        execution_order = []
        
        class OrderHook1(MemberLifecycleHooks):
            async def on_member_join(self, community_id, member_id, member):
                execution_order.append(1)
        
        class OrderHook2(MemberLifecycleHooks):
            async def on_member_join(self, community_id, member_id, member):
                execution_order.append(2)
        
        class OrderHook3(MemberLifecycleHooks):
            async def on_member_join(self, community_id, member_id, member):
                execution_order.append(3)
        
        manager = CommunityManager()
        manager.register_lifecycle_hook(OrderHook1())
        manager.register_lifecycle_hook(OrderHook2())
        manager.register_lifecycle_hook(OrderHook3())
        
        community_id = await manager.create_community(
            name="Order Test",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-order-test"
        )
        
        # Verify execution order
        assert execution_order == [1, 2, 3]


class TestStorageAndHooksIntegration:
    """Test integration of storage and hooks."""
    
    @pytest.mark.asyncio
    async def test_hooks_triggered_with_storage(self):
        """Test that hooks work correctly with persistent storage."""
        logger.info("Testing hooks with storage integration")
        
        storage = MockStorageEngine()
        manager = CommunityManager(context_engine=storage)
        await manager.initialize()
        
        hook = MockLifecycleHook()
        manager.register_lifecycle_hook(hook)
        
        community_id = await manager.create_community(
            name="Integration Test",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        member_id = await manager.add_member_to_community(
            community_id=community_id,
            agent_id="agent-integration"
        )
        
        # Verify both hook and storage worked
        assert len(hook.join_calls) == 1
        assert "community_members" in storage.storage
        assert member_id in storage.storage["community_members"]
    
    @pytest.mark.asyncio
    async def test_load_data_then_trigger_hooks(self):
        """Test that hooks work after loading data from storage."""
        logger.info("Testing hooks after loading from storage")
        
        storage = MockStorageEngine()
        
        # First session: create community and member
        manager1 = CommunityManager(context_engine=storage)
        await manager1.initialize()
        
        community_id = await manager1.create_community(
            name="Persistent Community",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        # Second session: load data and register hook
        manager2 = CommunityManager(context_engine=storage)
        await manager2.initialize()
        
        hook = MockLifecycleHook()
        manager2.register_lifecycle_hook(hook)
        
        # Verify community was loaded
        assert community_id in manager2.communities
        
        # Add new member (should trigger hook)
        member_id = await manager2.add_member_to_community(
            community_id=community_id,
            agent_id="agent-persistent"
        )
        
        # Verify hook was triggered
        assert len(hook.join_calls) == 1
        assert hook.join_calls[0]["community_id"] == community_id

