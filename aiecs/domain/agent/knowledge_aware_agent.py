"""
Knowledge-Aware Agent

Enhanced hybrid agent with knowledge graph integration.
Extends the standard HybridAgent with graph reasoning capabilities.
"""

import logging
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING
from datetime import datetime

from aiecs.llm import BaseLLMClient
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.tools.knowledge_graph import GraphReasoningTool
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.tools.base_tool import BaseTool

from .hybrid_agent import HybridAgent
from .models import AgentConfiguration

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol
    from aiecs.domain.agent.integration.protocols import (
        ConfigManagerProtocol,
        CheckpointerProtocol,
    )

logger = logging.getLogger(__name__)


class KnowledgeAwareAgent(HybridAgent):
    """
    Knowledge-Aware Agent with integrated knowledge graph reasoning.

    Extends HybridAgent with:
    - Knowledge graph consultation during reasoning
    - Graph-aware tool selection
    - Knowledge-augmented prompt construction
    - Automatic access to graph reasoning capabilities

    Example with tool names (backward compatible):
        ```python
        from aiecs.domain.agent import KnowledgeAwareAgent
        from aiecs.infrastructure.graph_storage import InMemoryGraphStore

        # Initialize with knowledge graph
        graph_store = InMemoryGraphStore()
        await graph_store.initialize()

        agent = KnowledgeAwareAgent(
            agent_id="kg_agent_001",
            name="Knowledge Assistant",
            llm_client=llm_client,
            tools=["web_search", "calculator"],
            config=config,
            graph_store=graph_store
        )

        await agent.initialize()
        result = await agent.execute_task("How is Alice connected to Company X?")
        ```

    Example with tool instances (new flexibility):
        ```python
        # Pre-configured tools with state
        agent = KnowledgeAwareAgent(
            agent_id="kg_agent_001",
            name="Knowledge Assistant",
            llm_client=llm_client,
            tools={
                "web_search": WebSearchTool(api_key="..."),
                "calculator": CalculatorTool()
            },
            config=config,
            graph_store=graph_store
        )
        ```
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_client: Union[BaseLLMClient, "LLMClientProtocol"],
        tools: Union[List[str], Dict[str, BaseTool]],
        config: AgentConfiguration,
        graph_store: Optional[GraphStore] = None,
        description: Optional[str] = None,
        version: str = "1.0.0",
        max_iterations: int = 10,
        enable_graph_reasoning: bool = True,
        config_manager: Optional["ConfigManagerProtocol"] = None,
        checkpointer: Optional["CheckpointerProtocol"] = None,
    ):
        """
        Initialize Knowledge-Aware agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            llm_client: LLM client for reasoning (BaseLLMClient or any LLMClientProtocol)
            tools: Tools - either list of tool names or dict of tool instances
                   (graph_reasoning auto-added if graph_store provided and tools is a list)
            config: Agent configuration
            graph_store: Optional knowledge graph store
            description: Optional description
            version: Agent version
            max_iterations: Maximum ReAct iterations
            enable_graph_reasoning: Whether to enable graph reasoning capabilities
            config_manager: Optional configuration manager for dynamic config
            checkpointer: Optional checkpointer for state persistence

        Note:
            When using tool instances (Dict[str, BaseTool]), graph_reasoning tool
            is NOT auto-added. You must include it manually if needed:

            ```python
            tools = {
                "web_search": WebSearchTool(),
                "graph_reasoning": GraphReasoningTool(graph_store)
            }
            ```
        """
        # Auto-add graph_reasoning tool if graph_store is provided and tools is a list
        if graph_store is not None and enable_graph_reasoning and isinstance(tools, list):
            if "graph_reasoning" not in tools:
                tools = tools + ["graph_reasoning"]

        super().__init__(
            agent_id=agent_id,
            name=name,
            llm_client=llm_client,
            tools=tools,
            config=config,
            description=description or "Knowledge-aware agent with integrated graph reasoning",
            version=version,
            max_iterations=max_iterations,
            config_manager=config_manager,
            checkpointer=checkpointer,
        )

        self.graph_store = graph_store
        self.enable_graph_reasoning = enable_graph_reasoning
        self._graph_reasoning_tool: Optional[GraphReasoningTool] = None
        self._knowledge_context: Dict[str, Any] = {}

        logger.info(
            f"KnowledgeAwareAgent initialized: {agent_id} "
            f"with graph_store={'enabled' if graph_store else 'disabled'}"
        )

    async def _initialize(self) -> None:
        """Initialize Knowledge-Aware agent - setup graph tools and augmented prompts."""
        # Call parent initialization
        await super()._initialize()

        # Initialize graph reasoning tool if graph store is available
        if self.graph_store is not None and self.enable_graph_reasoning:
            try:
                self._graph_reasoning_tool = GraphReasoningTool(self.graph_store)
                logger.info(f"KnowledgeAwareAgent {self.agent_id} initialized graph reasoning")
            except Exception as e:
                logger.warning(f"Failed to initialize graph reasoning tool: {e}")

        # Rebuild system prompt with knowledge graph capabilities
        if self.graph_store is not None:
            self._system_prompt = self._build_kg_augmented_system_prompt()

        logger.info(f"KnowledgeAwareAgent {self.agent_id} initialized with enhanced capabilities")

    async def _shutdown(self) -> None:
        """Shutdown Knowledge-Aware agent."""
        # Clear knowledge context
        self._knowledge_context.clear()

        # Shutdown graph store if needed
        if self.graph_store is not None:
            try:
                await self.graph_store.close()
            except Exception as e:
                logger.warning(f"Error closing graph store: {e}")

        # Call parent shutdown
        await super()._shutdown()

        logger.info(f"KnowledgeAwareAgent {self.agent_id} shut down")

    def _build_kg_augmented_system_prompt(self) -> str:
        """
        Build knowledge graph-augmented system prompt.

        Returns:
            Enhanced system prompt with KG capabilities
        """
        base_prompt = super()._build_system_prompt()

        # Add knowledge graph capabilities section
        kg_section = """

KNOWLEDGE GRAPH CAPABILITIES:
You have access to an integrated knowledge graph that can help answer complex questions.

REASONING WITH KNOWLEDGE:
Your reasoning process now includes an automatic RETRIEVE phase:
1. RETRIEVE: Relevant knowledge is automatically fetched from the graph before each reasoning step
2. THOUGHT: You analyze the task considering retrieved knowledge
3. ACTION: Use tools or provide final answer
4. OBSERVATION: Review results and continue

Retrieved knowledge will be provided as:
RETRIEVED KNOWLEDGE:
- Entity: id (properties)
- Entity: id (properties)
...

When to use the 'graph_reasoning' tool:
- Multi-hop questions (e.g., "How is X connected to Y?")
- Relationship discovery (e.g., "Who knows people at Company Z?")
- Knowledge completion (e.g., "What do we know about Person A?")
- Evidence-based reasoning (multiple sources needed)

The 'graph_reasoning' tool supports these modes:
- query_plan: Plan complex query execution
- multi_hop: Find connections between entities
- inference: Apply logical inference rules
- full_reasoning: Complete reasoning pipeline with evidence synthesis

Use graph reasoning proactively when questions involve:
- Connections, relationships, or paths
- Multiple entities or complex queries
- Need for evidence from multiple sources
"""

        return base_prompt + kg_section

    async def _reason_with_graph(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Consult knowledge graph during reasoning.

        Args:
            query: Query to reason about
            context: Optional context for reasoning

        Returns:
            Reasoning results from knowledge graph
        """
        if self._graph_reasoning_tool is None:
            logger.warning("Graph reasoning tool not available")
            return {"error": "Graph reasoning not available"}

        try:
            # Use multi_hop mode by default for general queries
            from aiecs.tools.knowledge_graph.graph_reasoning_tool import (
                GraphReasoningInput,
                ReasoningModeEnum,
            )

            # Extract entity IDs from context if available
            start_entity_id = None
            target_entity_id = None
            if context:
                start_entity_id = context.get("start_entity_id")
                target_entity_id = context.get("target_entity_id")

            input_data = GraphReasoningInput(  # type: ignore[call-arg]
                mode=ReasoningModeEnum.MULTI_HOP,
                query=query,
                start_entity_id=start_entity_id,
                target_entity_id=target_entity_id,
                max_hops=3,
                synthesize_evidence=True,
                confidence_threshold=0.6,
            )

            result = await self._graph_reasoning_tool._execute(input_data)

            # Store knowledge context for later use
            self._knowledge_context[query] = {
                "answer": result.get("answer"),
                "confidence": result.get("confidence"),
                "evidence_count": result.get("evidence_count"),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return result

        except Exception as e:
            logger.error(f"Error in graph reasoning: {e}")
            return {"error": str(e)}

    async def _select_tools_with_graph_awareness(
        self, task: str, available_tools: List[str]
    ) -> List[str]:
        """
        Select tools with graph awareness.

        Prioritizes graph reasoning tool for knowledge-related queries.

        Args:
            task: Task description
            available_tools: Available tool names

        Returns:
            Selected tool names
        """
        # Keywords that suggest graph reasoning might be useful
        graph_keywords = [
            "connected",
            "connection",
            "relationship",
            "related",
            "knows",
            "works",
            "friend",
            "colleague",
            "partner",
            "how",
            "why",
            "who",
            "what",
            "which",
            "find",
            "discover",
            "explore",
            "trace",
        ]

        task_lower = task.lower()

        # Check if task involves knowledge graph queries
        uses_graph_keywords = any(keyword in task_lower for keyword in graph_keywords)

        # If graph reasoning is available and task seems graph-related,
        # prioritize it
        if uses_graph_keywords and "graph_reasoning" in available_tools:
            # Put graph_reasoning first
            selected = ["graph_reasoning"]
            # Add other tools
            selected.extend([t for t in available_tools if t != "graph_reasoning"])
            return selected

        return available_tools

    async def _augment_prompt_with_knowledge(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Augment prompt with relevant knowledge from graph.

        Args:
            task: Original task
            context: Optional context

        Returns:
            Augmented task with knowledge context
        """
        if self.graph_store is None or not self.enable_graph_reasoning:
            return task

        # Check if we have cached knowledge for similar queries
        relevant_knowledge = []
        for query, kg_context in self._knowledge_context.items():
            # Simple keyword matching (could be enhanced with embeddings)
            if any(word in task.lower() for word in query.lower().split()):
                confidence = kg_context.get("confidence", 0.0)
                relevant_knowledge.append(
                    f"- {query}: {kg_context['answer']} (confidence: {confidence:.2f})"
                )

        if relevant_knowledge:
            knowledge_section = "\n\nRELEVANT KNOWLEDGE FROM GRAPH:\n" + "\n".join(
                relevant_knowledge[:3]
            )
            return task + knowledge_section

        return task

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task with knowledge graph augmentation.

        Uses knowledge-augmented ReAct loop that includes a RETRIEVE phase.

        Args:
            task: Task specification with 'description' or 'prompt'
            context: Execution context

        Returns:
            Task execution result
        """
        # Extract task description
        task_description = task.get("description") or task.get("prompt") or task.get("task")
        if not task_description:
            return await super().execute_task(task, context)

        # Augment task with knowledge if available
        augmented_task_desc = await self._augment_prompt_with_knowledge(task_description, context)

        # If task seems graph-related, consult graph first
        if self.graph_store is not None and self.enable_graph_reasoning:
            # Check if this is a direct graph query
            graph_keywords = [
                "connected",
                "connection",
                "relationship",
                "knows",
                "works at",
            ]
            if any(keyword in task_description.lower() for keyword in graph_keywords):
                logger.info(f"Consulting knowledge graph for task: {task_description}")

                # Try graph reasoning
                graph_result = await self._reason_with_graph(augmented_task_desc, context)

                # If we got a good answer from the graph, use it
                if "answer" in graph_result and graph_result.get("confidence", 0) > 0.7:
                    return {
                        "success": True,
                        "output": graph_result["answer"],
                        "confidence": graph_result["confidence"],
                        "source": "knowledge_graph",
                        "evidence_count": graph_result.get("evidence_count", 0),
                        "reasoning_trace": graph_result.get("reasoning_trace", []),
                        "timestamp": datetime.utcnow().isoformat(),
                    }

        # Fall back to standard hybrid agent execution
        # This will use the overridden _react_loop with knowledge retrieval
        # Create modified task dict with augmented description
        augmented_task = task.copy()
        if "description" in task:
            augmented_task["description"] = augmented_task_desc
        elif "prompt" in task:
            augmented_task["prompt"] = augmented_task_desc
        elif "task" in task:
            augmented_task["task"] = augmented_task_desc

        return await super().execute_task(augmented_task, context)

    async def _react_loop(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute knowledge-augmented ReAct loop: Retrieve → Reason → Act → Observe.

        Extends the standard ReAct loop with a RETRIEVE phase that fetches
        relevant knowledge from the graph before each reasoning step.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary with 'final_answer', 'steps', 'iterations'
        """
        steps = []
        tool_calls_count = 0
        total_tokens = 0
        knowledge_retrievals = 0

        # Build initial messages
        from aiecs.llm import LLMMessage

        messages = self._build_initial_messages(task, context)

        for iteration in range(self._max_iterations):
            logger.debug(f"KnowledgeAwareAgent {self.agent_id} - ReAct iteration {iteration + 1}")

            # RETRIEVE: Get relevant knowledge from graph (if enabled)
            retrieved_knowledge = []
            if self.graph_store is not None and self.enable_graph_reasoning:
                try:
                    retrieved_knowledge = await self._retrieve_relevant_knowledge(
                        task, context, iteration
                    )

                    if retrieved_knowledge:
                        knowledge_retrievals += 1
                        knowledge_str = self._format_retrieved_knowledge(retrieved_knowledge)

                        steps.append(
                            {
                                "type": "retrieve",
                                "knowledge_count": len(retrieved_knowledge),
                                "content": (
                                    knowledge_str[:200] + "..."
                                    if len(knowledge_str) > 200
                                    else knowledge_str
                                ),
                                "iteration": iteration + 1,
                            }
                        )

                        # Add knowledge to messages
                        messages.append(
                            LLMMessage(
                                role="system",
                                content=f"RETRIEVED KNOWLEDGE:\n{knowledge_str}",
                            )
                        )
                except Exception as e:
                    logger.warning(f"Knowledge retrieval failed: {e}")

            # THINK: LLM reasons about next action
            response = await self.llm_client.generate_text(
                messages=messages,
                model=self._config.llm_model,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            )

            thought = response.content
            total_tokens += getattr(response, "total_tokens", 0)

            steps.append(
                {
                    "type": "thought",
                    "content": thought,
                    "iteration": iteration + 1,
                }
            )

            # Check if final answer
            if "FINAL ANSWER:" in thought:
                final_answer = self._extract_final_answer(thought)
                return {
                    "final_answer": final_answer,
                    "steps": steps,
                    "iterations": iteration + 1,
                    "tool_calls_count": tool_calls_count,
                    "knowledge_retrievals": knowledge_retrievals,
                    "total_tokens": total_tokens,
                }

            # Check if tool call
            if "TOOL:" in thought:
                # ACT: Execute tool
                try:
                    tool_info = self._parse_tool_call(thought)
                    tool_result = await self._execute_tool(
                        tool_info["tool"],
                        tool_info.get("operation"),
                        tool_info.get("parameters", {}),
                    )
                    tool_calls_count += 1

                    steps.append(
                        {
                            "type": "action",
                            "tool": tool_info["tool"],
                            "operation": tool_info.get("operation"),
                            "parameters": tool_info.get("parameters"),
                            "iteration": iteration + 1,
                        }
                    )

                    # OBSERVE: Add tool result to conversation
                    observation = f"OBSERVATION: Tool '{tool_info['tool']}' returned: {tool_result}"
                    steps.append(
                        {
                            "type": "observation",
                            "content": observation,
                            "iteration": iteration + 1,
                        }
                    )

                    # Add to messages for next iteration
                    messages.append(LLMMessage(role="assistant", content=thought))
                    messages.append(LLMMessage(role="user", content=observation))

                except Exception as e:
                    error_msg = f"OBSERVATION: Tool execution failed: {str(e)}"
                    steps.append(
                        {
                            "type": "observation",
                            "content": error_msg,
                            "iteration": iteration + 1,
                            "error": True,
                        }
                    )
                    messages.append(LLMMessage(role="assistant", content=thought))
                    messages.append(LLMMessage(role="user", content=error_msg))

            else:
                # LLM didn't provide clear action - treat as final answer
                return {
                    "final_answer": thought,
                    "steps": steps,
                    "iterations": iteration + 1,
                    "tool_calls_count": tool_calls_count,
                    "knowledge_retrievals": knowledge_retrievals,
                    "total_tokens": total_tokens,
                }

        # Max iterations reached
        logger.warning(f"KnowledgeAwareAgent {self.agent_id} reached max iterations")
        return {
            "final_answer": "Max iterations reached. Unable to complete task fully.",
            "steps": steps,
            "iterations": self._max_iterations,
            "tool_calls_count": tool_calls_count,
            "knowledge_retrievals": knowledge_retrievals,
            "total_tokens": total_tokens,
            "max_iterations_reached": True,
        }

    async def _retrieve_relevant_knowledge(
        self, task: str, context: Dict[str, Any], iteration: int
    ) -> List[Entity]:
        """
        Retrieve relevant knowledge for the current reasoning step.

        Args:
            task: Task description
            context: Context dictionary
            iteration: Current iteration number

        Returns:
            List of relevant entities
        """
        # Extract entity IDs or types from context
        context.get("entity_types")
        context.get("session_id", f"temp_{self.agent_id}")

        # Try to retrieve knowledge
        # For now, use a simple approach - could be enhanced with embeddings
        try:
            # Use vector search if query is provided (simplified)
            # In production, this would generate embeddings for the task

            # For iteration 0, retrieve general context
            # For later iterations, retrieve more specific knowledge
            # limit = 5 if iteration == 0 else 3  # Reserved for future use

            if hasattr(self, "_knowledge_context") and self._knowledge_context:
                # Get entities mentioned in previous knowledge
                for _, kg_ctx in self._knowledge_context.items():
                    # This is simplified - in production would extract entity
                    # IDs properly
                    pass

            # Placeholder: Return empty for now
            # In a full implementation, this would:
            # 1. Generate embedding for task
            # 2. Use vector_search on graph_store
            # 3. Filter by relevance
            # 4. Return top-k results

            return []

        except Exception as e:
            logger.error(f"Error retrieving knowledge: {e}")
            return []

    def _format_retrieved_knowledge(self, entities: List[Entity]) -> str:
        """
        Format retrieved knowledge entities for inclusion in prompt.

        Args:
            entities: List of entities retrieved from graph

        Returns:
            Formatted knowledge string
        """
        if not entities:
            return ""

        lines = []
        for entity in entities:
            entity_str = f"- {entity.entity_type}: {entity.id}"
            if entity.properties:
                props_str = ", ".join(f"{k}={v}" for k, v in entity.properties.items())
                entity_str += f" ({props_str})"
            lines.append(entity_str)

        return "\n".join(lines)

    def get_knowledge_context(self) -> Dict[str, Any]:
        """
        Get accumulated knowledge context.

        Returns:
            Dictionary of accumulated knowledge
        """
        return self._knowledge_context.copy()

    def clear_knowledge_context(self) -> None:
        """Clear accumulated knowledge context."""
        self._knowledge_context.clear()
        logger.debug(f"Cleared knowledge context for agent {self.agent_id}")
