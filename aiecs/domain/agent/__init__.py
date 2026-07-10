# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Agent Domain Module

Provides the base AI agent model and related components.

Use ``HybridAgent`` with ``knowledge@builtin`` for optional L2 graph integration (ADR-002).
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
    VerificationExhausted,
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
    VerificationPolicy,
    WhenToVerify,
    PeerReviewPolicy,
    LoopDetectionConfig,
    GoalGraphConfig,
    GoalOrigin,
    RecoveryResult,
)

# Base Agent
from .base_agent import BaseAIAgent

# Concrete Agents
from .llm_agent import LLMAgent
from .tool_agent import ToolAgent
from .hybrid_agent import HybridAgent

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

from .verification import (
    AcceptanceCriterion,
    AggregatedGateScore,
    CitationUrlGate,
    EvidenceItem,
    FeedbackItem,
    GateRegistry,
    GateScore,
    ReadOnlyAdversarialVerifier,
    SpecGate,
    Verdict,
    VerificationContext,
    Verifier,
    build_gate_registry_from_config,
    build_verification_context,
    gate_aggregate_to_verdict,
    merge_verdicts,
    normalize_acceptance_criteria,
    run_gvr_pre_exit,
    run_verification_policy,
    build_peer_review_task,
    peer_review_response_to_verdict,
    DAWPResult,
    build_dawp_result,
    dawp_result_terminal_event,
)
from .loop_detection import LoopDetectionService, LoopSignal
from .search_burst_guard import SearchBurstGuardConfig, SearchBurstGuardService, SearchBurstSignal
from .goal_graph import GoalGraph, resolve_goal_graph_config

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
    "VerificationExhausted",
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
    "VerificationPolicy",
    "WhenToVerify",
    "PeerReviewPolicy",
    "LoopDetectionConfig",
    "LoopDetectionService",
    "LoopSignal",
    "SearchBurstGuardConfig",
    "SearchBurstGuardService",
    "SearchBurstSignal",
    "GoalGraph",
    "GoalGraphConfig",
    "GoalOrigin",
    "RecoveryResult",
    "resolve_goal_graph_config",
    # Base Agent
    "BaseAIAgent",
    # Concrete Agents
    "LLMAgent",
    "ToolAgent",
    "HybridAgent",
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
    # GVR verification (A-1)
    "AcceptanceCriterion",
    "EvidenceItem",
    "FeedbackItem",
    "Verdict",
    "VerificationContext",
    "Verifier",
    "ReadOnlyAdversarialVerifier",
    "build_verification_context",
    "merge_verdicts",
    "normalize_acceptance_criteria",
    "AggregatedGateScore",
    "GateRegistry",
    "GateScore",
    "SpecGate",
    "CitationUrlGate",
    "build_gate_registry_from_config",
    "gate_aggregate_to_verdict",
    "run_gvr_pre_exit",
    "run_verification_policy",
    "PeerReviewPolicy",
    "build_peer_review_task",
    "peer_review_response_to_verdict",
    "DAWPResult",
    "build_dawp_result",
    "dawp_result_terminal_event",
    "LoopDetectionConfig",
    "LoopDetectionService",
    "LoopSignal",
    "SearchBurstGuardConfig",
    "SearchBurstGuardService",
    "SearchBurstSignal",
    "GoalGraph",
    "GoalGraphConfig",
    "resolve_goal_graph_config",
]
