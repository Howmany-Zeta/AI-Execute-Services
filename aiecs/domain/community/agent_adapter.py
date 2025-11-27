"""
Agent Adapter System

Provides an adapter architecture for integrating custom agents and LLM clients
into the community system. Supports heterogeneous agent types and extensibility.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from enum import Enum

logger = logging.getLogger(__name__)


class AgentCapability(str, Enum):
    """Standard agent capabilities."""

    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    DECISION_MAKING = "decision_making"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    TASK_PLANNING = "task_planning"
    IMAGE_PROCESSING = "image_processing"
    AUDIO_PROCESSING = "audio_processing"
    MULTIMODAL = "multimodal"


class AgentAdapter(ABC):
    """
    Abstract base class for agent adapters.

    Implement this class to integrate custom agent types or LLM clients
    into the community system.
    """

    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agent adapter.

        Args:
            agent_id: Unique identifier for the agent
            config: Optional configuration for the agent
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.capabilities: List[AgentCapability] = []
        self.metadata: Dict[str, Any] = {}
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the agent adapter.

        Returns:
            True if initialization was successful
        """

    @abstractmethod
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a task with the agent.

        Args:
            task: Task description or instruction
            context: Optional context for the task
            **kwargs: Additional parameters

        Returns:
            Execution result with status and output
        """

    @abstractmethod
    async def communicate(
        self,
        message: str,
        recipient_id: Optional[str] = None,
        message_type: str = "request",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send a message to another agent or broadcast.

        Args:
            message: Message content
            recipient_id: Optional recipient agent ID (None = broadcast)
            message_type: Type of message (request, response, notification, share)
            **kwargs: Additional message parameters

        Returns:
            Message delivery status and response
        """

    @abstractmethod
    async def get_capabilities(self) -> List[AgentCapability]:
        """
        Get the capabilities of this agent.

        Returns:
            List of agent capabilities
        """

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the agent.

        Returns:
            Health status information
        """

    async def shutdown(self) -> bool:
        """
        Shutdown the agent adapter gracefully.

        Returns:
            True if shutdown was successful
        """
        self._initialized = False
        logger.info(f"Agent adapter {self.agent_id} shutdown")
        return True


class StandardLLMAdapter(AgentAdapter):
    """
    Adapter for standard LLM clients (OpenAI, Anthropic, etc.).
    """

    def __init__(
        self,
        agent_id: str,
        llm_client: Any,
        model_name: str,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize standard LLM adapter.

        Args:
            agent_id: Unique identifier for the agent
            llm_client: The LLM client instance
            model_name: Name of the model
            config: Optional configuration
        """
        super().__init__(agent_id, config)
        self.llm_client = llm_client
        self.model_name = model_name
        self.capabilities = [
            AgentCapability.TEXT_GENERATION,
            AgentCapability.DECISION_MAKING,
            AgentCapability.KNOWLEDGE_RETRIEVAL,
        ]

    async def initialize(self) -> bool:
        """Initialize the LLM adapter."""
        try:
            # Test connection with simple prompt
            if hasattr(self.llm_client, "health_check"):
                await self.llm_client.health_check()
            self._initialized = True
            logger.info(f"Initialized LLM adapter for {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM adapter: {e}")
            return False

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Execute a task with the LLM."""
        if not self._initialized:
            return {"status": "error", "error": "Adapter not initialized"}

        try:
            # Build prompt from task and context
            prompt = self._build_prompt(task, context)

            # Call LLM client
            if hasattr(self.llm_client, "generate"):
                response = await self.llm_client.generate(prompt=prompt, model=self.model_name, **kwargs)
            elif hasattr(self.llm_client, "complete"):
                response = await self.llm_client.complete(prompt, **kwargs)
            else:
                response = str(self.llm_client)  # Fallback

            return {
                "status": "success",
                "output": response,
                "agent_id": self.agent_id,
                "model": self.model_name,
            }
        except Exception as e:
            logger.error(f"Error executing task with LLM: {e}")
            return {"status": "error", "error": str(e)}

    async def communicate(
        self,
        message: str,
        recipient_id: Optional[str] = None,
        message_type: str = "request",
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a message through the LLM."""
        # LLMs typically don't directly communicate, but can format messages
        formatted_message = {
            "from": self.agent_id,
            "to": recipient_id or "broadcast",
            "type": message_type,
            "content": message,
            "model": self.model_name,
        }

        return {"status": "formatted", "message": formatted_message}

    async def get_capabilities(self) -> List[AgentCapability]:
        """Get LLM capabilities."""
        return self.capabilities

    async def health_check(self) -> Dict[str, Any]:
        """Check LLM health."""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "agent_id": self.agent_id,
            "model": self.model_name,
            "capabilities": [cap.value for cap in self.capabilities],
        }

    def _build_prompt(self, task: str, context: Optional[Dict[str, Any]]) -> str:
        """Build prompt from task and context."""
        prompt_parts = []

        if context:
            if "system" in context:
                prompt_parts.append(f"System: {context['system']}")
            if "history" in context:
                prompt_parts.append(f"History: {context['history']}")

        prompt_parts.append(f"Task: {task}")

        return "\n\n".join(prompt_parts)


class CustomAgentAdapter(AgentAdapter):
    """
    Adapter for custom agent implementations.
    Allows developers to wrap any agent implementation.
    """

    def __init__(
        self,
        agent_id: str,
        agent_instance: Any,
        execute_method: str = "execute",
        capabilities: Optional[List[AgentCapability]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize custom agent adapter.

        Args:
            agent_id: Unique identifier for the agent
            agent_instance: The custom agent instance
            execute_method: Name of the execute method on the agent
            capabilities: List of agent capabilities
            config: Optional configuration
        """
        super().__init__(agent_id, config)
        self.agent_instance = agent_instance
        self.execute_method = execute_method
        self.capabilities = capabilities or [AgentCapability.TEXT_GENERATION]

    async def initialize(self) -> bool:
        """Initialize the custom agent."""
        try:
            if hasattr(self.agent_instance, "initialize"):
                if asyncio.iscoroutinefunction(self.agent_instance.initialize):
                    await self.agent_instance.initialize()
                else:
                    self.agent_instance.initialize()
            self._initialized = True
            logger.info(f"Initialized custom agent adapter for {self.agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize custom agent: {e}")
            return False

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Execute a task with the custom agent."""
        if not self._initialized:
            return {"status": "error", "error": "Adapter not initialized"}

        try:
            execute_func = getattr(self.agent_instance, self.execute_method, None)
            if not execute_func:
                return {
                    "status": "error",
                    "error": f"Method {self.execute_method} not found on agent",
                }

            # Try to call the execute method
            if asyncio.iscoroutinefunction(execute_func):
                result = await execute_func(task, context=context, **kwargs)
            else:
                result = execute_func(task, context=context, **kwargs)

            return {
                "status": "success",
                "output": result,
                "agent_id": self.agent_id,
            }
        except Exception as e:
            logger.error(f"Error executing task with custom agent: {e}")
            return {"status": "error", "error": str(e)}

    async def communicate(
        self,
        message: str,
        recipient_id: Optional[str] = None,
        message_type: str = "request",
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a message through the custom agent."""
        if hasattr(self.agent_instance, "send_message"):
            send_func = self.agent_instance.send_message
            if asyncio.iscoroutinefunction(send_func):
                return await send_func(message, recipient_id, message_type, **kwargs)
            else:
                return send_func(message, recipient_id, message_type, **kwargs)

        # Default message formatting
        return {
            "status": "formatted",
            "message": {
                "from": self.agent_id,
                "to": recipient_id or "broadcast",
                "type": message_type,
                "content": message,
            },
        }

    async def get_capabilities(self) -> List[AgentCapability]:
        """Get custom agent capabilities."""
        return self.capabilities

    async def health_check(self) -> Dict[str, Any]:
        """Check custom agent health."""
        if hasattr(self.agent_instance, "health_check"):
            health_func = self.agent_instance.health_check
            if asyncio.iscoroutinefunction(health_func):
                return await health_func()
            else:
                return health_func()

        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "agent_id": self.agent_id,
            "capabilities": [cap.value for cap in self.capabilities],
        }


class AgentAdapterRegistry:
    """
    Registry for managing agent adapters.
    Allows registration, lookup, and management of agent adapters.
    """

    def __init__(self) -> None:
        """Initialize the adapter registry."""
        self.adapters: Dict[str, AgentAdapter] = {}
        self.adapter_types: Dict[str, Type[AgentAdapter]] = {
            "standard_llm": StandardLLMAdapter,
            "custom": CustomAgentAdapter,
        }
        logger.info("Agent adapter registry initialized")

    def register_adapter_type(self, type_name: str, adapter_class: Type[AgentAdapter]) -> None:
        """
        Register a new adapter type.

        Args:
            type_name: Name for the adapter type
            adapter_class: Adapter class
        """
        self.adapter_types[type_name] = adapter_class
        logger.info(f"Registered adapter type: {type_name}")

    async def register_adapter(self, adapter: AgentAdapter, auto_initialize: bool = True) -> bool:
        """
        Register an agent adapter.

        Args:
            adapter: Agent adapter to register
            auto_initialize: Whether to initialize the adapter automatically

        Returns:
            True if registration was successful
        """
        if adapter.agent_id in self.adapters:
            logger.warning(f"Adapter {adapter.agent_id} already registered, replacing")

        if auto_initialize and not adapter._initialized:
            success = await adapter.initialize()
            if not success:
                logger.error(f"Failed to initialize adapter {adapter.agent_id}")
                return False

        self.adapters[adapter.agent_id] = adapter
        logger.info(f"Registered adapter: {adapter.agent_id}")
        return True

    def get_adapter(self, agent_id: str) -> Optional[AgentAdapter]:
        """
        Get an adapter by agent ID.

        Args:
            agent_id: ID of the agent

        Returns:
            Agent adapter or None if not found
        """
        return self.adapters.get(agent_id)

    def unregister_adapter(self, agent_id: str) -> bool:
        """
        Unregister an adapter.

        Args:
            agent_id: ID of the agent to unregister

        Returns:
            True if adapter was unregistered
        """
        if agent_id in self.adapters:
            del self.adapters[agent_id]
            logger.info(f"Unregistered adapter: {agent_id}")
            return True
        return False

    def list_adapters(self) -> List[str]:
        """
        List all registered adapter IDs.

        Returns:
            List of adapter IDs
        """
        return list(self.adapters.keys())

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all adapters.

        Returns:
            Dictionary mapping agent IDs to health status
        """
        health_statuses = {}
        for agent_id, adapter in self.adapters.items():
            try:
                status = await adapter.health_check()
                health_statuses[agent_id] = status
            except Exception as e:
                health_statuses[agent_id] = {
                    "status": "error",
                    "error": str(e),
                }
        return health_statuses


# Import asyncio for async checks
