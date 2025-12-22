"""
Unit tests for knowledge graph schema management
"""

import pytest
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager


class TestPropertySchema:
    """Test PropertySchema"""
    
    def test_property_creation(self):
        """Test basic property schema creation"""
        prop = PropertySchema(
            name="age",
            property_type=PropertyType.INTEGER,
            required=True,
            min_value=0,
            max_value=150
        )
        
        assert prop.name == "age"
        assert prop.property_type == PropertyType.INTEGER
        assert prop.required is True
    
    def test_property_validation(self):
        """Test property value validation"""
        prop = PropertySchema(
            name="age",
            property_type=PropertyType.INTEGER,
            required=True,
            min_value=0,
            max_value=150
        )
        
        # Valid value
        assert prop.validate_value(25) is True
        
        # Invalid: too low
        with pytest.raises(ValueError):
            prop.validate_value(-5)
        
        # Invalid: too high
        with pytest.raises(ValueError):
            prop.validate_value(200)
        
        # Invalid: wrong type
        with pytest.raises(ValueError):
            prop.validate_value("not an integer")
    
    def test_property_allowed_values(self):
        """Test property with allowed values"""
        prop = PropertySchema(
            name="status",
            property_type=PropertyType.STRING,
            allowed_values=["active", "inactive", "pending"]
        )
        
        assert prop.validate_value("active") is True
        
        with pytest.raises(ValueError):
            prop.validate_value("invalid_status")
    
    def test_property_type_validation(self):
        """Test validation for different property types"""
        # STRING
        str_prop = PropertySchema(name="name", property_type=PropertyType.STRING)
        assert str_prop.validate_value("test") is True
        with pytest.raises(ValueError):
            str_prop.validate_value(123)
        
        # FLOAT
        float_prop = PropertySchema(name="price", property_type=PropertyType.FLOAT)
        assert float_prop.validate_value(3.14) is True
        assert float_prop.validate_value(5) is True  # int is valid for float
        with pytest.raises(ValueError):
            float_prop.validate_value("not a number")
        
        # BOOLEAN
        bool_prop = PropertySchema(name="active", property_type=PropertyType.BOOLEAN)
        assert bool_prop.validate_value(True) is True
        assert bool_prop.validate_value(False) is True
        with pytest.raises(ValueError):
            bool_prop.validate_value(1)
        
        # LIST
        list_prop = PropertySchema(name="tags", property_type=PropertyType.LIST)
        assert list_prop.validate_value([1, 2, 3]) is True
        with pytest.raises(ValueError):
            list_prop.validate_value("not a list")
        
        # DICT
        dict_prop = PropertySchema(name="metadata", property_type=PropertyType.DICT)
        assert dict_prop.validate_value({"key": "value"}) is True
        with pytest.raises(ValueError):
            dict_prop.validate_value("not a dict")
        
        # ANY (should accept any value)
        any_prop = PropertySchema(name="any_value", property_type=PropertyType.ANY)
        assert any_prop.validate_value("string") is True
        assert any_prop.validate_value(123) is True
        assert any_prop.validate_value(True) is True
        assert any_prop.validate_value([1, 2]) is True
    
    def test_property_none_value(self):
        """Test None value handling"""
        # Required property cannot be None
        required_prop = PropertySchema(name="name", property_type=PropertyType.STRING, required=True)
        with pytest.raises(ValueError, match="is required"):
            required_prop.validate_value(None)
        
        # Optional property can be None
        optional_prop = PropertySchema(name="age", property_type=PropertyType.INTEGER, required=False)
        assert optional_prop.validate_value(None) is True
    
    def test_property_string_representations(self):
        """Test string representations"""
        prop = PropertySchema(name="age", property_type=PropertyType.INTEGER, required=True)
        str_repr = str(prop)
        assert "age" in str_repr
        assert "integer" in str_repr.lower()
        assert "required" in str_repr.lower()
        
        repr_str = repr(prop)
        assert "age" in repr_str


class TestEntityType:
    """Test EntityType schema"""
    
    def test_entity_type_creation(self):
        """Test entity type creation"""
        entity_type = EntityType(
            name="Person",
            description="A person entity"
        )
        
        assert entity_type.name == "Person"
        assert entity_type.description == "A person entity"
        assert len(entity_type.properties) == 0
    
    def test_entity_type_with_properties(self):
        """Test entity type with properties"""
        name_prop = PropertySchema(name="name", property_type=PropertyType.STRING, required=True)
        age_prop = PropertySchema(name="age", property_type=PropertyType.INTEGER)
        
        entity_type = EntityType(
            name="Person",
            properties={
                "name": name_prop,
                "age": age_prop
            }
        )
        
        assert len(entity_type.properties) == 2
        assert entity_type.get_property("name") is not None
        assert entity_type.get_required_properties() == ["name"]
    
    def test_entity_type_property_validation(self):
        """Test entity type property validation"""
        entity_type = EntityType(
            name="Person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
                "age": PropertySchema(name="age", property_type=PropertyType.INTEGER)
            }
        )
        
        # Valid properties
        assert entity_type.validate_properties({"name": "Alice", "age": 30}) is True
        
        # Missing required property
        with pytest.raises(ValueError):
            entity_type.validate_properties({"age": 30})
    
    def test_entity_type_property_management(self):
        """Test add/remove/get property methods"""
        entity_type = EntityType(name="Person")
        
        # Add property
        name_prop = PropertySchema(name="name", property_type=PropertyType.STRING)
        entity_type.add_property(name_prop)
        assert entity_type.get_property("name") is not None
        assert "name" in entity_type.properties
        
        # Remove property
        entity_type.remove_property("name")
        assert entity_type.get_property("name") is None
        assert "name" not in entity_type.properties
        
        # Get non-existent property
        assert entity_type.get_property("missing") is None
    
    def test_entity_type_get_required_properties(self):
        """Test getting required properties"""
        entity_type = EntityType(
            name="Person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
                "age": PropertySchema(name="age", property_type=PropertyType.INTEGER, required=False),
                "email": PropertySchema(name="email", property_type=PropertyType.STRING, required=True)
            }
        )
        
        required = entity_type.get_required_properties()
        assert "name" in required
        assert "email" in required
        assert "age" not in required
        assert len(required) == 2
    
    def test_entity_type_validation_invalid_property_value(self):
        """Test validation with invalid property values"""
        entity_type = EntityType(
            name="Person",
            properties={
                "age": PropertySchema(name="age", property_type=PropertyType.INTEGER, min_value=0, max_value=150)
            }
        )
        
        # Invalid: wrong type
        with pytest.raises(ValueError):
            entity_type.validate_properties({"age": "not a number"})
        
        # Invalid: out of range
        with pytest.raises(ValueError):
            entity_type.validate_properties({"age": 200})
    
    def test_entity_type_with_parent_and_abstract(self):
        """Test entity type with parent type and abstract flag"""
        entity_type = EntityType(
            name="Person",
            parent_type="Entity",
            is_abstract=True
        )
        
        assert entity_type.parent_type == "Entity"
        assert entity_type.is_abstract is True
    
    def test_entity_type_string_representations(self):
        """Test string representations"""
        entity_type = EntityType(name="Person")
        str_repr = str(entity_type)
        assert "Person" in str_repr
        
        repr_str = repr(entity_type)
        assert "Person" in repr_str


class TestRelationType:
    """Test RelationType schema"""
    
    def test_relation_type_creation(self):
        """Test relation type creation"""
        relation_type = RelationType(
            name="WORKS_FOR",
            description="Employment relationship",
            source_entity_types=["Person"],
            target_entity_types=["Company"]
        )
        
        assert relation_type.name == "WORKS_FOR"
        assert relation_type.source_entity_types == ["Person"]
        assert relation_type.target_entity_types == ["Company"]
    
    def test_relation_type_entity_validation(self):
        """Test relation type entity type validation"""
        relation_type = RelationType(
            name="WORKS_FOR",
            source_entity_types=["Person"],
            target_entity_types=["Company"]
        )
        
        # Valid types
        assert relation_type.validate_entity_types("Person", "Company") is True
        
        # Invalid source type
        with pytest.raises(ValueError):
            relation_type.validate_entity_types("Animal", "Company")
        
        # Invalid target type
        with pytest.raises(ValueError):
            relation_type.validate_entity_types("Person", "Product")
    
    def test_relation_type_any_entity_types(self):
        """Test relation type with None entity types (any allowed)"""
        relation_type = RelationType(
            name="CONNECTED_TO",
            source_entity_types=None,
            target_entity_types=None
        )
        
        # Should accept any entity types
        assert relation_type.validate_entity_types("Person", "Company") is True
        assert relation_type.validate_entity_types("Animal", "Product") is True
    
    def test_relation_type_property_management(self):
        """Test add/remove/get property methods"""
        relation_type = RelationType(name="WORKS_FOR")
        
        # Add property
        role_prop = PropertySchema(name="role", property_type=PropertyType.STRING)
        relation_type.add_property(role_prop)
        assert relation_type.get_property("role") is not None
        
        # Remove property
        relation_type.remove_property("role")
        assert relation_type.get_property("role") is None
    
    def test_relation_type_validate_properties(self):
        """Test relation type property validation"""
        relation_type = RelationType(
            name="WORKS_FOR",
            properties={
                "role": PropertySchema(name="role", property_type=PropertyType.STRING, required=True),
                "since": PropertySchema(name="since", property_type=PropertyType.STRING, required=False)
            }
        )
        
        # Valid properties
        assert relation_type.validate_properties({"role": "Engineer", "since": "2020"}) is True
        
        # Missing required property
        with pytest.raises(ValueError):
            relation_type.validate_properties({"since": "2020"})
    
    def test_relation_type_symmetric_transitive(self):
        """Test symmetric and transitive flags"""
        relation_type = RelationType(
            name="KNOWS",
            is_symmetric=True,
            is_transitive=False
        )
        
        assert relation_type.is_symmetric is True
        assert relation_type.is_transitive is False
    
    def test_relation_type_string_representations(self):
        """Test string representations"""
        relation_type = RelationType(name="WORKS_FOR")
        str_repr = str(relation_type)
        assert "WORKS_FOR" in str_repr
        
        repr_str = repr(relation_type)
        assert "WORKS_FOR" in repr_str


class TestGraphSchema:
    """Test GraphSchema container"""
    
    def test_schema_creation(self):
        """Test schema creation"""
        schema = GraphSchema(version="1.0", description="Test schema")
        
        assert schema.version == "1.0"
        assert schema.description == "Test schema"
        assert len(schema.entity_types) == 0
        assert len(schema.relation_types) == 0
    
    def test_add_entity_type(self):
        """Test adding entity types"""
        schema = GraphSchema()
        person_type = EntityType(name="Person")
        
        schema.add_entity_type(person_type)
        assert schema.has_entity_type("Person")
        assert schema.get_entity_type("Person") is not None
        
        # Duplicate should raise error
        with pytest.raises(ValueError):
            schema.add_entity_type(person_type)
    
    def test_add_relation_type(self):
        """Test adding relation types"""
        schema = GraphSchema()
        knows_type = RelationType(name="KNOWS")
        
        schema.add_relation_type(knows_type)
        assert schema.has_relation_type("KNOWS")
        assert schema.get_relation_type("KNOWS") is not None
    
    def test_delete_entity_type_with_dependencies(self):
        """Test that deleting entity type checks for dependencies"""
        schema = GraphSchema()
        
        person_type = EntityType(name="Person")
        company_type = EntityType(name="Company")
        works_for = RelationType(
            name="WORKS_FOR",
            source_entity_types=["Person"],
            target_entity_types=["Company"]
        )
        
        schema.add_entity_type(person_type)
        schema.add_entity_type(company_type)
        schema.add_relation_type(works_for)
        
        # Should not allow deleting Person because it's referenced
        with pytest.raises(ValueError):
            schema.delete_entity_type("Person")
    
    def test_update_entity_type(self):
        """Test updating entity type"""
        schema = GraphSchema()
        person_type = EntityType(name="Person", description="Original")
        schema.add_entity_type(person_type)
        
        # Update
        updated_type = EntityType(name="Person", description="Updated")
        schema.update_entity_type(updated_type)
        
        assert schema.get_entity_type("Person").description == "Updated"
        
        # Update non-existent should fail
        with pytest.raises(ValueError):
            schema.update_entity_type(EntityType(name="NonExistent"))
    
    def test_update_relation_type(self):
        """Test updating relation type"""
        schema = GraphSchema()
        knows_type = RelationType(name="KNOWS", description="Original")
        schema.add_relation_type(knows_type)
        
        # Update
        updated_type = RelationType(name="KNOWS", description="Updated")
        schema.update_relation_type(updated_type)
        
        assert schema.get_relation_type("KNOWS").description == "Updated"
        
        # Update non-existent should fail
        with pytest.raises(ValueError):
            schema.update_relation_type(RelationType(name="NonExistent"))
    
    def test_delete_relation_type(self):
        """Test deleting relation type"""
        schema = GraphSchema()
        knows_type = RelationType(name="KNOWS")
        schema.add_relation_type(knows_type)
        
        assert schema.has_relation_type("KNOWS")
        schema.delete_relation_type("KNOWS")
        assert not schema.has_relation_type("KNOWS")
        
        # Delete non-existent should fail
        with pytest.raises(ValueError):
            schema.delete_relation_type("NonExistent")
    
    def test_delete_entity_type_not_found(self):
        """Test deleting non-existent entity type"""
        schema = GraphSchema()
        with pytest.raises(ValueError):
            schema.delete_entity_type("NonExistent")
    
    def test_get_entity_type_names(self):
        """Test getting entity type names"""
        schema = GraphSchema()
        schema.add_entity_type(EntityType(name="Person"))
        schema.add_entity_type(EntityType(name="Company"))
        
        names = schema.get_entity_type_names()
        assert "Person" in names
        assert "Company" in names
        assert len(names) == 2
    
    def test_get_relation_type_names(self):
        """Test getting relation type names"""
        schema = GraphSchema()
        schema.add_relation_type(RelationType(name="KNOWS"))
        schema.add_relation_type(RelationType(name="WORKS_FOR"))
        
        names = schema.get_relation_type_names()
        assert "KNOWS" in names
        assert "WORKS_FOR" in names
        assert len(names) == 2
    
    def test_get_entity_types_with_property(self):
        """Test getting entity types with a specific property"""
        schema = GraphSchema()
        
        person_type = EntityType(
            name="Person",
            properties={"name": PropertySchema(name="name", property_type=PropertyType.STRING)}
        )
        company_type = EntityType(
            name="Company",
            properties={"name": PropertySchema(name="name", property_type=PropertyType.STRING)}
        )
        product_type = EntityType(name="Product")  # No name property
        
        schema.add_entity_type(person_type)
        schema.add_entity_type(company_type)
        schema.add_entity_type(product_type)
        
        types_with_name = schema.get_entity_types_with_property("name")
        assert len(types_with_name) == 2
        assert any(t.name == "Person" for t in types_with_name)
        assert any(t.name == "Company" for t in types_with_name)
        
        types_with_price = schema.get_entity_types_with_property("price")
        assert len(types_with_price) == 0
    
    def test_get_relation_types_for_entities(self):
        """Test getting relation types for specific entity types"""
        schema = GraphSchema()
        
        works_for = RelationType(
            name="WORKS_FOR",
            source_entity_types=["Person"],
            target_entity_types=["Company"]
        )
        knows = RelationType(
            name="KNOWS",
            source_entity_types=["Person"],
            target_entity_types=["Person"]
        )
        any_rel = RelationType(name="CONNECTED_TO")  # No restrictions
        
        schema.add_relation_type(works_for)
        schema.add_relation_type(knows)
        schema.add_relation_type(any_rel)
        
        # Person -> Company: should include WORKS_FOR and CONNECTED_TO
        rels = schema.get_relation_types_for_entities("Person", "Company")
        assert len(rels) == 2
        assert any(r.name == "WORKS_FOR" for r in rels)
        assert any(r.name == "CONNECTED_TO" for r in rels)
        
        # Person -> Person: should include KNOWS and CONNECTED_TO
        rels = schema.get_relation_types_for_entities("Person", "Person")
        assert len(rels) == 2
        assert any(r.name == "KNOWS" for r in rels)
        assert any(r.name == "CONNECTED_TO" for r in rels)
    
    def test_graph_schema_string_representations(self):
        """Test string representations"""
        schema = GraphSchema(version="1.0")
        str_repr = str(schema)
        assert "1.0" in str_repr
        
        repr_str = repr(schema)
        assert "1.0" in repr_str


class TestSchemaManager:
    """Test SchemaManager service"""
    
    def test_manager_creation(self):
        """Test schema manager creation"""
        manager = SchemaManager()
        assert manager.schema is not None
        assert len(manager.list_entity_types()) == 0
    
    def test_create_entity_type(self):
        """Test creating entity type through manager"""
        manager = SchemaManager()
        person_type = EntityType(name="Person")
        
        manager.create_entity_type(person_type)
        assert "Person" in manager.list_entity_types()
        assert manager.get_entity_type("Person") is not None
    
    def test_validate_entity(self):
        """Test entity validation through manager"""
        manager = SchemaManager()
        
        entity_type = EntityType(
            name="Person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True)
            }
        )
        manager.create_entity_type(entity_type)
        
        # Valid entity
        assert manager.validate_entity("Person", {"name": "Alice"}) is True
        
        # Invalid entity (missing required property)
        with pytest.raises(ValueError):
            manager.validate_entity("Person", {})
    
    def test_transaction_support(self):
        """Test transaction support"""
        manager = SchemaManager()
        person_type = EntityType(name="Person")
        
        manager.create_entity_type(person_type)
        assert "Person" in manager.list_entity_types()
        
        # Begin transaction
        manager.begin_transaction()
        assert manager.is_in_transaction
        
        # Make changes
        company_type = EntityType(name="Company")
        manager.create_entity_type(company_type)
        assert "Company" in manager.list_entity_types()
        
        # Rollback
        manager.rollback()
        assert not manager.is_in_transaction
        assert "Company" not in manager.list_entity_types()
        assert "Person" in manager.list_entity_types()
    
    def test_update_entity_type(self):
        """Test updating entity type"""
        manager = SchemaManager()
        person_type = EntityType(name="Person", description="Original")
        manager.create_entity_type(person_type)
        
        updated_type = EntityType(name="Person", description="Updated")
        manager.update_entity_type(updated_type)
        
        assert manager.get_entity_type("Person").description == "Updated"
        
        # Update non-existent should fail
        with pytest.raises(ValueError):
            manager.update_entity_type(EntityType(name="NonExistent"))
    
    def test_delete_entity_type(self):
        """Test deleting entity type"""
        manager = SchemaManager()
        person_type = EntityType(name="Person")
        manager.create_entity_type(person_type)
        
        assert "Person" in manager.list_entity_types()
        manager.delete_entity_type("Person")
        assert "Person" not in manager.list_entity_types()
    
    def test_create_relation_type(self):
        """Test creating relation type"""
        manager = SchemaManager()
        knows_type = RelationType(name="KNOWS")
        
        manager.create_relation_type(knows_type)
        assert "KNOWS" in manager.list_relation_types()
        assert manager.get_relation_type("KNOWS") is not None
    
    def test_update_relation_type(self):
        """Test updating relation type"""
        manager = SchemaManager()
        knows_type = RelationType(name="KNOWS", description="Original")
        manager.create_relation_type(knows_type)
        
        updated_type = RelationType(name="KNOWS", description="Updated")
        manager.update_relation_type(updated_type)
        
        assert manager.get_relation_type("KNOWS").description == "Updated"
    
    def test_delete_relation_type(self):
        """Test deleting relation type"""
        manager = SchemaManager()
        knows_type = RelationType(name="KNOWS")
        manager.create_relation_type(knows_type)
        
        assert "KNOWS" in manager.list_relation_types()
        manager.delete_relation_type("KNOWS")
        assert "KNOWS" not in manager.list_relation_types()
    
    def test_validate_relation(self):
        """Test relation validation"""
        manager = SchemaManager()
        
        person_type = EntityType(name="Person")
        company_type = EntityType(name="Company")
        works_for_type = RelationType(
            name="WORKS_FOR",
            source_entity_types=["Person"],
            target_entity_types=["Company"],
            properties={
                "role": PropertySchema(name="role", property_type=PropertyType.STRING, required=True)
            }
        )
        
        manager.create_entity_type(person_type)
        manager.create_entity_type(company_type)
        manager.create_relation_type(works_for_type)
        
        # Valid relation
        assert manager.validate_relation("WORKS_FOR", "Person", "Company", {"role": "Engineer"}) is True
        
        # Invalid entity types
        with pytest.raises(ValueError):
            manager.validate_relation("WORKS_FOR", "Animal", "Company", {"role": "Engineer"})
        
        # Missing required property
        with pytest.raises(ValueError):
            manager.validate_relation("WORKS_FOR", "Person", "Company", {})
        
        # Non-existent relation type
        with pytest.raises(ValueError):
            manager.validate_relation("NonExistent", "Person", "Company", {})
    
    def test_save_and_load_schema(self, tmp_path):
        """Test saving and loading schema"""
        manager = SchemaManager()
        person_type = EntityType(name="Person", description="A person")
        manager.create_entity_type(person_type)
        
        # Save
        file_path = tmp_path / "schema.json"
        manager.save(str(file_path))
        assert file_path.exists()
        
        # Load
        loaded_manager = SchemaManager.load(str(file_path))
        assert "Person" in loaded_manager.list_entity_types()
        assert loaded_manager.get_entity_type("Person").description == "A person"
    
    def test_transaction_commit(self):
        """Test transaction commit"""
        manager = SchemaManager()
        manager.begin_transaction()
        
        company_type = EntityType(name="Company")
        manager.create_entity_type(company_type)
        
        # Commit
        manager.commit()
        assert not manager.is_in_transaction
        assert "Company" in manager.list_entity_types()
    
    def test_rollback_without_transaction(self):
        """Test rollback without active transaction"""
        manager = SchemaManager()
        with pytest.raises(RuntimeError, match="No active transaction"):
            manager.rollback()
    
    def test_schema_manager_with_custom_schema(self):
        """Test schema manager with custom schema"""
        custom_schema = GraphSchema(version="2.0", description="Custom")
        manager = SchemaManager(schema=custom_schema)
        
        assert manager.schema.version == "2.0"
        assert manager.schema.description == "Custom"
    
    def test_schema_manager_string_representations(self):
        """Test string representations"""
        manager = SchemaManager()
        str_repr = str(manager)
        assert "SchemaManager" in str_repr
        
        repr_str = repr(manager)
        assert "SchemaManager" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

