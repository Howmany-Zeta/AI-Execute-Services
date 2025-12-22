"""
Unit tests for Relation model tenant_id field.
"""

import pytest
from pydantic import ValidationError

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.tenant import (
    InvalidTenantIdError,
    CrossTenantRelationError,
)


class TestRelationTenantId:
    """Test Relation tenant_id field."""

    def test_relation_without_tenant_id(self):
        """Test Relation can be created without tenant_id (backward compatible)."""
        relation = Relation(
            id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"
        )
        assert relation.tenant_id is None

    def test_relation_with_valid_tenant_id(self):
        """Test Relation with valid tenant_id."""
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2",
            tenant_id="acme-corp",
        )
        assert relation.tenant_id == "acme-corp"

    def test_relation_with_invalid_tenant_id(self):
        """Test Relation with invalid tenant_id raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Relation(
                id="r1",
                relation_type="KNOWS",
                source_id="e1",
                target_id="e2",
                tenant_id="invalid@id",
            )
        # Check that the cause is InvalidTenantIdError
        assert exc_info.value.errors()[0]["type"] == "value_error"
        # The error message should contain the InvalidTenantIdError message
        error_msg = str(exc_info.value.errors()[0]["msg"])
        assert "Invalid tenant_id format" in error_msg or "invalid@id" in error_msg

    def test_relation_tenant_id_validation(self):
        """Test tenant_id validation on Relation."""
        # Valid formats
        valid_ids = ["acme-corp", "acme_corp", "acme123", "123"]
        for tenant_id in valid_ids:
            relation = Relation(
                id="r1",
                relation_type="KNOWS",
                source_id="e1",
                target_id="e2",
                tenant_id=tenant_id,
            )
            assert relation.tenant_id == tenant_id

        # Invalid formats
        invalid_ids = ["acme@corp", "acme.corp", "acme corp"]
        for tenant_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                Relation(
                    id="r1",
                    relation_type="KNOWS",
                    source_id="e1",
                    target_id="e2",
                    tenant_id=tenant_id,
                )
            # Check that the error is related to tenant_id validation
            error_msg = str(exc_info.value.errors()[0]["msg"])
            assert "Invalid tenant_id format" in error_msg or tenant_id in error_msg

    def test_relation_serialization_with_tenant_id(self):
        """Test Relation serialization includes tenant_id."""
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2",
            tenant_id="acme-corp",
        )
        relation_dict = relation.model_dump()
        assert "tenant_id" in relation_dict
        assert relation_dict["tenant_id"] == "acme-corp"

    def test_relation_serialization_without_tenant_id(self):
        """Test Relation serialization handles None tenant_id."""
        relation = Relation(
            id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"
        )
        relation_dict = relation.model_dump()
        assert "tenant_id" in relation_dict
        assert relation_dict["tenant_id"] is None


class TestRelationTenantConsistency:
    """Test Relation tenant consistency validation."""

    def test_validate_same_tenant_entities(self):
        """Test validation passes when entities have same tenant_id."""
        relation = Relation(
            id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"
        )
        # Should not raise, returns effective tenant_id
        effective_tenant_id = relation.validate_tenant_consistency("acme-corp", "acme-corp")
        assert effective_tenant_id == "acme-corp"

    def test_validate_different_tenant_entities(self):
        """Test validation raises error when entities have different tenant_ids."""
        relation = Relation(
            id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"
        )
        with pytest.raises(CrossTenantRelationError):
            relation.validate_tenant_consistency("tenant1", "tenant2")

    def test_validate_none_tenant_entities(self):
        """Test validation passes when both entities have None tenant_id."""
        relation = Relation(
            id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"
        )
        # Should not raise, returns None for effective tenant_id
        effective_tenant_id = relation.validate_tenant_consistency(None, None)
        assert effective_tenant_id is None

    def test_validate_relation_tenant_mismatch_source(self):
        """Test validation raises error when relation tenant_id doesn't match source."""
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2",
            tenant_id="tenant1",
        )
        with pytest.raises(CrossTenantRelationError):
            relation.validate_tenant_consistency("tenant2", "tenant1")

    def test_validate_relation_tenant_mismatch_target(self):
        """Test validation raises error when relation tenant_id doesn't match target."""
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2",
            tenant_id="tenant1",
        )
        with pytest.raises(CrossTenantRelationError):
            relation.validate_tenant_consistency("tenant1", "tenant2")

    def test_validate_returns_inferred_tenant_id(self):
        """Test validation returns inferred tenant_id from entities."""
        relation = Relation(
            id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"
        )
        assert relation.tenant_id is None
        # Method returns the effective tenant_id but doesn't mutate
        effective_tenant_id = relation.validate_tenant_consistency("acme-corp", "acme-corp")
        assert effective_tenant_id == "acme-corp"
        # Original relation is not mutated
        assert relation.tenant_id is None

    def test_with_tenant_id_creates_copy(self):
        """Test with_tenant_id creates a new relation with updated tenant_id."""
        relation = Relation(
            id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"
        )
        assert relation.tenant_id is None
        
        # Create a copy with tenant_id set
        new_relation = relation.with_tenant_id("acme-corp")
        
        # Original is unchanged
        assert relation.tenant_id is None
        # New relation has the tenant_id
        assert new_relation.tenant_id == "acme-corp"
        # Other fields are preserved
        assert new_relation.id == relation.id
        assert new_relation.relation_type == relation.relation_type
        assert new_relation.source_id == relation.source_id
        assert new_relation.target_id == relation.target_id

    def test_validate_and_with_tenant_workflow(self):
        """Test typical workflow: validate then create copy with tenant_id."""
        relation = Relation(
            id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"
        )
        
        # Validate and get effective tenant_id
        effective_tenant_id = relation.validate_tenant_consistency("acme-corp", "acme-corp")
        
        # Create relation with the effective tenant_id
        tenant_relation = relation.with_tenant_id(effective_tenant_id)
        
        assert tenant_relation.tenant_id == "acme-corp"
