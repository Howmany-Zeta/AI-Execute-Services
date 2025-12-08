"""
Per-Entity-Type Matching Configuration for Knowledge Fusion.

Provides configurable matching pipeline settings per entity type,
enabling precision/recall tradeoffs for different entity categories.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


# Valid matching stages
VALID_STAGES = {"exact", "alias", "abbreviation", "normalized", "semantic", "string"}

# Default stages enabled (string is the fallback)
DEFAULT_ENABLED_STAGES = ["exact", "alias", "abbreviation", "normalized", "semantic", "string"]


@dataclass
class EntityTypeConfig:
    """
    Configuration for a specific entity type.

    Defines which matching stages are enabled and threshold overrides
    for a particular entity type (e.g., Person, Organization, Concept).

    Example:
        ```python
        person_config = EntityTypeConfig(
            enabled_stages=["exact", "alias", "normalized"],
            thresholds={"alias_match_score": 0.99},
            semantic_enabled=False
        )
        ```
    """

    enabled_stages: List[str] = field(
        default_factory=lambda: DEFAULT_ENABLED_STAGES.copy()
    )
    semantic_enabled: bool = True
    thresholds: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate enabled stages."""
        invalid = set(self.enabled_stages) - VALID_STAGES
        if invalid:
            raise ValueError(
                f"Invalid matching stages: {invalid}. "
                f"Valid stages are: {VALID_STAGES}"
            )
        # Validate threshold values are in range
        for key, value in self.thresholds.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"Threshold '{key}' must be between 0.0 and 1.0, got {value}"
                )

    def merge_overrides(self, overrides: "EntityTypeConfig") -> None:
        """
        Merge threshold overrides from another config.

        Args:
            overrides: Config with override values
        """
        # Always apply enabled_stages from override, consistent with other properties
        self.enabled_stages = overrides.enabled_stages.copy()
        self.semantic_enabled = overrides.semantic_enabled
        self.thresholds.update(overrides.thresholds)

    def is_stage_enabled(self, stage: str) -> bool:
        """Check if a matching stage is enabled."""
        if stage == "semantic":
            return self.semantic_enabled and stage in self.enabled_stages
        return stage in self.enabled_stages

    def get_threshold(
        self, threshold_name: str, default: Optional[float] = None
    ) -> Optional[float]:
        """Get a threshold value, or default if not set."""
        return self.thresholds.get(threshold_name, default)


@dataclass
class FusionMatchingConfig:
    """
    Global fusion matching configuration with per-entity-type inheritance.

    Configuration follows strict inheritance order:
    1. System defaults (hardcoded fallbacks)
    2. Global configuration (this class)
    3. Per-entity-type configuration (entity_type_configs)
    4. Runtime overrides (method parameters)

    Example:
        ```python
        config = FusionMatchingConfig(
            alias_match_score=0.98,
            entity_type_configs={
                "Person": EntityTypeConfig(
                    enabled_stages=["exact", "alias", "normalized"],
                    semantic_enabled=False,
                    thresholds={"alias_match_score": 0.99}
                ),
                "Organization": EntityTypeConfig(
                    semantic_enabled=True,
                ),
                "_default": EntityTypeConfig(),  # Fallback for unknown types
            }
        )

        # Get effective config for an entity type
        person_config = config.get_config_for_type("Person")
        ```
    """

    # Global threshold defaults
    alias_match_score: float = 0.98
    abbreviation_match_score: float = 0.95
    normalization_match_score: float = 0.90
    semantic_threshold: float = 0.85
    string_similarity_threshold: float = 0.80

    # Default enabled stages
    enabled_stages: List[str] = field(
        default_factory=lambda: DEFAULT_ENABLED_STAGES.copy()
    )

    # Whether semantic matching is enabled globally
    semantic_enabled: bool = True

    # Per-entity-type configurations
    entity_type_configs: Dict[str, EntityTypeConfig] = field(default_factory=dict)

    # Configuration source tracking for debugging
    _config_sources: Dict[str, str] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __post_init__(self):
        """Validate configuration."""
        invalid = set(self.enabled_stages) - VALID_STAGES
        if invalid:
            raise ValueError(
                f"Invalid matching stages: {invalid}. "
                f"Valid stages are: {VALID_STAGES}"
            )
        self._validate_thresholds()

    def _validate_thresholds(self) -> None:
        """Validate all threshold values are in range [0.0, 1.0]."""
        thresholds = {
            "alias_match_score": self.alias_match_score,
            "abbreviation_match_score": self.abbreviation_match_score,
            "normalization_match_score": self.normalization_match_score,
            "semantic_threshold": self.semantic_threshold,
            "string_similarity_threshold": self.string_similarity_threshold,
        }
        for name, value in thresholds.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"Threshold '{name}' must be between 0.0 and 1.0, got {value}"
                )

    def get_config_for_type(self, entity_type: str) -> EntityTypeConfig:
        """
        Get effective config for entity type with inheritance.

        Resolution order:
        1. Start with global defaults
        2. Apply per-type overrides if exists
        3. Fall back to _default config if type not found

        Args:
            entity_type: Entity type name (e.g., "Person", "Organization")

        Returns:
            Effective EntityTypeConfig for the type
        """
        # Start with global defaults
        effective = EntityTypeConfig(
            enabled_stages=self.enabled_stages.copy(),
            semantic_enabled=self.semantic_enabled,
            thresholds={
                "alias_match_score": self.alias_match_score,
                "abbreviation_match_score": self.abbreviation_match_score,
                "normalization_match_score": self.normalization_match_score,
                "semantic_threshold": self.semantic_threshold,
                "string_similarity_threshold": self.string_similarity_threshold,
            },
        )

        # Apply per-type overrides (if exists)
        if entity_type in self.entity_type_configs:
            type_config = self.entity_type_configs[entity_type]
            effective.merge_overrides(type_config)
            self._log_config_source(entity_type, "per-type")
        elif "_default" in self.entity_type_configs:
            effective.merge_overrides(self.entity_type_configs["_default"])
            self._log_config_source(entity_type, "_default")
        else:
            self._log_config_source(entity_type, "global")

        return effective

    def _log_config_source(self, entity_type: str, source: str) -> None:
        """Log configuration source for debugging."""
        self._config_sources[entity_type] = source
        logger.debug(f"Config for '{entity_type}' resolved from: {source}")

    def get_global_thresholds(self) -> Dict[str, float]:
        """Get all global threshold values."""
        return {
            "alias_match_score": self.alias_match_score,
            "abbreviation_match_score": self.abbreviation_match_score,
            "normalization_match_score": self.normalization_match_score,
            "semantic_threshold": self.semantic_threshold,
            "string_similarity_threshold": self.string_similarity_threshold,
        }

    def add_entity_type_config(
        self, entity_type: str, config: EntityTypeConfig
    ) -> None:
        """
        Add or update configuration for an entity type.

        Args:
            entity_type: Entity type name
            config: Configuration for the type
        """
        self.entity_type_configs[entity_type] = config
        logger.info(f"Added config for entity type: {entity_type}")

    def remove_entity_type_config(self, entity_type: str) -> bool:
        """
        Remove configuration for an entity type.

        Args:
            entity_type: Entity type to remove

        Returns:
            True if config was removed, False if not found
        """
        if entity_type in self.entity_type_configs:
            del self.entity_type_configs[entity_type]
            return True
        return False

    def get_configured_entity_types(self) -> List[str]:
        """Get list of entity types with explicit configurations."""
        return list(self.entity_type_configs.keys())

    def get_config_sources(self) -> Dict[str, str]:
        """Get mapping of entity types to their config sources (for debugging)."""
        return dict(self._config_sources)


def load_matching_config_from_dict(data: Dict[str, Any]) -> FusionMatchingConfig:
    """
    Load FusionMatchingConfig from a dictionary.

    Expected format:
    ```python
    {
        "alias_match_score": 0.98,
        "abbreviation_match_score": 0.95,
        "normalization_match_score": 0.90,
        "semantic_threshold": 0.85,
        "string_similarity_threshold": 0.80,
        "enabled_stages": ["exact", "alias", "abbreviation", "normalized", "semantic"],
        "semantic_enabled": true,
        "entity_types": {
            "Person": {
                "enabled_stages": ["exact", "alias", "normalized"],
                "semantic_enabled": false,
                "thresholds": {"alias_match_score": 0.99}
            },
            "_default": {
                "enabled_stages": ["exact", "alias", "abbreviation", "normalized", "semantic"],
                "semantic_enabled": true,
                "thresholds": {}
            }
        }
    }
    ```

    Args:
        data: Configuration dictionary

    Returns:
        FusionMatchingConfig instance
    """
    if data is None:
        raise ValueError("Configuration data cannot be None")

    # Extract global settings
    global_settings = {
        k: v
        for k, v in data.items()
        if k not in ("entity_types", "entity_type_configs")
    }

    # Parse entity type configs
    entity_type_configs: Dict[str, EntityTypeConfig] = {}
    # Handle None values: use 'or' operator to fallback to empty dict if value is None
    entity_types_data = data.get("entity_types") or data.get("entity_type_configs") or {}

    for entity_type, type_data in entity_types_data.items():
        # Skip None values - they represent missing or invalid configs
        if type_data is None:
            continue
        
        entity_type_configs[entity_type] = EntityTypeConfig(
            enabled_stages=type_data.get("enabled_stages", DEFAULT_ENABLED_STAGES.copy()),
            semantic_enabled=type_data.get("semantic_enabled", True),
            thresholds=type_data.get("thresholds", {}),
        )

    return FusionMatchingConfig(
        alias_match_score=global_settings.get("alias_match_score", 0.98),
        abbreviation_match_score=global_settings.get("abbreviation_match_score", 0.95),
        normalization_match_score=global_settings.get("normalization_match_score", 0.90),
        semantic_threshold=global_settings.get("semantic_threshold", 0.85),
        string_similarity_threshold=global_settings.get("string_similarity_threshold", 0.80),
        enabled_stages=global_settings.get("enabled_stages", DEFAULT_ENABLED_STAGES.copy()),
        semantic_enabled=global_settings.get("semantic_enabled", True),
        entity_type_configs=entity_type_configs,
    )


def load_matching_config_from_json(filepath: str) -> FusionMatchingConfig:
    """
    Load FusionMatchingConfig from a JSON file.

    Args:
        filepath: Path to JSON configuration file

    Returns:
        FusionMatchingConfig instance

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = load_matching_config_from_dict(data)
    logger.info(f"Loaded matching config from JSON: {filepath}")
    return config


def load_matching_config_from_yaml(filepath: str) -> FusionMatchingConfig:
    """
    Load FusionMatchingConfig from a YAML file.

    Args:
        filepath: Path to YAML configuration file

    Returns:
        FusionMatchingConfig instance

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If file is not valid YAML
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"YAML file is empty or contains only null: {filepath}")

    config = load_matching_config_from_dict(data)
    logger.info(f"Loaded matching config from YAML: {filepath}")
    return config


def load_matching_config(filepath: str) -> FusionMatchingConfig:
    """
    Load FusionMatchingConfig from file (auto-detects format).

    Supports JSON (.json) and YAML (.yaml, .yml) formats.

    Args:
        filepath: Path to configuration file

    Returns:
        FusionMatchingConfig instance

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is not supported
    """
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == ".json":
        return load_matching_config_from_json(filepath)
    elif suffix in (".yaml", ".yml"):
        return load_matching_config_from_yaml(filepath)
    else:
        raise ValueError(
            f"Unsupported config file format: {suffix}. "
            f"Supported formats: .json, .yaml, .yml"
        )


def save_matching_config_to_dict(config: FusionMatchingConfig) -> Dict[str, Any]:
    """
    Convert FusionMatchingConfig to dictionary.

    Args:
        config: Configuration to convert

    Returns:
        Dictionary representation
    """
    entity_types = {}
    for entity_type, type_config in config.entity_type_configs.items():
        entity_types[entity_type] = {
            "enabled_stages": type_config.enabled_stages,
            "semantic_enabled": type_config.semantic_enabled,
            "thresholds": type_config.thresholds,
        }

    return {
        "alias_match_score": config.alias_match_score,
        "abbreviation_match_score": config.abbreviation_match_score,
        "normalization_match_score": config.normalization_match_score,
        "semantic_threshold": config.semantic_threshold,
        "string_similarity_threshold": config.string_similarity_threshold,
        "enabled_stages": config.enabled_stages,
        "semantic_enabled": config.semantic_enabled,
        "entity_types": entity_types,
    }


def save_matching_config_to_json(
    config: FusionMatchingConfig, filepath: str
) -> None:
    """
    Save FusionMatchingConfig to JSON file.

    Args:
        config: Configuration to save
        filepath: Path to output file
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = save_matching_config_to_dict(config)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved matching config to JSON: {filepath}")


def save_matching_config_to_yaml(
    config: FusionMatchingConfig, filepath: str
) -> None:
    """
    Save FusionMatchingConfig to YAML file.

    Args:
        config: Configuration to save
        filepath: Path to output file
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = save_matching_config_to_dict(config)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Saved matching config to YAML: {filepath}")
