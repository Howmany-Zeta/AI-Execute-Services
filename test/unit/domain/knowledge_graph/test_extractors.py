"""
Unit tests for knowledge graph extractors

Tests use real LLM extractors when LLM is configured in .env.test.
Tests will be skipped if LLM is not configured.
"""

import pytest
import json
from typing import List

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema, EntityType, RelationType
from aiecs.application.knowledge_graph.extractors.base import EntityExtractor, RelationExtractor
from aiecs.application.knowledge_graph.extractors.llm_entity_extractor import LLMEntityExtractor
from aiecs.application.knowledge_graph.extractors.llm_relation_extractor import LLMRelationExtractor
from aiecs.application.knowledge_graph.extractors.ner_entity_extractor import NEREntityExtractor


class TestEntityExtractor:
    """Test EntityExtractor abstract base class"""
    
    def test_entity_extractor_is_abstract(self):
        """Test that EntityExtractor cannot be instantiated directly"""
        with pytest.raises(TypeError):
            EntityExtractor()
    
    def test_entity_extractor_has_extract_entities_method(self):
        """Test that EntityExtractor defines extract_entities method"""
        assert hasattr(EntityExtractor, 'extract_entities')
        assert EntityExtractor.extract_entities.__isabstractmethod__
    
    def test_concrete_entity_extractor_implementation(self):
        """Test that concrete implementations can be created"""
        class ConcreteExtractor(EntityExtractor):
            async def extract_entities(self, text: str, entity_types=None, **kwargs):
                return []
        
        extractor = ConcreteExtractor()
        assert isinstance(extractor, EntityExtractor)


class TestRelationExtractor:
    """Test RelationExtractor abstract base class"""
    
    def test_relation_extractor_is_abstract(self):
        """Test that RelationExtractor cannot be instantiated directly"""
        with pytest.raises(TypeError):
            RelationExtractor()
    
    def test_relation_extractor_has_extract_relations_method(self):
        """Test that RelationExtractor defines extract_relations method"""
        assert hasattr(RelationExtractor, 'extract_relations')
        assert RelationExtractor.extract_relations.__isabstractmethod__
    
    def test_concrete_relation_extractor_implementation(self):
        """Test that concrete implementations can be created"""
        class ConcreteExtractor(RelationExtractor):
            async def extract_relations(self, text: str, entities: List[Entity], relation_types=None, **kwargs):
                return []
        
        extractor = ConcreteExtractor()
        assert isinstance(extractor, RelationExtractor)


class TestNEREntityExtractor:
    """Test NEREntityExtractor"""
    
    @pytest.fixture
    def ner_extractor(self):
        """Create NEREntityExtractor instance"""
        try:
            return NEREntityExtractor(model="en_core_web_sm")
        except RuntimeError:
            pytest.skip("spaCy model 'en_core_web_sm' not installed")
    
    @pytest.mark.asyncio
    async def test_extract_entities_basic(self, ner_extractor):
        """Test basic entity extraction"""
        text = "Alice works at Tech Corp in San Francisco."
        
        entities = await ner_extractor.extract_entities(text)
        
        assert isinstance(entities, list)
        assert len(entities) > 0
        assert all(isinstance(e, Entity) for e in entities)
    
    @pytest.mark.asyncio
    async def test_extract_entities_empty_text(self, ner_extractor):
        """Test extraction with empty text raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            await ner_extractor.extract_entities("")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            await ner_extractor.extract_entities("   ")
    
    @pytest.mark.asyncio
    async def test_extract_entities_with_entity_types_filter(self, ner_extractor):
        """Test extraction with entity type filter"""
        text = "Alice works at Tech Corp in San Francisco."
        
        # Filter for Person entities only
        entities = await ner_extractor.extract_entities(text, entity_types=["Person"])
        
        assert all(e.entity_type == "Person" for e in entities)
    
    @pytest.mark.asyncio
    async def test_extract_entities_properties(self, ner_extractor):
        """Test that extracted entities have required properties"""
        text = "Alice works at Tech Corp."
        
        entities = await ner_extractor.extract_entities(text)
        
        for entity in entities:
            assert entity.id is not None
            assert entity.entity_type is not None
            assert "name" in entity.properties
            assert "text" in entity.properties
            assert "_extraction_confidence" in entity.properties
    
    @pytest.mark.asyncio
    async def test_extract_entities_deduplication(self, ner_extractor):
        """Test that duplicate entities are deduplicated"""
        text = "Alice and Alice work together."
        
        entities = await ner_extractor.extract_entities(text)
        
        # Should not have duplicate entities with same text
        entity_texts = [e.properties.get("text") for e in entities]
        assert len(entity_texts) == len(set(entity_texts))
    
    def test_label_mapping(self, ner_extractor):
        """Test that label mapping works correctly"""
        assert "PERSON" in NEREntityExtractor.LABEL_MAPPING
        assert NEREntityExtractor.LABEL_MAPPING["PERSON"] == "Person"
        assert NEREntityExtractor.LABEL_MAPPING["ORG"] == "Organization"
        assert NEREntityExtractor.LABEL_MAPPING["GPE"] == "Location"
    
    def test_get_supported_types(self, ner_extractor):
        """Test get_supported_types method"""
        supported_types = ner_extractor.get_supported_types()
        
        assert isinstance(supported_types, list)
        assert "Person" in supported_types
        assert "Organization" in supported_types
        assert "Location" in supported_types
    
    def test_get_available_labels(self, ner_extractor):
        """Test get_available_labels method"""
        labels = ner_extractor.get_available_labels()
        
        # spaCy returns labels as a tuple, but we can convert it
        assert labels is not None
        assert len(labels) > 0
        # Check that it's iterable and contains strings
        assert all(isinstance(label, str) for label in labels)
    
    def test_init_with_custom_model(self):
        """Test initialization with custom model"""
        try:
            extractor = NEREntityExtractor(model="en_core_web_sm")
            assert extractor.model_name == "en_core_web_sm"
        except RuntimeError:
            pytest.skip("spaCy model not installed")
    
    def test_init_with_disable_components(self):
        """Test initialization with disabled components"""
        try:
            extractor = NEREntityExtractor(
                model="en_core_web_sm",
                disable_components=["tagger", "parser"]
            )
            assert extractor.model_name == "en_core_web_sm"
        except RuntimeError:
            pytest.skip("spaCy model not installed")
    
    def test_init_model_not_found(self):
        """Test initialization with non-existent model raises RuntimeError"""
        with pytest.raises(RuntimeError, match="not found"):
            NEREntityExtractor(model="non_existent_model_xyz")
    
    def test_generate_entity_id(self, ner_extractor):
        """Test entity ID generation"""
        entity_id = ner_extractor._generate_entity_id("Person", "Alice")
        
        assert isinstance(entity_id, str)
        assert "person" in entity_id.lower()
        assert "alice" in entity_id.lower()
    
    def test_estimate_confidence(self, ner_extractor):
        """Test confidence estimation"""
        # Create a mock entity
        class MockEntity:
            def __init__(self, text):
                self.text = text
        
        # Test with different entity lengths
        short_ent = MockEntity("AI")
        long_ent = MockEntity("Artificial Intelligence Corporation")
        capitalized_ent = MockEntity("Alice")
        
        conf_short = ner_extractor._estimate_confidence(short_ent)
        conf_long = ner_extractor._estimate_confidence(long_ent)
        conf_cap = ner_extractor._estimate_confidence(capitalized_ent)
        
        assert 0.0 <= conf_short <= 1.0
        assert 0.0 <= conf_long <= 1.0
        assert 0.0 <= conf_cap <= 1.0
        # Longer entities should have higher confidence
        assert conf_long >= conf_short


class TestLLMEntityExtractor:
    """Test LLMEntityExtractor with real LLM"""
    
    @pytest.fixture
    def llm_extractor(self, check_llm_configured):
        """Create LLMEntityExtractor instance with real LLM (XAI/Grok 3)"""
        # get_llm_manager is async but called synchronously in __init__
        # Access the global manager directly for testing
        from aiecs.llm.client_factory import _llm_manager
        from aiecs.llm.client_factory import AIProvider
        extractor = LLMEntityExtractor(
            schema=None,
            provider=AIProvider.XAI,
            model="grok-3"  # Grok 3 model name
        )
        # Fix the async issue by setting manager directly
        extractor.llm_manager = _llm_manager
        return extractor
    
    @pytest.fixture
    def llm_extractor_with_schema(self, check_llm_configured):
        """Create LLMEntityExtractor with schema (XAI/Grok 3)"""
        # Create a simple schema
        from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType
        schema = GraphSchema()
        entity_type = EntityType(
            name="Person",
            description="A person entity",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
                "age": PropertySchema(name="age", property_type=PropertyType.INTEGER)
            }
        )
        schema.add_entity_type(entity_type)
        
        from aiecs.llm.client_factory import _llm_manager
        from aiecs.llm.client_factory import AIProvider
        extractor = LLMEntityExtractor(
            schema=schema,
            provider=AIProvider.XAI,
            model="grok-3"  # Grok 3 model name
        )
        # Fix the async issue by setting manager directly
        extractor.llm_manager = _llm_manager
        return extractor
    
    @pytest.mark.asyncio
    async def test_extract_entities_basic(self, llm_extractor):
        """Test basic entity extraction with real LLM"""
        text = "Alice is a 30-year-old data scientist who works at Tech Corp in San Francisco."
        
        entities = await llm_extractor.extract_entities(text)
        
        assert isinstance(entities, list)
        assert len(entities) > 0
        assert all(isinstance(e, Entity) for e in entities)
        # Should extract at least one entity
        assert any(e.entity_type in ["Person", "Organization", "Location"] for e in entities)
    
    @pytest.mark.asyncio
    async def test_extract_entities_empty_text(self, llm_extractor):
        """Test extraction with empty text raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            await llm_extractor.extract_entities("")
    
    @pytest.mark.asyncio
    async def test_extract_entities_with_entity_types_filter(self, llm_extractor):
        """Test extraction with entity type filter"""
        text = "Alice works at Tech Corp in San Francisco."
        
        entities = await llm_extractor.extract_entities(text, entity_types=["Person"])
        
        # Should only extract Person entities
        assert all(e.entity_type == "Person" for e in entities)
    
    @pytest.mark.asyncio
    async def test_extract_entities_with_schema(self, llm_extractor_with_schema):
        """Test extraction with schema guidance"""
        text = "Alice is 30 years old and works at Tech Corp."
        
        entities = await llm_extractor_with_schema.extract_entities(text)
        
        assert isinstance(entities, list)
        # Should extract Person entities based on schema
        person_entities = [e for e in entities if e.entity_type == "Person"]
        assert len(person_entities) > 0
    
    @pytest.mark.asyncio
    async def test_extract_entities_properties(self, llm_extractor):
        """Test that extracted entities have properties"""
        text = "Alice is 30 years old."
        
        entities = await llm_extractor.extract_entities(text)
        
        assert len(entities) > 0
        for entity in entities:
            assert entity.id is not None
            assert entity.entity_type is not None
            assert isinstance(entity.properties, dict)
            # Should have confidence score
            assert "_extraction_confidence" in entity.properties
    
    @pytest.mark.asyncio
    async def test_extract_entities_complex_text(self, llm_extractor):
        """Test extraction from complex text"""
        text = """
        Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
        The company is headquartered in Cupertino, California.
        Tim Cook is the current CEO of Apple.
        """
        
        entities = await llm_extractor.extract_entities(text)
        
        assert len(entities) > 0
        # Should extract multiple entities
        entity_types = {e.entity_type for e in entities}
        assert len(entity_types) > 1
    
    def test_build_extraction_prompt_with_schema(self, llm_extractor_with_schema):
        """Test prompt building with schema"""
        prompt = llm_extractor_with_schema._build_extraction_prompt("Test text", None)
        
        assert isinstance(prompt, str)
        assert "Test text" in prompt
        assert "Person" in prompt
    
    def test_build_extraction_prompt_with_entity_types(self, llm_extractor):
        """Test prompt building with entity type filter"""
        prompt = llm_extractor._build_extraction_prompt("Test", ["Person"])
        
        assert "Person" in prompt
    
    def test_build_extraction_prompt_without_schema(self, check_llm_configured):
        """Test prompt building without schema"""
        from aiecs.llm.client_factory import _llm_manager, AIProvider
        extractor = LLMEntityExtractor(schema=None, provider=AIProvider.XAI, model="grok-beta")
        extractor.llm_manager = _llm_manager
        prompt = extractor._build_extraction_prompt("Test", ["Person"])
        
        assert "Person" in prompt
    
    def test_build_extraction_prompt_common_types(self, check_llm_configured):
        """Test prompt building with common types when no schema"""
        from aiecs.llm.client_factory import _llm_manager, AIProvider
        extractor = LLMEntityExtractor(schema=None, provider=AIProvider.XAI, model="grok-beta")
        extractor.llm_manager = _llm_manager
        prompt = extractor._build_extraction_prompt("Test", None)
        
        assert "Person" in prompt or "Organization" in prompt
    
    def test_parse_llm_response_valid_json(self, llm_extractor):
        """Test parsing valid JSON response"""
        response = json.dumps([
            {
                "type": "Person",
                "properties": {"name": "Alice"},
                "confidence": 0.9
            }
        ])
        
        entities = llm_extractor._parse_llm_response(response)
        
        assert len(entities) == 1
        assert entities[0].entity_type == "Person"
        assert entities[0].properties["name"] == "Alice"
        assert entities[0].properties["_extraction_confidence"] == 0.9
    
    def test_parse_llm_response_missing_fields(self, llm_extractor):
        """Test parsing response with missing fields"""
        response = json.dumps([
            {"type": "Person"}  # Missing properties and confidence
        ])
        
        entities = llm_extractor._parse_llm_response(response)
        
        assert len(entities) == 1
        assert entities[0].entity_type == "Person"
        assert entities[0].properties == {"_extraction_confidence": 0.5}
    
    def test_parse_llm_response_invalid_json(self, llm_extractor):
        """Test parsing invalid JSON returns empty list"""
        response = "This is not valid JSON"
        
        entities = llm_extractor._parse_llm_response(response)
        
        assert entities == []
    
    def test_parse_llm_response_single_object(self, llm_extractor):
        """Test parsing single object instead of array"""
        response = json.dumps({
            "type": "Person",
            "properties": {"name": "Alice"},
            "confidence": 0.9
        })
        
        entities = llm_extractor._parse_llm_response(response)
        
        assert len(entities) == 1
        assert entities[0].entity_type == "Person"
    
    def test_extract_json_from_text_array(self, llm_extractor):
        """Test extracting JSON array from text"""
        text = "Some text before [{\"type\": \"Person\"}] some text after"
        json_str = llm_extractor._extract_json_from_text(text)
        
        assert json_str.startswith("[")
        assert json_str.endswith("]")
    
    def test_extract_json_from_text_object(self, llm_extractor):
        """Test extracting JSON object from text"""
        text = "Some text before {\"type\": \"Person\"} some text after"
        json_str = llm_extractor._extract_json_from_text(text)
        
        assert json_str.startswith("{")
        assert json_str.endswith("}")
    
    def test_extract_json_from_text_no_json(self, llm_extractor):
        """Test extracting JSON when none exists"""
        text = "This is just plain text with no JSON"
        json_str = llm_extractor._extract_json_from_text(text)
        
        assert json_str == text
    
    def test_generate_entity_id_with_name(self, llm_extractor):
        """Test entity ID generation with name property"""
        entity_id = llm_extractor._generate_entity_id("Person", {"name": "Alice"})
        
        assert "person" in entity_id.lower()
        assert "alice" in entity_id.lower()
        assert len(entity_id) > 0
    
    def test_generate_entity_id_with_title(self, llm_extractor):
        """Test entity ID generation with title property"""
        entity_id = llm_extractor._generate_entity_id("Person", {"title": "Alice"})
        
        assert "person" in entity_id.lower()
        assert "alice" in entity_id.lower()
    
    def test_generate_entity_id_without_name(self, llm_extractor):
        """Test entity ID generation without name property"""
        entity_id = llm_extractor._generate_entity_id("Person", {"age": 30})
        
        assert "person" in entity_id.lower()
        assert len(entity_id) > 0
    
    def test_init_with_custom_params(self, check_llm_configured):
        """Test initialization with custom parameters"""
        from aiecs.llm.client_factory import _llm_manager, AIProvider
        extractor = LLMEntityExtractor(
            schema=None,
            provider=AIProvider.XAI,
            model="grok-beta",
            temperature=0.5,
            max_tokens=1000
        )
        extractor.llm_manager = _llm_manager
        
        assert extractor.temperature == 0.5
        assert extractor.max_tokens == 1000
        assert extractor.provider == AIProvider.XAI
        assert extractor.model == "grok-beta"


class TestLLMRelationExtractor:
    """Test LLMRelationExtractor with real LLM"""
    
    @pytest.fixture
    def sample_entities(self):
        """Create sample entities for testing"""
        return [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Company", properties={"name": "Tech Corp"}),
            Entity(id="e3", entity_type="Location", properties={"name": "San Francisco"})
        ]
    
    @pytest.fixture
    def llm_relation_extractor(self, check_llm_configured):
        """Create LLMRelationExtractor instance with real LLM (XAI/Grok 3)"""
        from aiecs.llm.client_factory import _llm_manager
        from aiecs.llm.client_factory import AIProvider
        extractor = LLMRelationExtractor(
            schema=None,
            provider=AIProvider.XAI,
            model="grok-3"  # Grok 3 model name
        )
        # Fix the async issue by setting manager directly
        extractor.llm_manager = _llm_manager
        return extractor
    
    @pytest.fixture
    def llm_relation_extractor_with_schema(self, check_llm_configured):
        """Create LLMRelationExtractor with schema (XAI/Grok 3)"""
        schema = GraphSchema()
        relation_type = RelationType(
            name="WORKS_FOR",
            description="Employment relationship",
            source_types=["Person"],
            target_types=["Company"]
        )
        schema.add_relation_type(relation_type)
        
        from aiecs.llm.client_factory import _llm_manager
        from aiecs.llm.client_factory import AIProvider
        extractor = LLMRelationExtractor(
            schema=schema,
            provider=AIProvider.XAI,
            model="grok-3"  # Grok 3 model name
        )
        # Fix the async issue by setting manager directly
        extractor.llm_manager = _llm_manager
        return extractor
    
    @pytest.mark.asyncio
    async def test_extract_relations_basic(self, llm_relation_extractor, sample_entities):
        """Test basic relation extraction with real LLM"""
        text = "Alice works at Tech Corp as a senior engineer."
        
        relations = await llm_relation_extractor.extract_relations(text, sample_entities)
        
        assert isinstance(relations, list)
        # Should extract at least one relation
        assert len(relations) > 0
        assert all(isinstance(r, Relation) for r in relations)
    
    @pytest.mark.asyncio
    async def test_extract_relations_empty_text(self, llm_relation_extractor, sample_entities):
        """Test extraction with empty text raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            await llm_relation_extractor.extract_relations("", sample_entities)
    
    @pytest.mark.asyncio
    async def test_extract_relations_insufficient_entities(self, llm_relation_extractor):
        """Test extraction with less than 2 entities returns empty list"""
        text = "Some text"
        entities = [Entity(id="e1", entity_type="Person", properties={})]
        
        relations = await llm_relation_extractor.extract_relations(text, entities)
        
        assert relations == []
    
    @pytest.mark.asyncio
    async def test_extract_relations_empty_entities(self, llm_relation_extractor):
        """Test extraction with empty entities list returns empty list"""
        text = "Some text"
        
        relations = await llm_relation_extractor.extract_relations(text, [])
        
        assert relations == []
    
    @pytest.mark.asyncio
    async def test_extract_relations_with_schema(self, llm_relation_extractor_with_schema, sample_entities):
        """Test relation extraction with schema guidance"""
        text = "Alice works at Tech Corp."
        
        relations = await llm_relation_extractor_with_schema.extract_relations(text, sample_entities)
        
        assert isinstance(relations, list)
        # Should extract WORKS_FOR relations based on schema
        works_for_relations = [r for r in relations if r.relation_type == "WORKS_FOR"]
        assert len(works_for_relations) > 0
    
    @pytest.mark.asyncio
    async def test_extract_relations_with_relation_types_filter(self, llm_relation_extractor, sample_entities):
        """Test extraction with relation type filter"""
        text = "Alice works at Tech Corp and lives in San Francisco."
        
        relations = await llm_relation_extractor.extract_relations(
            text, 
            sample_entities, 
            relation_types=["WORKS_FOR"]
        )
        
        # Should only extract WORKS_FOR relations
        assert all(r.relation_type == "WORKS_FOR" for r in relations)
    
    @pytest.mark.asyncio
    async def test_extract_relations_properties(self, llm_relation_extractor, sample_entities):
        """Test that extracted relations have properties"""
        text = "Alice works at Tech Corp as a senior engineer since 2020."
        
        relations = await llm_relation_extractor.extract_relations(text, sample_entities)
        
        assert len(relations) > 0
        for relation in relations:
            assert relation.id is not None
            assert relation.relation_type is not None
            assert relation.source_id is not None
            assert relation.target_id is not None
            assert isinstance(relation.properties, dict)
            assert "_extraction_confidence" in relation.properties
    
    @pytest.mark.asyncio
    async def test_extract_relations_complex_text(self, llm_relation_extractor, sample_entities):
        """Test extraction from complex text"""
        text = """
        Alice works at Tech Corp as a senior engineer.
        Tech Corp is located in San Francisco.
        Alice has been working there since 2020.
        """
        
        relations = await llm_relation_extractor.extract_relations(text, sample_entities)
        
        assert len(relations) > 0
        # Should extract multiple relations
        relation_types = {r.relation_type for r in relations}
        assert len(relation_types) > 0
    
    def test_build_extraction_prompt_with_schema(self, llm_relation_extractor_with_schema, sample_entities):
        """Test prompt building with schema"""
        prompt = llm_relation_extractor_with_schema._build_extraction_prompt("Test text", sample_entities, None)
        
        assert isinstance(prompt, str)
        assert "Test text" in prompt
        assert "e1" in prompt
        assert "e2" in prompt
        assert "WORKS_FOR" in prompt
    
    def test_build_extraction_prompt_with_relation_types(self, llm_relation_extractor, sample_entities):
        """Test prompt building with relation type filter"""
        prompt = llm_relation_extractor._build_extraction_prompt("Test", sample_entities, ["WORKS_FOR"])
        
        assert "WORKS_FOR" in prompt
    
    def test_build_extraction_prompt_without_schema(self, check_llm_configured, sample_entities):
        """Test prompt building without schema"""
        from aiecs.llm.client_factory import _llm_manager, AIProvider
        extractor = LLMRelationExtractor(schema=None, provider=AIProvider.XAI, model="grok-beta")
        extractor.llm_manager = _llm_manager
        prompt = extractor._build_extraction_prompt("Test", sample_entities, None)
        
        assert "WORKS_FOR" in prompt or "LOCATED_IN" in prompt
    
    def test_parse_llm_response_valid(self, llm_relation_extractor, sample_entities):
        """Test parsing valid JSON response"""
        response = json.dumps([
            {
                "source_id": "e1",
                "target_id": "e2",
                "relation_type": "WORKS_FOR",
                "properties": {"title": "engineer"},
                "confidence": 0.9
            }
        ])
        
        relations = llm_relation_extractor._parse_llm_response(response, sample_entities)
        
        assert len(relations) == 1
        assert relations[0].source_id == "e1"
        assert relations[0].target_id == "e2"
        assert relations[0].relation_type == "WORKS_FOR"
        assert relations[0].properties["_extraction_confidence"] == 0.9
    
    def test_parse_llm_response_invalid_entity_ids(self, llm_relation_extractor, sample_entities):
        """Test filtering of relations with invalid entity IDs"""
        response = json.dumps([
            {
                "source_id": "e1",
                "target_id": "e2",
                "relation_type": "WORKS_FOR",
                "confidence": 0.9
            },
            {
                "source_id": "invalid_id",
                "target_id": "e2",
                "relation_type": "WORKS_FOR",
                "confidence": 0.9
            }
        ])
        
        relations = llm_relation_extractor._parse_llm_response(response, sample_entities)
        
        # Should only include valid relations
        assert len(relations) == 1
        assert relations[0].source_id == "e1"
    
    def test_parse_llm_response_self_loop_filtered(self, llm_relation_extractor, sample_entities):
        """Test that self-loops are filtered out"""
        response = json.dumps([
            {
                "source_id": "e1",
                "target_id": "e1",  # Self-loop
                "relation_type": "KNOWS",
                "confidence": 0.9
            }
        ])
        
        relations = llm_relation_extractor._parse_llm_response(response, sample_entities)
        
        assert relations == []
    
    def test_parse_llm_response_missing_fields(self, llm_relation_extractor, sample_entities):
        """Test handling of relations with missing fields"""
        response = json.dumps([
            {
                "source_id": "e1",
                "target_id": "e2"
                # Missing relation_type
            },
            {
                "source_id": "e1",
                "target_id": "e2",
                "relation_type": None  # None relation_type
            }
        ])
        
        relations = llm_relation_extractor._parse_llm_response(response, sample_entities)
        
        # Should skip relations with missing or None required fields
        assert len(relations) == 0
    
    def test_parse_llm_response_single_object(self, llm_relation_extractor, sample_entities):
        """Test parsing single object response"""
        response = json.dumps({
            "source_id": "e1",
            "target_id": "e2",
            "relation_type": "WORKS_FOR",
            "confidence": 0.9
        })
        
        relations = llm_relation_extractor._parse_llm_response(response, sample_entities)
        
        assert len(relations) == 1
    
    def test_parse_llm_response_invalid_json(self, llm_relation_extractor, sample_entities):
        """Test handling of invalid JSON response"""
        response = "This is not valid JSON"
        
        relations = llm_relation_extractor._parse_llm_response(response, sample_entities)
        
        assert relations == []
    
    def test_extract_json_from_text(self, llm_relation_extractor):
        """Test JSON extraction from text"""
        text = "Some text [{\"source_id\": \"e1\"}] more text"
        json_str = llm_relation_extractor._extract_json_from_text(text)
        
        assert json_str.startswith("[")
        assert json_str.endswith("]")
    
    def test_get_entity_name(self, llm_relation_extractor):
        """Test entity name extraction"""
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Company", properties={"title": "Tech Corp"})
        entity3 = Entity(id="e3", entity_type="Location", properties={})
        
        assert llm_relation_extractor._get_entity_name(entity1) == "Alice"
        assert llm_relation_extractor._get_entity_name(entity2) == "Tech Corp"
        assert "e3" in llm_relation_extractor._get_entity_name(entity3)
    
    def test_init_with_custom_params(self, check_llm_configured):
        """Test initialization with custom parameters"""
        from aiecs.llm.client_factory import _llm_manager, AIProvider
        extractor = LLMRelationExtractor(
            schema=None,
            provider=AIProvider.XAI,
            model="grok-beta",
            temperature=0.5,
            max_tokens=1000
        )
        extractor.llm_manager = _llm_manager
        
        assert extractor.temperature == 0.5
        assert extractor.max_tokens == 1000
        assert extractor.provider == AIProvider.XAI
        assert extractor.model == "grok-beta"
