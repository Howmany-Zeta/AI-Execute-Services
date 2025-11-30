"""
Example: Building Knowledge Graph from Document

This example demonstrates how to build a knowledge graph from a document file
(PDF, DOCX, TXT) using the DocumentGraphBuilder.
"""

import asyncio
from pathlib import Path
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.extractors.llm_entity_extractor import LLMEntityExtractor
from aiecs.application.knowledge_graph.extractors.ner_entity_extractor import NEREntityExtractor
from aiecs.application.knowledge_graph.extractors.llm_relation_extractor import LLMRelationExtractor
from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder
from aiecs.application.knowledge_graph.builder.document_builder import DocumentGraphBuilder


async def main():
    print("━" * 80)
    print("Knowledge Graph Builder Example: Extract from Document")
    print("━" * 80)
    
    # Create a sample text file for demonstration
    sample_file = Path("sample_document.txt")
    sample_text = """
    The Quantum Computing Revolution
    
    Dr. Emily Chen, a renowned physicist at MIT, has been leading groundbreaking
    research in quantum computing. Her team recently achieved a major breakthrough
    in quantum error correction, published in Nature Physics.
    
    Quantum Corp, a startup founded in Boston in 2019, has partnered with MIT
    to commercialize these technologies. The company's CEO, Michael Rodriguez,
    believes this partnership will accelerate the development of practical
    quantum computers.
    
    The research has implications for cryptography, drug discovery, and
    artificial intelligence. Companies like IBM and Google are also investing
    heavily in quantum computing research.
    """
    
    # Write sample file
    sample_file.write_text(sample_text)
    print(f"\n📄 Created sample document: {sample_file}")
    print(f"   ({len(sample_text)} characters)")
    
    # Step 1: Initialize graph store
    print("\n🔧 Initializing graph store...")
    graph_store = InMemoryGraphStore()
    await graph_store.initialize()
    
    # Step 2: Initialize extractors
    print("🔧 Initializing extractors...")
    entity_extractor = NEREntityExtractor(model="en_core_web_sm")  # Fast, offline
    relation_extractor = LLMRelationExtractor()  # Requires LLM API
    
    # Step 3: Create builders
    print("🔧 Creating builders...")
    graph_builder = GraphBuilder(
        graph_store=graph_store,
        entity_extractor=entity_extractor,
        relation_extractor=relation_extractor,
        enable_deduplication=True,
        enable_linking=True,
        progress_callback=lambda msg, pct: print(f"  [{pct*100:>3.0f}%] {msg}")
    )
    
    document_builder = DocumentGraphBuilder(
        graph_builder=graph_builder,
        chunk_size=500,  # Small chunks for demo
        chunk_overlap=50,
        enable_chunking=True,
        parallel_chunks=False  # Sequential for clearer output
    )
    
    # Step 4: Build graph from document
    print(f"\n🚀 Building knowledge graph from: {sample_file}")
    result = await document_builder.build_from_document(sample_file)
    
    # Step 5: Display results
    print("\n" + "━" * 80)
    print("📊 BUILD RESULTS")
    print("━" * 80)
    print(f"✅ Success: {result.success}")
    print(f"📄 Document: {result.document_path}")
    print(f"📋 Document type: {result.document_type}")
    print(f"🧩 Total chunks: {result.total_chunks}")
    print(f"✅ Chunks processed: {result.chunks_processed}")
    print(f"🔢 Total entities added: {result.total_entities_added}")
    print(f"🔗 Total relations added: {result.total_relations_added}")
    
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
    
    # Cleanup
    await graph_store.close()
    sample_file.unlink()  # Delete sample file
    
    print("\n✅ Example complete!")
    print("━" * 80)


if __name__ == "__main__":
    asyncio.run(main())

