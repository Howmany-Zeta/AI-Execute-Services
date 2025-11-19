# Agent Domain API Reference

This document provides a comprehensive API reference for all agent domain classes, methods, and models.

## Table of Contents

1. [BaseAIAgent](#baseaiagent)
2. [Concrete Agent Types](#concrete-agent-types)
   - [LLMAgent](#llmagent)
   - [ToolAgent](#toolagent)
   - [HybridAgent](#hybridagent)
3. [ConversationMemory and Session](#conversationmemory-and-session)
4. [ContextEngine](#contextengine)
5. [Models and Configuration](#models-and-configuration)

---

## BaseAIAgent

Abstract base class for all AI agents providing core functionality for lifecycle management, state management, memory, goals, and metrics tracking.

**Module**: `aiecs.domain.agent.base_agent`

```python
from aiecs.domain.agent import BaseAIAgent
from aiecs.domain.agent.models import AgentType, AgentConfiguration

class BaseAIAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        name: str,
        agent_type: AgentType,
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        tools: Optional[Union[List[str], Dict[str, BaseTool]]] = None,
        llm_client: Optional[LLMClientProtocol] = None,
        config_manager: Optional[ConfigManagerProtocol] = None,
        checkpointer: Optional[CheckpointerProtocol] = None,
        context_engine: Optional[ContextEngine] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[ResourceLimits] = None,
    )
```

### Lifecycle Methods

#### `async initialize() -> None`

Initialize the agent and prepare it for use.

**Raises:**
- `AgentInitializationError`: If initialization fails

**Example:**
```python
agent = HybridAgent(...)
await agent.initialize()
```

#### `async activate() -> None`

Activate the agent, transitioning it to ACTIVE state.

**Raises:**
- `InvalidStateTransitionError`: If transition is invalid

#### `async deactivate() -> None`

Deactivate the agent, transitioning it to INACTIVE state.

#### `async shutdown() -> None`

Shutdown the agent, cleaning up resources.

### State Management

#### `state() -> AgentState`

Get current agent state (property).

**Returns:** `AgentState` - Current agent state

#### `get_state() -> AgentState`

Get current agent state.

**Returns:** `AgentState` - Current agent state

### Task Execution

#### `async execute_task(task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]`

Execute a task (abstract method, implemented by subclasses).

**Parameters:**
- `task` (Dict[str, Any]): Task specification
- `context` (Dict[str, Any]): Execution context

**Returns:** `Dict[str, Any]` - Task execution result

**Raises:**
- `TaskExecutionError`: If task execution fails

#### `async process_message(message: str, sender_id: Optional[str] = None) -> Dict[str, Any]`

Process an incoming message (abstract method, implemented by subclasses).

**Parameters:**
- `message` (str): Message content
- `sender_id` (Optional[str]): Optional sender identifier

**Returns:** `Dict[str, Any]` - Response dictionary

### Tool Execution

#### `async execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Any`

Execute a tool by name.

**Parameters:**
- `tool_name` (str): Name of the tool
- `parameters` (Dict[str, Any]): Tool parameters

**Returns:** `Any` - Tool execution result

**Raises:**
- `ToolAccessDeniedError`: If tool access is denied

#### `async execute_tools_parallel(tool_calls: List[Dict[str, Any]], max_concurrency: int = 5) -> List[Dict[str, Any]]`

Execute multiple tools in parallel with concurrency limit.

**Parameters:**
- `tool_calls` (List[Dict[str, Any]]): List of tool call dicts with 'tool_name' and 'parameters'
- `max_concurrency` (int): Maximum number of concurrent tool executions (default: 5)

**Returns:** `List[Dict[str, Any]]` - List of results in same order as tool_calls

**Example:**
```python
results = await agent.execute_tools_parallel([
    {"tool_name": "search", "parameters": {"query": "AI"}},
    {"tool_name": "calculator", "parameters": {"operation": "add", "a": 1, "b": 2}}
], max_concurrency=3)
```

#### `async execute_tool_with_cache(tool_name: str, parameters: Dict[str, Any]) -> Any`

Execute tool with caching support.

**Parameters:**
- `tool_name` (str): Name of the tool
- `parameters` (Dict[str, Any]): Tool parameters

**Returns:** `Any` - Tool result (from cache or fresh execution)

**Example:**
```python
result = await agent.execute_tool_with_cache("search", {"query": "AI"})
```

#### `invalidate_cache(tool_name: Optional[str] = None, pattern: Optional[str] = None) -> int`

Invalidate cache entries.

**Parameters:**
- `tool_name` (Optional[str]): Specific tool name to invalidate (None = all)
- `pattern` (Optional[str]): Pattern to match cache keys

**Returns:** `int` - Number of entries invalidated

#### `get_cache_stats() -> Dict[str, Any]`

Get cache statistics.

**Returns:** `Dict[str, Any]` - Cache statistics including size, hits, misses, hit_rate

### Streaming

#### `async execute_task_streaming(task: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]`

Execute task with streaming response.

**Parameters:**
- `task` (Dict[str, Any]): Task specification
- `context` (Dict[str, Any]): Execution context

**Yields:** `Dict[str, Any]` - Event dictionaries with type ('token', 'tool_call', 'tool_result', 'status', 'result', 'error')

**Example:**
```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'token':
        print(event['content'], end='', flush=True)
    elif event['type'] == 'tool_call':
        print(f"Calling {event['tool_name']}...")
```

#### `async process_message_streaming(message: str, sender_id: Optional[str] = None) -> AsyncIterator[str]`

Process a message with streaming response.

**Parameters:**
- `message` (str): Message content
- `sender_id` (Optional[str]): Optional sender identifier

**Yields:** `str` - Response text tokens/chunks

### Memory Management

#### `async add_to_memory(key: str, value: Any, memory_type: MemoryType = MemoryType.SHORT_TERM) -> None`

Add value to agent memory.

**Parameters:**
- `key` (str): Memory key
- `value` (Any): Value to store
- `memory_type` (MemoryType): Type of memory (default: SHORT_TERM)

#### `async retrieve_memory(key: str, default: Any = None) -> Any`

Retrieve value from agent memory.

**Parameters:**
- `key` (str): Memory key
- `default` (Any): Default value if key not found

**Returns:** `Any` - Stored value or default

#### `async clear_memory(memory_type: Optional[MemoryType] = None) -> None`

Clear agent memory.

**Parameters:**
- `memory_type` (Optional[MemoryType]): Type of memory to clear (None = all)

#### `get_memory_summary() -> Dict[str, Any]`

Get memory summary.

**Returns:** `Dict[str, Any]` - Memory summary with counts and sizes

### Goals Management

#### `set_goal(goal_id: str, description: str, priority: GoalPriority = GoalPriority.MEDIUM, deadline: Optional[datetime] = None) -> AgentGoal`

Set a goal for the agent.

**Parameters:**
- `goal_id` (str): Unique goal identifier
- `description` (str): Goal description
- `priority` (GoalPriority): Goal priority (default: MEDIUM)
- `deadline` (Optional[datetime]): Optional deadline

**Returns:** `AgentGoal` - Created goal object

#### `get_goals(status: Optional[GoalStatus] = None) -> List[AgentGoal]`

Get agent goals, optionally filtered by status.

**Parameters:**
- `status` (Optional[GoalStatus]): Filter by status (None = all)

**Returns:** `List[AgentGoal]` - List of goals

#### `get_goal(goal_id: str) -> Optional[AgentGoal]`

Get a specific goal by ID.

**Parameters:**
- `goal_id` (str): Goal identifier

**Returns:** `Optional[AgentGoal]` - Goal object or None

#### `update_goal_status(goal_id: str, status: GoalStatus, notes: Optional[str] = None) -> None`

Update goal status.

**Parameters:**
- `goal_id` (str): Goal identifier
- `status` (GoalStatus): New status
- `notes` (Optional[str]): Optional notes

### Configuration Management

#### `get_config() -> AgentConfiguration`

Get current agent configuration.

**Returns:** `AgentConfiguration` - Current configuration

#### `update_config(updates: Dict[str, Any]) -> None`

Update agent configuration.

**Parameters:**
- `updates` (Dict[str, Any]): Configuration updates

**Note:** Uses config manager if available, otherwise updates in-memory config

### Capabilities

#### `declare_capability(capability_type: str, description: str, level: CapabilityLevel = CapabilityLevel.BASIC) -> None`

Declare an agent capability.

**Parameters:**
- `capability_type` (str): Capability type
- `description` (str): Capability description
- `level` (CapabilityLevel): Capability level (default: BASIC)

#### `has_capability(capability_type: str) -> bool`

Check if agent has a capability.

**Parameters:**
- `capability_type` (str): Capability type

**Returns:** `bool` - True if agent has capability

#### `get_capabilities() -> List[AgentCapabilityDeclaration]`

Get all declared capabilities.

**Returns:** `List[AgentCapabilityDeclaration]` - List of capabilities

### Metrics and Performance

#### `get_metrics() -> AgentMetrics`

Get agent metrics.

**Returns:** `AgentMetrics` - Current metrics

#### `update_metrics(execution_time: Optional[float] = None, success: Optional[bool] = None, tokens_used: Optional[int] = None, tool_calls: Optional[int] = None) -> None`

Update agent metrics.

**Parameters:**
- `execution_time` (Optional[float]): Execution time in seconds
- `success` (Optional[bool]): Whether operation succeeded
- `tokens_used` (Optional[int]): Tokens used
- `tool_calls` (Optional[int]): Number of tool calls

#### `track_operation_time(operation_name: str) -> OperationTimer`

Track operation execution time (context manager).

**Parameters:**
- `operation_name` (str): Operation name

**Returns:** `OperationTimer` - Context manager for tracking

**Example:**
```python
with agent.track_operation_time("data_processing"):
    result = await agent.execute_task(task, context)
```

#### `get_performance_metrics() -> Dict[str, Any]`

Get performance metrics.

**Returns:** `Dict[str, Any]` - Performance metrics including avg_response_time, p95_response_time, p99_response_time, operation_metrics

#### `get_health_status() -> Dict[str, Any]`

Get agent health status.

**Returns:** `Dict[str, Any]` - Health status with score, status, issues, recommendations

#### `get_comprehensive_status() -> Dict[str, Any]`

Get comprehensive agent status.

**Returns:** `Dict[str, Any]` - Complete status including state, metrics, health, goals, capabilities

#### `reset_metrics() -> None`

Reset agent metrics.

### Serialization

#### `to_dict() -> Dict[str, Any]`

Serialize agent to dictionary.

**Returns:** `Dict[str, Any]` - Serialized agent data

#### `@classmethod from_dict(data: Dict[str, Any]) -> BaseAIAgent`

Deserialize agent from dictionary.

**Parameters:**
- `data` (Dict[str, Any]): Serialized agent data

**Returns:** `BaseAIAgent` - Deserialized agent instance

### Checkpointing

#### `async save_checkpoint(session_id: Optional[str] = None) -> Optional[str]`

Save agent state checkpoint.

**Parameters:**
- `session_id` (Optional[str]): Optional session ID

**Returns:** `Optional[str]` - Checkpoint ID if saved

**Raises:**
- `SerializationError`: If serialization fails

#### `async load_checkpoint(checkpoint_id: str) -> bool`

Load agent state from checkpoint.

**Parameters:**
- `checkpoint_id` (str): Checkpoint ID

**Returns:** `bool` - True if loaded successfully

**Raises:**
- `SerializationError`: If deserialization fails

### Agent Collaboration

#### `async delegate_task(task_description: str, target_agent_id: Optional[str] = None, required_capabilities: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

Delegate task to another agent.

**Parameters:**
- `task_description` (str): Task description
- `target_agent_id` (Optional[str]): Specific agent ID (None = auto-select)
- `required_capabilities` (Optional[List[str]]): Required capabilities
- `context` (Optional[Dict[str, Any]]): Additional context

**Returns:** `Dict[str, Any]` - Delegated task result

**Raises:**
- `ValueError`: If collaboration not enabled or agent not found

#### `async find_capable_agents(required_capabilities: List[str]) -> List[Any]`

Find agents with required capabilities.

**Parameters:**
- `required_capabilities` (List[str]): Required capabilities

**Returns:** `List[Any]` - List of capable agents

#### `async request_peer_review(task: Dict[str, Any], result: Dict[str, Any], reviewer_id: Optional[str] = None) -> Dict[str, Any]`

Request peer review of a task result.

**Parameters:**
- `task` (Dict[str, Any]): Original task specification
- `result` (Dict[str, Any]): Task execution result to review
- `reviewer_id` (Optional[str]): Specific reviewer agent ID (None = auto-select)

**Returns:** `Dict[str, Any]` - Review result with 'approved' (bool), 'feedback' (str), 'reviewer_id' (str)

**Raises:**
- `ValueError`: If collaboration not enabled or reviewer not found

#### `async collaborate_on_task(task: Dict[str, Any], strategy: str = "parallel", required_capabilities: Optional[List[str]] = None, agent_weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]`

Collaborate on task with multiple agents.

**Parameters:**
- `task` (Dict[str, Any]): Task specification
- `strategy` (str): Collaboration strategy ('parallel', 'sequential', 'consensus', 'weighted_consensus')
- `required_capabilities` (Optional[List[str]]): Required capabilities
- `agent_weights` (Optional[Dict[str, float]]): Agent weights for weighted consensus

**Returns:** `Dict[str, Any]` - Collaboration result

### Learning and Adaptation

#### `async record_experience(task: Dict[str, Any], result: Dict[str, Any], approach: str, tools_used: Optional[List[str]] = None) -> None`

Record an experience for learning and adaptation.

**Parameters:**
- `task` (Dict[str, Any]): Task specification
- `result` (Dict[str, Any]): Task execution result
- `approach` (str): Approach/strategy used
- `tools_used` (Optional[List[str]]): List of tools used

#### `async get_recommended_approach(task: Dict[str, Any]) -> Optional[Dict[str, Any]]`

Get recommended approach based on past experiences.

**Parameters:**
- `task` (Dict[str, Any]): Task specification

**Returns:** `Optional[Dict[str, Any]]` - Recommended approach with 'approach' (str), 'confidence' (float), 'experience_count' (int)

#### `async get_learning_insights() -> Dict[str, Any]`

Get learning insights from experiences.

**Returns:** `Dict[str, Any]` - Learning insights including successful_approaches, failed_approaches, recommendations

#### `async adapt_strategy(task: Dict[str, Any]) -> Dict[str, Any]`

Adapt strategy based on past experiences.

**Parameters:**
- `task` (Dict[str, Any]): Task specification

**Returns:** `Dict[str, Any]` - Adapted strategy

### Resource Management

#### `async check_resource_availability() -> Dict[str, Any]`

Check if resources are available for task execution.

**Returns:** `Dict[str, Any]` - Resource status with 'available' (bool), 'reason' (str), details

#### `async wait_for_resources(timeout: Optional[float] = None) -> bool`

Wait for resources to become available.

**Parameters:**
- `timeout` (Optional[float]): Maximum wait time in seconds (None = use default)

**Returns:** `bool` - True if resources became available

#### `async get_resource_usage() -> Dict[str, Any]`

Get current resource usage.

**Returns:** `Dict[str, Any]` - Resource usage statistics

### Error Recovery

#### `async execute_with_recovery(task: Dict[str, Any], context: Dict[str, Any], strategies: Optional[List[str]] = None) -> Dict[str, Any]`

Execute task with recovery strategies.

**Parameters:**
- `task` (Dict[str, Any]): Task specification
- `context` (Dict[str, Any]): Execution context
- `strategies` (Optional[List[str]]): Recovery strategies (None = use default)

**Returns:** `Dict[str, Any]` - Task execution result

**Raises:**
- `TaskExecutionError`: If all recovery strategies fail

### Context Management

#### `async get_relevant_context(query: str, max_items: int = 10, min_score: float = 0.5) -> List[Dict[str, Any]]`

Get relevant context items for a query.

**Parameters:**
- `query` (str): Query string
- `max_items` (int): Maximum number of items (default: 10)
- `min_score` (float): Minimum relevance score (default: 0.5)

**Returns:** `List[Dict[str, Any]]` - List of relevant context items

#### `async score_context_relevance(context_items: List[Dict[str, Any]], query: str) -> List[float]`

Score context items for relevance to query.

**Parameters:**
- `context_items` (List[Dict[str, Any]]): Context items to score
- `query` (str): Query string

**Returns:** `List[float]` - Relevance scores

#### `async prune_context(context_items: List[Dict[str, Any]], max_tokens: int, query: Optional[str] = None, preserve_types: Optional[List[str]] = None) -> List[Dict[str, Any]]`

Prune context items to fit within token limit.

**Parameters:**
- `context_items` (List[Dict[str, Any]]): Context items to prune
- `max_tokens` (int): Maximum tokens
- `query` (Optional[str]): Optional query for relevance scoring
- `preserve_types` (Optional[List[str]]): Types to preserve

**Returns:** `List[Dict[str, Any]]` - Pruned context items

### Utility Methods

#### `is_available() -> bool`

Check if agent is available.

**Returns:** `bool` - True if agent is available

#### `is_busy() -> bool`

Check if agent is busy.

**Returns:** `bool` - True if agent is busy

---

## Concrete Agent Types

### LLMAgent

LLM-powered agent for text generation and reasoning.

**Module**: `aiecs.domain.agent.llm_agent`

```python
from aiecs.domain.agent import LLMAgent
from aiecs.llm import BaseLLMClient

class LLMAgent(BaseAIAgent):
    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_client: Union[BaseLLMClient, LLMClientProtocol],
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        config_manager: Optional[ConfigManagerProtocol] = None,
        checkpointer: Optional[CheckpointerProtocol] = None,
        context_engine: Optional[ContextEngine] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[ResourceLimits] = None,
    )
```

#### Methods

All methods from `BaseAIAgent` plus:

#### `async execute_task(task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]`

Execute a task using LLM.

**Parameters:**
- `task` (Dict[str, Any]): Task specification with 'description', 'prompt', or 'task' field
- `context` (Dict[str, Any]): Execution context

**Returns:** `Dict[str, Any]` - Execution result with 'output', 'execution_time', 'tokens_used'

#### `async process_message(message: str, sender_id: Optional[str] = None) -> Dict[str, Any]`

Process a message using LLM.

**Parameters:**
- `message` (str): Message content
- `sender_id` (Optional[str]): Optional sender identifier

**Returns:** `Dict[str, Any]` - Response dictionary with 'response', 'execution_time'

#### `async execute_task_streaming(task: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]`

Execute task with streaming response.

**Parameters:**
- `task` (Dict[str, Any]): Task specification
- `context` (Dict[str, Any]): Execution context

**Yields:** `Dict[str, Any]` - Event dictionaries with 'type' ('token', 'result', 'error')

### ToolAgent

Agent specialized in tool selection and execution.

**Module**: `aiecs.domain.agent.tool_agent`

```python
from aiecs.domain.agent import ToolAgent

class ToolAgent(BaseAIAgent):
    def __init__(
        self,
        agent_id: str,
        name: str,
        tools: Union[List[str], Dict[str, BaseTool]],
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        config_manager: Optional[ConfigManagerProtocol] = None,
        checkpointer: Optional[CheckpointerProtocol] = None,
        context_engine: Optional[ContextEngine] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[ResourceLimits] = None,
    )
```

#### Methods

All methods from `BaseAIAgent` plus:

#### `async execute_task(task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]`

Execute a task using tools.

**Parameters:**
- `task` (Dict[str, Any]): Task specification with 'tool', 'operation', and 'parameters'
- `context` (Dict[str, Any]): Execution context

**Returns:** `Dict[str, Any]` - Execution result with 'output', 'tool_used', 'execution_time'

**Raises:**
- `TaskExecutionError`: If task execution fails
- `ToolAccessDeniedError`: If tool access is denied

### HybridAgent

Hybrid agent combining LLM reasoning with tool execution (ReAct pattern).

**Module**: `aiecs.domain.agent.hybrid_agent`

```python
from aiecs.domain.agent import HybridAgent

class HybridAgent(BaseAIAgent):
    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_client: Union[BaseLLMClient, LLMClientProtocol],
        tools: Union[List[str], Dict[str, BaseTool]],
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        config_manager: Optional[ConfigManagerProtocol] = None,
        checkpointer: Optional[CheckpointerProtocol] = None,
        context_engine: Optional[ContextEngine] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[ResourceLimits] = None,
        max_iterations: int = 10,
    )
```

#### Methods

All methods from `BaseAIAgent` plus:

#### `async execute_task(task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]`

Execute a task using ReAct pattern (Reason → Act → Observe).

**Parameters:**
- `task` (Dict[str, Any]): Task specification with 'description' or 'prompt'
- `context` (Dict[str, Any]): Execution context

**Returns:** `Dict[str, Any]` - Execution result with 'output', 'steps', 'iterations', 'execution_time'

#### `async process_message(message: str, sender_id: Optional[str] = None) -> Dict[str, Any]`

Process a message using ReAct pattern.

**Parameters:**
- `message` (str): Message content
- `sender_id` (Optional[str]): Optional sender identifier

**Returns:** `Dict[str, Any]` - Response dictionary

#### `async execute_task_streaming(task: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]`

Execute task with streaming response (tokens + tool calls).

**Parameters:**
- `task` (Dict[str, Any]): Task specification
- `context` (Dict[str, Any]): Execution context

**Yields:** `Dict[str, Any]` - Event dictionaries with 'type' ('token', 'tool_call', 'tool_result', 'status', 'result')

#### `async _execute_tool_with_observation(tool_name: str, operation: Optional[str], parameters: Dict[str, Any]) -> ToolObservation`

Execute a tool and return structured observation.

**Parameters:**
- `tool_name` (str): Name of the tool to execute
- `operation` (Optional[str]): Optional operation name
- `parameters` (Dict[str, Any]): Tool parameters

**Returns:** `ToolObservation` - Structured observation with execution details

#### `get_available_tools() -> List[str]`

Get list of available tools.

**Returns:** `List[str]` - List of tool names

---

## ConversationMemory and Session

### ConversationMemory

Multi-turn conversation handling with session management.

**Module**: `aiecs.domain.agent.memory.conversation`

```python
from aiecs.domain.agent.memory import ConversationMemory

class ConversationMemory:
    def __init__(
        self,
        agent_id: str,
        context_engine: Optional[ContextEngine] = None,
        max_history_length: int = 100,
    )
```

#### Methods

#### `async add_message(role: str, content: str, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None`

Add a message to conversation history.

**Parameters:**
- `role` (str): Message role ('user', 'assistant', 'system')
- `content` (str): Message content
- `session_id` (Optional[str]): Optional session ID
- `metadata` (Optional[Dict[str, Any]]): Optional metadata

#### `async get_messages(session_id: Optional[str] = None, limit: Optional[int] = None) -> List[LLMMessage]`

Get conversation messages.

**Parameters:**
- `session_id` (Optional[str]): Optional session ID
- `limit` (Optional[int]): Optional limit on number of messages

**Returns:** `List[LLMMessage]` - List of messages

#### `async clear(session_id: Optional[str] = None) -> None`

Clear conversation history.

**Parameters:**
- `session_id` (Optional[str]): Optional session ID (None = all sessions)

#### `async get_session(session_id: str) -> Optional[Session]`

Get a session by ID.

**Parameters:**
- `session_id` (str): Session ID

**Returns:** `Optional[Session]` - Session object or None

#### `async create_session(session_id: Optional[str] = None, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Session`

Create a new session.

**Parameters:**
- `session_id` (Optional[str]): Optional session ID (auto-generated if None)
- `user_id` (Optional[str]): Optional user ID
- `metadata` (Optional[Dict[str, Any]]): Optional metadata

**Returns:** `Session` - Created session

#### `async end_session(session_id: str, status: str = "completed") -> None`

End a session.

**Parameters:**
- `session_id` (str): Session ID
- `status` (str): Session status ('completed', 'failed', 'expired')

#### `async list_sessions(active_only: bool = False) -> List[Session]`

List all sessions.

**Parameters:**
- `active_only` (bool): Only return active sessions

**Returns:** `List[Session]` - List of sessions

### Session

Conversation session with lifecycle management and metrics tracking.

**Module**: `aiecs.domain.agent.memory.conversation`

```python
from aiecs.domain.agent.memory import Session

@dataclass
class Session:
    session_id: str
    agent_id: str
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    messages: List[LLMMessage] = field(default_factory=list)
    request_count: int = 0
    error_count: int = 0
    total_processing_time: float = 0.0
```

#### Methods

#### `add_message(role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Add a message to the session.

**Parameters:**
- `role` (str): Message role
- `content` (str): Message content
- `metadata` (Optional[Dict[str, Any]]): Optional metadata

#### `track_request(processing_time: float, is_error: bool = False) -> None`

Track a request in the session.

**Parameters:**
- `processing_time` (float): Processing time in seconds
- `is_error` (bool): Whether request resulted in error

#### `get_metrics() -> Dict[str, Any]`

Get session metrics.

**Returns:** `Dict[str, Any]` - Metrics including request_count, error_count, average_processing_time, message_count

#### `is_active() -> bool`

Check if session is active.

**Returns:** `bool` - True if session is active

#### `end(status: str = "completed") -> None`

End the session.

**Parameters:**
- `status` (str): Session status ('completed', 'failed', 'expired')

#### `is_expired(max_idle_seconds: int = 1800) -> bool`

Check if session is expired.

**Parameters:**
- `max_idle_seconds` (int): Maximum idle time in seconds (default: 1800 = 30 minutes)

**Returns:** `bool` - True if session is expired

---

## ContextEngine

Advanced context and session management engine with Redis backend storage.

**Module**: `aiecs.domain.context.context_engine`

```python
from aiecs.domain.context import ContextEngine

class ContextEngine:
    def __init__(
        self,
        storage_backend: Optional[IStorageBackend] = None,
        compression_config: Optional[CompressionConfig] = None,
    )
```

### Initialization

#### `async initialize() -> None`

Initialize the context engine.

**Raises:**
- `RuntimeError`: If initialization fails

### Session Management

#### `async create_session(session_id: Optional[str] = None, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str`

Create a new session.

**Parameters:**
- `session_id` (Optional[str]): Optional session ID (auto-generated if None)
- `user_id` (Optional[str]): Optional user ID
- `metadata` (Optional[Dict[str, Any]]): Optional metadata

**Returns:** `str` - Session ID

#### `async get_session(session_id: str) -> Optional[SessionMetrics]`

Get session metrics.

**Parameters:**
- `session_id` (str): Session ID

**Returns:** `Optional[SessionMetrics]` - Session metrics or None

#### `async end_session(session_id: str, status: str = "completed") -> None`

End a session.

**Parameters:**
- `session_id` (str): Session ID
- `status` (str): Session status

### Conversation History

#### `async add_message(session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Add a message to conversation history.

**Parameters:**
- `session_id` (str): Session ID
- `role` (str): Message role
- `content` (str): Message content
- `metadata` (Optional[Dict[str, Any]]): Optional metadata

#### `async get_messages(session_id: str, limit: Optional[int] = None, offset: int = 0) -> List[ConversationMessage]`

Get conversation messages.

**Parameters:**
- `session_id` (str): Session ID
- `limit` (Optional[int]): Optional limit
- `offset` (int): Offset for pagination

**Returns:** `List[ConversationMessage]` - List of messages

#### `async clear_messages(session_id: str) -> None`

Clear conversation messages for a session.

**Parameters:**
- `session_id` (str): Session ID

### Compression Methods

#### `async compress_conversation(session_id: str, strategy: Optional[str] = None, target_length: Optional[int] = None, custom_prompt: Optional[str] = None) -> Dict[str, Any]`

Compress conversation history.

**Parameters:**
- `session_id` (str): Session ID
- `strategy` (Optional[str]): Compression strategy ('truncate', 'summarize', 'semantic', 'hybrid') (None = use config)
- `target_length` (Optional[int]): Target length in messages (None = use config)
- `custom_prompt` (Optional[str]): Custom compression prompt (None = use default)

**Returns:** `Dict[str, Any]` - Compression result with 'original_length', 'compressed_length', 'strategy', 'summary'

**Example:**
```python
result = await context_engine.compress_conversation(
    session_id="session-123",
    strategy="summarize",
    target_length=10
)
```

#### `async summarize_conversation(session_id: str, max_messages: Optional[int] = None, custom_prompt: Optional[str] = None) -> str`

Summarize conversation history.

**Parameters:**
- `session_id` (str): Session ID
- `max_messages` (Optional[int]): Maximum messages to summarize (None = all)
- `custom_prompt` (Optional[str]): Custom summarization prompt

**Returns:** `str` - Conversation summary

#### `async truncate_conversation(session_id: str, keep_last: int) -> int`

Truncate conversation history, keeping only the last N messages.

**Parameters:**
- `session_id` (str): Session ID
- `keep_last` (int): Number of messages to keep

**Returns:** `int` - Number of messages removed

#### `async semantic_compress_conversation(session_id: str, query: Optional[str] = None, max_messages: Optional[int] = None) -> Dict[str, Any]`

Semantically compress conversation based on relevance.

**Parameters:**
- `session_id` (str): Session ID
- `query` (Optional[str]): Optional query for relevance scoring
- `max_messages` (Optional[int]): Maximum messages to keep

**Returns:** `Dict[str, Any]` - Compression result

### Context Storage

#### `async store_context(session_id: str, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None`

Store context data.

**Parameters:**
- `session_id` (str): Session ID
- `key` (str): Context key
- `value` (Any): Context value
- `metadata` (Optional[Dict[str, Any]]): Optional metadata

#### `async get_context(session_id: str, key: str, default: Any = None) -> Any`

Get context data.

**Parameters:**
- `session_id` (str): Session ID
- `key` (str): Context key
- `default` (Any): Default value if not found

**Returns:** `Any` - Context value or default

#### `async list_context_keys(session_id: str) -> List[str]`

List all context keys for a session.

**Parameters:**
- `session_id` (str): Session ID

**Returns:** `List[str]` - List of context keys

### Cleanup

#### `async cleanup_expired_sessions(max_idle_seconds: int = 1800) -> int`

Clean up expired sessions.

**Parameters:**
- `max_idle_seconds` (int): Maximum idle time in seconds

**Returns:** `int` - Number of sessions cleaned up

---

## Models and Configuration

### CompressionConfig

Configuration for conversation compression.

**Module**: `aiecs.domain.context.context_engine`

```python
from aiecs.domain.context.context_engine import CompressionConfig

@dataclass
class CompressionConfig:
    strategy: str = "truncate"
    max_messages: int = 50
    keep_recent: int = 10
    summary_prompt_template: Optional[str] = None
    summary_max_tokens: int = 500
    include_summary_in_history: bool = True
    similarity_threshold: float = 0.95
    embedding_model: str = "text-embedding-ada-002"
    hybrid_strategies: List[str] = None
    auto_compress_enabled: bool = False
    auto_compress_threshold: int = 100
    auto_compress_target: int = 50
    compression_timeout: float = 30.0
```

#### Fields

##### `strategy: str = "truncate"`

Compression strategy to use.

**Values:**
- `"truncate"`: Fast truncation, keeps most recent N messages (no LLM required)
- `"summarize"`: LLM-based summarization of older messages
- `"semantic"`: Embedding-based deduplication of similar messages
- `"hybrid"`: Combination of multiple strategies applied sequentially

##### `max_messages: int = 50`

Maximum messages to keep (for truncation strategy).

##### `keep_recent: int = 10`

Always keep N most recent messages (applies to all strategies).

##### `summary_prompt_template: Optional[str] = None`

Custom prompt template for summarization. Uses `{messages}` placeholder.

**Example:**
```python
config = CompressionConfig(
    summary_prompt_template="Summarize focusing on key decisions:\n\n{messages}"
)
```

##### `summary_max_tokens: int = 500`

Maximum tokens for summary output.

##### `include_summary_in_history: bool = True`

Whether to add summary as system message in history.

##### `similarity_threshold: float = 0.95`

Similarity threshold for semantic deduplication (0.0-1.0). Messages above this similarity are considered duplicates.

##### `embedding_model: str = "text-embedding-ada-002"`

Embedding model name for semantic deduplication.

##### `hybrid_strategies: List[str] = None`

List of strategies to combine for hybrid mode. Default: `["truncate", "summarize"]`.

##### `auto_compress_enabled: bool = False`

Enable automatic compression when threshold exceeded.

##### `auto_compress_threshold: int = 100`

Message count threshold to trigger auto-compression.

##### `auto_compress_target: int = 50`

Target message count after auto-compression.

##### `compression_timeout: float = 30.0`

Maximum time for compression operation in seconds.

---

### CacheConfig

Configuration for tool result caching.

**Module**: `aiecs.domain.agent.base_agent`

```python
from aiecs.domain.agent.base_agent import CacheConfig

@dataclass
class CacheConfig:
    enabled: bool = True
    default_ttl: int = 300
    tool_specific_ttl: Dict[str, int] = None
    max_cache_size: int = 1000
    max_memory_mb: int = 100
    cleanup_interval: int = 60
    cleanup_threshold: float = 0.9
    include_timestamp_in_key: bool = False
    hash_large_inputs: bool = True
```

#### Fields

##### `enabled: bool = True`

Enable/disable caching globally.

##### `default_ttl: int = 300`

Default time-to-live in seconds for cached entries (default: 300 = 5 minutes).

##### `tool_specific_ttl: Dict[str, int] = None`

Dictionary mapping tool names to custom TTL values (overrides default_ttl).

**Example:**
```python
config = CacheConfig(
    tool_specific_ttl={
        "search": 600,  # 10 minutes
        "calculator": 3600  # 1 hour
    }
)
```

##### `max_cache_size: int = 1000`

Maximum number of cached entries before cleanup (default: 1000).

##### `max_memory_mb: int = 100`

Maximum cache memory usage in MB (approximate, default: 100).

##### `cleanup_interval: int = 60`

Interval in seconds between cleanup checks (default: 60).

##### `cleanup_threshold: float = 0.9`

Capacity threshold (0.0-1.0) to trigger cleanup (default: 0.9 = 90%).

##### `include_timestamp_in_key: bool = False`

Whether to include timestamp in cache key (default: False).

##### `hash_large_inputs: bool = True`

Whether to hash inputs larger than 1KB for cache keys (default: True).

#### Methods

##### `get_ttl(tool_name: str) -> int`

Get TTL for a specific tool.

**Parameters:**
- `tool_name` (str): Name of the tool

**Returns:** `int` - TTL in seconds (tool-specific if set, otherwise default)

---

### ResourceLimits

Configuration for agent resource limits and rate limiting.

**Module**: `aiecs.domain.agent.models`

```python
from aiecs.domain.agent.models import ResourceLimits

class ResourceLimits(BaseModel):
    max_concurrent_tasks: int = 10
    max_tokens_per_minute: Optional[int] = None
    max_tokens_per_hour: Optional[int] = None
    token_burst_size: Optional[int] = None
    max_tool_calls_per_minute: Optional[int] = None
    max_tool_calls_per_hour: Optional[int] = None
    max_memory_mb: Optional[int] = None
    task_timeout_seconds: Optional[int] = None
    resource_wait_timeout_seconds: int = 60
    enforce_limits: bool = True
    reject_on_limit: bool = False
```

#### Fields

##### `max_concurrent_tasks: int = 10`

Maximum number of concurrent tasks (default: 10, minimum: 1).

##### `max_tokens_per_minute: Optional[int] = None`

Maximum tokens per minute (None = unlimited).

##### `max_tokens_per_hour: Optional[int] = None`

Maximum tokens per hour (None = unlimited).

##### `token_burst_size: Optional[int] = None`

Token burst size for token bucket algorithm. If None, uses `max_tokens_per_minute`.

**Example:**
```python
limits = ResourceLimits(
    max_tokens_per_minute=10000,
    token_burst_size=20000  # Allow 2x burst
)
```

##### `max_tool_calls_per_minute: Optional[int] = None`

Maximum tool calls per minute (None = unlimited).

##### `max_tool_calls_per_hour: Optional[int] = None`

Maximum tool calls per hour (None = unlimited).

##### `max_memory_mb: Optional[int] = None`

Maximum memory usage in MB (None = unlimited).

##### `task_timeout_seconds: Optional[int] = None`

Maximum task execution time in seconds (None = unlimited).

##### `resource_wait_timeout_seconds: int = 60`

Maximum time to wait for resources in seconds (default: 60).

##### `enforce_limits: bool = True`

Whether to enforce resource limits (default: True). If False, limits are monitored but not enforced.

##### `reject_on_limit: bool = False`

Reject requests when limit reached vs wait (default: False). If True, requests are rejected immediately when limits are reached. If False, requests wait for resources to become available.

---

### Experience

Model for recording agent learning experiences.

**Module**: `aiecs.domain.agent.models`

```python
from aiecs.domain.agent.models import Experience

class Experience(BaseModel):
    experience_id: str
    agent_id: str
    task_type: str
    task_description: str
    task_complexity: Optional[str] = None
    approach: str
    tools_used: List[str] = []
    execution_time: float
    success: bool
    quality_score: Optional[float] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    context_size: Optional[int] = None
    iterations: Optional[int] = None
    lessons_learned: Optional[str] = None
    recommended_improvements: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = {}
```

#### Fields

##### `experience_id: str`

Unique identifier for the experience (auto-generated UUID if not provided).

##### `agent_id: str`

ID of the agent that had this experience.

##### `task_type: str`

Type/category of task (e.g., "data_analysis", "search", "translation").

##### `task_description: str`

Human-readable task description.

##### `task_complexity: Optional[str] = None`

Task complexity level. Common values: "simple", "medium", "complex".

##### `approach: str`

Approach/strategy used (e.g., "parallel_tools", "sequential", "react_loop").

##### `tools_used: List[str] = []`

List of tool names used in execution.

##### `execution_time: float`

Execution time in seconds (must be >= 0).

##### `success: bool`

Whether task execution succeeded.

##### `quality_score: Optional[float] = None`

Quality score from 0.0 to 1.0 (None if not available).

##### `error_type: Optional[str] = None`

Type of error if failed (e.g., "timeout", "validation_error", "network_error").

##### `error_message: Optional[str] = None`

Error message if execution failed.

##### `context_size: Optional[int] = None`

Context size in tokens (if applicable, must be >= 0).

##### `iterations: Optional[int] = None`

Number of iterations/attempts (if applicable, must be >= 0).

##### `lessons_learned: Optional[str] = None`

Human-readable lessons learned from this experience.

##### `recommended_improvements: Optional[str] = None`

Recommended improvements for future tasks.

##### `timestamp: datetime`

When the experience occurred (defaults to current UTC time if not provided).

##### `metadata: Dict[str, Any] = {}`

Additional experience metadata.

---

### RecoveryStrategy

Recovery strategies for error handling.

**Module**: `aiecs.domain.agent.models`

```python
from aiecs.domain.agent.models import RecoveryStrategy

class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    SIMPLIFY = "simplify"
    FALLBACK = "fallback"
    DELEGATE = "delegate"
    ABORT = "abort"
```

#### Enum Values

##### `RETRY = "retry"`

Retry the same task with exponential backoff.

**Use When:**
- Transient errors (network, timeout, rate limits)
- Temporary failures
- Errors likely to succeed on retry

**Example:**
```python
strategies = [RecoveryStrategy.RETRY]
result = await agent.execute_with_recovery(task, context, strategies)
```

##### `SIMPLIFY = "simplify"`

Simplify the task and retry.

**Use When:**
- Task is too complex
- Breaking down helps
- Simpler version likely to succeed

**Example:**
```python
strategies = [RecoveryStrategy.SIMPLIFY]
result = await agent.execute_with_recovery(task, context, strategies)
```

##### `FALLBACK = "fallback"`

Use a fallback approach or alternative method.

**Use When:**
- Alternative approach available
- Primary method failed
- Fallback method acceptable

**Example:**
```python
strategies = [RecoveryStrategy.FALLBACK]
result = await agent.execute_with_recovery(task, context, strategies)
```

##### `DELEGATE = "delegate"`

Delegate the task to another capable agent.

**Use When:**
- Other agents available
- Current agent lacks capability
- Delegation appropriate

**Example:**
```python
strategies = [RecoveryStrategy.DELEGATE]
result = await agent.execute_with_recovery(task, context, strategies)
```

**Note:** Requires `collaboration_enabled=True` and `agent_registry` to be configured.

##### `ABORT = "abort"`

Abort execution and return error (terminal strategy).

**Use When:**
- All recovery attempts exhausted
- Error is terminal
- No further recovery possible

**Example:**
```python
strategies = [RecoveryStrategy.ABORT]
try:
    result = await agent.execute_with_recovery(task, context, strategies)
except Exception as e:
    # Task aborted
    print(f"Task aborted: {e}")
```

#### Usage Pattern

Strategies are typically chained together, trying each in sequence:

```python
# Full recovery chain
strategies = [
    RecoveryStrategy.RETRY,      # Try retry first
    RecoveryStrategy.SIMPLIFY,   # Then simplify
    RecoveryStrategy.FALLBACK,   # Then fallback
    RecoveryStrategy.DELEGATE,   # Then delegate
    RecoveryStrategy.ABORT      # Finally abort
]

result = await agent.execute_with_recovery(task, context, strategies)
```

---

## Protocols

Protocols define interfaces for duck typing, enabling flexible integration of custom components without inheritance requirements.

### LLMClientProtocol

Protocol for LLM clients enabling duck typing integration.

**Module**: `aiecs.llm.protocols`

```python
from aiecs.llm.protocols import LLMClientProtocol
from aiecs.llm.clients.base_client import LLMMessage, LLMResponse

@runtime_checkable
class LLMClientProtocol(Protocol):
    provider_name: str
    
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse
    
    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]
    
    async def close(self) -> None
    
    async def get_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]
```

#### Required Attributes

##### `provider_name: str`

Provider name identifier (e.g., "openai", "xai", "custom").

#### Required Methods

##### `async generate_text(messages: List[LLMMessage], model: Optional[str] = None, temperature: float = 0.7, max_tokens: Optional[int] = None, **kwargs) -> LLMResponse`

Generate text using the LLM provider's API.

**Parameters:**
- `messages` (List[LLMMessage]): List of conversation messages
- `model` (Optional[str]): Model name (optional, uses default if not provided)
- `temperature` (float): Sampling temperature (0.0 to 1.0, default: 0.7)
- `max_tokens` (Optional[int]): Maximum tokens to generate
- `**kwargs`: Additional provider-specific parameters

**Returns:** `LLMResponse` - Response with generated text and metadata

##### `async stream_text(messages: List[LLMMessage], model: Optional[str] = None, temperature: float = 0.7, max_tokens: Optional[int] = None, **kwargs) -> AsyncGenerator[str, None]`

Stream text generation using the LLM provider's API.

**Parameters:**
- `messages` (List[LLMMessage]): List of conversation messages
- `model` (Optional[str]): Model name (optional, uses default if not provided)
- `temperature` (float): Sampling temperature (0.0 to 1.0, default: 0.7)
- `max_tokens` (Optional[int]): Maximum tokens to generate
- `**kwargs`: Additional provider-specific parameters

**Yields:** `str` - Text tokens as they are generated

##### `async close() -> None`

Clean up resources (connections, sessions, etc.).

##### `async get_embeddings(texts: List[str], model: Optional[str] = None, **kwargs) -> List[List[float]]`

Get embeddings for a list of texts (optional, for semantic compression).

**Parameters:**
- `texts` (List[str]): List of texts to embed
- `model` (Optional[str]): Embedding model name
- `**kwargs`: Additional provider-specific parameters

**Returns:** `List[List[float]]` - List of embedding vectors

**Note:** Not all LLM clients support embeddings. If not supported, raise `NotImplementedError`.

#### Example Implementation

```python
class CustomLLMClient:
    provider_name = "custom"
    
    async def generate_text(self, messages, model=None, temperature=0.7, max_tokens=None, **kwargs):
        # Custom implementation
        return LLMResponse(content="...", provider="custom")
    
    async def stream_text(self, messages, model=None, temperature=0.7, max_tokens=None, **kwargs):
        async for token in self._custom_stream():
            yield token
    
    async def close(self):
        # Cleanup
        pass

# Use with agent (no inheritance required!)
agent = HybridAgent(
    llm_client=CustomLLMClient(),
    ...
)
```

---

### ConfigManagerProtocol

Protocol for custom configuration managers enabling dynamic configuration loading.

**Module**: `aiecs.domain.agent.integration.protocols`

```python
from aiecs.domain.agent.integration.protocols import ConfigManagerProtocol

@runtime_checkable
class ConfigManagerProtocol(Protocol):
    async def get_config(self, key: str, default: Any = None) -> Any
    async def set_config(self, key: str, value: Any) -> None
    async def reload_config(self) -> None
```

#### Required Methods

##### `async get_config(key: str, default: Any = None) -> Any`

Get configuration value by key.

**Parameters:**
- `key` (str): Configuration key
- `default` (Any): Default value if key not found

**Returns:** `Any` - Configuration value or default

##### `async set_config(key: str, value: Any) -> None`

Set configuration value.

**Parameters:**
- `key` (str): Configuration key
- `value` (Any): Configuration value

##### `async reload_config() -> None`

Reload configuration from source. This method should refresh any cached configuration data.

#### Example Implementation

```python
class DatabaseConfigManager:
    async def get_config(self, key: str, default: Any = None) -> Any:
        return await db.get_config(key, default)
    
    async def set_config(self, key: str, value: Any) -> None:
        await db.set_config(key, value)
    
    async def reload_config(self) -> None:
        await db.refresh_cache()

# Use with agent
agent = HybridAgent(
    config_manager=DatabaseConfigManager(),
    ...
)
```

---

### CheckpointerProtocol

Protocol for custom checkpointers enabling state persistence (LangGraph compatible).

**Module**: `aiecs.domain.agent.integration.protocols`

```python
from aiecs.domain.agent.integration.protocols import CheckpointerProtocol

@runtime_checkable
class CheckpointerProtocol(Protocol):
    async def save_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]
    ) -> str
    
    async def load_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]
    
    async def list_checkpoints(self, agent_id: str, session_id: str) -> list[str]
```

#### Required Methods

##### `async save_checkpoint(agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]) -> str`

Save checkpoint and return checkpoint ID.

**Parameters:**
- `agent_id` (str): Agent identifier
- `session_id` (str): Session identifier
- `checkpoint_data` (Dict[str, Any]): Checkpoint data to save

**Returns:** `str` - Checkpoint ID for later retrieval

##### `async load_checkpoint(agent_id: str, session_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]`

Load checkpoint data.

**Parameters:**
- `agent_id` (str): Agent identifier
- `session_id` (str): Session identifier
- `checkpoint_id` (Optional[str]): Specific checkpoint ID (loads latest if None)

**Returns:** `Optional[Dict[str, Any]]` - Checkpoint data or None if not found

##### `async list_checkpoints(agent_id: str, session_id: str) -> list[str]`

List all checkpoint IDs for a session.

**Parameters:**
- `agent_id` (str): Agent identifier
- `session_id` (str): Session identifier

**Returns:** `list[str]` - List of checkpoint IDs

#### Example Implementation

```python
class RedisCheckpointer:
    async def save_checkpoint(self, agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]) -> str:
        checkpoint_id = str(uuid.uuid4())
        await redis.set(f"checkpoint:{checkpoint_id}", json.dumps(checkpoint_data))
        return checkpoint_id
    
    async def load_checkpoint(self, agent_id: str, session_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if checkpoint_id:
            data = await redis.get(f"checkpoint:{checkpoint_id}")
            return json.loads(data) if data else None
        return await self._load_latest(agent_id, session_id)
    
    async def list_checkpoints(self, agent_id: str, session_id: str) -> list[str]:
        return await redis.keys(f"checkpoint:{agent_id}:{session_id}:*")

# Use with agent
agent = HybridAgent(
    checkpointer=RedisCheckpointer(),
    ...
)
```

---

### AgentCollaborationProtocol

Protocol for agent collaboration enabling multi-agent workflows.

**Module**: `aiecs.domain.agent.integration.protocols`

```python
from aiecs.domain.agent.integration.protocols import AgentCollaborationProtocol

@runtime_checkable
class AgentCollaborationProtocol(Protocol):
    agent_id: str
    name: str
    capabilities: List[str]
    
    async def execute_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]
    
    async def review_result(
        self, task: Dict[str, Any], result: Dict[str, Any]
    ) -> Dict[str, Any]
```

#### Required Attributes

##### `agent_id: str`

Unique identifier for the agent.

##### `name: str`

Human-readable agent name.

##### `capabilities: List[str]`

List of capability strings (e.g., ["search", "analysis", "web_scraping"]).

#### Required Methods

##### `async execute_task(task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]`

Execute a task.

**Parameters:**
- `task` (Dict[str, Any]): Task specification
- `context` (Dict[str, Any]): Execution context

**Returns:** `Dict[str, Any]` - Task execution result

##### `async review_result(task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]`

Review another agent's task result.

**Parameters:**
- `task` (Dict[str, Any]): Original task specification
- `result` (Dict[str, Any]): Task execution result to review

**Returns:** `Dict[str, Any]` - Review result with 'approved' (bool) and 'feedback' (str)

#### Example Implementation

```python
class CollaborativeAgent(BaseAIAgent):
    agent_id: str
    name: str
    capabilities: List[str]
    
    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "output": "result"}
    
    async def review_result(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        return {"approved": True, "feedback": "Looks good"}

# Use with agent registry
agent_registry = {
    "agent1": CollaborativeAgent(...),
    "agent2": CollaborativeAgent(...)
}

agent = HybridAgent(
    collaboration_enabled=True,
    agent_registry=agent_registry,
    ...
)
```

---

## ToolObservation

Structured observation of tool execution results.

**Module**: `aiecs.domain.agent.models`

```python
from aiecs.domain.agent.models import ToolObservation

class ToolObservation(BaseModel):
    tool_name: str
    parameters: Dict[str, Any] = {}
    result: Any = None
    success: bool
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    timestamp: str
```

### Fields

##### `tool_name: str`

Name of the tool that was executed.

##### `parameters: Dict[str, Any] = {}`

Dictionary of parameters passed to the tool.

##### `result: Any = None`

Tool execution result (any type).

##### `success: bool`

Whether tool execution succeeded (True/False).

##### `error: Optional[str] = None`

Error message if execution failed (None if successful).

##### `execution_time_ms: Optional[float] = None`

Execution time in milliseconds (None if not measured, must be >= 0).

##### `timestamp: str`

ISO format timestamp of execution (auto-generated if not provided).

### Methods

##### `to_dict() -> Dict[str, Any]`

Convert observation to dictionary for serialization.

**Returns:** `Dict[str, Any]` - Dictionary representation

**Example:**
```python
obs = ToolObservation(tool_name="search", success=True, result="data")
data = obs.to_dict()
# {'tool_name': 'search', 'success': True, 'result': 'data', ...}
```

##### `to_text() -> str`

Format observation as text for LLM context.

**Returns:** `str` - Formatted text representation

**Example:**
```python
obs = ToolObservation(
    tool_name="search",
    parameters={"query": "AI"},
    success=True,
    result="Found 10 results",
    execution_time_ms=250.5
)
text = obs.to_text()
# "Tool: search
# Parameters: {'query': 'AI'}
# Status: SUCCESS
# Result: Found 10 results
# Execution time: 250.5ms
# Timestamp: 2024-01-01T12:00:00"
```

---

## Enhanced Methods

### _execute_tool_with_observation()

Execute a tool and return structured observation.

**Module**: `aiecs.domain.agent.hybrid_agent`

**Class**: `HybridAgent`

```python
async def _execute_tool_with_observation(
    self,
    tool_name: str,
    operation: Optional[str],
    parameters: Dict[str, Any],
) -> ToolObservation
```

#### Description

Wraps tool execution with automatic success/error tracking, execution time measurement, and structured result formatting. Returns a `ToolObservation` object that can be used for debugging, analysis, and LLM reasoning loops.

#### Parameters

- `tool_name` (str): Name of the tool to execute
- `operation` (Optional[str]): Optional operation name
- `parameters` (Dict[str, Any]): Tool parameters

#### Returns

`ToolObservation` - Structured observation with execution details including:
- `tool_name`: Name of the tool
- `parameters`: Parameters passed
- `result`: Tool execution result (or None if failed)
- `success`: Whether execution succeeded
- `error`: Error message if failed
- `execution_time_ms`: Execution time in milliseconds
- `timestamp`: ISO timestamp

#### Example

```python
# Execute tool with observation
obs = await agent._execute_tool_with_observation(
    tool_name="search",
    operation="query",
    parameters={"q": "Python"}
)

# Check success
if obs.success:
    print(f"Found results: {obs.result}")
    print(f"Execution time: {obs.execution_time_ms}ms")
else:
    print(f"Error: {obs.error}")

# Format for LLM context
observation_text = obs.to_text()
# Include in LLM prompt
```

#### Notes

- Automatically measures execution time
- Catches exceptions and returns error observation
- Returns observation even on failure (with `success=False`)
- Essential for MasterController compatibility and observation-based reasoning

---

## Performance Enhancement APIs

### Caching APIs

#### `execute_tool_with_cache(tool_name: str, parameters: Dict[str, Any]) -> Any`

Execute tool with caching support. See [Tool Execution](#tool-execution) section.

#### `invalidate_cache(tool_name: Optional[str] = None, pattern: Optional[str] = None) -> int`

Invalidate cache entries. See [Tool Execution](#tool-execution) section.

#### `get_cache_stats() -> Dict[str, Any]`

Get cache statistics. See [Tool Execution](#tool-execution) section.

### Parallel Execution APIs

#### `execute_tools_parallel(tool_calls: List[Dict[str, Any]], max_concurrency: int = 5) -> List[Dict[str, Any]]`

Execute multiple tools in parallel. See [Tool Execution](#tool-execution) section.

#### `analyze_tool_dependencies(tool_calls: List[Dict[str, Any]]) -> Dict[str, List[str]]`

Analyze dependencies between tool calls.

**Parameters:**
- `tool_calls` (List[Dict[str, Any]]): List of tool calls

**Returns:** `Dict[str, List[str]]` - Dependency graph mapping tool names to dependent tools

#### `execute_tools_with_dependencies(tool_calls: List[Dict[str, Any]], max_concurrency: int = 5) -> List[Dict[str, Any]]`

Execute tools respecting dependencies.

**Parameters:**
- `tool_calls` (List[Dict[str, Any]]): List of tool calls
- `max_concurrency` (int): Maximum concurrent executions

**Returns:** `List[Dict[str, Any]]` - Results in execution order

### Streaming APIs

#### `execute_task_streaming(task: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]`

Execute task with streaming response. See [Streaming](#streaming) section.

#### `process_message_streaming(message: str, sender_id: Optional[str] = None) -> AsyncIterator[str]`

Process message with streaming response. See [Streaming](#streaming) section.

---

## Reliability Enhancement APIs

### Error Recovery APIs

#### `execute_with_recovery(task: Dict[str, Any], context: Dict[str, Any], strategies: Optional[List[str]] = None) -> Dict[str, Any]`

Execute task with recovery strategies. See [Error Recovery](#error-recovery) section.

### Resource Management APIs

#### `check_resource_availability() -> Dict[str, Any]`

Check if resources are available. See [Resource Management](#resource-management) section.

#### `wait_for_resources(timeout: Optional[float] = None) -> bool`

Wait for resources to become available. See [Resource Management](#resource-management) section.

#### `get_resource_usage() -> Dict[str, Any]`

Get current resource usage. See [Resource Management](#resource-management) section.

### Checkpointing APIs

#### `save_checkpoint(session_id: Optional[str] = None) -> Optional[str]`

Save agent state checkpoint. See [Checkpointing](#checkpointing) section.

#### `load_checkpoint(checkpoint_id: str) -> bool`

Load agent state from checkpoint. See [Checkpointing](#checkpointing) section.

---

## Observability Enhancement APIs

### Metrics APIs

#### `get_metrics() -> AgentMetrics`

Get agent metrics. See [Metrics and Performance](#metrics-and-performance) section.

#### `update_metrics(execution_time: Optional[float] = None, success: Optional[bool] = None, tokens_used: Optional[int] = None, tool_calls: Optional[int] = None) -> None`

Update agent metrics. See [Metrics and Performance](#metrics-and-performance) section.

#### `get_performance_metrics() -> Dict[str, Any]`

Get performance metrics. See [Metrics and Performance](#metrics-and-performance) section.

#### `reset_metrics() -> None`

Reset agent metrics. See [Metrics and Performance](#metrics-and-performance) section.

### Health Status APIs

#### `get_health_status() -> Dict[str, Any]`

Get agent health status. See [Metrics and Performance](#metrics-and-performance) section.

#### `get_comprehensive_status() -> Dict[str, Any]`

Get comprehensive agent status. See [Metrics and Performance](#metrics-and-performance) section.

### Operation Tracking APIs

#### `track_operation_time(operation_name: str) -> OperationTimer`

Track operation execution time (context manager). See [Metrics and Performance](#metrics-and-performance) section.

### Session Metrics APIs

#### `update_session_metrics(session_id: str, processing_time: float, is_error: bool = False) -> None`

Update session-level metrics.

**Parameters:**
- `session_id` (str): Session ID
- `processing_time` (float): Processing time in seconds
- `is_error` (bool): Whether request resulted in error

---

This API reference covers the main classes, methods, models, configuration classes, protocols, and enhancement APIs. For additional examples and usage patterns, see the integration guides and examples documentation.

