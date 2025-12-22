"""
Pytest Configuration and Fixtures for Community Tests

Provides shared fixtures and configuration for all community tests.
"""

import pytest
import asyncio
import logging
from datetime import datetime

from aiecs.domain.community.community_manager import CommunityManager
from aiecs.domain.community.decision_engine import DecisionEngine
from aiecs.domain.community.resource_manager import ResourceManager
from aiecs.domain.community.collaborative_workflow import CollaborativeWorkflowEngine
from aiecs.domain.community.community_integration import CommunityIntegration
from aiecs.domain.community.communication_hub import CommunicationHub
from aiecs.domain.community.shared_context_manager import SharedContextManager
from aiecs.domain.community.agent_adapter import AgentAdapterRegistry
from aiecs.domain.community.analytics import CommunityAnalytics
from aiecs.domain.community.models import GovernanceType, CommunityRole

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def community_manager(event_loop):
    """Create a community manager instance."""
    manager = CommunityManager(context_engine=None)
    event_loop.run_until_complete(manager.initialize())
    logger.debug("Created CommunityManager fixture")
    return manager


@pytest.fixture
def decision_engine(community_manager):
    """Create a decision engine instance."""
    engine = DecisionEngine(community_manager)
    logger.debug("Created DecisionEngine fixture")
    return engine


@pytest.fixture
def resource_manager(community_manager):
    """Create a resource manager instance."""
    manager = ResourceManager(community_manager, context_engine=None)
    logger.debug("Created ResourceManager fixture")
    return manager


@pytest.fixture
def workflow_engine(community_manager, resource_manager, decision_engine):
    """Create a collaborative workflow engine instance."""
    engine = CollaborativeWorkflowEngine(
        community_manager,
        resource_manager,
        decision_engine
    )
    logger.debug("Created CollaborativeWorkflowEngine fixture")
    return engine


@pytest.fixture
def community_integration(event_loop):
    """Create a community integration instance."""
    integration = CommunityIntegration(agent_manager=None, context_engine=None)
    event_loop.run_until_complete(integration.initialize())
    logger.debug("Created CommunityIntegration fixture")
    return integration


@pytest.fixture
def communication_hub():
    """Create a communication hub instance."""
    hub = CommunicationHub(max_queue_size=100)
    logger.debug("Created CommunicationHub fixture")
    return hub


@pytest.fixture
def context_manager():
    """Create a shared context manager instance."""
    manager = SharedContextManager()
    logger.debug("Created SharedContextManager fixture")
    return manager


@pytest.fixture
def agent_registry():
    """Create an agent adapter registry instance."""
    registry = AgentAdapterRegistry()
    logger.debug("Created AgentAdapterRegistry fixture")
    return registry


@pytest.fixture
def analytics(community_manager):
    """Create a community analytics instance."""
    analytics_inst = CommunityAnalytics(community_manager)
    logger.debug("Created CommunityAnalytics fixture")
    return analytics_inst


@pytest.fixture
def sample_community(community_manager, event_loop):
    """Create a sample community for testing."""
    community_id = event_loop.run_until_complete(
        community_manager.create_community(
            name="Test Community",
            description="A test community",
            governance_type=GovernanceType.DEMOCRATIC
        )
    )
    logger.debug(f"Created sample community: {community_id}")
    return community_id


@pytest.fixture
def sample_members(community_manager, sample_community, event_loop):
    """Create sample members in the test community."""
    member_ids = []
    
    # Create leader
    leader_id = event_loop.run_until_complete(
        community_manager.add_member_to_community(
            community_id=sample_community,
            agent_id="agent_leader",
            agent_role="leader",
            community_role=CommunityRole.LEADER,
            specializations=["leadership", "strategy"]
        )
    )
    member_ids.append(leader_id)
    
    # Create coordinator
    coordinator_id = event_loop.run_until_complete(
        community_manager.add_member_to_community(
            community_id=sample_community,
            agent_id="agent_coordinator",
            agent_role="coordinator",
            community_role=CommunityRole.COORDINATOR,
            specializations=["coordination", "planning"]
        )
    )
    member_ids.append(coordinator_id)
    
    # Create contributors
    for i in range(3):
        contributor_id = event_loop.run_until_complete(
            community_manager.add_member_to_community(
                community_id=sample_community,
                agent_id=f"agent_contributor_{i}",
                agent_role="contributor",
                community_role=CommunityRole.CONTRIBUTOR,
                specializations=["development", "testing"]
            )
        )
        member_ids.append(contributor_id)
    
    logger.debug(f"Created {len(member_ids)} sample members")
    return member_ids


@pytest.fixture
def sample_agent_roles():
    """Provide sample agent roles for testing."""
    return ["analyst", "developer", "tester", "reviewer"]


# Helper functions for tests

def assert_datetime_recent(dt: datetime, seconds: int = 5):
    """Assert that a datetime is recent (within seconds)."""
    now = datetime.utcnow()
    delta = (now - dt).total_seconds()
    assert delta < seconds, f"Datetime not recent: {delta} seconds ago"
    

async def create_test_decision(community_manager, community_id, proposer_id):
    """Helper to create a test decision."""
    decision_id = await community_manager.propose_decision(
        community_id=community_id,
        proposer_member_id=proposer_id,
        title="Test Decision",
        description="A test decision for voting",
        decision_type="policy"
    )
    return decision_id

