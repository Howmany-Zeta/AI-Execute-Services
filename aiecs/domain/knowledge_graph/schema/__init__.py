"""
Knowledge Graph Schema Management

Schema definitions for entity types, relation types, and properties.
"""

from aiecs.domain.knowledge_graph.schema.property_schema import (
    PropertySchema,
    PropertyType,
)
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager

__all__ = [
    "PropertySchema",
    "PropertyType",
    "EntityType",
    "RelationType",
    "GraphSchema",
    "SchemaManager",
]
