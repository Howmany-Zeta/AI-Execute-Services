"""
Unit tests for schema mapping functionality
"""

import pytest
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping,
    PropertyTransformation,
    TransformationType,
)
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType


class TestPropertyTransformation:
    """Test PropertyTransformation"""
    
    def test_rename_transformation(self):
        """Test rename transformation"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.RENAME,
            source_column="name",
            target_property="full_name"
        )
        
        row = {"name": "Alice", "age": 30}
        result = trans.apply(row)
        assert result == "Alice"
    
    def test_rename_missing_column(self):
        """Test rename with missing column"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.RENAME,
            source_column="missing",
            target_property="value"
        )
        
        row = {"name": "Alice"}
        result = trans.apply(row)
        assert result is None
    
    def test_type_cast_string_to_integer(self):
        """Test type cast from string to integer"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.TYPE_CAST,
            source_column="age",
            target_property="age",
            target_type=PropertyType.INTEGER
        )
        
        row = {"age": "30"}
        result = trans.apply(row)
        assert result == 30
        assert isinstance(result, int)
    
    def test_type_cast_string_to_float(self):
        """Test type cast from string to float"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.TYPE_CAST,
            source_column="price",
            target_property="price",
            target_type=PropertyType.FLOAT
        )
        
        row = {"price": "19.99"}
        result = trans.apply(row)
        assert result == 19.99
        assert isinstance(result, float)
    
    def test_type_cast_to_boolean(self):
        """Test type cast to boolean"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.TYPE_CAST,
            source_column="active",
            target_property="is_active",
            target_type=PropertyType.BOOLEAN
        )
        
        assert trans.apply({"active": "true"}) is True
        assert trans.apply({"active": "1"}) is True
        assert trans.apply({"active": "yes"}) is True
        assert trans.apply({"active": "false"}) is False
        assert trans.apply({"active": "0"}) is False
        assert trans.apply({"active": 1}) is True
        assert trans.apply({"active": 0}) is False
    
    def test_type_cast_to_list(self):
        """Test type cast to list"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.TYPE_CAST,
            source_column="tags",
            target_property="tags",
            target_type=PropertyType.LIST
        )
        
        # Already a list
        assert trans.apply({"tags": ["a", "b"]}) == ["a", "b"]
        
        # JSON string
        assert trans.apply({"tags": '["a", "b"]'}) == ["a", "b"]
        
        # Comma-separated string
        assert trans.apply({"tags": "a, b, c"}) == ["a", "b", "c"]
        
        # Single value
        assert trans.apply({"tags": "single"}) == ["single"]
    
    def test_type_cast_to_dict(self):
        """Test type cast to dict"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.TYPE_CAST,
            source_column="metadata",
            target_property="metadata",
            target_type=PropertyType.DICT
        )
        
        # Already a dict
        assert trans.apply({"metadata": {"key": "value"}}) == {"key": "value"}
        
        # JSON string
        assert trans.apply({"metadata": '{"key": "value"}'}) == {"key": "value"}
        
        # Single value
        assert trans.apply({"metadata": "value"}) == {"value": "value"}
    
    def test_type_cast_invalid(self):
        """Test type cast with invalid value"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.TYPE_CAST,
            source_column="age",
            target_property="age",
            target_type=PropertyType.INTEGER
        )
        
        with pytest.raises(ValueError):
            trans.apply({"age": "not a number"})
    
    def test_constant_transformation(self):
        """Test constant transformation"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.CONSTANT,
            target_property="status",
            constant_value="active"
        )
        
        row = {"name": "Alice"}
        result = trans.apply(row)
        assert result == "active"
    
    def test_compute_concat(self):
        """Test compute concat function"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.COMPUTE,
            source_column="first_name",
            target_property="full_name",
            compute_function="concat_space",
            compute_args=["last_name"]
        )
        
        row = {"first_name": "Alice", "last_name": "Smith"}
        result = trans.apply(row)
        assert result == "Alice Smith"
    
    def test_compute_sum(self):
        """Test compute sum function"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.COMPUTE,
            source_column="price1",
            target_property="total",
            compute_function="sum",
            compute_args=["price2", "price3"]
        )
        
        row = {"price1": 10, "price2": 20, "price3": 30}
        result = trans.apply(row)
        assert result == 60.0
    
    def test_compute_avg(self):
        """Test compute average function"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.COMPUTE,
            source_column="score1",
            target_property="avg_score",
            compute_function="avg",
            compute_args=["score2", "score3"]
        )
        
        row = {"score1": 10, "score2": 20, "score3": 30}
        result = trans.apply(row)
        assert result == 20.0
    
    def test_compute_max(self):
        """Test compute max function"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.COMPUTE,
            source_column="value1",
            target_property="max_value",
            compute_function="max",
            compute_args=["value2"]
        )
        
        row = {"value1": 10, "value2": 30}
        result = trans.apply(row)
        assert result == 30.0
    
    def test_compute_min(self):
        """Test compute min function"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.COMPUTE,
            source_column="value1",
            target_property="min_value",
            compute_function="min",
            compute_args=["value2"]
        )
        
        row = {"value1": 30, "value2": 10}
        result = trans.apply(row)
        assert result == 10.0
    
    def test_compute_unknown_function(self):
        """Test compute with unknown function"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.COMPUTE,
            source_column="value",
            target_property="result",
            compute_function="unknown_func"
        )
        
        with pytest.raises(ValueError, match="Unknown compute function"):
            trans.apply({"value": 10})
    
    def test_skip_transformation(self):
        """Test skip transformation"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.SKIP,
            target_property="skipped"
        )
        
        row = {"name": "Alice"}
        result = trans.apply(row)
        assert result is None
    
    def test_transformation_missing_source_column(self):
        """Test transformation with missing required source column"""
        trans = PropertyTransformation(
            transformation_type=TransformationType.RENAME,
            target_property="value"
            # Missing source_column
        )
        
        with pytest.raises(ValueError, match="source_column required"):
            trans.apply({"name": "Alice"})


class TestEntityMapping:
    """Test EntityMapping"""
    
    def test_entity_mapping_simple(self):
        """Test simple entity mapping"""
        mapping = EntityMapping(
            source_columns=["id", "name", "age"],
            entity_type="Person",
            property_mapping={
                "id": "id",
                "name": "name",
                "age": "age"
            }
        )
        
        row = {"id": "1", "name": "Alice", "age": 30}
        result = mapping.map_row_to_entity(row)
        
        assert result["id"] == "1"
        assert result["type"] == "Person"
        assert result["properties"]["name"] == "Alice"
        assert result["properties"]["age"] == 30
    
    def test_entity_mapping_with_id_column(self):
        """Test entity mapping with explicit ID column"""
        mapping = EntityMapping(
            source_columns=["emp_id", "name"],
            entity_type="Employee",
            id_column="emp_id"
        )
        
        row = {"emp_id": "E001", "name": "Bob"}
        result = mapping.map_row_to_entity(row)
        
        assert result["id"] == "E001"
    
    def test_entity_mapping_with_transformations(self):
        """Test entity mapping with transformations"""
        mapping = EntityMapping(
            source_columns=["first_name", "last_name", "age_str"],
            entity_type="Person",
            transformations=[
                PropertyTransformation(
                    transformation_type=TransformationType.COMPUTE,
                    source_column="first_name",
                    target_property="full_name",
                    compute_function="concat_space",
                    compute_args=["last_name"]
                ),
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="age_str",
                    target_property="age",
                    target_type=PropertyType.INTEGER
                )
            ]
        )
        
        row = {"first_name": "Alice", "last_name": "Smith", "age_str": "30"}
        result = mapping.map_row_to_entity(row)
        
        assert result["properties"]["full_name"] == "Alice Smith"
        assert result["properties"]["age"] == 30
    
    def test_entity_mapping_with_provided_id(self):
        """Test entity mapping with provided entity ID"""
        mapping = EntityMapping(
            source_columns=["name"],
            entity_type="Person"
        )
        
        row = {"name": "Alice"}
        result = mapping.map_row_to_entity(row, entity_id="custom-id-123")
        
        assert result["id"] == "custom-id-123"
    
    def test_entity_mapping_empty_source_columns(self):
        """Test entity mapping validation"""
        with pytest.raises(ValueError, match="source_columns cannot be empty"):
            EntityMapping(
                source_columns=[],
                entity_type="Person"
            )


class TestRelationMapping:
    """Test RelationMapping"""
    
    def test_relation_mapping_simple(self):
        """Test simple relation mapping"""
        mapping = RelationMapping(
            source_columns=["emp_id", "dept_id", "role"],
            relation_type="WORKS_IN",
            source_entity_column="emp_id",
            target_entity_column="dept_id",
            property_mapping={"role": "position"}
        )
        
        row = {"emp_id": "E001", "dept_id": "D001", "role": "Engineer"}
        result = mapping.map_row_to_relation(row)
        
        assert result["source_id"] == "E001"
        assert result["target_id"] == "D001"
        assert result["type"] == "WORKS_IN"
        assert result["properties"]["position"] == "Engineer"
    
    def test_relation_mapping_missing_entity_ids(self):
        """Test relation mapping with missing entity IDs"""
        mapping = RelationMapping(
            source_columns=["emp_id", "dept_id"],
            relation_type="WORKS_IN",
            source_entity_column="emp_id",
            target_entity_column="dept_id"
        )
        
        row = {"emp_id": "", "dept_id": "D001"}
        
        with pytest.raises(ValueError, match="Missing entity IDs"):
            mapping.map_row_to_relation(row)
    
    def test_relation_mapping_with_transformations(self):
        """Test relation mapping with transformations"""
        mapping = RelationMapping(
            source_columns=["source", "target", "since"],
            relation_type="KNOWS",
            source_entity_column="source",
            target_entity_column="target",
            transformations=[
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="since",
                    target_property="since_year",
                    target_type=PropertyType.INTEGER
                )
            ]
        )
        
        row = {"source": "P1", "target": "P2", "since": "2020"}
        result = mapping.map_row_to_relation(row)
        
        assert result["properties"]["since_year"] == 2020
    
    def test_relation_mapping_empty_source_columns(self):
        """Test relation mapping validation"""
        with pytest.raises(ValueError, match="source_columns cannot be empty"):
            RelationMapping(
                source_columns=[],
                relation_type="KNOWS",
                source_entity_column="source",
                target_entity_column="target"
            )
    
    def test_relation_mapping_empty_entity_columns(self):
        """Test relation mapping validation for entity columns"""
        with pytest.raises(ValueError, match="Entity column names cannot be empty"):
            RelationMapping(
                source_columns=["source", "target"],
                relation_type="KNOWS",
                source_entity_column="",
                target_entity_column="target"
            )


class TestSchemaMapping:
    """Test SchemaMapping"""
    
    def test_schema_mapping_creation(self):
        """Test schema mapping creation"""
        mapping = SchemaMapping(
            entity_mappings=[
                EntityMapping(
                    source_columns=["id", "name"],
                    entity_type="Person"
                )
            ],
            relation_mappings=[
                RelationMapping(
                    source_columns=["source", "target"],
                    relation_type="KNOWS",
                    source_entity_column="source",
                    target_entity_column="target"
                )
            ]
        )
        
        assert len(mapping.entity_mappings) == 1
        assert len(mapping.relation_mappings) == 1
    
    def test_schema_mapping_validation_valid(self):
        """Test schema mapping validation - valid mapping"""
        mapping = SchemaMapping(
            entity_mappings=[
                EntityMapping(
                    source_columns=["id", "name"],
                    entity_type="Person"
                )
            ]
        )
        
        errors = mapping.validate()
        assert len(errors) == 0
        assert mapping.is_valid() is True
    
    def test_schema_mapping_validation_duplicate_entity_type(self):
        """Test schema mapping validation - duplicate entity type"""
        mapping = SchemaMapping(
            entity_mappings=[
                EntityMapping(
                    source_columns=["id", "name"],
                    entity_type="Person"
                ),
                EntityMapping(
                    source_columns=["id", "name"],
                    entity_type="Person"  # Duplicate
                )
            ]
        )
        
        errors = mapping.validate()
        assert len(errors) > 0
        assert any("duplicate entity_type" in err for err in errors)
        assert mapping.is_valid() is False
    
    def test_schema_mapping_validation_duplicate_relation_type(self):
        """Test schema mapping validation - duplicate relation type"""
        mapping = SchemaMapping(
            relation_mappings=[
                RelationMapping(
                    source_columns=["source", "target"],
                    relation_type="KNOWS",
                    source_entity_column="source",
                    target_entity_column="target"
                ),
                RelationMapping(
                    source_columns=["source", "target"],
                    relation_type="KNOWS",  # Duplicate
                    source_entity_column="source",
                    target_entity_column="target"
                )
            ]
        )
        
        errors = mapping.validate()
        assert len(errors) > 0
        assert any("duplicate relation_type" in err for err in errors)
    
    def test_schema_mapping_validation_missing_entity_column(self):
        """Test schema mapping validation - missing entity column in source_columns"""
        mapping = SchemaMapping(
            relation_mappings=[
                RelationMapping(
                    source_columns=["other_col"],  # Missing source_entity_column
                    relation_type="KNOWS",
                    source_entity_column="source",
                    target_entity_column="target"
                )
            ]
        )
        
        errors = mapping.validate()
        assert len(errors) > 0
        assert any("must be in source_columns" in err for err in errors)
    
    def test_schema_mapping_validation_invalid_transformation(self):
        """Test schema mapping validation - invalid transformation"""
        mapping = SchemaMapping(
            entity_mappings=[
                EntityMapping(
                    source_columns=["name"],
                    entity_type="Person",
                    transformations=[
                        PropertyTransformation(
                            transformation_type=TransformationType.RENAME,
                            target_property="name"
                            # Missing source_column
                        )
                    ]
                )
            ]
        )
        
        errors = mapping.validate()
        assert len(errors) > 0
        assert any("source_column required" in err for err in errors)
    
    def test_schema_mapping_get_entity_mapping(self):
        """Test getting entity mapping by type"""
        mapping = SchemaMapping(
            entity_mappings=[
                EntityMapping(
                    source_columns=["id", "name"],
                    entity_type="Person"
                ),
                EntityMapping(
                    source_columns=["id", "name"],
                    entity_type="Company"
                )
            ]
        )
        
        person_mapping = mapping.get_entity_mapping("Person")
        assert person_mapping is not None
        assert person_mapping.entity_type == "Person"
        
        company_mapping = mapping.get_entity_mapping("Company")
        assert company_mapping is not None
        assert company_mapping.entity_type == "Company"
        
        missing_mapping = mapping.get_entity_mapping("Missing")
        assert missing_mapping is None
    
    def test_schema_mapping_get_relation_mapping(self):
        """Test getting relation mapping by type"""
        mapping = SchemaMapping(
            relation_mappings=[
                RelationMapping(
                    source_columns=["source", "target"],
                    relation_type="KNOWS",
                    source_entity_column="source",
                    target_entity_column="target"
                ),
                RelationMapping(
                    source_columns=["source", "target"],
                    relation_type="WORKS_FOR",
                    source_entity_column="source",
                    target_entity_column="target"
                )
            ]
        )
        
        knows_mapping = mapping.get_relation_mapping("KNOWS")
        assert knows_mapping is not None
        assert knows_mapping.relation_type == "KNOWS"
        
        works_for_mapping = mapping.get_relation_mapping("WORKS_FOR")
        assert works_for_mapping is not None
        assert works_for_mapping.relation_type == "WORKS_FOR"
        
        missing_mapping = mapping.get_relation_mapping("Missing")
        assert missing_mapping is None
    
    def test_schema_mapping_empty(self):
        """Test empty schema mapping"""
        mapping = SchemaMapping()
        
        assert len(mapping.entity_mappings) == 0
        assert len(mapping.relation_mappings) == 0
        assert mapping.is_valid() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

