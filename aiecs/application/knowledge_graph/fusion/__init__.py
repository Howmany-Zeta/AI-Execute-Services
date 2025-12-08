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
from aiecs.application.knowledge_graph.fusion.matching_config import (
    EntityTypeConfig,
    FusionMatchingConfig,
    load_matching_config,
    load_matching_config_from_dict,
    load_matching_config_from_json,
    load_matching_config_from_yaml,
    save_matching_config_to_dict,
    save_matching_config_to_json,
    save_matching_config_to_yaml,
    VALID_STAGES,
    DEFAULT_ENABLED_STAGES,
)
from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
    SimilarityPipeline,
    MatchStage,
    MatchResult,
    PipelineResult,
)
from aiecs.application.knowledge_graph.fusion.ab_testing import (
    ABTestingFramework,
    EvaluationMetrics,
    ExperimentResult,
)
from aiecs.application.knowledge_graph.fusion.evaluation_dataset import (
    EntityPair,
    EvaluationDataset,
    create_default_evaluation_dataset,
    create_minimal_evaluation_dataset,
)

__all__ = [
    "EntityDeduplicator",
    "EntityLinker",
    "RelationDeduplicator",
    "KnowledgeFusion",
    # Matching configuration
    "EntityTypeConfig",
    "FusionMatchingConfig",
    "load_matching_config",
    "load_matching_config_from_dict",
    "load_matching_config_from_json",
    "load_matching_config_from_yaml",
    "save_matching_config_to_dict",
    "save_matching_config_to_json",
    "save_matching_config_to_yaml",
    "VALID_STAGES",
    "DEFAULT_ENABLED_STAGES",
    # Similarity pipeline
    "SimilarityPipeline",
    "MatchStage",
    "MatchResult",
    "PipelineResult",
    # Evaluation and testing
    "ABTestingFramework",
    "EvaluationMetrics",
    "ExperimentResult",
    "EntityPair",
    "EvaluationDataset",
    "create_default_evaluation_dataset",
    "create_minimal_evaluation_dataset",
]
