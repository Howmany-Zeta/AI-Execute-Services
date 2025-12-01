"""
Configuration loader for tool configurations.

This module provides a singleton configuration loader that loads and manages
tool configurations from YAML files and .env files with support for
sensitive credential separation and runtime configuration management.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union
import yaml
from threading import Lock
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ToolConfigLoader:
    """
    Singleton configuration loader for tools.

    Supports:
    - Loading sensitive configuration from .env files (via dotenv)
    - Loading runtime configuration from YAML files
    - Configuration merging with precedence order
    - Schema validation against tool's Pydantic Config class
    - Config directory discovery (walking up directory tree)
    - Thread-safe access
    - Caching for performance
    """

    _instance: Optional["ToolConfigLoader"] = None
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

        self._config_path: Optional[Path] = None
        self._cached_config_dir: Optional[Path] = None
        self._initialized = True
        logger.info("ToolConfigLoader initialized")

    def find_config_directory(self) -> Optional[Path]:
        """
        Discover config/ directory in project.

        Search order:
        1. Custom config path set via set_config_path()
        2. Settings tool_config_path (if available)
        3. Environment variable TOOL_CONFIG_PATH
        4. Walk up directory tree from current working directory
        5. Check aiecs/config/ directory

        Returns:
            Path to config directory if found, None otherwise
        """
        # Check if custom path was set
        if self._config_path:
            if self._config_path.is_dir():
                return self._config_path
            elif self._config_path.is_file():
                return self._config_path.parent

        # Check if config directory was already cached
        if self._cached_config_dir and self._cached_config_dir.exists():
            return self._cached_config_dir

        # Check settings (if available)
        try:
            from aiecs.config.config import get_settings

            settings = get_settings()
            if hasattr(settings, "tool_config_path") and settings.tool_config_path:
                path = Path(settings.tool_config_path)
                if path.exists():
                    logger.info(f"Using tool config path from settings: {path}")
                    self._cached_config_dir = path if path.is_dir() else path.parent
                    return self._cached_config_dir
        except Exception as e:
            logger.debug(f"Could not load settings: {e}")

        # Check environment variable
        env_path = os.environ.get("TOOL_CONFIG_PATH")
        if env_path:
            path = Path(env_path)
            if path.exists():
                logger.info(f"Using tool config path from environment: {path}")
                self._cached_config_dir = path if path.is_dir() else path.parent
                return self._cached_config_dir

        # Walk up directory tree from current working directory
        current_dir = Path.cwd()
        while current_dir != current_dir.parent:  # Stop at root
            config_dir = current_dir / "config"
            if config_dir.exists() and config_dir.is_dir():
                logger.info(f"Found config directory: {config_dir}")
                self._cached_config_dir = config_dir
                return config_dir
            current_dir = current_dir.parent

        # Check aiecs/config/ directory as fallback
        aiecs_config_dir = Path(__file__).parent.parent / "config"
        if aiecs_config_dir.exists() and aiecs_config_dir.is_dir():
            logger.info(f"Using aiecs config directory: {aiecs_config_dir}")
            self._cached_config_dir = aiecs_config_dir
            return aiecs_config_dir

        logger.debug("No config directory found")
        return None

    def load_env_config(self) -> Dict[str, Any]:
        """
        Load sensitive configuration from .env files via dotenv.

        Supports multiple .env files in order:
        1. .env (base)
        2. .env.local (local overrides)
        3. .env.production (production overrides, if NODE_ENV=production)

        Returns:
            Dictionary of environment variables loaded from .env files
        """
        config_dir = self.find_config_directory()
        env_vars = {}

        # Determine base directory for .env files
        if config_dir:
            base_dir = config_dir.parent if (config_dir / "tools").exists() else config_dir
        else:
            base_dir = Path.cwd()

        # Load .env files in order (later files override earlier ones)
        env_files = [".env"]
        if os.environ.get("NODE_ENV") == "production":
            env_files.append(".env.production")
        else:
            env_files.append(".env.local")

        for env_file in env_files:
            env_path = base_dir / env_file
            if env_path.exists():
                try:
                    load_dotenv(env_path, override=False)  # Don't override already loaded vars
                    logger.debug(f"Loaded environment variables from {env_path}")
                except Exception as e:
                    logger.warning(f"Failed to load {env_path}: {e}")

        # Return all environment variables (dotenv loads them into os.environ)
        # We return empty dict here since dotenv modifies os.environ directly
        # The actual env vars will be picked up by BaseSettings or os.getenv()
        return {}

    def load_yaml_config(self, tool_name: str) -> Dict[str, Any]:
        """
        Load runtime configuration from YAML files.

        Loads from:
        1. Tool-specific: config/tools/{tool_name}.yaml
        2. Global: config/tools.yaml

        Tool-specific config takes precedence over global config.

        Args:
            tool_name: Name of the tool (e.g., "DocumentParserTool")

        Returns:
            Dictionary of configuration values from YAML files
        """
        config_dir = self.find_config_directory()
        if not config_dir:
            logger.debug("No config directory found, skipping YAML config loading")
            return {}

        merged_config = {}

        # Load global config first (lower precedence)
        global_config_path = config_dir / "tools.yaml"
        if global_config_path.exists():
            try:
                with open(global_config_path, "r", encoding="utf-8") as f:
                    global_data = yaml.safe_load(f)
                    if global_data:
                        # Support tool-specific sections in global config
                        if isinstance(global_data, dict):
                            # If there's a tools section, look for tool-specific config
                            if "tools" in global_data and isinstance(global_data["tools"], dict):
                                # Global defaults
                                merged_config.update(global_data.get("defaults", {}))
                            else:
                                # Flat global config
                                merged_config.update(global_data)
                        logger.debug(f"Loaded global config from {global_config_path}")
            except yaml.YAMLError as e:
                logger.warning(f"Invalid YAML in {global_config_path}: {e}. Skipping.")
            except Exception as e:
                logger.warning(f"Failed to load {global_config_path}: {e}. Skipping.")

        # Load tool-specific config (higher precedence)
        tools_dir = config_dir / "tools"
        if tools_dir.exists() and tools_dir.is_dir():
            tool_config_path = tools_dir / f"{tool_name}.yaml"
            if tool_config_path.exists():
                try:
                    with open(tool_config_path, "r", encoding="utf-8") as f:
                        tool_data = yaml.safe_load(f)
                        if tool_data:
                            # Merge tool-specific config (overrides global)
                            merged_config.update(tool_data)
                            logger.debug(f"Loaded tool-specific config from {tool_config_path}")
                except yaml.YAMLError as e:
                    logger.warning(f"Invalid YAML in {tool_config_path}: {e}. Skipping.")
                except Exception as e:
                    logger.warning(f"Failed to load {tool_config_path}: {e}. Skipping.")

        return merged_config

    def merge_config(
        self,
        explicit_config: Optional[Dict[str, Any]] = None,
        yaml_config: Optional[Dict[str, Any]] = None,
        env_config: Optional[Dict[str, Any]] = None,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Merge configurations according to precedence order.

        Precedence (highest to lowest):
        1. Explicit config dict
        2. YAML config
        3. Environment variables
        4. Defaults

        Args:
            explicit_config: Explicit configuration dict (highest priority)
            yaml_config: Configuration from YAML files
            env_config: Configuration from environment variables
            defaults: Default configuration values (lowest priority)

        Returns:
            Merged configuration dictionary
        """
        merged = {}

        # Start with defaults (lowest priority)
        if defaults:
            merged.update(defaults)

        # Add environment variables (dotenv loads them into os.environ)
        # Note: We don't merge env_config here since dotenv modifies os.environ
        # Environment variables will be picked up by BaseSettings automatically

        # Add YAML config
        if yaml_config:
            merged.update(yaml_config)

        # Add explicit config (highest priority)
        if explicit_config:
            merged.update(explicit_config)

        return merged

    def validate_config(self, config_dict: Dict[str, Any], config_schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Validate merged config against tool's Pydantic schema.

        Args:
            config_dict: Configuration dictionary to validate
            config_schema: Pydantic model class for validation

        Returns:
            Validated configuration dictionary

        Raises:
            ValidationError: If configuration is invalid
        """
        try:
            # Create instance of config schema to validate
            config_instance = config_schema(**config_dict)
            # Convert back to dict (handles aliases, validators, etc.)
            return config_instance.model_dump()
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error["loc"])
                error_messages.append(f"{field}: {error['msg']}")
            raise ValidationError(
                f"Tool configuration validation failed:\n" + "\n".join(error_messages),
                e.model,
            ) from e

    def load_tool_config(
        self,
        tool_name: str,
        config_schema: Optional[Type[BaseModel]] = None,
        explicit_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for loading tool configuration.

        Loads, merges, and validates configuration from all sources:
        1. Explicit config dict (highest priority)
        2. YAML config files (tool-specific and global)
        3. Environment variables (via dotenv)
        4. Tool defaults (lowest priority)

        Args:
            tool_name: Name of the tool (e.g., "DocumentParserTool")
            config_schema: Optional Pydantic model class for validation
            explicit_config: Optional explicit configuration dict (overrides everything)

        Returns:
            Merged and validated configuration dictionary

        Raises:
            ValidationError: If config_schema is provided and validation fails
        """
        with self._config_lock:
            # Load environment variables from .env files
            self.load_env_config()

            # Load YAML configuration
            yaml_config = self.load_yaml_config(tool_name)

            # Get defaults from config schema if available
            defaults = {}
            if config_schema:
                try:
                    # Create instance with no args to get defaults
                    default_instance = config_schema()
                    defaults = default_instance.model_dump(exclude_unset=True)
                except Exception:
                    # Schema might require some fields, that's okay
                    pass

            # Merge configurations according to precedence
            merged_config = self.merge_config(
                explicit_config=explicit_config,
                yaml_config=yaml_config,
                defaults=defaults,
            )

            # Validate against schema if provided
            if config_schema:
                merged_config = self.validate_config(merged_config, config_schema)

            logger.debug(f"Loaded config for {tool_name}: {len(merged_config)} keys")
            return merged_config

    def set_config_path(self, path: Union[str, Path]) -> None:
        """
        Set custom config path.

        Args:
            path: Path to config directory or file
        """
        self._config_path = Path(path)
        # Clear cached config directory to force re-discovery
        self._cached_config_dir = None
        logger.info(f"Set custom config path: {self._config_path}")

    def get_config_path(self) -> Optional[Path]:
        """
        Get current config path.

        Returns:
            Path to config directory if set, None otherwise
        """
        return self._config_path or self._cached_config_dir


# Global singleton instance
_loader = ToolConfigLoader()


def get_tool_config_loader() -> ToolConfigLoader:
    """
    Get the global tool configuration loader instance.

    Returns:
        ToolConfigLoader: Global singleton instance
    """
    return _loader

