"""
Agent Integration Protocols

Defines Protocol interfaces for agent integrations to enable duck typing and flexible integration.
"""

from typing import Protocol, Dict, Any, Optional, runtime_checkable, List


@runtime_checkable
class ConfigManagerProtocol(Protocol):
    """
    Protocol for custom configuration managers.

    This protocol defines the interface for configuration managers that can
    provide dynamic configuration to agents from external sources (databases,
    config servers, environment variables, etc.).

    Example:
        ```python
        class DatabaseConfigManager:
            async def get_config(self, key: str, default: Any = None) -> Any:
                # Fetch from database
                return await db.get_config(key, default)

            async def set_config(self, key: str, value: Any) -> None:
                # Save to database
                await db.set_config(key, value)

            async def reload_config(self) -> None:
                # Refresh cache
                await db.refresh_cache()

        # Use with agents
        agent = HybridAgent(
            config_manager=DatabaseConfigManager(),
            ...
        )
        ```
    """

    async def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        ...

    async def set_config(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        ...

    async def reload_config(self) -> None:
        """
        Reload configuration from source.

        This method should refresh any cached configuration data.
        """
        ...


@runtime_checkable
class CheckpointerProtocol(Protocol):
    """
    Protocol for custom checkpointers.

    This protocol defines the interface for checkpointers that can save and
    load agent state for persistence and recovery. Compatible with LangGraph
    checkpointing patterns.

    Example:
        ```python
        class RedisCheckpointer:
            async def save_checkpoint(
                self,
                agent_id: str,
                session_id: str,
                checkpoint_data: Dict[str, Any]
            ) -> str:
                # Save to Redis
                checkpoint_id = str(uuid.uuid4())
                await redis.set(f"checkpoint:{checkpoint_id}", json.dumps(checkpoint_data))
                return checkpoint_id

            async def load_checkpoint(
                self,
                agent_id: str,
                session_id: str,
                checkpoint_id: Optional[str] = None
            ) -> Optional[Dict[str, Any]]:
                # Load from Redis
                if checkpoint_id:
                    data = await redis.get(f"checkpoint:{checkpoint_id}")
                    return json.loads(data) if data else None
                # Load latest
                return await self._load_latest(agent_id, session_id)

            async def list_checkpoints(
                self,
                agent_id: str,
                session_id: str
            ) -> list[str]:
                # List all checkpoint IDs
                return await redis.keys(f"checkpoint:{agent_id}:{session_id}:*")

        # Use with agents
        agent = HybridAgent(
            checkpointer=RedisCheckpointer(),
            ...
        )
        ```
    """

    async def save_checkpoint(self, agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]) -> str:
        """
        Save checkpoint and return checkpoint ID.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            checkpoint_data: Checkpoint data to save

        Returns:
            Checkpoint ID for later retrieval
        """
        ...

    async def load_checkpoint(self, agent_id: str, session_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            checkpoint_id: Specific checkpoint ID (loads latest if None)

        Returns:
            Checkpoint data or None if not found
        """
        ...

    async def list_checkpoints(self, agent_id: str, session_id: str) -> list[str]:
        """
        List all checkpoint IDs for a session.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier

        Returns:
            List of checkpoint IDs
        """
        ...


@runtime_checkable
class AgentCollaborationProtocol(Protocol):
    """
    Protocol for agent collaboration.

    This protocol defines the interface for agents that can collaborate with
    other agents through task delegation, peer review, and consensus-based
    decision making. Enables multi-agent workflows and distributed task execution.

    **Key Features:**
    - Task delegation to capable agents
    - Peer review of task results
    - Consensus-based decision making
    - Capability-based agent discovery
    - Multi-agent parallel execution

    **Required Attributes:**
    - agent_id: Unique identifier for the agent
    - name: Human-readable agent name
    - capabilities: List of capability strings (e.g., ["search", "analysis"])

    **Required Methods:**
    - execute_task: Execute a task and return result
    - review_result: Review another agent's task result

    Examples:
        # Example 1: Basic collaborative agent implementation
        class CollaborativeAgent(BaseAIAgent):
            agent_id: str
            name: str
            capabilities: List[str]

            async def execute_task(
                self, task: Dict[str, Any], context: Dict[str, Any]
            ) -> Dict[str, Any]:
                # Execute task
                return {"success": True, "output": "result"}

            async def review_result(
                self, task: Dict[str, Any], result: Dict[str, Any]
            ) -> Dict[str, Any]:
                # Review another agent's result
                return {"approved": True, "feedback": "Looks good"}

        # Example 2: Using with agent registry
        registry = {
            "agent1": CollaborativeAgent(
                agent_id="agent1",
                name="Search Agent",
                capabilities=["search", "web_scraping"]
            ),
            "agent2": CollaborativeAgent(
                agent_id="agent2",
                name="Analysis Agent",
                capabilities=["data_analysis", "statistics"]
            ),
        }

        agent = HybridAgent(
            collaboration_enabled=True,
            agent_registry=registry,
            ...
        )

        # Example 3: Delegate task to capable agent
        result = await agent.delegate_task(
            task_description="Search for recent AI papers",
            required_capabilities=["search"]
        )

        # Example 4: Request peer review
        review = await agent.request_peer_review(
            task=task,
            result=result,
            reviewer_agent_id="agent2"
        )

        # Example 5: Multi-agent collaboration
        result = await agent.collaborate_on_task(
            task=task,
            strategy="parallel",  # Execute in parallel
            required_capabilities=["search", "analysis"]
        )
    """

    agent_id: str
    name: str
    capabilities: List[str]

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task.

        Args:
            task: Task specification
            context: Execution context

        Returns:
            Task execution result
        """
        ...

    async def review_result(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review another agent's task result.

        Args:
            task: Original task specification
            result: Task execution result to review

        Returns:
            Review result with 'approved' (bool) and 'feedback' (str)
        """
        ...
