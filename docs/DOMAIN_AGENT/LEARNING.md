# Agent Learning and Adaptation

This guide covers how to enable and use agent learning features to improve performance over time by learning from past experiences and recommending optimal approaches.

## Table of Contents

1. [Overview](#overview)
2. [Enabling Learning](#enabling-learning)
3. [Recording Experiences](#recording-experiences)
4. [Getting Recommendations](#getting-recommendations)
5. [Experience Analysis](#experience-analysis)
6. [Adaptation Strategies](#adaptation-strategies)
7. [Best Practices](#best-practices)

## Overview

Agent learning enables:

- **Experience Recording**: Track task execution experiences
- **Approach Recommendation**: Recommend optimal approaches based on history
- **Performance Improvement**: Learn from successes and failures
- **Adaptation**: Adapt strategies based on past experiences
- **Quality Insights**: Understand what works best for different tasks

### When to Use Learning

- ✅ Repetitive tasks with varying approaches
- ✅ Performance optimization needed
- ✅ Quality improvement desired
- ✅ Adaptive behavior required
- ✅ Learning from failures important

## Enabling Learning

### Pattern 1: Basic Learning Setup

Enable learning with default configuration.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search", "calculator"],
    config=AgentConfiguration(),
    learning_enabled=True  # Enable learning
)

await agent.initialize()
```

### Pattern 2: Learning with Experience Limit

Configure maximum number of experiences to store.

```python
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    learning_enabled=True,
    max_experiences=1000  # Store up to 1000 experiences
)
```

## Recording Experiences

### Pattern 1: Automatic Recording

Agent automatically records experiences when learning is enabled.

```python
# Execute task - experience recorded automatically
result = await agent.execute_task(
    {"description": "Analyze data", "type": "data_analysis"},
    {}
)
# Experience recorded automatically with success/failure, execution time, etc.
```

### Pattern 2: Manual Recording

Manually record experiences for custom tracking.

```python
from aiecs.domain.agent.models import Experience

# Record experience manually
await agent.record_experience(
    task={
        "description": "Analyze sales data",
        "type": "data_analysis",
        "complexity": "medium"
    },
    result={
        "success": True,
        "execution_time": 2.5,
        "quality_score": 0.95
    },
    approach="parallel_tools",
    tools_used=["pandas", "numpy"]
)
```

### Pattern 3: Record After Execution

Record experience after task execution.

```python
# Execute task
result = await agent.execute_task(task, context)

# Record experience with result details
await agent.record_experience(
    task=task,
    result={
        "success": result.get("success", True),
        "execution_time": result.get("execution_time", 0),
        "quality_score": result.get("quality_score"),
        "iterations": result.get("iterations", 1)
    },
    approach="react_loop",
    tools_used=result.get("tools_used", [])
)
```

### Pattern 4: Record Failed Experiences

Record failed experiences for learning.

```python
try:
    result = await agent.execute_task(task, context)
    await agent.record_experience(
        task=task,
        result={"success": True, **result},
        approach="standard"
    )
except Exception as e:
    # Record failure
    await agent.record_experience(
        task=task,
        result={
            "success": False,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "execution_time": 0
        },
        approach="standard"
    )
```

## Getting Recommendations

### Pattern 1: Get Recommended Approach

Get recommended approach for a task.

```python
# Get recommended approach
recommendation = await agent.get_recommended_approach(
    task={"description": "Analyze data", "type": "data_analysis"}
)

if recommendation:
    print(f"Recommended approach: {recommendation['approach']}")
    print(f"Confidence: {recommendation['confidence']}")
    print(f"Based on {recommendation['experience_count']} past experiences")
    
    # Use recommended approach
    result = await agent.execute_task_with_approach(
        task,
        approach=recommendation['approach']
    )
```

### Pattern 2: Compare Approaches

Compare multiple approaches based on history.

```python
task = {"description": "Analyze data", "type": "data_analysis"}

# Get recommendations for different approaches
approaches = ["parallel_tools", "sequential", "hybrid"]

for approach in approaches:
    recommendation = await agent.get_recommended_approach(
        task,
        approach_filter=approach
    )
    if recommendation:
        print(f"{approach}: {recommendation['confidence']} confidence")
```

### Pattern 3: Task-Specific Recommendations

Get recommendations for specific task types.

```python
# Get recommendation for specific task type
recommendation = await agent.get_recommended_approach(
    task={"type": "data_analysis"}
)

# Use recommendation
if recommendation:
    result = await agent.execute_task(
        task,
        context={"recommended_approach": recommendation['approach']}
    )
```

## Experience Analysis

### Pattern 1: Get All Experiences

Retrieve all recorded experiences.

```python
# Get all experiences
experiences = await agent.get_experiences()

print(f"Total experiences: {len(experiences)}")

# Analyze experiences
successful = [e for e in experiences if e.success]
failed = [e for e in experiences if not e.success]

print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")
print(f"Success rate: {len(successful) / len(experiences) * 100:.1f}%")
```

### Pattern 2: Filter Experiences

Filter experiences by criteria.

```python
# Get experiences for specific task type
data_analysis_experiences = [
    e for e in await agent.get_experiences()
    if e.task_type == "data_analysis"
]

# Get successful experiences
successful_experiences = [
    e for e in await agent.get_experiences()
    if e.success
]

# Get experiences with high quality
high_quality_experiences = [
    e for e in await agent.get_experiences()
    if e.quality_score and e.quality_score > 0.9
]
```

### Pattern 3: Analyze Performance

Analyze performance by approach.

```python
experiences = await agent.get_experiences()

# Group by approach
by_approach = {}
for exp in experiences:
    if exp.approach not in by_approach:
        by_approach[exp.approach] = []
    by_approach[exp.approach].append(exp)

# Analyze each approach
for approach, exps in by_approach.items():
    avg_time = sum(e.execution_time for e in exps) / len(exps)
    success_rate = sum(1 for e in exps if e.success) / len(exps)
    avg_quality = sum(e.quality_score for e in exps if e.quality_score) / len([e for e in exps if e.quality_score])
    
    print(f"{approach}:")
    print(f"  Avg time: {avg_time:.2f}s")
    print(f"  Success rate: {success_rate:.1%}")
    print(f"  Avg quality: {avg_quality:.2f}")
```

## Adaptation Strategies

### Pattern 1: Adaptive Approach Selection

Select approach based on recommendations.

```python
# Get recommendation
recommendation = await agent.get_recommended_approach(task)

if recommendation and recommendation['confidence'] > 0.7:
    # Use recommended approach with high confidence
    result = await agent.execute_task_with_approach(
        task,
        approach=recommendation['approach']
    )
else:
    # Use default approach
    result = await agent.execute_task(task, context)
```

### Pattern 2: Learning from Failures

Adapt based on failure patterns.

```python
# Get failed experiences
failed_experiences = [
    e for e in await agent.get_experiences()
    if not e.success
]

# Analyze failure patterns
error_types = {}
for exp in failed_experiences:
    if exp.error_type:
        error_types[exp.error_type] = error_types.get(exp.error_type, 0) + 1

# Adapt based on common errors
if error_types.get("timeout", 0) > 5:
    # Increase timeout for similar tasks
    task["timeout"] = 60
```

### Pattern 3: Performance-Based Adaptation

Adapt based on performance metrics.

```python
# Get experiences for task type
experiences = [
    e for e in await agent.get_experiences()
    if e.task_type == task.get("type")
]

if experiences:
    # Find best performing approach
    best_approach = max(
        experiences,
        key=lambda e: e.quality_score if e.quality_score else 0
    )
    
    # Use best approach
    result = await agent.execute_task_with_approach(
        task,
        approach=best_approach.approach
    )
```

## Best Practices

### 1. Enable Learning for Repetitive Tasks

Enable learning when tasks are repeated:

```python
# Enable learning for repetitive tasks
if task_is_repetitive(task):
    agent = HybridAgent(
        learning_enabled=True,
        max_experiences=1000
    )
```

### 2. Record Comprehensive Experiences

Record comprehensive experience data:

```python
await agent.record_experience(
    task=task,
    result={
        "success": True,
        "execution_time": duration,
        "quality_score": quality,
        "iterations": iterations,
        "context_size": context_size
    },
    approach=approach,
    tools_used=tools_used
)
```

### 3. Use Recommendations Wisely

Use recommendations with confidence thresholds:

```python
recommendation = await agent.get_recommended_approach(task)

if recommendation and recommendation['confidence'] > 0.7:
    # High confidence - use recommendation
    use_approach(recommendation['approach'])
elif recommendation:
    # Low confidence - consider but verify
    consider_approach(recommendation['approach'])
else:
    # No recommendation - use default
    use_default_approach()
```

### 4. Analyze Experience Patterns

Regularly analyze experience patterns:

```python
# Analyze experiences periodically
experiences = await agent.get_experiences()

# Find patterns
successful_approaches = [
    e.approach for e in experiences
    if e.success and e.quality_score and e.quality_score > 0.9
]

# Use most successful approaches
if successful_approaches:
    most_common = max(set(successful_approaches), key=successful_approaches.count)
    print(f"Most successful approach: {most_common}")
```

### 5. Learn from Failures

Focus on learning from failures:

```python
# Record failures with detailed information
try:
    result = await agent.execute_task(task, context)
except Exception as e:
    await agent.record_experience(
        task=task,
        result={
            "success": False,
            "error_type": type(e).__name__,
            "error_message": str(e)
        },
        approach=approach
    )
    
    # Analyze failure for improvement
    analyze_failure(e, task, approach)
```

## Summary

Agent learning provides:
- ✅ Experience recording
- ✅ Approach recommendations
- ✅ Performance improvement
- ✅ Adaptation strategies
- ✅ Quality insights

**Key Takeaways**:
- Enable for repetitive tasks
- Record comprehensive experiences
- Use recommendations wisely
- Analyze patterns regularly
- Learn from failures

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Experience Model](../../aiecs/domain/agent/models.py)

