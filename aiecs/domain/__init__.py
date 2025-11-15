"""Domain layer module

Contains business logic and domain models.
"""

from .execution.model import TaskStepResult, TaskStatus, ErrorCode
from .task.model import TaskContext, DSLStep
from .task.dsl_processor import DSLProcessor
from .context import (
    ContextEngine,
    SessionMetrics,
    ConversationMessage,
    ConversationParticipant,
    ConversationSession,
    AgentCommunicationMessage,
    create_session_key,
    validate_conversation_isolation_pattern,
)
from .community import (
    # Core managers
    CommunityManager,
    CommunityIntegration,
    DecisionEngine,
    ResourceManager,
    CollaborativeWorkflowEngine,
    CommunityAnalytics,
    MemberLifecycleHooks,
    # Communication and context
    CommunicationHub,
    Message,
    Event,
    MessageType,
    EventType,
    SharedContextManager,
    SharedContext,
    ContextScope,
    ContextConflictStrategy,
    # Agent adapters
    AgentAdapter,
    StandardLLMAdapter,
    CustomAgentAdapter,
    AgentAdapterRegistry,
    AgentCapability,
    # Builder
    CommunityBuilder,
    builder,
    # Enums
    CommunityRole,
    GovernanceType,
    DecisionStatus,
    ResourceType,
    ConsensusAlgorithm,
    ConflictResolutionStrategy,
    # Models
    CommunityMember,
    CommunityResource,
    CommunityDecision,
    AgentCommunity,
    CollaborationSession,
    # Exceptions
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

from .agent import (
    # Exceptions
    AgentException,
    AgentNotFoundError,
    AgentAlreadyRegisteredError,
    InvalidStateTransitionError,
    ConfigurationError,
    TaskExecutionError,
    ToolAccessDeniedError,
    SerializationError,
    AgentInitializationError,
    # Enums
    AgentState,
    AgentType,
    GoalStatus,
    GoalPriority,
    CapabilityLevel,
    MemoryType,
    # Models
    RetryPolicy,
    AgentConfiguration,
    AgentGoal,
    AgentCapabilityDeclaration,
    AgentMetrics,
    AgentInteraction,
    AgentMemory,
    # Base and Concrete Agents
    BaseAIAgent,
    LLMAgent,
    ToolAgent,
    HybridAgent,
    # Lifecycle Management
    AgentRegistry,
    AgentLifecycleManager,
    get_global_registry,
    get_global_lifecycle_manager,
    # Persistence
    InMemoryPersistence,
    FilePersistence,
    get_global_persistence,
    set_global_persistence,
    # Observability
    AgentController,
    LoggingObserver,
    MetricsObserver,
    # Prompts
    PromptTemplate,
    ChatPromptTemplate,
    MessageBuilder,
    # Tools
    ToolSchemaGenerator,
    generate_tool_schema,
    # Memory
    ConversationMemory,
    Session,
    # Integration
    ContextEngineAdapter,
    EnhancedRetryPolicy,
    RoleConfiguration,
    ContextCompressor,
    compress_messages,
    # Migration
    LegacyAgentWrapper,
    convert_langchain_prompt,
    convert_legacy_config,
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
    # Agent domain - Exceptions
    "AgentException",
    "AgentNotFoundError",
    "AgentAlreadyRegisteredError",
    "InvalidStateTransitionError",
    "ConfigurationError",
    "TaskExecutionError",
    "ToolAccessDeniedError",
    "SerializationError",
    "AgentInitializationError",
    # Agent domain - Enums
    "AgentState",
    "AgentType",
    "GoalStatus",
    "GoalPriority",
    "CapabilityLevel",
    "MemoryType",
    # Agent domain - Models
    "RetryPolicy",
    "AgentConfiguration",
    "AgentGoal",
    "AgentCapabilityDeclaration",
    "AgentMetrics",
    "AgentInteraction",
    "AgentMemory",
    # Agent domain - Base and Concrete Agents
    "BaseAIAgent",
    "LLMAgent",
    "ToolAgent",
    "HybridAgent",
    # Agent domain - Lifecycle Management
    "AgentRegistry",
    "AgentLifecycleManager",
    "get_global_registry",
    "get_global_lifecycle_manager",
    # Agent domain - Persistence
    "InMemoryPersistence",
    "FilePersistence",
    "get_global_persistence",
    "set_global_persistence",
    # Agent domain - Observability
    "AgentController",
    "LoggingObserver",
    "MetricsObserver",
    # Agent domain - Prompts
    "PromptTemplate",
    "ChatPromptTemplate",
    "MessageBuilder",
    # Agent domain - Tools
    "ToolSchemaGenerator",
    "generate_tool_schema",
    # Agent domain - Memory
    "ConversationMemory",
    "Session",
    # Agent domain - Integration
    "ContextEngineAdapter",
    "EnhancedRetryPolicy",
    "RoleConfiguration",
    "ContextCompressor",
    "compress_messages",
    # Agent domain - Migration
    "LegacyAgentWrapper",
    "convert_langchain_prompt",
    "convert_legacy_config",
]
