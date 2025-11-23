"""
LLM Agent

Agent implementation powered by LLM for text generation and reasoning.
"""

import logging
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING, AsyncIterator
from datetime import datetime

from aiecs.llm import BaseLLMClient, LLMMessage

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration
from .exceptions import TaskExecutionError

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol
    from aiecs.domain.agent.integration.protocols import ConfigManagerProtocol

logger = logging.getLogger(__name__)


class LLMAgent(BaseAIAgent):
    """
    LLM-powered agent for text generation and reasoning.

    This agent uses an LLM client to process tasks and generate responses.

    **LLM Client Configuration:**
    - BaseLLMClient: Standard LLM clients (OpenAI, xAI, etc.)
    - Custom clients: Any object implementing LLMClientProtocol (duck typing)
    - No inheritance required: Custom clients work without BaseLLMClient

    Examples:
        # Example 1: Basic usage with standard client (backward compatible)
        agent = LLMAgent(
            agent_id="agent1",
            name="My LLM Agent",
            llm_client=OpenAIClient(),
            config=config
        )

        # Example 2: Custom LLM client without BaseLLMClient inheritance
        class CustomLLMClient:
            provider_name = "custom"

            def __init__(self, api_key: str):
                self.api_key = api_key
                self.call_count = 0

            async def generate_text(self, messages, **kwargs):
                self.call_count += 1
                # Custom implementation
                return LLMResponse(
                    content="Custom response",
                    provider="custom",
                    model="custom-model"
                )

            async def stream_text(self, messages, **kwargs):
                # Custom streaming
                tokens = ["Hello", " ", "world", "!"]
                for token in tokens:
                    yield token
                    await asyncio.sleep(0.1)

            async def close(self):
                # Cleanup
                pass

        agent = LLMAgent(
            agent_id="agent1",
            name="My LLM Agent",
            llm_client=CustomLLMClient(api_key="..."),  # Works without BaseLLMClient!
            config=config
        )

        # Example 3: LLM client wrapper with additional features
        class RetryLLMClient:
            provider_name = "retry_wrapper"

            def __init__(self, base_client, max_retries: int = 3):
                self.base_client = base_client
                self.max_retries = max_retries
                self.retry_count = 0

            async def generate_text(self, messages, **kwargs):
                for attempt in range(self.max_retries):
                    try:
                        return await self.base_client.generate_text(messages, **kwargs)
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise
                        self.retry_count += 1
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff

            async def stream_text(self, messages, **kwargs):
                async for token in self.base_client.stream_text(messages, **kwargs):
                    yield token

            async def close(self):
                await self.base_client.close()

        # Wrap existing client
        base_client = OpenAIClient()
        retry_client = RetryLLMClient(base_client, max_retries=3)

        agent = LLMAgent(
            agent_id="agent1",
            name="My LLM Agent",
            llm_client=retry_client,  # Custom wrapper with retry logic
            config=config
        )

        # Example 4: LLM client with caching
        class CachedLLMClient:
            provider_name = "cached_wrapper"

            def __init__(self, base_client):
                self.base_client = base_client
                self.cache = {}

            async def generate_text(self, messages, **kwargs):
                # Generate cache key
                cache_key = hash(str(messages) + str(kwargs))
                if cache_key in self.cache:
                    return self.cache[cache_key]

                # Call base client
                response = await self.base_client.generate_text(messages, **kwargs)
                self.cache[cache_key] = response
                return response

            async def stream_text(self, messages, **kwargs):
                # Streaming bypasses cache
                async for token in self.base_client.stream_text(messages, **kwargs):
                    yield token

            async def close(self):
                await self.base_client.close()

        cached_client = CachedLLMClient(OpenAIClient())

        agent = LLMAgent(
            agent_id="agent1",
            name="My LLM Agent",
            llm_client=cached_client,  # Cached client
            config=config
        )

        # Example 5: Streaming with custom client
        agent = LLMAgent(
            agent_id="agent1",
            name="My LLM Agent",
            llm_client=CustomLLMClient(api_key="..."),
            config=config
        )

        # Stream task execution
        async for event in agent.execute_task_streaming(task, context):
            if event['type'] == 'token':
                print(event['content'], end='', flush=True)
            elif event['type'] == 'result':
                print(f"\\nFinal result: {event['output']}")

        # Example 6: Full-featured agent with all options
        from aiecs.domain.context import ContextEngine
        from aiecs.domain.agent.models import ResourceLimits

        context_engine = ContextEngine()
        await context_engine.initialize()

        resource_limits = ResourceLimits(
            max_concurrent_tasks=5,
            max_tokens_per_minute=10000
        )

        agent = LLMAgent(
            agent_id="agent1",
            name="My LLM Agent",
            llm_client=RetryLLMClient(CachedLLMClient(OpenAIClient())),
            config=config,
            config_manager=DatabaseConfigManager(),
            checkpointer=RedisCheckpointer(),
            context_engine=context_engine,
            collaboration_enabled=True,
            agent_registry={"agent2": other_agent},
            learning_enabled=True,
            resource_limits=resource_limits
        )
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_client: Union[BaseLLMClient, "LLMClientProtocol"],
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        config_manager: Optional["ConfigManagerProtocol"] = None,
        checkpointer: Optional[Any] = None,
        context_engine: Optional[Any] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[Any] = None,
    ):
        """
        Initialize LLM agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            llm_client: LLM client instance (BaseLLMClient or any LLMClientProtocol)
            config: Agent configuration
            description: Optional description
            version: Agent version
            config_manager: Optional configuration manager for dynamic config
            checkpointer: Optional checkpointer for state persistence
            context_engine: Optional context engine for persistent storage
            collaboration_enabled: Enable collaboration features
            agent_registry: Registry of other agents for collaboration
            learning_enabled: Enable learning features
            resource_limits: Optional resource limits configuration

        Example with custom LLM client:
            ```python
            # Custom LLM client without BaseLLMClient inheritance
            class CustomLLMClient:
                provider_name = "custom"

                async def generate_text(self, messages, **kwargs):
                    # Custom implementation
                    return LLMResponse(...)

                async def stream_text(self, messages, **kwargs):
                    # Custom streaming
                    yield "token"

                async def close(self):
                    # Cleanup
                    pass

            agent = LLMAgent(
                agent_id="agent1",
                name="My LLM Agent",
                llm_client=CustomLLMClient(),  # Works without BaseLLMClient!
                config=config
            )
            ```

        Example with standard client (backward compatible):
            ```python
            agent = LLMAgent(
                agent_id="agent1",
                name="My LLM Agent",
                llm_client=OpenAIClient(),
                config=config
            )
            ```
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.CONVERSATIONAL,
            config=config,
            description=description or "LLM-powered conversational agent",
            version=version,
            llm_client=llm_client,  # type: ignore[arg-type]
            config_manager=config_manager,
            checkpointer=checkpointer,
            context_engine=context_engine,
            collaboration_enabled=collaboration_enabled,
            agent_registry=agent_registry,
            learning_enabled=learning_enabled,
            resource_limits=resource_limits,
        )

        # Store LLM client reference (from BaseAIAgent or local)
        self.llm_client = self._llm_client if self._llm_client else llm_client
        self._system_prompt: Optional[str] = None
        self._conversation_history: List[LLMMessage] = []

        logger.info(f"LLMAgent initialized: {agent_id} with client {self.llm_client.provider_name}")

    async def _initialize(self) -> None:
        """Initialize LLM agent - validate LLM client and build system prompt."""
        # Validate LLM client using BaseAIAgent helper
        self._validate_llm_client()

        # Build system prompt
        self._system_prompt = self._build_system_prompt()
        logger.debug(f"LLMAgent {self.agent_id} initialized with system prompt")

    async def _shutdown(self) -> None:
        """Shutdown LLM agent."""
        # Clear conversation history
        self._conversation_history.clear()

        # Close LLM client if it has a close method
        if hasattr(self.llm_client, "close"):
            await self.llm_client.close()

        logger.info(f"LLMAgent {self.agent_id} shut down")

    def _build_system_prompt(self) -> str:
        """Build system prompt from configuration."""
        parts = []

        if self._config.goal:
            parts.append(f"Goal: {self._config.goal}")

        if self._config.backstory:
            parts.append(f"Background: {self._config.backstory}")

        if self._config.domain_knowledge:
            parts.append(f"Domain Knowledge: {self._config.domain_knowledge}")

        if self._config.reasoning_guidance:
            parts.append(f"Reasoning Approach: {self._config.reasoning_guidance}")

        if not parts:
            return "You are a helpful AI assistant."

        return "\n\n".join(parts)

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using the LLM.

        Args:
            task: Task specification with 'description' or 'prompt'
            context: Execution context

        Returns:
            Execution result with 'output', 'reasoning', 'tokens_used'

        Raises:
            TaskExecutionError: If task execution fails
        """
        start_time = datetime.utcnow()

        try:
            # Extract task description
            task_description = task.get("description") or task.get("prompt") or task.get("task")
            if not task_description:
                raise TaskExecutionError(
                    "Task must contain 'description', 'prompt', or 'task' field",
                    agent_id=self.agent_id,
                )

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            # Build messages
            messages = self._build_messages(task_description, context)

            # Call LLM
            response = await self.llm_client.generate_text(
                messages=messages,
                model=self._config.llm_model,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            )

            # Extract result
            output = response.content

            # Store in conversation history if enabled
            if self._config.memory_enabled:
                self._conversation_history.append(LLMMessage(role="user", content=task_description))
                self._conversation_history.append(LLMMessage(role="assistant", content=output))

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Update metrics
            self.update_metrics(
                execution_time=execution_time,
                success=True,
                tokens_used=getattr(response, "total_tokens", None),
            )

            # Transition back to active
            self._transition_state(self.state.__class__.ACTIVE)
            self._current_task_id = None
            self.last_active_at = datetime.utcnow()

            return {
                "success": True,
                "output": output,
                "provider": response.provider,
                "model": response.model,
                "tokens_used": getattr(response, "total_tokens", None),
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Task execution failed for {self.agent_id}: {e}")

            # Update metrics for failure
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.update_metrics(execution_time=execution_time, success=False)

            # Transition to error state
            self._transition_state(self.state.__class__.ERROR)
            self._current_task_id = None

            raise TaskExecutionError(
                f"Task execution failed: {str(e)}",
                agent_id=self.agent_id,
                task_id=task.get("task_id"),
            )

    async def process_message(self, message: str, sender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an incoming message.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Returns:
            Response dictionary with 'response', 'tokens_used'
        """
        try:
            # Build task from message
            task = {
                "description": message,
                "task_id": f"msg_{datetime.utcnow().timestamp()}",
            }

            # Execute as task
            result = await self.execute_task(task, {"sender_id": sender_id})

            return {
                "response": result.get("output"),
                "tokens_used": result.get("tokens_used"),
                "timestamp": result.get("timestamp"),
            }

        except Exception as e:
            logger.error(f"Message processing failed for {self.agent_id}: {e}")
            raise

    async def execute_task_streaming(self, task: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a task with streaming LLM tokens.

        Args:
            task: Task specification with 'description' or 'prompt'
            context: Execution context

        Yields:
            Dict[str, Any]: Event dictionaries with streaming tokens and final result

        Example:
            ```python
            async for event in agent.execute_task_streaming(task, context):
                if event['type'] == 'token':
                    print(event['content'], end='', flush=True)
                elif event['type'] == 'result':
                    print(f"\\nTokens used: {event['tokens_used']}")
            ```
        """
        start_time = datetime.utcnow()

        try:
            # Extract task description
            task_description = task.get("description") or task.get("prompt") or task.get("task")
            if not task_description:
                yield {
                    "type": "error",
                    "error": "Task must contain 'description', 'prompt', or 'task' field",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            # Yield status
            yield {
                "type": "status",
                "status": "started",
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Build messages
            messages = self._build_messages(task_description, context)

            # Stream LLM response
            output_tokens = []
            async for token in self.llm_client.stream_text(  # type: ignore[attr-defined]
                messages=messages,
                model=self._config.llm_model,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            ):
                output_tokens.append(token)
                yield {
                    "type": "token",
                    "content": token,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Combine output
            output = "".join(output_tokens)

            # Store in conversation history if enabled
            if self._config.memory_enabled:
                self._conversation_history.append(LLMMessage(role="user", content=task_description))
                self._conversation_history.append(LLMMessage(role="assistant", content=output))

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Update metrics
            self.update_metrics(
                execution_time=execution_time,
                success=True,
                tokens_used=None,  # Token count not available in streaming mode
            )

            # Transition back to active
            self._transition_state(self.state.__class__.ACTIVE)
            self._current_task_id = None
            self.last_active_at = datetime.utcnow()

            # Yield final result
            yield {
                "type": "result",
                "success": True,
                "output": output,
                "provider": self.llm_client.provider_name,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Streaming task execution failed for {self.agent_id}: {e}")

            # Update metrics for failure
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.update_metrics(execution_time=execution_time, success=False)

            # Transition to error state
            self._transition_state(self.state.__class__.ERROR)
            self._current_task_id = None

            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def process_message_streaming(self, message: str, sender_id: Optional[str] = None) -> AsyncIterator[str]:
        """
        Process a message with streaming response.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Yields:
            str: Response text tokens

        Example:
            ```python
            async for token in agent.process_message_streaming("Hello!"):
                print(token, end='', flush=True)
            ```
        """
        try:
            # Build task from message
            task = {
                "description": message,
                "task_id": f"msg_{datetime.utcnow().timestamp()}",
            }

            # Stream task execution
            async for event in self.execute_task_streaming(task, {"sender_id": sender_id}):
                if event["type"] == "token":
                    yield event["content"]

        except Exception as e:
            logger.error(f"Streaming message processing failed for {self.agent_id}: {e}")
            raise

    def _build_messages(self, user_message: str, context: Dict[str, Any]) -> List[LLMMessage]:
        """
        Build LLM messages from task and context.

        Args:
            user_message: User message
            context: Context dictionary

        Returns:
            List of LLM messages
        """
        messages = []

        # Add system prompt
        if self._system_prompt:
            messages.append(LLMMessage(role="system", content=self._system_prompt))

        # Add conversation history if available and memory enabled
        if self._config.memory_enabled and self._conversation_history:
            # Limit history to prevent token overflow
            max_history = 10  # Keep last 10 exchanges
            messages.extend(self._conversation_history[-max_history:])

        # Add additional context if provided
        if context:
            context_str = self._format_context(context)
            if context_str:
                messages.append(
                    LLMMessage(
                        role="system",
                        content=f"Additional Context:\n{context_str}",
                    )
                )

        # Add user message
        messages.append(LLMMessage(role="user", content=user_message))

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string."""
        relevant_fields = []

        # Filter out internal fields
        for key, value in context.items():
            if not key.startswith("_") and value is not None:
                relevant_fields.append(f"{key}: {value}")

        return "\n".join(relevant_fields) if relevant_fields else ""

    def clear_conversation_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()
        logger.info(f"LLMAgent {self.agent_id} conversation history cleared")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return [{"role": msg.role, "content": msg.content} for msg in self._conversation_history]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMAgent":
        """
        Deserialize LLMAgent from dictionary.

        Note: LLM client must be provided separately as it cannot be serialized.

        Args:
            data: Dictionary representation

        Returns:
            LLMAgent instance
        """
        # This is a placeholder - actual implementation would require
        # providing the LLM client separately
        raise NotImplementedError("LLMAgent.from_dict requires LLM client to be provided separately. " "Use constructor instead.")
