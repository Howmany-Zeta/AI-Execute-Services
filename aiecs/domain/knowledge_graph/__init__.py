# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Knowledge Graph Domain Layer

This module contains the domain models and business logic for the knowledge graph capability.
It provides entity models, relation models, schema definitions, and graph query abstractions.
"""

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.query import GraphQuery, GraphResult

__all__ = [
    "Entity",
    "Relation",
    "Path",
    "GraphQuery",
    "GraphResult",
]
