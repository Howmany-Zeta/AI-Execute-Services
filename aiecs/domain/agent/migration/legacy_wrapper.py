"""
Legacy Agent Wrapper

Compatibility wrapper for gradual migration from legacy agents.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LegacyAgentWrapper:
    """
    Wrapper for legacy agents to work with BaseAIAgent interface.

    This enables gradual migration without breaking existing code.

    Example:
        legacy_agent = SomeLegacyAgent()
        wrapped = LegacyAgentWrapper(legacy_agent)
        result = await wrapped.execute_task(task, context)
    """

    def __init__(self, legacy_agent: Any):
        """
        Initialize wrapper.

        Args:
            legacy_agent: Legacy agent instance
        """
        self.legacy_agent = legacy_agent
        self._is_wrapped = True
        logger.info(f"Legacy agent wrapped: {type(legacy_agent).__name__}")

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task using legacy agent.

        Args:
            task: Task specification
            context: Execution context

        Returns:
            Result dictionary
        """
        # Try various legacy interfaces
        if hasattr(self.legacy_agent, "execute_task"):
            return await self.legacy_agent.execute_task(task, context)
        elif hasattr(self.legacy_agent, "run"):
            result = await self.legacy_agent.run(task.get("description", ""))
            return {"output": result, "success": True}
        elif hasattr(self.legacy_agent, "process"):
            result = await self.legacy_agent.process(task)
            return {"output": result, "success": True}
        else:
            raise NotImplementedError(f"Legacy agent {type(self.legacy_agent).__name__} has no compatible interface")

    async def process_message(self, message: str, sender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process message using legacy agent.

        Args:
            message: Message content
            sender_id: Optional sender ID

        Returns:
            Response dictionary
        """
        if hasattr(self.legacy_agent, "process_message"):
            return await self.legacy_agent.process_message(message, sender_id)
        elif hasattr(self.legacy_agent, "chat"):
            response = await self.legacy_agent.chat(message)
            return {"response": response}
        else:
            # Fallback to execute_task
            task = {"description": message}
            result = await self.execute_task(task, {"sender_id": sender_id})
            return {"response": result.get("output")}

    def __getattr__(self, name: str):
        """Forward attribute access to legacy agent."""
        return getattr(self.legacy_agent, name)

    def __repr__(self) -> str:
        return f"LegacyAgentWrapper({type(self.legacy_agent).__name__})"
