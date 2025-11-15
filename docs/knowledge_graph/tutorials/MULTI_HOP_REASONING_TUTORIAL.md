# Multi-Hop Reasoning Tutorial

## Overview

This tutorial demonstrates how to perform multi-hop reasoning over knowledge graphs to answer complex questions that require traversing multiple relationships.

## Learning Objectives

By the end of this tutorial, you will:
- Understand multi-hop reasoning concepts
- Build a knowledge graph for reasoning
- Perform path finding and traversal
- Use query planning for complex questions
- Apply logical inference rules
- Synthesize evidence from multiple paths

## What is Multi-Hop Reasoning?

Multi-hop reasoning involves answering questions by following multiple relationships (hops) in a knowledge graph:

- **1-hop**: "Who does Alice work for?" → Alice --WORKS_FOR--> Tech Corp
- **2-hop**: "Where does Alice's company located?" → Alice --WORKS_FOR--> Tech Corp --LOCATED_IN--> San Francisco
- **3-hop**: "What projects are in Alice's company's city?" → Alice --WORKS_FOR--> Tech Corp --LOCATED_IN--> San Francisco --HAS_PROJECT--> AI Platform

## Scenario: Corporate Knowledge Graph

We'll build a knowledge graph about companies, employees, projects, and locations, then answer complex multi-hop questions.

## Step 1: Build the Knowledge Graph

```python
import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

async def build_corporate_graph():
    """Build a corporate knowledge graph"""

    store = InMemoryGraphStore()
    await store.initialize()

    # Create entities
    # People
    alice = Entity(id="alice", entity_type="Person",
                   properties={"name": "Alice Smith", "role": "Engineer", "experience": 8})
    bob = Entity(id="bob", entity_type="Person",
                 properties={"name": "Bob Jones", "role": "Designer", "experience": 5})
    charlie = Entity(id="charlie", entity_type="Person",
                     properties={"name": "Charlie Brown", "role": "Manager", "experience": 10})
    diana = Entity(id="diana", entity_type="Person",
                   properties={"name": "Diana Prince", "role": "Engineer", "experience": 6})

    # Companies
    tech_corp = Entity(id="tech_corp", entity_type="Company",
                       properties={"name": "Tech Corp", "industry": "Technology", "size": 500})
    data_inc = Entity(id="data_inc", entity_type="Company",
                      properties={"name": "Data Inc", "industry": "Analytics", "size": 200})

    # Locations
    sf = Entity(id="sf", entity_type="Location",
                properties={"name": "San Francisco", "country": "USA", "population": 875000})
    ny = Entity(id="ny", entity_type="Location",
                properties={"name": "New York", "country": "USA", "population": 8400000})

    # Projects
    ai_platform = Entity(id="ai_platform", entity_type="Project",
                         properties={"name": "AI Platform", "budget": 1000000, "status": "active"})
    data_pipeline = Entity(id="data_pipeline", entity_type="Project",
                           properties={"name": "Data Pipeline", "budget": 500000, "status": "active"})
    ml_engine = Entity(id="ml_engine", entity_type="Project",
                       properties={"name": "ML Engine", "budget": 750000, "status": "planning"})

    # Add all entities
    entities = [alice, bob, charlie, diana, tech_corp, data_inc, sf, ny,
                ai_platform, data_pipeline, ml_engine]
    for entity in entities:
        await store.add_entity(entity)

    # Create relations
    relations = [
        # Employment
        Relation(id="r1", relation_type="WORKS_FOR", source_id="alice", target_id="tech_corp",
                 properties={"start_date": "2020-01-01", "department": "Engineering"}),
        Relation(id="r2", relation_type="WORKS_FOR", source_id="bob", target_id="tech_corp",
                 properties={"start_date": "2021-06-01", "department": "Design"}),
        Relation(id="r3", relation_type="WORKS_FOR", source_id="charlie", target_id="data_inc",
                 properties={"start_date": "2018-03-01", "department": "Management"}),
        Relation(id="r4", relation_type="WORKS_FOR", source_id="diana", target_id="data_inc",
                 properties={"start_date": "2019-09-01", "department": "Engineering"}),

        # Company locations
        Relation(id="r5", relation_type="LOCATED_IN", source_id="tech_corp", target_id="sf"),
        Relation(id="r6", relation_type="LOCATED_IN", source_id="data_inc", target_id="ny"),

        # Project assignments
        Relation(id="r7", relation_type="WORKS_ON", source_id="alice", target_id="ai_platform",
                 properties={"role": "Lead Engineer", "allocation": 1.0}),
        Relation(id="r8", relation_type="WORKS_ON", source_id="bob", target_id="ai_platform",
                 properties={"role": "UI Designer", "allocation": 0.5}),
        Relation(id="r9", relation_type="WORKS_ON", source_id="diana", target_id="data_pipeline",
                 properties={"role": "Engineer", "allocation": 1.0}),
        Relation(id="r10", relation_type="WORKS_ON", source_id="alice", target_id="ml_engine",
                 properties={"role": "Architect", "allocation": 0.3}),

        # Project ownership
        Relation(id="r11", relation_type="OWNS_PROJECT", source_id="tech_corp", target_id="ai_platform"),
        Relation(id="r12", relation_type="OWNS_PROJECT", source_id="tech_corp", target_id="ml_engine"),
        Relation(id="r13", relation_type="OWNS_PROJECT", source_id="data_inc", target_id="data_pipeline"),

        # Collaborations
        Relation(id="r14", relation_type="KNOWS", source_id="alice", target_id="bob"),
        Relation(id="r15", relation_type="KNOWS", source_id="alice", target_id="diana"),
        Relation(id="r16", relation_type="KNOWS", source_id="charlie", target_id="diana"),

        # Management
        Relation(id="r17", relation_type="MANAGES", source_id="charlie", target_id="diana"),
    ]

    for relation in relations:
        await store.add_relation(relation)

    print("✅ Corporate knowledge graph built")
    print(f"   Entities: {len(entities)}")
    print(f"   Relations: {len(relations)}")

    return store

# Run
store = await build_corporate_graph()
```





## Step 2: Simple Path Finding (2-Hop)

Find paths between two entities:

```python
async def find_connection_path(store):
    """Find how Alice is connected to New York"""

    print("\n🔍 Question: How is Alice connected to New York?")

    # Find all paths from Alice to NY (max 3 hops)
    paths = await store.find_paths(
        start_id="alice",
        end_id="ny",
        max_depth=3
    )

    print(f"   Found {len(paths)} paths:\n")

    for i, path in enumerate(paths):
        # Extract path description
        path_desc = []
        for j, entity in enumerate(path.entities):
            path_desc.append(entity.properties['name'])
            if j < len(path.relations):
                path_desc.append(f"--{path.relations[j].relation_type}-->")

        print(f"   Path {i+1}: {' '.join(path_desc)}")

# Run
await find_connection_path(store)
```

**Output**:
```
🔍 Question: How is Alice connected to New York?
   Found 2 paths:

   Path 1: Alice Smith --KNOWS--> Diana Prince --WORKS_FOR--> Data Inc --LOCATED_IN--> New York
   Path 2: Alice Smith --WORKS_FOR--> Tech Corp --LOCATED_IN--> San Francisco
```

## Step 3: Multi-Hop Question Answering

Answer complex questions using multi-hop traversal:

```python
async def answer_complex_questions(store):
    """Answer multi-hop questions"""

    # Question 1: What projects are in Alice's company's city?
    print("\n🔍 Question 1: What projects are owned by companies in San Francisco?")

    # Step 1: Find Alice's company
    companies = await store.get_neighbors("alice", direction="outgoing", relation_types=["WORKS_FOR"])
    alice_company = companies[0] if companies else None

    if alice_company:
        # Step 2: Find company's location
        locations = await store.get_neighbors(alice_company.id, direction="outgoing", relation_types=["LOCATED_IN"])
        location = locations[0] if locations else None

        if location:
            # Step 3: Find projects owned by the company
            projects = await store.get_neighbors(alice_company.id, direction="outgoing", relation_types=["OWNS_PROJECT"])

            print(f"   Answer: {alice_company.properties['name']} in {location.properties['name']} owns:")
            for project in projects:
                print(f"     - {project.properties['name']}")

    # Question 2: Who works on projects with Alice?
    print("\n🔍 Question 2: Who works on the same projects as Alice?")

    alice_projects = await store.get_neighbors("alice", direction="outgoing", relation_types=["WORKS_ON"])

    collaborators = set()
    for project in alice_projects:
        coworkers = await store.get_neighbors(project.id, direction="incoming", relation_types=["WORKS_ON"])
        for person in coworkers:
            if person.id != "alice":
                collaborators.add(person.properties['name'])

    print(f"   Collaborators: {', '.join(collaborators)}")

# Run
await answer_complex_questions(store)
```

## Step 4: Evidence-Based Reasoning

Synthesize evidence from multiple paths:

```python
from aiecs.application.knowledge_graph.reasoning import EvidenceSynthesizer
from aiecs.domain.knowledge_graph.models.evidence import Evidence, EvidenceType

async def synthesize_evidence(store):
    """Synthesize evidence from multiple sources"""

    synthesizer = EvidenceSynthesizer(graph_store=store)

    print("\n🔍 Question: Is Alice qualified to lead the ML Engine project?")

    # Collect evidence
    evidence_list = []

    # Evidence 1: Alice's experience
    alice = await store.get_entity("alice")
    evidence_list.append(Evidence(
        evidence_type=EvidenceType.ENTITY,
        content=alice,
        confidence=1.0,
        source="entity_properties",
        metadata={"experience_years": alice.properties.get("experience", 0)}
    ))

    # Evidence 2: Alice's current projects
    projects = await store.get_neighbors("alice", direction="outgoing", relation_types=["WORKS_ON"])
    for project in projects:
        evidence_list.append(Evidence(
            evidence_type=EvidenceType.RELATION,
            content=f"Works on {project.properties['name']}",
            confidence=0.9,
            source="current_projects"
        ))

    # Evidence 3: Alice's role in ML Engine
    ml_engine_rel = await store.get_relation("r10")
    if ml_engine_rel:
        evidence_list.append(Evidence(
            evidence_type=EvidenceType.RELATION,
            content=f"Role: {ml_engine_rel.properties.get('role')}",
            confidence=0.95,
            source="project_assignment"
        ))

    # Synthesize
    result = await synthesizer.synthesize(
        question="Is Alice qualified to lead ML Engine?",
        evidence=evidence_list
    )

    print(f"   Answer: {result.answer}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Evidence:")
    for ev in result.evidence:
        print(f"     - {ev.content} (confidence: {ev.confidence:.2f})")

# Run
await synthesize_evidence(store)
```

## Step 5: Complete Example

Here's the complete multi-hop reasoning example:

```python
import asyncio

async def main():
    """Complete multi-hop reasoning tutorial"""

    # Step 1: Build knowledge graph
    store = await build_corporate_graph()

    # Step 2: Find paths
    await find_connection_path(store)

    # Step 3: Answer complex questions
    await answer_complex_questions(store)

    # Step 4: Evidence synthesis
    await synthesize_evidence(store)

    # Cleanup
    await store.close()
    print("\n✅ Tutorial complete!")

# Run
asyncio.run(main())
```

## Key Concepts

### 1. Path Finding
- **Single Path**: Find one path between entities
- **All Paths**: Find all possible paths (up to max depth)
- **Shortest Path**: Find the shortest connection

### 2. Multi-Hop Traversal
- **BFS Traversal**: Breadth-first search from starting entity
- **DFS Traversal**: Depth-first search for specific patterns
- **Filtered Traversal**: Only follow specific relation types

### 3. Query Planning
- **Cost Estimation**: Estimate query execution cost
- **Optimization**: Reorder operations for efficiency
- **Caching**: Cache intermediate results

### 4. Evidence Synthesis
- **Multiple Sources**: Combine evidence from different paths
- **Confidence Scoring**: Weight evidence by confidence
- **Contradiction Detection**: Identify conflicting evidence

## Best Practices

1. **Limit Depth**: Use reasonable max_depth (2-4 hops) to avoid explosion
2. **Filter Relations**: Specify relation_types to reduce search space
3. **Use Query Planning**: For complex queries, let the planner optimize
4. **Cache Results**: Cache frequently accessed paths
5. **Validate Paths**: Check that paths make semantic sense

## Performance Tips

- **Index Frequently Queried Entities**: Improve lookup speed
- **Use Batch Operations**: Process multiple queries together
- **Enable Schema Caching**: Cache schema lookups
- **Optimize Storage Backend**: Use PostgreSQL for large graphs

## Next Steps

- **Advanced Reasoning**: Explore temporal reasoning, probabilistic inference
- **Custom Algorithms**: Implement domain-specific reasoning logic
- **Agent Integration**: Use reasoning in AI agent workflows
- **Visualization**: Visualize reasoning paths and evidence

## Resources

- **API Reference**: [API_REFERENCE.md](../API_REFERENCE.md)
- **Reasoning Guide**: [reasoning/REASONING_ENGINE.md](../reasoning/REASONING_ENGINE.md)
- **Examples**: [examples/09_multi_hop_qa.py](../examples/09_multi_hop_qa.py)

Happy reasoning! 🧠🚀
