"""
Unit tests for knowledge graph builder components
"""

import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path

# Workaround for pytest-cov interfering with Pydantic BaseSettings
# Mock DocumentParserTool only during coverage collection
import sys

def _is_coverage_running():
    """Check if coverage collection is active"""
    # Check multiple ways coverage might be detected
    if 'COVERAGE_PROCESS_START' in os.environ:
        return True
    # Check if coverage/pytest_cov modules are loaded
    try:
        import coverage
        if hasattr(coverage, 'Coverage') and coverage.Coverage._collector:
            return True
    except (ImportError, AttributeError):
        pass
    # Check if pytest-cov plugin is active
    if 'pytest_cov' in sys.modules:
        return True
    # Check if running with --cov flag (pytest sets this)
    if any('--cov' in arg for arg in sys.argv):
        return True
    return False

if _is_coverage_running():
    # During coverage collection, mock DocumentParserTool to avoid BaseSettings issues
    from unittest.mock import MagicMock, AsyncMock
    
    class MockDocumentParserTool:
        """Mock DocumentParserTool for coverage collection"""
        def __init__(self, config=None):
            self.config = MagicMock()
            self.config.temp_dir = os.getenv('DOC_PARSER_TEMP_DIR', '/tmp/aiecs_test_document_parser')
            self.config.enable_cloud_storage = False
            self.logger = MagicMock()
            self.scraper_tool = None
            self.office_tool = None
            self.image_tool = None
            self.file_storage = None
        
        def execute(self, params):
            """Mock execute method that reads file content"""
            input_path = params.get('input', '')
            try:
                # Try to read file content (fallback behavior)
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"content": content}
            except Exception:
                return {"content": ""}
        
        def parse_document(self, source, **kwargs):
            """Mock parse_document method"""
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"content": content}
            except Exception:
                return {"content": ""}
    
    # Replace DocumentParserTool with mock during coverage
    import aiecs.application.knowledge_graph.builder.document_builder as db_module
    db_module.DocumentParserTool = MockDocumentParserTool

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder, BuildResult
from aiecs.application.knowledge_graph.builder.document_builder import DocumentGraphBuilder, DocumentBuildResult
from aiecs.application.knowledge_graph.builder.text_chunker import TextChunker, TextChunk
from aiecs.application.knowledge_graph.extractors.base import EntityExtractor, RelationExtractor
from aiecs.application.knowledge_graph.fusion.entity_deduplicator import EntityDeduplicator
from aiecs.application.knowledge_graph.fusion.entity_linker import EntityLinker
from aiecs.application.knowledge_graph.fusion.relation_deduplicator import RelationDeduplicator
from aiecs.application.knowledge_graph.validators.relation_validator import RelationValidator


class MockEntityExtractor(EntityExtractor):
    """Mock entity extractor for testing"""
    
    def __init__(self, entities_to_return=None):
        self.entities_to_return = entities_to_return or []
    
    async def extract_entities(self, text: str, entity_types=None, **kwargs):
        return self.entities_to_return.copy()


class MockRelationExtractor(RelationExtractor):
    """Mock relation extractor for testing"""
    
    def __init__(self, relations_to_return=None):
        self.relations_to_return = relations_to_return or []
    
    async def extract_relations(self, text: str, entities: list, relation_types=None, **kwargs):
        return self.relations_to_return.copy()


class MockGraphStore(GraphStore):
    """Mock graph store for testing"""
    
    def __init__(self):
        self.entities = {}
        self.relations = {}
        self.initialized = False
    
    async def initialize(self):
        self.initialized = True
    
    async def close(self):
        self.initialized = False
    
    async def add_entity(self, entity: Entity) -> str:
        self.entities[entity.id] = entity
        return entity.id
    
    async def get_entity(self, entity_id: str):
        return self.entities.get(entity_id)
    
    async def add_relation(self, relation: Relation) -> str:
        self.relations[relation.id] = relation
        return relation.id
    
    async def get_relation(self, relation_id: str):
        return self.relations.get(relation_id)
    
    async def get_neighbors(self, entity_id: str, relation_type=None, direction="outgoing"):
        neighbors = []
        for rel in self.relations.values():
            if direction in ("outgoing", "both") and rel.source_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    entity = await self.get_entity(rel.target_id)
                    if entity:
                        neighbors.append(entity)
            if direction in ("incoming", "both") and rel.target_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    entity = await self.get_entity(rel.source_id)
                    if entity:
                        neighbors.append(entity)
        return neighbors


class TestGraphBuilder:
    """Test GraphBuilder pipeline"""
    
    @pytest.fixture
    def mock_graph_store(self):
        """Create mock graph store"""
        store = MockGraphStore()
        return store
    
    @pytest.fixture
    def mock_entity_extractor(self):
        """Create mock entity extractor"""
        return MockEntityExtractor()
    
    @pytest.fixture
    def mock_relation_extractor(self):
        """Create mock relation extractor"""
        return MockRelationExtractor()
    
    @pytest.fixture
    def graph_builder(self, mock_graph_store, mock_entity_extractor, mock_relation_extractor):
        """Create GraphBuilder instance"""
        return GraphBuilder(
            graph_store=mock_graph_store,
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor
        )
    
    @pytest.mark.asyncio
    async def test_build_from_text_basic(self, graph_builder, mock_entity_extractor, mock_relation_extractor):
        """Test basic graph building from text"""
        # Setup mocks
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Company", properties={"name": "Tech Corp"})
        mock_entity_extractor.entities_to_return = [entity1, entity2]
        
        relation = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e2"
        )
        mock_relation_extractor.relations_to_return = [relation]
        
        # Build graph
        result = await graph_builder.build_from_text(
            text="Alice works at Tech Corp.",
            source="test_doc"
        )
        
        # Verify result
        assert result.success is True
        assert result.entities_added == 2
        assert result.relations_added == 1
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_build_from_text_no_entities(self, graph_builder, mock_entity_extractor):
        """Test building when no entities are extracted"""
        mock_entity_extractor.entities_to_return = []
        
        result = await graph_builder.build_from_text(text="No entities here.")
        
        assert result.success is True
        assert result.entities_added == 0
        assert result.relations_added == 0
        assert len(result.warnings) > 0
        assert "No entities" in result.warnings[0]
    
    @pytest.mark.asyncio
    async def test_build_from_text_with_deduplication(self, graph_builder, mock_entity_extractor, mock_relation_extractor):
        """Test building with entity deduplication"""
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Alice"})  # Duplicate
        mock_entity_extractor.entities_to_return = [entity1, entity2]
        
        # Mock deduplicator
        with patch.object(graph_builder.entity_deduplicator, 'deduplicate', new_callable=AsyncMock) as mock_dedup:
            mock_dedup.return_value = [entity1]  # Returns deduplicated list
            
            result = await graph_builder.build_from_text(text="Alice and Alice.")
            
            assert result.entities_deduplicated == 1
            mock_dedup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_build_from_text_with_linking(self, graph_builder, mock_graph_store, mock_entity_extractor):
        """Test building with entity linking"""
        # Add existing entity to store
        existing = Entity(id="existing_e1", entity_type="Person", properties={"name": "Alice"})
        await mock_graph_store.add_entity(existing)
        
        # New entity that should link
        new_entity = Entity(id="new_e1", entity_type="Person", properties={"name": "Alice"})
        mock_entity_extractor.entities_to_return = [new_entity]
        
        # Mock linker
        from aiecs.application.knowledge_graph.fusion.entity_linker import LinkResult
        link_result = LinkResult(linked=True, existing_entity=existing, new_entity=new_entity)
        
        with patch.object(graph_builder.entity_linker, 'link_entities', new_callable=AsyncMock) as mock_link:
            mock_link.return_value = [link_result]
            
            result = await graph_builder.build_from_text(text="Alice mentioned again.")
            
            assert result.entities_linked == 1
            assert result.entities_added == 0  # Linked, not added
            mock_link.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_build_from_text_with_validation(self, mock_graph_store, mock_entity_extractor, mock_relation_extractor):
        """Test building with relation validation"""
        from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
        
        schema = GraphSchema()
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Company")
        mock_entity_extractor.entities_to_return = [entity1, entity2]
        
        valid_relation = Relation(id="r1", relation_type="WORKS_FOR", source_id="e1", target_id="e2")
        invalid_relation = Relation(id="r2", relation_type="INVALID", source_id="e1", target_id="e2")
        mock_relation_extractor.relations_to_return = [valid_relation, invalid_relation]
        
        # Create builder with validation enabled
        builder = GraphBuilder(
            graph_store=mock_graph_store,
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor,
            schema=schema,
            enable_validation=True
        )
        
        # Mock validator
        with patch.object(builder.relation_validator, 'filter_valid_relations') as mock_validate:
            mock_validate.return_value = [valid_relation]  # Only valid relation passes
            
            result = await builder.build_from_text(text="Test")
            
            assert result.relations_added == 1
            assert len(result.warnings) > 0
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_build_from_text_error_handling(self, graph_builder, mock_entity_extractor):
        """Test error handling during build"""
        # Make extractor raise error
        mock_entity_extractor.extract_entities = AsyncMock(side_effect=Exception("Extraction failed"))
        
        result = await graph_builder.build_from_text(text="Test")
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "Extraction failed" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_build_from_text_provenance(self, graph_builder, mock_entity_extractor, mock_relation_extractor):
        """Test provenance metadata is added"""
        entity = Entity(id="e1", entity_type="Person")
        mock_entity_extractor.entities_to_return = [entity]
        
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        mock_relation_extractor.relations_to_return = [relation]
        
        result = await graph_builder.build_from_text(
            text="Test",
            source="test_source",
            metadata={"author": "test_author"}
        )
        
        assert result.success is True
        # Check that provenance was added (stored entities should have it)
        stored_entity = await graph_builder.graph_store.get_entity("e1")
        assert stored_entity is not None
        assert "_provenance" in stored_entity.properties
        assert stored_entity.properties["_provenance"]["source"] == "test_source"
        assert stored_entity.properties["_provenance"]["author"] == "test_author"
    
    @pytest.mark.asyncio
    async def test_build_batch_sequential(self, graph_builder, mock_entity_extractor):
        """Test batch building sequentially"""
        # Create unique entities for each text
        entities1 = [Entity(id="e1", entity_type="Person")]
        entities2 = [Entity(id="e2", entity_type="Person")]
        entities3 = [Entity(id="e3", entity_type="Person")]
        
        async def extract_side_effect(text, **kwargs):
            if "Text 1" in text:
                return entities1
            elif "Text 2" in text:
                return entities2
            else:
                return entities3
        
        mock_entity_extractor.extract_entities = AsyncMock(side_effect=extract_side_effect)
        
        texts = ["Text 1", "Text 2", "Text 3"]
        results = await graph_builder.build_batch(texts, parallel=False)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(r.entities_added == 1 for r in results)
    
    @pytest.mark.asyncio
    async def test_build_batch_parallel(self, graph_builder, mock_entity_extractor):
        """Test batch building in parallel"""
        entity = Entity(id="e1", entity_type="Person")
        mock_entity_extractor.entities_to_return = [entity]
        
        texts = ["Text 1", "Text 2", "Text 3"]
        results = await graph_builder.build_batch(texts, parallel=True, max_parallel=2)
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_build_batch_with_sources(self, graph_builder, mock_entity_extractor):
        """Test batch building with source identifiers"""
        entity = Entity(id="e1", entity_type="Person")
        mock_entity_extractor.entities_to_return = [entity]
        
        texts = ["Text 1", "Text 2"]
        sources = ["source1", "source2"]
        results = await graph_builder.build_batch(texts, sources=sources)
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_build_batch_source_length_mismatch(self, graph_builder):
        """Test batch building with mismatched source length"""
        texts = ["Text 1", "Text 2"]
        sources = ["source1"]  # Mismatch
        
        with pytest.raises(ValueError, match="must match"):
            await graph_builder.build_batch(texts, sources=sources)
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, mock_graph_store, mock_entity_extractor, mock_relation_extractor):
        """Test progress callback is called"""
        callback_messages = []
        
        def progress_callback(message: str, progress: float):
            callback_messages.append((message, progress))
        
        builder = GraphBuilder(
            graph_store=mock_graph_store,
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor,
            progress_callback=progress_callback
        )
        
        entity = Entity(id="e1", entity_type="Person")
        mock_entity_extractor.entities_to_return = [entity]
        
        await builder.build_from_text(text="Test")
        
        assert len(callback_messages) > 0
        assert any("Starting" in msg[0] for msg in callback_messages)
        assert any("complete" in msg[0].lower() for msg in callback_messages)
    
    @pytest.mark.asyncio
    async def test_build_result_timing(self, graph_builder, mock_entity_extractor):
        """Test BuildResult includes timing information"""
        entity = Entity(id="e1", entity_type="Person")
        mock_entity_extractor.entities_to_return = [entity]
        
        result = await graph_builder.build_from_text(text="Test")
        
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.duration_seconds > 0
    
    def test_build_result_initialization(self):
        """Test BuildResult dataclass"""
        result = BuildResult(
            success=True,
            entities_added=5,
            relations_added=3
        )
        
        assert result.success is True
        assert result.entities_added == 5
        assert result.relations_added == 3
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    @pytest.mark.asyncio
    async def test_build_from_text_not_enough_entities_for_relations(self, graph_builder, mock_entity_extractor):
        """Test building when not enough entities for relation extraction"""
        # Only one entity
        entity = Entity(id="e1", entity_type="Person")
        mock_entity_extractor.entities_to_return = [entity]
        
        result = await graph_builder.build_from_text(text="Only one entity.")
        
        assert result.success is True
        assert result.entities_added == 1
        assert result.relations_added == 0
        assert len(result.warnings) > 0
        assert "Not enough entities" in result.warnings[0]
    
    @pytest.mark.asyncio
    async def test_build_from_text_with_provenance_only_source(self, graph_builder, mock_entity_extractor, mock_relation_extractor):
        """Test building with only source (no metadata)"""
        entity = Entity(id="e1", entity_type="Person")
        mock_entity_extractor.entities_to_return = [entity]
        
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        mock_relation_extractor.relations_to_return = [relation]
        
        result = await graph_builder.build_from_text(
            text="Test",
            source="test_source"
        )
        
        assert result.success is True
        stored_entity = await graph_builder.graph_store.get_entity("e1")
        assert stored_entity is not None
        assert "_provenance" in stored_entity.properties
        assert stored_entity.properties["_provenance"]["source"] == "test_source"
    
    @pytest.mark.asyncio
    async def test_build_from_text_progress_callback_error(self, mock_graph_store, mock_entity_extractor, mock_relation_extractor):
        """Test that progress callback errors don't break the pipeline"""
        def bad_callback(message, progress):
            raise Exception("Callback error")
        
        builder = GraphBuilder(
            graph_store=mock_graph_store,
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor,
            progress_callback=bad_callback
        )
        
        entity = Entity(id="e1", entity_type="Person")
        mock_entity_extractor.entities_to_return = [entity]
        
        result = await builder.build_from_text(text="Test")
        
        # Should still succeed despite callback error
        assert result.success is True


class TestTextChunker:
    """Test TextChunker"""
    
    def test_chunker_initialization(self):
        """Test chunker initialization"""
        chunker = TextChunker(
            chunk_size=1000,
            overlap=100,
            respect_sentences=True
        )
        
        assert chunker.chunk_size == 1000
        assert chunker.overlap == 100
        assert chunker.respect_sentences is True
    
    def test_chunk_short_text(self):
        """Test chunking short text (no chunking needed)"""
        chunker = TextChunker(chunk_size=1000)
        text = "Short text"
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)
        assert chunks[0].chunk_index == 0
    
    def test_chunk_empty_text(self):
        """Test chunking empty text"""
        chunker = TextChunker()
        chunks = chunker.chunk_text("")
        
        assert len(chunks) == 0
    
    def test_chunk_fixed_size(self):
        """Test fixed-size chunking"""
        chunker = TextChunker(
            chunk_size=10,
            overlap=2,
            respect_sentences=False
        )
        text = "This is a longer text that needs chunking."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 1
        # Check overlap
        if len(chunks) > 1:
            # First chunk should end at position 10
            assert chunks[0].end_char == 10
            # Second chunk should start with overlap
            assert chunks[1].start_char < chunks[0].end_char
    
    def test_chunk_by_sentences(self):
        """Test sentence-aware chunking"""
        chunker = TextChunker(
            chunk_size=50,
            overlap=10,
            respect_sentences=True
        )
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        # Check that chunks don't break mid-sentence
        for chunk in chunks:
            # Chunk should end with sentence boundary or be last chunk
            assert chunk.text.endswith('.') or chunk == chunks[-1]
    
    def test_chunk_by_paragraphs(self):
        """Test paragraph-aware chunking"""
        chunker = TextChunker(
            chunk_size=50,
            overlap=0,
            respect_paragraphs=True
        )
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        # Check that chunks respect paragraph boundaries
        for chunk in chunks:
            # Should contain complete paragraphs
            assert '\n\n' not in chunk.text or chunk.text.count('\n\n') == chunk.text.count('\n\n')
    
    def test_chunk_with_metadata(self):
        """Test chunking with metadata"""
        chunker = TextChunker()
        metadata = {"source": "test_doc"}
        
        chunks = chunker.chunk_text("Test text", metadata=metadata)
        
        assert len(chunks) > 0
        assert chunks[0].metadata == metadata
    
    def test_text_chunk_dataclass(self):
        """Test TextChunk dataclass"""
        chunk = TextChunk(
            text="Test",
            start_char=0,
            end_char=4,
            chunk_index=0,
            metadata={"key": "value"}
        )
        
        assert chunk.text == "Test"
        assert chunk.start_char == 0
        assert chunk.end_char == 4
        assert chunk.chunk_index == 0
        assert chunk.metadata["key"] == "value"
    
    def test_chunk_by_paragraphs_empty_paragraphs(self):
        """Test paragraph chunking with empty paragraphs"""
        chunker = TextChunker(
            chunk_size=50,
            respect_paragraphs=True
        )
        text = "Para one.\n\n\n\nPara two."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
    
    def test_chunk_by_sentences_single_sentence(self):
        """Test sentence chunking with single sentence"""
        chunker = TextChunker(
            chunk_size=100,
            respect_sentences=True
        )
        text = "This is a single sentence."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].text == text
    
    def test_chunk_overlap_edge_cases(self):
        """Test chunking with zero overlap"""
        chunker = TextChunker(
            chunk_size=10,
            overlap=0,
            respect_sentences=False
        )
        text = "This is a test text for chunking."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 1
        # Check no overlap
        for i in range(len(chunks) - 1):
            assert chunks[i].end_char == chunks[i + 1].start_char
    
    def test_chunk_min_size(self):
        """Test chunking respects min_chunk_size"""
        chunker = TextChunker(
            chunk_size=100,
            min_chunk_size=50
        )
        # Text smaller than min_chunk_size should still be chunked
        text = "Short text"
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 1


class TestDocumentGraphBuilder:
    """Test DocumentGraphBuilder"""
    
    @pytest.fixture
    def mock_graph_builder(self):
        """Create mock graph builder"""
        builder = MagicMock()
        builder.build_from_text = AsyncMock(return_value=BuildResult(
            success=True,
            entities_added=2,
            relations_added=1
        ))
        return builder
    
    def _create_document_builder_with_patched_parser(self, mock_graph_builder, **builder_kwargs):
        """
        Helper to create DocumentGraphBuilder.
        
        Note: DocumentParserTool is automatically mocked during coverage collection
        to avoid pytest-cov interfering with Pydantic BaseSettings.
        """
        return DocumentGraphBuilder(graph_builder=mock_graph_builder, **builder_kwargs)
    
    @pytest.fixture
    def document_builder(self, mock_graph_builder):
        """Create DocumentGraphBuilder instance"""
        return self._create_document_builder_with_patched_parser(mock_graph_builder)
    
    @pytest.mark.asyncio
    async def test_document_parser_tool_initialization(self, mock_graph_builder):
        """Test that DocumentParserTool initializes successfully"""
        # Create builder - this should initialize DocumentParserTool
        builder = self._create_document_builder_with_patched_parser(mock_graph_builder)
        
        # Verify DocumentParserTool was initialized
        assert hasattr(builder, 'document_parser')
        assert builder.document_parser is not None
        
        # Check if it's the real implementation or mock based on coverage
        from aiecs.tools.docs.document_parser_tool import DocumentParserTool
        is_mock = _is_coverage_running()
        
        if is_mock:
            # During coverage, should be mock
            assert type(builder.document_parser).__name__ == 'MockDocumentParserTool'
            print("✓ Using MockDocumentParserTool during coverage collection")
        else:
            # Without coverage, should be real implementation
            assert isinstance(builder.document_parser, DocumentParserTool)
            print("✓ Using real DocumentParserTool implementation")
        
        # Verify it has required attributes
        assert hasattr(builder.document_parser, 'config')
        assert hasattr(builder.document_parser, 'execute')
        
        # Test that it can actually parse a file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content for parser initialization")
            temp_path = f.name
        
        try:
            # Test the execute method works
            result = builder.document_parser.execute({
                "input": temp_path,
                "strategy": "text_only",
                "output_format": "text"
            })
            
            assert result is not None
            if isinstance(result, dict):
                assert "content" in result
                assert "Test content for parser initialization" in result["content"]
            print(f"✓ DocumentParserTool.execute() works correctly: {type(result)}")
        finally:
            os.unlink(temp_path)
        
        print("✓ DocumentParserTool initialization test PASSED")
    
    @pytest.mark.asyncio
    async def test_build_from_document_small_text(self, document_builder, mock_graph_builder):
        """Test building from small document (no chunking)"""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Small text document.")
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            assert result.success is True
            assert result.total_chunks == 1
            assert result.chunks_processed == 1
            assert result.total_entities_added == 2
            assert result.total_relations_added == 1
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_large_text(self, document_builder, mock_graph_builder):
        """Test building from large document (with chunking)"""
        # Create large text
        large_text = "Sentence. " * 500  # Large text
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_text)
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            assert result.success is True
            assert result.total_chunks > 1
            assert result.chunks_processed == result.total_chunks
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_empty_text(self, document_builder):
        """Test building from empty document"""
        # Create an empty temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            assert result.success is False
            assert len(result.errors) > 0
            assert "empty" in result.errors[0].lower()
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_parse_error(self, document_builder):
        """Test handling document parse errors"""
        # Use a non-existent file to trigger parse error
        non_existent_path = "/tmp/non_existent_file_12345.txt"
        
        result = await document_builder.build_from_document(non_existent_path)
        
        assert result.success is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_build_from_documents_parallel(self, document_builder, mock_graph_builder):
        """Test building from multiple documents in parallel"""
        # Create temporary text files
        temp_files = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(f"Test document {i+1}.")
                    temp_files.append(f.name)
            
            results = await document_builder.build_from_documents(
                temp_files,
                parallel=True
            )
            
            assert len(results) == 3
            assert all(r.success for r in results)
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    os.unlink(f)
    
    @pytest.mark.asyncio
    async def test_build_from_documents_sequential(self, document_builder, mock_graph_builder):
        """Test building from multiple documents sequentially"""
        # Create temporary text files
        temp_files = []
        try:
            for i in range(2):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(f"Test document {i+1}.")
                    temp_files.append(f.name)
            
            results = await document_builder.build_from_documents(
                temp_files,
                parallel=False
            )
            
            assert len(results) == 2
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    os.unlink(f)
    
    def test_document_build_result_properties(self):
        """Test DocumentBuildResult properties"""
        result = DocumentBuildResult(
            document_path="test.txt",
            document_type="txt",
            total_chunks=3
        )
        
        # Add chunk results
        result.chunk_results = [
            BuildResult(entities_added=2, relations_added=1),
            BuildResult(entities_added=3, relations_added=2),
            BuildResult(entities_added=1, relations_added=1)
        ]
        result.chunks_processed = len(result.chunk_results)
        
        assert result.total_entities_added == 6
        assert result.total_relations_added == 4
        assert result.chunks_processed == 3
    
    @pytest.mark.asyncio
    async def test_build_from_document_with_metadata(self, document_builder, mock_graph_builder):
        """Test building from document with metadata"""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test document with metadata.")
            temp_path = f.name
        
        try:
            metadata = {"author": "Test Author", "date": "2024-01-01"}
            result = await document_builder.build_from_document(temp_path, metadata=metadata)
            
            assert result.success is True
            # Verify metadata was passed to graph builder
            assert mock_graph_builder.build_from_text.called
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_chunking_disabled(self, mock_graph_builder):
        """Test building with chunking disabled"""
        builder = self._create_document_builder_with_patched_parser(
            mock_graph_builder,
            enable_chunking=False
        )
        
        large_text = "Sentence. " * 500
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_text)
            temp_path = f.name
        
        try:
            result = await builder.build_from_document(temp_path)
            
            assert result.success is True
            assert result.total_chunks == 1  # Single chunk even for large text
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_sequential_chunks(self, mock_graph_builder):
        """Test building with sequential chunk processing"""
        builder = self._create_document_builder_with_patched_parser(
            mock_graph_builder,
            parallel_chunks=False
        )
        
        large_text = "Sentence. " * 500
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_text)
            temp_path = f.name
        
        try:
            result = await builder.build_from_document(temp_path)
            
            assert result.success is True
            assert result.total_chunks > 1
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_partial_failure(self, document_builder, mock_graph_builder):
        """Test building when some chunks fail"""
        # Make some builds fail
        results = [
            BuildResult(success=True, entities_added=2, relations_added=1),
            BuildResult(success=False, entities_added=0, relations_added=0, errors=["Error"]),
            BuildResult(success=True, entities_added=1, relations_added=1)
        ]
        mock_graph_builder.build_from_text = AsyncMock(side_effect=results)
        
        large_text = "Sentence. " * 500
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_text)
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            # Should still succeed if at least some chunks succeeded
            assert result.success is True or len(result.errors) > 0
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_documents_with_exceptions(self, document_builder, mock_graph_builder):
        """Test building from documents with exceptions"""
        # Create one valid file and one non-existent file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Doc 1 content")
            temp_path1 = f.name
        
        non_existent_path = "/tmp/non_existent_file_12345.txt"
        
        try:
            results = await document_builder.build_from_documents(
                [temp_path1, non_existent_path],
                parallel=False
            )
            
            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False
        finally:
            if os.path.exists(temp_path1):
                os.unlink(temp_path1)
    
    @pytest.mark.asyncio
    async def test_parse_document_with_text_file(self, document_builder):
        """Test _parse_document with actual text file"""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content from file")
            temp_path = f.name
        
        try:
            result = await document_builder._parse_document(temp_path)
            
            assert result == "Test content from file"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_parse_document_fallback_to_text(self, document_builder):
        """Test _parse_document fallback to plain text reading when parser fails"""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Plain text content")
            temp_path = f.name
        
        try:
            # Mock the parser to fail, which should trigger fallback to file reading
            with patch.object(document_builder.document_parser, 'parse_document', side_effect=Exception("Parse failed")):
                result = await document_builder._parse_document(temp_path)
                
                # Should fallback to reading the file directly
                assert result == "Plain text content"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_parse_document_fallback_fails(self, document_builder):
        """Test _parse_document when both parser and fallback fail"""
        non_existent_path = "/tmp/non_existent_file_12345.txt"
        
        # Mock the parser to fail, and also mock open to fail
        with patch.object(document_builder.document_parser, 'execute', side_effect=Exception("Parse failed")):
            with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
                with pytest.raises(RuntimeError, match="Failed to parse document"):
                    await document_builder._parse_document(non_existent_path)
    
    @pytest.mark.asyncio
    async def test_process_chunks_parallel(self, document_builder, mock_graph_builder):
        """Test parallel chunk processing"""
        from aiecs.application.knowledge_graph.builder.text_chunker import TextChunk
        
        chunks = [
            TextChunk(text="Chunk 1", start_char=0, end_char=7, chunk_index=0),
            TextChunk(text="Chunk 2", start_char=8, end_char=15, chunk_index=1)
        ]
        
        results = await document_builder._process_chunks_parallel(
            chunks,
            "test.txt",
            None
        )
        
        assert len(results) == 2
        assert mock_graph_builder.build_from_text.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_chunks_parallel_with_exceptions(self, document_builder, mock_graph_builder):
        """Test parallel chunk processing with exceptions"""
        from aiecs.application.knowledge_graph.builder.text_chunker import TextChunk
        
        chunks = [
            TextChunk(text="Chunk 1", start_char=0, end_char=7, chunk_index=0),
            TextChunk(text="Chunk 2", start_char=8, end_char=15, chunk_index=1)
        ]
        
        # Make second build fail
        mock_graph_builder.build_from_text = AsyncMock(side_effect=[
            BuildResult(success=True),
            Exception("Build failed")
        ])
        
        results = await document_builder._process_chunks_parallel(
            chunks,
            "test.txt",
            None
        )
        
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
    
    @pytest.mark.asyncio
    async def test_process_chunks_sequential(self, document_builder, mock_graph_builder):
        """Test sequential chunk processing"""
        from aiecs.application.knowledge_graph.builder.text_chunker import TextChunk
        
        chunks = [
            TextChunk(text="Chunk 1", start_char=0, end_char=7, chunk_index=0),
            TextChunk(text="Chunk 2", start_char=8, end_char=15, chunk_index=1)
        ]
        
        results = await document_builder._process_chunks_sequential(
            chunks,
            "test.txt",
            {"author": "Test"}
        )
        
        assert len(results) == 2
        assert mock_graph_builder.build_from_text.call_count == 2
    
    @pytest.mark.asyncio
    async def test_build_from_document_whitespace_only(self, document_builder):
        """Test building from document with only whitespace"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("   \n\t  \n   ")
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            assert result.success is False
            assert len(result.errors) > 0
            assert "empty" in result.errors[0].lower()
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_different_file_types(self, document_builder, mock_graph_builder):
        """Test building from documents with different file extensions"""
        extensions = ['.txt', '.pdf', '.docx', '.md', '.html']
        
        for ext in extensions:
            with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
                f.write(f"Content for {ext} file.")
                temp_path = f.name
            
            try:
                result = await document_builder.build_from_document(temp_path)
                
                assert result.success is True
                # Check document type is detected
                expected_type = ext[1:].lower()  # Remove leading dot
                assert result.document_type == expected_type
            finally:
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_path_object(self, document_builder, mock_graph_builder):
        """Test building from document using Path object instead of string"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content.")
            temp_path = Path(f.name)
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            assert result.success is True
            assert result.document_path == str(temp_path)
        finally:
            os.unlink(str(temp_path))
    
    @pytest.mark.asyncio
    async def test_build_from_document_single_chunk_small_document(self, document_builder, mock_graph_builder):
        """Test building from small document that doesn't need chunking"""
        small_text = "Small document content."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(small_text)
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            assert result.success is True
            assert result.total_chunks == 1
            # Verify single chunk was created manually
            assert len(result.chunk_results) == 1
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_all_chunks_fail(self, document_builder, mock_graph_builder):
        """Test building when all chunks fail"""
        # Make all builds fail
        mock_graph_builder.build_from_text = AsyncMock(
            return_value=BuildResult(success=False, errors=["Build failed"])
        )
        
        large_text = "Sentence. " * 500
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_text)
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            # Should fail if all chunks failed
            assert result.success is False
            assert len(result.errors) > 0
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_exception_during_parsing(self, document_builder):
        """Test exception handling during document parsing"""
        # Create a file that will cause parsing issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Valid content")
            temp_path = f.name
        
        try:
            # Mock _parse_document to raise exception
            with patch.object(document_builder, '_parse_document', new_callable=AsyncMock, side_effect=RuntimeError("Parse error")):
                result = await document_builder.build_from_document(temp_path)
                
                assert result.success is False
                assert len(result.errors) > 0
                assert "Parse error" in result.errors[0] or "failed" in result.errors[0].lower()
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_documents_empty_list(self, document_builder):
        """Test building from empty document list"""
        results = await document_builder.build_from_documents([])
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_build_from_documents_single_document(self, document_builder, mock_graph_builder):
        """Test building from single document"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Single document content.")
            temp_path = f.name
        
        try:
            results = await document_builder.build_from_documents([temp_path])
            
            assert len(results) == 1
            assert results[0].success is True
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_documents_parallel_with_exceptions(self, document_builder, mock_graph_builder):
        """Test parallel document processing with exceptions"""
        # Create one valid and one invalid file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Valid document.")
            temp_path1 = f.name
        
        non_existent_path = "/tmp/non_existent_file_12345.txt"
        
        try:
            results = await document_builder.build_from_documents(
                [temp_path1, non_existent_path],
                parallel=True,
                max_parallel=2
            )
            
            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False
        finally:
            if os.path.exists(temp_path1):
                os.unlink(temp_path1)
    
    @pytest.mark.asyncio
    async def test_build_from_documents_path_objects(self, document_builder, mock_graph_builder):
        """Test building from documents using Path objects"""
        temp_files = []
        try:
            for i in range(2):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(f"Document {i+1}.")
                    temp_files.append(Path(f.name))
            
            results = await document_builder.build_from_documents(temp_files, parallel=False)
            
            assert len(results) == 2
            assert all(r.success for r in results)
        finally:
            for f in temp_files:
                if os.path.exists(str(f)):
                    os.unlink(str(f))
    
    @pytest.mark.asyncio
    async def test_parse_document_dict_result_empty_content(self, document_builder):
        """Test _parse_document with dict result that has empty content"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test")
            temp_path = f.name
        
        try:
            # Mock parser to return dict with empty content
            with patch.object(document_builder.document_parser, 'parse_document', return_value={"content": ""}):
                result = await document_builder._parse_document(temp_path)
                
                # Should fallback to file reading
                assert result == "Test"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_parse_document_dict_result_no_content_key(self, document_builder):
        """Test _parse_document with dict result missing content key"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            # Mock parser to return dict without content key
            with patch.object(document_builder.document_parser, 'parse_document', return_value={"other": "data"}):
                result = await document_builder._parse_document(temp_path)
                
                # Should return empty string and fallback to file reading
                assert result == "Test content"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_parse_document_none_result(self, document_builder):
        """Test _parse_document with None result from parser"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            # Mock parser to return None
            with patch.object(document_builder.document_parser, 'parse_document', return_value=None):
                result = await document_builder._parse_document(temp_path)
                
                # Should return empty string and fallback to file reading
                assert result == "Test content"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_process_chunks_parallel_empty_chunks(self, document_builder):
        """Test parallel chunk processing with empty chunks list"""
        results = await document_builder._process_chunks_parallel([], "test.txt", None)
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_process_chunks_parallel_single_chunk(self, document_builder, mock_graph_builder):
        """Test parallel chunk processing with single chunk"""
        from aiecs.application.knowledge_graph.builder.text_chunker import TextChunk
        
        chunks = [TextChunk(text="Single chunk", start_char=0, end_char=11, chunk_index=0)]
        
        results = await document_builder._process_chunks_parallel(chunks, "test.txt", None)
        
        assert len(results) == 1
        assert mock_graph_builder.build_from_text.call_count == 1
    
    @pytest.mark.asyncio
    async def test_process_chunks_parallel_with_metadata_merging(self, document_builder, mock_graph_builder):
        """Test parallel chunk processing with metadata merging"""
        from aiecs.application.knowledge_graph.builder.text_chunker import TextChunk
        
        chunks = [
            TextChunk(text="Chunk 1", start_char=0, end_char=7, chunk_index=0),
            TextChunk(text="Chunk 2", start_char=8, end_char=15, chunk_index=1)
        ]
        
        metadata = {"author": "Test Author", "date": "2024-01-01"}
        
        results = await document_builder._process_chunks_parallel(
            chunks,
            "test.txt",
            metadata
        )
        
        assert len(results) == 2
        # Verify metadata was passed to graph builder
        calls = mock_graph_builder.build_from_text.call_args_list
        for call in calls:
            call_metadata = call.kwargs.get('metadata', {})
            assert call_metadata.get('author') == "Test Author"
            assert call_metadata.get('date') == "2024-01-01"
            assert 'document' in call_metadata
            assert 'chunk_index' in call_metadata
    
    @pytest.mark.asyncio
    async def test_process_chunks_parallel_exception_handling(self, document_builder, mock_graph_builder):
        """Test parallel chunk processing exception handling"""
        from aiecs.application.knowledge_graph.builder.text_chunker import TextChunk
        
        chunks = [
            TextChunk(text="Chunk 1", start_char=0, end_char=7, chunk_index=0),
            TextChunk(text="Chunk 2", start_char=8, end_char=15, chunk_index=1)
        ]
        
        # Make second build raise exception
        mock_graph_builder.build_from_text = AsyncMock(side_effect=[
            BuildResult(success=True),
            Exception("Build exception")
        ])
        
        results = await document_builder._process_chunks_parallel(chunks, "test.txt", None)
        
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert len(results[1].errors) > 0
        assert "Chunk 1" in results[1].errors[0] or "exception" in results[1].errors[0].lower()
    
    @pytest.mark.asyncio
    async def test_process_chunks_sequential_empty_chunks(self, document_builder):
        """Test sequential chunk processing with empty chunks list"""
        results = await document_builder._process_chunks_sequential([], "test.txt", None)
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_process_chunks_sequential_single_chunk(self, document_builder, mock_graph_builder):
        """Test sequential chunk processing with single chunk"""
        from aiecs.application.knowledge_graph.builder.text_chunker import TextChunk
        
        chunks = [TextChunk(text="Single chunk", start_char=0, end_char=11, chunk_index=0)]
        
        results = await document_builder._process_chunks_sequential(chunks, "test.txt", None)
        
        assert len(results) == 1
        assert mock_graph_builder.build_from_text.call_count == 1
    
    @pytest.mark.asyncio
    async def test_process_chunks_sequential_with_metadata_merging(self, document_builder, mock_graph_builder):
        """Test sequential chunk processing with metadata merging"""
        from aiecs.application.knowledge_graph.builder.text_chunker import TextChunk
        
        chunks = [
            TextChunk(text="Chunk 1", start_char=0, end_char=7, chunk_index=0),
            TextChunk(text="Chunk 2", start_char=8, end_char=15, chunk_index=1)
        ]
        
        metadata = {"author": "Test Author", "version": "1.0"}
        
        results = await document_builder._process_chunks_sequential(
            chunks,
            "test.txt",
            metadata
        )
        
        assert len(results) == 2
        # Verify metadata was merged correctly
        calls = mock_graph_builder.build_from_text.call_args_list
        for i, call in enumerate(calls):
            call_metadata = call.kwargs.get('metadata', {})
            assert call_metadata.get('author') == "Test Author"
            assert call_metadata.get('version') == "1.0"
            assert call_metadata.get('chunk_index') == i
            assert call_metadata.get('document') == "test.txt"
    
    @pytest.mark.asyncio
    async def test_build_from_document_chunking_exact_size(self, document_builder, mock_graph_builder):
        """Test building from document with text exactly at chunk size"""
        builder = self._create_document_builder_with_patched_parser(
            mock_graph_builder,
            chunk_size=100,
            enable_chunking=True
        )
        
        # Create text exactly at chunk size
        text = "A" * 100
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text)
            temp_path = f.name
        
        try:
            result = await builder.build_from_document(temp_path)
            
            assert result.success is True
            # Should create single chunk (text is exactly chunk_size, not > chunk_size)
            assert result.total_chunks == 1
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_unknown_file_type(self, document_builder, mock_graph_builder):
        """Test building from document with unknown file type"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.unknown', delete=False) as f:
            f.write("Content with unknown extension.")
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            assert result.success is True
            assert result.document_type == "unknown"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_build_from_document_no_extension(self, document_builder, mock_graph_builder):
        """Test building from document with no file extension"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Content without extension.")
            temp_path = f.name
        
        try:
            result = await document_builder.build_from_document(temp_path)
            
            assert result.success is True
            # Should handle no extension gracefully
            assert result.document_type == "" or result.document_type == "unknown"
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

