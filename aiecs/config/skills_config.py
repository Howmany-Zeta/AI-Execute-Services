"""
Skill Configuration Module

Provides configuration management for the agent skills system,
including skill directory paths, discovery settings, and validation.

Configuration can be loaded from environment variables or .env files:
    AIECS_SKILL_DIRECTORIES: Comma-separated list of skill directories
    AIECS_SKILL_AUTO_DISCOVER: Enable auto-discovery at startup (default: false)
    AIECS_SKILL_CACHE_TTL: Resource cache TTL in seconds (default: 3600)
    AIECS_SKILL_MAX_CONCURRENT_DISCOVERY: Max concurrent skill loading (default: 10)
    AIECS_SKILL_DEFAULT_TIMEOUT: Default script execution timeout (default: 30)

Example:
    export AIECS_SKILL_DIRECTORIES="/path/to/skills,/another/skills"
    export AIECS_SKILL_AUTO_DISCOVER=true
    export AIECS_SKILL_CACHE_TTL=7200
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# Default environment variable names (for reference)
SKILL_DIRECTORIES_ENV = "AIECS_SKILL_DIRECTORIES"
DEFAULT_SKILL_DIRECTORY = "aiecs/domain/agent/skills/builtin"


class SkillsConfig(BaseSettings):
    """
    Configuration for the agent skills system.
    
    Manages skill directory paths, discovery settings, caching,
    and script execution parameters.
    
    Usage:
        from aiecs.config.skills_config import get_skills_config
        
        config = get_skills_config()
        directories = config.get_skill_directories()
    """
    
    # Skill directories (comma-separated list)
    skill_directories: str = Field(
        default="",
        alias="AIECS_SKILL_DIRECTORIES",
        description="Comma-separated list of paths to skill directories",
    )
    
    # Auto-discovery at startup
    skill_auto_discover: bool = Field(
        default=False,
        alias="AIECS_SKILL_AUTO_DISCOVER",
        description="Enable automatic skill discovery at startup",
    )
    
    # Resource caching
    skill_cache_ttl: int = Field(
        default=3600,
        alias="AIECS_SKILL_CACHE_TTL",
        description="Time-to-live for cached skill resources in seconds",
    )
    
    # Discovery settings
    skill_max_concurrent_discovery: int = Field(
        default=10,
        alias="AIECS_SKILL_MAX_CONCURRENT_DISCOVERY",
        description="Maximum number of concurrent skill loading operations",
    )
    
    # Script execution settings
    skill_default_timeout: int = Field(
        default=30,
        alias="AIECS_SKILL_DEFAULT_TIMEOUT",
        description="Default timeout for script execution in seconds",
    )
    
    skill_max_timeout: int = Field(
        default=600,
        alias="AIECS_SKILL_MAX_TIMEOUT",
        description="Maximum allowed timeout for script execution in seconds",
    )
    
    skill_max_output_size: int = Field(
        default=1048576,  # 1MB
        alias="AIECS_SKILL_MAX_OUTPUT_SIZE",
        description="Maximum output size for script execution in bytes",
    )
    
    # Validation settings
    skill_validate_on_load: bool = Field(
        default=True,
        alias="AIECS_SKILL_VALIDATE_ON_LOAD",
        description="Validate skills when loading",
    )
    
    # Default native mode for Python scripts
    skill_default_python_mode: str = Field(
        default="native",
        alias="AIECS_SKILL_DEFAULT_PYTHON_MODE",
        description="Default execution mode for Python scripts (native/subprocess)",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator("skill_cache_ttl")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        """Validate cache TTL is positive."""
        if v < 0:
            raise ValueError("AIECS_SKILL_CACHE_TTL must be non-negative")
        return v
    
    @field_validator("skill_max_concurrent_discovery")
    @classmethod
    def validate_max_concurrent(cls, v: int) -> int:
        """Validate max concurrent discovery."""
        if v < 1:
            raise ValueError("AIECS_SKILL_MAX_CONCURRENT_DISCOVERY must be at least 1")
        if v > 100:
            logger.warning(
                f"AIECS_SKILL_MAX_CONCURRENT_DISCOVERY is {v}, "
                "which may cause resource issues. Consider using <= 100."
            )
        return v
    
    @field_validator("skill_default_timeout")
    @classmethod
    def validate_default_timeout(cls, v: int) -> int:
        """Validate default timeout is positive."""
        if v < 1:
            raise ValueError("AIECS_SKILL_DEFAULT_TIMEOUT must be at least 1 second")
        return v
    
    @field_validator("skill_max_timeout")
    @classmethod
    def validate_max_timeout(cls, v: int) -> int:
        """Validate max timeout is reasonable."""
        if v < 1:
            raise ValueError("AIECS_SKILL_MAX_TIMEOUT must be at least 1 second")
        if v > 3600:
            logger.warning(
                f"AIECS_SKILL_MAX_TIMEOUT is {v}s (> 1 hour), "
                "which may cause issues with long-running scripts."
            )
        return v
    
    @field_validator("skill_default_python_mode")
    @classmethod
    def validate_python_mode(cls, v: str) -> str:
        """Validate Python execution mode."""
        valid_modes = ["native", "subprocess", "auto"]
        if v.lower() not in valid_modes:
            raise ValueError(
                f"Invalid AIECS_SKILL_DEFAULT_PYTHON_MODE: {v}. "
                f"Must be one of: {', '.join(valid_modes)}"
            )
        return v.lower()
    
    def get_skill_directories(self) -> List[Path]:
        """
        Get list of skill directories from configuration.
        
        Parses the comma-separated AIECS_SKILL_DIRECTORIES and
        returns a list of Path objects. Expands user home directory
        references (~) and validates that paths exist.
        
        Returns:
            List of Path objects for existing skill directories
        """
        directories: List[Path] = []
        
        # Parse configured directories
        if self.skill_directories:
            for path_str in self.skill_directories.split(","):
                path_str = path_str.strip()
                if not path_str:
                    continue
                
                path = Path(path_str).expanduser()
                if path.exists():
                    directories.append(path)
                else:
                    logger.warning(f"Skill directory does not exist: {path}")
        
        # Add default directory if it exists and not already included
        default_path = Path(DEFAULT_SKILL_DIRECTORY)
        if default_path.exists() and default_path not in directories:
            directories.append(default_path)
        
        return directories
    
    def get_all_configured_directories(self) -> List[Path]:
        """
        Get all configured directories, including non-existent ones.
        
        Unlike get_skill_directories(), this returns all configured paths
        even if they don't exist. Useful for validation and debugging.
        
        Returns:
            List of all configured Path objects
        """
        directories: List[Path] = []
        
        if self.skill_directories:
            for path_str in self.skill_directories.split(","):
                path_str = path_str.strip()
                if path_str:
                    directories.append(Path(path_str).expanduser())
        
        # Add default
        default_path = Path(DEFAULT_SKILL_DIRECTORY)
        if default_path not in directories:
            directories.append(default_path)
        
        return directories
    
    def validate_directories(self) -> tuple[List[Path], List[Path]]:
        """
        Validate configured skill directories.
        
        Returns:
            Tuple of (valid_directories, invalid_directories)
        """
        valid: List[Path] = []
        invalid: List[Path] = []
        
        for path in self.get_all_configured_directories():
            if path.exists() and path.is_dir():
                # Check if readable
                try:
                    list(path.iterdir())
                    valid.append(path)
                except PermissionError:
                    logger.error(f"Skill directory not readable: {path}")
                    invalid.append(path)
            else:
                invalid.append(path)
        
        return valid, invalid
    
    @property
    def discovery_config(self) -> dict:
        """Get discovery-related configuration as dict."""
        return {
            "directories": self.get_skill_directories(),
            "auto_discover": self.skill_auto_discover,
            "max_concurrent": self.skill_max_concurrent_discovery,
        }
    
    @property
    def executor_config(self) -> dict:
        """Get script executor configuration as dict."""
        return {
            "default_timeout": self.skill_default_timeout,
            "max_timeout": self.skill_max_timeout,
            "max_output_size": self.skill_max_output_size,
            "default_python_mode": self.skill_default_python_mode,
        }
    
    @property
    def loader_config(self) -> dict:
        """Get loader configuration as dict."""
        return {
            "cache_ttl": self.skill_cache_ttl,
            "validate_on_load": self.skill_validate_on_load,
        }


@lru_cache()
def get_skills_config() -> SkillsConfig:
    """
    Get the skills configuration singleton.
    
    Configuration is loaded from environment variables or .env file.
    The instance is cached for performance.
    
    Returns:
        SkillsConfig instance
        
    Example:
        config = get_skills_config()
        dirs = config.get_skill_directories()
        print(f"Skill directories: {dirs}")
    """
    return SkillsConfig()


def validate_skills_config() -> bool:
    """
    Validate the skills configuration.
    
    Checks that:
    - At least one skill directory is configured and accessible
    - Configuration values are valid
    
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    config = get_skills_config()
    
    # Validate directories
    valid, invalid = config.validate_directories()
    
    if not valid:
        if invalid:
            raise ValueError(
                f"No valid skill directories found. "
                f"Invalid directories: {[str(p) for p in invalid]}"
            )
        else:
            # No directories configured at all - this is okay, just log
            logger.info(
                "No skill directories configured. "
                "Skills system will start with empty registry."
            )
    
    return True

