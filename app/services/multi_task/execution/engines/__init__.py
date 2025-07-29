"""
Execution Engines

This module contains specific execution engine implementations for different
execution modes and strategies.

Engines:
- DSLEngine: Executes Domain Specific Language workflows
- LangChainEngine: Executes LangChain-based agent workflows with LangGraph support
- ParallelEngine: Executes tasks in parallel with optimization

Note: CrewEngine has been deprecated and replaced by LangChainEngine
"""

from .dsl_engine import DSLEngine
from .langchain_engine import LangChainEngine
from .parallel_engine import ParallelEngine

# Deprecated imports (for backward compatibility)
try:
    from .crew_engine_deprecated import CrewEngine
    _CREW_ENGINE_AVAILABLE = True
except ImportError:
    _CREW_ENGINE_AVAILABLE = False
    # Create a placeholder class that raises an error when used
    class CrewEngine:
        def __init__(self, *args, **kwargs):
            raise DeprecationWarning(
                "CrewEngine has been deprecated. Please use LangChainEngine instead. "
                "See langchain_engine.py for the replacement implementation."
            )

__all__ = ['DSLEngine', 'LangChainEngine', 'ParallelEngine', 'CrewEngine']

# Provide migration guidance
def get_recommended_engine():
    """
    Get the recommended engine for agent-based workflows.

    Returns:
        LangChainEngine class - the recommended replacement for CrewEngine
    """
    return LangChainEngine

def migrate_from_crew_to_langchain():
    """
    Provide guidance for migrating from CrewEngine to LangChainEngine.

    Returns:
        dict: Migration guidance and mapping
    """
    return {
        "migration_guide": {
            "old_engine": "CrewEngine",
            "new_engine": "LangChainEngine",
            "key_differences": [
                "Uses LangChain agents instead of CrewAI agents",
                "Supports LangGraph for advanced workflow orchestration",
                "Includes dynamic agent management and pooling",
                "Better integration with existing agent infrastructure"
            ],
            "migration_steps": [
                "1. Replace CrewEngine imports with LangChainEngine",
                "2. Update agent definitions to use LangChain format",
                "3. Modify workflow definitions if using LangGraph features",
                "4. Test with new engine to ensure compatibility"
            ]
        },
        "api_mapping": {
            "CrewEngine.__init__": "LangChainEngine.__init__",
            "CrewEngine.execute_task": "LangChainEngine.execute_task",
            "CrewEngine.execute_workflow": "LangChainEngine.execute_workflow",
            "CrewEngine.add_agent": "LangChainEngine.dynamic_agent_manager.create_agent_on_demand",
            "CrewEngine.remove_agent": "LangChainEngine.dynamic_agent_manager.destroy_agent"
        }
    }
