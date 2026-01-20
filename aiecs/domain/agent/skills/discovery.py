"""
Skill Discovery

Provides auto-discovery of skills from configured directories.
Supports async concurrent scanning with validation and error handling.

Configuration is loaded from environment variables or the centralized
SkillsConfig in aiecs.config.skills_config:
    AIECS_SKILL_DIRECTORIES: Comma-separated list of skill directories
    AIECS_SKILL_MAX_CONCURRENT_DISCOVERY: Max concurrent skill loading
    AIECS_SKILL_AUTO_DISCOVER: Enable auto-discovery at startup

Example:
    export AIECS_SKILL_DIRECTORIES="/path/to/skills,/another/skills"
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .loader import SkillLoadError, SkillLoader
from .models import SkillDefinition
from .registry import SkillRegistry

logger = logging.getLogger(__name__)


# Default environment variable for skill directories (re-exported for backward compat)
SKILL_DIRECTORIES_ENV = "AIECS_SKILL_DIRECTORIES"

# Default skill directory (relative to project root)
DEFAULT_SKILL_DIRECTORY = "aiecs/domain/agent/skills/builtin"


def _get_skills_config():
    """
    Lazy import of skills config to avoid circular imports.

    Returns the SkillsConfig or None if not available.
    """
    try:
        from aiecs.config.skills_config import get_skills_config
        return get_skills_config()
    except ImportError:
        return None


class SkillDiscoveryError(Exception):
    """Raised when skill discovery fails."""
    pass


class SkillDiscoveryResult:
    """Result of a skill discovery operation."""
    
    def __init__(self):
        self.discovered: List[SkillDefinition] = []
        self.failed: Dict[Path, str] = {}  # path -> error message
        self.skipped: List[Path] = []  # paths skipped (already registered)
    
    @property
    def success_count(self) -> int:
        """Number of successfully discovered skills."""
        return len(self.discovered)
    
    @property
    def failure_count(self) -> int:
        """Number of failed skill discoveries."""
        return len(self.failed)
    
    @property
    def skip_count(self) -> int:
        """Number of skipped skills (already registered)."""
        return len(self.skipped)
    
    def __repr__(self) -> str:
        return (
            f"SkillDiscoveryResult(discovered={self.success_count}, "
            f"failed={self.failure_count}, skipped={self.skip_count})"
        )


class SkillDiscovery:
    """
    Discovers and loads skills from configured directories.
    
    Supports:
    - Async concurrent scanning of multiple directories
    - Automatic skill validation during loading
    - Configurable paths via environment variables
    - Error handling with detailed reporting
    - Skip already-registered skills option
    
    Usage:
        discovery = SkillDiscovery()
        result = await discovery.discover()
        print(f"Discovered {result.success_count} skills")
    """
    
    def __init__(
        self,
        loader: Optional[SkillLoader] = None,
        registry: Optional[SkillRegistry] = None,
        directories: Optional[List[Path]] = None,
        auto_register: bool = True,
        skip_registered: bool = True,
        max_concurrent: Optional[int] = None
    ):
        """
        Initialize skill discovery.

        Args:
            loader: SkillLoader instance (creates new if None)
            registry: SkillRegistry instance (uses singleton if None)
            directories: List of directories to scan (uses config if None)
            auto_register: Whether to auto-register discovered skills
            skip_registered: Whether to skip already-registered skills
            max_concurrent: Maximum concurrent loading operations (uses config if None)
        """
        self._loader = loader or SkillLoader()
        self._registry = registry or SkillRegistry.get_instance()
        self._directories = directories or self._get_configured_directories()
        self._auto_register = auto_register
        self._skip_registered = skip_registered
        self._max_concurrent = max_concurrent or self._get_max_concurrent()
        self._on_skill_discovered: Optional[Callable[[SkillDefinition], None]] = None
        self._on_skill_failed: Optional[Callable[[Path, str], None]] = None

    def _get_max_concurrent(self) -> int:
        """Get max concurrent from config or default."""
        skills_config = _get_skills_config()
        if skills_config is not None:
            return skills_config.skill_max_concurrent_discovery
        return 10  # Default
    
    def _get_configured_directories(self) -> List[Path]:
        """
        Get skill directories from configuration.

        Priority order:
        1. SkillsConfig (aiecs.config.skills_config) if available
        2. AIECS_SKILL_DIRECTORIES environment variable
        3. Default skill directory (aiecs/domain/agent/skills/builtin)

        Returns:
            List of existing Path objects for skill directories
        """
        # Try to use centralized config first
        skills_config = _get_skills_config()
        if skills_config is not None:
            directories = skills_config.get_skill_directories()
            if directories:
                return directories

        # Fall back to direct environment variable (backward compatibility)
        env_dirs = os.environ.get(SKILL_DIRECTORIES_ENV, "")

        if env_dirs:
            # Parse comma-separated paths from environment
            paths = [
                Path(p.strip()).expanduser()
                for p in env_dirs.split(",")
                if p.strip()
            ]
            return [p for p in paths if p.exists()]

        # Use default directory if no environment config
        default_path = Path(DEFAULT_SKILL_DIRECTORY)
        if default_path.exists():
            return [default_path]

        return []
    
    def set_directories(self, directories: List[Path]) -> None:
        """Set directories to scan for skills."""
        self._directories = directories
    
    def add_directory(self, directory: Path) -> None:
        """Add a directory to scan for skills."""
        if directory not in self._directories:
            self._directories.append(directory)
    
    def on_discovered(self, callback: Callable[[SkillDefinition], None]) -> None:
        """Set callback for when a skill is discovered."""
        self._on_skill_discovered = callback

    def on_failed(self, callback: Callable[[Path, str], None]) -> None:
        """Set callback for when a skill fails to load."""
        self._on_skill_failed = callback

    async def discover(
        self,
        directories: Optional[List[Path]] = None,
        load_body: bool = True
    ) -> SkillDiscoveryResult:
        """
        Discover and load skills from directories.

        Args:
            directories: Directories to scan (uses configured if None)
            load_body: Whether to load skill body content

        Returns:
            SkillDiscoveryResult with discovered, failed, and skipped skills
        """
        result = SkillDiscoveryResult()
        dirs_to_scan = directories or self._directories

        if not dirs_to_scan:
            logger.warning("No skill directories configured for discovery")
            return result

        # Find all potential skill directories
        skill_paths: List[Path] = []
        for directory in dirs_to_scan:
            directory = Path(directory)
            if not directory.exists():
                logger.warning(f"Skill directory does not exist: {directory}")
                continue

            # Find subdirectories containing SKILL.md
            found = await self._find_skill_directories(directory)
            skill_paths.extend(found)

        if not skill_paths:
            logger.info("No skills found in configured directories")
            return result

        logger.info(f"Found {len(skill_paths)} potential skills to load")

        # Load skills concurrently with semaphore
        semaphore = asyncio.Semaphore(self._max_concurrent)
        tasks = [
            self._load_skill_with_semaphore(
                path, semaphore, result, load_body
            )
            for path in skill_paths
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(
            f"Discovery complete: {result.success_count} discovered, "
            f"{result.failure_count} failed, {result.skip_count} skipped"
        )

        return result

    async def _find_skill_directories(self, root: Path) -> List[Path]:
        """Find all directories containing SKILL.md files."""
        skill_dirs: List[Path] = []

        # Check if root itself contains SKILL.md
        if (root / "SKILL.md").exists():
            skill_dirs.append(root)

        # Scan subdirectories (one level deep by default)
        try:
            for entry in root.iterdir():
                if entry.is_dir() and (entry / "SKILL.md").exists():
                    skill_dirs.append(entry)
        except PermissionError:
            logger.warning(f"Permission denied scanning: {root}")

        return skill_dirs

    async def _load_skill_with_semaphore(
        self,
        skill_path: Path,
        semaphore: asyncio.Semaphore,
        result: SkillDiscoveryResult,
        load_body: bool
    ) -> None:
        """Load a skill with semaphore for concurrency control."""
        async with semaphore:
            await self._load_skill(skill_path, result, load_body)

    async def _load_skill(
        self,
        skill_path: Path,
        result: SkillDiscoveryResult,
        load_body: bool
    ) -> None:
        """Load a single skill and update result."""
        try:
            # Load skill using loader
            skill = await self._loader.load_skill(skill_path, load_body=load_body)

            # Check if already registered
            if self._skip_registered and self._registry.has_skill(skill.metadata.name):
                result.skipped.append(skill_path)
                logger.debug(f"Skipped already registered skill: {skill.metadata.name}")
                return

            # Auto-register if enabled
            if self._auto_register:
                try:
                    self._registry.register_skill(skill)
                except Exception as e:
                    result.failed[skill_path] = f"Registration failed: {e}"
                    if self._on_skill_failed:
                        self._on_skill_failed(skill_path, str(e))
                    return

            result.discovered.append(skill)
            logger.debug(f"Discovered skill: {skill.metadata.name}")

            if self._on_skill_discovered:
                self._on_skill_discovered(skill)

        except SkillLoadError as e:
            result.failed[skill_path] = str(e)
            logger.warning(f"Failed to load skill from {skill_path}: {e}")
            if self._on_skill_failed:
                self._on_skill_failed(skill_path, str(e))
        except Exception as e:
            result.failed[skill_path] = f"Unexpected error: {e}"
            logger.error(f"Unexpected error loading {skill_path}: {e}")
            if self._on_skill_failed:
                self._on_skill_failed(skill_path, str(e))

    async def discover_single(
        self,
        skill_path: Path,
        load_body: bool = True
    ) -> SkillDefinition:
        """
        Discover and load a single skill.

        Args:
            skill_path: Path to the skill directory
            load_body: Whether to load skill body content

        Returns:
            SkillDefinition for the discovered skill

        Raises:
            SkillDiscoveryError: If skill cannot be loaded
        """
        try:
            skill = await self._loader.load_skill(skill_path, load_body=load_body)

            if self._auto_register:
                self._registry.register_skill(skill)

            if self._on_skill_discovered:
                self._on_skill_discovered(skill)

            return skill

        except SkillLoadError as e:
            raise SkillDiscoveryError(f"Failed to discover skill: {e}") from e

    def get_directories(self) -> List[Path]:
        """Get configured skill directories."""
        return list(self._directories)

    async def refresh(self) -> SkillDiscoveryResult:
        """
        Refresh skills by re-discovering from all directories.

        Unlike discover(), this will update already-registered skills.

        Returns:
            SkillDiscoveryResult with refresh results
        """
        # Temporarily disable skip_registered for refresh
        original_skip = self._skip_registered
        self._skip_registered = False

        try:
            return await self.discover()
        finally:
            self._skip_registered = original_skip

