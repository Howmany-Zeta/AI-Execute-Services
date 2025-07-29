"""
Agent Layer

This module provides agent management capabilities for the multi-task service,
including agent creation, configuration, and lifecycle management.

The agent layer is organized into several components:
- BaseAgent: Abstract base class for all agents
- AgentFactory: Factory for creating agents based on configuration
- AgentRegistry: Registry for managing agent instances
- AgentManager: High-level manager implementing IAgentManager interface
- System Agents: Core workflow agents (intent parser, planner, etc.)
- Domain Agents: Specialized agents for specific domains (researcher, analyst, etc.)
"""

from .base_agent import BaseAgent

# System agents
from .system.intent_parser import IntentParserAgent
from .system.task_decomposer import TaskDecomposerAgent
from .system.planner import PlannerAgent
from .system.supervisor import SupervisorAgent
from .system.director import DirectorAgent

# Domain agents
from .domain.researcher import ResearcherAgent
from .domain.analyst import AnalystAgent
from .domain.fieldwork import FieldworkAgent
from .domain.writer import WriterAgent
from .domain.meta_architect import MetaArchitectAgent

# Note: AgentManager, AgentFactory, and AgentRegistry are not imported here
# to avoid circular dependencies. Import them directly from their modules:
# from .agent_manager import AgentManager
# from .factory.agent_factory import AgentFactory
# from .registry.agent_registry import AgentRegistry

__all__ = [
    # Core components
    'BaseAgent',

    # System agents
    'IntentParserAgent',
    'TaskDecomposerAgent',
    'PlannerAgent',
    'SupervisorAgent',
    'DirectorAgent',

    # Domain agents
    'ResearcherAgent',
    'AnalystAgent',
    'FieldworkAgent',
    'WriterAgent',
    'MetaArchitectAgent'
]
