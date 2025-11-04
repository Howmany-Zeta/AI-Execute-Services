# Base AI Agent Examples

## Quick Start

### 1. Creating an LLM Agent

```python
from aiecs.domain.agent import LLMAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

# Create LLM client
llm_client = OpenAIClient()

# Configure agent
config = AgentConfiguration(
    goal="Assist users with coding questions",
    llm_model="gpt-4",
    temperature=0.7
)

# Create agent
agent = LLMAgent(
    agent_id="assistant-1",
    name="Code Assistant",
    llm_client=llm_client,
    config=config
)

# Initialize and activate
await agent.initialize()
await agent.activate()

# Execute task
task = {"description": "Explain recursion in Python"}
result = await agent.execute_task(task, {})
print(result["output"])
```

### 2. Creating a Tool Agent

```python
from aiecs.domain.agent import ToolAgent, AgentConfiguration

# Configure agent with tools
config = AgentConfiguration(
    goal="Search and retrieve information"
)

# Create agent with available tools
agent = ToolAgent(
    agent_id="searcher-1",
    name="Search Agent",
    tools=["search", "apisource"],
    config=config
)

await agent.initialize()
await agent.activate()

# Execute tool task
task = {
    "tool": "search",
    "operation": "search_web",
    "parameters": {"query": "AI agents"}
}
result = await agent.execute_task(task, {})
```

### 3. Creating a Hybrid Agent (ReAct Pattern)

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

llm_client = OpenAIClient()

config = AgentConfiguration(
    goal="Research and analyze information using tools",
    llm_model="gpt-4",
    temperature=0.5
)

# Hybrid agent combines LLM reasoning with tool usage
agent = HybridAgent(
    agent_id="researcher-1",
    name="Research Agent",
    llm_client=llm_client,
    tools=["search", "apisource"],
    config=config,
    max_iterations=10
)

await agent.initialize()
await agent.activate()

# Agent will use ReAct loop: Think → Act → Observe
task = {"description": "Research the latest trends in AI agents"}
result = await agent.execute_task(task, {})

# View reasoning steps
for step in result["reasoning_steps"]:
    print(f"{step['type']}: {step.get('content', '')}")
```

### 4. Using Agent Lifecycle Management

```python
from aiecs.domain.agent import (
    LLMAgent,
    AgentLifecycleManager,
    get_global_registry
)

# Create lifecycle manager
lifecycle = AgentLifecycleManager()

# Create and register agent
agent = LLMAgent(...)
await lifecycle.create_and_initialize(agent)

# Get registry to track agents
registry = get_global_registry()
print(f"Active agents: {registry.count()}")

# Get agent status
status = lifecycle.get_agent_status(agent.agent_id)
print(f"Agent state: {status['state']}")

# Shutdown when done
await lifecycle.shutdown(agent.agent_id)
```

### 5. Using Prompt Templates

```python
from aiecs.domain.agent import PromptTemplate, ChatPromptTemplate, MessageTemplate

# Simple string template
template = PromptTemplate(
    "You are a {role}. Your task is to {task}.",
    required_variables=["role", "task"]
)
prompt = template.format(role="developer", task="write clean code")

# Chat template with multiple messages
chat_template = ChatPromptTemplate([
    MessageTemplate("system", "You are a {role}."),
    MessageTemplate("user", "{question}")
])
messages = chat_template.format_messages(
    role="helpful assistant",
    question="What is Python?"
)
```

### 6. Conversation Memory

```python
from aiecs.domain.agent import ConversationMemory

# Create memory for agent
memory = ConversationMemory(agent_id="agent-1")

# Create session
session_id = memory.create_session()

# Add messages
memory.add_message(session_id, "user", "Hello")
memory.add_message(session_id, "assistant", "Hi! How can I help?")

# Get history
history = memory.get_history(session_id, limit=10)
formatted = memory.format_history(session_id)
print(formatted)
```

### 7. Role-Based Configuration

```python
from aiecs.domain.agent import RoleConfiguration, get_role_template

# Use predefined role template
role_config = get_role_template("developer")
agent_config = role_config.to_agent_config()

# Or load from file
role_config = RoleConfiguration.load_from_file("roles/researcher.yaml")

# Or create custom role
role_config = RoleConfiguration(
    role_name="analyst",
    goal="Analyze data and provide insights",
    backstory="Expert data analyst",
    temperature=0.4
)
```

### 8. Context Compression

```python
from aiecs.domain.agent import ContextCompressor, CompressionStrategy
from aiecs.llm import LLMMessage

messages = [...]  # List of LLMMessage

# Compress to fit token limit
compressor = ContextCompressor(
    max_tokens=4000,
    strategy=CompressionStrategy.PRESERVE_RECENT
)
compressed = compressor.compress_messages(messages)
```

### 9. Migration from Legacy Agents

```python
from aiecs.domain.agent import (
    LegacyAgentWrapper,
    convert_legacy_config,
    convert_langchain_prompt
)

# Wrap legacy agent
legacy_agent = SomeLegacyAgent()
wrapped = LegacyAgentWrapper(legacy_agent)

# Use with new interface
result = await wrapped.execute_task(task, context)

# Convert legacy configuration
legacy_config = {"model": "gpt-4", "temp": 0.7}
new_config = convert_legacy_config(legacy_config)

# Convert LangChain prompts
langchain_prompt = "You are a {role}. Task: {task}"
prompt_template = convert_langchain_prompt(langchain_prompt)
```

### 10. Using Retry Logic in Agent Implementations

```python
from aiecs.domain.agent import BaseAIAgent, AgentConfiguration, RetryPolicy, AgentType

class MyCustomAgent(BaseAIAgent):
    async def _initialize(self):
        pass
    
    async def _shutdown(self):
        pass
    
    async def execute_task(self, task, context):
        # Wrap internal execution with retry logic
        async def _internal_execute():
            # Your actual task execution logic
            # This will automatically retry on transient errors
            if "fail" in task.get("description", ""):
                raise ConnectionError("Network issue")
            return {"success": True, "output": "Done"}
        
        # Use built-in retry helper - automatically uses agent's retry policy
        return await self._execute_with_retry(_internal_execute)
    
    async def process_message(self, message, sender_id=None):
        return await self.execute_task({"description": message}, {"sender_id": sender_id})

# Configure retry policy
retry_policy = RetryPolicy(
    max_retries=5,
    base_delay=1.0,
    max_delay=60.0,
    exponential_factor=2.0,
    jitter_factor=0.2
)

config = AgentConfiguration(
    goal="Process tasks with automatic retry",
    retry_policy=retry_policy
)

agent = MyCustomAgent(
    agent_id="retry-agent",
    name="Retry Agent",
    agent_type=AgentType.TASK_EXECUTOR,
    config=config
)

# Retry will automatically handle transient errors
await agent.initialize()
result = await agent.execute_task({"description": "test"}, {})
```

### 11. Observability

```python
from aiecs.domain.agent import (
    AgentController,
    LoggingObserver,
    MetricsObserver
)

# Create controller
controller = AgentController(agent)

# Add observers
controller.add_observer(LoggingObserver())
metrics_observer = MetricsObserver()
controller.add_observer(metrics_observer)

# Execute with observation
result = await controller.execute_task_with_observation(task, context)

# Get metrics
metrics = metrics_observer.get_metrics()
print(f"Tool calls: {metrics['tool_calls']}")
```

## Best Practices

1. **Always initialize and activate agents** before using them
2. **Use lifecycle management** for proper cleanup
3. **Choose the right agent type**:
   - `LLMAgent`: Pure reasoning tasks
   - `ToolAgent`: Direct tool execution
   - `HybridAgent`: Complex tasks requiring both reasoning and tools
4. **Use built-in retry logic** via `_execute_with_retry()` for automatic retry with exponential backoff
5. **Configure retry policies** in AgentConfiguration for production use
6. **Use conversation memory** for multi-turn interactions
7. **Compress context** when dealing with long conversations
8. **Monitor with observers** for debugging and metrics

## See Also

- [OpenSpec Proposal](../../openspec/changes/add-base-ai-agent-model/proposal.md)
- [Design Decisions](../../openspec/changes/add-base-ai-agent-model/design.md)
- [Migration Guide](../../openspec/changes/add-base-ai-agent-model/MIGRATION_GUIDE.md)

