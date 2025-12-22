"""
Performance Benchmarks for New Knowledge Graph Features

Benchmarks for:
- Structured data import (CSV/JSON)
- Reranking strategies
- Schema caching
- Query optimization
- Knowledge fusion
"""

import pytest
import time
import tempfile
import json
import os
from typing import List

from aiecs.application.knowledge_graph.builder.structured_pipeline import (
    StructuredDataPipeline,
    SchemaMapping,
    EntityMapping,
    RelationMapping
)
from aiecs.application.knowledge_graph.search.reranker import ResultReranker
from aiecs.application.knowledge_graph.search.reranker_strategies import (
    TextSimilarityReranker,
    SemanticReranker,
    StructuralReranker,
    HybridReranker
)
from aiecs.application.knowledge_graph.fusion.knowledge_fusion import KnowledgeFusion
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity


@pytest.fixture
async def clean_store():
    """Create a clean in-memory graph store"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


class TestStructuredDataImportBenchmarks:
    """Benchmark structured data import performance"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_csv_import_throughput_small(self, clean_store):
        """Benchmark CSV import with 100 rows"""
        # Create CSV with 100 rows
        rows = 100
        csv_content = "id,name,age\n"
        for i in range(rows):
            csv_content += f"{i},Person{i},{20 + (i % 50)}\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            mapping = SchemaMapping(
                entity_mappings=[
                    EntityMapping(
                        entity_type="Person",
                        id_column="id",
                        property_mappings={"name": "name", "age": "age"}
                    )
                ]
            )
            
            pipeline = StructuredDataPipeline(
                mapping=mapping,
                graph_store=clean_store,
                batch_size=50
            )
            
            # Benchmark import
            start_time = time.time()
            result = await pipeline.import_from_csv(csv_path)
            end_time = time.time()
            
            duration = end_time - start_time
            throughput = rows / duration if duration > 0 else 0
            
            print(f"\n=== CSV Import Benchmark (100 rows) ===")
            print(f"Duration: {duration:.3f}s")
            print(f"Throughput: {throughput:.1f} rows/second")
            print(f"Entities added: {result.entities_added}")
            
            assert result.success is True
            assert result.entities_added == rows
            assert throughput > 10  # At least 10 rows/second
            
        finally:
            os.unlink(csv_path)
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_csv_import_throughput_large(self, clean_store):
        """Benchmark CSV import with 1000 rows"""
        rows = 1000
        csv_content = "id,name,age,city\n"
        for i in range(rows):
            csv_content += f"{i},Person{i},{20 + (i % 50)},City{i % 10}\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            mapping = SchemaMapping(
                entity_mappings=[
                    EntityMapping(
                        entity_type="Person",
                        id_column="id",
                        property_mappings={"name": "name", "age": "age", "city": "city"}
                    )
                ]
            )
            
            pipeline = StructuredDataPipeline(
                mapping=mapping,
                graph_store=clean_store,
                batch_size=100
            )
            
            start_time = time.time()
            result = await pipeline.import_from_csv(csv_path)
            end_time = time.time()
            
            duration = end_time - start_time
            throughput = rows / duration if duration > 0 else 0
            
            print(f"\n=== CSV Import Benchmark (1000 rows) ===")
            print(f"Duration: {duration:.3f}s")
            print(f"Throughput: {throughput:.1f} rows/second")
            print(f"Entities added: {result.entities_added}")
            
            assert result.success is True
            assert throughput > 50  # At least 50 rows/second for larger batches
            
        finally:
            os.unlink(csv_path)
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_json_import_throughput(self, clean_store):
        """Benchmark JSON import with 500 records"""
        records = 500
        json_data = [
            {"id": str(i), "name": f"Person{i}", "age": 20 + (i % 50)}
            for i in range(records)
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_data, f)
            json_path = f.name
        
        try:
            mapping = SchemaMapping(
                entity_mappings=[
                    EntityMapping(
                        entity_type="Person",
                        id_column="id",
                        property_mappings={"name": "name", "age": "age"}
                    )
                ]
            )
            
            pipeline = StructuredDataPipeline(
                mapping=mapping,
                graph_store=clean_store,
                batch_size=100
            )
            
            start_time = time.time()
            result = await pipeline.import_from_json(json_path)
            end_time = time.time()
            
            duration = end_time - start_time
            throughput = records / duration if duration > 0 else 0
            
            print(f"\n=== JSON Import Benchmark (500 records) ===")
            print(f"Duration: {duration:.3f}s")
            print(f"Throughput: {throughput:.1f} records/second")
            print(f"Entities added: {result.entities_added}")
            
            assert result.success is True
            assert throughput > 50  # At least 50 records/second

        finally:
            os.unlink(json_path)


class TestRerankingBenchmarks:
    """Benchmark reranking strategy performance"""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_text_reranking_latency(self):
        """Benchmark text similarity reranking latency"""
        # Create test entities
        entities = [
            Entity(
                id=f"e{i}",
                entity_type="Paper",
                properties={
                    "title": f"Paper {i} about machine learning",
                    "abstract": f"This paper discusses machine learning topic {i}"
                }
            )
            for i in range(100)
        ]

        strategy = TextSimilarityReranker()
        reranker = ResultReranker(strategies=[strategy])

        # Benchmark reranking
        start_time = time.time()
        results = await reranker.rerank(
            query="machine learning algorithms",
            entities=entities,
            top_k=20
        )
        end_time = time.time()

        latency = (end_time - start_time) * 1000  # Convert to ms

        print(f"\n=== Text Reranking Benchmark ===")
        print(f"Entities: {len(entities)}")
        print(f"Latency: {latency:.2f}ms")
        print(f"Results returned: {len(results)}")

        assert len(results) <= 20
        assert latency < 500  # Should complete in under 500ms

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_hybrid_reranking_latency(self):
        """Benchmark hybrid reranking latency"""
        entities = [
            Entity(
                id=f"e{i}",
                entity_type="Paper",
                properties={
                    "title": f"Paper {i}",
                    "abstract": f"Abstract {i}"
                },
                embedding=[0.1 * (i % 10)] * 128
            )
            for i in range(50)
        ]

        strategy = HybridReranker(
            text_weight=0.4,
            semantic_weight=0.4,
            structural_weight=0.2
        )
        reranker = ResultReranker(strategies=[strategy])

        start_time = time.time()
        results = await reranker.rerank(
            query="research paper",
            entities=entities,
            top_k=10
        )
        end_time = time.time()

        latency = (end_time - start_time) * 1000

        print(f"\n=== Hybrid Reranking Benchmark ===")
        print(f"Entities: {len(entities)}")
        print(f"Latency: {latency:.2f}ms")
        print(f"Results returned: {len(results)}")

        assert len(results) <= 10
        assert latency < 1000  # Hybrid is slower but should be under 1s

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_reranking_overhead_comparison(self):
        """Compare reranking overhead across strategies"""
        entities = [
            Entity(
                id=f"e{i}",
                entity_type="Paper",
                properties={"title": f"Paper {i}"},
                embedding=[0.1] * 128
            )
            for i in range(100)
        ]

        strategies = {
            "text": TextSimilarityReranker(),
            "semantic": SemanticReranker(),
            "structural": StructuralReranker(),
            "hybrid": HybridReranker()
        }

        results = {}

        print(f"\n=== Reranking Strategy Comparison ===")
        print(f"Entities: {len(entities)}, Top-K: 20")

        for name, strategy in strategies.items():
            reranker = ResultReranker(strategies=[strategy])

            start_time = time.time()
            ranked = await reranker.rerank(
                query="test query",
                entities=entities,
                top_k=20
            )
            end_time = time.time()

            latency = (end_time - start_time) * 1000
            results[name] = latency

            print(f"{name:12s}: {latency:6.2f}ms")

        # Text should be fastest
        assert results["text"] < results["hybrid"]


class TestKnowledgeFusionBenchmarks:
    """Benchmark knowledge fusion performance"""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_fusion_performance_small_graph(self, clean_store):
        """Benchmark fusion with 50 entities"""
        # Add 50 entities with some duplicates
        for i in range(50):
            entity = Entity(
                id=f"e{i}",
                entity_type="Person",
                properties={
                    "name": f"Person {i // 5}",  # Create duplicates
                    "_provenance": {"source": f"doc{i % 10}"}
                },
                embedding=[0.1 * (i // 5)] * 128
            )
            await clean_store.add_entity(entity)

        fusion = KnowledgeFusion(clean_store, similarity_threshold=0.9)

        start_time = time.time()
        stats = await fusion.fuse_cross_document_entities()
        end_time = time.time()

        duration = end_time - start_time

        print(f"\n=== Knowledge Fusion Benchmark (50 entities) ===")
        print(f"Duration: {duration:.3f}s")
        print(f"Entities analyzed: {stats['entities_analyzed']}")
        print(f"Entities merged: {stats['entities_merged']}")
        print(f"Merge groups: {stats['merge_groups']}")

        assert stats["success"] is True
        assert duration < 5.0  # Should complete in under 5 seconds

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_fusion_performance_large_graph(self, clean_store):
        """Benchmark fusion with 200 entities"""
        for i in range(200):
            entity = Entity(
                id=f"e{i}",
                entity_type="Person",
                properties={
                    "name": f"Person {i // 10}",
                    "_provenance": {"source": f"doc{i % 20}"}
                },
                embedding=[0.1 * (i // 10)] * 128
            )
            await clean_store.add_entity(entity)

        fusion = KnowledgeFusion(clean_store, similarity_threshold=0.85)

        start_time = time.time()
        stats = await fusion.fuse_cross_document_entities()
        end_time = time.time()

        duration = end_time - start_time

        print(f"\n=== Knowledge Fusion Benchmark (200 entities) ===")
        print(f"Duration: {duration:.3f}s")
        print(f"Entities analyzed: {stats['entities_analyzed']}")
        print(f"Entities merged: {stats['entities_merged']}")
        print(f"Throughput: {stats['entities_analyzed'] / duration:.1f} entities/second")

        assert stats["success"] is True
        assert duration < 30.0  # Should complete in under 30 seconds


class TestPerformanceComparison:
    """Compare performance before/after optimizations"""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_search_with_vs_without_reranking(self, clean_store):
        """Compare search performance with and without reranking"""
        # Add test entities
        for i in range(100):
            entity = Entity(
                id=f"e{i}",
                entity_type="Paper",
                properties={"title": f"Paper {i}"},
                embedding=[0.1 * i] * 128
            )
            await clean_store.add_entity(entity)

        from aiecs.application.knowledge_graph.search.graph_search import GraphSearch

        search = GraphSearch(clean_store)

        # Without reranking
        start_time = time.time()
        results_no_rerank = await search.vector_search(
            query_embedding=[0.5] * 128,
            max_results=20
        )
        time_no_rerank = time.time() - start_time

        # With reranking
        reranker = ResultReranker(strategies=[TextSimilarityReranker()])
        start_time = time.time()
        results_with_rerank = await reranker.rerank(
            query="test query",
            entities=results_no_rerank,
            top_k=20
        )
        time_with_rerank = time.time() - start_time

        overhead = (time_with_rerank / time_no_rerank - 1) * 100 if time_no_rerank > 0 else 0

        print(f"\n=== Search Performance Comparison ===")
        print(f"Without reranking: {time_no_rerank*1000:.2f}ms")
        print(f"With reranking: {time_with_rerank*1000:.2f}ms")
        print(f"Overhead: {overhead:.1f}%")

        # Reranking overhead should be reasonable
        assert overhead < 200  # Less than 200% overhead

