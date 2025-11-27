"""
Agent Domain Module

Provides the base AI agent model and related components.
"""

# Exceptions
from .exceptions import (
    AgentException,
    AgentNotFoundError,
    AgentAlreadyRegisteredError,
    InvalidStateTransitionError,
    ConfigurationError,
    TaskExecutionError,
    ToolAccessDeniedError,
    SerializationError,
    AgentInitializationError,
)

# Models and Enums
from .models import (
    AgentState,
    AgentType,
    GoalStatus,
    GoalPriority,
    CapabilityLevel,
    MemoryType,
    RetryPolicy,
    AgentConfiguration,
    AgentGoal,
    AgentCapabilityDeclaration,
    AgentMetrics,
    GraphMetrics,
    AgentInteraction,
    AgentMemory,
)

# Base Agent
from .base_agent import BaseAIAgent

# Concrete Agents
from .llm_agent import LLMAgent
from .tool_agent import ToolAgent
from .hybrid_agent import HybridAgent
from .knowledge_aware_agent import KnowledgeAwareAgent

# Graph-Aware Mixin
from .graph_aware_mixin import GraphAwareAgentMixin

# Lifecycle Management
from .registry import AgentRegistry, get_global_registry, reset_global_registry
from .lifecycle import (
    AgentLifecycleManager,
    get_global_lifecycle_manager,
    reset_global_lifecycle_manager,
)

# Persistence
from .persistence import (
    AgentPersistence,
    InMemoryPersistence,
    FilePersistence,
    AgentStateSerializer,
    get_global_persistence,
    set_global_persistence,
    reset_global_persistence,
)

# Observability
from .observability import (
    AgentObserver,
    LoggingObserver,
    MetricsObserver,
    AgentController,
)

# Prompts
from .prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    MessageBuilder,
)

# Tools
from .tools import (
    ToolSchemaGenerator,
    generate_tool_schema,
)

# Memory
from .memory import (
    ConversationMemory,
    Session,
)

# Integration
from .integration import (
    ContextEngineAdapter,
    EnhancedRetryPolicy,
    ErrorClassifier,
    RoleConfiguration,
    load_role_config,
    ContextCompressor,
    compress_messages,
)

# Migration
from .migration import (
    LegacyAgentWrapper,
    convert_langchain_prompt,
    convert_legacy_config,
)

__all__ = [
    # Exceptions
    "AgentException",
    "AgentNotFoundError",
    "AgentAlreadyRegisteredError",
    "InvalidStateTransitionError",
    "ConfigurationError",
    "TaskExecutionError",
    "ToolAccessDeniedError",
    "SerializationError",
    "AgentInitializationError",
    # Enums
    "AgentState",
    "AgentType",
    "GoalStatus",
    "GoalPriority",
    "CapabilityLevel",
    "MemoryType",
    # Models
    "RetryPolicy",
    "AgentConfiguration",
    "AgentGoal",
    "AgentCapabilityDeclaration",
    "AgentMetrics",
    "GraphMetrics",
    "AgentInteraction",
    "AgentMemory",
    # Base Agent
    "BaseAIAgent",
    # Concrete Agents
    "LLMAgent",
    "ToolAgent",
    "HybridAgent",  # Original hybrid agent (backward compatible)
    "KnowledgeAwareAgent",  # Enhanced agent with knowledge graph integration
    "GraphAwareAgentMixin",  # Reusable mixin for graph-aware agents
    # Lifecycle Management
    "AgentRegistry",
    "get_global_registry",
    "reset_global_registry",
    "AgentLifecycleManager",
    "get_global_lifecycle_manager",
    "reset_global_lifecycle_manager",
    # Persistence
    "AgentPersistence",
    "InMemoryPersistence",
    "FilePersistence",
    "AgentStateSerializer",
    "get_global_persistence",
    "set_global_persistence",
    "reset_global_persistence",
    # Observability
    "AgentObserver",
    "LoggingObserver",
    "MetricsObserver",
    "AgentController",
    # Prompts
    "PromptTemplate",
    "ChatPromptTemplate",
    "MessageBuilder",
    # Tools
    "ToolSchemaGenerator",
    "generate_tool_schema",
    # Memory
    "ConversationMemory",
    "Session",
    # Integration
    "ContextEngineAdapter",
    "EnhancedRetryPolicy",
    "ErrorClassifier",
    "RoleConfiguration",
    "load_role_config",
    "ContextCompressor",
    "compress_messages",
    # Migration
    "LegacyAgentWrapper",
    "convert_langchain_prompt",
    "convert_legacy_config",
]
