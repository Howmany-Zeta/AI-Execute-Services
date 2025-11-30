"""
Example: HybridAgent with Knowledge Graph

Demonstrates how to use KnowledgeAwareAgent (enhanced HybridAgent)
with knowledge graph integration.
"""

import asyncio
from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.llm import BaseLLMClient, LLMResponse


# Mock LLM client for demonstration
class MockLLMClient:
    def __init__(self):
        self.provider_name = "mock"
    
    async def generate_text(self, messages, model=None, temperature=None, max_tokens=None):
        # Simulate LLM response
        content = "THOUGHT: Based on the retrieved knowledge, Alice works at TechCorp.\nFINAL ANSWER: Alice works at TechCorp as an Engineer."
        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
            tokens_used=20
        )


async def main():
    """Main example function"""
    
    print("=" * 60)
    print("Example: HybridAgent with Knowledge Graph")
    print("=" * 60)
    
    # 1. Create and initialize graph store
    print("\n1. Creating graph store...")
    graph_store = InMemoryGraphStore()
    await graph_store.initialize()
    
    # 2. Populate graph with sample data
    print("2. Populating graph with sample data...")
    
    # Create entities
    alice = Entity(
        id="alice",
        entity_type="Person",
        properties={"name": "Alice", "role": "Engineer", "department": "Engineering"}
    )
    
    bob = Entity(
        id="bob",
        entity_type="Person",
        properties={"name": "Bob", "role": "Manager", "department": "Engineering"}
    )
    
    tech_corp = Entity(
        id="tech_corp",
        entity_type="Company",
        properties={"name": "TechCorp", "industry": "Technology"}
    )
    
    await graph_store.add_entity(alice)
    await graph_store.add_entity(bob)
    await graph_store.add_entity(tech_corp)
    
    # Create relations
    await graph_store.add_relation(Relation(
        id="rel1",
        source_id="alice",
        target_id="bob",
        relation_type="KNOWS",
        properties={}
    ))
    
    await graph_store.add_relation(Relation(
        id="rel2",
        source_id="alice",
        target_id="tech_corp",
        relation_type="WORKS_FOR",
        properties={}
    ))
    
    await graph_store.add_relation(Relation(
        id="rel3",
        source_id="bob",
        target_id="tech_corp",
        relation_type="WORKS_FOR",
        properties={}
    ))
    
    print(f"   - Added {3} entities and {3} relations")
    
    # 3. Create knowledge-aware agent
    print("\n3. Creating KnowledgeAwareAgent...")
    
    llm_client = MockLLMClient()
    config = AgentConfiguration(
        max_retries=3,
        timeout_seconds=30,
        enable_logging=True,
        llm_model="mock-model",
        temperature=0.7,
    )
    
    agent = KnowledgeAwareAgent(
        agent_id="kg_agent_1",
        name="Knowledge-Aware Agent",
        llm_client=llm_client,
        tools=[],  # Graph tools are automatically added
        config=config,
        graph_store=graph_store,
        enable_graph_reasoning=True
    )
    
    await agent.initialize()
    print("   - Agent initialized with graph store")
    
    # 4. Execute tasks with knowledge graph
    print("\n4. Executing tasks with knowledge graph...")
    
    # Task 1: Simple query
    print("\n   Task 1: Where does Alice work?")
    result1 = await agent.execute_task(
        task={"description": "Where does Alice work?"},
        context={}
    )
    print(f"   Result: {result1.get('output', 'N/A')}")
    print(f"   Reasoning steps: {len(result1.get('reasoning_steps', []))}")
    
    # Task 2: Graph relationship query
    print("\n   Task 2: How is Alice connected to TechCorp?")
    result2 = await agent.execute_task(
        task={"description": "How is Alice connected to TechCorp?"},
        context={}
    )
    print(f"   Result: {result2.get('output', 'N/A')}")
    if result2.get('source') == 'knowledge_graph':
        print(f"   Confidence: {result2.get('confidence', 0):.2f}")
    
    # Task 3: Multi-hop query
    print("\n   Task 3: Who does Alice know at TechCorp?")
    result3 = await agent.execute_task(
        task={"description": "Who does Alice know at TechCorp?"},
        context={}
    )
    print(f"   Result: {result3.get('output', 'N/A')}")
    
    # 5. Demonstrate graph utilities
    print("\n5. Using graph utilities...")
    
    # Get neighbors
    neighbors = await agent.get_entity_neighbors("alice")
    print(f"   Alice's neighbors: {len(neighbors)}")
    for neighbor in neighbors:
        print(f"     - {neighbor.entity_type}: {neighbor.id}")
    
    # Format entities
    formatted = agent.format_entities(neighbors)
    print(f"\n   Formatted neighbors:\n{formatted}")
    
    # Get graph stats
    stats = agent.get_graph_stats()
    print(f"\n   Graph statistics:")
    print(f"     - Entities: {stats.get('entity_count', 'N/A')}")
    print(f"     - Relations: {stats.get('relation_count', 'N/A')}")
    
    # 6. Cleanup
    print("\n6. Cleaning up...")
    await agent.shutdown()
    await graph_store.close()
    print("   - Agent and graph store closed")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

