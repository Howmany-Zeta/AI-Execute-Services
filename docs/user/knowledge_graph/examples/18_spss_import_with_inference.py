"""
Example: Import SPSS File with Automatic Schema Inference

This example demonstrates how to import SPSS (.sav) files into a knowledge graph
with automatic schema inference, eliminating the need for manual schema mapping.
"""

import asyncio
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.application.knowledge_graph.builder.schema_inference import SchemaInference
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore


async def main():
    """Import SPSS file with automatic schema inference."""
    
    print("📊 Importing SPSS file with automatic schema inference...")
    
    # Step 1: Initialize graph store
    store = SQLiteGraphStore("spss_import.db")
    await store.initialize()
    
    # Step 2: Infer schema from SPSS file
    print("\n🔍 Inferring schema from SPSS file...")
    inference = SchemaInference()
    inferred = inference.infer_from_spss("survey_data.sav")
    
    # Review inferred schema
    print(f"\n✅ Inferred Schema:")
    print(f"   Entity types: {len(inferred.entity_mappings)}")
    print(f"   Relation types: {len(inferred.relation_mappings)}")
    print(f"   Confidence scores: {inferred.confidence_scores}")
    
    if inferred.warnings:
        print(f"\n⚠️  Warnings:")
        for warning in inferred.warnings:
            print(f"   - {warning}")
    
    # Step 3: Convert to schema mapping
    mapping = inferred.to_schema_mapping()
    
    # Step 4: Create pipeline with inferred schema
    print("\n📥 Creating pipeline...")
    pipeline = StructuredDataPipeline(
        mapping=mapping,
        graph_store=store,
        batch_size=100
    )
    
    # Step 5: Import SPSS file
    print("\n📥 Importing SPSS data...")
    result = await pipeline.import_from_spss("survey_data.sav")
    
    # Step 6: Display results
    print(f"\n✅ Import complete!")
    print(f"   Entities added: {result.entities_added}")
    print(f"   Relations added: {result.relations_added}")
    print(f"   Rows processed: {result.rows_processed}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    
    if result.performance_metrics:
        print(f"\n📈 Performance Metrics:")
        print(f"   Throughput: {result.performance_metrics.rows_per_second:.0f} rows/sec")
        print(f"   Peak memory: {result.performance_metrics.peak_memory_mb:.1f} MB")
    
    # Step 7: Query graph
    print("\n🔍 Querying graph...")
    entities = await store.get_entities_by_type(inferred.entity_mappings[0].entity_type)
    print(f"   Found {len(entities)} entities of type '{inferred.entity_mappings[0].entity_type}'")
    
    # Show sample entity with SPSS metadata
    if entities:
        sample = entities[0]
        print(f"\n📋 Sample Entity:")
        print(f"   ID: {sample.id}")
        print(f"   Type: {sample.entity_type}")
        print(f"   Properties: {list(sample.properties.keys())[:5]}...")
        
        # Check for SPSS metadata
        if "_spss_variable_labels" in sample.properties:
            print(f"   SPSS variable labels preserved: ✅")
    
    await store.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())


