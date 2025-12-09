"""
Entity Domain Model

Represents a node/entity in the knowledge graph with properties and embeddings.
"""

from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
import numpy as np

from aiecs.infrastructure.graph_storage.tenant import validate_tenant_id, InvalidTenantIdError


class Entity(BaseModel):
    """
    Knowledge Graph Entity

    Represents a node in the knowledge graph with:
    - Unique identifier
    - Entity type (e.g., "Person", "Company", "Product")
    - Properties (arbitrary key-value data)
    - Optional vector embedding for semantic search
    - Metadata (timestamps, source info)

    Example:
        ```python
        entity = Entity(
            id="person_001",
            entity_type="Person",
            properties={
                "name": "John Doe",
                "age": 30,
                "occupation": "Software Engineer"
            }
        )
        ```
    """

    id: str = Field(..., description="Unique identifier for the entity")

    entity_type: str = Field(..., description="Type of the entity (e.g., 'Person', 'Company')")

    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary properties associated with the entity",
    )

    embedding: Optional[list[float]] = Field(default=None, description="Vector embedding for semantic search")

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when entity was created",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when entity was last updated",
    )

    source: Optional[str] = Field(
        default=None,
        description="Source of the entity data (e.g., document ID)",
    )

    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier for multi-tenant isolation (alphanumeric, hyphens, underscores only)",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        # Allow arbitrary types for numpy arrays if needed
        arbitrary_types_allowed = True

    @field_validator("embedding")
    @classmethod
    def validate_embedding(cls, v: Optional[list[float]]) -> Optional[list[float]]:
        """Validate embedding is a list of floats"""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("Embedding must be a list of floats")
            if not all(isinstance(x, (int, float)) for x in v):
                raise ValueError("All embedding values must be numeric")
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

    def get_embedding_vector(self) -> Optional[np.ndarray]:
        """
        Get embedding as numpy array

        Returns:
            numpy array of embedding or None if no embedding
        """
        if self.embedding is None:
            return None
        return np.array(self.embedding, dtype=np.float32)

    def set_embedding_vector(self, vector: np.ndarray) -> None:
        """
        Set embedding from numpy array

        Args:
            vector: Numpy array of embedding values
        """
        self.embedding = vector.tolist()

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
        self.updated_at = datetime.utcnow()

    def __str__(self) -> str:
        return f"Entity(id={self.id}, type={self.entity_type})"

    def __repr__(self) -> str:
        return f"Entity(id='{self.id}', entity_type='{self.entity_type}', properties={len(self.properties)} keys)"
