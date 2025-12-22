"""
Unit tests for tenant context infrastructure.
"""

import pytest

from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    InvalidTenantIdError,
    CrossTenantRelationError,
    validate_tenant_id,
    normalize_tenant_id,
)


class TestTenantIsolationMode:
    """Test TenantIsolationMode enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert TenantIsolationMode.DISABLED == "disabled"
        assert TenantIsolationMode.SHARED_SCHEMA == "shared_schema"
        assert TenantIsolationMode.SEPARATE_SCHEMA == "separate_schema"


class TestValidateTenantId:
    """Test tenant_id validation."""

    def test_valid_tenant_ids(self):
        """Test valid tenant_id formats."""
        valid_ids = [
            "acme-corp",
            "acme_corp",
            "acme123",
            "123",
            "a",
            "a" * 255,  # Max length
        ]
        for tenant_id in valid_ids:
            result = validate_tenant_id(tenant_id)
            assert result == tenant_id

    def test_invalid_tenant_ids(self):
        """Test invalid tenant_id formats."""
        invalid_cases = [
            ("", "empty string"),
            ("acme@corp", "contains @"),
            ("acme.corp", "contains ."),
            ("acme corp", "contains space"),
            ("acme/corp", "contains /"),
        ]

        for tenant_id, reason in invalid_cases:
            with pytest.raises(InvalidTenantIdError):
                validate_tenant_id(tenant_id)

    def test_tenant_id_too_long(self):
        """Test tenant_id exceeds max length."""
        too_long = "a" * 256  # Exceeds max length of 255
        with pytest.raises(InvalidTenantIdError) as exc_info:
            validate_tenant_id(too_long)
        assert "at most 255 characters" in str(exc_info.value)

    def test_tenant_id_non_string(self):
        """Test tenant_id must be string."""
        with pytest.raises(InvalidTenantIdError) as exc_info:
            validate_tenant_id(123)  # type: ignore
        assert "must be a string" in str(exc_info.value)


class TestNormalizeTenantId:
    """Test tenant_id normalization."""

    def test_normalize_valid(self):
        """Test normalization of valid tenant_id."""
        assert normalize_tenant_id("acme-corp") == "acme-corp"
        assert normalize_tenant_id("  acme-corp  ") == "acme-corp"
        assert normalize_tenant_id("ACME-CORP") == "ACME-CORP"  # No lowercase conversion

    def test_normalize_none(self):
        """Test normalization of None."""
        assert normalize_tenant_id(None) is None

    def test_normalize_empty(self):
        """Test normalization of empty/whitespace."""
        assert normalize_tenant_id("") is None
        assert normalize_tenant_id("   ") is None


class TestTenantContext:
    """Test TenantContext dataclass."""

    def test_create_with_valid_tenant_id(self):
        """Test creating TenantContext with valid tenant_id."""
        context = TenantContext(tenant_id="acme-corp")
        assert context.tenant_id == "acme-corp"
        assert context.isolation_mode == TenantIsolationMode.SHARED_SCHEMA
        assert context.validate is True

    def test_create_with_isolation_mode(self):
        """Test creating TenantContext with custom isolation mode."""
        context = TenantContext(
            tenant_id="acme-corp", isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
        )
        assert context.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA

    def test_create_with_validation_disabled(self):
        """Test creating TenantContext with validation disabled."""
        # Should not raise error even with invalid format
        context = TenantContext(tenant_id="invalid@id", validate=False)
        assert context.tenant_id == "invalid@id"

    def test_create_with_invalid_tenant_id(self):
        """Test creating TenantContext with invalid tenant_id raises error."""
        with pytest.raises(InvalidTenantIdError):
            TenantContext(tenant_id="invalid@id")

    def test_str_repr(self):
        """Test string representation."""
        context = TenantContext(tenant_id="acme-corp")
        str_repr = str(context)
        assert "acme-corp" in str_repr
        assert "SHARED_SCHEMA" in str_repr or "shared_schema" in str_repr

        repr_str = repr(context)
        assert "acme-corp" in repr_str
        assert "TenantContext" in repr_str


class TestCrossTenantRelationError:
    """Test CrossTenantRelationError exception."""

    def test_error_message(self):
        """Test error message format."""
        error = CrossTenantRelationError("tenant1", "tenant2")
        assert "tenant1" in str(error)
        assert "tenant2" in str(error)
        assert error.source_tenant == "tenant1"
        assert error.target_tenant == "tenant2"

    def test_error_with_none(self):
        """Test error with None tenant IDs."""
        error = CrossTenantRelationError(None, "tenant2")
        assert error.source_tenant is None
        assert error.target_tenant == "tenant2"
