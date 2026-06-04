# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""L2 knowledge graph integration shell (factory + NoOp; private backend optional)."""

from aiecs.infrastructure.knowledge.graph_store_factory import (
    create_graph_store,
    resolve_kg_enabled,
)
from aiecs.infrastructure.knowledge.graph_store_protocol import GraphStoreProtocol
from aiecs.infrastructure.knowledge.noop_graph_store import NoOpGraphStore

__all__ = [
    "GraphStoreProtocol",
    "NoOpGraphStore",
    "create_graph_store",
    "resolve_kg_enabled",
]
