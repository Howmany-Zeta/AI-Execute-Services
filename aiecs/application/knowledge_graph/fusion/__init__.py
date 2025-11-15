"""
Knowledge Fusion Components

Components for deduplicating, merging, and linking entities across documents.
"""

from aiecs.application.knowledge_graph.fusion.entity_deduplicator import (
    EntityDeduplicator,
)
from aiecs.application.knowledge_graph.fusion.entity_linker import EntityLinker
from aiecs.application.knowledge_graph.fusion.relation_deduplicator import (
    RelationDeduplicator,
)
from aiecs.application.knowledge_graph.fusion.knowledge_fusion import (
    KnowledgeFusion,
)

__all__ = [
    "EntityDeduplicator",
    "EntityLinker",
    "RelationDeduplicator",
    "KnowledgeFusion",
]
