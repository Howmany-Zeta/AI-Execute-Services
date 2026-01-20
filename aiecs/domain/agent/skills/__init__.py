"""
Agent Skills Extension

Provides modular, reusable knowledge packages for agents with progressive disclosure,
auto-discovery, and flexible integration strategies.

This module implements the claude-code agent skills pattern adapted for AIECS,
enabling agents to dynamically acquire specialized knowledge and capabilities.
"""

from .models import (
    SkillMetadata,
    SkillResource,
    SkillDefinition,
)
from .loader import (
    SkillLoader,
    SkillLoadError,
)
from .executor import (
    ExecutionMode,
    ScriptExecutionResult,
    SkillScriptExecutor,
)
from .registry import (
    SkillRegistry,
    SkillRegistryError,
)
from .discovery import (
    SkillDiscovery,
    SkillDiscoveryError,
    SkillDiscoveryResult,
    SKILL_DIRECTORIES_ENV,
)
from .matcher import (
    SkillMatcher,
    SkillMatcherError,
    MatchResult,
)
from .context import (
    SkillContext,
    SkillContextError,
    ContextOptions,
    SkillContextResult,
)
from .mixin import (
    SkillCapableMixin,
)
from .validator import (
    SkillValidator,
    SkillValidationError,
    ValidationResult,
    ValidationIssue,
)

__all__ = [
    # Models
    "SkillMetadata",
    "SkillResource",
    "SkillDefinition",
    # Loader
    "SkillLoader",
    "SkillLoadError",
    # Executor
    "ExecutionMode",
    "ScriptExecutionResult",
    "SkillScriptExecutor",
    # Registry
    "SkillRegistry",
    "SkillRegistryError",
    # Discovery
    "SkillDiscovery",
    "SkillDiscoveryError",
    "SkillDiscoveryResult",
    "SKILL_DIRECTORIES_ENV",
    # Matcher
    "SkillMatcher",
    "SkillMatcherError",
    "MatchResult",
    # Context
    "SkillContext",
    "SkillContextError",
    "ContextOptions",
    "SkillContextResult",
    # Mixin
    "SkillCapableMixin",
    # Validator
    "SkillValidator",
    "SkillValidationError",
    "ValidationResult",
    "ValidationIssue",
]

