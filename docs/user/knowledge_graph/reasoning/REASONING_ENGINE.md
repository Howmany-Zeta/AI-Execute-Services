# Knowledge Graph Reasoning Engine

**Status**: ✅ Complete  
**Version**: 1.0.0  
**Phase**: 4 - Reasoning Engine

## Overview

The Knowledge Graph Reasoning Engine provides advanced reasoning capabilities over knowledge graphs. It combines query planning, multi-hop reasoning, logical inference, and evidence synthesis to answer complex questions and discover implicit knowledge.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Reasoning Engine                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Query     │  │   Multi-Hop  │  │  Inference   │     │
│  │   Planner    │→ │  Reasoning   │→ │   Engine     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            ↓                                │
│                  ┌──────────────────┐                       │
│                  │    Evidence      │                       │
│                  │  Synthesizer     │                       │
│                  └──────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Query Planner

**Purpose**: Translates natural language queries into optimized execution plans.

**Key Features**:
- Query decomposition into steps
- Dependency resolution
- Cost and latency estimation
- Three optimization strategies (cost, latency, balanced)

**Example**:
```python
from aiecs.application.knowledge_graph.reasoning import QueryPlanner

planner = QueryPlanner(graph_store)
plan = planner.plan_query("Who works at companies that Alice knows people at?")

# Optimize for minimal cost
optimized_plan = planner.optimize_plan(plan, OptimizationStrategy.MINIMIZE_COST)
```

### 2. Multi-Hop Reasoning Engine

**Purpose**: Finds and reasons over multi-hop paths in the knowledge graph.

**Key Features**:
- Path finding with depth limits
- Evidence collection from paths
- Path ranking by relevance
- Answer generation from evidence
- Query execution with trace

**Example**:
```python
from aiecs.application.knowledge_graph.reasoning import ReasoningEngine

engine = ReasoningEngine(graph_store)
result = await engine.reason(
    query="How is Alice connected to Company X?",
    context={"start_entity_id": "alice", "target_entity_id": "company_x"},
    max_hops=3
)

print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence}")
print(f"Evidence: {result.evidence_count} pieces")
```

### 3. Inference Engine

**Purpose**: Applies logical inference rules to discover implicit knowledge.

**Key Features**:
- Transitive inference (A→B, B→C ⇒ A→C)
- Symmetric inference (A→B ⇒ B→A)
- Rule-based inference
- Inference result caching
- Full explainability (trace inference steps)

**Example**:
```python
from aiecs.application.knowledge_graph.reasoning import InferenceEngine
from aiecs.domain.knowledge_graph.models.inference_rule import InferenceRule, RuleType

engine = InferenceEngine(graph_store)

# Add transitive rule for KNOWS relations
engine.add_rule(InferenceRule(
    rule_id="transitive_knows",
    rule_type=RuleType.TRANSITIVE,
    relation_type="KNOWS",
    description="Transitive closure for KNOWS"
))

# Apply inference
result = await engine.infer_relations(
    relation_type="KNOWS",
    max_steps=5,
    use_cache=True
)

print(f"Inferred {len(result.inferred_relations)} new relations")
```

### 4. Evidence Synthesizer

**Purpose**: Combines evidence from multiple sources for robust conclusions.

**Key Features**:
- Evidence grouping by overlap
- Multiple synthesis methods (weighted average, max, voting)
- Confidence boosting from agreement
- Contradiction detection
- Reliability ranking

**Example**:
```python
from aiecs.application.knowledge_graph.reasoning import EvidenceSynthesizer

synthesizer = EvidenceSynthesizer(
    confidence_threshold=0.7,
    contradiction_threshold=0.3
)

# Synthesize overlapping evidence
synthesized = synthesizer.synthesize_evidence(
    evidence_list,
    method="weighted_average"
)

# Estimate overall confidence
overall_confidence = synthesizer.estimate_overall_confidence(synthesized)

# Rank by reliability
ranked = synthesizer.rank_by_reliability(synthesized)
```

## Reasoning Workflow

### Complete Reasoning Pipeline

```python
from aiecs.tools.knowledge_graph import GraphReasoningTool

tool = GraphReasoningTool(graph_store)

# Full reasoning with all components
result = await tool._execute(GraphReasoningInput(
    mode="full_reasoning",
    query="How is Alice connected to Company X?",
    start_entity_id="alice",
    target_entity_id="company_x",
    max_hops=3,
    apply_inference=True,
    inference_relation_type="KNOWS",
    synthesize_evidence=True,
    confidence_threshold=0.7
))

# Results include:
# - Query plan steps
# - Multi-hop reasoning results
# - Inferred relations (if enabled)
# - Synthesized evidence
# - Final answer with confidence
# - Complete reasoning trace
```

### Step-by-Step Workflow

```
1. Query Planning
   ├─ Parse natural language query
   ├─ Identify query type (vector, traversal, path finding, etc.)
   ├─ Decompose into executable steps
   └─ Optimize for cost/latency

2. Multi-Hop Reasoning
   ├─ Execute query plan
   ├─ Find paths in knowledge graph
   ├─ Collect evidence from paths
   ├─ Rank evidence by relevance
   └─ Generate answer

3. Logical Inference (Optional)
   ├─ Apply inference rules
   ├─ Discover implicit relations
   ├─ Track inference steps
   └─ Cache results

4. Evidence Synthesis
   ├─ Group overlapping evidence
   ├─ Combine using synthesis method
   ├─ Boost confidence from agreement
   ├─ Detect contradictions
   └─ Rank by reliability

5. Answer Generation
   ├─ Combine evidence and inferences
   ├─ Calculate overall confidence
   ├─ Generate natural language answer
   └─ Provide reasoning trace
```

## Domain Models

### QueryPlan

```python
class QueryPlan(BaseModel):
    plan_id: str
    original_query: str
    steps: List[QueryStep]
    total_estimated_cost: float
    optimized: bool
    explanation: str
```

### QueryStep

```python
class QueryStep(BaseModel):
    step_id: str
    operation: QueryOperation
    query: GraphQuery
    depends_on: List[str]
    description: str
    estimated_cost: float
```

### ReasoningResult

```python
class ReasoningResult(BaseModel):
    query: str
    evidence: List[Evidence]
    answer: str
    confidence: float
    reasoning_trace: List[str]
    execution_time_ms: float
```

### Evidence

```python
class Evidence(BaseModel):
    evidence_id: str
    evidence_type: EvidenceType
    entities: List[Entity]
    relations: List[Relation]
    paths: List[Path]
    confidence: float
    relevance_score: float
    explanation: str
    source: str
```

### InferenceResult

```python
class InferenceResult(BaseModel):
    inferred_relations: List[Relation]
    inference_steps: List[InferenceStep]
    confidence: float
    total_steps: int
```

## Use Cases

### 1. Complex Question Answering

```python
# Multi-hop question with inference
result = await engine.reason(
    query="Who are the most influential people connected to Alice?",
    context={"start_entity_id": "alice"},
    max_hops=4
)
```

### 2. Relationship Discovery

```python
# Find all transitive connections
result = await inference_engine.infer_relations(
    relation_type="KNOWS",
    max_steps=10,
    use_cache=True
)
```

### 3. Evidence-Based Decision Making

```python
# Collect and synthesize evidence
evidence = await collect_evidence(query)
synthesized = synthesizer.synthesize_evidence(evidence)
ranked = synthesizer.rank_by_reliability(synthesized)

# Make decision based on top evidence
decision = make_decision(ranked[0])
```

### 4. Knowledge Graph Completion

```python
# Infer missing relations
symmetric_rule = InferenceRule(
    rule_id="symmetric_friend",
    rule_type=RuleType.SYMMETRIC,
    relation_type="FRIEND_OF"
)
inference_engine.add_rule(symmetric_rule)

result = await inference_engine.infer_relations("FRIEND_OF")
# Adds reverse friendship relations
```

## Performance

### Benchmarks

| Operation | Graph Size | Time (ms) | Throughput |
|-----------|------------|-----------|------------|
| Query Planning | Any | <10 | >100 queries/sec |
| Multi-Hop (3 hops) | 1K entities | 20-50 | ~20 queries/sec |
| Multi-Hop (3 hops) | 10K entities | 50-150 | ~7 queries/sec |
| Inference (Transitive) | 100 relations | 10-30 | ~30 ops/sec |
| Inference (Transitive) | 1K relations | 50-200 | ~5 ops/sec |
| Evidence Synthesis | 10 pieces | <5 | >200 ops/sec |

### Optimization Tips

1. **Use Caching**:
   - Enable inference result caching
   - Cache query plans for repeated queries
   - Use retrieval cache for frequent lookups

2. **Limit Depth**:
   - Set `max_hops` appropriately (3-4 is usually sufficient)
   - Use `max_evidence` to limit evidence collection

3. **Optimize Inference**:
   - Set `max_steps` based on graph size
   - Enable only needed inference rules
   - Use cache for repeated relation types

4. **Parallel Execution**:
   - Query planner identifies parallel steps
   - Use `execution_order` for optimal parallelization

## Best Practices

### Query Writing

```python
# Good: Specific and focused
"How is Alice connected to Company X?"

# Better: With constraints
"How is Alice connected to Company X through WORKS_FOR relations?"

# Best: With context
context = {
    "start_entity_id": "alice",
    "target_entity_id": "company_x",
    "relation_types": ["WORKS_FOR", "KNOWS"]
}
```

### Inference Rules

```python
# Enable only needed rules
for rule in inference_engine.get_rules("KNOWS"):
    rule.enabled = True  # Only when needed

# Set appropriate confidence decay
InferenceRule(
    rule_id="transitive_knows",
    rule_type=RuleType.TRANSITIVE,
    relation_type="KNOWS",
    confidence_decay=0.1  # 10% decay per hop
)
```

### Evidence Synthesis

```python
# Filter before synthesis
high_confidence = synthesizer.filter_by_confidence(
    evidence_list,
    threshold=0.7
)

# Use appropriate method
synthesized = synthesizer.synthesize_evidence(
    high_confidence,
    method="weighted_average"  # Balanced approach
)

# Check for contradictions
contradictions = synthesizer.detect_contradictions(synthesized)
if contradictions:
    # Handle contradictions
    pass
```

## Error Handling

```python
from aiecs.application.knowledge_graph.reasoning import (
    QueryPlanner,
    ReasoningEngine,
    InferenceEngine
)

try:
    # Query planning
    plan = planner.plan_query(query)
    
    # Multi-hop reasoning
    result = await engine.reason(query, context, max_hops=3)
    
    # Inference
    inferred = await inference_engine.infer_relations(
        relation_type="KNOWS",
        max_steps=5
    )
    
except ValueError as e:
    print(f"Invalid parameter: {e}")
except Exception as e:
    print(f"Reasoning error: {e}")
```

## Testing

All reasoning components are thoroughly tested:

- **Query Planning**: 22 unit tests
- **Multi-Hop Reasoning**: 20 unit tests
- **Logical Inference**: 21 unit tests
- **Evidence Synthesis**: 14 unit tests
- **Reasoning Tools**: 11 unit tests

**Total**: 88 tests passing

## API Reference

### QueryPlanner

- `plan_query(query, context) -> QueryPlan`
- `optimize_plan(plan, strategy) -> QueryPlan`
- `translate_to_graph_query(query) -> GraphQuery`

### ReasoningEngine

- `reason(query, context, max_hops, max_evidence) -> ReasoningResult`
- `find_multi_hop_paths(start_id, target_id, max_hops) -> List[Path]`
- `collect_evidence_from_paths(paths) -> List[Evidence]`
- `rank_evidence(evidence) -> List[Evidence]`

### InferenceEngine

- `infer_relations(relation_type, max_steps, use_cache) -> InferenceResult`
- `add_rule(rule) -> None`
- `remove_rule(rule_id) -> None`
- `get_rules(relation_type) -> List[InferenceRule]`

### EvidenceSynthesizer

- `synthesize_evidence(evidence_list, method) -> List[Evidence]`
- `filter_by_confidence(evidence_list, threshold) -> List[Evidence]`
- `detect_contradictions(evidence_list) -> List[Dict]`
- `estimate_overall_confidence(evidence_list) -> float`
- `rank_by_reliability(evidence_list) -> List[Evidence]`

## Examples

See `docs/knowledge_graph/examples/` for complete examples:
- `09_multi_hop_qa.py` - Multi-hop question answering
- `10_logical_inference.py` - Logical inference over knowledge
- `11_evidence_reasoning.py` - Evidence-based reasoning

## Related Documentation

- [Multi-Hop Reasoning Tutorial](../tutorials/MULTI_HOP_REASONING_TUTORIAL.md)
- [Logic Query Parser](./logic_query_parser.md)
- [Graph Reasoning Tool](../tools/GRAPH_REASONING_TOOL.md)

---

**Status**: ✅ Complete  
**Phase**: 4 - Reasoning Engine  
**Tests**: 88/88 passing  
**Coverage**: >80%  
**Ready for**: Production use

