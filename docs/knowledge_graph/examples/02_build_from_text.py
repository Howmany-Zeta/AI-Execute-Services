"""
Example: Building Knowledge Graph from Text

This example demonstrates how to build a knowledge graph from text using
the full Phase 2 pipeline.
"""

import asyncio
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.extractors.llm_entity_extractor import LLMEntityExtractor
from aiecs.application.knowledge_graph.extractors.ner_entity_extractor import NEREntityExtractor
from aiecs.application.knowledge_graph.extractors.llm_relation_extractor import LLMRelationExtractor
from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder


async def main():
    print("━" * 80)
    print("Knowledge Graph Builder Example: Extract from Text")
    print("━" * 80)
    
    # Sample text
    text = """
    Alice Johnson is a senior software engineer at Tech Corp, a technology company
    based in San Francisco. She has been working there since 2020, leading the
    AI research team. Alice previously worked at Innovation Labs in New York.
    
    Tech Corp was founded by Bob Smith in 2015 and specializes in artificial
    intelligence and machine learning solutions. The company recently opened
    a new office in Seattle.
    
    Alice collaborates closely with Dr. Carol Zhang, the Chief AI Officer at
    Tech Corp. Together, they published a research paper on neural networks
    at the International Conference on AI last year.
    """
    
    print("\n📝 Input Text:")
    print("-" * 80)
    print(text[:200] + "...")
    print()
    
    # Step 1: Initialize graph store
    print("🔧 Initializing graph store...")
    graph_store = InMemoryGraphStore()
    await graph_store.initialize()
    
    # Step 2: Initialize extractors
    print("🔧 Initializing extractors...")
    
    # Option 1: Use LLM extractor (more accurate, requires LLM API)
    # entity_extractor = LLMEntityExtractor()
    
    # Option 2: Use NER extractor (fast, offline, no API required)
    entity_extractor = NEREntityExtractor(model="en_core_web_sm")
    
    relation_extractor = LLMRelationExtractor()
    
    # Step 3: Create graph builder
    print("🔧 Creating graph builder...")
    builder = GraphBuilder(
        graph_store=graph_store,
        entity_extractor=entity_extractor,
        relation_extractor=relation_extractor,
        enable_deduplication=True,
        enable_linking=True,
        enable_validation=False,  # No schema validation
        progress_callback=lambda msg, pct: print(f"  [{pct*100:>3.0f}%] {msg}")
    )
    
    # Step 4: Build graph from text
    print("\n🚀 Building knowledge graph from text...")
    result = await builder.build_from_text(
        text=text,
        source="example_document"
    )
    
    # Step 5: Display results
    print("\n" + "━" * 80)
    print("📊 BUILD RESULTS")
    print("━" * 80)
    print(f"✅ Success: {result.success}")
    print(f"🔢 Entities added: {result.entities_added}")
    print(f"🔗 Relations added: {result.relations_added}")
    print(f"🔗 Entities linked: {result.entities_linked}")
    print(f"🔀 Entities deduplicated: {result.entities_deduplicated}")
    print(f"🔀 Relations deduplicated: {result.relations_deduplicated}")
    print(f"⏱️  Duration: {result.duration_seconds:.2f} seconds")
    
    if result.warnings:
        print(f"\n⚠️  Warnings: {len(result.warnings)}")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.errors:
        print(f"\n❌ Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error}")
    
    # Step 6: Query the graph
    print("\n" + "━" * 80)
    print("🔍 GRAPH STATISTICS")
    print("━" * 80)
    
    stats = await graph_store.get_stats()
    print(f"Total entities: {stats['entity_count']}")
    print(f"Total relations: {stats['relation_count']}")
    
    # Close resources
    await graph_store.close()
    
    print("\n✅ Example complete!")
    print("━" * 80)


if __name__ == "__main__":
    asyncio.run(main())

