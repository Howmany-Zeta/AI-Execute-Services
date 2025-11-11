"""
Example: Knowledge-Augmented Conversation

Demonstrates how KnowledgeAwareAgent uses knowledge graph
to enhance conversations with context and memory.
"""

import asyncio
from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.domain.context.graph_memory import GraphMemoryMixin
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.llm import BaseLLMClient, LLMResponse


# Mock LLM client for demonstration
class MockLLMClient:
    def __init__(self):
        self.provider_name = "mock"
        self.conversation_context = []
    
    async def generate_text(self, messages, model=None, temperature=None, max_tokens=None):
        # Simulate context-aware LLM response
        last_message = messages[-1].content if messages else ""
        
        if "Alice" in last_message:
            content = "THOUGHT: Based on the knowledge graph, I know about Alice.\nFINAL ANSWER: Alice is an Engineer who works at TechCorp. She knows Bob."
        elif "Bob" in last_message:
            content = "THOUGHT: I can see Bob's information from the graph.\nFINAL ANSWER: Bob is a Manager at TechCorp. He works with Alice."
        else:
            content = "THOUGHT: I'll use the knowledge graph to answer.\nFINAL ANSWER: I can help you with information from the knowledge graph."
        
        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
            tokens_used=25
        )


async def main():
    """Main example function"""
    
    print("=" * 60)
    print("Example: Knowledge-Augmented Conversation")
    print("=" * 60)
    
    # 1. Create graph store and populate with initial knowledge
    print("\n1. Setting up knowledge graph...")
    graph_store = InMemoryGraphStore()
    await graph_store.initialize()
    
    # Add initial entities
    alice = Entity(
        id="alice",
        entity_type="Person",
        properties={"name": "Alice", "role": "Engineer"}
    )
    
    bob = Entity(
        id="bob",
        entity_type="Person",
        properties={"name": "Bob", "role": "Manager"}
    )
    
    tech_corp = Entity(
        id="tech_corp",
        entity_type="Company",
        properties={"name": "TechCorp"}
    )
    
    await graph_store.add_entity(alice)
    await graph_store.add_entity(bob)
    await graph_store.add_entity(tech_corp)
    
    await graph_store.add_relation(Relation(
        id="rel1",
        source_id="alice",
        target_id="tech_corp",
        relation_type="WORKS_FOR",
        properties={}
    ))
    
    await graph_store.add_relation(Relation(
        id="rel2",
        source_id="alice",
        target_id="bob",
        relation_type="KNOWS",
        properties={}
    ))
    
    print("   - Graph initialized with 3 entities and 2 relations")
    
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
        agent_id="conversation_agent",
        name="Conversation Agent",
        llm_client=llm_client,
        tools=[],
        config=config,
        graph_store=graph_store,
        enable_graph_reasoning=True
    )
    
    await agent.initialize()
    print("   - Agent ready for conversation")
    
    # 3. Simulate conversation with knowledge retrieval
    print("\n3. Simulating conversation...")
    
    session_id = "session_1"
    conversation = [
        "Tell me about Alice",
        "What about Bob?",
        "How are they connected?",
    ]
    
    for i, user_message in enumerate(conversation, 1):
        print(f"\n   Turn {i}:")
        print(f"   User: {user_message}")
        
        # Execute task
        result = await agent.execute_task(
            task={"description": user_message},
            context={"session_id": session_id}
        )
        
        response = result.get("output", "N/A")
        print(f"   Agent: {response}")
        
        # Show reasoning steps
        steps = result.get("reasoning_steps", [])
        retrieve_steps = [s for s in steps if s.get("type") == "retrieve"]
        if retrieve_steps:
            print(f"   [Retrieved knowledge in {len(retrieve_steps)} step(s)]")
    
    # 4. Demonstrate knowledge accumulation
    print("\n4. Demonstrating knowledge accumulation...")
    
    # Store new knowledge from conversation
    charlie = Entity(
        id="charlie",
        entity_type="Person",
        properties={"name": "Charlie", "role": "Designer"}
    )
    
    await graph_store.add_entity(charlie)
    await graph_store.add_relation(Relation(
        id="rel3",
        source_id="charlie",
        target_id="tech_corp",
        relation_type="WORKS_FOR",
        properties={}
    ))
    
    print("   - Added new entity: Charlie")
    
    # Query with new knowledge
    print("\n   Query: Who works at TechCorp?")
    result = await agent.execute_task(
        task={"description": "Who works at TechCorp?"},
        context={"session_id": session_id}
    )
    print(f"   Response: {result.get('output', 'N/A')}")
    
    # 5. Show knowledge context
    print("\n5. Knowledge context for session...")
    
    # Get session subgraph
    subgraph = await agent.get_entity_subgraph("alice", max_depth=2)
    print(f"   Entities in context: {len(subgraph['entities'])}")
    
    # Format knowledge summary
    entities = [Entity(**e) for e in subgraph['entities'][:3]]
    summary = agent.format_knowledge_summary(entities)
    print(f"\n   Knowledge summary:\n{summary}")
    
    # 6. Cleanup
    print("\n6. Cleaning up...")
    await agent.shutdown()
    await graph_store.close()
    print("   - Conversation ended")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

