# Multi-Agent System Design Guide

This guide covers architectural patterns and best practices for designing multi-agent systems with task delegation, peer review, consensus, and distributed execution.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Agent Specialization](#agent-specialization)
4. [Coordination Patterns](#coordination-patterns)
5. [Communication Patterns](#communication-patterns)
6. [Scalability Considerations](#scalability-considerations)
7. [Best Practices](#best-practices)

## Overview

Multi-agent systems enable:

- **Specialization**: Each agent specializes in specific tasks
- **Scalability**: Distribute load across multiple agents
- **Reliability**: Redundancy and peer review
- **Efficiency**: Parallel execution and delegation
- **Quality**: Consensus and peer review

### Design Principles

1. **Specialization**: Agents should specialize in specific domains
2. **Coordination**: Clear coordination mechanisms
3. **Communication**: Efficient inter-agent communication
4. **Scalability**: Design for horizontal scaling
5. **Reliability**: Redundancy and error handling

## Architecture Patterns

### Pattern 1: Coordinator-Worker

Coordinator delegates to specialized workers.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

# Create specialized workers
search_worker = HybridAgent(
    agent_id="search-worker",
    name="Search Specialist",
    llm_client=OpenAIClient(),
    tools=["web_search", "paper_search"],
    config=AgentConfiguration(goal="Search and retrieve information")
)

analysis_worker = HybridAgent(
    agent_id="analysis-worker",
    name="Analysis Specialist",
    llm_client=OpenAIClient(),
    tools=["data_analysis", "statistics"],
    config=AgentConfiguration(goal="Analyze data")
)

# Create coordinator
coordinator = HybridAgent(
    agent_id="coordinator",
    name="Coordinator",
    llm_client=OpenAIClient(),
    tools=[],
    config=AgentConfiguration(goal="Coordinate tasks"),
    collaboration_enabled=True,
    agent_registry={
        "search-worker": search_worker,
        "analysis-worker": analysis_worker
    }
)

# Coordinator delegates to workers
result = await coordinator.delegate_task(
    task_description="Search and analyze",
    target_agent_id="search-worker"
)
```

### Pattern 2: Hierarchical

Hierarchical agent structure with managers and workers.

```python
# Level 1: Managers
search_manager = HybridAgent(
    agent_id="search-manager",
    name="Search Manager",
    llm_client=llm_client,
    tools=[],
    config=config,
    collaboration_enabled=True,
    agent_registry={
        "search-worker-1": search_worker_1,
        "search-worker-2": search_worker_2
    }
)

# Level 2: Top-level coordinator
top_coordinator = HybridAgent(
    agent_id="top-coordinator",
    name="Top Coordinator",
    llm_client=llm_client,
    tools=[],
    config=config,
    collaboration_enabled=True,
    agent_registry={
        "search-manager": search_manager,
        "analysis-manager": analysis_manager
    }
)
```

### Pattern 3: Peer-to-Peer

Peer-to-peer agents with mutual collaboration.

```python
# Create peer agents
agent1 = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    collaboration_enabled=True,
    agent_registry={
        "agent-2": agent2,
        "agent-3": agent3
    }
)

agent2 = HybridAgent(
    agent_id="agent-2",
    llm_client=llm_client,
    tools=["analysis"],
    config=config,
    collaboration_enabled=True,
    agent_registry={
        "agent-1": agent1,
        "agent-3": agent3
    }
)

# Agents can delegate to each other
result = await agent1.delegate_task(
    task_description="Analyze data",
    target_agent_id="agent-2"
)
```

## Agent Specialization

### Pattern 1: Domain Specialization

Specialize agents by domain.

```python
# Domain-specific agents
research_agent = HybridAgent(
    agent_id="research-agent",
    name="Research Specialist",
    tools=["web_search", "paper_search", "citation_search"],
    config=AgentConfiguration(goal="Research and information retrieval")
)

analysis_agent = HybridAgent(
    agent_id="analysis-agent",
    name="Analysis Specialist",
    tools=["data_analysis", "statistics", "visualization"],
    config=AgentConfiguration(goal="Data analysis and insights")
)

writing_agent = HybridAgent(
    agent_id="writing-agent",
    name="Writing Specialist",
    tools=["text_generation", "editing"],
    config=AgentConfiguration(goal="Content creation and editing")
)
```

### Pattern 2: Tool Specialization

Specialize agents by tool capabilities.

```python
# Tool-specialized agents
api_agent = HybridAgent(
    agent_id="api-agent",
    name="API Specialist",
    tools=["rest_api", "graphql_api"],
    config=config
)

database_agent = HybridAgent(
    agent_id="db-agent",
    name="Database Specialist",
    tools=["sql_query", "nosql_query"],
    config=config
)
```

### Pattern 3: Task Complexity Specialization

Specialize agents by task complexity.

```python
# Simple task agent
simple_agent = HybridAgent(
    agent_id="simple-agent",
    name="Simple Task Handler",
    tools=["basic_tools"],
    config=AgentConfiguration(max_iterations=3)
)

# Complex task agent
complex_agent = HybridAgent(
    agent_id="complex-agent",
    name="Complex Task Handler",
    tools=["advanced_tools"],
    config=AgentConfiguration(max_iterations=10)
)
```

## Coordination Patterns

### Pattern 1: Task Routing

Route tasks to appropriate agents.

```python
class TaskRouter:
    def __init__(self, agent_registry):
        self.agent_registry = agent_registry
    
    async def route_task(self, task):
        """Route task to appropriate agent"""
        task_type = self._classify_task(task)
        
        if task_type == "search":
            return await self.agent_registry["search-agent"].execute_task(task, {})
        elif task_type == "analysis":
            return await self.agent_registry["analysis-agent"].execute_task(task, {})
        else:
            return await self.agent_registry["general-agent"].execute_task(task, {})
```

### Pattern 2: Load Balancing

Balance load across agents.

```python
class LoadBalancer:
    def __init__(self, agent_registry):
        self.agent_registry = agent_registry
        self.agent_loads = {agent_id: 0 for agent_id in agent_registry}
    
    async def route_task(self, task):
        """Route to least loaded agent"""
        # Find least loaded agent
        least_loaded = min(
            self.agent_loads.items(),
            key=lambda x: x[1]
        )[0]
        
        # Increment load
        self.agent_loads[least_loaded] += 1
        
        try:
            result = await self.agent_registry[least_loaded].execute_task(task, {})
        finally:
            # Decrement load
            self.agent_loads[least_loaded] -= 1
        
        return result
```

### Pattern 3: Consensus-Based Decisions

Make decisions through consensus.

```python
# Execute task with multiple agents and get consensus
result = await coordinator.collaborate_on_task(
    task={"description": "Analyze data"},
    strategy="consensus",
    required_capabilities=["analysis"]
)

if result.get('agreement', 0) > 0.8:  # 80% agreement
    print("High consensus - result reliable")
else:
    print("Low consensus - result uncertain")
```

## Communication Patterns

### Pattern 1: Direct Delegation

Direct task delegation between agents.

```python
# Agent 1 delegates directly to Agent 2
result = await agent1.delegate_task(
    task_description="Specialized task",
    target_agent_id="agent-2"
)
```

### Pattern 2: Peer Review

Peer review for quality assurance.

```python
# Execute task
result = await agent1.execute_task(task, context)

# Request peer review
review = await agent1.request_peer_review(
    task=task,
    result=result,
    reviewer_id="agent-2"
)

if review['approved']:
    # Use result
    return result
else:
    # Revise based on feedback
    return await agent1.revise_result(result, review['feedback'])
```

### Pattern 3: Broadcast

Broadcast tasks to multiple agents.

```python
# Broadcast to all capable agents
capable_agents = await coordinator.find_capable_agents(
    required_capabilities=["search"]
)

# Execute with all agents
results = await asyncio.gather(*[
    agent.execute_task(task, context)
    for agent in capable_agents
])

# Aggregate results
aggregated_result = aggregate_results(results)
```

## Scalability Considerations

### Pattern 1: Horizontal Scaling

Scale agents horizontally.

```python
# Create multiple instances of same agent type
search_agents = [
    HybridAgent(
        agent_id=f"search-agent-{i}",
        name=f"Search Agent {i}",
        tools=["search"],
        config=config
    )
    for i in range(5)  # 5 instances
]

# Load balance across instances
load_balancer = LoadBalancer({agent.agent_id: agent for agent in search_agents})
```

### Pattern 2: Agent Pooling

Use agent pools for better resource utilization.

```python
class AgentPool:
    def __init__(self, agent_type, pool_size=10):
        self.pool = asyncio.Queue()
        for i in range(pool_size):
            agent = create_agent(agent_type, agent_id=f"{agent_type}-{i}")
            self.pool.put_nowait(agent)
    
    async def get_agent(self):
        """Get agent from pool"""
        return await self.pool.get()
    
    async def return_agent(self, agent):
        """Return agent to pool"""
        await self.pool.put(agent)

# Use agent pool
pool = AgentPool("search", pool_size=10)
agent = await pool.get_agent()
try:
    result = await agent.execute_task(task, context)
finally:
    await pool.return_agent(agent)
```

### Pattern 3: Distributed Execution

Distribute execution across multiple nodes.

```python
# Agents on different nodes
node1_agents = {
    "agent-1": agent1,
    "agent-2": agent2
}

node2_agents = {
    "agent-3": agent3,
    "agent-4": agent4
}

# Coordinator can delegate across nodes
coordinator = HybridAgent(
    agent_id="coordinator",
    collaboration_enabled=True,
    agent_registry={**node1_agents, **node2_agents}
)
```

## Best Practices

### 1. Design for Specialization

Design agents with clear specializations:

```python
# Good: Clear specialization
search_agent = HybridAgent(
    agent_id="search-agent",
    tools=["web_search"],
    config=AgentConfiguration(goal="Search")
)

# Bad: Generic agent doing everything
generic_agent = HybridAgent(
    agent_id="generic-agent",
    tools=["search", "analysis", "writing", "translation", ...]  # Too many
)
```

### 2. Use Coordinator Pattern

Use coordinator for complex workflows:

```python
# Coordinator orchestrates workflow
coordinator = HybridAgent(
    collaboration_enabled=True,
    agent_registry={
        "search": search_agent,
        "analysis": analysis_agent,
        "writing": writing_agent
    }
)

# Coordinator manages workflow
result = await coordinator.orchestrate_workflow(task)
```

### 3. Implement Peer Review

Use peer review for quality:

```python
# Always review important results
if task_is_important(task):
    result = await agent.execute_task(task, context)
    review = await agent.request_peer_review(task, result)
    if not review['approved']:
        result = await agent.revise_result(result, review['feedback'])
```

### 4. Monitor Agent Health

Monitor health of all agents:

```python
# Monitor all agents
for agent_id, agent in agent_registry.items():
    health = agent.get_health_status()
    if health['status'] != 'healthy':
        logger.warning(f"Agent {agent_id} is {health['status']}")
```

### 5. Handle Agent Failures

Handle agent failures gracefully:

```python
try:
    result = await agent.delegate_task(task, target_agent_id="agent-2")
except AgentNotFoundError:
    # Fall back to another agent
    result = await agent.delegate_task(task, target_agent_id="agent-3")
except Exception as e:
    # Handle other errors
    logger.error(f"Delegation failed: {e}")
    result = await agent.execute_task(task, context)  # Fall back to local
```

## Summary

Multi-agent system design provides:
- ✅ Specialization and efficiency
- ✅ Scalability and load distribution
- ✅ Reliability through redundancy
- ✅ Quality through peer review
- ✅ Flexibility through delegation

**Key Design Principles**:
- Specialize agents by domain/tool
- Use coordinator pattern
- Implement peer review
- Monitor agent health
- Handle failures gracefully

For more details, see:
- [Collaboration](./COLLABORATION.md)
- [Agent Integration Guide](./AGENT_INTEGRATION.md)

