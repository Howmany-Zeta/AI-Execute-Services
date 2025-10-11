"""Domain layer module

Contains business logic and domain models.
"""

from .execution.model import TaskStepResult, TaskStatus, ErrorCode
from .task.model import TaskContext, DSLStep
from .task.dsl_processor import DSLProcessor
from .context import (
    ContextEngine, SessionMetrics, ConversationMessage,
    ConversationParticipant, ConversationSession, AgentCommunicationMessage,
    create_session_key, validate_conversation_isolation_pattern
)
from .community import (
    # Core managers
    CommunityManager, CommunityIntegration, DecisionEngine, ResourceManager,
    CollaborativeWorkflowEngine, CommunityAnalytics, MemberLifecycleHooks,
    
    # Communication and context
    CommunicationHub, Message, Event, MessageType, EventType,
    SharedContextManager, SharedContext, ContextScope, ContextConflictStrategy,
    
    # Agent adapters
    AgentAdapter, StandardLLMAdapter, CustomAgentAdapter, AgentAdapterRegistry, AgentCapability,
    
    # Builder
    CommunityBuilder, builder,
    
    # Enums
    CommunityRole, GovernanceType, DecisionStatus, ResourceType,
    ConsensusAlgorithm, ConflictResolutionStrategy,
    
    # Models
    CommunityMember, CommunityResource, CommunityDecision, AgentCommunity, CollaborationSession,
    
    # Exceptions
    CommunityException, CommunityNotFoundError, MemberNotFoundError, ResourceNotFoundError,
    DecisionNotFoundError, AccessDeniedError, MembershipError, VotingError, GovernanceError,
    CollaborationError, CommunityInitializationError, CommunityValidationError,
    QuorumNotMetError, ConflictResolutionError, CommunityCapacityError,
    AgentAdapterError, CommunicationError, ContextError,
)

__all__ = [
    # Execution domain
    "TaskStepResult",
    "TaskStatus",
    "ErrorCode",

    # Task domain
    "TaskContext",
    "DSLStep",
    "DSLProcessor",

    # Context domain
    "ContextEngine",
    "SessionMetrics",
    "ConversationMessage",
    "ConversationParticipant",
    "ConversationSession",
    "AgentCommunicationMessage",
    "create_session_key",
    "validate_conversation_isolation_pattern",

    # Community domain - Core managers
    "CommunityManager",
    "CommunityIntegration",
    "DecisionEngine",
    "ResourceManager",
    "CollaborativeWorkflowEngine",
    "CommunityAnalytics",
    "MemberLifecycleHooks",

    # Community domain - Communication and context
    "CommunicationHub",
    "Message",
    "Event",
    "MessageType",
    "EventType",
    "SharedContextManager",
    "SharedContext",
    "ContextScope",
    "ContextConflictStrategy",

    # Community domain - Agent adapters
    "AgentAdapter",
    "StandardLLMAdapter",
    "CustomAgentAdapter",
    "AgentAdapterRegistry",
    "AgentCapability",

    # Community domain - Builder
    "CommunityBuilder",
    "builder",

    # Community domain - Enums
    "CommunityRole",
    "GovernanceType",
    "DecisionStatus",
    "ResourceType",
    "ConsensusAlgorithm",
    "ConflictResolutionStrategy",

    # Community domain - Models
    "CommunityMember",
    "CommunityResource",
    "CommunityDecision",
    "AgentCommunity",
    "CollaborationSession",

    # Community domain - Exceptions
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
