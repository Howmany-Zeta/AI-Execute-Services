"""
Unit tests for knowledge graph domain models
"""

import pytest
from datetime import datetime
import numpy as np
from pydantic import ValidationError

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.query import GraphQuery, GraphResult, QueryType
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern, TraversalDirection
from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan, QueryStep, QueryOperation, OptimizationStrategy
from aiecs.domain.knowledge_graph.models.evidence import Evidence, EvidenceType, ReasoningResult
from aiecs.domain.knowledge_graph.models.inference_rule import InferenceRule, InferenceStep, InferenceResult, RuleType


class TestEntity:
    """Test Entity model"""
    
    def test_entity_creation(self):
        """Test basic entity creation"""
        entity = Entity(
            id="test_1",
            entity_type="Person",
            properties={"name": "Alice", "age": 30}
        )
        
        assert entity.id == "test_1"
        assert entity.entity_type == "Person"
        assert entity.properties["name"] == "Alice"
        assert entity.properties["age"] == 30
        assert isinstance(entity.created_at, datetime)
    
    def test_entity_with_embedding(self):
        """Test entity with vector embedding"""
        embedding = [0.1, 0.2, 0.3]
        entity = Entity(
            id="test_1",
            entity_type="Document",
            embedding=embedding
        )
        
        assert entity.embedding == embedding
        vector = entity.get_embedding_vector()
        assert isinstance(vector, np.ndarray)
        assert len(vector) == 3
    
    def test_entity_property_access(self):
        """Test property getter/setter"""
        entity = Entity(id="test_1", entity_type="Person")
        
        entity.set_property("name", "Bob")
        assert entity.get_property("name") == "Bob"
        assert entity.get_property("missing", "default") == "default"
    
    def test_entity_set_embedding_vector(self):
        """Test setting embedding from numpy array"""
        entity = Entity(id="test_1", entity_type="Document")
        vector = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        
        entity.set_embedding_vector(vector)
        # Check approximate equality due to float32 precision
        assert len(entity.embedding) == 3
        assert abs(entity.embedding[0] - 0.1) < 0.0001
        assert abs(entity.embedding[1] - 0.2) < 0.0001
        assert abs(entity.embedding[2] - 0.3) < 0.0001
        assert isinstance(entity.get_embedding_vector(), np.ndarray)
    
    def test_entity_embedding_validation(self):
        """Test embedding validation"""
        # Valid: list of floats
        entity1 = Entity(id="e1", entity_type="Document", embedding=[0.1, 0.2, 0.3])
        assert entity1.embedding == [0.1, 0.2, 0.3]
        
        # Valid: list of ints (converted to floats)
        entity2 = Entity(id="e2", entity_type="Document", embedding=[1, 2, 3])
        assert entity2.embedding == [1, 2, 3]
        
        # Invalid: not a list (Pydantic validation error)
        with pytest.raises(ValidationError):
            Entity(id="e3", entity_type="Document", embedding="not a list")
        
        # Invalid: contains non-numeric values (Pydantic validation error)
        with pytest.raises(ValidationError):
            Entity(id="e4", entity_type="Document", embedding=[0.1, "invalid", 0.3])
    
    def test_entity_updated_at_timestamp(self):
        """Test that updated_at changes when setting properties"""
        entity = Entity(id="test_1", entity_type="Person")
        original_updated = entity.updated_at
        
        # Wait a tiny bit to ensure timestamp changes
        import time
        time.sleep(0.01)
        
        entity.set_property("name", "Alice")
        assert entity.updated_at > original_updated
    
    def test_entity_string_representations(self):
        """Test string representations"""
        entity = Entity(id="test_1", entity_type="Person", properties={"name": "Alice"})
        
        str_repr = str(entity)
        assert "test_1" in str_repr
        assert "Person" in str_repr
        
        repr_str = repr(entity)
        assert "test_1" in repr_str
        assert "Person" in repr_str
        assert "properties" in repr_str.lower()
    
    def test_entity_with_source(self):
        """Test entity with source metadata"""
        entity = Entity(
            id="test_1",
            entity_type="Person",
            source="document_123"
        )
        assert entity.source == "document_123"


class TestRelation:
    """Test Relation model"""
    
    def test_relation_creation(self):
        """Test basic relation creation"""
        relation = Relation(
            id="rel_1",
            relation_type="KNOWS",
            source_id="person_1",
            target_id="person_2",
            weight=0.8
        )
        
        assert relation.id == "rel_1"
        assert relation.relation_type == "KNOWS"
        assert relation.source_id == "person_1"
        assert relation.target_id == "person_2"
        assert relation.weight == 0.8
    
    def test_relation_with_properties(self):
        """Test relation with properties"""
        relation = Relation(
            id="rel_1",
            relation_type="WORKS_FOR",
            source_id="person_1",
            target_id="company_1",
            properties={"since": "2020-01-01", "role": "Engineer"}
        )
        
        assert relation.get_property("role") == "Engineer"
        assert relation.get_property("since") == "2020-01-01"
    
    def test_relation_reverse(self):
        """Test relation reversal"""
        relation = Relation(
            id="rel_1",
            relation_type="KNOWS",
            source_id="person_1",
            target_id="person_2"
        )
        
        reversed_rel = relation.reverse()
        assert reversed_rel.source_id == "person_2"
        assert reversed_rel.target_id == "person_1"
        assert reversed_rel.relation_type == "KNOWS_REVERSE"
    
    def test_relation_set_property(self):
        """Test setting relation properties"""
        relation = Relation(
            id="rel_1",
            relation_type="WORKS_FOR",
            source_id="person_1",
            target_id="company_1"
        )
        
        relation.set_property("role", "Engineer")
        assert relation.get_property("role") == "Engineer"
    
    def test_relation_entity_id_validation(self):
        """Test entity ID validation"""
        # Valid: non-empty string
        relation1 = Relation(
            id="rel_1",
            relation_type="KNOWS",
            source_id="person_1",
            target_id="person_2"
        )
        assert relation1.source_id == "person_1"
        
        # Invalid: empty string
        with pytest.raises(ValueError, match="Entity IDs must be non-empty"):
            Relation(
                id="rel_2",
                relation_type="KNOWS",
                source_id="",
                target_id="person_2"
            )
        
        # Invalid: whitespace only
        with pytest.raises(ValueError, match="Entity IDs must be non-empty"):
            Relation(
                id="rel_3",
                relation_type="KNOWS",
                source_id="person_1",
                target_id="   "
            )
    
    def test_relation_weight_validation(self):
        """Test weight boundary validation"""
        # Valid: 0.0
        relation1 = Relation(
            id="rel_1",
            relation_type="KNOWS",
            source_id="person_1",
            target_id="person_2",
            weight=0.0
        )
        assert relation1.weight == 0.0
        
        # Valid: 1.0
        relation2 = Relation(
            id="rel_2",
            relation_type="KNOWS",
            source_id="person_1",
            target_id="person_2",
            weight=1.0
        )
        assert relation2.weight == 1.0
        
        # Invalid: negative
        with pytest.raises(ValueError):
            Relation(
                id="rel_3",
                relation_type="KNOWS",
                source_id="person_1",
                target_id="person_2",
                weight=-0.1
            )
        
        # Invalid: > 1.0
        with pytest.raises(ValueError):
            Relation(
                id="rel_4",
                relation_type="KNOWS",
                source_id="person_1",
                target_id="person_2",
                weight=1.1
            )
    
    def test_relation_string_representations(self):
        """Test string representations"""
        relation = Relation(
            id="rel_1",
            relation_type="KNOWS",
            source_id="person_1",
            target_id="person_2",
            weight=0.8
        )
        
        str_repr = str(relation)
        assert "person_1" in str_repr
        assert "person_2" in str_repr
        assert "KNOWS" in str_repr
        
        repr_str = repr(relation)
        assert "rel_1" in repr_str
        assert "KNOWS" in repr_str
        assert "0.8" in repr_str
    
    def test_relation_with_source(self):
        """Test relation with source metadata"""
        relation = Relation(
            id="rel_1",
            relation_type="KNOWS",
            source_id="person_1",
            target_id="person_2",
            source="document_123"
        )
        assert relation.source == "document_123"


class TestPath:
    """Test Path model"""
    
    def test_path_creation(self):
        """Test basic path creation"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        entity3 = Entity(id="e3", entity_type="Person")
        
        relation1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        relation2 = Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3")
        
        path = Path(
            nodes=[entity1, entity2, entity3],
            edges=[relation1, relation2],
            score=0.9
        )
        
        assert path.length == 2
        assert path.start_entity.id == "e1"
        assert path.end_entity.id == "e3"
        assert path.score == 0.9
    
    def test_path_validation(self):
        """Test path structure validation"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        
        # Valid path
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        path = Path(nodes=[entity1, entity2], edges=[relation])
        assert path.length == 1
        
        # Invalid: wrong number of edges
        with pytest.raises(ValueError):
            Path(nodes=[entity1, entity2], edges=[relation, relation])
    
    def test_path_edge_connectivity_validation(self):
        """Test path edge connectivity validation"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        entity3 = Entity(id="e3", entity_type="Person")
        
        # Invalid: edge source doesn't match node
        relation1 = Relation(id="r1", relation_type="KNOWS", source_id="wrong", target_id="e2")
        with pytest.raises(ValueError, match="doesn't match"):
            Path(nodes=[entity1, entity2], edges=[relation1])
        
        # Invalid: edge target doesn't match node
        relation2 = Relation(id="r2", relation_type="KNOWS", source_id="e1", target_id="wrong")
        with pytest.raises(ValueError, match="doesn't match"):
            Path(nodes=[entity1, entity2], edges=[relation2])
    
    def test_path_single_node(self):
        """Test path with single node (no edges)"""
        entity1 = Entity(id="e1", entity_type="Person")
        path = Path(nodes=[entity1], edges=[])
        
        assert path.length == 0
        assert path.start_entity.id == "e1"
        assert path.end_entity.id == "e1"
    
    def test_path_get_entity_ids(self):
        """Test getting entity IDs from path"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        entity3 = Entity(id="e3", entity_type="Person")
        
        relation1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        relation2 = Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3")
        
        path = Path(nodes=[entity1, entity2, entity3], edges=[relation1, relation2])
        
        entity_ids = path.get_entity_ids()
        assert entity_ids == ["e1", "e2", "e3"]
    
    def test_path_get_relation_types(self):
        """Test getting relation types from path"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        entity3 = Entity(id="e3", entity_type="Person")
        
        relation1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        relation2 = Relation(id="r2", relation_type="WORKS_FOR", source_id="e2", target_id="e3")
        
        path = Path(nodes=[entity1, entity2, entity3], edges=[relation1, relation2])
        
        relation_types = path.get_relation_types()
        assert relation_types == ["KNOWS", "WORKS_FOR"]
    
    def test_path_contains_entity(self):
        """Test checking if path contains entity"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        entity3 = Entity(id="e3", entity_type="Person")
        
        relation1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        relation2 = Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3")
        
        path = Path(nodes=[entity1, entity2, entity3], edges=[relation1, relation2])
        
        assert path.contains_entity("e1") is True
        assert path.contains_entity("e2") is True
        assert path.contains_entity("e3") is True
        assert path.contains_entity("e4") is False
    
    def test_path_contains_relation_type(self):
        """Test checking if path contains relation type"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        entity3 = Entity(id="e3", entity_type="Person")
        
        relation1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        relation2 = Relation(id="r2", relation_type="WORKS_FOR", source_id="e2", target_id="e3")
        
        path = Path(nodes=[entity1, entity2, entity3], edges=[relation1, relation2])
        
        assert path.contains_relation_type("KNOWS") is True
        assert path.contains_relation_type("WORKS_FOR") is True
        assert path.contains_relation_type("LIKES") is False
    
    def test_path_string_representations(self):
        """Test path string representations"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        path = Path(nodes=[entity1, entity2], edges=[relation], score=0.9)
        
        str_repr = str(path)
        assert "e1" in str_repr
        assert "e2" in str_repr
        assert "KNOWS" in str_repr
        assert "0.9" in str_repr or "score" in str_repr.lower()
        
        repr_str = repr(path)
        assert "length" in repr_str.lower() or "2" in repr_str


class TestGraphQuery:
    """Test GraphQuery model"""
    
    def test_entity_lookup_query(self):
        """Test entity lookup query"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="person_1"
        )
        
        assert query.query_type == QueryType.ENTITY_LOOKUP
        assert query.entity_id == "person_1"
    
    def test_vector_search_query(self):
        """Test vector search query"""
        query = GraphQuery(
            query_type=QueryType.VECTOR_SEARCH,
            embedding=[0.1, 0.2, 0.3],
            entity_type="Document",
            max_results=5,
            score_threshold=0.7
        )
        
        assert query.query_type == QueryType.VECTOR_SEARCH
        assert len(query.embedding) == 3
        assert query.max_results == 5
        assert query.score_threshold == 0.7
    
    def test_traversal_query(self):
        """Test traversal query"""
        query = GraphQuery(
            query_type=QueryType.TRAVERSAL,
            entity_id="person_1",
            relation_type="KNOWS",
            max_depth=3
        )
        
        assert query.query_type == QueryType.TRAVERSAL
        assert query.entity_id == "person_1"
        assert query.relation_type == "KNOWS"
        assert query.max_depth == 3
    
    def test_path_finding_query(self):
        """Test path finding query"""
        query = GraphQuery(
            query_type=QueryType.PATH_FINDING,
            source_entity_id="person_1",
            target_entity_id="person_2",
            max_depth=5
        )
        
        assert query.query_type == QueryType.PATH_FINDING
        assert query.source_entity_id == "person_1"
        assert query.target_entity_id == "person_2"
        assert query.max_depth == 5
    
    def test_subgraph_query(self):
        """Test subgraph query"""
        query = GraphQuery(
            query_type=QueryType.SUBGRAPH,
            entity_id="person_1",
            max_depth=2,
            entity_type="Person"
        )
        
        assert query.query_type == QueryType.SUBGRAPH
        assert query.entity_id == "person_1"
        assert query.max_depth == 2
        assert query.entity_type == "Person"
    
    def test_query_with_properties(self):
        """Test query with property constraints"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            properties={"age": 30, "city": "NYC"}
        )
        
        assert query.properties["age"] == 30
        assert query.properties["city"] == "NYC"
    
    def test_query_with_custom_params(self):
        """Test query with custom parameters"""
        query = GraphQuery(
            query_type=QueryType.CUSTOM,
            custom_params={"algorithm": "dijkstra", "weighted": True}
        )
        
        assert query.custom_params["algorithm"] == "dijkstra"
        assert query.custom_params["weighted"] is True
    
    def test_query_string_representation(self):
        """Test query string representation"""
        query = GraphQuery(
            query_type=QueryType.VECTOR_SEARCH,
            entity_type="Document"
        )
        
        str_repr = str(query)
        assert "VECTOR_SEARCH" in str_repr or "vector_search" in str_repr.lower()
        assert "Document" in str_repr


class TestGraphResult:
    """Test GraphResult model"""
    
    def test_empty_result(self):
        """Test empty result"""
        query = GraphQuery(query_type=QueryType.ENTITY_LOOKUP)
        result = GraphResult(query=query)
        
        assert not result.has_results
        assert result.entity_count == 0
        assert result.path_count == 0
    
    def test_result_with_entities(self):
        """Test result with entities"""
        query = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        
        result = GraphResult(
            query=query,
            entities=[entity1, entity2],
            scores=[0.9, 0.7],
            total_count=2
        )
        
        assert result.has_results
        assert result.entity_count == 2
        assert len(result.get_entity_ids()) == 2
        
        top_entities = result.get_top_entities(n=1)
        assert len(top_entities) == 1
        assert top_entities[0].id == "e1"  # Highest score
    
    def test_result_with_paths(self):
        """Test result with paths"""
        query = GraphQuery(query_type=QueryType.PATH_FINDING)
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        path = Path(nodes=[entity1, entity2], edges=[relation])
        
        result = GraphResult(
            query=query,
            paths=[path],
            total_count=1
        )
        
        assert result.has_results
        assert result.path_count == 1
        assert result.entity_count == 0
    
    def test_result_with_relations(self):
        """Test result with relations"""
        query = GraphQuery(query_type=QueryType.TRAVERSAL)
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        
        result = GraphResult(
            query=query,
            relations=[relation],
            total_count=1
        )
        
        assert len(result.relations) == 1
        assert result.relations[0].id == "r1"
    
    def test_result_get_top_entities_no_scores(self):
        """Test get_top_entities when no scores provided"""
        query = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        entity3 = Entity(id="e3", entity_type="Person")
        
        result = GraphResult(
            query=query,
            entities=[entity1, entity2, entity3],
            scores=[]  # No scores
        )
        
        top_entities = result.get_top_entities(n=2)
        assert len(top_entities) == 2
        assert top_entities[0].id == "e1"  # First entity
    
    def test_result_get_top_entities_more_than_available(self):
        """Test get_top_entities when requesting more than available"""
        query = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        
        result = GraphResult(
            query=query,
            entities=[entity1, entity2],
            scores=[0.9, 0.7]
        )
        
        top_entities = result.get_top_entities(n=10)
        assert len(top_entities) == 2  # Only 2 available
    
    def test_result_with_execution_time(self):
        """Test result with execution time"""
        query = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        result = GraphResult(
            query=query,
            execution_time_ms=15.5
        )
        
        assert result.execution_time_ms == 15.5
    
    def test_result_string_representations(self):
        """Test result string representations"""
        query = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        entity1 = Entity(id="e1", entity_type="Person")
        
        result = GraphResult(
            query=query,
            entities=[entity1],
            execution_time_ms=10.5
        )
        
        str_repr = str(result)
        assert "1" in str_repr  # entity_count
        assert "10.5" in str_repr or "time" in str_repr.lower()
        
        repr_str = repr(result)
        assert "GraphResult" in repr_str or "entities" in repr_str.lower()


class TestPathPattern:
    """Test PathPattern model"""
    
    def test_path_pattern_creation(self):
        """Test basic path pattern creation"""
        pattern = PathPattern(
            relation_types=["KNOWS", "WORKS_FOR"],
            max_depth=3
        )
        
        assert pattern.max_depth == 3
        assert "KNOWS" in pattern.relation_types
        assert pattern.direction == TraversalDirection.OUTGOING
    
    def test_path_pattern_with_entity_types(self):
        """Test path pattern with entity type constraints"""
        pattern = PathPattern(
            entity_types=["Person", "Company"],
            max_depth=2
        )
        
        assert "Person" in pattern.entity_types
        assert pattern.max_depth == 2
    
    def test_path_pattern_directions(self):
        """Test different traversal directions"""
        outgoing = PathPattern(direction=TraversalDirection.OUTGOING)
        incoming = PathPattern(direction=TraversalDirection.INCOMING)
        both = PathPattern(direction=TraversalDirection.BOTH)
        
        assert outgoing.direction == TraversalDirection.OUTGOING
        assert incoming.direction == TraversalDirection.INCOMING
        assert both.direction == TraversalDirection.BOTH
    
    def test_is_relation_allowed(self):
        """Test relation type checking"""
        # With relation types constraint
        pattern = PathPattern(relation_types=["KNOWS", "WORKS_FOR"])
        assert pattern.is_relation_allowed("KNOWS") is True
        assert pattern.is_relation_allowed("WORKS_FOR") is True
        assert pattern.is_relation_allowed("LIKES") is False
        
        # With required sequence
        pattern = PathPattern(required_relation_sequence=["KNOWS", "WORKS_FOR"])
        assert pattern.is_relation_allowed("KNOWS", depth=0) is True
        assert pattern.is_relation_allowed("WORKS_FOR", depth=1) is True
        assert pattern.is_relation_allowed("KNOWS", depth=1) is False
        assert pattern.is_relation_allowed("KNOWS", depth=2) is False  # Beyond sequence
        
        # No constraints - all allowed
        pattern = PathPattern()
        assert pattern.is_relation_allowed("ANY_RELATION") is True
    
    def test_is_entity_allowed(self):
        """Test entity checking"""
        # With excluded entities
        pattern = PathPattern(excluded_entity_ids={"e1", "e2"})
        assert pattern.is_entity_allowed("e1", "Person") is False
        assert pattern.is_entity_allowed("e3", "Person") is True
        
        # With entity type constraint
        pattern = PathPattern(entity_types=["Person"])
        assert pattern.is_entity_allowed("e1", "Person") is True
        assert pattern.is_entity_allowed("e2", "Company") is False
        
        # No constraints - all allowed
        pattern = PathPattern()
        assert pattern.is_entity_allowed("e1", "AnyType") is True
    
    def test_is_valid_path_length(self):
        """Test path length validation"""
        pattern = PathPattern(max_depth=3, min_path_length=1)
        assert pattern.is_valid_path_length(1) is True
        assert pattern.is_valid_path_length(2) is True
        assert pattern.is_valid_path_length(3) is True
        assert pattern.is_valid_path_length(4) is False
        assert pattern.is_valid_path_length(0) is False
        
        pattern = PathPattern(max_depth=5, min_path_length=2)
        assert pattern.is_valid_path_length(1) is False
        assert pattern.is_valid_path_length(2) is True
        assert pattern.is_valid_path_length(5) is True
    
    def test_should_continue_traversal(self):
        """Test traversal continuation check"""
        pattern = PathPattern(max_depth=3)
        assert pattern.should_continue_traversal(0) is True
        assert pattern.should_continue_traversal(1) is True
        assert pattern.should_continue_traversal(2) is True
        assert pattern.should_continue_traversal(3) is False
    
    def test_path_pattern_string_representation(self):
        """Test string representation"""
        pattern = PathPattern(
            relation_types=["KNOWS"],
            entity_types=["Person"],
            max_depth=3,
            allow_cycles=True,
            required_relation_sequence=["KNOWS", "WORKS_FOR"]
        )
        
        str_repr = str(pattern)
        assert "depth=3" in str_repr
        assert "KNOWS" in str_repr


class TestQueryStep:
    """Test QueryStep model"""
    
    def test_query_step_creation(self):
        """Test basic query step creation"""
        query = GraphQuery(query_type=QueryType.ENTITY_LOOKUP, entity_id="e1")
        step = QueryStep(
            step_id="step_1",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=query,
            description="Find entity e1"
        )
        
        assert step.step_id == "step_1"
        assert step.operation == QueryOperation.ENTITY_LOOKUP
        assert step.description == "Find entity e1"
        assert step.estimated_cost == 0.5  # default
    
    def test_query_step_with_dependencies(self):
        """Test query step with dependencies"""
        query = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        step = QueryStep(
            step_id="step_2",
            operation=QueryOperation.VECTOR_SEARCH,
            query=query,
            description="Search",
            depends_on=["step_1"],
            estimated_cost=0.8
        )
        
        assert "step_1" in step.depends_on
        assert step.estimated_cost == 0.8
    
    def test_query_step_metadata(self):
        """Test query step with metadata"""
        query = GraphQuery(query_type=QueryType.TRAVERSAL)
        step = QueryStep(
            step_id="step_1",
            operation=QueryOperation.TRAVERSAL,
            query=query,
            description="Traverse",
            metadata={"cache_key": "traverse_123"}
        )
        
        assert step.metadata["cache_key"] == "traverse_123"


class TestQueryPlan:
    """Test QueryPlan model"""
    
    def test_query_plan_creation(self):
        """Test basic query plan creation"""
        query = GraphQuery(query_type=QueryType.ENTITY_LOOKUP)
        step = QueryStep(
            step_id="step_1",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=query,
            description="Find entity"
        )
        
        plan = QueryPlan(
            plan_id="plan_1",
            original_query="Find entity e1",
            steps=[step]
        )
        
        assert plan.plan_id == "plan_1"
        assert plan.original_query == "Find entity e1"
        assert len(plan.steps) == 1
        assert plan.optimized is False
    
    def test_calculate_total_cost(self):
        """Test cost calculation"""
        query1 = GraphQuery(query_type=QueryType.ENTITY_LOOKUP)
        query2 = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        
        step1 = QueryStep(
            step_id="step_1",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=query1,
            description="Step 1",
            estimated_cost=0.3
        )
        step2 = QueryStep(
            step_id="step_2",
            operation=QueryOperation.VECTOR_SEARCH,
            query=query2,
            description="Step 2",
            estimated_cost=0.7
        )
        
        plan = QueryPlan(
            plan_id="plan_1",
            original_query="Test",
            steps=[step1, step2]
        )
        
        assert plan.calculate_total_cost() == 1.0
    
    def test_get_executable_steps(self):
        """Test getting executable steps"""
        query1 = GraphQuery(query_type=QueryType.ENTITY_LOOKUP)
        query2 = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        query3 = GraphQuery(query_type=QueryType.TRAVERSAL)
        
        step1 = QueryStep(
            step_id="step_1",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=query1,
            description="Step 1"
        )
        step2 = QueryStep(
            step_id="step_2",
            operation=QueryOperation.VECTOR_SEARCH,
            query=query2,
            description="Step 2",
            depends_on=["step_1"]
        )
        step3 = QueryStep(
            step_id="step_3",
            operation=QueryOperation.TRAVERSAL,
            query=query3,
            description="Step 3",
            depends_on=["step_1"]
        )
        
        plan = QueryPlan(
            plan_id="plan_1",
            original_query="Test",
            steps=[step1, step2, step3]
        )
        
        # Initially, only step_1 is executable
        executable = plan.get_executable_steps(set())
        assert len(executable) == 1
        assert executable[0].step_id == "step_1"
        
        # After step_1 completes, step_2 and step_3 are executable
        executable = plan.get_executable_steps({"step_1"})
        assert len(executable) == 2
        assert any(s.step_id == "step_2" for s in executable)
        assert any(s.step_id == "step_3" for s in executable)
        
        # Completed steps are not returned
        executable = plan.get_executable_steps({"step_1", "step_2"})
        assert len(executable) == 1
        assert executable[0].step_id == "step_3"
    
    def test_get_execution_order(self):
        """Test execution order calculation"""
        query1 = GraphQuery(query_type=QueryType.ENTITY_LOOKUP)
        query2 = GraphQuery(query_type=QueryType.VECTOR_SEARCH)
        query3 = GraphQuery(query_type=QueryType.TRAVERSAL)
        
        step1 = QueryStep(
            step_id="step_1",
            operation=QueryOperation.ENTITY_LOOKUP,
            query=query1,
            description="Step 1"
        )
        step2 = QueryStep(
            step_id="step_2",
            operation=QueryOperation.VECTOR_SEARCH,
            query=query2,
            description="Step 2",
            depends_on=["step_1"]
        )
        step3 = QueryStep(
            step_id="step_3",
            operation=QueryOperation.TRAVERSAL,
            query=query3,
            description="Step 3",
            depends_on=["step_1"]
        )
        
        plan = QueryPlan(
            plan_id="plan_1",
            original_query="Test",
            steps=[step1, step2, step3]
        )
        
        order = plan.get_execution_order()
        assert len(order) == 2
        assert order[0] == ["step_1"]  # First batch
        assert set(order[1]) == {"step_2", "step_3"}  # Can run in parallel


class TestEvidence:
    """Test Evidence model"""
    
    def test_evidence_creation(self):
        """Test basic evidence creation"""
        entity = Entity(id="e1", entity_type="Person")
        evidence = Evidence(
            evidence_id="ev_1",
            evidence_type=EvidenceType.ENTITY,
            entities=[entity],
            confidence=0.9
        )
        
        assert evidence.evidence_id == "ev_1"
        assert evidence.evidence_type == EvidenceType.ENTITY
        assert len(evidence.entities) == 1
        assert evidence.confidence == 0.9
    
    def test_evidence_combined_score(self):
        """Test combined score calculation"""
        evidence = Evidence(
            evidence_id="ev_1",
            evidence_type=EvidenceType.ENTITY,
            confidence=0.8,
            relevance_score=0.7
        )
        
        assert evidence.combined_score == 0.8 * 0.7
    
    def test_evidence_get_entity_ids(self):
        """Test getting entity IDs from evidence"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        
        evidence = Evidence(
            evidence_id="ev_1",
            evidence_type=EvidenceType.ENTITY,
            entities=[entity1, entity2]
        )
        
        entity_ids = evidence.get_entity_ids()
        assert "e1" in entity_ids
        assert "e2" in entity_ids
    
    def test_evidence_string_representation(self):
        """Test evidence string representation"""
        evidence = Evidence(
            evidence_id="ev_1",
            evidence_type=EvidenceType.PATH,
            explanation="Test evidence"
        )
        
        str_repr = str(evidence)
        assert "ev_1" in str_repr or "evidence" in str_repr.lower()


class TestReasoningResult:
    """Test ReasoningResult model"""
    
    def test_reasoning_result_creation(self):
        """Test basic reasoning result creation"""
        entity = Entity(id="e1", entity_type="Person")
        evidence = Evidence(
            evidence_id="ev_1",
            evidence_type=EvidenceType.ENTITY,
            entities=[entity]
        )
        
        result = ReasoningResult(
            query="What companies does Alice work at?",
            answer="Alice works at Company X",
            evidence=[evidence],
            confidence=0.85
        )
        
        assert result.query == "What companies does Alice work at?"
        assert result.answer == "Alice works at Company X"
        assert len(result.evidence) == 1
        assert result.confidence == 0.85
    
    def test_reasoning_result_evidence_count(self):
        """Test evidence count property"""
        evidence1 = Evidence(evidence_id="ev_1", evidence_type=EvidenceType.ENTITY)
        evidence2 = Evidence(evidence_id="ev_2", evidence_type=EvidenceType.ENTITY)
        
        result = ReasoningResult(
            query="Test query",
            answer="Test",
            evidence=[evidence1, evidence2]
        )
        
        assert result.evidence_count == 2
    
    def test_reasoning_result_has_answer(self):
        """Test has_answer property"""
        result_with_answer = ReasoningResult(query="Test", answer="Yes", evidence=[])
        result_no_answer = ReasoningResult(query="Test", answer="", evidence=[])
        
        assert result_with_answer.has_answer is True
        assert result_no_answer.has_answer is False
    
    def test_reasoning_result_get_top_evidence(self):
        """Test getting top evidence"""
        evidence1 = Evidence(
            evidence_id="ev_1",
            evidence_type=EvidenceType.ENTITY,
            confidence=0.9,
            relevance_score=0.8
        )
        evidence2 = Evidence(
            evidence_id="ev_2",
            evidence_type=EvidenceType.ENTITY,
            confidence=0.7,
            relevance_score=0.6
        )
        evidence3 = Evidence(
            evidence_id="ev_3",
            evidence_type=EvidenceType.ENTITY,
            confidence=0.8,
            relevance_score=0.7
        )
        
        result = ReasoningResult(
            query="Test query",
            answer="Test",
            evidence=[evidence1, evidence2, evidence3]
        )
        
        top = result.get_top_evidence(n=2)
        assert len(top) == 2
        assert top[0].evidence_id == "ev_1"  # Highest combined score
    
    def test_reasoning_result_reasoning_trace(self):
        """Test reasoning trace"""
        result = ReasoningResult(
            query="Test query",
            reasoning_trace=["Step 1: Find entities", "Step 2: Filter results"]
        )
        
        assert len(result.reasoning_trace) == 2
        trace_str = result.get_trace_string()
        assert "Step 1" in trace_str
        assert "Step 2" in trace_str
    
    def test_reasoning_result_string_representation(self):
        """Test string representation"""
        result = ReasoningResult(
            query="Test query",
            answer="Test answer",
            confidence=0.9,
            evidence=[Evidence(evidence_id="ev_1", evidence_type=EvidenceType.ENTITY)]
        )
        
        str_repr = str(result)
        assert "evidence=1" in str_repr or "1" in str_repr
        assert "confidence" in str_repr.lower() or "0.9" in str_repr


class TestInferenceRule:
    """Test InferenceRule model"""
    
    def test_inference_rule_creation(self):
        """Test basic inference rule creation"""
        rule = InferenceRule(
            rule_id="rule_1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="WORKS_FOR",
            description="Transitive works_for rule"
        )
        
        assert rule.rule_id == "rule_1"
        assert rule.rule_type == RuleType.TRANSITIVE
        assert rule.relation_type == "WORKS_FOR"
        assert rule.enabled is True
    
    def test_inference_rule_can_apply(self):
        """Test can_apply method"""
        rule = InferenceRule(
            rule_id="rule_1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="WORKS_FOR"
        )
        
        # Matching relation
        relation1 = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e2"
        )
        assert rule.can_apply(relation1) is True
        
        # Non-matching relation
        relation2 = Relation(
            id="r2",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        assert rule.can_apply(relation2) is False
        
        # Disabled rule
        rule.enabled = False
        assert rule.can_apply(relation1) is False
    
    def test_inference_rule_types(self):
        """Test different rule types"""
        transitive = InferenceRule(
            rule_id="r1",
            rule_type=RuleType.TRANSITIVE,
            relation_type="WORKS_FOR"
        )
        symmetric = InferenceRule(
            rule_id="r2",
            rule_type=RuleType.SYMMETRIC,
            relation_type="KNOWS"
        )
        custom = InferenceRule(
            rule_id="r3",
            rule_type=RuleType.CUSTOM,
            relation_type="CUSTOM"
        )
        
        assert transitive.rule_type == RuleType.TRANSITIVE
        assert symmetric.rule_type == RuleType.SYMMETRIC
        assert custom.rule_type == RuleType.CUSTOM


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

