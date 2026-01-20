"""
Skill Context

Provides context building and formatting for skill injection into agent prompts.

Supports:
- Context building from skill metadata and body
- Resource path listing
- Script availability listing with metadata
- Tool recommendations extraction and formatting
- Progressive disclosure logic
- Markdown formatting for LLM consumption

Usage:
    from aiecs.domain.agent.skills.context import SkillContext

    context = SkillContext(skills=[python_skill, testing_skill])
    prompt_context = context.build_context(request="write unit tests")
    resources = context.get_resource_paths()
    tools = context.get_recommended_tools(request, available_tools)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .models import SkillDefinition, SkillResource

logger = logging.getLogger(__name__)


@dataclass
class ContextOptions:
    """Options for context building."""
    include_body: bool = True
    include_resources: bool = True
    include_scripts: bool = True
    include_tool_recommendations: bool = True
    max_body_length: Optional[int] = None  # None = no limit


@dataclass
class SkillContextResult:
    """Result of context building for a single skill."""
    skill_name: str
    context: str
    matched_score: float = 0.0
    has_scripts: bool = False
    has_resources: bool = False


class SkillContext:
    """
    Builds and formats skill context for agent prompt injection.

    Provides methods to:
    - Build formatted context from skills
    - List available resources and scripts
    - Extract and filter tool recommendations
    - Apply progressive disclosure

    The context is formatted as markdown for optimal LLM consumption.
    """

    def __init__(
        self,
        skills: Optional[List[SkillDefinition]] = None,
        matcher: Optional["SkillMatcher"] = None,
    ):
        """
        Initialize the skill context builder.

        Args:
            skills: List of skills to build context from
            matcher: Optional SkillMatcher for request matching
        """
        self._skills = skills or []
        self._matcher = matcher

    def set_skills(self, skills: List[SkillDefinition]) -> None:
        """Set the skills to build context from."""
        self._skills = skills

    def add_skill(self, skill: SkillDefinition) -> None:
        """Add a skill to the context builder."""
        self._skills.append(skill)

    def clear_skills(self) -> None:
        """Clear all skills from the context builder."""
        self._skills = []

    def get_skills(self) -> List[SkillDefinition]:
        """Get the current list of skills."""
        return self._skills.copy()

    def build_context(
        self,
        request: Optional[str] = None,
        options: Optional[ContextOptions] = None,
        include_scripts: bool = True,
    ) -> str:
        """
        Build formatted context from all skills.

        Args:
            request: Optional request for skill matching/filtering
            options: Context building options
            include_scripts: Whether to include script information

        Returns:
            Formatted context string for prompt injection
        """
        if not self._skills:
            return ""

        options = options or ContextOptions()
        skills_to_include = self._skills

        # If request provided and matcher available, filter by match
        if request and self._matcher:
            matched = self._matcher.match(
                request, skills=self._skills, threshold=0.0
            )
            if matched:
                skills_to_include = [skill for skill, _ in matched]

        context_parts = []
        for skill in skills_to_include:
            skill_context = self._build_skill_context(
                skill, options, include_scripts
            )
            if skill_context:
                context_parts.append(skill_context)

        if not context_parts:
            return ""

        return "\n\n---\n\n".join(context_parts)

    def _build_skill_context(
        self,
        skill: SkillDefinition,
        options: ContextOptions,
        include_scripts: bool,
    ) -> str:
        """Build context for a single skill."""
        parts = []

        # Header
        parts.append(f"## Skill: {skill.metadata.name}")
        parts.append(f"*{skill.metadata.description.strip()}*")

        # Body content (Level 2 - progressive disclosure)
        if options.include_body and skill.body:
            body = skill.body
            if options.max_body_length and len(body) > options.max_body_length:
                body = body[:options.max_body_length] + "\n\n...(truncated)"
            parts.append("")
            parts.append(body)

        # Script availability listing
        if include_scripts and options.include_scripts and skill.scripts:
            parts.append(self._format_scripts_section(skill))

        # Resource listing (Level 3 references)
        if options.include_resources:
            resource_section = self._format_resources_section(skill)
            if resource_section:
                parts.append(resource_section)

        # Tool recommendations
        if options.include_tool_recommendations and skill.recommended_tools:
            parts.append(self._format_tool_recommendations_section(skill))

        return "\n".join(parts)

    def _format_scripts_section(self, skill: SkillDefinition) -> str:
        """Format the scripts section for a skill."""
        lines = ["\n### Available Scripts"]

        for name, script in skill.scripts.items():
            mode = script.mode or "auto"
            desc = script.description or f"Execute {name}"
            lines.append(f"- **{name}**: `{script.path}` (mode: {mode})")
            lines.append(f"  - {desc}")

            if script.parameters:
                lines.append("  - Parameters:")
                for param_name, param_def in script.parameters.items():
                    param_type = param_def.get("type", "any") if isinstance(param_def, dict) else "any"
                    required = param_def.get("required", False) if isinstance(param_def, dict) else False
                    req_marker = " (required)" if required else ""
                    lines.append(f"    - `{param_name}`: {param_type}{req_marker}")

        lines.append("")
        lines.append(
            "To execute a script, use the `execute_skill_script` tool or "
            "call the script directly via Bash/Python."
        )
        return "\n".join(lines)

    def _format_resources_section(self, skill: SkillDefinition) -> str:
        """Format the resources section for a skill."""
        lines = []
        has_resources = False

        for resource_type, label in [
            ("references", "References"),
            ("examples", "Examples"),
            ("assets", "Assets"),
        ]:
            resources = getattr(skill, resource_type, {})
            if resources:
                has_resources = True
                if not lines:
                    lines.append("\n### Available Resources")
                lines.append(f"\n**{label}:**")
                for name, resource in resources.items():
                    lines.append(f"- `{resource.path}`")

        if has_resources:
            lines.append("")
            lines.append(
                "To load a resource, use `load_skill_resource(skill_name, path)`."
            )
            return "\n".join(lines)
        return ""

    def _format_tool_recommendations_section(self, skill: SkillDefinition) -> str:
        """Format the tool recommendations section for a skill."""
        if not skill.recommended_tools:
            return ""

        lines = ["\n### Recommended Tools"]
        lines.append(
            "The following tools are recommended when working with this skill:"
        )
        for tool in skill.recommended_tools:
            lines.append(f"- `{tool}`")
        return "\n".join(lines)

    def get_resource_paths(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Get available resource paths organized by skill and type.

        Returns:
            Dictionary mapping skill names to resource types to paths:
            {
                "skill-name": {
                    "references": ["path1", "path2"],
                    "examples": ["path1"],
                    "scripts": ["path1"],
                    "assets": []
                }
            }
        """
        result: Dict[str, Dict[str, List[str]]] = {}

        for skill in self._skills:
            skill_name = skill.metadata.name
            result[skill_name] = {
                "references": [r.path for r in skill.references.values()],
                "examples": [e.path for e in skill.examples.values()],
                "scripts": [s.path for s in skill.scripts.values()],
                "assets": [a.path for a in skill.assets.values()],
            }

        return result

    def get_script_info(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Get detailed script information organized by skill.

        Returns:
            Dictionary mapping skill names to script info:
            {
                "skill-name": {
                    "script-name": {
                        "path": "scripts/run.py",
                        "mode": "native",
                        "description": "Run the script",
                        "parameters": {...}
                    }
                }
            }
        """
        result: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for skill in self._skills:
            skill_name = skill.metadata.name
            scripts: Dict[str, Dict[str, Any]] = {}

            for name, script in skill.scripts.items():
                scripts[name] = {
                    "path": script.path,
                    "mode": script.mode or "auto",
                    "description": script.description,
                    "parameters": script.parameters,
                    "executable": script.executable,
                }

            if scripts:
                result[skill_name] = scripts

        return result

    def get_recommended_tools(
        self,
        request: str,
        available_tools: Optional[List[str]] = None,
        skills: Optional[List[SkillDefinition]] = None,
    ) -> List[str]:
        """
        Get recommended tools based on skills matching the request.

        Logic:
        1. Match skills to request using SkillMatcher (if available)
        2. For each matching skill, get its recommended_tools
        3. Filter to only include available tools (if provided)
        4. Return unique list preserving order

        Args:
            request: User request to match skills against
            available_tools: Optional list of available tool names to filter by
            skills: Optional list of skills (uses instance skills if None)

        Returns:
            List of unique recommended tool names
        """
        skills_to_check = skills if skills is not None else self._skills

        if not skills_to_check:
            return []

        # Collect recommended tools from matching skills
        recommended: List[str] = []
        seen: Set[str] = set()

        # If matcher is available, use it to filter by match score
        if self._matcher and request:
            matched = self._matcher.match(
                request, skills=skills_to_check, threshold=0.0
            )
            matched_skills = [skill for skill, _ in matched]
        else:
            # No matcher or empty request - use all skills
            matched_skills = skills_to_check

        for skill in matched_skills:
            for tool in skill.recommended_tools:
                # Filter by availability if provided
                if available_tools is not None and tool not in available_tools:
                    logger.debug(
                        f"Recommended tool '{tool}' from skill "
                        f"'{skill.metadata.name}' not in available tools"
                    )
                    continue

                # Preserve uniqueness and order
                if tool not in seen:
                    seen.add(tool)
                    recommended.append(tool)

        return recommended

    def format_tool_recommendations(
        self,
        request: str,
        available_tools: Optional[List[str]] = None,
        tool_descriptions: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Format tool recommendations as a prompt-ready string.

        Args:
            request: User request to match skills against
            available_tools: Optional list of available tool names
            tool_descriptions: Optional dict of tool name to description

        Returns:
            Formatted string for prompt injection
        """
        tools = self.get_recommended_tools(request, available_tools)

        if not tools:
            return ""

        lines = [
            "## Tool Recommendations",
            "",
            "Based on attached skills, the following tools are recommended:",
            "",
        ]

        for tool in tools:
            if tool_descriptions and tool in tool_descriptions:
                lines.append(f"- **{tool}**: {tool_descriptions[tool]}")
            else:
                lines.append(f"- `{tool}`")

        return "\n".join(lines)


class SkillContextError(Exception):
    """Raised when skill context building fails."""
    pass

