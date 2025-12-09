"""
Relation Domain Model

Represents an edge/relationship between two entities in the knowledge graph.
"""

from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

from aiecs.infrastructure.graph_storage.tenant import validate_tenant_id, InvalidTenantIdError, CrossTenantRelationError


class Relation(BaseModel):
    """
    Knowledge Graph Relation

    Represents a directed edge between two entities in the knowledge graph.

    Attributes:
        id: Unique identifier for the relation
        relation_type: Type of relation (e.g., "WORKS_FOR", "KNOWS")
        source_id: ID of the source entity
        target_id: ID of the target entity
        properties: Additional properties of the relation
        weight: Optional weight/strength of the relation (0.0-1.0)
        created_at: Creation timestamp
        source: Source of the relation data

    Example:
        ```python
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={"role": "Engineer", "since": "2020-01-01"},
            weight=1.0
        )
        ```
    """

    id: str = Field(..., description="Unique identifier for the relation")

    relation_type: str = Field(..., description="Type of the relation (e.g., 'WORKS_FOR', 'KNOWS')")

    source_id: str = Field(..., description="ID of the source entity")

    target_id: str = Field(..., description="ID of the target entity")

    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional properties of the relation",
    )

    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Weight/strength of the relation (0.0-1.0)",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when relation was created",
    )

    source: Optional[str] = Field(default=None, description="Source of the relation data")

    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier for multi-tenant isolation (alphanumeric, hyphens, underscores only)",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    @field_validator("source_id", "target_id")
    @classmethod
    def validate_entity_ids(cls, v: str) -> str:
        """Validate entity IDs are non-empty"""
        if not v or not v.strip():
            raise ValueError("Entity IDs must be non-empty strings")
        return v

    @field_validator("source_id")
    @classmethod
    def validate_no_self_loop(cls, v: str, info) -> str:
        """Prevent self-loops (optional validation)"""
        # Note: We allow self-loops for now, but this validator can be enabled if needed
        # if info.data.get('target_id') and v == info.data['target_id']:
        #     raise ValueError("Self-loops are not allowed (source_id == target_id)")
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_tenant_id_before(cls, data: Any) -> Any:
        """Validate tenant_id format before model creation"""
        # Pydantic converts keyword arguments to dict before calling model_validator
        if isinstance(data, dict):
            tenant_id = data.get("tenant_id")
            if tenant_id is not None:
                # Validate and raise InvalidTenantIdError directly
                # Note: Pydantic will wrap this in ValidationError, but the error info is preserved
                validate_tenant_id(tenant_id)
        return data

    def validate_tenant_consistency(self, source_entity_tenant_id: Optional[str], target_entity_tenant_id: Optional[str]) -> Optional[str]:
        """
        Validate that relation tenant_id matches source and target entity tenant_ids.

        This should be called when creating a relation to ensure tenant isolation.
        Returns the effective tenant_id that should be used for this relation.

        Args:
            source_entity_tenant_id: Tenant ID of the source entity
            target_entity_tenant_id: Tenant ID of the target entity

        Returns:
            The effective tenant_id for this relation (relation's tenant_id if set,
            otherwise inferred from entities). Callers should use this value to
            set the relation's tenant_id if needed.

        Raises:
            CrossTenantRelationError: If tenant IDs don't match
        """
        # If relation has tenant_id, it must match both entities
        if self.tenant_id is not None:
            if source_entity_tenant_id != self.tenant_id:
                raise CrossTenantRelationError(source_entity_tenant_id, self.tenant_id)
            if target_entity_tenant_id != self.tenant_id:
                raise CrossTenantRelationError(self.tenant_id, target_entity_tenant_id)
        
        # Both entities must have the same tenant_id (or both None)
        if source_entity_tenant_id != target_entity_tenant_id:
            raise CrossTenantRelationError(source_entity_tenant_id, target_entity_tenant_id)
        
        # Return the effective tenant_id (relation's own or inferred from entities)
        # Callers can use this to set the relation's tenant_id if needed
        return self.tenant_id if self.tenant_id is not None else source_entity_tenant_id
    
    def with_tenant_id(self, tenant_id: Optional[str]) -> "Relation":
        """
        Create a copy of this relation with a new tenant_id.
        
        This is the Pydantic-idiomatic way to create a modified copy
        without mutating the original instance.
        
        Args:
            tenant_id: The tenant_id to set on the new relation
            
        Returns:
            A new Relation instance with the updated tenant_id
        """
        return self.model_copy(update={"tenant_id": tenant_id})

    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a specific property value

        Args:
            key: Property key
            default: Default value if key not found

        Returns:
            Property value or default
        """
        return self.properties.get(key, default)

    def set_property(self, key: str, value: Any) -> None:
        """
        Set a property value

        Args:
            key: Property key
            value: Property value
        """
        self.properties[key] = value

    def reverse(self) -> "Relation":
        """
        Create a reversed relation (swap source and target)

        Returns:
            New Relation with swapped source and target
        """
        return Relation(
            id=f"{self.id}_reversed",
            relation_type=f"{self.relation_type}_REVERSE",
            source_id=self.target_id,
            target_id=self.source_id,
            properties=self.properties.copy(),
            weight=self.weight,
            created_at=self.created_at,
            source=self.source,
        )

    def __str__(self) -> str:
        return f"Relation({self.source_id} -[{self.relation_type}]-> {self.target_id})"

    def __repr__(self) -> str:
        return f"Relation(id='{self.id}', type='{self.relation_type}', " f"source='{self.source_id}', target='{self.target_id}', weight={self.weight})"
