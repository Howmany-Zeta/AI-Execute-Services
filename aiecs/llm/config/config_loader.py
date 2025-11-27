"""
Configuration loader for LLM models.

This module provides a singleton configuration loader that loads and manages
LLM model configurations from YAML files with support for hot-reloading.
"""

import logging
import os
from pathlib import Path
from typing import Optional
import yaml
from threading import Lock

from aiecs.llm.config.model_config import (
    LLMModelsConfig,
    ProviderConfig,
    ModelConfig,
)

logger = logging.getLogger(__name__)


class LLMConfigLoader:
    """
    Singleton configuration loader for LLM models.

    Supports:
    - Loading configuration from YAML files
    - Hot-reloading (manual refresh)
    - Thread-safe access
    - Caching for performance
    """

    _instance: Optional["LLMConfigLoader"] = None
    _lock = Lock()
    _config_lock = Lock()
    _initialized: bool = False

    def __new__(cls):
        """Ensure singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the configuration loader"""
        if self._initialized:
            return

        self._config: Optional[LLMModelsConfig] = None
        self._config_path: Optional[Path] = None
        self._initialized = True
        logger.info("LLMConfigLoader initialized")

    def _find_config_file(self) -> Path:
        """
        Find the configuration file.

        Search order:
        1. Settings llm_models_config_path
        2. Environment variable LLM_MODELS_CONFIG
        3. aiecs/config/llm_models.yaml
        4. config/llm_models.yaml
        """
        # Check settings first
        try:
            from aiecs.config.config import get_settings

            settings = get_settings()
            if settings.llm_models_config_path:
                path = Path(settings.llm_models_config_path)
                if path.exists():
                    logger.info(f"Using LLM config from settings: {path}")
                    return path
                else:
                    logger.warning(f"Settings llm_models_config_path does not exist: {path}")
        except Exception as e:
            logger.debug(f"Could not load settings: {e}")

        # Check environment variable
        env_path = os.environ.get("LLM_MODELS_CONFIG")
        if env_path:
            path = Path(env_path)
            if path.exists():
                logger.info(f"Using LLM config from environment: {path}")
                return path
            else:
                logger.warning(f"LLM_MODELS_CONFIG path does not exist: {path}")

        # Check standard locations
        current_dir = Path(__file__).parent.parent  # aiecs/

        # Try aiecs/config/llm_models.yaml
        config_path1 = current_dir / "config" / "llm_models.yaml"
        if config_path1.exists():
            logger.info(f"Using LLM config from: {config_path1}")
            return config_path1

        # Try config/llm_models.yaml (relative to project root)
        config_path2 = current_dir.parent / "config" / "llm_models.yaml"
        if config_path2.exists():
            logger.info(f"Using LLM config from: {config_path2}")
            return config_path2

        # Default to the first path even if it doesn't exist
        logger.warning(f"LLM config file not found, using default path: {config_path1}")
        return config_path1

    def load_config(self, config_path: Optional[Path] = None) -> LLMModelsConfig:
        """
        Load configuration from YAML file.

        Args:
            config_path: Optional path to configuration file. If not provided,
                        will search in standard locations.

        Returns:
            LLMModelsConfig: Loaded and validated configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        with self._config_lock:
            if config_path is None:
                config_path = self._find_config_file()
            else:
                config_path = Path(config_path)

            if not config_path.exists():
                raise FileNotFoundError(f"LLM models configuration file not found: {config_path}\n" f"Please create the configuration file or set LLM_MODELS_CONFIG environment variable.")

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)

                if not config_data:
                    raise ValueError("Configuration file is empty")

                # Validate and parse using Pydantic
                self._config = LLMModelsConfig(**config_data)
                self._config_path = config_path

                logger.info(f"Loaded LLM configuration from {config_path}: " f"{len(self._config.providers)} providers, " f"{sum(len(p.models) for p in self._config.providers.values())} models")

                return self._config

            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in configuration file: {e}")
            except Exception as e:
                raise ValueError(f"Failed to load configuration: {e}")

    def reload_config(self) -> LLMModelsConfig:
        """
        Reload configuration from the current config file.

        This supports the hybrid loading mode - configuration is loaded at startup
        but can be manually refreshed without restarting the application.

        Returns:
            LLMModelsConfig: Reloaded configuration
        """
        logger.info("Reloading LLM configuration...")
        return self.load_config(self._config_path)

    def get_config(self) -> LLMModelsConfig:
        """
        Get the current configuration.

        Loads configuration on first access if not already loaded.

        Returns:
            LLMModelsConfig: Current configuration
        """
        if self._config is None:
            self.load_config()
        # After load_config(), _config should never be None
        if self._config is None:
            raise RuntimeError("Failed to load LLM configuration")
        return self._config

    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider (e.g., "Vertex", "OpenAI")

        Returns:
            ProviderConfig if found, None otherwise
        """
        config = self.get_config()
        return config.get_provider_config(provider_name)

    def get_model_config(self, provider_name: str, model_name: str) -> Optional[ModelConfig]:
        """
        Get configuration for a specific model.

        Args:
            provider_name: Name of the provider
            model_name: Name of the model (or alias)

        Returns:
            ModelConfig if found, None otherwise
        """
        config = self.get_config()
        return config.get_model_config(provider_name, model_name)

    def get_default_model(self, provider_name: str) -> Optional[str]:
        """
        Get the default model name for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Default model name if found, None otherwise
        """
        provider_config = self.get_provider_config(provider_name)
        if provider_config:
            return provider_config.default_model
        return None

    def is_loaded(self) -> bool:
        """Check if configuration has been loaded"""
        return self._config is not None

    def get_config_path(self) -> Optional[Path]:
        """Get the path to the current configuration file"""
        return self._config_path


# Global singleton instance
_loader = LLMConfigLoader()


def get_llm_config_loader() -> LLMConfigLoader:
    """
    Get the global LLM configuration loader instance.

    Returns:
        LLMConfigLoader: Global singleton instance
    """
    return _loader


def get_llm_config() -> LLMModelsConfig:
    """
    Get the current LLM configuration.

    Convenience function that returns the configuration from the global loader.

    Returns:
        LLMModelsConfig: Current configuration
    """
    return _loader.get_config()


def reload_llm_config() -> LLMModelsConfig:
    """
    Reload the LLM configuration.

    Convenience function that reloads the configuration in the global loader.

    Returns:
        LLMModelsConfig: Reloaded configuration
    """
    return _loader.reload_config()
