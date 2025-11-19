# Multi-Agent Collaboration Patterns

This guide covers how to enable and use multi-agent collaboration features including task delegation, peer review, and consensus-based decision making.

## Table of Contents

1. [Overview](#overview)
2. [Enabling Collaboration](#enabling-collaboration)
3. [Task Delegation](#task-delegation)
4. [Peer Review](#peer-review)
5. [Consensus-Based Decisions](#consensus-based-decisions)
6. [Capability-Based Discovery](#capability-based-discovery)
7. [Best Practices](#best-practices)

## Overview

Multi-agent collaboration enables:

- **Task Delegation**: Delegate tasks to specialized agents
- **Peer Review**: Request peer review of task results
- **Consensus**: Make decisions through consensus
- **Capability Discovery**: Find agents with required capabilities
- **Distributed Execution**: Execute tasks across multiple agents

### When to Use Collaboration

- ✅ Complex tasks requiring multiple agents
- ✅ Quality assurance through peer review
- ✅ Specialized agent capabilities needed
- ✅ Distributed task execution
- ✅ Consensus-based decision making

## Enabling Collaboration

### Pattern 1: Basic Collaboration Setup

Enable collaboration with agent registry.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

# Create multiple agents
search_agent = HybridAgent(
    agent_id="search-agent",
    name="Search Specialist",
    llm_client=OpenAIClient(),
    tools=["web_search", "paper_search"],
    config=AgentConfiguration(goal="Search and retrieve information")
)

analysis_agent = HybridAgent(
    agent_id="analysis-agent",
    name="Analysis Specialist",
    llm_client=OpenAIClient(),
    tools=["data_analysis", "statistics"],
    config=AgentConfiguration(goal="Analyze data and generate insights")
)

# Create agent registry
agent_registry = {
    "search-agent": search_agent,
    "analysis-agent": analysis_agent
}

# Enable collaboration
coordinator = HybridAgent(
    agent_id="coordinator",
    name="Coordinator Agent",
    llm_client=OpenAIClient(),
    tools=["search"],
    config=AgentConfiguration(),
    collaboration_enabled=True,
    agent_registry=agent_registry
)

await coordinator.initialize()
```

### Pattern 2: Dynamic Registry

Build registry dynamically.

```python
# Build registry from existing agents
agent_registry = {}

# Add agents to registry
for agent in all_agents:
    agent_registry[agent.agent_id] = agent

# Enable collaboration
coordinator = HybridAgent(
    agent_id="coordinator",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    collaboration_enabled=True,
    agent_registry=agent_registry
)
```

## Task Delegation

### Pattern 1: Delegate to Specific Agent

Delegate task to a specific agent.

```python
# Delegate task to specific agent
result = await coordinator.delegate_task(
    task_description="Search for recent AI papers",
    target_agent_id="search-agent"
)

print(f"Delegated result: {result['output']}")
```

### Pattern 2: Delegate by Capability

Delegate task to agent with required capabilities.

```python
# Find capable agents
capable_agents = await coordinator.find_capable_agents(
    required_capabilities=["search", "web_scraping"]
)

if capable_agents:
    # Delegate to first capable agent
    result = await coordinator.delegate_task(
        task_description="Search and scrape web data",
        target_agent_id=capable_agents[0].agent_id
    )
```

### Pattern 3: Delegate with Context

Delegate task with context information.

```python
# Delegate with context
result = await coordinator.delegate_task(
    task_description="Analyze this data",
    target_agent_id="analysis-agent",
    context={
        "data_source": "database",
        "analysis_type": "statistical"
    }
)
```

## Peer Review

### Pattern 1: Request Peer Review

Request peer review of task result.

```python
# Execute task
result = await coordinator.execute_task(
    {"description": "Analyze data"},
    {}
)

# Request peer review
review = await coordinator.request_peer_review(
    task={"description": "Analyze data"},
    result=result,
    reviewer_id="analysis-agent"  # Specific reviewer
)

if review['approved']:
    print(f"Approved: {review['feedback']}")
else:
    print(f"Needs revision: {review['feedback']}")
```

### Pattern 2: Automatic Reviewer Selection

Let agent select reviewer automatically.

```python
# Request review without specifying reviewer
review = await coordinator.request_peer_review(
    task={"description": "Analyze data"},
    result=result
    # reviewer_id not specified - agent selects automatically
)

print(f"Reviewer: {review['reviewer_id']}")
print(f"Approved: {review['approved']}")
print(f"Feedback: {review['feedback']}")
```

### Pattern 3: Multiple Reviews

Request reviews from multiple agents.

```python
# Get multiple reviews
reviews = []

for reviewer_id in ["analysis-agent", "quality-agent"]:
    review = await coordinator.request_peer_review(
        task=task,
        result=result,
        reviewer_id=reviewer_id
    )
    reviews.append(review)

# Check if majority approve
approved_count = sum(1 for r in reviews if r['approved'])
if approved_count >= len(reviews) / 2:
    print("Majority approved")
```

## Consensus-Based Decisions

### Pattern 1: Consensus on Task

Make consensus-based decision on task.

```python
# Execute task with multiple agents and get consensus
result = await coordinator.collaborate_on_task(
    task={"description": "Analyze data"},
    strategy="consensus",  # Consensus-based decision
    required_capabilities=["analysis"]
)

print(f"Consensus result: {result['output']}")
print(f"Agreement: {result.get('agreement', 0)}%")
```

### Pattern 2: Parallel Execution with Consensus

Execute in parallel and reach consensus.

```python
# Execute in parallel and get consensus
result = await coordinator.collaborate_on_task(
    task={"description": "Research topic"},
    strategy="parallel",  # Execute in parallel
    required_capabilities=["search"]
)

# Results from multiple agents combined
print(f"Combined result: {result['output']}")
```

### Pattern 3: Weighted Consensus

Use weighted consensus based on agent expertise.

```python
# Execute with weighted consensus
result = await coordinator.collaborate_on_task(
    task={"description": "Complex analysis"},
    strategy="weighted_consensus",
    required_capabilities=["analysis"],
    agent_weights={
        "expert-agent": 0.6,
        "general-agent": 0.4
    }
)
```

## Capability-Based Discovery

### Pattern 1: Find Capable Agents

Find agents with required capabilities.

```python
# Find agents with search capability
capable_agents = await coordinator.find_capable_agents(
    required_capabilities=["search"]
)

print(f"Found {len(capable_agents)} agents with search capability")
for agent in capable_agents:
    print(f"- {agent.agent_id}: {agent.capabilities}")
```

### Pattern 2: Multiple Capabilities

Find agents with multiple capabilities.

```python
# Find agents with both search and analysis
capable_agents = await coordinator.find_capable_agents(
    required_capabilities=["search", "analysis"]
)

print(f"Found {len(capable_agents)} agents with both capabilities")
```

### Pattern 3: Capability Matching

Match tasks to agents by capabilities.

```python
# Define task requirements
task_requirements = {
    "capabilities": ["search", "web_scraping"],
    "priority": "high"
}

# Find matching agents
matching_agents = await coordinator.find_capable_agents(
    required_capabilities=task_requirements["capabilities"]
)

# Select best agent (e.g., by priority or load)
best_agent = matching_agents[0]  # Or use selection logic

# Delegate to best agent
result = await coordinator.delegate_task(
    task_description="Search and scrape",
    target_agent_id=best_agent.agent_id
)
```

## Best Practices

### 1. Use Specialized Agents

Create specialized agents for different tasks:

```python
# Specialized agents
search_agent = HybridAgent(
    agent_id="search-agent",
    tools=["web_search"],
    config=AgentConfiguration(goal="Search")
)

analysis_agent = HybridAgent(
    agent_id="analysis-agent",
    tools=["data_analysis"],
    config=AgentConfiguration(goal="Analysis")
)

# Coordinator delegates to specialists
coordinator = HybridAgent(
    collaboration_enabled=True,
    agent_registry={"search-agent": search_agent, "analysis-agent": analysis_agent}
)
```

### 2. Enable Collaboration Only When Needed

Enable collaboration only when needed:

```python
# Enable collaboration for complex tasks
if task_is_complex(task):
    agent = HybridAgent(
        collaboration_enabled=True,
        agent_registry=agent_registry
    )
else:
    # Simple task - no collaboration needed
    agent = HybridAgent(
        collaboration_enabled=False
    )
```

### 3. Monitor Collaboration Performance

Monitor collaboration performance:

```python
import time

start = time.time()
result = await coordinator.delegate_task(
    task_description="Complex task",
    target_agent_id="specialist-agent"
)
duration = time.time() - start

print(f"Delegation took {duration:.2f}s")
print(f"Result quality: {result.get('quality_score', 0)}")
```

### 4. Handle Delegation Errors

Handle delegation errors gracefully:

```python
try:
    result = await coordinator.delegate_task(
        task_description="Task",
        target_agent_id="agent-id"
    )
except AgentNotFoundError:
    logger.error("Agent not found in registry")
    # Fall back to local execution
    result = await coordinator.execute_task(task, context)
except Exception as e:
    logger.error(f"Delegation failed: {e}")
    raise
```

### 5. Use Peer Review for Quality

Use peer review for quality assurance:

```python
# Execute task
result = await agent.execute_task(task, context)

# Always request peer review for important tasks
if task_is_important(task):
    review = await agent.request_peer_review(task, result)
    if not review['approved']:
        # Revise based on feedback
        result = await agent.revise_result(result, review['feedback'])
```

## Summary

Multi-agent collaboration provides:
- ✅ Task delegation to specialists
- ✅ Peer review for quality
- ✅ Consensus-based decisions
- ✅ Capability-based discovery
- ✅ Distributed execution

**Key Takeaways**:
- Use specialized agents
- Enable collaboration when needed
- Monitor performance
- Handle errors gracefully
- Use peer review for quality

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [AgentCollaborationProtocol](../../aiecs/domain/agent/integration/protocols.py)

