"""
Example: Multi-Step Reasoning with Knowledge Graph

Demonstrates how KnowledgeAwareAgent performs multi-hop reasoning
using the knowledge graph structure.
"""

import asyncio
from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.llm import BaseLLMClient, LLMResponse


# Mock LLM client that simulates multi-step reasoning
class MockLLMClient:
    def __init__(self):
        self.provider_name = "mock"
        self.iteration = 0
    
    async def generate_text(self, messages, model=None, temperature=None, max_tokens=None):
        self.iteration += 1
        
        # Simulate multi-step reasoning
        if self.iteration == 1:
            content = "THOUGHT: I need to find how Alice is connected to TechCorp. Let me use the graph_reasoning tool.\nTOOL: graph_reasoning\nOPERATION: multi_hop\nPARAMETERS: {\"query\": \"How is Alice connected to TechCorp?\"}"
        elif self.iteration == 2:
            content = "THOUGHT: I found that Alice WORKS_FOR TechCorp. Now I can answer the question.\nFINAL ANSWER: Alice works at TechCorp as an Engineer."
        else:
            content = "FINAL ANSWER: Based on the knowledge graph, I can provide the answer."
        
        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
            tokens_used=30
        )


async def main():
    """Main example function"""
    
    print("=" * 60)
    print("Example: Multi-Step Reasoning with Knowledge Graph")
    print("=" * 60)
    
    # 1. Create complex knowledge graph
    print("\n1. Creating complex knowledge graph...")
    graph_store = InMemoryGraphStore()
    await graph_store.initialize()
    
    # Create entities
    entities_data = [
        ("alice", "Person", {"name": "Alice", "role": "Engineer", "department": "Engineering"}),
        ("bob", "Person", {"name": "Bob", "role": "Manager", "department": "Engineering"}),
        ("charlie", "Person", {"name": "Charlie", "role": "Designer", "department": "Design"}),
        ("diana", "Person", {"name": "Diana", "role": "CEO", "department": "Executive"}),
        ("tech_corp", "Company", {"name": "TechCorp", "industry": "Technology"}),
        ("project_alpha", "Project", {"name": "Project Alpha", "status": "active"}),
    ]
    
    for entity_id, entity_type, properties in entities_data:
        entity = Entity(id=entity_id, entity_type=entity_type, properties=properties)
        await graph_store.add_entity(entity)
    
    # Create relations (multi-hop paths)
    relations_data = [
        ("alice", "bob", "KNOWS"),
        ("alice", "tech_corp", "WORKS_FOR"),
        ("bob", "tech_corp", "WORKS_FOR"),
        ("bob", "diana", "REPORTS_TO"),
        ("charlie", "tech_corp", "WORKS_FOR"),
        ("charlie", "project_alpha", "WORKS_ON"),
        ("alice", "project_alpha", "WORKS_ON"),
        ("diana", "tech_corp", "OWNS"),
    ]
    
    for i, (source, target, rel_type) in enumerate(relations_data, 1):
        await graph_store.add_relation(Relation(
            id=f"rel{i}",
            source_id=source,
            target_id=target,
            relation_type=rel_type,
            properties={}
        ))
    
    print(f"   - Created {len(entities_data)} entities and {len(relations_data)} relations")
    
    # 2. Create knowledge-aware agent
    print("\n2. Creating KnowledgeAwareAgent...")
    
    llm_client = MockLLMClient()
    config = AgentConfiguration(
        max_retries=3,
        timeout_seconds=30,
        enable_logging=True,
        llm_model="mock-model",
        temperature=0.7,
    )
    
    agent = KnowledgeAwareAgent(
        agent_id="reasoning_agent",
        name="Multi-Step Reasoning Agent",
        llm_client=llm_client,
        tools=[],  # Graph tools automatically available
        config=config,
        graph_store=graph_store,
        enable_graph_reasoning=True,
        max_iterations=5  # Allow multiple reasoning steps
    )
    
    await agent.initialize()
    print("   - Agent ready for multi-step reasoning")
    
    # 3. Multi-hop reasoning queries
    print("\n3. Multi-hop reasoning queries...")
    
    queries = [
        {
            "description": "How is Alice connected to TechCorp?",
            "expected_hops": 1
        },
        {
            "description": "Who does Alice know that works at TechCorp?",
            "expected_hops": 2
        },
        {
            "description": "Who is the CEO of the company where Alice works?",
            "expected_hops": 3
        },
    ]
    
    for i, query_info in enumerate(queries, 1):
        print(f"\n   Query {i}: {query_info['description']}")
        print(f"   Expected hops: {query_info['expected_hops']}")
        
        # Reset iteration counter
        llm_client.iteration = 0
        
        result = await agent.execute_task(
            task={"description": query_info['description']},
            context={}
        )
        
        print(f"   Answer: {result.get('output', 'N/A')}")
        print(f"   Iterations: {result.get('iterations', 0)}")
        print(f"   Tool calls: {result.get('tool_calls_count', 0)}")
        
        # Show reasoning steps
        steps = result.get('reasoning_steps', [])
        step_types = [s.get('type') for s in steps]
        print(f"   Step types: {', '.join(set(step_types))}")
    
    # 4. Demonstrate path finding
    print("\n4. Finding paths between entities...")
    
    paths = await agent.find_paths_between(
        source_id="alice",
        target_id="diana",
        max_depth=4
    )
    
    print(f"   Found {len(paths)} path(s) from Alice to Diana:")
    for i, path in enumerate(paths[:3], 1):  # Show first 3 paths
        path_str = agent.format_path(path)
        print(f"     Path {i}: {path_str}")
    
    # 5. Demonstrate subgraph extraction
    print("\n5. Extracting subgraph around entity...")
    
    subgraph = await agent.get_entity_subgraph(
        entity_id="alice",
        max_depth=2
    )
    
    print(f"   Subgraph around Alice:")
    print(f"     - Entities: {len(subgraph['entities'])}")
    
    # Format entities
    entities = [Entity(**e) for e in subgraph['entities']]
    formatted = agent.format_entities(entities, max_items=5)
    print(f"\n   Entities:\n{formatted}")
    
    # 6. Show reasoning trace
    print("\n6. Reasoning trace example...")
    
    result = await agent.execute_task(
        task={"description": "What projects is Alice working on?"},
        context={}
    )
    
    steps = result.get('reasoning_steps', [])
    print(f"   Total steps: {len(steps)}")
    for i, step in enumerate(steps[:5], 1):  # Show first 5 steps
        step_type = step.get('type', 'unknown')
        content = step.get('content', '')[:50]
        print(f"     Step {i} [{step_type}]: {content}...")
    
    # 7. Cleanup
    print("\n7. Cleaning up...")
    await agent.shutdown()
    await graph_store.close()
    print("   - Agent and graph store closed")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

