# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Knowledge Graph Validators

Validators for entities and relations against schema.
"""

from aiecs.application.knowledge_graph.validators.relation_validator import (
    RelationValidator,
)

__all__ = [
    "RelationValidator",
]
