"""
Thinker Module

Contains the core planning services that handle the cognitive aspects of workflow planning:
- IntentParserService: Parses user intent and determines task categories
- TaskDecomposerService: Breaks down intent categories into executable sub-tasks
- SequencePlannerService: Generates DSL execution plans from task breakdowns

These services work together to transform user queries into structured, executable plans.
"""

from .mining import MiningService

__all__ = [
    "MiningService",
]
