"""
Example: Statistical Aggregation During Import

This example demonstrates how to compute statistical aggregations (mean, std dev, min, max)
during data import and store them as entity properties.
"""

import asyncio
import pandas as pd
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    AggregationConfig
)
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore


async def main():
    """Import data with statistical aggregation."""
    
    print("📊 Importing data with statistical aggregation...")
    
    # Step 1: Create sample data
    print("\n📊 Creating sample data...")
    data = {
        "sample_id": [f"sample_{i:03d}" for i in range(1, 101)],
        "option_1": [0.1 * i for i in range(100)],
        "option_2": [0.2 * i for i in range(100)],
        "option_3": [0.3 * i for i in range(100)],
        "option_4": [0.4 * i for i in range(100)],
        "option_5": [0.5 * i for i in range(100)],
    }
    df = pd.DataFrame(data)
    print(f"   Created {len(df)} samples with 5 options each")
    
    # Step 2: Define schema mapping with aggregation
    print("\n📋 Defining schema with aggregation...")
    
    # Get option column names
    option_columns = [f"option_{i}" for i in range(1, 6)]
    
    mapping = SchemaMapping(
        entity_mappings=[
            EntityMapping(
                source_columns=["sample_id"] + option_columns,
                entity_type="Sample",
                property_mapping={"sample_id": "id"},
                id_column="sample_id"
            )
        ],
        aggregations={
            "Sample": {
                "option_values": {
                    "mean": "avg_value",
                    "std": "std_value",
                    "min": "min_value",
                    "max": "max_value",
                    "count": "option_count"
                }
            }
        }
    )
    
    print("   Aggregations configured:")
    print("     - Mean → avg_value")
    print("     - Std Dev → std_value")
    print("     - Min → min_value")
    print("     - Max → max_value")
    print("     - Count → option_count")
    
    # Step 3: Initialize graph store
    print("\n🗄️  Initializing graph store...")
    store = SQLiteGraphStore("aggregated_graph.db")
    await store.initialize()
    
    # Step 4: Create pipeline
    print("\n📥 Creating pipeline...")
    pipeline = StructuredDataPipeline(
        mapping=mapping,
        graph_store=store,
        batch_size=50
    )
    
    # Step 5: Import data with aggregation
    print("\n📥 Importing data...")
    result = await pipeline.import_from_dataframe(df)
    
    # Step 6: Display results
    print(f"\n✅ Import complete!")
    print(f"   Entities added: {result.entities_added}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    
    # Step 7: Verify aggregated values
    print("\n🔍 Verifying aggregated values...")
    samples = await store.get_entities_by_type("Sample")
    
    if samples:
        sample = samples[0]
        print(f"\n📋 Sample Entity: {sample.id}")
        print(f"   Properties with aggregations:")
        
        if "avg_value" in sample.properties:
            print(f"     avg_value: {sample.properties['avg_value']:.4f}")
        if "std_value" in sample.properties:
            print(f"     std_value: {sample.properties['std_value']:.4f}")
        if "min_value" in sample.properties:
            print(f"     min_value: {sample.properties['min_value']:.4f}")
        if "max_value" in sample.properties:
            print(f"     max_value: {sample.properties['max_value']:.4f}")
        if "option_count" in sample.properties:
            print(f"     option_count: {sample.properties['option_count']}")
        
        # Verify aggregation accuracy
        print(f"\n   Verification:")
        option_values = [
            sample.properties.get(f"option_{i}", 0)
            for i in range(1, 6)
            if f"option_{i}" in sample.properties
        ]
        if option_values:
            import statistics
            actual_mean = statistics.mean(option_values)
            actual_std = statistics.stdev(option_values) if len(option_values) > 1 else 0
            print(f"     Actual mean: {actual_mean:.4f}")
            print(f"     Computed mean: {sample.properties.get('avg_value', 'N/A')}")
            print(f"     Match: {'✅' if abs(actual_mean - sample.properties.get('avg_value', 0)) < 0.001 else '❌'}")
    
    await store.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())

