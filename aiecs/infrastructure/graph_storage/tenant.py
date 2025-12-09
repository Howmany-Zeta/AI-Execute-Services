"""
Tenant Context Infrastructure for Multi-Tenancy Support

Provides tenant isolation mechanisms and context management for knowledge graph storage.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TenantIsolationMode(str, Enum):
    """
    Tenant isolation mode for multi-tenant deployments.

    - DISABLED: No tenant isolation; all data in shared namespace (backward compatible)
    - SHARED_SCHEMA: Shared database schema with tenant_id column filtering (PostgreSQL RLS, SQLite column filtering)
    - SEPARATE_SCHEMA: Separate database schemas per tenant (PostgreSQL schemas, SQLite databases)
    """

    DISABLED = "disabled"
    SHARED_SCHEMA = "shared_schema"
    SEPARATE_SCHEMA = "separate_schema"


@dataclass
class TenantContext:
    """
    Tenant context for multi-tenant operations.

    Carries tenant identification and isolation mode through storage operations.

    Attributes:
        tenant_id: Unique identifier for the tenant (alphanumeric, hyphens, underscores)
        isolation_mode: Tenant isolation mode (default: SHARED_SCHEMA)
        validate: Whether to validate tenant_id format (default: True)

    Example:
        ```python
        context = TenantContext(tenant_id="acme-corp", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)
        await graph_store.add_entity(entity, context=context)
        ```
    """

    tenant_id: str
    isolation_mode: TenantIsolationMode = TenantIsolationMode.SHARED_SCHEMA
    validate: bool = True

    def __post_init__(self) -> None:
        """Validate tenant_id format if validation is enabled."""
        if self.validate:
            validate_tenant_id(self.tenant_id)

    def __str__(self) -> str:
        return f"TenantContext(tenant_id={self.tenant_id}, mode={self.isolation_mode.value})"

    def __repr__(self) -> str:
        return (
            f"TenantContext(tenant_id='{self.tenant_id}', "
            f"isolation_mode=TenantIsolationMode.{self.isolation_mode.name})"
        )


class InvalidTenantIdError(ValueError):
    """
    Raised when tenant_id format is invalid.

    Tenant IDs must be alphanumeric strings with hyphens and underscores only.
    """

    def __init__(self, tenant_id: str, reason: str = ""):
        message = f"Invalid tenant_id format: '{tenant_id}'"
        if reason:
            message += f". {reason}"
        super().__init__(message)
        self.tenant_id = tenant_id
        self.reason = reason


class CrossTenantRelationError(ValueError):
    """
    Raised when attempting to create a relation between entities from different tenants.

    Relations must always be within the same tenant scope.
    """

    def __init__(self, source_tenant: Optional[str], target_tenant: Optional[str]):
        message = (
            f"Cannot create relation across tenants: "
            f"source_tenant={source_tenant}, target_tenant={target_tenant}"
        )
        super().__init__(message)
        self.source_tenant = source_tenant
        self.target_tenant = target_tenant


class CrossTenantFusionError(ValueError):
    """
    Raised when attempting to fuse entities from different tenants.

    Knowledge fusion operations must always be within the same tenant scope.
    """

    def __init__(self, tenant_ids: set):
        message = (
            f"Cannot fuse entities across tenants. "
            f"Found entities from multiple tenants: {sorted(tenant_ids)}"
        )
        super().__init__(message)
        self.tenant_ids = tenant_ids


class TenantContextRequiredError(ValueError):
    """
    Raised when a tenant context is required but not provided.

    In multi-tenant mode, certain operations require explicit tenant context.
    """

    def __init__(self, operation: str = "operation"):
        message = (
            f"TenantContext is required for {operation} in multi-tenant mode. "
            f"Please provide a TenantContext with tenant_id."
        )
        super().__init__(message)
        self.operation = operation


# Tenant ID validation pattern: alphanumeric, hyphens, underscores only
TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
TENANT_ID_MIN_LENGTH = 1
TENANT_ID_MAX_LENGTH = 255


def validate_tenant_id(tenant_id: str) -> str:
    """
    Validate tenant_id format.

    Tenant IDs must:
    - Be non-empty strings
    - Contain only alphanumeric characters, hyphens, and underscores
    - Be between 1 and 255 characters

    Args:
        tenant_id: Tenant ID to validate

    Returns:
        Validated tenant_id (unchanged if valid)

    Raises:
        InvalidTenantIdError: If tenant_id format is invalid

    Example:
        ```python
        validate_tenant_id("acme-corp")  # OK
        validate_tenant_id("acme_corp_123")  # OK
        validate_tenant_id("acme@corp")  # Raises InvalidTenantIdError
        ```
    """
    if not isinstance(tenant_id, str):
        raise InvalidTenantIdError(
            str(tenant_id), reason="tenant_id must be a string"
        )

    if not tenant_id:
        raise InvalidTenantIdError(
            tenant_id, reason="tenant_id cannot be empty"
        )

    if len(tenant_id) < TENANT_ID_MIN_LENGTH:
        raise InvalidTenantIdError(
            tenant_id,
            reason=f"tenant_id must be at least {TENANT_ID_MIN_LENGTH} character(s)",
        )

    if len(tenant_id) > TENANT_ID_MAX_LENGTH:
        raise InvalidTenantIdError(
            tenant_id,
            reason=f"tenant_id must be at most {TENANT_ID_MAX_LENGTH} characters",
        )

    if not TENANT_ID_PATTERN.match(tenant_id):
        raise InvalidTenantIdError(
            tenant_id,
            reason="tenant_id can only contain alphanumeric characters, hyphens, and underscores",
        )

    return tenant_id


def normalize_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
    """
    Normalize tenant_id (strip whitespace, convert to lowercase if needed).

    Args:
        tenant_id: Tenant ID to normalize

    Returns:
        Normalized tenant_id or None if input is None/empty

    Note:
        This function does not validate format. Use validate_tenant_id() for validation.
    """
    if tenant_id is None:
        return None

    normalized = tenant_id.strip()
    if not normalized:
        return None

    return normalized


class TenantAwareStorageResolver:
    """
    Resolves storage targets based on tenant context and isolation mode.
    
    This class provides unified path resolution for all GraphStore implementations,
    ensuring consistent tenant routing regardless of backend storage type.
    
    The resolver handles:
    - Table name resolution (base table, prefixed tables for separate-schema mode)
    - Connection/schema routing (PostgreSQL schemas, SQLite database files)
    - Tenant validation and normalization
    
    Example:
        ```python
        resolver = TenantAwareStorageResolver()
        
        # SHARED_SCHEMA mode: returns base table name
        context = TenantContext(tenant_id="acme", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)
        table = resolver.resolve_table_name("entities", context)  # "entities"
        
        # SEPARATE_SCHEMA mode: returns prefixed table name (for SQLite)
        context = TenantContext(tenant_id="acme", isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA)
        table = resolver.resolve_table_name("entities", context)  # "tenant_acme_entities"
        
        # Schema name resolution for PostgreSQL SEPARATE_SCHEMA mode
        schema = resolver.resolve_schema_name(context)  # "tenant_acme"
        ```
    """
    
    def __init__(self, table_prefix: str = "tenant", schema_prefix: str = "tenant"):
        """
        Initialize storage resolver.
        
        Args:
            table_prefix: Prefix for tenant-specific tables in SEPARATE_SCHEMA mode (default: "tenant")
            schema_prefix: Prefix for tenant-specific PostgreSQL schemas (default: "tenant")
        """
        self.table_prefix = table_prefix
        self.schema_prefix = schema_prefix
    
    def resolve_table_name(
        self, 
        base_table: str, 
        context: Optional[TenantContext] = None
    ) -> str:
        """
        Resolve table name based on tenant context and isolation mode.
        
        Resolution logic:
        - DISABLED or None context: returns base_table
        - SHARED_SCHEMA: returns base_table (filtering by tenant_id column)
        - SEPARATE_SCHEMA: returns "{prefix}_{tenant_id}_{base_table}"
        
        Args:
            base_table: Base table name (e.g., "entities", "relations")
            context: Optional tenant context
        
        Returns:
            Resolved table name
            
        Example:
            ```python
            resolver.resolve_table_name("entities", None)  # "entities"
            
            ctx = TenantContext("acme", TenantIsolationMode.SHARED_SCHEMA)
            resolver.resolve_table_name("entities", ctx)  # "entities"
            
            ctx = TenantContext("acme", TenantIsolationMode.SEPARATE_SCHEMA)
            resolver.resolve_table_name("entities", ctx)  # "tenant_acme_entities"
            ```
        """
        if context is None or context.isolation_mode == TenantIsolationMode.DISABLED:
            return base_table
        
        if context.isolation_mode == TenantIsolationMode.SHARED_SCHEMA:
            # Use base table with tenant_id column filtering
            return base_table
        
        if context.isolation_mode == TenantIsolationMode.SEPARATE_SCHEMA:
            # Use tenant-prefixed table name
            return f"{self.table_prefix}_{context.tenant_id}_{base_table}"
        
        return base_table
    
    def resolve_schema_name(self, context: Optional[TenantContext] = None) -> Optional[str]:
        """
        Resolve PostgreSQL schema name for SEPARATE_SCHEMA mode.
        
        Returns schema name for PostgreSQL search_path configuration.
        
        Args:
            context: Optional tenant context
        
        Returns:
            Schema name (e.g., "tenant_acme") or None if not in SEPARATE_SCHEMA mode
            
        Example:
            ```python
            ctx = TenantContext("acme", TenantIsolationMode.SEPARATE_SCHEMA)
            schema = resolver.resolve_schema_name(ctx)  # "tenant_acme"
            
            ctx = TenantContext("acme", TenantIsolationMode.SHARED_SCHEMA)
            schema = resolver.resolve_schema_name(ctx)  # None
            ```
        """
        if context is None or context.isolation_mode != TenantIsolationMode.SEPARATE_SCHEMA:
            return None
        
        return f"{self.schema_prefix}_{context.tenant_id}"
    
    def resolve_database_path(
        self, 
        base_path: str, 
        context: Optional[TenantContext] = None
    ) -> str:
        """
        Resolve SQLite database file path for SEPARATE_SCHEMA mode.
        
        In SEPARATE_SCHEMA mode, each tenant gets its own SQLite database file.
        
        Args:
            base_path: Base database path (e.g., "/data/graph.db")
            context: Optional tenant context
        
        Returns:
            Resolved database path
            
        Example:
            ```python
            ctx = TenantContext("acme", TenantIsolationMode.SEPARATE_SCHEMA)
            path = resolver.resolve_database_path("/data/graph.db", ctx)
            # "/data/tenant_acme.db"
            
            ctx = TenantContext("acme", TenantIsolationMode.SHARED_SCHEMA)
            path = resolver.resolve_database_path("/data/graph.db", ctx)
            # "/data/graph.db"
            ```
        """
        if context is None or context.isolation_mode != TenantIsolationMode.SEPARATE_SCHEMA:
            return base_path
        
        # Extract directory and base name from path
        import os
        directory = os.path.dirname(base_path)
        # Generate tenant-specific database file
        tenant_db = f"{self.table_prefix}_{context.tenant_id}.db"
        
        if directory:
            return os.path.join(directory, tenant_db)
        return tenant_db
    
    def should_filter_by_tenant_id(self, context: Optional[TenantContext] = None) -> bool:
        """
        Determine if queries should include tenant_id column filter.
        
        Returns True for SHARED_SCHEMA mode, False for SEPARATE_SCHEMA or DISABLED.
        
        Args:
            context: Optional tenant context
        
        Returns:
            True if queries should filter by tenant_id column, False otherwise
            
        Example:
            ```python
            ctx = TenantContext("acme", TenantIsolationMode.SHARED_SCHEMA)
            resolver.should_filter_by_tenant_id(ctx)  # True
            
            ctx = TenantContext("acme", TenantIsolationMode.SEPARATE_SCHEMA)
            resolver.should_filter_by_tenant_id(ctx)  # False (separate storage)
            ```
        """
        if context is None or context.isolation_mode == TenantIsolationMode.DISABLED:
            return False
        
        return context.isolation_mode == TenantIsolationMode.SHARED_SCHEMA
    
    def validate_context(self, context: Optional[TenantContext]) -> None:
        """
        Validate tenant context format and configuration.
        
        Args:
            context: Tenant context to validate
        
        Raises:
            InvalidTenantIdError: If tenant_id format is invalid
            
        Example:
            ```python
            ctx = TenantContext("acme-corp", TenantIsolationMode.SHARED_SCHEMA)
            resolver.validate_context(ctx)  # OK
            
            ctx = TenantContext("acme@corp", TenantIsolationMode.SHARED_SCHEMA)
            resolver.validate_context(ctx)  # Raises InvalidTenantIdError
            ```
        """
        if context is not None:
            validate_tenant_id(context.tenant_id)
