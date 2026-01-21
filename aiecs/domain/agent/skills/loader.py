"""
Skill Loader

Loads and parses SKILL.md files with YAML frontmatter and Markdown body.
Supports progressive disclosure with lazy loading for body and resources.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import yaml

from .models import SkillDefinition, SkillMetadata, SkillResource

logger = logging.getLogger(__name__)

# YAML frontmatter delimiter pattern
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n(.*)$', re.DOTALL)


class SkillLoadError(Exception):
    """Raised when skill loading fails."""
    pass


class SkillLoader:
    """
    Loads and parses skill definitions from SKILL.md files.
    
    Supports:
    - YAML frontmatter parsing with script configuration
    - Markdown body extraction
    - Resource discovery (references/, examples/, scripts/, assets/)
    - Lazy loading for body and resources
    - Async file I/O
    """
    
    def __init__(self, cache_ttl: int = 3600):
        """
        Initialize skill loader.
        
        Args:
            cache_ttl: Cache TTL for loaded resources in seconds
        """
        self._cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[str, float]] = {}  # (content, timestamp)
    
    async def load_skill(
        self,
        skill_path: Path,
        load_body: bool = True
    ) -> SkillDefinition:
        """
        Load a skill from a directory containing SKILL.md.
        
        Args:
            skill_path: Path to the skill directory
            load_body: Whether to load the body content (default True)
            
        Returns:
            SkillDefinition with metadata, body, and discovered resources
            
        Raises:
            SkillLoadError: If the skill cannot be loaded
        """
        skill_md_path = skill_path / "SKILL.md"
        
        if not skill_md_path.exists():
            raise SkillLoadError(f"SKILL.md not found in {skill_path}")
        
        try:
            # Read SKILL.md content
            async with aiofiles.open(skill_md_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Parse frontmatter and body
            metadata_dict, body = self._parse_frontmatter(content)
            
            # Extract script configuration from YAML
            scripts_config = metadata_dict.pop('scripts', {}) or {}
            
            # Create metadata
            metadata = self._create_metadata(metadata_dict)
            
            # Discover resources
            references = await self._discover_resources(skill_path, 'references', 'reference')
            examples = await self._discover_resources(skill_path, 'examples', 'example')
            assets = await self._discover_resources(skill_path, 'assets', 'asset')
            
            # Discover and merge scripts
            scripts = await self._discover_scripts(skill_path, scripts_config)
            
            return SkillDefinition(
                metadata=metadata,
                skill_path=skill_path,
                body=body if load_body else None,
                references=references,
                examples=examples,
                scripts=scripts,
                assets=assets
            )
            
        except SkillLoadError:
            raise
        except Exception as e:
            raise SkillLoadError(f"Failed to load skill from {skill_path}: {e}") from e
    
    def _parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Parse YAML frontmatter and extract Markdown body.
        
        Args:
            content: Full SKILL.md content
            
        Returns:
            Tuple of (metadata dict, body string)
            
        Raises:
            SkillLoadError: If frontmatter is missing or malformed
        """
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            raise SkillLoadError(
                "SKILL.md must have YAML frontmatter delimited by '---'"
            )
        
        yaml_content = match.group(1)
        body = match.group(2).strip()
        
        try:
            metadata_dict = yaml.safe_load(yaml_content)
            if not isinstance(metadata_dict, dict):
                raise SkillLoadError("YAML frontmatter must be a dictionary")
            return metadata_dict, body
        except yaml.YAMLError as e:
            raise SkillLoadError(f"Invalid YAML frontmatter: {e}") from e
    
    def _create_metadata(self, metadata_dict: Dict[str, Any]) -> SkillMetadata:
        """
        Create SkillMetadata from parsed YAML dict.

        Args:
            metadata_dict: Parsed YAML frontmatter

        Returns:
            SkillMetadata instance

        Raises:
            SkillLoadError: If required fields are missing
        """
        required_fields = ['name', 'description']  # version is optional with default
        missing = [f for f in required_fields if f not in metadata_dict]
        if missing:
            raise SkillLoadError(f"Missing required fields: {missing}")

        try:
            return SkillMetadata(
                name=metadata_dict['name'],
                description=metadata_dict['description'],
                version=metadata_dict.get('version', '1.0.0'),  # Default version
                author=metadata_dict.get('author'),
                tags=metadata_dict.get('tags'),
                dependencies=metadata_dict.get('dependencies'),
                recommended_tools=metadata_dict.get('recommended_tools')
            )
        except ValueError as e:
            raise SkillLoadError(f"Invalid metadata: {e}") from e

    async def _discover_resources(
        self,
        skill_path: Path,
        directory_name: str,
        resource_type: str
    ) -> Dict[str, SkillResource]:
        """
        Discover resources in a skill subdirectory.

        Args:
            skill_path: Path to the skill directory
            directory_name: Name of subdirectory (references, examples, assets)
            resource_type: Type of resource ('reference', 'example', 'asset')

        Returns:
            Dictionary mapping resource names to SkillResource objects
        """
        resources: Dict[str, SkillResource] = {}
        directory = skill_path / directory_name

        if not directory.exists():
            return resources

        try:
            for file_path in directory.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    # Use relative path from skill directory
                    relative_path = str(file_path.relative_to(skill_path))
                    # Use file stem as resource name
                    resource_name = file_path.stem

                    resources[resource_name] = SkillResource(
                        path=relative_path,
                        type=resource_type,
                        content=None,  # Lazy loaded
                        executable=False
                    )
        except OSError as e:
            logger.warning(f"Failed to scan directory {directory}: {e}")

        return resources

    async def _discover_scripts(
        self,
        skill_path: Path,
        scripts_config: Dict[str, Any]
    ) -> Dict[str, SkillResource]:
        """
        Discover scripts from scripts/ directory and merge with YAML configuration.

        YAML-declared scripts take precedence over discovered scripts.
        Scripts not declared in YAML are auto-discovered from scripts/ directory.

        Args:
            skill_path: Path to the skill directory
            scripts_config: Script configuration from YAML frontmatter

        Returns:
            Dictionary mapping script names to SkillResource objects
        """
        scripts: Dict[str, SkillResource] = {}
        scripts_dir = skill_path / "scripts"

        # First, process YAML-declared scripts
        for script_name, config in scripts_config.items():
            if isinstance(config, dict):
                script_path = config.get('path')
                if not script_path:
                    logger.warning(
                        f"Script '{script_name}' missing 'path' in YAML config"
                    )
                    continue

                # Validate script path exists
                full_path = skill_path / script_path
                if not full_path.exists():
                    logger.warning(
                        f"Script path does not exist: {script_path} "
                        f"(declared in YAML for '{script_name}')"
                    )
                    continue

                # Determine default mode based on file extension
                mode = config.get('mode')
                if mode is None:
                    mode = self._get_default_mode(script_path)

                scripts[script_name] = SkillResource(
                    path=script_path,
                    type='script',
                    content=None,
                    executable=True,
                    mode=mode,
                    description=config.get('description'),
                    parameters=config.get('parameters')
                )
            elif isinstance(config, str):
                # Simple path-only format: script_name: "scripts/script.py"
                full_path = skill_path / config
                if not full_path.exists():
                    logger.warning(
                        f"Script path does not exist: {config} "
                        f"(declared in YAML for '{script_name}')"
                    )
                    continue

                scripts[script_name] = SkillResource(
                    path=config,
                    type='script',
                    content=None,
                    executable=True,
                    mode=self._get_default_mode(config)
                )

        # Then, auto-discover scripts from scripts/ directory
        if scripts_dir.exists():
            try:
                for file_path in scripts_dir.iterdir():
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        # Use file stem as script name
                        script_name = file_path.stem

                        # Skip if already declared in YAML
                        if script_name in scripts:
                            continue

                        relative_path = str(file_path.relative_to(skill_path))

                        scripts[script_name] = SkillResource(
                            path=relative_path,
                            type='script',
                            content=None,
                            executable=True,
                            mode=self._get_default_mode(relative_path)
                        )
            except OSError as e:
                logger.warning(f"Failed to scan scripts directory {scripts_dir}: {e}")

        return scripts

    def _get_default_mode(self, script_path: str) -> str:
        """
        Get default execution mode based on file extension.

        Args:
            script_path: Path to the script file

        Returns:
            Default mode ('native' for .py, 'subprocess' for others)
        """
        path = Path(script_path)
        if path.suffix == '.py':
            return 'native'
        return 'subprocess'

    async def load_body(self, skill: SkillDefinition) -> str:
        """
        Load skill body content from SKILL.md.

        Args:
            skill: SkillDefinition to load body for

        Returns:
            Body content string

        Raises:
            SkillLoadError: If body cannot be loaded
        """
        if skill.body is not None:
            return skill.body

        skill_md_path = skill.skill_path / "SKILL.md"

        try:
            async with aiofiles.open(skill_md_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            _, body = self._parse_frontmatter(content)
            skill.body = body
            return body

        except Exception as e:
            raise SkillLoadError(
                f"Failed to load body for skill '{skill.metadata.name}': {e}"
            ) from e

    async def load_resource(
        self,
        skill: SkillDefinition,
        resource_type: str,
        resource_name: str
    ) -> str:
        """
        Load specific resource content with caching.

        Args:
            skill: SkillDefinition containing the resource
            resource_type: Type of resource ('reference', 'example', 'script', 'asset')
            resource_name: Name of the resource

        Returns:
            Resource content string

        Raises:
            SkillLoadError: If resource cannot be loaded
        """
        import time

        # Get resource dictionary
        resource_dict = getattr(skill, f"{resource_type}s", None)
        if resource_dict is None:
            raise SkillLoadError(f"Invalid resource type: {resource_type}")

        resource = resource_dict.get(resource_name)
        if resource is None:
            raise SkillLoadError(
                f"Resource not found: {resource_type}/{resource_name}"
            )

        # Check if already loaded
        if resource.content is not None:
            return resource.content

        # Check cache
        cache_key = f"{skill.metadata.name}:{resource.path}"
        if cache_key in self._cache:
            cached_content, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                resource.content = cached_content
                return cached_content

        # Load from file
        resource_path = skill.skill_path / resource.path

        try:
            async with aiofiles.open(resource_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Update cache and resource
            self._cache[cache_key] = (content, time.time())
            resource.content = content
            return content

        except Exception as e:
            raise SkillLoadError(
                f"Failed to load resource '{resource.path}': {e}"
            ) from e

    def clear_cache(self) -> None:
        """Clear the resource cache."""
        self._cache.clear()

