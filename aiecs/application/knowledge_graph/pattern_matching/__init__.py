# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Pattern Matching Module

Provides graph pattern matching capabilities for custom query execution.

Phase: 3.3 - Full Custom Query Execution
"""

from aiecs.application.knowledge_graph.pattern_matching.pattern_matcher import (
    PatternMatcher,
    PatternMatch,
)
from aiecs.application.knowledge_graph.pattern_matching.query_executor import (
    CustomQueryExecutor,
)

__all__ = [
    "PatternMatcher",
    "PatternMatch",
    "CustomQueryExecutor",
]
