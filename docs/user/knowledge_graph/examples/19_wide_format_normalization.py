"""
Example: Reshape Wide Format to Normalized Graph Structure

This example demonstrates how to convert wide format data (many columns)
to a normalized graph structure with separate Sample and Option entities
connected by HAS_VALUE relations.
"""

import asyncio
import pandas as pd
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.application.knowledge_graph.builder.data_reshaping import DataReshaping
from aiecs.application.knowledge_graph.builder.schema_mapping import SchemaMapping, EntityMapping, RelationMapping
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore


async def main():
    """Reshape wide format data to normalized graph structure."""
    
    print("🔄 Reshaping wide format data to normalized structure...")
    
    # Step 1: Create sample wide format data (1000 rows × 200 columns)
    print("\n📊 Creating sample wide format data...")
    data = {
        "sample_id": [f"sample_{i:03d}" for i in range(1, 1001)]
    }
    # Add 200 option columns
    for i in range(1, 201):
        data[f"option_{i:03d}"] = [0.5 + (i % 10) * 0.1 for _ in range(1000)]
    
    df_wide = pd.DataFrame(data)
    print(f"   Wide format: {df_wide.shape[0]} rows × {df_wide.shape[1]} columns")
    
    # Step 2: Reshape to long format
    print("\n🔄 Reshaping to long format...")
    reshaping = DataReshaping()
    
    id_vars = ["sample_id"]
    value_vars = [f"option_{i:03d}" for i in range(1, 201)]
    
    reshape_result = reshaping.melt_wide_to_long(
        df=df_wide,
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="option_id",
        value_name="value"
    )
    
    print(f"   Long format: {reshape_result.data.shape[0]} rows × {reshape_result.data.shape[1]} columns")
    print(f"   Transformation: {reshape_result.original_shape} → {reshape_result.new_shape}")
    
    # Step 3: Generate normalized schema mapping
    print("\n📋 Generating normalized schema mapping...")
    mapping = reshaping.generate_normalized_mapping(
        id_column="sample_id",
        entity_type="Sample",
        variable_type="Option",
        relation_type="HAS_VALUE"
    )
    
    print(f"   Entity types: {len(mapping.entity_mappings)}")
    print(f"   Relation types: {len(mapping.relation_mappings)}")
    
    # Step 4: Initialize graph store
    print("\n🗄️  Initializing graph store...")
    store = SQLiteGraphStore("normalized_graph.db")
    await store.initialize()
    
    # Step 5: Create pipeline
    print("\n📥 Creating pipeline...")
    pipeline = StructuredDataPipeline(
        mapping=mapping,
        graph_store=store,
        batch_size=1000  # Process 1000 relations at a time
    )
    
    # Step 6: Import reshaped data
    print("\n📥 Importing normalized data...")
    result = await pipeline.import_from_dataframe(reshape_result.data)
    
    # Step 7: Display results
    print(f"\n✅ Import complete!")
    print(f"   Sample entities: {len(await store.get_entities_by_type('Sample'))}")
    print(f"   Option entities: {len(await store.get_entities_by_type('Option'))}")
    print(f"   Relations added: {result.relations_added}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    
    if result.performance_metrics:
        print(f"\n📈 Performance Metrics:")
        print(f"   Throughput: {result.performance_metrics.rows_per_second:.0f} rows/sec")
    
    # Step 8: Query normalized structure
    print("\n🔍 Querying normalized graph...")
    
    # Get a sample entity
    samples = await store.get_entities_by_type("Sample")
    if samples:
        sample = samples[0]
        print(f"\n📋 Sample Entity:")
        print(f"   ID: {sample.id}")
        print(f"   Type: {sample.entity_type}")
        
        # Get relations (options) for this sample
        neighbors = await store.get_neighbors(sample.id, direction="outgoing")
        print(f"   Connected to {len(neighbors)} options")
        
        # Show first few option values
        if neighbors:
            print(f"\n   First 5 option values:")
            for i, neighbor in enumerate(neighbors[:5]):
                # Get relation to see value property
                relations = await store.get_relations_by_entity(sample.id, neighbor.id)
                if relations:
                    rel = relations[0]
                    value = rel.properties.get("value", "N/A")
                    print(f"      {neighbor.id}: {value}")
    
    await store.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())


