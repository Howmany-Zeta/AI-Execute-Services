"""
Example: Data Quality Validation During Import

This example demonstrates how to validate data quality during import with
range checks, outlier detection, and completeness validation.
"""

import asyncio
import pandas as pd
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping
)
from aiecs.application.knowledge_graph.builder.data_quality import (
    DataQualityValidator,
    ValidationConfig,
    RangeRule,
    OutlierRule
)
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore


async def main():
    """Import data with quality validation."""
    
    print("📊 Importing data with quality validation...")
    
    # Step 1: Create sample data with some quality issues
    print("\n📊 Creating sample data...")
    data = {
        "sample_id": [f"sample_{i:03d}" for i in range(1, 101)],
        "option_1": [0.5 + 0.1 * i for i in range(100)],  # Values 0.5-10.4 (some out of range)
        "option_2": [0.2 * i for i in range(100)],  # Values 0-19.8
        "option_3": [None if i % 10 == 0 else 0.3 * i for i in range(100)],  # Some missing
    }
    df = pd.DataFrame(data)
    print(f"   Created {len(df)} samples")
    print(f"   Note: Some values out of range, some missing")
    
    # Step 2: Define schema mapping
    print("\n📋 Defining schema...")
    mapping = SchemaMapping(
        entity_mappings=[
            EntityMapping(
                source_columns=["sample_id", "option_1", "option_2", "option_3"],
                entity_type="Sample",
                property_mapping={
                    "sample_id": "id",
                    "option_1": "option_1",
                    "option_2": "option_2",
                    "option_3": "option_3"
                },
                id_column="sample_id"
            )
        ]
    )
    
    # Step 3: Configure validation rules
    print("\n✅ Configuring validation rules...")
    validation_config = ValidationConfig(
        rules={
            "Sample": {
                "option_1": RangeRule(min=0.0, max=1.0),  # Should be 0-1
                "option_2": RangeRule(min=0.0, max=10.0),  # Should be 0-10
            }
        },
        outlier_detection={
            "Sample": {
                "option_1": OutlierRule(method="zscore", threshold=3.0)
            }
        },
        required_properties={
            "Sample": ["sample_id", "option_1"]  # option_1 required
        },
        fail_on_violations=False  # Continue import, log violations
    )
    
    print("   Validation rules:")
    print("     - option_1: Range 0.0-1.0")
    print("     - option_2: Range 0.0-10.0")
    print("     - option_1: Outlier detection (z-score > 3)")
    print("     - Required: sample_id, option_1")
    
    # Step 4: Initialize graph store
    print("\n🗄️  Initializing graph store...")
    store = SQLiteGraphStore("validated_graph.db")
    await store.initialize()
    
    # Step 5: Create pipeline with validation
    print("\n📥 Creating pipeline with validation...")
    pipeline = StructuredDataPipeline(
        mapping=mapping,
        graph_store=store,
        validation_config=validation_config,
        batch_size=50
    )
    
    # Step 6: Import data with validation
    print("\n📥 Importing data...")
    result = await pipeline.import_from_dataframe(df)
    
    # Step 7: Display results
    print(f"\n✅ Import complete!")
    print(f"   Entities added: {result.entities_added}")
    print(f"   Rows processed: {result.rows_processed}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    
    # Step 8: Display quality report
    if result.quality_report:
        print(f"\n📋 Quality Report:")
        report = result.quality_report
        
        if report.range_violations:
            print(f"\n   Range Violations: {len(report.range_violations)}")
            for violation in report.range_violations[:5]:  # Show first 5
                print(f"     Row {violation.row_idx}, {violation.column}: "
                      f"{violation.value} (expected {violation.rule})")
        
        if report.outliers:
            print(f"\n   Outliers Detected: {len(report.outliers)}")
            for outlier in report.outliers[:5]:  # Show first 5
                print(f"     Row {outlier.row_idx}, {outlier.column}: "
                      f"{outlier.value} (z-score: {outlier.z_score:.2f})")
        
        if report.completeness:
            print(f"\n   Completeness:")
            for prop, pct in report.completeness.items():
                print(f"     {prop}: {pct:.1f}%")
        
        if report.summary:
            print(f"\n   Summary:")
            for key, value in report.summary.items():
                print(f"     {key}: {value}")
    else:
        print("\n   No quality report generated")
    
    await store.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())

