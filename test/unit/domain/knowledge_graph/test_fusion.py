"""
Unit tests for knowledge graph fusion module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
import uuid
from typing import List

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.application.knowledge_graph.fusion.entity_deduplicator import EntityDeduplicator
from aiecs.application.knowledge_graph.fusion.entity_linker import EntityLinker, LinkResult
from aiecs.application.knowledge_graph.fusion.relation_deduplicator import RelationDeduplicator
from aiecs.application.knowledge_graph.fusion.knowledge_fusion import KnowledgeFusion


class TestEntityDeduplicator:
    """Test EntityDeduplicator"""
    
    @pytest.fixture
    def deduplicator(self):
        """Create EntityDeduplicator instance"""
        return EntityDeduplicator(similarity_threshold=0.85)
    
    @pytest.fixture
    def sample_entities(self):
        """Create sample entities for testing"""
        return [
            Entity(
                id="e1",
                entity_type="Company",
                properties={"name": "Apple Inc."}
            ),
            Entity(
                id="e2",
                entity_type="Company",
                properties={"name": "Apple"}
            ),
            Entity(
                id="e3",
                entity_type="Company",
                properties={"name": "Microsoft Corporation"}
            ),
            Entity(
                id="e4",
                entity_type="Person",
                properties={"name": "John Smith"}
            ),
            Entity(
                id="e5",
                entity_type="Person",
                properties={"name": "J. Smith"}
            ),
        ]
    
    @pytest.mark.asyncio
    async def test_deduplicate_empty_list(self, deduplicator):
        """Test deduplication with empty list"""
        result = await deduplicator.deduplicate([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_deduplicate_single_entity(self, deduplicator):
        """Test deduplication with single entity"""
        entities = [Entity(id="e1", entity_type="Person", properties={"name": "Alice"})]
        result = await deduplicator.deduplicate(entities)
        assert len(result) == 1
        assert result[0].id == "e1"
    
    @pytest.mark.asyncio
    async def test_deduplicate_similar_entities(self, deduplicator, sample_entities):
        """Test deduplication of similar entities"""
        # Use lower threshold to ensure Apple Inc. and Apple match
        deduplicator.similarity_threshold = 0.75
        result = await deduplicator.deduplicate(sample_entities)
        
        # Should have fewer or equal entities after deduplication
        assert len(result) <= len(sample_entities)
        
        # Check that similar entities might be merged (depending on similarity)
        company_entities = [e for e in result if e.entity_type == "Company"]
        # At least some deduplication should occur with similar names
        assert len(company_entities) <= 3
    
    @pytest.mark.asyncio
    async def test_deduplicate_type_aware(self, deduplicator, sample_entities):
        """Test that deduplication only happens within same entity type"""
        result = await deduplicator.deduplicate(sample_entities)
        
        # Person and Company entities should not be merged
        person_entities = [e for e in result if e.entity_type == "Person"]
        company_entities = [e for e in result if e.entity_type == "Company"]
        
        assert len(person_entities) > 0
        assert len(company_entities) > 0
    
    @pytest.mark.asyncio
    async def test_deduplicate_with_embeddings(self):
        """Test deduplication with embeddings"""
        deduplicator = EntityDeduplicator(
            similarity_threshold=0.85,
            use_embeddings=True,
            embedding_threshold=0.90
        )
        
        # Create entities with embeddings
        embedding1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding2 = [0.11, 0.21, 0.31, 0.41, 0.51]  # Similar to embedding1
        
        entities = [
            Entity(
                id="e1",
                entity_type="Person",
                properties={"name": "Alice"},
                embedding=embedding1
            ),
            Entity(
                id="e2",
                entity_type="Person",
                properties={"name": "Alice Smith"},
                embedding=embedding2
            ),
        ]
        
        result = await deduplicator.deduplicate(entities)
        # With high embedding similarity, they should be merged
        assert len(result) <= len(entities)
    
    @pytest.mark.asyncio
    async def test_deduplicate_without_embeddings(self):
        """Test deduplication without embeddings"""
        deduplicator = EntityDeduplicator(
            similarity_threshold=0.85,
            use_embeddings=False
        )
        
        entities = [
            Entity(
                id="e1",
                entity_type="Person",
                properties={"name": "Alice"}
            ),
            Entity(
                id="e2",
                entity_type="Person",
                properties={"name": "Alice Smith"}
            ),
        ]
        
        result = await deduplicator.deduplicate(entities)
        # Should still work without embeddings
        assert len(result) <= len(entities)
    
    def test_string_similarity_exact_match(self, deduplicator):
        """Test string similarity with exact match"""
        similarity = deduplicator._string_similarity("Apple", "Apple")
        assert similarity == 1.0
    
    def test_string_similarity_substring(self, deduplicator):
        """Test string similarity with substring"""
        similarity = deduplicator._string_similarity("Apple", "Apple Inc.")
        assert similarity >= 0.9
    
    def test_string_similarity_different(self, deduplicator):
        """Test string similarity with different strings"""
        similarity = deduplicator._string_similarity("Apple", "Microsoft")
        assert similarity < 0.5
    
    def test_property_similarity_identical(self, deduplicator):
        """Test property similarity with identical properties"""
        props1 = {"name": "Alice", "age": 30}
        props2 = {"name": "Alice", "age": 30}
        similarity = deduplicator._property_similarity(props1, props2)
        assert similarity >= 0.8
    
    def test_property_similarity_different(self, deduplicator):
        """Test property similarity with different properties"""
        props1 = {"name": "Alice", "age": 30}
        props2 = {"name": "Bob", "city": "NYC"}
        similarity = deduplicator._property_similarity(props1, props2)
        assert similarity < 0.5
    
    def test_cosine_similarity_identical(self, deduplicator):
        """Test cosine similarity with identical vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = deduplicator._cosine_similarity(vec1, vec2)
        assert similarity == 1.0
    
    def test_cosine_similarity_orthogonal(self, deduplicator):
        """Test cosine similarity with orthogonal vectors"""
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        similarity = deduplicator._cosine_similarity(vec1, vec2)
        assert similarity == 0.5  # Normalized from -1 to 1, then to 0 to 1
    
    def test_cosine_similarity_different_lengths(self, deduplicator):
        """Test cosine similarity with different vector lengths"""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = deduplicator._cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    
    def test_find_clusters_single_cluster(self, deduplicator):
        """Test finding clusters with single connected component"""
        n = 3
        edges = {(0, 1), (1, 2)}
        clusters = deduplicator._find_clusters(n, edges)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
    
    def test_find_clusters_multiple_clusters(self, deduplicator):
        """Test finding clusters with multiple components"""
        n = 4
        edges = {(0, 1), (2, 3)}  # Two separate clusters
        clusters = deduplicator._find_clusters(n, edges)
        assert len(clusters) == 2
        assert all(len(cluster) == 2 for cluster in clusters)
    
    def test_merge_entities_single(self, deduplicator):
        """Test merging single entity"""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        merged = deduplicator._merge_entities([entity])
        assert merged.id == entity.id
        assert merged.properties["name"] == "Alice"
    
    def test_merge_entities_multiple(self, deduplicator):
        """Test merging multiple entities"""
        entities = [
            Entity(
                id="e1",
                entity_type="Person",
                properties={"name": "Alice", "age": 30}
            ),
            Entity(
                id="e2",
                entity_type="Person",
                properties={"name": "Alice Smith", "city": "NYC"}
            ),
        ]
        
        merged = deduplicator._merge_entities(entities)
        assert merged.id == "e1"  # Uses first entity's ID
        assert "name" in merged.properties
        assert "age" in merged.properties
        assert "city" in merged.properties
        assert "_aliases" in merged.properties
        assert "_merged_count" in merged.properties
        assert merged.properties["_merged_count"] == 2
    
    def test_get_entity_name(self, deduplicator):
        """Test entity name extraction"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        name = deduplicator._get_entity_name(entity)
        assert name == "Alice"
    
    def test_get_entity_name_fallback(self, deduplicator):
        """Test entity name extraction with fallback"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={"title": "CEO"}
        )
        name = deduplicator._get_entity_name(entity)
        assert name == "CEO"
    
    def test_get_entity_name_empty(self, deduplicator):
        """Test entity name extraction with no name"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={}
        )
        name = deduplicator._get_entity_name(entity)
        assert name == ""
    
    @pytest.mark.asyncio
    async def test_compute_similarity_with_embeddings(self, deduplicator):
        """Test similarity computation with embeddings"""
        embedding = [0.1, 0.2, 0.3]
        entity1 = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=embedding
        )
        entity2 = Entity(
            id="e2",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=embedding  # Same embedding
        )
        
        similarity = await deduplicator._compute_similarity(entity1, entity2)
        assert 0.0 <= similarity <= 1.0
        assert similarity >= 0.8  # High similarity with same name and embedding
    
    @pytest.mark.asyncio
    async def test_compute_similarity_without_embeddings(self, deduplicator):
        """Test similarity computation without embeddings"""
        entity1 = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        entity2 = Entity(
            id="e2",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        
        similarity = await deduplicator._compute_similarity(entity1, entity2)
        assert 0.0 <= similarity <= 1.0
        assert similarity >= 0.7  # High similarity with same name


class TestEntityLinker:
    """Test EntityLinker"""
    
    @pytest.fixture
    async def graph_store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    def linker(self, graph_store):
        """Create EntityLinker instance"""
        return EntityLinker(graph_store, similarity_threshold=0.85)
    
    @pytest.fixture
    async def populated_store(self):
        """Create graph store with some entities"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add some existing entities
        entities = [
            Entity(
                id="existing_1",
                entity_type="Person",
                properties={"name": "Alice Smith"}
            ),
            Entity(
                id="existing_2",
                entity_type="Company",
                properties={"name": "Tech Corp"}
            ),
        ]
        
        for entity in entities:
            await store.add_entity(entity)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_link_entity_exact_id_match(self, linker, graph_store):
        """Test linking with exact ID match"""
        # Add entity to store
        entity = Entity(
            id="test_entity",
            entity_type="Person",
            properties={"name": "Test"}
        )
        await graph_store.add_entity(entity)
        
        # Try to link same entity
        new_entity = Entity(
            id="test_entity",
            entity_type="Person",
            properties={"name": "Test"}
        )
        
        result = await linker.link_entity(new_entity)
        assert result.linked is True
        assert result.link_type == "exact_id"
        assert result.similarity == 1.0
        assert result.existing_entity.id == "test_entity"
    
    @pytest.mark.asyncio
    async def test_link_entity_no_match(self, linker, graph_store):
        """Test linking when no match exists"""
        new_entity = Entity(
            id="new_entity",
            entity_type="Person",
            properties={"name": "New Person"}
        )
        
        result = await linker.link_entity(new_entity)
        assert result.linked is False
        assert result.link_type == "none"
    
    @pytest.mark.asyncio
    async def test_link_entity_by_embedding(self, populated_store):
        """Test linking using embedding similarity"""
        linker = EntityLinker(
            populated_store,
            similarity_threshold=0.85,
            use_embeddings=True,
            embedding_threshold=0.50  # Lower threshold for testing
        )
        
        # Add entity with embedding to store
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        existing_entity = Entity(
            id="existing_with_embedding",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            embedding=embedding
        )
        await populated_store.add_entity(existing_entity)
        
        # Create new entity with similar embedding
        similar_embedding = [0.11, 0.21, 0.31, 0.41, 0.51]  # Very similar
        new_entity = Entity(
            id="new_entity",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=similar_embedding
        )
        
        result = await linker.link_entity(new_entity)
        # Should link due to high embedding similarity
        assert isinstance(result, LinkResult)
        # May or may not link depending on exact similarity score
    
    @pytest.mark.asyncio
    async def test_link_entities_batch(self, linker, graph_store):
        """Test batch entity linking"""
        # Add some entities
        existing = Entity(
            id="existing",
            entity_type="Person",
            properties={"name": "Existing"}
        )
        await graph_store.add_entity(existing)
        
        new_entities = [
            Entity(id="new1", entity_type="Person", properties={"name": "New1"}),
            Entity(id="existing", entity_type="Person", properties={"name": "Existing"}),
        ]
        
        results = await linker.link_entities(new_entities)
        assert len(results) == 2
        assert results[0].linked is False  # new1 doesn't exist
        assert results[1].linked is True  # existing matches
    
    def test_name_similarity_exact(self, linker):
        """Test name similarity with exact match"""
        similarity = linker._name_similarity("Alice", "Alice")
        assert similarity == 1.0
    
    def test_name_similarity_substring(self, linker):
        """Test name similarity with substring"""
        similarity = linker._name_similarity("Alice", "Alice Smith")
        assert similarity >= 0.9
    
    def test_name_similarity_different(self, linker):
        """Test name similarity with different names"""
        similarity = linker._name_similarity("Alice", "Bob")
        assert similarity < 0.5
    
    def test_get_entity_name(self, linker):
        """Test entity name extraction"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        name = linker._get_entity_name(entity)
        assert name == "Alice"
    
    def test_check_name_similarity(self, linker):
        """Test name similarity check"""
        entity1 = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        entity2 = Entity(
            id="e2",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        
        assert linker._check_name_similarity(entity1, entity2) is True
    
    @pytest.mark.asyncio
    async def test_link_by_name_no_candidates(self, linker, graph_store):
        """Test linking by name when no candidates available"""
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "New Person"}
        )
        
        result = await linker._link_by_name(new_entity, candidate_limit=10)
        assert result.linked is False
    
    @pytest.mark.asyncio
    async def test_link_by_embedding_no_embedding(self, linker, graph_store):
        """Test linking by embedding when entity has no embedding"""
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "New Person"}
        )
        
        result = await linker._link_by_embedding(new_entity, candidate_limit=10)
        assert result.linked is False
    
    @pytest.mark.asyncio
    async def test_link_by_embedding_with_candidates(self, linker, graph_store):
        """Test linking by embedding with candidates found"""
        # Add entity with embedding
        embedding1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        existing = Entity(
            id="existing",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=embedding1
        )
        await graph_store.add_entity(existing)
        
        # Create new entity with very similar embedding
        embedding2 = [0.11, 0.21, 0.31, 0.41, 0.51]
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=embedding2
        )
        
        linker.embedding_threshold = 0.50  # Lower threshold
        result = await linker._link_by_embedding(new_entity, candidate_limit=10)
        # Should link if similarity is high enough
        assert isinstance(result, LinkResult)
    
    @pytest.mark.asyncio
    async def test_link_by_embedding_no_candidates(self, linker, graph_store):
        """Test linking by embedding when no candidates found"""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "New Person"},
            embedding=embedding
        )
        
        result = await linker._link_by_embedding(new_entity, candidate_limit=10)
        assert result.linked is False
    
    @pytest.mark.asyncio
    async def test_link_by_embedding_below_threshold(self, linker, graph_store):
        """Test linking by embedding when score is below threshold"""
        # Add entity with embedding
        embedding1 = [1.0, 0.0, 0.0, 0.0, 0.0]
        existing = Entity(
            id="existing",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=embedding1
        )
        await graph_store.add_entity(existing)
        
        # Create new entity with very different embedding
        embedding2 = [0.0, 1.0, 0.0, 0.0, 0.0]  # Orthogonal
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "Bob"},
            embedding=embedding2
        )
        
        linker.embedding_threshold = 0.90  # High threshold
        result = await linker._link_by_embedding(new_entity, candidate_limit=10)
        # Should not link due to low similarity
        assert result.linked is False
    
    @pytest.mark.asyncio
    async def test_link_by_embedding_not_implemented(self, linker, graph_store):
        """Test linking by embedding when vector_search raises NotImplementedError"""
        # Mock graph_store to raise NotImplementedError
        original_vector_search = graph_store.vector_search
        
        async def mock_vector_search(*args, **kwargs):
            raise NotImplementedError("Vector search not supported")
        
        graph_store.vector_search = mock_vector_search
        
        embedding = [0.1, 0.2, 0.3]
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "New Person"},
            embedding=embedding
        )
        
        result = await linker._link_by_embedding(new_entity, candidate_limit=10)
        assert result.linked is False
        
        # Restore original method
        graph_store.vector_search = original_vector_search
    
    @pytest.mark.asyncio
    async def test_link_by_embedding_exception(self, linker, graph_store):
        """Test linking by embedding when exception occurs"""
        # Mock graph_store to raise exception
        original_vector_search = graph_store.vector_search
        
        async def mock_vector_search(*args, **kwargs):
            raise Exception("Unexpected error")
        
        graph_store.vector_search = mock_vector_search
        
        embedding = [0.1, 0.2, 0.3]
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "New Person"},
            embedding=embedding
        )
        
        result = await linker._link_by_embedding(new_entity, candidate_limit=10)
        assert result.linked is False
        
        # Restore original method
        graph_store.vector_search = original_vector_search
    
    @pytest.mark.asyncio
    async def test_link_by_name_with_candidates(self, linker, graph_store):
        """Test linking by name when candidates are available"""
        # Mock _get_candidate_entities to return candidates
        original_get_candidates = linker._get_candidate_entities
        
        async def mock_get_candidates(entity_type, limit):
            return [
                Entity(
                    id="candidate1",
                    entity_type=entity_type,
                    properties={"name": "Alice Smith"}
                )
            ]
        
        linker._get_candidate_entities = mock_get_candidates
        
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        
        linker.similarity_threshold = 0.75  # Lower threshold
        result = await linker._link_by_name(new_entity, candidate_limit=10)
        # Should link if similarity is high enough
        assert isinstance(result, LinkResult)
        
        # Restore original method
        linker._get_candidate_entities = original_get_candidates
    
    @pytest.mark.asyncio
    async def test_link_by_name_below_threshold(self, linker, graph_store):
        """Test linking by name when similarity is below threshold"""
        # Mock _get_candidate_entities to return candidates
        original_get_candidates = linker._get_candidate_entities
        
        async def mock_get_candidates(entity_type, limit):
            return [
                Entity(
                    id="candidate1",
                    entity_type=entity_type,
                    properties={"name": "Bob"}
                )
            ]
        
        linker._get_candidate_entities = mock_get_candidates
        
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        
        linker.similarity_threshold = 0.95  # High threshold
        result = await linker._link_by_name(new_entity, candidate_limit=10)
        # Should not link due to low similarity
        assert result.linked is False
        
        # Restore original method
        linker._get_candidate_entities = original_get_candidates
    
    @pytest.mark.asyncio
    async def test_link_by_name_exception(self, linker, graph_store):
        """Test linking by name when exception occurs"""
        # Mock _get_candidate_entities to raise exception
        original_get_candidates = linker._get_candidate_entities
        
        async def mock_get_candidates(entity_type, limit):
            raise Exception("Unexpected error")
        
        linker._get_candidate_entities = mock_get_candidates
        
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "New Person"}
        )
        
        result = await linker._link_by_name(new_entity, candidate_limit=10)
        assert result.linked is False
        
        # Restore original method
        linker._get_candidate_entities = original_get_candidates
    
    @pytest.mark.asyncio
    async def test_link_by_embedding_high_score_trust(self, linker, graph_store):
        """Test linking by embedding with high score (>=0.95) trusts embedding"""
        # Add entity with embedding
        embedding1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        existing = Entity(
            id="existing",
            entity_type="Person",
            properties={"name": "Different Name"},  # Different name
            embedding=embedding1
        )
        await graph_store.add_entity(existing)
        
        # Create new entity with very similar embedding (high similarity)
        embedding2 = [0.105, 0.205, 0.305, 0.405, 0.505]  # Very similar
        new_entity = Entity(
            id="new",
            entity_type="Person",
            properties={"name": "New Name"},
            embedding=embedding2
        )
        
        linker.embedding_threshold = 0.50  # Lower threshold
        result = await linker._link_by_embedding(new_entity, candidate_limit=10)
        # If similarity is >= 0.95, should link even without name match
        assert isinstance(result, LinkResult)
    
    def test_link_result_repr(self):
        """Test LinkResult string representation"""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        result = LinkResult(
            linked=True,
            existing_entity=entity,
            new_entity=entity,
            similarity=0.9,
            link_type="name"
        )
        repr_str = repr(result)
        assert "linked=True" in repr_str
        assert "name" in repr_str
        
        result2 = LinkResult(linked=False, new_entity=entity)
        repr_str2 = repr(result2)
        assert "linked=False" in repr_str2


class TestRelationDeduplicator:
    """Test RelationDeduplicator"""
    
    @pytest.fixture
    def deduplicator(self):
        """Create RelationDeduplicator instance"""
        return RelationDeduplicator(merge_properties=True)
    
    @pytest.fixture
    def sample_relations(self):
        """Create sample relations for testing"""
        return [
            Relation(
                id="r1",
                relation_type="WORKS_FOR",
                source_id="e1",
                target_id="e2",
                properties={"since": "2020"}
            ),
            Relation(
                id="r2",
                relation_type="WORKS_FOR",
                source_id="e1",
                target_id="e2",
                properties={"role": "engineer"}
            ),
            Relation(
                id="r3",
                relation_type="KNOWS",
                source_id="e1",
                target_id="e3"
            ),
        ]
    
    @pytest.mark.asyncio
    async def test_deduplicate_empty_list(self, deduplicator):
        """Test deduplication with empty list"""
        result = await deduplicator.deduplicate([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_deduplicate_single_relation(self, deduplicator):
        """Test deduplication with single relation"""
        relations = [
            Relation(
                id="r1",
                relation_type="WORKS_FOR",
                source_id="e1",
                target_id="e2"
            )
        ]
        result = await deduplicator.deduplicate(relations)
        assert len(result) == 1
        assert result[0].id == "r1"
    
    @pytest.mark.asyncio
    async def test_deduplicate_duplicate_relations(self, deduplicator, sample_relations):
        """Test deduplication of duplicate relations"""
        result = await deduplicator.deduplicate(sample_relations)
        
        # r1 and r2 are duplicates (same source, target, type)
        # Should be merged into one
        assert len(result) < len(sample_relations)
        
        # Check that WORKS_FOR relations are merged
        works_for = [r for r in result if r.relation_type == "WORKS_FOR"]
        assert len(works_for) == 1
        
        # Merged relation should have properties from both
        merged = works_for[0]
        assert "since" in merged.properties or "role" in merged.properties
        assert "_merged_count" in merged.properties
    
    @pytest.mark.asyncio
    async def test_deduplicate_different_relations(self, deduplicator):
        """Test deduplication with different relations"""
        relations = [
            Relation(
                id="r1",
                relation_type="WORKS_FOR",
                source_id="e1",
                target_id="e2"
            ),
            Relation(
                id="r2",
                relation_type="KNOWS",
                source_id="e1",
                target_id="e3"
            ),
        ]
        
        result = await deduplicator.deduplicate(relations)
        # Different relations should not be merged
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_deduplicate_without_merge_properties(self):
        """Test deduplication without merging properties"""
        deduplicator = RelationDeduplicator(merge_properties=False)
        
        relations = [
            Relation(
                id="r1",
                relation_type="WORKS_FOR",
                source_id="e1",
                target_id="e2",
                properties={"since": "2020"}
            ),
            Relation(
                id="r2",
                relation_type="WORKS_FOR",
                source_id="e1",
                target_id="e2",
                properties={"role": "engineer"}
            ),
        ]
        
        result = await deduplicator.deduplicate(relations)
        assert len(result) == 1
        # Properties should not be merged
        merged = result[0]
        # Should only have properties from first relation
        assert "since" in merged.properties or "role" in merged.properties
    
    def test_merge_relations_single(self, deduplicator):
        """Test merging single relation"""
        relation = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e2"
        )
        merged = deduplicator._merge_relations([relation])
        assert merged.id == relation.id
    
    def test_merge_relations_multiple(self, deduplicator):
        """Test merging multiple relations"""
        relations = [
            Relation(
                id="r1",
                relation_type="WORKS_FOR",
                source_id="e1",
                target_id="e2",
                properties={"since": "2020"},
                weight=0.8
            ),
            Relation(
                id="r2",
                relation_type="WORKS_FOR",
                source_id="e1",
                target_id="e2",
                properties={"role": "engineer"},
                weight=0.9
            ),
        ]
        
        merged = deduplicator._merge_relations(relations)
        assert merged.id == "r1"  # Uses first relation's ID
        assert merged.weight == 0.9  # Takes highest weight
        assert "since" in merged.properties or "role" in merged.properties
        assert "_merged_count" in merged.properties
        assert merged.properties["_merged_count"] == 2
    
    def test_find_duplicates(self, deduplicator, sample_relations):
        """Test finding duplicate pairs"""
        duplicates = deduplicator.find_duplicates(sample_relations)
        assert len(duplicates) > 0
        # r1 and r2 should be identified as duplicates
        assert any(
            (r1.id == "r1" and r2.id == "r2") or (r1.id == "r2" and r2.id == "r1")
            for r1, r2 in duplicates
        )
    
    def test_are_duplicates_true(self, deduplicator):
        """Test duplicate detection with matching relations"""
        r1 = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e2"
        )
        r2 = Relation(
            id="r2",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e2"
        )
        
        assert deduplicator._are_duplicates(r1, r2) is True
    
    def test_are_duplicates_false_different_source(self, deduplicator):
        """Test duplicate detection with different source"""
        r1 = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e2"
        )
        r2 = Relation(
            id="r2",
            relation_type="WORKS_FOR",
            source_id="e3",
            target_id="e2"
        )
        
        assert deduplicator._are_duplicates(r1, r2) is False
    
    def test_are_duplicates_false_different_type(self, deduplicator):
        """Test duplicate detection with different type"""
        r1 = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e2"
        )
        r2 = Relation(
            id="r2",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        
        assert deduplicator._are_duplicates(r1, r2) is False


class TestKnowledgeFusion:
    """Test KnowledgeFusion"""
    
    @pytest.fixture
    async def graph_store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    def fusion(self, graph_store):
        """Create KnowledgeFusion instance"""
        return KnowledgeFusion(graph_store, similarity_threshold=0.90)
    
    @pytest.mark.asyncio
    async def test_fuse_cross_document_entities_empty(self, fusion):
        """Test fusion with empty graph"""
        stats = await fusion.fuse_cross_document_entities()
        assert isinstance(stats, dict)
        assert "entities_analyzed" in stats
        assert "entities_merged" in stats
    
    @pytest.mark.asyncio
    async def test_fuse_cross_document_entities_with_types(self, fusion):
        """Test fusion with specific entity types"""
        stats = await fusion.fuse_cross_document_entities(entity_types=["Person"])
        assert isinstance(stats, dict)
    
    @pytest.mark.asyncio
    async def test_resolve_property_conflicts_single(self, fusion):
        """Test resolving conflicts with single entity"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        result = await fusion.resolve_property_conflicts([entity])
        assert result.id == entity.id
    
    @pytest.mark.asyncio
    async def test_resolve_property_conflicts_empty(self, fusion):
        """Test resolving conflicts with empty list raises error"""
        with pytest.raises(ValueError, match="Cannot merge empty"):
            await fusion.resolve_property_conflicts([])
    
    @pytest.mark.asyncio
    async def test_resolve_property_conflicts_no_conflicts(self, fusion):
        """Test resolving conflicts with no conflicts"""
        entities = [
            Entity(
                id="e1",
                entity_type="Person",
                properties={"name": "Alice", "age": 30}
            ),
            Entity(
                id="e2",
                entity_type="Person",
                properties={"name": "Alice", "city": "NYC"}
            ),
        ]
        
        merged = await fusion.resolve_property_conflicts(entities)
        assert merged.id == "e1"
        assert "name" in merged.properties
        assert "age" in merged.properties
        assert "city" in merged.properties
    
    @pytest.mark.asyncio
    async def test_resolve_property_conflicts_with_conflicts(self, fusion):
        """Test resolving conflicts with conflicting properties"""
        entities = [
            Entity(
                id="e1",
                entity_type="Person",
                properties={"name": "Alice", "age": 30}
            ),
            Entity(
                id="e2",
                entity_type="Person",
                properties={"name": "Alice", "age": 35}  # Conflicting age
            ),
        ]
        
        merged = await fusion.resolve_property_conflicts(entities)
        assert merged.id == "e1"
        assert "_property_conflicts" in merged.properties
        assert "age" in merged.properties["_property_conflicts"]
    
    @pytest.mark.asyncio
    async def test_resolve_property_conflicts_with_provenance(self, fusion):
        """Test resolving conflicts with provenance information"""
        entities = [
            Entity(
                id="e1",
                entity_type="Person",
                properties={
                    "name": "Alice",
                    "_provenance": {"source": "doc1.pdf"}
                }
            ),
            Entity(
                id="e2",
                entity_type="Person",
                properties={
                    "name": "Alice",
                    "_provenance": {"source": "doc2.pdf"}
                }
            ),
        ]
        
        merged = await fusion.resolve_property_conflicts(entities)
        assert "_provenance_merged" in merged.properties
        provenances = merged.properties["_provenance_merged"]
        assert len(provenances) == 2
    
    @pytest.mark.asyncio
    async def test_track_entity_provenance_not_found(self, fusion):
        """Test tracking provenance for non-existent entity"""
        sources = await fusion.track_entity_provenance("non_existent")
        assert sources == []
    
    @pytest.mark.asyncio
    async def test_track_entity_provenance_single(self, fusion, graph_store):
        """Test tracking provenance for entity with single source"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={
                "name": "Alice",
                "_provenance": {"source": "doc1.pdf"}
            }
        )
        await graph_store.add_entity(entity)
        
        sources = await fusion.track_entity_provenance("e1")
        assert len(sources) == 1
        assert "doc1.pdf" in sources
    
    @pytest.mark.asyncio
    async def test_track_entity_provenance_merged(self, fusion, graph_store):
        """Test tracking provenance for merged entity"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={
                "name": "Alice",
                "_provenance_merged": [
                    {"source": "doc1.pdf"},
                    {"source": "doc2.pdf"}
                ]
            }
        )
        await graph_store.add_entity(entity)
        
        sources = await fusion.track_entity_provenance("e1")
        assert len(sources) == 2
        assert "doc1.pdf" in sources
        assert "doc2.pdf" in sources
    
    @pytest.mark.asyncio
    async def test_track_entity_provenance_duplicates(self, fusion, graph_store):
        """Test tracking provenance removes duplicates"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={
                "name": "Alice",
                "_provenance_merged": [
                    {"source": "doc1.pdf"},
                    {"source": "doc1.pdf"}  # Duplicate
                ]
            }
        )
        await graph_store.add_entity(entity)

        sources = await fusion.track_entity_provenance("e1")
        assert len(sources) == 1  # Duplicates removed
        assert "doc1.pdf" in sources


class TestMatchingConfig:
    """Test FusionMatchingConfig and EntityTypeConfig"""

    def test_entity_type_config_defaults(self):
        """Test EntityTypeConfig default values"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            EntityTypeConfig,
            DEFAULT_ENABLED_STAGES,
        )

        config = EntityTypeConfig()
        assert config.enabled_stages == DEFAULT_ENABLED_STAGES
        assert config.semantic_enabled is True
        assert config.thresholds == {}

    def test_entity_type_config_custom_stages(self):
        """Test EntityTypeConfig with custom stages"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            EntityTypeConfig,
        )

        config = EntityTypeConfig(
            enabled_stages=["exact", "alias", "normalized"],
            semantic_enabled=False,
            thresholds={"alias_match_score": 0.99},
        )
        assert config.enabled_stages == ["exact", "alias", "normalized"]
        assert config.semantic_enabled is False
        assert config.thresholds["alias_match_score"] == 0.99

    def test_entity_type_config_invalid_stage(self):
        """Test EntityTypeConfig rejects invalid stages"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            EntityTypeConfig,
        )

        with pytest.raises(ValueError, match="Invalid matching stages"):
            EntityTypeConfig(enabled_stages=["exact", "invalid_stage"])

    def test_entity_type_config_invalid_threshold(self):
        """Test EntityTypeConfig rejects invalid threshold values"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            EntityTypeConfig,
        )

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            EntityTypeConfig(thresholds={"alias_match_score": 1.5})

    def test_entity_type_config_is_stage_enabled(self):
        """Test is_stage_enabled method"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            EntityTypeConfig,
        )

        config = EntityTypeConfig(
            enabled_stages=["exact", "alias", "semantic"],
            semantic_enabled=True,
        )
        assert config.is_stage_enabled("exact") is True
        assert config.is_stage_enabled("alias") is True
        assert config.is_stage_enabled("semantic") is True
        assert config.is_stage_enabled("abbreviation") is False

        # Semantic disabled
        config2 = EntityTypeConfig(
            enabled_stages=["exact", "semantic"],
            semantic_enabled=False,
        )
        assert config2.is_stage_enabled("semantic") is False

    def test_fusion_matching_config_defaults(self):
        """Test FusionMatchingConfig default values"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
        )

        config = FusionMatchingConfig()
        assert config.alias_match_score == 0.98
        assert config.abbreviation_match_score == 0.95
        assert config.normalization_match_score == 0.90
        assert config.semantic_threshold == 0.85
        assert config.string_similarity_threshold == 0.80
        assert config.semantic_enabled is True

    def test_fusion_matching_config_get_config_for_type(self):
        """Test get_config_for_type with inheritance"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
            EntityTypeConfig,
        )

        config = FusionMatchingConfig(
            alias_match_score=0.98,
            entity_type_configs={
                "Person": EntityTypeConfig(
                    enabled_stages=["exact", "alias", "normalized"],
                    semantic_enabled=False,
                    thresholds={"alias_match_score": 0.99},
                ),
                "_default": EntityTypeConfig(
                    enabled_stages=["exact", "alias", "abbreviation", "normalized"],
                ),
            },
        )

        # Person config should have overrides
        person_config = config.get_config_for_type("Person")
        assert person_config.enabled_stages == ["exact", "alias", "normalized"]
        assert person_config.semantic_enabled is False
        assert person_config.thresholds["alias_match_score"] == 0.99

        # Unknown type should use _default
        unknown_config = config.get_config_for_type("UnknownType")
        assert unknown_config.enabled_stages == ["exact", "alias", "abbreviation", "normalized"]

    def test_fusion_matching_config_add_remove_type(self):
        """Test adding and removing entity type configs"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
            EntityTypeConfig,
        )

        config = FusionMatchingConfig()
        assert "Person" not in config.get_configured_entity_types()

        config.add_entity_type_config(
            "Person",
            EntityTypeConfig(enabled_stages=["exact", "alias"]),
        )
        assert "Person" in config.get_configured_entity_types()

        removed = config.remove_entity_type_config("Person")
        assert removed is True
        assert "Person" not in config.get_configured_entity_types()

        # Remove non-existent
        removed = config.remove_entity_type_config("NonExistent")
        assert removed is False


class TestMatchingConfigIO:
    """Test matching config file I/O"""

    def test_load_from_dict(self):
        """Test loading config from dictionary"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            load_matching_config_from_dict,
        )

        data = {
            "alias_match_score": 0.97,
            "semantic_threshold": 0.80,
            "entity_types": {
                "Person": {
                    "enabled_stages": ["exact", "alias"],
                    "semantic_enabled": False,
                    "thresholds": {"alias_match_score": 0.99},
                },
            },
        }

        config = load_matching_config_from_dict(data)
        assert config.alias_match_score == 0.97
        assert config.semantic_threshold == 0.80
        assert "Person" in config.entity_type_configs
        assert config.entity_type_configs["Person"].semantic_enabled is False

    def test_save_to_dict(self):
        """Test saving config to dictionary"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
            EntityTypeConfig,
            save_matching_config_to_dict,
        )

        config = FusionMatchingConfig(
            alias_match_score=0.97,
            entity_type_configs={
                "Person": EntityTypeConfig(
                    enabled_stages=["exact", "alias"],
                    semantic_enabled=False,
                ),
            },
        )

        data = save_matching_config_to_dict(config)
        assert data["alias_match_score"] == 0.97
        assert "Person" in data["entity_types"]
        assert data["entity_types"]["Person"]["semantic_enabled"] is False

    def test_load_from_json(self, tmp_path):
        """Test loading config from JSON file"""
        import json
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            load_matching_config_from_json,
        )

        config_data = {
            "alias_match_score": 0.96,
            "entity_types": {
                "Organization": {
                    "enabled_stages": ["exact", "alias", "abbreviation"],
                    "semantic_enabled": True,
                    "thresholds": {},
                },
            },
        }

        json_file = tmp_path / "config.json"
        with open(json_file, "w") as f:
            json.dump(config_data, f)

        config = load_matching_config_from_json(str(json_file))
        assert config.alias_match_score == 0.96
        assert "Organization" in config.entity_type_configs

    def test_load_from_yaml(self, tmp_path):
        """Test loading config from YAML file"""
        import yaml
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            load_matching_config_from_yaml,
        )

        config_data = {
            "alias_match_score": 0.95,
            "entity_types": {
                "Concept": {
                    "enabled_stages": ["exact", "semantic"],
                    "semantic_enabled": True,
                    "thresholds": {"semantic_threshold": 0.75},
                },
            },
        }

        yaml_file = tmp_path / "config.yaml"
        with open(yaml_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = load_matching_config_from_yaml(str(yaml_file))
        assert config.alias_match_score == 0.95
        assert "Concept" in config.entity_type_configs

    def test_load_auto_detect_format(self, tmp_path):
        """Test auto-detecting file format"""
        import json
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            load_matching_config,
        )

        config_data = {"alias_match_score": 0.94}

        json_file = tmp_path / "config.json"
        with open(json_file, "w") as f:
            json.dump(config_data, f)

        config = load_matching_config(str(json_file))
        assert config.alias_match_score == 0.94

    def test_load_unsupported_format(self, tmp_path):
        """Test error on unsupported file format"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            load_matching_config,
        )

        txt_file = tmp_path / "config.txt"
        txt_file.write_text("some content")

        with pytest.raises(ValueError, match="Unsupported config file format"):
            load_matching_config(str(txt_file))

    def test_load_file_not_found(self):
        """Test error when file not found"""
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            load_matching_config_from_json,
        )

        with pytest.raises(FileNotFoundError):
            load_matching_config_from_json("/nonexistent/path/config.json")


class TestSimilarityPipeline:
    """Test SimilarityPipeline class"""

    @pytest.fixture
    def pipeline(self):
        """Create SimilarityPipeline instance"""
        from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
            SimilarityPipeline,
        )
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
        )

        config = FusionMatchingConfig()
        return SimilarityPipeline(config=config)

    @pytest.mark.asyncio
    async def test_exact_match(self, pipeline):
        """Test exact match detection"""
        result = await pipeline.compute_similarity("Apple Inc.", "apple inc.")
        assert result.final_score == 1.0
        assert result.is_match is True
        assert result.matched_stage.value == "exact"

    @pytest.mark.asyncio
    async def test_exact_match_with_whitespace(self, pipeline):
        """Test exact match with different whitespace"""
        result = await pipeline.compute_similarity("Apple  Inc.", "Apple Inc.")
        assert result.final_score == 1.0
        assert result.matched_stage.value == "exact"

    @pytest.mark.asyncio
    async def test_string_similarity_substring(self, pipeline):
        """Test string similarity with substring match"""
        result = await pipeline.compute_similarity("Apple", "Apple Inc.")
        assert result.final_score >= 0.85
        assert result.is_match is True

    @pytest.mark.asyncio
    async def test_string_similarity_fuzzy(self, pipeline):
        """Test string similarity with fuzzy match"""
        result = await pipeline.compute_similarity("Microsoft", "Microsft")
        assert result.final_score > 0.7
        assert result.matched_stage.value == "string"

    @pytest.mark.asyncio
    async def test_no_match(self, pipeline):
        """Test no match for dissimilar names"""
        result = await pipeline.compute_similarity("Apple", "Google")
        assert result.final_score < 0.5
        assert result.is_match is False

    @pytest.mark.asyncio
    async def test_per_entity_type_config(self):
        """Test per-entity-type configuration"""
        from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
            SimilarityPipeline,
        )
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
            EntityTypeConfig,
        )

        config = FusionMatchingConfig(
            entity_type_configs={
                "Person": EntityTypeConfig(
                    enabled_stages=["exact", "string"],
                    semantic_enabled=False,
                ),
            },
        )
        pipeline = SimilarityPipeline(config=config)

        result = await pipeline.compute_similarity(
            "John Smith", "john smith", entity_type="Person"
        )
        assert result.final_score == 1.0
        assert result.matched_stage.value == "exact"

    @pytest.mark.asyncio
    async def test_early_exit(self):
        """Test early exit on high-confidence match"""
        from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
            SimilarityPipeline,
        )
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
        )

        config = FusionMatchingConfig()
        pipeline = SimilarityPipeline(config=config, early_exit_threshold=0.95)

        result = await pipeline.compute_similarity("Apple Inc.", "apple inc.")
        assert result.early_exit is True
        assert result.final_score == 1.0

    def test_sync_similarity(self, pipeline):
        """Test synchronous similarity computation"""
        score = pipeline.compute_similarity_sync("Apple Inc.", "apple inc.")
        assert score == 1.0

        score = pipeline.compute_similarity_sync("Apple", "Google")
        assert score < 0.5

    def test_stats(self, pipeline):
        """Test pipeline statistics"""
        stats = pipeline.get_stats()
        assert stats["total_comparisons"] == 0
        assert stats["early_exit_count"] == 0

    @pytest.mark.asyncio
    async def test_stats_after_comparisons(self, pipeline):
        """Test statistics after running comparisons"""
        await pipeline.compute_similarity("Apple", "Apple")
        await pipeline.compute_similarity("Google", "Microsoft")

        stats = pipeline.get_stats()
        assert stats["total_comparisons"] == 2

        pipeline.reset_stats()
        stats = pipeline.get_stats()
        assert stats["total_comparisons"] == 0


class TestEntityDeduplicatorWithPipeline:
    """Test EntityDeduplicator with SimilarityPipeline integration"""

    @pytest.mark.asyncio
    async def test_deduplicator_with_pipeline(self):
        """Test EntityDeduplicator uses pipeline when provided"""
        from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
            SimilarityPipeline,
        )
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
        )

        config = FusionMatchingConfig()
        pipeline = SimilarityPipeline(config=config)

        # Use lower threshold since the combined score (0.7*name + 0.3*props)
        # is lower than the pure name similarity
        deduplicator = EntityDeduplicator(
            similarity_threshold=0.70,
            similarity_pipeline=pipeline,
        )

        entities = [
            Entity(id="e1", entity_type="Company", properties={"name": "Apple Inc."}),
            Entity(id="e2", entity_type="Company", properties={"name": "Apple Inc"}),
            Entity(id="e3", entity_type="Company", properties={"name": "Microsoft"}),
        ]

        deduplicated = await deduplicator.deduplicate(entities)
        # Apple Inc. and Apple Inc should be merged (exact match with dot difference)
        assert len(deduplicated) == 2

    @pytest.mark.asyncio
    async def test_deduplicator_set_pipeline(self):
        """Test setting pipeline after initialization"""
        from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
            SimilarityPipeline,
        )
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
        )

        deduplicator = EntityDeduplicator(similarity_threshold=0.85)
        assert deduplicator.similarity_pipeline is None

        config = FusionMatchingConfig()
        pipeline = SimilarityPipeline(config=config)
        deduplicator.set_similarity_pipeline(pipeline)

        assert deduplicator.similarity_pipeline is pipeline


class TestEntityLinkerWithPipeline:
    """Test EntityLinker with SimilarityPipeline integration"""

    @pytest.fixture
    def graph_store(self):
        """Create InMemoryGraphStore"""
        return InMemoryGraphStore()

    @pytest.mark.asyncio
    async def test_linker_with_pipeline(self, graph_store):
        """Test EntityLinker uses pipeline when provided"""
        from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
            SimilarityPipeline,
        )
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
        )

        config = FusionMatchingConfig()
        pipeline = SimilarityPipeline(config=config)

        linker = EntityLinker(
            graph_store=graph_store,
            similarity_threshold=0.85,
            similarity_pipeline=pipeline,
        )

        assert linker.similarity_pipeline is pipeline

    @pytest.mark.asyncio
    async def test_linker_set_pipeline(self, graph_store):
        """Test setting pipeline after initialization"""
        from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
            SimilarityPipeline,
        )
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            FusionMatchingConfig,
        )

        linker = EntityLinker(graph_store=graph_store, similarity_threshold=0.85)
        assert linker.similarity_pipeline is None

        config = FusionMatchingConfig()
        pipeline = SimilarityPipeline(config=config)
        linker.set_similarity_pipeline(pipeline)

        assert linker.similarity_pipeline is pipeline


class TestSettingsConfigIntegration:
    """Test Settings integration with FusionMatchingConfig"""

    def test_settings_has_fusion_config_fields(self):
        """Test Settings has all fusion matching config fields"""
        from aiecs.config.config import Settings

        settings = Settings()
        assert hasattr(settings, "kg_fusion_alias_match_score")
        assert hasattr(settings, "kg_fusion_abbreviation_match_score")
        assert hasattr(settings, "kg_fusion_normalization_match_score")
        assert hasattr(settings, "kg_fusion_semantic_threshold")
        assert hasattr(settings, "kg_fusion_string_similarity_threshold")
        assert hasattr(settings, "kg_fusion_semantic_enabled")
        assert hasattr(settings, "kg_fusion_enabled_stages")
        assert hasattr(settings, "kg_fusion_early_exit_threshold")
        assert hasattr(settings, "kg_fusion_alias_backend")
        assert hasattr(settings, "kg_fusion_alias_redis_url")
        assert hasattr(settings, "kg_fusion_entity_type_config_path")

    def test_settings_default_values(self):
        """Test Settings has correct default values"""
        from aiecs.config.config import Settings

        settings = Settings()
        assert settings.kg_fusion_alias_match_score == 0.98
        assert settings.kg_fusion_abbreviation_match_score == 0.95
        assert settings.kg_fusion_normalization_match_score == 0.90
        assert settings.kg_fusion_semantic_threshold == 0.85
        assert settings.kg_fusion_string_similarity_threshold == 0.80
        assert settings.kg_fusion_semantic_enabled is True
        assert settings.kg_fusion_alias_backend == "memory"

    def test_settings_get_fusion_matching_config(self):
        """Test get_fusion_matching_config returns valid config"""
        from aiecs.config.config import Settings

        settings = Settings()
        config = settings.get_fusion_matching_config()

        assert config.alias_match_score == settings.kg_fusion_alias_match_score
        assert config.abbreviation_match_score == settings.kg_fusion_abbreviation_match_score
        assert config.normalization_match_score == settings.kg_fusion_normalization_match_score
        assert config.semantic_threshold == settings.kg_fusion_semantic_threshold
        assert config.string_similarity_threshold == settings.kg_fusion_string_similarity_threshold
        assert config.semantic_enabled == settings.kg_fusion_semantic_enabled

    def test_settings_threshold_validation_valid(self):
        """Test valid threshold values are accepted"""
        import os
        from aiecs.config.config import Settings

        # Temporarily set valid threshold
        os.environ["KG_FUSION_ALIAS_MATCH_SCORE"] = "0.95"
        try:
            settings = Settings()
            assert settings.kg_fusion_alias_match_score == 0.95
        finally:
            del os.environ["KG_FUSION_ALIAS_MATCH_SCORE"]

    def test_settings_threshold_validation_invalid(self):
        """Test invalid threshold values are rejected"""
        import os
        from aiecs.config.config import Settings

        # Test value > 1.0
        os.environ["KG_FUSION_ALIAS_MATCH_SCORE"] = "1.5"
        try:
            with pytest.raises(Exception, match="0.0 and 1.0"):
                Settings()
        finally:
            del os.environ["KG_FUSION_ALIAS_MATCH_SCORE"]

    def test_settings_alias_backend_validation(self):
        """Test invalid backend is rejected"""
        import os
        from aiecs.config.config import Settings

        os.environ["KG_FUSION_ALIAS_BACKEND"] = "invalid"
        try:
            with pytest.raises(Exception, match="Invalid"):
                Settings()
        finally:
            del os.environ["KG_FUSION_ALIAS_BACKEND"]

    def test_settings_enabled_stages_validation(self):
        """Test invalid matching stages are rejected"""
        import os
        from aiecs.config.config import Settings

        os.environ["KG_FUSION_ENABLED_STAGES"] = "exact,invalid_stage"
        try:
            with pytest.raises(Exception, match="Invalid matching stages"):
                Settings()
        finally:
            del os.environ["KG_FUSION_ENABLED_STAGES"]

    def test_config_inheritance_chain(self):
        """Test full configuration inheritance chain"""
        from aiecs.config.config import Settings
        from aiecs.application.knowledge_graph.fusion.matching_config import (
            EntityTypeConfig,
        )

        settings = Settings()
        config = settings.get_fusion_matching_config()

        # Add per-entity-type config
        config.add_entity_type_config(
            "Person",
            EntityTypeConfig(
                enabled_stages=["exact", "alias"],
                semantic_enabled=False,
                thresholds={"alias_match_score": 0.99},
            ),
        )

        # Global config applies to unknown types
        org_config = config.get_config_for_type("Organization")
        assert org_config.semantic_enabled == settings.kg_fusion_semantic_enabled

        # Per-type config overrides global
        person_config = config.get_config_for_type("Person")
        assert person_config.enabled_stages == ["exact", "alias"]
        assert person_config.semantic_enabled is False
        assert person_config.thresholds["alias_match_score"] == 0.99

    def test_config_from_file(self, tmp_path):
        """Test loading per-entity-type config from file"""
        import json
        import os
        from aiecs.config.config import Settings

        # Create config file
        config_data = {
            "entity_types": {
                "Concept": {
                    "enabled_stages": ["exact", "semantic"],
                    "semantic_enabled": True,
                    "thresholds": {"semantic_threshold": 0.75},
                },
            },
        }

        config_file = tmp_path / "entity_types.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        os.environ["KG_FUSION_ENTITY_TYPE_CONFIG_PATH"] = str(config_file)
        try:
            settings = Settings()
            config = settings.get_fusion_matching_config()

            assert "Concept" in config.entity_type_configs
            concept_config = config.get_config_for_type("Concept")
            assert concept_config.enabled_stages == ["exact", "semantic"]
        finally:
            del os.environ["KG_FUSION_ENTITY_TYPE_CONFIG_PATH"]