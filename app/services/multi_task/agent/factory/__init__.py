"""
Agent Factory Module

Provides factory classes for creating and managing agents.
The factory layer is organized into:
- AgentFactory: Main factory for creating agents based on configuration
- LazyAgentPuul: Factory that creates agents on demand, optimizing resource usage
"""

from .agent_factory import AgentFactory
from .lazy_agent_pool import LazyAgentPool

__all__ = [
    'AgentFactory',
    'LazyAgentPool'
]
