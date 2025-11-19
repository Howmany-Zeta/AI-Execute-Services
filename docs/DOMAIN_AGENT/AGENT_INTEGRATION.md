# Agent Integration Guide

This comprehensive guide covers all features and integration patterns for AIECS agents, including the enhanced flexibility features introduced in `enhance-hybrid-agent-flexibility`.

## Table of Contents

1. [Overview](#overview)
2. [Agent Types](#agent-types)
3. [Tool Integration](#tool-integration)
4. [LLM Client Integration](#llm-client-integration)
5. [Memory and Session Management](#memory-and-session-management)
6. [Configuration Management](#configuration-management)
7. [State Persistence](#state-persistence)
8. [Performance Features](#performance-features)
9. [Collaboration Features](#collaboration-features)
10. [Learning and Adaptation](#learning-and-adaptation)
11. [Resource Management](#resource-management)
12. [Error Recovery](#error-recovery)
13. [Observability](#observability)
14. [Best Practices](#best-practices)

## Overview

AIECS agents provide a flexible, production-ready framework for building AI-powered applications with:

- **Multiple agent types**: LLM-only, tool-only, and hybrid (ReAct) agents
- **Flexible tool integration**: Support for tool names or tool instances
- **Custom LLM clients**: Protocol-based integration for any LLM implementation
- **Persistent memory**: ContextEngine integration for conversation history
- **Dynamic configuration**: Custom config managers for runtime updates
- **State persistence**: Checkpointers for LangGraph and custom state management
- **Performance optimization**: Caching, parallel execution, streaming
- **Multi-agent workflows**: Collaboration, delegation, consensus
- **Production features**: Resource limits, error recovery, health monitoring

## Agent Types

### BaseAIAgent

Abstract base class providing core functionality for all agent types.

**Key Features**:
- Lifecycle management (initialize, activate, shutdown)
- State management (goals, metrics, health)
- Tool integration (names or instances)
- LLM client integration (protocol-based)
- Memory management (ConversationMemory)
- Performance tracking (metrics, timers)
- Health monitoring (status, scores)

**Example**:
```python
from aiecs.domain.agent import BaseAIAgent, AgentType, AgentConfiguration

class CustomAgent(BaseAIAgent):
    def __init__(self, agent_id, name, config):
        super().__init__(agent_id, name, AgentType.CUSTOM, config)
    
    async def execute_task(self, task, context):
        # Your custom implementation
        return {"output": "result"}
```

### LLMAgent

LLM-powered agent for text generation and reasoning without tools.

**Use When**:
- You only need LLM capabilities
- No tool execution required
- Simple text generation tasks

**Example**:
```python
from aiecs.domain.agent import LLMAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

llm_client = OpenAIClient()
config = AgentConfiguration(
    goal="Answer questions",
    llm_model="gpt-4"
)

agent = LLMAgent(
    agent_id="llm_1",
    name="Question Answerer",
    llm_client=llm_client,
    config=config
)

await agent.initialize()
result = await agent.execute_task(
    {"description": "What is AI?"},
    {}
)
```

### ToolAgent

Agent specialized in tool selection and execution without LLM reasoning.

**Use When**:
- You need tool execution only
- No LLM reasoning required
- Direct tool invocation

**Example**:
```python
from aiecs.domain.agent import ToolAgent, AgentConfiguration

agent = ToolAgent(
    agent_id="tool_1",
    name="Tool Executor",
    tools=["search", "calculator"],
    config=AgentConfiguration()
)

await agent.initialize()
result = await agent.execute_task(
    {"description": "Search for Python tutorials"},
    {}
)
```

### HybridAgent

Combines LLM reasoning with tool capabilities using the ReAct pattern.

**Use When**:
- You need both reasoning and tool execution
- Complex multi-step tasks
- Tool selection based on reasoning

**Example**:
```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

llm_client = OpenAIClient()
config = AgentConfiguration(
    goal="Help users with research",
    llm_model="gpt-4"
)

agent = HybridAgent(
    agent_id="hybrid_1",
    name="Research Assistant",
    llm_client=llm_client,
    tools=["web_search", "calculator", "file_reader"],
    config=config
)

await agent.initialize()
result = await agent.execute_task(
    {"description": "Research Python async programming and summarize"},
    {}
)
```

## Tool Integration

### Tool Names (Simple)

Use tool names when tools don't need state or dependencies.

```python
agent = HybridAgent(
    agent_id="agent1",
    name="Simple Agent",
    llm_client=llm_client,
    tools=["search", "calculator"],  # Tool names
    config=config
)
```

**Benefits**:
- Simple and clean
- Tools loaded automatically
- Good for stateless tools

**Limitations**:
- Can't inject dependencies
- Can't use stateful tools
- Limited customization

### Tool Instances (Advanced)

Use tool instances when tools need state, dependencies, or custom configuration.

```python
from aiecs.tools import BaseTool
from aiecs.domain.context import ContextEngine

# Create tool instances with dependencies
context_engine = ContextEngine()
await context_engine.initialize()

read_context_tool = ReadContextTool(context_engine=context_engine)
smart_analysis_tool = SmartAnalysisTool(llm_manager=llm_manager)

# Pass tool instances
agent = HybridAgent(
    agent_id="agent1",
    name="Advanced Agent",
    llm_client=llm_client,
    tools={
        "read_context": read_context_tool,  # Stateful tool
        "smart_analysis": smart_analysis_tool
    },
    config=config
)
```

**Benefits**:
- Stateful tools supported
- Dependency injection
- Custom configuration
- Better for production

**Use Cases**:
- Tools with context_engine dependencies
- Tools with service instances
- Tools with LLM manager dependencies
- Tools requiring initialization

### Stateful Tool Example

```python
class DatabaseQueryTool(BaseTool):
    def __init__(self, db_connection):
        self.db = db_connection
        super().__init__(
            name="database_query",
            description="Query the database"
        )
    
    async def run_async(self, query: str, **kwargs):
        return await self.db.execute(query)

# Create tool with database connection
db_tool = DatabaseQueryTool(db_connection=my_db)

agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools={"database_query": db_tool},  # Stateful tool instance
    config=config
)
```

### Tool with Dependencies Example

```python
class ServiceCallTool(BaseTool):
    def __init__(self, service_instance):
        self.service = service_instance
        super().__init__(
            name="service_call",
            description="Call external service"
        )
    
    async def run_async(self, endpoint: str, method: str = "GET", **kwargs):
        return await self.service.call(endpoint, method)

# Create tool with service instance
service_tool = ServiceCallTool(service_instance=my_service)

agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools={"service_call": service_tool},  # Tool with dependencies
    config=config
)
```

## LLM Client Integration

### Standard LLM Clients

Use `BaseLLMClient` subclasses for standard LLM providers.

```python
from aiecs.llm import OpenAIClient, AnthropicClient

# OpenAI client
openai_client = OpenAIClient(api_key="sk-...")
agent = HybridAgent(
    agent_id="agent1",
    llm_client=openai_client,
    tools=["search"],
    config=config
)

# Anthropic client
anthropic_client = AnthropicClient(api_key="sk-ant-...")
agent = HybridAgent(
    agent_id="agent2",
    llm_client=anthropic_client,
    tools=["search"],
    config=config
)
```

### Custom LLM Clients

Use any LLM implementation that follows `LLMClientProtocol`.

```python
class CustomLLMClient:
    """Custom LLM client that doesn't inherit from BaseLLMClient"""
    
    provider_name = "custom"
    
    def __init__(self, api_endpoint, api_key):
        self.endpoint = api_endpoint
        self.api_key = api_key
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        # Your custom implementation
        response = await self._call_api(messages, model, temperature, max_tokens)
        return LLMResponse(
            text=response["text"],
            model=response["model"],
            usage=response["usage"]
        )
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        # Your custom streaming implementation
        async for chunk in self._stream_api(messages, model, temperature):
            yield chunk["text"]
    
    async def close(self):
        # Cleanup
        await self._close_connection()

# Use custom client directly - no adapter needed!
custom_client = CustomLLMClient(api_endpoint="https://...", api_key="...")
agent = HybridAgent(
    agent_id="agent1",
    llm_client=custom_client,  # Works directly!
    tools=["search"],
    config=config
)
```

### LLM Client Wrappers

Create wrappers for retry, caching, rate limiting, etc.

```python
class RetryLLMClient:
    """Wrapper that adds retry logic to any LLM client"""
    
    def __init__(self, base_client, max_retries=3):
        self.base_client = base_client
        self.max_retries = max_retries
        self.provider_name = base_client.provider_name
    
    async def generate_text(self, messages, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return await self.base_client.generate_text(messages, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
    
    async def stream_text(self, messages, **kwargs):
        # Similar retry logic for streaming
        pass
    
    async def close(self):
        await self.base_client.close()

# Use wrapper
wrapped_client = RetryLLMClient(OpenAIClient(), max_retries=5)
agent = HybridAgent(
    agent_id="agent1",
    llm_client=wrapped_client,  # Wrapped client works!
    tools=["search"],
    config=config
)
```

### MasterController Integration

Integrate with MasterController's `LLMIntegrationManager` directly.

```python
from aiecs.domain.execution.master_controller import MasterController

# MasterController's LLMIntegrationManager works directly
master_controller = MasterController(...)
agent = HybridAgent(
    agent_id="agent1",
    llm_client=master_controller.llm_manager,  # Direct integration!
    tools={
        "read_context": ReadContextTool(context_engine=master_controller.context_engine)
    },
    config=config
)
```

## Memory and Session Management

### Basic Memory

Default in-memory conversation history.

```python
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config
)

# Conversation history stored in memory
result1 = await agent.execute_task({"description": "Hello"}, {})
result2 = await agent.execute_task({"description": "What did I say?"}, {})
# Agent remembers previous conversation
```

### ContextEngine Integration

Persistent conversation history across agent restarts.

```python
from aiecs.domain.context import ContextEngine

# Initialize ContextEngine
context_engine = ContextEngine()
await context_engine.initialize()

# Agent with persistent memory
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine  # Enables persistence
)

# Conversation persists across restarts
session_id = "user-123"
result1 = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": session_id}
)

# Agent restarts...
agent2 = HybridAgent(
    agent_id="agent1",  # Same agent ID
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)
await agent2.initialize()

# Previous conversation still available!
result2 = await agent2.execute_task(
    {"description": "What did I say?"},
    {"session_id": session_id}  # Same session ID
)
```

### Session Lifecycle Management

Manage sessions with lifecycle tracking and metrics.

```python
from aiecs.domain.agent.memory import Session

# Create session
session = await agent.create_session("user-123")

# Use session
result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": session.session_id}
)

# Get session metrics
metrics = await agent.get_session_metrics(session.session_id)
print(f"Requests: {metrics.request_count}")
print(f"Errors: {metrics.error_count}")
print(f"Avg time: {metrics.avg_processing_time_ms}ms")

# Cleanup inactive sessions
await agent.cleanup_inactive_sessions(max_age_hours=24)
```

### Conversation Compression

Automatic compression to manage conversation history size.

```python
from aiecs.domain.context import CompressionConfig

# Configure compression
compression_config = CompressionConfig(
    strategy="summarize",  # LLM-based summarization
    keep_recent=10,  # Always keep 10 most recent messages
    auto_compress_enabled=True,
    auto_compress_threshold=50,  # Compress when 50+ messages
    auto_compress_target=30  # Target 30 messages after compression
)

context_engine = ContextEngine(compression_config=compression_config)
await context_engine.initialize()

agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Compression happens automatically when threshold exceeded
```

## Configuration Management

### Static Configuration

Standard static configuration.

```python
from aiecs.domain.agent import AgentConfiguration

config = AgentConfiguration(
    goal="Help users",
    llm_model="gpt-4",
    temperature=0.7,
    max_tokens=2000
)

agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config
)
```

### Dynamic Configuration

Use custom config managers for runtime configuration updates.

```python
from aiecs.domain.agent.integration import ConfigManagerProtocol

class DatabaseConfigManager:
    """Config manager that loads from database"""
    
    async def get_config(self, key: str, default: Any = None) -> Any:
        return await db.get_config(key, default)
    
    async def set_config(self, key: str, value: Any) -> None:
        await db.set_config(key, value)
    
    async def reload_config(self) -> None:
        await db.refresh_cache()

# Agent with dynamic config
config_manager = DatabaseConfigManager()
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    config_manager=config_manager  # Dynamic config
)

# Update config at runtime
await agent.get_config_manager().set_config("goal", "New goal")
await agent.get_config_manager().reload_config()
```

### Environment-Based Configuration

Load configuration from environment variables.

```python
import os

class EnvironmentConfigManager:
    async def get_config(self, key: str, default: Any = None) -> Any:
        env_key = f"AGENT_{key.upper()}"
        return os.getenv(env_key, default)
    
    async def set_config(self, key: str, value: Any) -> None:
        # Environment variables are read-only
        raise NotImplementedError("Environment config is read-only")
    
    async def reload_config(self) -> None:
        # No-op for environment config
        pass

config_manager = EnvironmentConfigManager()
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    config_manager=config_manager
)
```

## State Persistence

### Checkpointers

Save and load agent state for LangGraph integration or custom persistence.

```python
from aiecs.domain.agent.integration import CheckpointerProtocol

class RedisCheckpointer:
    """Redis-based checkpointer for distributed systems"""
    
    async def save_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_data: Dict[str, Any]
    ) -> str:
        checkpoint_id = str(uuid.uuid4())
        key = f"checkpoint:{agent_id}:{session_id}:{checkpoint_id}"
        await redis.setex(
            key,
            3600,  # 1 hour TTL
            json.dumps(checkpoint_data)
        )
        return checkpoint_id
    
    async def load_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if checkpoint_id:
            key = f"checkpoint:{agent_id}:{session_id}:{checkpoint_id}"
            data = await redis.get(key)
            return json.loads(data) if data else None
        
        # Load latest checkpoint
        pattern = f"checkpoint:{agent_id}:{session_id}:*"
        keys = await redis.keys(pattern)
        if keys:
            latest_key = max(keys, key=lambda k: await redis.ttl(k))
            data = await redis.get(latest_key)
            return json.loads(data) if data else None
        return None
    
    async def list_checkpoints(
        self,
        agent_id: str,
        session_id: str
    ) -> list[str]:
        pattern = f"checkpoint:{agent_id}:{session_id}:*"
        keys = await redis.keys(pattern)
        return [k.split(":")[-1] for k in keys]

# Agent with checkpointing
checkpointer = RedisCheckpointer()
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    checkpointer=checkpointer  # Enable checkpointing
)

# Save checkpoint
checkpoint_id = await agent.save_checkpoint("session-123")

# Load checkpoint
state = await agent.load_checkpoint("session-123", checkpoint_id)

# List all checkpoints
checkpoints = await agent.list_checkpoints("session-123")
```

### LangGraph Integration

Use checkpointers for LangGraph state management.

```python
from langgraph.graph import StateGraph
from aiecs.domain.agent.integration import CheckpointerProtocol

class LangGraphCheckpointer:
    """Checkpointer compatible with LangGraph"""
    
    async def save_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_data: Dict[str, Any]
    ) -> str:
        # Save in LangGraph-compatible format
        checkpoint = {
            "channel_values": checkpoint_data,
            "channel_versions": {},
            "versions_seen": {}
        }
        checkpoint_id = str(uuid.uuid4())
        await storage.save(checkpoint_id, checkpoint)
        return checkpoint_id
    
    # ... implement other methods ...

# Use with LangGraph
checkpointer = LangGraphCheckpointer()
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    checkpointer=checkpointer
)

# LangGraph can use the same checkpointer
graph = StateGraph(...)
graph.compile(checkpointer=checkpointer)
```

## Performance Features

### Tool Result Caching

Cache tool results to reduce API calls and costs.

```python
from aiecs.domain.agent import CacheConfig

# Configure caching
cache_config = CacheConfig(
    enabled=True,
    default_ttl=300,  # 5 minutes default
    tool_specific_ttl={
        "search": 600,  # Search cached for 10 minutes
        "calculator": 3600,  # Calculator cached for 1 hour
        "weather": 1800  # Weather cached for 30 minutes
    },
    max_cache_size=1000,
    cleanup_threshold=0.9
)

agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search", "calculator", "weather"],
    config=config,
    cache_config=cache_config  # Enable caching
)

# First call - executes tool
result1 = await agent.execute_task(
    {"description": "What's the weather in NYC?"},
    {}
)

# Second call with same parameters - uses cache!
result2 = await agent.execute_task(
    {"description": "What's the weather in NYC?"},
    {}
)
```

### Parallel Tool Execution

Execute independent tools concurrently for faster execution.

```python
# Agent automatically detects independent tools and executes in parallel
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search", "calculator", "weather"],
    config=config,
    enable_parallel_execution=True  # Enable parallel execution
)

# Tools executed in parallel when possible
result = await agent.execute_task(
    {"description": "Search for Python, calculate 2+2, and get weather"},
    {}
)
# All three tools execute concurrently!
```

### Streaming Responses

Stream tokens, tool calls, and results as they're generated.

```python
# Enable streaming
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    enable_streaming=True
)

# Stream response
async for chunk in agent.stream_task(
    {"description": "Research Python async programming"},
    {}
):
    if chunk["type"] == "token":
        print(chunk["content"], end="", flush=True)
    elif chunk["type"] == "tool_call":
        print(f"\nCalling tool: {chunk['tool']}")
    elif chunk["type"] == "tool_result":
        print(f"\nTool result: {chunk['result']}")
```

## Collaboration Features

### Multi-Agent Workflows

Enable agents to collaborate on tasks.

```python
from aiecs.domain.agent.integration import AgentCollaborationProtocol

class ResearchAgent(BaseAIAgent, AgentCollaborationProtocol):
    """Agent that can collaborate with others"""
    
    async def delegate_task(
        self,
        task: Dict[str, Any],
        target_agent_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Delegate to another agent
        target_agent = await self.get_agent_registry().get_agent(target_agent_id)
        return await target_agent.execute_task(task, context)
    
    async def request_review(
        self,
        result: Dict[str, Any],
        reviewer_agent_id: str
    ) -> Dict[str, Any]:
        # Request peer review
        reviewer = await self.get_agent_registry().get_agent(reviewer_agent_id)
        review_task = {
            "description": f"Review this result: {result['output']}"
        }
        return await reviewer.execute_task(review_task, {})

# Create collaborating agents
research_agent = ResearchAgent(...)
review_agent = ReviewAgent(...)

# Agents can collaborate
result = await research_agent.delegate_task(
    task={"description": "Research topic"},
    target_agent_id=review_agent.agent_id,
    context={}
)
```

### Task Delegation

Delegate tasks to specialized agents.

```python
# Specialized agents
coding_agent = HybridAgent(
    agent_id="coding_agent",
    name="Coding Specialist",
    llm_client=llm_client,
    tools=["code_executor", "linter"],
    config=config
)

research_agent = HybridAgent(
    agent_id="research_agent",
    name="Research Specialist",
    llm_client=llm_client,
    tools=["web_search", "paper_search"],
    config=config
)

# Coordinator agent delegates to specialists
coordinator = CoordinatorAgent(
    agent_id="coordinator",
    llm_client=llm_client,
    tools=[],
    config=config
)

# Delegate based on task type
if task["type"] == "coding":
    result = await coordinator.delegate_task(task, "coding_agent")
elif task["type"] == "research":
    result = await coordinator.delegate_task(task, "research_agent")
```

## Learning and Adaptation

### Experience Recording

Agents learn from past experiences.

```python
from aiecs.domain.agent.models import Experience

# Agent automatically records experiences
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search", "calculator"],
    config=config,
    enable_learning=True  # Enable learning
)

# Execute tasks - experiences recorded automatically
result1 = await agent.execute_task(
    {"description": "Search for Python"},
    {}
)

result2 = await agent.execute_task(
    {"description": "Calculate 2+2"},
    {}
)

# Get learned experiences
experiences = await agent.get_experiences()
for exp in experiences:
    print(f"Task: {exp.task_type}")
    print(f"Success: {exp.success}")
    print(f"Approach: {exp.approach_used}")
    print(f"Outcome: {exp.outcome}")
```

### Approach Recommendation

Agents recommend best approaches based on past experiences.

```python
# Agent recommends approach for new task
recommendation = await agent.recommend_approach(
    task={"description": "Research topic"},
    context={}
)

print(f"Recommended approach: {recommendation['approach']}")
print(f"Confidence: {recommendation['confidence']}")
print(f"Based on {recommendation['experience_count']} past experiences")
```

## Resource Management

### Resource Limits

Configure rate limiting and resource quotas.

```python
from aiecs.domain.agent.models import ResourceLimits

# Configure resource limits
resource_limits = ResourceLimits(
    max_requests_per_minute=60,
    max_tokens_per_request=4000,
    max_concurrent_requests=10,
    max_memory_mb=512,
    rate_limit_window_seconds=60
)

agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits  # Enable resource limits
)

# Agent automatically enforces limits
try:
    result = await agent.execute_task(task, context)
except ResourceLimitExceeded:
    print("Rate limit exceeded")
```

### Throttling

Automatic throttling when limits approached.

```python
# Agent automatically throttles when approaching limits
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits,
    enable_throttling=True  # Enable throttling
)

# Throttling happens automatically
for i in range(100):
    result = await agent.execute_task(task, context)
    # Agent throttles if approaching rate limit
```

## Error Recovery

### Recovery Strategies

Configure error recovery strategies.

```python
from aiecs.domain.agent.models import RecoveryStrategy

# Configure recovery strategies
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search", "calculator"],
    config=config,
    recovery_strategies=[
        RecoveryStrategy.RETRY,  # Retry on failure
        RecoveryStrategy.FALLBACK_TOOL,  # Try alternative tool
        RecoveryStrategy.SIMPLIFY_TASK,  # Simplify task and retry
        RecoveryStrategy.DELEGATE  # Delegate to another agent
    ]
)

# Agent automatically recovers from errors
result = await agent.execute_task(
    {"description": "Complex task that might fail"},
    {}
)
# Agent tries multiple strategies if initial attempt fails
```

### Custom Recovery Logic

Implement custom recovery logic.

```python
class CustomRecoveryAgent(HybridAgent):
    async def _recover_from_error(
        self,
        error: Exception,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Custom recovery logic
        if isinstance(error, ToolExecutionError):
            # Try alternative tool
            return await self._try_alternative_tool(task, context)
        elif isinstance(error, LLMError):
            # Retry with different model
            return await self._retry_with_fallback_model(task, context)
        else:
            # Default recovery
            return await super()._recover_from_error(error, task, context)
```

## Observability

### Performance Metrics

Track agent performance metrics.

```python
# Get metrics
metrics = agent.get_metrics()

print(f"Total requests: {metrics.total_requests}")
print(f"Success rate: {metrics.success_rate}")
print(f"Avg response time: {metrics.avg_response_time_ms}ms")
print(f"Tool executions: {metrics.total_tool_executions}")
print(f"Cache hit rate: {metrics.cache_hit_rate}")
```

### Health Status

Monitor agent health status.

```python
# Get health status
health = agent.get_health_status()

print(f"Status: {health.status}")  # HEALTHY, DEGRADED, UNHEALTHY
print(f"Health score: {health.health_score}")  # 0-100
print(f"Issues: {health.issues}")
print(f"Last check: {health.last_check_time}")
```

### Tool Observations

Track tool execution with structured observations.

```python
from aiecs.domain.agent.models import ToolObservation

# Tool observations automatically tracked
result = await agent.execute_task(task, context)

# Get observations
observations = await agent.get_tool_observations()

for obs in observations:
    print(f"Tool: {obs.tool_name}")
    print(f"Success: {obs.success}")
    print(f"Execution time: {obs.execution_time_ms}ms")
    if obs.error:
        print(f"Error: {obs.error}")
```

## Best Practices

### 1. Tool Selection

- Use tool names for simple, stateless tools
- Use tool instances for stateful tools or tools with dependencies
- Prefer tool instances in production for better control

### 2. LLM Client Selection

- Use `BaseLLMClient` subclasses for standard providers
- Use custom clients for wrappers (retry, caching, etc.)
- Use protocol-based clients for maximum flexibility

### 3. Memory Management

- Use ContextEngine for persistent memory
- Configure compression for long conversations
- Clean up inactive sessions regularly

### 4. Configuration

- Use static config for simple cases
- Use config managers for dynamic configuration
- Reload config periodically in production

### 5. Performance

- Enable caching for expensive tools
- Use parallel execution for independent tools
- Monitor metrics and adjust limits

### 6. Error Handling

- Configure appropriate recovery strategies
- Monitor error rates and adjust strategies
- Implement custom recovery for domain-specific errors

### 7. Resource Management

- Set appropriate resource limits
- Enable throttling for production
- Monitor resource usage

### 8. Observability

- Track metrics and health status
- Use tool observations for debugging
- Monitor performance and adjust configuration

## Next Steps

- See [Migration Guide](./MIGRATION_GUIDE.md) for migration instructions
- See [Example Implementations](./EXAMPLES.md) for common patterns
- See [API Reference](../api/AGENT_API.md) for detailed API documentation

