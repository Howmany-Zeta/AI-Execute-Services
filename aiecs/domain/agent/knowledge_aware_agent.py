"""
Knowledge-Aware Agent

Enhanced hybrid agent with knowledge graph integration.
Extends the standard HybridAgent with graph reasoning capabilities.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING, Callable, Awaitable, AsyncIterator
from datetime import datetime

from aiecs.llm import BaseLLMClient
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.infrastructure.graph_storage.error_handling import (
    RetryHandler,
    GraphStoreConnectionError,
    GraphStoreQueryError,
    GraphStoreTimeoutError,
)
from aiecs.tools.knowledge_graph import GraphReasoningTool
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.tools.base_tool import BaseTool

from .hybrid_agent import HybridAgent
from .models import AgentConfiguration, GraphMetrics

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol
    from aiecs.domain.agent.integration.protocols import (
        ConfigManagerProtocol,
        CheckpointerProtocol,
    )
    from aiecs.application.knowledge_graph.search.hybrid_search import SearchMode

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
        context_engine: Optional[Any] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[Any] = None,
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
            context_engine: Optional context engine for persistent storage
            collaboration_enabled: Enable collaboration features
            agent_registry: Registry of other agents for collaboration
            learning_enabled: Enable learning features
            resource_limits: Optional resource limits configuration

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
            context_engine=context_engine,
            collaboration_enabled=collaboration_enabled,
            agent_registry=agent_registry,
            learning_enabled=learning_enabled,
            resource_limits=resource_limits,
        )

        self.graph_store = graph_store
        self.enable_graph_reasoning = enable_graph_reasoning
        self._graph_reasoning_tool: Optional[GraphReasoningTool] = None
        self._knowledge_context: Dict[str, Any] = {}
        self._query_intent_classifier: Optional[Any] = None  # Initialized in _initialize()
        self._hybrid_search: Optional[Any] = None  # Initialized in _initialize()
        self._entity_extractor: Optional[Any] = None  # Initialized in _initialize()
        self._entity_extraction_cache: Dict[str, List[Any]] = {}  # Cache for entity extraction results
        self._graph_cache: Optional[Any] = None  # Initialized in _initialize()

        # Cache metrics
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        # Graph metrics
        self._graph_metrics: GraphMetrics = GraphMetrics(
            min_graph_query_time=None,
            max_graph_query_time=None,
            last_reset_at=None
        )

        # Prometheus metrics (initialized lazily)
        self._prometheus_metrics: Optional[Dict[str, Any]] = None
        self._prometheus_enabled: bool = False

        # Context management configuration
        self._max_context_size: int = 50
        self._relevance_threshold: float = 0.3
        self._relevance_weight: float = 0.6
        self._recency_weight: float = 0.4

        # Retry handler for knowledge retrieval operations
        self._retry_handler: RetryHandler = RetryHandler(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
        )

        # Circuit breaker state
        self._circuit_breaker_failures: int = 0
        self._circuit_breaker_threshold: int = 5
        self._circuit_breaker_open: bool = False

        logger.info(f"KnowledgeAwareAgent initialized: {agent_id} " f"with graph_store={'enabled' if graph_store else 'disabled'}")

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

        # Initialize HybridSearchStrategy if graph store is available
        if self.graph_store is not None and self.enable_graph_reasoning:
            try:
                from aiecs.application.knowledge_graph.search.hybrid_search import HybridSearchStrategy

                self._hybrid_search = HybridSearchStrategy(self.graph_store)
                logger.info(f"KnowledgeAwareAgent {self.agent_id} initialized hybrid search strategy")
            except Exception as e:
                logger.warning(f"Failed to initialize hybrid search strategy: {e}")

        # Initialize query intent classifier if configured
        if self.graph_store is not None and self.enable_graph_reasoning:
            try:
                self._query_intent_classifier = self._create_query_intent_classifier()
                if self._query_intent_classifier is not None:
                    logger.info(f"KnowledgeAwareAgent {self.agent_id} initialized query intent classifier")
            except Exception as e:
                logger.warning(f"Failed to initialize query intent classifier: {e}")

        # Initialize LLMEntityExtractor if graph store is available
        if self.graph_store is not None and self.enable_graph_reasoning:
            try:
                from aiecs.application.knowledge_graph.extractors.llm_entity_extractor import LLMEntityExtractor

                # Use the agent's LLM client for entity extraction
                # Cast to LLMClientProtocol since BaseLLMClient implements the protocol
                from typing import cast
                from aiecs.llm.protocols import LLMClientProtocol
                llm_client_protocol = cast(LLMClientProtocol, self.llm_client)
                self._entity_extractor = LLMEntityExtractor(
                    schema=None,  # No schema constraint for now
                    llm_client=llm_client_protocol,
                    temperature=0.1,  # Low temperature for deterministic extraction
                    max_tokens=1000,
                )
                logger.info(f"KnowledgeAwareAgent {self.agent_id} initialized entity extractor")
            except Exception as e:
                logger.warning(f"Failed to initialize entity extractor: {e}")

        # Initialize GraphStoreCache if graph store is available and caching is enabled
        if self.graph_store is not None and self.enable_graph_reasoning:
            try:
                from aiecs.infrastructure.graph_storage.cache import GraphStoreCache, GraphStoreCacheConfig

                # Check if caching is enabled in config
                enable_caching = getattr(self._config, "enable_knowledge_caching", True)
                cache_ttl = getattr(self._config, "cache_ttl", 300)  # Default 5 minutes

                if enable_caching:
                    cache_config = GraphStoreCacheConfig(
                        enabled=True,
                        ttl=cache_ttl,
                        max_cache_size_mb=100,
                        redis_url=None,  # Use in-memory cache by default
                        key_prefix="knowledge:",
                    )
                    self._graph_cache = GraphStoreCache(cache_config)
                    await self._graph_cache.initialize()
                    logger.info(f"KnowledgeAwareAgent {self.agent_id} initialized graph cache (TTL: {cache_ttl}s)")
            except Exception as e:
                logger.warning(f"Failed to initialize graph cache: {e}")

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

    def _create_query_intent_classifier(self) -> Optional[Any]:
        """
        Create query intent classifier from configuration.

        Returns:
            QueryIntentClassifier instance or None if not configured
        """
        from aiecs.application.knowledge_graph.retrieval import QueryIntentClassifier
        from aiecs.llm import LLMClientFactory

        # Check if strategy selection LLM is configured
        config = self.get_config()
        if (
            config.strategy_selection_llm_provider is not None
            and config.strategy_selection_llm_provider.strip()
        ):
            try:
                # Resolve LLM client from provider name
                client = LLMClientFactory.get_client(
                    config.strategy_selection_llm_provider
                )
                # Cast to LLMClientProtocol since BaseLLMClient implements the protocol
                from typing import cast
                from aiecs.llm.protocols import LLMClientProtocol
                llm_client = cast(LLMClientProtocol, client) if client else None

                # Create classifier with custom client
                classifier = QueryIntentClassifier(
                    llm_client=llm_client,
                    enable_caching=True,
                )

                logger.info(
                    f"Created QueryIntentClassifier with provider: "
                    f"{config.strategy_selection_llm_provider}"
                )
                return classifier

            except Exception as e:
                logger.warning(
                    f"Failed to create QueryIntentClassifier with custom LLM: {e}, "
                    f"falling back to rule-based classification"
                )
                # Fall back to rule-based classifier (no LLM client)
                return QueryIntentClassifier(llm_client=None, enable_caching=True)
        else:
            # No custom LLM configured, use rule-based classifier
            logger.debug("No strategy selection LLM configured, using rule-based classification")
            return QueryIntentClassifier(llm_client=None, enable_caching=True)

    async def _reason_with_graph(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    async def _select_tools_with_graph_awareness(self, task: str, available_tools: List[str]) -> List[str]:
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

    async def _augment_prompt_with_knowledge(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
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
                timestamp = kg_context.get("timestamp")
                relevant_knowledge.append({
                    "query": query,
                    "answer": kg_context['answer'],
                    "confidence": confidence,
                    "timestamp": timestamp,
                })

        if relevant_knowledge:
            # Prioritize knowledge by confidence (relevance) and recency
            # Convert to (item, score) tuples for prioritization
            knowledge_items = []
            for item in relevant_knowledge:
                # Create a simple object with the required attributes
                class KnowledgeItem:
                    def __init__(self, data):
                        self.data = data
                        self.created_at = None
                        if data.get("timestamp"):
                            try:
                                from dateutil import parser  # type: ignore[import-untyped]
                                self.created_at = parser.parse(data["timestamp"])
                            except:
                                pass

                knowledge_items.append((KnowledgeItem(item), item["confidence"]))

            # Prioritize using our prioritization method
            prioritized = self._prioritize_knowledge_context(
                knowledge_items,
                relevance_weight=0.7,  # Favor relevance over recency for knowledge context
                recency_weight=0.3,
            )

            # Format top 3 prioritized items
            formatted_knowledge = []
            for kg_item, priority_score in prioritized[:3]:
                data = kg_item.data
                formatted_knowledge.append(
                    f"- {data['query']}: {data['answer']} (confidence: {data['confidence']:.2f})"
                )

            knowledge_section = "\n\nRELEVANT KNOWLEDGE FROM GRAPH:\n" + "\n".join(formatted_knowledge)
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

    async def execute_task_streaming(self, task: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute task with streaming knowledge graph events.

        Extends HybridAgent's streaming to include knowledge retrieval events.

        Args:
            task: Task specification with 'description' or 'prompt'
            context: Execution context

        Yields:
            Dict[str, Any]: Event dictionaries including knowledge events

        Event types:
            - 'knowledge_retrieval_started': Knowledge retrieval initiated
            - 'entity_extraction_completed': Entity extraction finished
            - 'knowledge_cache_hit': Cache hit occurred
            - 'knowledge_retrieval_completed': Knowledge retrieval finished
            - Plus all standard HybridAgent events (status, token, tool_call, etc.)
        """
        # Store event callback in context for _retrieve_relevant_knowledge to use
        events_queue = []

        async def event_callback(event: Dict[str, Any]):
            """Callback to collect knowledge events."""
            events_queue.append(event)

        # Add callback to context
        context_with_callback = context.copy()
        context_with_callback["_knowledge_event_callback"] = event_callback

        # Stream from parent class
        async for event in super().execute_task_streaming(task, context_with_callback):
            # Yield any queued knowledge events first
            while events_queue:
                yield events_queue.pop(0)

            # Then yield the main event
            yield event

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
                    # Get event callback from context if available
                    event_callback = context.get("_knowledge_event_callback")
                    retrieved_knowledge = await self._retrieve_relevant_knowledge(
                        task, context, iteration, event_callback
                    )

                    if retrieved_knowledge:
                        knowledge_retrievals += 1
                        knowledge_str = self._format_retrieved_knowledge(retrieved_knowledge)

                        steps.append(
                            {
                                "type": "retrieve",
                                "knowledge_count": len(retrieved_knowledge),
                                "content": (knowledge_str[:200] + "..." if len(knowledge_str) > 200 else knowledge_str),
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
        self,
        task: str,
        context: Dict[str, Any],
        iteration: int,
        event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> List[Entity]:
        """
        Retrieve relevant knowledge for the current reasoning step.

        Uses HybridSearchStrategy to retrieve relevant entities from the knowledge graph
        based on semantic similarity and graph structure.

        Implements retry logic with exponential backoff and circuit breaker pattern
        for resilience against transient failures.

        Args:
            task: Task description
            context: Context dictionary
            iteration: Current iteration number
            event_callback: Optional async callback for streaming events

        Returns:
            List of relevant entities
        """
        # Return empty if hybrid search not available
        if self._hybrid_search is None or self.graph_store is None:
            return []

        # Circuit breaker: if open, return empty results immediately
        if self._circuit_breaker_open:
            logger.warning(
                f"Circuit breaker is OPEN - skipping knowledge retrieval "
                f"(failures: {self._circuit_breaker_failures}/{self._circuit_breaker_threshold})"
            )
            return []

        # Start timing
        start_time = time.time()

        # Emit knowledge_retrieval_started event
        if event_callback:
            await event_callback({
                "type": "knowledge_retrieval_started",
                "query": task,
                "iteration": iteration,
                "timestamp": datetime.utcnow().isoformat(),
            })

        try:
            # Step 1: Extract entities from task description (with caching)
            # Check if seed entities are provided in context first
            seed_entity_ids = context.get("seed_entity_ids")
            if not seed_entity_ids:
                seed_entity_ids = await self._extract_seed_entities(task)

            # Emit entity_extraction_completed event
            if event_callback:
                await event_callback({
                    "type": "entity_extraction_completed",
                    "entity_ids": seed_entity_ids if seed_entity_ids else [],
                    "entity_count": len(seed_entity_ids) if seed_entity_ids else 0,
                    "timestamp": datetime.utcnow().isoformat(),
                })

            # Step 2: Determine retrieval strategy
            strategy = getattr(self._config, "retrieval_strategy", "hybrid")
            if "retrieval_strategy" in context:
                strategy = context["retrieval_strategy"]

            # Step 3: Check cache for this query
            cache_key = self._generate_cache_key("knowledge_retrieval", {"task": task, "strategy": strategy})
            cached_entities = await self._get_cached_knowledge(cache_key)
            if cached_entities is not None:
                logger.debug(f"Cache hit for knowledge retrieval (key: {cache_key})")
                self._cache_hits += 1

                # Emit knowledge_cache_hit event
                if event_callback:
                    await event_callback({
                        "type": "knowledge_cache_hit",
                        "cache_key": cache_key,
                        "entity_count": len(cached_entities),
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                # Update metrics
                self._update_graph_metrics(
                    query_time=time.time() - start_time,
                    entities_count=len(cached_entities),
                    strategy=strategy,
                    cache_hit=True,
                )

                # Emit knowledge_retrieval_completed event
                if event_callback:
                    await event_callback({
                        "type": "knowledge_retrieval_completed",
                        "entity_count": len(cached_entities),
                        "retrieval_time_ms": (time.time() - start_time) * 1000,
                        "cache_hit": True,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                return cached_entities

            # Cache miss - proceed with retrieval
            logger.debug(f"Cache miss for knowledge retrieval (key: {cache_key})")
            self._cache_misses += 1

            # Step 4: Configure search mode based on agent config
            from aiecs.application.knowledge_graph.search.hybrid_search import (
                HybridSearchConfig,
                SearchMode,
            )

            # Convert strategy to search mode
            search_mode = self._select_search_mode(strategy, task)

            # Step 5: Generate embedding for task description (not required for graph-only if we have seeds)
            query_embedding = None
            if search_mode != SearchMode.GRAPH_ONLY or not seed_entity_ids:
                # Need embedding for vector search or hybrid search, or if no seed entities for graph search
                query_embedding = await self._get_query_embedding(task)
                if not query_embedding and search_mode != SearchMode.GRAPH_ONLY:
                    logger.warning("Failed to generate query embedding, returning empty results")
                    return []
                elif not query_embedding and search_mode == SearchMode.GRAPH_ONLY and not seed_entity_ids:
                    logger.warning("Failed to generate query embedding and no seed entities available for graph search")
                    return []

            # Step 6: Create search configuration
            max_results = getattr(self._config, "max_context_size", 10)
            config = HybridSearchConfig(
                mode=search_mode,
                vector_weight=0.6,
                graph_weight=0.4,
                max_results=max_results,
                vector_threshold=0.0,
                max_graph_depth=2,
                expand_results=True,
                min_combined_score=0.0,
            )

            # Step 7: Execute hybrid search with retry logic
            async def _execute_search():
                """Execute search with retry support"""
                return await self._hybrid_search.search(
                    query_embedding=query_embedding,
                    config=config,
                    seed_entity_ids=seed_entity_ids if seed_entity_ids else None,
                )

            # Retry on connection, query, and timeout errors
            results = await self._retry_handler.execute(
                _execute_search,
                retry_on=[
                    GraphStoreConnectionError,
                    GraphStoreQueryError,
                    GraphStoreTimeoutError,
                ],
            )

            # Step 8: Extract entities from results
            entities = [entity for entity, score in results]

            logger.debug(
                f"Retrieved {len(entities)} entities using {search_mode.value} search "
                f"(iteration {iteration})"
            )

            # Reset circuit breaker on successful retrieval
            if self._circuit_breaker_failures > 0:
                logger.info(
                    f"Knowledge retrieval succeeded - resetting circuit breaker "
                    f"(was at {self._circuit_breaker_failures} failures)"
                )
                self._circuit_breaker_failures = 0

            # Step 9: Apply context prioritization and pruning
            # First prioritize by relevance + recency
            prioritized_entities = self._prioritize_knowledge_context(
                entities,
                relevance_weight=self._relevance_weight,
                recency_weight=self._recency_weight,
            )

            # Then prune to keep only the most relevant
            pruned_entities_with_scores = self._prune_knowledge_context(
                prioritized_entities,
                max_context_size=self._max_context_size,
                relevance_threshold=self._relevance_threshold,
                max_age_seconds=None,  # No age limit by default
            )

            # Extract entities from (Entity, score) tuples for caching
            pruned_entities = [
                entity if isinstance(entity, Entity) else entity[0]
                for entity in pruned_entities_with_scores
            ]

            logger.debug(
                f"Context management: {len(entities)} → {len(prioritized_entities)} prioritized → "
                f"{len(pruned_entities)} pruned"
            )

            # Step 10: Cache the pruned results
            await self._cache_knowledge(cache_key, pruned_entities)

            # Step 11: Update metrics
            query_time = time.time() - start_time
            self._update_graph_metrics(
                query_time=query_time,
                entities_count=len(pruned_entities),
                strategy=strategy,
                cache_hit=False,
            )

            # Emit knowledge_retrieval_completed event
            if event_callback:
                # Calculate average relevance score
                avg_score = 0.0
                if results:
                    avg_score = sum(score for _, score in results) / len(results)

                await event_callback({
                    "type": "knowledge_retrieval_completed",
                    "entity_count": len(pruned_entities),
                    "retrieval_time_ms": query_time * 1000,
                    "cache_hit": False,
                    "average_relevance_score": avg_score,
                    "timestamp": datetime.utcnow().isoformat(),
                })

            return pruned_entities

        except Exception as e:
            # Increment circuit breaker failure count
            self._circuit_breaker_failures += 1

            logger.error(
                f"Error retrieving knowledge (failure {self._circuit_breaker_failures}/"
                f"{self._circuit_breaker_threshold}): {e}",
                exc_info=True
            )

            # Open circuit breaker if threshold reached
            if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
                self._circuit_breaker_open = True
                logger.error(
                    f"Circuit breaker OPENED after {self._circuit_breaker_failures} consecutive failures. "
                    f"Knowledge retrieval will be disabled until manual reset."
                )

            # Fallback to empty results
            return []

    async def _get_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Generate embedding for query text.

        Args:
            query: Query text

        Returns:
            Embedding vector or None if generation fails
        """
        try:
            # Use LLM client to generate embeddings
            # Check if client supports embeddings (check both method existence and callability)
            if not hasattr(self.llm_client, "get_embeddings"):
                logger.warning(
                    f"LLM client ({type(self.llm_client).__name__}) does not support embeddings. "
                    f"Available methods: {[m for m in dir(self.llm_client) if not m.startswith('_')]}"
                )
                return None
            
            # Verify the method is callable
            get_embeddings_method = getattr(self.llm_client, "get_embeddings", None)
            if not callable(get_embeddings_method):
                logger.warning(
                    f"LLM client ({type(self.llm_client).__name__}) has 'get_embeddings' attribute but it's not callable"
                )
                return None

            embeddings = await self.llm_client.get_embeddings(
                texts=[query],
                model=None,  # Use default embedding model
            )

            if embeddings and len(embeddings) > 0:
                return embeddings[0]

            return None

        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}", exc_info=True)
            return None

    async def _extract_seed_entities(self, task: str) -> List[str]:
        """
        Extract entities from task description to use as seed entities for graph traversal.

        Uses caching to avoid redundant LLM calls for the same task.

        Args:
            task: Task description

        Returns:
            List of entity IDs to use as seed entities
        """
        # Check cache first
        if task in self._entity_extraction_cache:
            cached_entities = self._entity_extraction_cache[task]
            logger.debug(f"Using cached entity extraction for task (found {len(cached_entities)} entities)")
            return [e.id for e in cached_entities]

        # Return empty if entity extractor not available
        if self._entity_extractor is None:
            logger.debug("Entity extractor not available, skipping entity extraction")
            return []

        try:
            # Extract entities from task description with timing
            extraction_start = time.time()
            entities = await self._entity_extractor.extract_entities(task)
            extraction_time = time.time() - extraction_start

            # Update extraction metrics
            self._graph_metrics.entity_extraction_count += 1
            self._graph_metrics.total_extraction_time += extraction_time
            self._graph_metrics.average_extraction_time = (
                self._graph_metrics.total_extraction_time / self._graph_metrics.entity_extraction_count
            )

            # Record to Prometheus if enabled
            if self._prometheus_enabled and self._prometheus_metrics is not None:
                try:
                    self._prometheus_metrics["entity_extraction_total"].labels(
                        agent_id=self.agent_id,
                    ).inc()
                    self._prometheus_metrics["entity_extraction_duration"].labels(
                        agent_id=self.agent_id,
                    ).observe(extraction_time)
                except Exception as e:
                    logger.warning(f"Failed to record entity extraction Prometheus metrics: {e}")

            # Cache the results
            self._entity_extraction_cache[task] = entities

            # Convert to entity IDs
            entity_ids = [e.id for e in entities]

            if entity_ids:
                logger.debug(f"Extracted {len(entity_ids)} seed entities from task: {entity_ids[:5]} (took {extraction_time:.3f}s)")
            else:
                logger.debug("No entities extracted from task")

            return entity_ids

        except Exception as e:
            logger.warning(f"Failed to extract entities from task: {e}")
            return []

    def _select_search_mode(self, strategy: str, task: str) -> "SearchMode":
        """
        Select search mode based on retrieval strategy and task analysis.

        Supports automatic strategy selection based on query keywords when strategy is "auto".

        Args:
            strategy: Retrieval strategy ("vector", "graph", "hybrid", or "auto")
            task: Task description for auto-selection analysis

        Returns:
            SearchMode enum value
        """
        from aiecs.application.knowledge_graph.search.hybrid_search import SearchMode

        # Handle explicit strategies
        if strategy == "vector":
            return SearchMode.VECTOR_ONLY
        elif strategy == "graph":
            return SearchMode.GRAPH_ONLY
        elif strategy == "hybrid":
            return SearchMode.HYBRID
        elif strategy == "auto":
            # Auto-select based on task analysis
            return self._auto_select_search_mode(task)
        else:
            # Default to hybrid for unknown strategies
            logger.warning(f"Unknown retrieval strategy '{strategy}', defaulting to hybrid")
            return SearchMode.HYBRID

    def _auto_select_search_mode(self, task: str) -> "SearchMode":
        """
        Automatically select search mode based on task analysis.

        Uses keyword matching to determine the most appropriate search mode:
        - Relationship/connection keywords → GRAPH mode
        - Semantic/conceptual keywords → VECTOR mode
        - Default → HYBRID mode

        Args:
            task: Task description

        Returns:
            SearchMode enum value
        """
        from aiecs.application.knowledge_graph.search.hybrid_search import SearchMode

        task_lower = task.lower()

        # Keywords indicating graph traversal is preferred
        graph_keywords = [
            "related", "connected", "relationship", "link", "path", "neighbor",
            "upstream", "downstream", "dependency", "depends on", "used by",
            "parent", "child", "ancestor", "descendant", "connected to"
        ]

        # Keywords indicating semantic search is preferred
        vector_keywords = [
            "similar", "like", "about", "concept", "topic", "meaning",
            "semantic", "understand", "explain", "describe", "what is"
        ]

        # Check for graph keywords
        if any(keyword in task_lower for keyword in graph_keywords):
            logger.debug(f"Auto-selected GRAPH mode based on task keywords")
            return SearchMode.GRAPH_ONLY

        # Check for vector keywords
        if any(keyword in task_lower for keyword in vector_keywords):
            logger.debug(f"Auto-selected VECTOR mode based on task keywords")
            return SearchMode.VECTOR_ONLY

        # Default to hybrid mode
        logger.debug(f"Auto-selected HYBRID mode (default)")
        return SearchMode.HYBRID

    def _generate_cache_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Generate cache key for knowledge retrieval.

        Overrides base class method to handle knowledge retrieval cache keys.
        Expects parameters dict with 'task' and 'strategy' keys.

        Args:
            tool_name: Name of the tool (unused for knowledge retrieval)
            parameters: Tool parameters dict containing 'task' and 'strategy'

        Returns:
            Cache key string
        """
        import hashlib

        # Extract task and strategy from parameters
        task = parameters.get("task", "")
        strategy = parameters.get("strategy", "")

        # Create hash of task description
        task_hash = hashlib.md5(task.encode()).hexdigest()[:16]

        # Combine with strategy
        cache_key = f"knowledge:{task_hash}:{strategy}"

        return cache_key

    async def _get_cached_knowledge(self, cache_key: str) -> Optional[List[Entity]]:
        """
        Get cached knowledge retrieval results.

        Args:
            cache_key: Cache key

        Returns:
            List of cached entities or None if not cached
        """
        if self._graph_cache is None or not self._graph_cache._initialized:
            return None

        try:
            # Get from cache
            cached_data = await self._graph_cache.backend.get(cache_key)
            if cached_data is None:
                return None

            # Deserialize entities
            import json
            entity_dicts = json.loads(cached_data)

            # Convert back to Entity objects
            entities = []
            for entity_dict in entity_dicts:
                entity = Entity(
                    id=entity_dict["id"],
                    entity_type=entity_dict["entity_type"],
                    properties=entity_dict.get("properties", {}),
                    embedding=entity_dict.get("embedding"),
                )
                entities.append(entity)

            return entities

        except Exception as e:
            logger.warning(f"Failed to get cached knowledge: {e}")
            return None

    async def _cache_knowledge(self, cache_key: str, entities: List[Entity]) -> None:
        """
        Cache knowledge retrieval results.

        Args:
            cache_key: Cache key
            entities: Entities to cache
        """
        if self._graph_cache is None or not self._graph_cache._initialized:
            return

        try:
            # Serialize entities to JSON
            import json
            entity_dicts = []
            for entity in entities:
                entity_dict = {
                    "id": entity.id,
                    "entity_type": entity.entity_type,
                    "properties": entity.properties,
                    "embedding": entity.embedding,
                }
                entity_dicts.append(entity_dict)

            cached_data = json.dumps(entity_dicts)

            # Store in cache with TTL
            ttl = getattr(self._config, "cache_ttl", 300)
            await self._graph_cache.backend.set(cache_key, cached_data, ttl)

            logger.debug(f"Cached {len(entities)} entities (key: {cache_key}, TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"Failed to cache knowledge: {e}")

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

    def _update_graph_metrics(
        self,
        query_time: float,
        entities_count: int,
        strategy: str,
        cache_hit: bool,
        relationships_count: int = 0,
    ) -> None:
        """
        Update graph metrics after a retrieval operation.

        Args:
            query_time: Time taken for the query in seconds
            entities_count: Number of entities retrieved
            strategy: Retrieval strategy used
            cache_hit: Whether this was a cache hit
            relationships_count: Number of relationships traversed
        """
        # Update query counts
        self._graph_metrics.total_graph_queries += 1
        self._graph_metrics.total_entities_retrieved += entities_count
        self._graph_metrics.total_relationships_traversed += relationships_count

        # Update timing metrics
        self._graph_metrics.total_graph_query_time += query_time
        self._graph_metrics.average_graph_query_time = (
            self._graph_metrics.total_graph_query_time / self._graph_metrics.total_graph_queries
        )

        # Update min/max query times
        if self._graph_metrics.min_graph_query_time is None or query_time < self._graph_metrics.min_graph_query_time:
            self._graph_metrics.min_graph_query_time = query_time
        if self._graph_metrics.max_graph_query_time is None or query_time > self._graph_metrics.max_graph_query_time:
            self._graph_metrics.max_graph_query_time = query_time

        # Update cache metrics
        if cache_hit:
            self._graph_metrics.cache_hits += 1
        else:
            self._graph_metrics.cache_misses += 1

        total_cache_requests = self._graph_metrics.cache_hits + self._graph_metrics.cache_misses
        if total_cache_requests > 0:
            self._graph_metrics.cache_hit_rate = self._graph_metrics.cache_hits / total_cache_requests

        # Update strategy counts
        strategy_lower = strategy.lower()
        if "vector" in strategy_lower:
            self._graph_metrics.vector_search_count += 1
        elif "graph" in strategy_lower:
            self._graph_metrics.graph_search_count += 1
        elif "hybrid" in strategy_lower:
            self._graph_metrics.hybrid_search_count += 1

        # Update timestamp
        self._graph_metrics.updated_at = datetime.utcnow()

        # Record to Prometheus if enabled
        self._record_prometheus_metrics(
            query_time=query_time,
            entities_count=entities_count,
            strategy=strategy,
            cache_hit=cache_hit,
        )

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

    def _prune_knowledge_context(
        self,
        entities: List[Any],
        max_context_size: int = 50,
        relevance_threshold: float = 0.3,
        max_age_seconds: Optional[int] = None,
    ) -> List[Any]:
        """
        Prune knowledge context based on relevance and recency.

        This method filters entities to keep only the most relevant and recent ones,
        preventing context overflow and improving retrieval quality.

        Args:
            entities: List of (Entity, score) tuples from retrieval
            max_context_size: Maximum number of entities to keep
            relevance_threshold: Minimum relevance score (0.0-1.0)
            max_age_seconds: Maximum age in seconds (None = no age limit)

        Returns:
            Pruned list of (Entity, score) tuples
        """
        if not entities:
            return []

        pruned = []
        current_time = datetime.utcnow()

        for item in entities:
            # Handle both (Entity, score) tuples and Entity objects
            if isinstance(item, tuple):
                entity, score = item
            else:
                entity = item
                score = 1.0  # Default score if not provided

            # Filter by relevance score
            if score < relevance_threshold:
                continue

            # Filter by age if specified
            if max_age_seconds is not None:
                entity_age = None

                # Try to get timestamp from entity
                if hasattr(entity, 'updated_at') and entity.updated_at:
                    entity_age = (current_time - entity.updated_at).total_seconds()
                elif hasattr(entity, 'created_at') and entity.created_at:
                    entity_age = (current_time - entity.created_at).total_seconds()

                # Skip if too old
                if entity_age is not None and entity_age > max_age_seconds:
                    continue

            pruned.append((entity, score))

        # Sort by score descending and limit to max_context_size
        pruned.sort(key=lambda x: x[1], reverse=True)
        pruned = pruned[:max_context_size]

        logger.debug(
            f"Pruned knowledge context: {len(entities)} → {len(pruned)} entities "
            f"(threshold={relevance_threshold}, max_size={max_context_size})"
        )

        return pruned

    def _prioritize_knowledge_context(
        self,
        entities: List[Any],
        relevance_weight: float = 0.6,
        recency_weight: float = 0.4,
    ) -> List[Any]:
        """
        Prioritize knowledge context using hybrid scoring.

        Combines relevance scores with recency to determine the most important
        entities for the current context. More recent entities get a boost.

        Args:
            entities: List of (Entity, score) tuples from retrieval
            relevance_weight: Weight for relevance score (0.0-1.0)
            recency_weight: Weight for recency score (0.0-1.0)

        Returns:
            Prioritized list of (Entity, priority_score) tuples sorted by priority
        """
        if not entities:
            return []

        # Normalize weights
        total_weight = relevance_weight + recency_weight
        if total_weight == 0:
            total_weight = 1.0

        norm_relevance_weight = relevance_weight / total_weight
        norm_recency_weight = recency_weight / total_weight

        current_time = datetime.utcnow()
        prioritized = []

        # Find oldest and newest timestamps for normalization
        timestamps = []
        for item in entities:
            entity = item[0] if isinstance(item, tuple) else item

            if hasattr(entity, 'updated_at') and entity.updated_at:
                timestamps.append(entity.updated_at)
            elif hasattr(entity, 'created_at') and entity.created_at:
                timestamps.append(entity.created_at)

        # Calculate recency scores
        if timestamps:
            oldest_time = min(timestamps)
            newest_time = max(timestamps)
            time_range = (newest_time - oldest_time).total_seconds()

            # Avoid division by zero
            if time_range == 0:
                time_range = 1.0
        else:
            time_range = 1.0
            oldest_time = current_time

        for item in entities:
            # Handle both (Entity, score) tuples and Entity objects
            if isinstance(item, tuple):
                entity, relevance_score = item
            else:
                entity = item
                relevance_score = 1.0

            # Calculate recency score (0.0 = oldest, 1.0 = newest)
            recency_score = 0.5  # Default middle value

            if hasattr(entity, 'updated_at') and entity.updated_at:
                age_seconds = (newest_time - entity.updated_at).total_seconds()
                recency_score = 1.0 - (age_seconds / time_range) if time_range > 0 else 1.0
            elif hasattr(entity, 'created_at') and entity.created_at:
                age_seconds = (newest_time - entity.created_at).total_seconds()
                recency_score = 1.0 - (age_seconds / time_range) if time_range > 0 else 1.0

            # Combine scores with weights
            priority_score = (
                relevance_score * norm_relevance_weight +
                recency_score * norm_recency_weight
            )

            prioritized.append((entity, priority_score))

        # Sort by priority score descending
        prioritized.sort(key=lambda x: x[1], reverse=True)

        logger.debug(
            f"Prioritized {len(prioritized)} entities "
            f"(relevance_weight={norm_relevance_weight:.2f}, recency_weight={norm_recency_weight:.2f})"
        )

        return prioritized


    def get_cache_metrics(self) -> Dict[str, Any]:
        """
        Get knowledge cache metrics.

        Returns:
            Dictionary with cache statistics including:
            - cache_hits: Number of cache hits
            - cache_misses: Number of cache misses
            - total_requests: Total cache requests
            - hit_rate: Cache hit rate (0.0 to 1.0)
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "hit_rate_percentage": hit_rate * 100,
        }

    def reset_cache_metrics(self) -> None:
        """Reset cache metrics counters."""
        self._cache_hits = 0
        self._cache_misses = 0
        logger.debug(f"Reset cache metrics for agent {self.agent_id}")

    def get_graph_metrics(self) -> Dict[str, Any]:
        """
        Get knowledge graph retrieval metrics.

        Returns:
            Dictionary with graph metrics including:
            - Query counts and entity statistics
            - Performance metrics (timing)
            - Cache metrics
            - Strategy usage counts
            - Entity extraction metrics
        """
        return self._graph_metrics.model_dump()

    def reset_graph_metrics(self) -> None:
        """Reset graph metrics to initial state."""
        self._graph_metrics = GraphMetrics(
            min_graph_query_time=None,
            max_graph_query_time=None,
            last_reset_at=None
        )
        logger.debug(f"Reset graph metrics for agent {self.agent_id}")

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive agent status including cache metrics.

        Extends base agent status with knowledge graph cache metrics.

        Returns:
            Dictionary with comprehensive status information
        """
        # Get base status from parent
        status = super().get_comprehensive_status()

        # Add cache metrics
        status["cache_metrics"] = self.get_cache_metrics()

        # Add graph metrics
        status["graph_metrics"] = self.get_graph_metrics()

        # Add graph store status
        status["graph_store_enabled"] = self.graph_store is not None
        status["graph_reasoning_enabled"] = self.enable_graph_reasoning

        return status

    def initialize_prometheus_metrics(self) -> None:
        """
        Initialize Prometheus metrics for knowledge graph operations.

        Defines counters, histograms, and gauges for tracking graph queries,
        entity extraction, and cache performance.

        Note: This should be called after the global Prometheus registry is set up.
        """
        try:
            from prometheus_client import Counter, Histogram, Gauge

            self._prometheus_metrics = {
                # Graph query counters
                "knowledge_retrieval_total": Counter(
                    "knowledge_retrieval_total",
                    "Total number of knowledge graph queries",
                    ["agent_id", "strategy"],
                ),
                "knowledge_entities_retrieved": Counter(
                    "knowledge_entities_retrieved_total",
                    "Total number of entities retrieved from knowledge graph",
                    ["agent_id"],
                ),
                # Query latency histogram
                "knowledge_retrieval_duration": Histogram(
                    "knowledge_retrieval_duration_seconds",
                    "Knowledge graph query duration in seconds",
                    ["agent_id", "strategy"],
                    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                ),
                # Cache metrics
                "knowledge_cache_hit_rate": Gauge(
                    "knowledge_cache_hit_rate",
                    "Knowledge graph cache hit rate",
                    ["agent_id"],
                ),
                "knowledge_cache_hits": Counter(
                    "knowledge_cache_hits_total",
                    "Total number of cache hits",
                    ["agent_id"],
                ),
                "knowledge_cache_misses": Counter(
                    "knowledge_cache_misses_total",
                    "Total number of cache misses",
                    ["agent_id"],
                ),
                # Entity extraction metrics
                "entity_extraction_total": Counter(
                    "entity_extraction_total",
                    "Total number of entity extractions",
                    ["agent_id"],
                ),
                "entity_extraction_duration": Histogram(
                    "entity_extraction_duration_seconds",
                    "Entity extraction duration in seconds",
                    ["agent_id"],
                    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
                ),
            }

            self._prometheus_enabled = True
            logger.info(f"Prometheus metrics initialized for agent {self.agent_id}")

        except ImportError:
            logger.warning("prometheus_client not available, Prometheus metrics disabled")
            self._prometheus_enabled = False
        except Exception as e:
            logger.warning(f"Failed to initialize Prometheus metrics: {e}")
            self._prometheus_enabled = False

    def _record_prometheus_metrics(
        self,
        query_time: float,
        entities_count: int,
        strategy: str,
        cache_hit: bool,
        extraction_time: Optional[float] = None,
    ) -> None:
        """
        Record metrics to Prometheus.

        Args:
            query_time: Query execution time in seconds
            entities_count: Number of entities retrieved
            strategy: Retrieval strategy used
            cache_hit: Whether this was a cache hit
            extraction_time: Entity extraction time (if applicable)
        """
        if not self._prometheus_enabled or self._prometheus_metrics is None:
            return

        try:
            # Record query
            self._prometheus_metrics["knowledge_retrieval_total"].labels(
                agent_id=self.agent_id,
                strategy=strategy,
            ).inc()

            # Record entities retrieved
            self._prometheus_metrics["knowledge_entities_retrieved"].labels(
                agent_id=self.agent_id,
            ).inc(entities_count)

            # Record query duration
            self._prometheus_metrics["knowledge_retrieval_duration"].labels(
                agent_id=self.agent_id,
                strategy=strategy,
            ).observe(query_time)

            # Record cache metrics
            if cache_hit:
                self._prometheus_metrics["knowledge_cache_hits"].labels(
                    agent_id=self.agent_id,
                ).inc()
            else:
                self._prometheus_metrics["knowledge_cache_misses"].labels(
                    agent_id=self.agent_id,
                ).inc()

            # Update cache hit rate gauge
            total_requests = self._graph_metrics.cache_hits + self._graph_metrics.cache_misses
            if total_requests > 0:
                hit_rate = self._graph_metrics.cache_hits / total_requests
                self._prometheus_metrics["knowledge_cache_hit_rate"].labels(
                    agent_id=self.agent_id,
                ).set(hit_rate)

            # Record entity extraction if applicable
            if extraction_time is not None:
                self._prometheus_metrics["entity_extraction_total"].labels(
                    agent_id=self.agent_id,
                ).inc()
                self._prometheus_metrics["entity_extraction_duration"].labels(
                    agent_id=self.agent_id,
                ).observe(extraction_time)

        except Exception as e:
            logger.warning(f"Failed to record Prometheus metrics: {e}")

    def reset_circuit_breaker(self) -> None:
        """
        Manually reset the circuit breaker for knowledge retrieval.

        This allows knowledge retrieval to resume after persistent failures
        have been resolved.
        """
        if self._circuit_breaker_open:
            logger.info(
                f"Resetting circuit breaker (was at {self._circuit_breaker_failures} failures)"
            )
        self._circuit_breaker_open = False
        self._circuit_breaker_failures = 0

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get the current status of the circuit breaker.

        Returns:
            Dictionary with circuit breaker status information
        """
        return {
            "open": self._circuit_breaker_open,
            "failures": self._circuit_breaker_failures,
            "threshold": self._circuit_breaker_threshold,
            "status": "OPEN" if self._circuit_breaker_open else "CLOSED",
        }
