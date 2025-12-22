"""
Unit tests for Entity model tenant_id field.
"""

import pytest
from pydantic import ValidationError

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.tenant import InvalidTenantIdError


class TestEntityTenantId:
    """Test Entity tenant_id field."""

    def test_entity_without_tenant_id(self):
        """Test Entity can be created without tenant_id (backward compatible)."""
        entity = Entity(id="e1", entity_type="Person")
        assert entity.tenant_id is None

    def test_entity_with_valid_tenant_id(self):
        """Test Entity with valid tenant_id."""
        entity = Entity(id="e1", entity_type="Person", tenant_id="acme-corp")
        assert entity.tenant_id == "acme-corp"

    def test_entity_with_invalid_tenant_id(self):
        """Test Entity with invalid tenant_id raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Entity(id="e1", entity_type="Person", tenant_id="invalid@id")
        # Check that the cause is InvalidTenantIdError
        assert exc_info.value.errors()[0]["type"] == "value_error"
        # The error message should contain the InvalidTenantIdError message
        error_msg = str(exc_info.value.errors()[0]["msg"])
        assert "Invalid tenant_id format" in error_msg or "invalid@id" in error_msg

    def test_entity_tenant_id_validation(self):
        """Test tenant_id validation on Entity."""
        # Valid formats
        valid_ids = ["acme-corp", "acme_corp", "acme123", "123"]
        for tenant_id in valid_ids:
            entity = Entity(id="e1", entity_type="Person", tenant_id=tenant_id)
            assert entity.tenant_id == tenant_id

        # Invalid formats
        invalid_ids = ["acme@corp", "acme.corp", "acme corp"]
        for tenant_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                Entity(id="e1", entity_type="Person", tenant_id=tenant_id)
            # Check that the error is related to tenant_id validation
            error_msg = str(exc_info.value.errors()[0]["msg"])
            assert "Invalid tenant_id format" in error_msg or tenant_id in error_msg

    def test_entity_serialization_with_tenant_id(self):
        """Test Entity serialization includes tenant_id."""
        entity = Entity(id="e1", entity_type="Person", tenant_id="acme-corp")
        entity_dict = entity.model_dump()
        assert "tenant_id" in entity_dict
        assert entity_dict["tenant_id"] == "acme-corp"

    def test_entity_serialization_without_tenant_id(self):
        """Test Entity serialization handles None tenant_id."""
        entity = Entity(id="e1", entity_type="Person")
        entity_dict = entity.model_dump()
        assert "tenant_id" in entity_dict
        assert entity_dict["tenant_id"] is None

    def test_entity_json_serialization(self):
        """Test Entity JSON serialization includes tenant_id."""
        entity = Entity(id="e1", entity_type="Person", tenant_id="acme-corp")
        json_str = entity.model_dump_json()
        assert "tenant_id" in json_str
        assert "acme-corp" in json_str
