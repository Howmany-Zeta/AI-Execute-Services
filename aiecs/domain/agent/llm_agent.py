"""
LLM Agent

Agent implementation powered by LLM for text generation and reasoning.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration
from .exceptions import TaskExecutionError, AgentInitializationError

logger = logging.getLogger(__name__)


class LLMAgent(BaseAIAgent):
    """
    LLM-powered agent for text generation and reasoning.

    This agent uses an LLM client to process tasks and generate responses.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_client: BaseLLMClient,
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
    ):
        """
        Initialize LLM agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            llm_client: LLM client instance
            config: Agent configuration
            description: Optional description
            version: Agent version
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.CONVERSATIONAL,
            config=config,
            description=description or "LLM-powered conversational agent",
            version=version,
        )
        
        self.llm_client = llm_client
        self._system_prompt: Optional[str] = None
        self._conversation_history: List[LLMMessage] = []

        logger.info(f"LLMAgent initialized: {agent_id} with client {llm_client.provider_name}")

    async def _initialize(self) -> None:
        """Initialize LLM agent."""
        # Build system prompt
        self._system_prompt = self._build_system_prompt()
        logger.debug(f"LLMAgent {self.agent_id} initialized with system prompt")

    async def _shutdown(self) -> None:
        """Shutdown LLM agent."""
        # Clear conversation history
        self._conversation_history.clear()
        
        # Close LLM client if it has a close method
        if hasattr(self.llm_client, 'close'):
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

    async def execute_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            task_description = task.get('description') or task.get('prompt') or task.get('task')
            if not task_description:
                raise TaskExecutionError(
                    "Task must contain 'description', 'prompt', or 'task' field",
                    agent_id=self.agent_id
                )

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get('task_id')

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
                tokens_used=getattr(response, 'total_tokens', None),
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
                "tokens_used": getattr(response, 'total_tokens', None),
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
                task_id=task.get('task_id')
            )

    async def process_message(
        self,
        message: str,
        sender_id: Optional[str] = None
    ) -> Dict[str, Any]:
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

    def _build_messages(
        self,
        user_message: str,
        context: Dict[str, Any]
    ) -> List[LLMMessage]:
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
                messages.append(LLMMessage(role="system", content=f"Additional Context:\n{context_str}"))

        # Add user message
        messages.append(LLMMessage(role="user", content=user_message))

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string."""
        relevant_fields = []
        
        # Filter out internal fields
        for key, value in context.items():
            if not key.startswith('_') and value is not None:
                relevant_fields.append(f"{key}: {value}")
        
        return "\n".join(relevant_fields) if relevant_fields else ""

    def clear_conversation_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()
        logger.info(f"LLMAgent {self.agent_id} conversation history cleared")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self._conversation_history
        ]

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
        raise NotImplementedError(
            "LLMAgent.from_dict requires LLM client to be provided separately. "
            "Use constructor instead."
        )

