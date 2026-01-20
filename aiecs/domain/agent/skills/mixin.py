"""
Skill Capable Mixin

Provides skill integration capabilities for agents via a mixin pattern.

The mixin offers multiple integration strategies:
1. Direct Call API - Programmatic script execution
2. Tool Registration - Opt-in LLM-driven script execution
3. Context Injection - Default skill knowledge injection

Usage:
    from aiecs.domain.agent.skills import SkillCapableMixin
    
    class MyAgent(SkillCapableMixin, BaseAIAgent):
        pass
    
    agent = MyAgent(name="assistant", llm_client=client)
    agent.attach_skills(["python-testing"])
    context = agent.get_skill_context("write unit tests")
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from .context import SkillContext, ContextOptions
from .executor import ExecutionMode, ScriptExecutionResult, SkillScriptExecutor
from .models import SkillDefinition, SkillResource
from .registry import SkillRegistry

if TYPE_CHECKING:
    from ..tools.models import Tool
    from ..tools.registry import SkillScriptRegistry

logger = logging.getLogger(__name__)


class SkillCapableMixin:
    """
    Mixin that adds skill support to agents.
    
    Provides:
    - Skill attachment and detachment
    - Skill context injection for prompts
    - Direct script execution API
    - Optional tool registration from scripts
    - Tool recommendations from skills
    
    Integration Strategies:
    1. Direct Call: Use execute_skill_script() for programmatic control
    2. Tool Registration: Set auto_register_tools=True to register scripts as tools
    3. Context Injection: Default - skills inject knowledge into prompts
    
    Attributes:
        _attached_skills: List of attached SkillDefinition objects
        _skill_tools: Dict mapping tool names to tools created from skills
        _skill_injection_config: Dict mapping skill names to injection config
        _script_executor: SkillScriptExecutor for running scripts
        _skill_registry: SkillRegistry for loading skills by name
        _tool_registry: Optional SkillScriptRegistry for loading recommended tools
    """
    
    # These will be set during initialization
    _attached_skills: List[SkillDefinition]
    _skill_tools: Dict[str, "Tool"]
    _skill_injection_config: Dict[str, Dict[str, Any]]
    _script_executor: SkillScriptExecutor
    _skill_registry: Optional[SkillRegistry]
    _tool_registry: Optional["SkillScriptRegistry"]
    _skill_context: SkillContext
    
    def __init_skills__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        tool_registry: Optional["SkillScriptRegistry"] = None,
        script_executor: Optional[SkillScriptExecutor] = None,
    ) -> None:
        """
        Initialize skill-related state.
        
        Called by agents that include this mixin to set up skill support.
        
        Args:
            skill_registry: Registry for loading skills by name
            tool_registry: Optional registry for loading recommended tools
            script_executor: Optional custom script executor
        """
        self._attached_skills = []
        self._skill_tools = {}
        self._skill_injection_config = {}
        self._script_executor = script_executor or SkillScriptExecutor()
        self._skill_registry = skill_registry
        self._tool_registry = tool_registry
        self._skill_context = SkillContext()
    
    @property
    def attached_skills(self) -> List[SkillDefinition]:
        """Get list of attached skills."""
        return list(self._attached_skills)
    
    @property
    def skill_names(self) -> List[str]:
        """Get names of attached skills."""
        return [skill.metadata.name for skill in self._attached_skills]
    
    def has_skill(self, skill_name: str) -> bool:
        """Check if a skill is attached."""
        return any(s.metadata.name == skill_name for s in self._attached_skills)
    
    def get_attached_skill(self, skill_name: str) -> Optional[SkillDefinition]:
        """Get an attached skill by name."""
        for skill in self._attached_skills:
            if skill.metadata.name == skill_name:
                return skill
        return None
    
    # ==========================================================================
    # Skill Attachment Methods
    # ==========================================================================
    
    def attach_skills(
        self,
        skill_names: List[str],
        auto_register_tools: bool = False,
        inject_script_paths: bool = True,
    ) -> List[str]:
        """
        Attach skills by name from the skill registry.
        
        Args:
            skill_names: List of skill names to attach
            auto_register_tools: If True, register skill scripts as LLM-callable tools
            inject_script_paths: If True, include script paths in context injection
            
        Returns:
            List of successfully attached skill names
            
        Raises:
            ValueError: If skill registry is not configured
        """
        if self._skill_registry is None:
            raise ValueError(
                "Skill registry not configured. Pass skill_registry to __init_skills__ "
                "or use attach_skill_instances() instead."
            )
        
        # Get skills from registry
        skills = self._skill_registry.get_skills(skill_names)
        
        if not skills:
            logger.warning(f"No skills found for names: {skill_names}")
            return []
        
        # Attach the skill instances
        return self.attach_skill_instances(
            skills=skills,
            auto_register_tools=auto_register_tools,
            inject_script_paths=inject_script_paths,
        )
    
    def attach_skill_instances(
        self,
        skills: List[SkillDefinition],
        auto_register_tools: bool = False,
        inject_script_paths: bool = True,
    ) -> List[str]:
        """
        Attach skill instances directly.

        Same as attach_skills but accepts SkillDefinition objects.

        Args:
            skills: List of SkillDefinition objects to attach
            auto_register_tools: If True, register skill scripts as LLM-callable tools
            inject_script_paths: If True, include script paths in context injection

        Returns:
            List of successfully attached skill names
        """
        attached_names: List[str] = []

        for skill in skills:
            skill_name = skill.metadata.name

            # Skip if already attached
            if self.has_skill(skill_name):
                logger.debug(f"Skill '{skill_name}' already attached, skipping")
                continue

            # Store the skill
            self._attached_skills.append(skill)

            # Store injection config for this skill
            self._skill_injection_config[skill_name] = {
                "inject_script_paths": inject_script_paths,
            }

            # Add to skill context
            self._skill_context.add_skill(skill)

            # Conditionally register scripts as tools
            if auto_register_tools:
                self._register_skill_scripts_as_tools(skill)

            # Load recommended tools from registry (if available)
            self._load_recommended_tools(skill)

            attached_names.append(skill_name)
            logger.info(f"Attached skill: {skill_name}")

        return attached_names

    def detach_skills(self, skill_names: List[str]) -> List[str]:
        """
        Detach skills by name.

        Cleans up associated tools and injection config.

        Args:
            skill_names: List of skill names to detach

        Returns:
            List of successfully detached skill names
        """
        detached_names: List[str] = []

        for skill_name in skill_names:
            skill = self.get_attached_skill(skill_name)
            if skill is None:
                logger.debug(f"Skill '{skill_name}' not attached, skipping")
                continue

            # Remove from attached skills
            self._attached_skills = [
                s for s in self._attached_skills
                if s.metadata.name != skill_name
            ]

            # Remove injection config
            if skill_name in self._skill_injection_config:
                del self._skill_injection_config[skill_name]

            # Clean up registered tools for this skill
            self._cleanup_skill_tools(skill)

            # Update skill context
            self._skill_context.set_skills(self._attached_skills)

            detached_names.append(skill_name)
            logger.info(f"Detached skill: {skill_name}")

        return detached_names

    def detach_all_skills(self) -> List[str]:
        """
        Detach all attached skills.

        Returns:
            List of detached skill names
        """
        return self.detach_skills(self.skill_names)

    # ==========================================================================
    # Tool Registration (Strategy 2 - Opt-in)
    # ==========================================================================

    def _register_skill_scripts_as_tools(self, skill: SkillDefinition) -> None:
        """
        Register skill scripts as LLM-callable tools.

        Only called when auto_register_tools=True.

        Args:
            skill: Skill whose scripts should be registered as tools
        """
        # Import here to avoid circular imports
        from ..tools.models import Tool

        for script_name, script_resource in skill.scripts.items():
            tool_name = f"{skill.metadata.name}_{script_name}"

            # Check for naming conflicts
            if self._has_tool(tool_name):
                raise ValueError(
                    f"Tool '{tool_name}' already exists. Detach the conflicting "
                    f"skill first or use different skill/script names."
                )

            # Create tool
            tool = Tool(
                name=tool_name,
                description=self._get_script_description(skill, script_name),
                parameters=self._infer_script_parameters(script_resource),
                execute=self._create_script_executor(skill, script_resource),
                source=skill.metadata.name,
            )

            # Register tool
            self._add_tool(tool)
            self._skill_tools[tool_name] = tool
            logger.debug(f"Registered tool '{tool_name}' from skill '{skill.metadata.name}'")

    def _get_script_description(
        self, skill: SkillDefinition, script_name: str
    ) -> str:
        """
        Get description for a script tool.

        Uses YAML metadata description if available, otherwise generates a generic one.
        """
        script = skill.scripts.get(script_name)
        if script and script.description:
            return script.description
        return f"Execute {script_name} script from {skill.metadata.name} skill"

    def _infer_script_parameters(self, script_resource: SkillResource) -> Dict[str, Any]:
        """
        Infer JSON Schema parameters for a script tool.

        Uses YAML metadata parameters if available, otherwise returns generic schema.
        """
        if script_resource.parameters:
            # Convert YAML parameter definitions to JSON Schema
            properties: Dict[str, Any] = {}
            required: List[str] = []

            for param_name, param_def in script_resource.parameters.items():
                if isinstance(param_def, dict):
                    param_type = param_def.get("type", "string")
                    param_desc = param_def.get("description", "")
                    properties[param_name] = {
                        "type": param_type,
                    }
                    if param_desc:
                        properties[param_name]["description"] = param_desc
                    if param_def.get("required", False):
                        required.append(param_name)
                else:
                    # Simple string type definition
                    properties[param_name] = {"type": str(param_def)}

            return {
                "type": "object",
                "properties": properties,
                "required": required,
            }

        # Default generic parameters
        return {
            "type": "object",
            "properties": {
                "input_data": {
                    "type": "object",
                    "description": "Input data for the script",
                }
            },
            "required": [],
        }

    def _create_script_executor(
        self, skill: SkillDefinition, script: SkillResource
    ) -> Callable[[Dict[str, Any]], Any]:
        """
        Create an async executor function for a script tool.

        The executor wraps the script execution and returns a dictionary result.
        """
        async def executor(input_data: Dict[str, Any]) -> Dict[str, Any]:
            # Resolve mode from script metadata
            mode = ExecutionMode.AUTO
            if script.mode:
                mode = ExecutionMode(script.mode)

            result = await self._script_executor.execute(
                script_path=Path(skill.skill_path) / script.path,
                skill_root=skill.skill_path,
                input_data=input_data,
                mode=mode,
            )

            return {
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "execution_time": result.execution_time,
            }

        return executor

    def _cleanup_skill_tools(self, skill: SkillDefinition) -> None:
        """
        Clean up tools registered from a skill.

        Called when detaching a skill.
        """
        skill_name = skill.metadata.name
        tools_to_remove = [
            name for name, tool in self._skill_tools.items()
            if getattr(tool, "source", None) == skill_name
        ]

        for tool_name in tools_to_remove:
            self._remove_tool(tool_name)
            del self._skill_tools[tool_name]
            logger.debug(f"Removed tool '{tool_name}' from skill '{skill_name}'")

    def _load_recommended_tools(self, skill: SkillDefinition) -> None:
        """
        Load recommended tools from the tool registry.

        If a tool registry is configured, attempts to load tools
        recommended by the skill.
        """
        if self._tool_registry is None:
            return

        for tool_name in skill.recommended_tools:
            if self._tool_registry.has_tool(tool_name):
                tool = self._tool_registry.get_tool(tool_name)
                if tool and not self._has_tool(tool_name):
                    self._add_tool(tool)
                    logger.debug(
                        f"Loaded recommended tool '{tool_name}' "
                        f"for skill '{skill.metadata.name}'"
                    )

    # ==========================================================================
    # Tool Management Hooks (to be overridden by agent classes)
    # ==========================================================================

    def _has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool exists.

        Override in agent class to integrate with agent's tool system.
        Default implementation checks _skill_tools only.
        """
        return tool_name in self._skill_tools

    def _add_tool(self, tool: "Tool") -> None:
        """
        Add a tool to the agent.

        Override in agent class to integrate with agent's tool system.
        Default implementation is a no-op (tools stored in _skill_tools).
        """
        pass

    def _remove_tool(self, tool_name: str) -> None:
        """
        Remove a tool from the agent.

        Override in agent class to integrate with agent's tool system.
        Default implementation is a no-op.
        """
        pass

    # ==========================================================================
    # Strategy 1: Direct Call API (programmatic use)
    # ==========================================================================

    async def execute_skill_script(
        self,
        skill_name: str,
        script_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.AUTO,
        timeout: Optional[int] = None,
    ) -> ScriptExecutionResult:
        """
        Execute a skill script directly (programmatic use).

        This is Strategy 1 for skill script execution - direct programmatic
        control without going through LLM tool calls.

        Mode Resolution Logic:
        1. If mode is NATIVE or SUBPROCESS (explicit override):
           - Use the provided mode regardless of script metadata
        2. If mode is AUTO:
           - Check if script has mode field in YAML metadata (script.mode)
           - If script.mode exists, use it (NATIVE or SUBPROCESS from YAML)
           - If script.mode is None, pass AUTO to executor (let executor resolve)

        Args:
            skill_name: Name of the attached skill
            script_name: Name of the script (key in skill.scripts)
            input_data: Optional input data dictionary to pass to the script
            mode: Execution mode (AUTO, NATIVE, SUBPROCESS)
            timeout: Optional execution timeout in seconds

        Returns:
            ScriptExecutionResult with success status, result, and metadata

        Raises:
            ValueError: If skill is not attached or script is not found

        Example:
            >>> result = await agent.execute_skill_script(
            ...     "python-testing",
            ...     "validate_syntax",
            ...     {"code": "def foo(): pass"}
            ... )
            >>> if result.success:
            ...     print(result.result)
        """
        # Get skill from attached skills
        skill = self.get_attached_skill(skill_name)
        if skill is None:
            raise ValueError(
                f"Skill '{skill_name}' is not attached. "
                f"Use attach_skills() or attach_skill_instances() first."
            )

        # Get script from skill
        script = skill.scripts.get(script_name)
        if script is None:
            available_scripts = list(skill.scripts.keys())
            raise ValueError(
                f"Script '{script_name}' not found in skill '{skill_name}'. "
                f"Available scripts: {available_scripts}"
            )

        # Resolve execution mode
        resolved_mode = self._resolve_execution_mode(mode, script)

        # Build script path
        script_path = Path(skill.skill_path) / script.path

        # Execute the script
        result = await self._script_executor.execute(
            script_path=script_path,
            skill_root=skill.skill_path,
            input_data=input_data,
            mode=resolved_mode,
            timeout=timeout,
        )

        logger.debug(
            f"Executed script '{script_name}' from skill '{skill_name}': "
            f"success={result.success}, mode={result.mode_used.value}, "
            f"time={result.execution_time:.3f}s"
        )

        return result

    def _resolve_execution_mode(
        self,
        requested_mode: ExecutionMode,
        script: SkillResource,
    ) -> ExecutionMode:
        """
        Resolve the execution mode for a script.

        Mode resolution logic:
        1. If requested_mode is NATIVE or SUBPROCESS (explicit override):
           - Return the requested mode
        2. If requested_mode is AUTO:
           - Check if script has mode field from YAML metadata
           - If script.mode exists, convert to ExecutionMode and return
           - If script.mode is None, return AUTO (let executor resolve)

        Args:
            requested_mode: The mode requested by the caller
            script: The script resource with optional mode metadata

        Returns:
            Resolved ExecutionMode
        """
        # Explicit mode overrides script metadata
        if requested_mode != ExecutionMode.AUTO:
            return requested_mode

        # AUTO mode: check script metadata
        if script.mode is not None:
            try:
                return ExecutionMode(script.mode)
            except ValueError:
                logger.warning(
                    f"Invalid script mode '{script.mode}', falling back to AUTO"
                )
                return ExecutionMode.AUTO

        # No script metadata, let executor resolve based on file extension
        return ExecutionMode.AUTO

    async def execute_skill_script_by_path(
        self,
        skill_name: str,
        script_path: str,
        input_data: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.AUTO,
        timeout: Optional[int] = None,
    ) -> ScriptExecutionResult:
        """
        Execute a skill script by its relative path.

        Alternative to execute_skill_script() when you have the script path
        rather than the script name from the scripts dictionary.

        Args:
            skill_name: Name of the attached skill
            script_path: Path to the script relative to skill directory
                        (e.g., "scripts/validate.py")
            input_data: Optional input data dictionary
            mode: Execution mode (AUTO, NATIVE, SUBPROCESS)
            timeout: Optional execution timeout in seconds

        Returns:
            ScriptExecutionResult with success status, result, and metadata

        Raises:
            ValueError: If skill is not attached
        """
        # Get skill from attached skills
        skill = self.get_attached_skill(skill_name)
        if skill is None:
            raise ValueError(
                f"Skill '{skill_name}' is not attached. "
                f"Use attach_skills() or attach_skill_instances() first."
            )

        # Build full script path
        full_script_path = Path(skill.skill_path) / script_path

        # Execute the script directly
        result = await self._script_executor.execute(
            script_path=full_script_path,
            skill_root=skill.skill_path,
            input_data=input_data,
            mode=mode,
            timeout=timeout,
        )

        logger.debug(
            f"Executed script '{script_path}' from skill '{skill_name}': "
            f"success={result.success}, mode={result.mode_used.value}, "
            f"time={result.execution_time:.3f}s"
        )

        return result

    def list_skill_scripts(self, skill_name: str) -> Dict[str, SkillResource]:
        """
        List available scripts for a skill.

        Args:
            skill_name: Name of the attached skill

        Returns:
            Dictionary mapping script names to SkillResource objects

        Raises:
            ValueError: If skill is not attached
        """
        skill = self.get_attached_skill(skill_name)
        if skill is None:
            raise ValueError(
                f"Skill '{skill_name}' is not attached. "
                f"Use attach_skills() or attach_skill_instances() first."
            )
        return dict(skill.scripts)

    def get_script_info(
        self, skill_name: str, script_name: str
    ) -> Optional[SkillResource]:
        """
        Get information about a specific script.

        Args:
            skill_name: Name of the attached skill
            script_name: Name of the script

        Returns:
            SkillResource with script metadata, or None if not found
        """
        skill = self.get_attached_skill(skill_name)
        if skill is None:
            return None
        return skill.scripts.get(script_name)

    # ==========================================================================
    # Strategy 3: Context Injection (default)
    # ==========================================================================

    def get_skill_context(
        self,
        request: Optional[str] = None,
        include_all_skills: bool = False,
    ) -> str:
        """
        Get formatted skill context for prompt injection.

        Builds a markdown-formatted context string from attached skills,
        respecting the inject_script_paths configuration for each skill.

        Args:
            request: Optional request string for skill matching
            include_all_skills: If True, include all skills regardless of matching

        Returns:
            Formatted context string ready for prompt injection
        """
        if not self._attached_skills:
            return ""

        context_parts = []

        for skill in self._attached_skills:
            skill_name = skill.metadata.name

            # Get injection config for this skill
            config = self._skill_injection_config.get(skill_name, {})
            include_scripts = config.get("inject_script_paths", True)

            # Build context for this skill
            skill_context = self._build_single_skill_context(
                skill, include_scripts=include_scripts
            )
            if skill_context:
                context_parts.append(skill_context)

        if not context_parts:
            return ""

        return "\n\n---\n\n".join(context_parts)

    def _build_single_skill_context(
        self,
        skill: SkillDefinition,
        include_scripts: bool = True,
    ) -> str:
        """
        Build context for a single skill.

        Args:
            skill: The skill to build context for
            include_scripts: Whether to include script information

        Returns:
            Formatted context string for the skill
        """
        parts = []

        # Header
        parts.append(f"## Skill: {skill.metadata.name}")
        if skill.metadata.description:
            parts.append(f"*{skill.metadata.description.strip()}*")

        # Body content
        if skill.body:
            parts.append("")
            parts.append(skill.body)

        # Script availability listing (conditional)
        if include_scripts and skill.scripts:
            parts.append(self._format_scripts_section(skill))

        # Tool recommendations (always included)
        if skill.recommended_tools:
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
                    if isinstance(param_def, dict):
                        param_type = param_def.get("type", "any")
                        required = param_def.get("required", False)
                    else:
                        param_type = str(param_def)
                        required = False
                    req_marker = " (required)" if required else ""
                    lines.append(f"    - `{param_name}`: {param_type}{req_marker}")

        lines.append("")
        lines.append(
            "To execute a script, use `execute_skill_script` or call directly via Bash/Python."
        )
        return "\n".join(lines)

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

    def get_recommended_tools(
        self,
        request: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Get recommended tools from attached skills.

        Collects tool recommendations from all attached skills and optionally
        filters by availability.

        Args:
            request: Optional request for skill matching (currently unused)
            available_tools: Optional list of available tool names to filter by

        Returns:
            Unique list of recommended tool names, preserving order
        """
        recommended: List[str] = []
        seen: set = set()

        for skill in self._attached_skills:
            for tool in skill.recommended_tools:
                # Filter by availability if provided
                if available_tools is not None and tool not in available_tools:
                    continue

                # Preserve uniqueness and order
                if tool not in seen:
                    seen.add(tool)
                    recommended.append(tool)

        return recommended

    def list_skill_tools(self) -> Dict[str, "Tool"]:
        """
        List all tools registered from skills.

        Returns:
            Dictionary mapping tool names to Tool objects
        """
        return dict(self._skill_tools)

    async def load_skill_resource(
        self,
        skill_name: str,
        resource_path: str,
    ) -> str:
        """
        Load a skill resource by path.

        Loads the content of a reference, example, script, or asset file
        from an attached skill.

        Args:
            skill_name: Name of the attached skill
            resource_path: Path to the resource (relative to skill directory)

        Returns:
            Resource content as string

        Raises:
            ValueError: If skill is not attached or resource not found
            IOError: If resource cannot be read
        """
        skill = self.get_attached_skill(skill_name)
        if skill is None:
            raise ValueError(
                f"Skill '{skill_name}' is not attached. "
                f"Use attach_skills() or attach_skill_instances() first."
            )

        # Find the resource in the skill
        resource = self._find_resource_by_path(skill, resource_path)
        if resource is None:
            raise ValueError(
                f"Resource '{resource_path}' not found in skill '{skill_name}'"
            )

        # Load content if not already loaded
        if resource.content is None:
            full_path = Path(skill.skill_path) / resource.path
            if not full_path.exists():
                raise IOError(f"Resource file not found: {full_path}")
            resource.content = full_path.read_text(encoding="utf-8")

        return resource.content

    def _find_resource_by_path(
        self, skill: SkillDefinition, resource_path: str
    ) -> Optional[SkillResource]:
        """Find a resource in a skill by its path."""
        # Check all resource collections
        for collection in [
            skill.references,
            skill.examples,
            skill.scripts,
            skill.assets,
        ]:
            for resource in collection.values():
                if resource.path == resource_path:
                    return resource
        return None

