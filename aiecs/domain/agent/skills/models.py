"""
Skill Data Models

Defines the core data structures for agent skills including metadata,
resources, and skill definitions with lazy loading support.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import re


@dataclass
class SkillMetadata:
    """
    Metadata for a skill extracted from YAML frontmatter.

    Attributes:
        name: Unique skill identifier (kebab-case)
        description: Brief description for skill triggering
        version: Semantic version (e.g., "1.0.0"), defaults to "1.0.0" if not specified
        author: Optional author information
        tags: Optional tags for categorization
        dependencies: Optional list of required skills
        recommended_tools: Optional list of tool names to recommend when skill is active
    """
    name: str
    description: str
    version: str = "1.0.0"  # Default version for backward compatibility
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    recommended_tools: Optional[List[str]] = None

    def __post_init__(self):
        """Validate metadata fields."""
        # Validate name is kebab-case
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', self.name):
            raise ValueError(
                f"Skill name must be kebab-case (lowercase with hyphens): {self.name}"
            )

        # Validate version is semver-like
        if not re.match(r'^\d+\.\d+\.\d+', self.version):
            raise ValueError(
                f"Skill version must be semantic version (e.g., '1.0.0'): {self.version}"
            )
        
        # Ensure lists are not None
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
        if self.recommended_tools is None:
            self.recommended_tools = []


@dataclass
class SkillResource:
    """
    Represents a skill resource (reference, example, script, or asset).
    
    Attributes:
        path: Path to the resource file (relative to skill directory)
        type: Resource type ('reference', 'example', 'script', 'asset')
        content: Lazy-loaded content of the resource
        executable: Whether the resource is executable (True for scripts)
        mode: Execution mode for scripts ('native', 'subprocess', 'auto')
        description: Optional description for scripts (used for tool registration)
        parameters: Optional parameter definitions for scripts (used for tool registration)
    """
    path: str
    type: str  # 'reference', 'example', 'script', 'asset'
    content: Optional[str] = None
    executable: bool = False
    mode: Optional[str] = None  # For scripts: 'native', 'subprocess', 'auto'
    description: Optional[str] = None  # For scripts: tool description
    parameters: Optional[Dict[str, Any]] = None  # For scripts: parameter definitions
    
    def __post_init__(self):
        """Validate resource fields."""
        valid_types = {'reference', 'example', 'script', 'asset'}
        if self.type not in valid_types:
            raise ValueError(
                f"Resource type must be one of {valid_types}: {self.type}"
            )
        
        # Validate mode if provided
        if self.mode is not None:
            valid_modes = {'native', 'subprocess', 'auto'}
            if self.mode not in valid_modes:
                raise ValueError(
                    f"Script mode must be one of {valid_modes}: {self.mode}"
                )
        
        # Scripts should be marked as executable
        if self.type == 'script':
            self.executable = True


@dataclass
class SkillDefinition:
    """
    Complete skill definition with metadata, body, and resources.
    
    Supports progressive disclosure:
    - Level 1: Metadata only (always loaded)
    - Level 2: Body content (loaded when skill is triggered)
    - Level 3: Resources (loaded as needed)
    
    Attributes:
        metadata: Skill metadata from YAML frontmatter
        skill_path: Path to the skill directory
        body: Markdown body content (lazy loaded)
        references: Dictionary of reference resources
        examples: Dictionary of example resources
        scripts: Dictionary of script resources
        assets: Dictionary of asset resources
        recommended_tools: List of recommended tool names (from metadata)
    """
    metadata: SkillMetadata
    skill_path: Path
    body: Optional[str] = None
    references: Dict[str, SkillResource] = field(default_factory=dict)
    examples: Dict[str, SkillResource] = field(default_factory=dict)
    scripts: Dict[str, SkillResource] = field(default_factory=dict)
    assets: Dict[str, SkillResource] = field(default_factory=dict)
    
    @property
    def recommended_tools(self) -> List[str]:
        """Get recommended tools from metadata."""
        return self.metadata.recommended_tools or []
    
    def is_body_loaded(self) -> bool:
        """Check if body content is loaded."""
        return self.body is not None
    
    def is_resource_loaded(self, resource_type: str, resource_name: str) -> bool:
        """
        Check if a specific resource is loaded.
        
        Args:
            resource_type: Type of resource ('reference', 'example', 'script', 'asset')
            resource_name: Name of the resource
            
        Returns:
            True if resource content is loaded, False otherwise
        """
        resource_dict = getattr(self, f"{resource_type}s", None)
        if resource_dict is None:
            return False
        resource = resource_dict.get(resource_name)
        return resource is not None and resource.content is not None

