"""
Skill Registry

Central registry for managing available skills with discovery, registration,
and lookup capabilities. Implements singleton pattern with thread-safe access.
"""

import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional

from .models import SkillDefinition, SkillMetadata

logger = logging.getLogger(__name__)


class SkillRegistryError(Exception):
    """Raised when skill registry operations fail."""
    pass


class SkillRegistry:
    """
    Central registry for managing available skills.
    
    Implements singleton pattern with thread-safe access for concurrent usage.
    Supports skill registration, lookup, listing, and filtering by tags.
    
    Usage:
        registry = SkillRegistry.get_instance()
        registry.register_skill(skill)
        skill = registry.get_skill("python-coding")
        skills = registry.list_skills(tags=["python"])
    """
    
    _instance: Optional["SkillRegistry"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "SkillRegistry":
        """Create or return singleton instance."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize registry if not already initialized."""
        if getattr(self, "_initialized", False):
            return
        
        self._skills: Dict[str, SkillDefinition] = {}
        self._metadata_cache: Dict[str, SkillMetadata] = {}
        self._access_lock = threading.RLock()
        self._initialized = True
    
    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        """Get the singleton instance of the registry."""
        return cls()
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance (primarily for testing).
        
        Warning: This clears all registered skills. Use with caution.
        """
        with cls._lock:
            cls._instance = None
    
    def register_skill(self, skill: SkillDefinition) -> None:
        """
        Register a skill in the registry.
        
        Args:
            skill: SkillDefinition to register
            
        Raises:
            SkillRegistryError: If skill with same name already exists
        """
        with self._access_lock:
            name = skill.metadata.name
            if name in self._skills:
                raise SkillRegistryError(
                    f"Skill '{name}' is already registered. "
                    f"Use unregister_skill() first to replace it."
                )
            
            self._skills[name] = skill
            self._metadata_cache[name] = skill.metadata
            logger.info(f"Registered skill: {name} v{skill.metadata.version}")
    
    def unregister_skill(self, name: str) -> bool:
        """
        Unregister a skill from the registry.
        
        Args:
            name: Name of the skill to unregister
            
        Returns:
            True if skill was unregistered, False if not found
        """
        with self._access_lock:
            if name in self._skills:
                del self._skills[name]
                del self._metadata_cache[name]
                logger.info(f"Unregistered skill: {name}")
                return True
            return False
    
    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """
        Get a skill by name.
        
        Args:
            name: Name of the skill
            
        Returns:
            SkillDefinition if found, None otherwise
        """
        with self._access_lock:
            return self._skills.get(name)
    
    def get_skills(self, names: List[str]) -> List[SkillDefinition]:
        """
        Get multiple skills by name.
        
        Args:
            names: List of skill names
            
        Returns:
            List of found SkillDefinitions (missing skills are skipped)
        """
        with self._access_lock:
            return [
                self._skills[name] for name in names 
                if name in self._skills
            ]
    
    def has_skill(self, name: str) -> bool:
        """
        Check if a skill is registered.

        Args:
            name: Name of the skill

        Returns:
            True if skill is registered, False otherwise
        """
        with self._access_lock:
            return name in self._skills

    def list_skills(
        self,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None
    ) -> List[SkillMetadata]:
        """
        List available skills with optional filtering.

        Args:
            tags: Filter by tags (skills must have at least one matching tag)
            dependencies: Filter by dependencies (skills must have all specified)

        Returns:
            List of SkillMetadata for matching skills
        """
        with self._access_lock:
            result = []

            for metadata in self._metadata_cache.values():
                # Filter by tags if specified
                if tags is not None:
                    skill_tags = set(metadata.tags or [])
                    if not skill_tags.intersection(set(tags)):
                        continue

                # Filter by dependencies if specified
                if dependencies is not None:
                    skill_deps = set(metadata.dependencies or [])
                    if not set(dependencies).issubset(skill_deps):
                        continue

                result.append(metadata)

            return result

    def list_skill_names(self) -> List[str]:
        """
        Get all registered skill names.

        Returns:
            List of skill names
        """
        with self._access_lock:
            return list(self._skills.keys())

    def get_all_skills(self) -> List[SkillDefinition]:
        """
        Get all registered skills.

        Returns:
            List of all SkillDefinitions
        """
        with self._access_lock:
            return list(self._skills.values())

    def skill_count(self) -> int:
        """
        Get the number of registered skills.

        Returns:
            Number of registered skills
        """
        with self._access_lock:
            return len(self._skills)

    def clear(self) -> None:
        """
        Clear all registered skills.

        Warning: This removes all skills from the registry.
        """
        with self._access_lock:
            count = len(self._skills)
            self._skills.clear()
            self._metadata_cache.clear()
            logger.info(f"Cleared {count} skills from registry")

    def get_skills_by_tag(self, tag: str) -> List[SkillDefinition]:
        """
        Get all skills that have a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of SkillDefinitions with the tag
        """
        with self._access_lock:
            return [
                skill for skill in self._skills.values()
                if tag in (skill.metadata.tags or [])
            ]

    def get_skill_metadata(self, name: str) -> Optional[SkillMetadata]:
        """
        Get skill metadata without loading full skill.

        This is useful for quick lookups when only metadata is needed.

        Args:
            name: Name of the skill

        Returns:
            SkillMetadata if found, None otherwise
        """
        with self._access_lock:
            return self._metadata_cache.get(name)

    def find_skills_with_tool(self, tool_name: str) -> List[SkillDefinition]:
        """
        Find skills that recommend a specific tool.

        Args:
            tool_name: Name of the tool to search for

        Returns:
            List of SkillDefinitions that recommend the tool
        """
        with self._access_lock:
            return [
                skill for skill in self._skills.values()
                if tool_name in (skill.metadata.recommended_tools or [])
            ]

