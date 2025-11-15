"""
Community Domain Module

Provides agent community collaboration features including governance,
resource sharing, decision-making, and collaborative workflows.

This module enables developers to:
- Create and manage agent communities
- Facilitate agent-to-agent communication
- Share resources and knowledge between agents
- Make collective decisions through various governance models
- Run collaborative workflows and sessions

Version: 1.0.0
"""

__version__ = "1.0.0"

# Core managers
from .community_manager import CommunityManager, MemberLifecycleHooks
from .community_integration import CommunityIntegration
from .decision_engine import (
    DecisionEngine,
    ConsensusAlgorithm,
    ConflictResolutionStrategy,
)
from .resource_manager import ResourceManager
from .collaborative_workflow import CollaborativeWorkflowEngine
from .analytics import CommunityAnalytics

# Communication and context
from .communication_hub import (
    CommunicationHub,
    Message,
    Event,
    MessageType,
    EventType,
)
from .shared_context_manager import (
    SharedContextManager,
    SharedContext,
    ContextScope,
    ConflictResolutionStrategy as ContextConflictStrategy,
)

# Agent adapters
from .agent_adapter import (
    AgentAdapter,
    StandardLLMAdapter,
    CustomAgentAdapter,
    AgentAdapterRegistry,
    AgentCapability,
)

# Builder
from .community_builder import CommunityBuilder, builder

# Models
from .models import (
    CommunityRole,
    GovernanceType,
    DecisionStatus,
    ResourceType,
    CommunityMember,
    CommunityResource,
    CommunityDecision,
    AgentCommunity,
    CollaborationSession,
)

# Exceptions
from .exceptions import (
    CommunityException,
    CommunityNotFoundError,
    MemberNotFoundError,
    ResourceNotFoundError,
    DecisionNotFoundError,
    AccessDeniedError,
    MembershipError,
    VotingError,
    GovernanceError,
    CollaborationError,
    CommunityInitializationError,
    CommunityValidationError,
    QuorumNotMetError,
    ConflictResolutionError,
    CommunityCapacityError,
    AgentAdapterError,
    CommunicationError,
    ContextError,
)

__all__ = [
    # Version
    "__version__",
    # Core managers
    "CommunityManager",
    "CommunityIntegration",
    "DecisionEngine",
    "ResourceManager",
    "CollaborativeWorkflowEngine",
    "CommunityAnalytics",
    "MemberLifecycleHooks",
    # Communication and context
    "CommunicationHub",
    "Message",
    "Event",
    "MessageType",
    "EventType",
    "SharedContextManager",
    "SharedContext",
    "ContextScope",
    "ContextConflictStrategy",
    # Agent adapters
    "AgentAdapter",
    "StandardLLMAdapter",
    "CustomAgentAdapter",
    "AgentAdapterRegistry",
    "AgentCapability",
    # Builder
    "CommunityBuilder",
    "builder",
    # Enums
    "CommunityRole",
    "GovernanceType",
    "DecisionStatus",
    "ResourceType",
    "ConsensusAlgorithm",
    "ConflictResolutionStrategy",
    # Models
    "CommunityMember",
    "CommunityResource",
    "CommunityDecision",
    "AgentCommunity",
    "CollaborationSession",
    # Exceptions
    "CommunityException",
    "CommunityNotFoundError",
    "MemberNotFoundError",
    "ResourceNotFoundError",
    "DecisionNotFoundError",
    "AccessDeniedError",
    "MembershipError",
    "VotingError",
    "GovernanceError",
    "CollaborationError",
    "CommunityInitializationError",
    "CommunityValidationError",
    "QuorumNotMetError",
    "ConflictResolutionError",
    "CommunityCapacityError",
    "AgentAdapterError",
    "CommunicationError",
    "ContextError",
]
