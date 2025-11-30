# Graph Reasoning Tool

**Tool Name**: `graph_reasoning`  
**Category**: Knowledge Graph Reasoning  
**Status**: ✅ Complete

## Overview

The `GraphReasoningTool` provides advanced reasoning capabilities over knowledge graphs. It integrates query planning, multi-hop reasoning, logical inference, and evidence synthesis into a single unified tool for AIECS agents.

## Features

- **Query Planning**: Optimize query execution plans
- **Multi-Hop Reasoning**: Find and reason over paths in the graph
- **Logical Inference**: Apply inference rules (transitive, symmetric)
- **Evidence Synthesis**: Combine evidence from multiple sources
- **Logical Query Parsing**: Convert natural language to structured logical queries
- **Full Reasoning Pipeline**: End-to-end reasoning with all components

## Tool Registration

The tool is automatically registered with the AIECS tool registry:

```python
from aiecs.tools.knowledge_graph import GraphReasoningTool

# Tool is registered as "graph_reasoning"
```

## Input Schema

### GraphReasoningInput

```python
{
    "mode": str,  # Required: "query_plan", "multi_hop", "inference", "evidence_synthesis", "logical_query", "full_reasoning"
    "query": str,  # Required: Natural language query
    "start_entity_id": str,  # Optional: Starting entity for multi-hop reasoning
    "target_entity_id": str,  # Optional: Target entity for path finding
    "max_hops": int,  # Optional: Max hops (1-5, default: 3)
    "relation_types": List[str],  # Optional: Filter by relation types
    "optimization_strategy": str,  # Optional: "cost", "latency", "balanced" (default: "balanced")
    "apply_inference": bool,  # Optional: Apply inference rules (default: False)
    "inference_relation_type": str,  # Optional: Relation type for inference
    "inference_max_steps": int,  # Optional: Max inference steps (1-10, default: 3)
    "synthesize_evidence": bool,  # Optional: Synthesize evidence (default: True)
    "synthesis_method": str,  # Optional: "weighted_average", "max", "voting" (default: "weighted_average")
    "confidence_threshold": float  # Optional: Min confidence (0.0-1.0, default: 0.5)
}
```

## Modes

### 1. Query Plan Mode

**Mode**: `"query_plan"`

Plans and optimizes query execution.

**Example**:
```python
result = await tool.run(
    op="graph_reasoning",
    mode="query_plan",
    query="Find connections between Alice and Company X",
    optimization_strategy="balanced"
)
```

**Response**:
```python
{
    "mode": "query_plan",
    "query": "Find connections between Alice and Company X",
    "plan": {
        "steps": [
            {
                "step_id": "step_1",
                "operation": "entity_lookup",
                "depends_on": [],
                "estimated_cost": 0.3,
                "description": "Find Alice entity"
            },
            ...
        ],
        "total_cost": 1.2,
        "estimated_latency_ms": 120.0,
        "optimization_strategy": "balanced"
    }
}
```

### 2. Multi-Hop Reasoning Mode

**Mode**: `"multi_hop"`

Performs multi-hop path reasoning with optional evidence synthesis.

**Example**:
```python
result = await tool.run(
    op="graph_reasoning",
    mode="multi_hop",
    query="How is Alice connected to Company X?",
    start_entity_id="alice",
    target_entity_id="company_x",
    max_hops=3,
    synthesize_evidence=True,
    confidence_threshold=0.7
)
```

**Response**:
```python
{
    "mode": "multi_hop",
    "query": "How is Alice connected to Company X?",
    "answer": "Alice knows Bob who works at Company X",
    "confidence": 0.85,
    "evidence_count": 3,
    "evidence": [
        {
            "evidence_id": "ev_001",
            "type": "path",
            "confidence": 0.9,
            "relevance_score": 0.85,
            "explanation": "Alice -> Bob -> Company X",
            "entity_ids": ["alice", "bob", "company_x"]
        },
        ...
    ],
    "execution_time_ms": 45.2,
    "reasoning_trace": ["Planning query...", "Found 3 paths...", ...]
}
```

### 3. Inference Mode

**Mode**: `"inference"`

Applies logical inference rules to infer new relations.

**Example**:
```python
result = await tool.run(
    op="graph_reasoning",
    mode="inference",
    query="Infer transitive KNOWS relations",
    apply_inference=True,
    inference_relation_type="KNOWS",
    inference_max_steps=3
)
```

**Response**:
```python
{
    "mode": "inference",
    "relation_type": "KNOWS",
    "inferred_count": 5,
    "inferred_relations": [
        {
            "source_id": "alice",
            "target_id": "charlie",
            "relation_type": "KNOWS",
            "properties": {}
        },
        ...
    ],
    "confidence": 0.81,
    "total_steps": 2,
    "inference_trace": [
        "Step 1: Transitive: alice -> bob -> charlie => alice -> charlie",
        ...
    ]
}
```

### 4. Evidence Synthesis Mode

**Mode**: `"evidence_synthesis"`

Synthesizes pre-collected evidence (typically used with full reasoning).

**Example**:
```python
result = await tool.run(
    op="graph_reasoning",
    mode="evidence_synthesis",
    query="Synthesize evidence",
    synthesis_method="weighted_average",
    confidence_threshold=0.7
)
```

**Response**:
```python
{
    "mode": "evidence_synthesis",
    "message": "Evidence synthesis requires pre-collected evidence. Use 'full_reasoning' mode for end-to-end reasoning with synthesis.",
    "synthesis_method": "weighted_average",
    "confidence_threshold": 0.7
}
```

### 5. Logical Query Mode

**Mode**: `"logical_query"`

Parses natural language queries into structured logical forms that can be executed against the knowledge graph.

**Example**:
```python
result = await tool.run(
    op="graph_reasoning",
    mode="logical_query",
    query="Find all people who work for companies in San Francisco"
)
```

**Response**:
```python
{
    "mode": "logical_query",
    "query": "Find all people who work for companies in San Francisco",
    "logical_form": {
        "query_type": "SELECT",
        "variables": ["?person", "?company"],
        "predicates": [
            {
                "name": "type",
                "arguments": ["?person", "Person"]
            },
            {
                "name": "type",
                "arguments": ["?company", "Company"]
            },
            {
                "name": "WORKS_FOR",
                "arguments": ["?person", "?company"]
            },
            {
                "name": "LOCATED_IN",
                "arguments": ["?company", "San Francisco"]
            }
        ],
        "constraints": [
            {
                "type": "property_equals",
                "variable": "?company",
                "value": "San Francisco"
            }
        ]
    },
    "query_type": "SELECT",
    "variables": ["?person", "?company"],
    "predicates": [
        {
            "name": "WORKS_FOR",
            "arguments": ["?person", "?company"]
        },
        {
            "name": "LOCATED_IN",
            "arguments": ["?company", "San Francisco"]
        }
    ],
    "constraints": [
        {
            "type": "property_equals",
            "variable": "?company",
            "value": "San Francisco"
        }
    ]
}
```

**Use Cases:**
- Converting natural language to structured queries
- Query validation and optimization
- Building query interfaces
- Debugging complex queries

### 6. Full Reasoning Mode

**Mode**: `"full_reasoning"`

Complete reasoning pipeline with all components.

**Example**:
```python
result = await tool.run(
    op="graph_reasoning",
    mode="full_reasoning",
    query="How is Alice connected to Company X?",
    start_entity_id="alice",
    target_entity_id="company_x",
    max_hops=3,
    apply_inference=True,
    inference_relation_type="KNOWS",
    inference_max_steps=3,
    synthesize_evidence=True,
    confidence_threshold=0.5
)
```

**Response**:
```python
{
    "mode": "full_reasoning",
    "query": "How is Alice connected to Company X?",
    "steps": [
        {
            "name": "query_planning",
            "plan_steps": 3,
            "estimated_cost": 1.2,
            "estimated_latency_ms": 120.0
        },
        {
            "name": "multi_hop_reasoning",
            "evidence_collected": 5,
            "confidence": 0.85,
            "execution_time_ms": 45.2
        },
        {
            "name": "logical_inference",
            "inferred_relations": 3,
            "inference_confidence": 0.81,
            "inference_steps": 2
        },
        {
            "name": "evidence_synthesis",
            "original_evidence": 5,
            "synthesized_evidence": 3,
            "filtered_evidence": 3,
            "overall_confidence": 0.88
        }
    ],
    "answer": "Alice knows Bob who works at Company X",
    "final_confidence": 0.88,
    "evidence_count": 3,
    "top_evidence": [
        {
            "evidence_id": "ev_001",
            "type": "path",
            "confidence": 0.9,
            "relevance_score": 0.85,
            "explanation": "Alice -> Bob -> Company X"
        },
        ...
    ],
    "reasoning_trace": ["Planning query...", "Found paths...", ...]
}
```

## Use Cases

### 1. Simple Query Planning

```python
# Plan a query without execution
result = await tool.run(
    op="graph_reasoning",
    mode="query_plan",
    query="Find all people who work at tech companies"
)
```

### 2. Path Finding

```python
# Find how two entities are connected
result = await tool.run(
    op="graph_reasoning",
    mode="multi_hop",
    query="How are Alice and Company X connected?",
    start_entity_id="alice",
    target_entity_id="company_x",
    max_hops=3
)
```

### 3. Transitive Inference

```python
# Infer transitive relations
result = await tool.run(
    op="graph_reasoning",
    mode="inference",
    query="Infer transitive KNOWS relations",
    apply_inference=True,
    inference_relation_type="KNOWS",
    inference_max_steps=5
)
```

### 4. Complete Reasoning

```python
# Full reasoning pipeline
result = await tool.run(
    op="graph_reasoning",
    mode="full_reasoning",
    query="Who are the most influential people connected to Alice?",
    start_entity_id="alice",
    max_hops=4,
    apply_inference=True,
    inference_relation_type="KNOWS",
    synthesize_evidence=True,
    synthesis_method="weighted_average",
    confidence_threshold=0.7
)
```

## Optimization Strategies

### Cost Optimization

Minimizes total computational cost:

```python
result = await tool.run(
    op="graph_reasoning",
    mode="query_plan",
    query="...",
    optimization_strategy="cost"
)
```

### Latency Optimization

Maximizes parallelization to minimize latency:

```python
result = await tool.run(
    op="graph_reasoning",
    mode="query_plan",
    query="...",
    optimization_strategy="latency"
)
```

### Balanced Optimization

Balances cost and latency (default):

```python
result = await tool.run(
    op="graph_reasoning",
    mode="query_plan",
    query="...",
    optimization_strategy="balanced"
)
```

## Evidence Synthesis Methods

### Weighted Average (Default)

Averages confidence with agreement boost:

```python
result = await tool.run(
    op="graph_reasoning",
    mode="multi_hop",
    query="...",
    start_entity_id="alice",
    synthesize_evidence=True,
    synthesis_method="weighted_average"
)
```

### Max

Takes maximum confidence values:

```python
result = await tool.run(
    op="graph_reasoning",
    mode="multi_hop",
    query="...",
    start_entity_id="alice",
    synthesize_evidence=True,
    synthesis_method="max"
)
```

### Voting

Majority voting with confidence weights:

```python
result = await tool.run(
    op="graph_reasoning",
    mode="multi_hop",
    query="...",
    start_entity_id="alice",
    synthesize_evidence=True,
    synthesis_method="voting"
)
```

## Error Handling

### Missing Required Parameters

```python
# Multi-hop requires start_entity_id
try:
    result = await tool.run(
        op="graph_reasoning",
        mode="multi_hop",
        query="test"
    )
except ValueError as e:
    print(f"Error: {e}")  # "start_entity_id is required for multi-hop reasoning"
```

### Inference Requires Relation Type

```python
# Inference requires inference_relation_type
try:
    result = await tool.run(
        op="graph_reasoning",
        mode="inference",
        query="test",
        apply_inference=True
    )
except ValueError as e:
    print(f"Error: {e}")  # "inference_relation_type is required for inference mode"
```

## Default Inference Rules

The tool automatically sets up default inference rules for common relation types:

**Transitive Rules** (disabled by default):
- `KNOWS`
- `FOLLOWS`
- `CONNECTED_TO`
- `RELATED_TO`

**Symmetric Rules** (disabled by default):
- `FRIEND_OF`
- `COLLEAGUE_OF`
- `PARTNER_WITH`
- `SIBLING_OF`

Rules are enabled when `apply_inference=True` and `inference_relation_type` matches.

## Performance Considerations

- **Query Planning**: Fast (synchronous, no I/O)
- **Multi-Hop Reasoning**: Moderate (depends on graph size and max_hops)
- **Inference**: Moderate (depends on relation count and max_steps)
- **Evidence Synthesis**: Fast (in-memory operations)
- **Full Reasoning**: Slowest (combines all components)

## Integration with AIECS Agents

The tool is automatically available to AIECS agents:

```python
from aiecs.agent import Agent

agent = Agent(...)

# Agent can use graph_reasoning tool
response = await agent.run(
    "How is Alice connected to Company X?",
    tools=["graph_reasoning"]
)
```

## Related Tools

- **GraphSearchTool**: Basic graph search operations
- **KnowledgeGraphBuilderTool**: Build and manage knowledge graphs

## Examples

See `docs/knowledge_graph/examples/` for complete examples:
- Multi-hop question answering
- Logical inference over knowledge
- Evidence-based reasoning

## API Reference

### GraphReasoningTool

**Location**: `aiecs.tools.knowledge_graph.graph_reasoning_tool`

**Methods**:
- `__init__(graph_store: GraphStore)`: Initialize tool
- `_execute(validated_input: GraphReasoningInput) -> Dict[str, Any]`: Execute reasoning

**Registered As**: `"graph_reasoning"`

---

**Status**: ✅ Complete  
**Tests**: 11/11 passing  
**Documentation**: Complete  
**Ready for**: Production use

