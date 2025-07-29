"""
Planner Agent

Specialized agent for creating task execution sequences with DSL support.
Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
"""

import json
import logging
from typing import Dict, List, Any

# LangChain dependencies
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain.schema import AgentAction, AgentFinish

# Import our system's core components
from ..base_agent import BaseAgent
from ...core.models.agent_models import AgentConfig
from app.services.llm_integration import LLMIntegrationManager
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Agent specialized in planning task execution sequences.

    Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the planner agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # DSL constructs supported by the planner
        self.dsl_constructs = {
            "task": "Execute a single task",
            "parallel": "Execute multiple tasks in parallel",
            "if": "Conditional execution based on conditions",
            "sequence": "Execute tasks in sequence",
            "loop": "Repeat tasks based on conditions"
        }

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the planner agent."""
        logger.info(f"Planner agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task sequence planning using LangChain-based approach.
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            subtask_breakdown = task_data.get("subtask_breakdown", {})
            available_tools = task_data.get("available_tools", [])

            if not subtask_breakdown:
                raise ValueError("No subtask breakdown provided for planning")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Prepare planning input
            planning_context = self._build_planning_context(subtask_breakdown, available_tools)
            planning_input = {
                "input": f"Create optimized task execution sequence",
                "task_description": f"""
                Subtask Breakdown: {json.dumps(subtask_breakdown, indent=2)}
                Available Tools: {available_tools}

                {planning_context}

                Create an optimized execution sequence that:
                1. Respects task dependencies (collect → process → analyze → generate)
                2. Maximizes parallelization where possible
                3. Includes quality control checkpoints
                4. Uses appropriate DSL constructs for workflow control
                5. Considers available tools and resources

                DSL Constructs Available:
                - task: Execute a single task
                - parallel: Execute multiple tasks in parallel
                - if: Conditional execution based on conditions
                - sequence: Execute tasks in sequence
                - loop: Repeat tasks based on conditions

                Provide response in JSON format as an array of execution steps:
                [
                    {{
                        "task": "task_name",
                        "category": "category",
                        "tools": ["tool1", "tool2"]
                    }},
                    {{
                        "parallel": [
                            {{"task": "task1", "category": "category1", "tools": []}},
                            {{"task": "task2", "category": "category2", "tools": []}}
                        ]
                    }},
                    {{
                        "if": "condition",
                        "then": [
                            {{"task": "conditional_task", "category": "category", "tools": []}}
                        ],
                        "else": [
                            {{"task": "alternative_task", "category": "category", "tools": []}}
                        ]
                    }}
                ]
                """,
                "expected_output": "Optimized task execution sequence with DSL constructs",
                "input_data": task_data
            }

            # Execute the planning task using LangChain agent
            result = await agent_executor.ainvoke(planning_input)

            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))

            # Parse the result
            if isinstance(actual_output, str):
                try:
                    sequence = json.loads(actual_output)
                except json.JSONDecodeError:
                    # Fallback: create default sequence
                    sequence = self._create_default_sequence(subtask_breakdown)
            else:
                sequence = actual_output

            # Validate and optimize the sequence
            validated_sequence = self._validate_sequence(sequence, subtask_breakdown)
            optimized_sequence = self._optimize_sequence(validated_sequence)

            # Store in memory for future reference
            self.add_memory('last_plan', {
                'subtask_breakdown': subtask_breakdown,
                'sequence': optimized_sequence,
                'timestamp': context.get('timestamp')
            })

            self.set_available()

            return {
                'sequence': optimized_sequence,
                'total_steps': len(optimized_sequence),
                'estimated_duration': self._estimate_duration(optimized_sequence),
                'parallelizable_steps': self._count_parallel_steps(optimized_sequence),
                'reasoning': f"Created optimized execution plan with {len(optimized_sequence)} steps using LangChain-based planning"
            }

        except Exception as e:
            self.set_available()
            logger.error(f"Task planning failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "task_planning",
            "sequence_optimization",
            "dsl_generation",
            "workflow_design",
            "parallel_planning",
            "dependency_management"
        ]

    def _build_planning_context(self, subtask_breakdown: Dict[str, List[str]], available_tools: List[str]) -> str:
        """
        Build context information for planning.

        Args:
            subtask_breakdown: Mapping of categories to sub-tasks
            available_tools: List of available tools

        Returns:
            Formatted context string
        """
        context_lines = [
            "Planning Context:",
            f"Categories to handle: {list(subtask_breakdown.keys())}",
            f"Total sub-tasks: {sum(len(tasks) for tasks in subtask_breakdown.values())}",
            f"Available tools: {len(available_tools)}",
            "",
            "Sub-task Details:"
        ]

        for category, tasks in subtask_breakdown.items():
            context_lines.append(f"  {category.upper()}: {tasks}")

        context_lines.extend([
            "",
            "Quality Control Requirements:",
            "- collect/process tasks need examination by supervisor",
            "- analyze/generate tasks need acceptance by director",
            "- Failed quality checks should trigger retry or escalation"
        ])

        return "\n".join(context_lines)

    def _create_default_sequence(self, subtask_breakdown: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Create a default execution sequence when planning fails.

        Args:
            subtask_breakdown: Subtask breakdown to create sequence for

        Returns:
            Default sequence
        """
        sequence = []

        # Define execution order based on dependencies
        execution_order = ["answer", "collect", "process", "analyze", "generate"]

        for category in execution_order:
            if category in subtask_breakdown:
                tasks = subtask_breakdown[category]

                if len(tasks) == 1:
                    # Single task
                    sequence.append({
                        "task": tasks[0],
                        "category": category,
                        "tools": []
                    })
                else:
                    # Multiple tasks - can be parallelized
                    parallel_tasks = []
                    for task in tasks:
                        parallel_tasks.append({
                            "task": task,
                            "category": category,
                            "tools": []
                        })
                    sequence.append({"parallel": parallel_tasks})

        return sequence

    def _validate_sequence(self, sequence: List[Dict[str, Any]], subtask_breakdown: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Validate the planned sequence.

        Args:
            sequence: Sequence to validate
            subtask_breakdown: Original subtask breakdown

        Returns:
            Validated sequence
        """
        if not isinstance(sequence, list):
            return self._create_default_sequence(subtask_breakdown)

        validated = []

        for step in sequence:
            if isinstance(step, dict):
                validated_step = self._validate_step(step, subtask_breakdown)
                if validated_step:
                    validated.append(validated_step)

        # Ensure we have at least one step
        if not validated:
            validated = self._create_default_sequence(subtask_breakdown)

        return validated

    def _validate_step(self, step: Dict[str, Any], subtask_breakdown: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate a single step in the sequence.

        Args:
            step: Step to validate
            subtask_breakdown: Original subtask breakdown

        Returns:
            Validated step or None if invalid
        """
        if "task" in step:
            # Single task step
            task_name = step["task"]
            if self._is_valid_task(task_name, subtask_breakdown):
                return {
                    "task": task_name,
                    "category": step.get("category", self._get_task_category(task_name, subtask_breakdown)),
                    "tools": step.get("tools", [])
                }

        elif "parallel" in step:
            # Parallel execution step
            parallel_tasks = step["parallel"]
            if isinstance(parallel_tasks, list):
                validated_parallel = []
                for task_step in parallel_tasks:
                    validated_task = self._validate_step(task_step, subtask_breakdown)
                    if validated_task:
                        validated_parallel.append(validated_task)

                if validated_parallel:
                    return {"parallel": validated_parallel}

        elif "if" in step:
            # Conditional step
            condition = step.get("if")
            then_steps = step.get("then", [])
            else_steps = step.get("else", [])

            if condition and then_steps:
                validated_then = []
                for then_step in then_steps:
                    validated_step = self._validate_step(then_step, subtask_breakdown)
                    if validated_step:
                        validated_then.append(validated_step)

                validated_conditional = {
                    "if": condition,
                    "then": validated_then
                }

                if else_steps:
                    validated_else = []
                    for else_step in else_steps:
                        validated_step = self._validate_step(else_step, subtask_breakdown)
                        if validated_step:
                            validated_else.append(validated_step)
                    if validated_else:
                        validated_conditional["else"] = validated_else

                return validated_conditional

        return None

    def _is_valid_task(self, task_name: str, subtask_breakdown: Dict[str, List[str]]) -> bool:
        """
        Check if a task name is valid.

        Args:
            task_name: Task name to check
            subtask_breakdown: Subtask breakdown

        Returns:
            True if task is valid
        """
        for tasks in subtask_breakdown.values():
            if task_name in tasks:
                return True
        return False

    def _get_task_category(self, task_name: str, subtask_breakdown: Dict[str, List[str]]) -> str:
        """
        Get the category for a task.

        Args:
            task_name: Task name
            subtask_breakdown: Subtask breakdown

        Returns:
            Category name or "unknown"
        """
        for category, tasks in subtask_breakdown.items():
            if task_name in tasks:
                return category
        return "unknown"

    def _optimize_sequence(self, sequence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize the execution sequence.

        Args:
            sequence: Sequence to optimize

        Returns:
            Optimized sequence
        """
        # Simple optimization: group consecutive single tasks that can be parallelized
        optimized = []
        pending_parallel = []

        for step in sequence:
            if "task" in step:
                # Check if this task can be parallelized with pending tasks
                if self._can_parallelize(step, pending_parallel):
                    pending_parallel.append(step)
                else:
                    # Flush pending parallel tasks
                    if pending_parallel:
                        if len(pending_parallel) == 1:
                            optimized.append(pending_parallel[0])
                        else:
                            optimized.append({"parallel": pending_parallel})
                        pending_parallel = []
                    pending_parallel.append(step)
            else:
                # Flush pending parallel tasks
                if pending_parallel:
                    if len(pending_parallel) == 1:
                        optimized.append(pending_parallel[0])
                    else:
                        optimized.append({"parallel": pending_parallel})
                    pending_parallel = []
                optimized.append(step)

        # Flush any remaining pending tasks
        if pending_parallel:
            if len(pending_parallel) == 1:
                optimized.append(pending_parallel[0])
            else:
                optimized.append({"parallel": pending_parallel})

        return optimized

    def _can_parallelize(self, step: Dict[str, Any], pending_tasks: List[Dict[str, Any]]) -> bool:
        """
        Check if a step can be parallelized with pending tasks.

        Args:
            step: Step to check
            pending_tasks: List of pending tasks

        Returns:
            True if can be parallelized
        """
        if not pending_tasks:
            return True

        step_category = step.get("category", "")

        # Check if all pending tasks are in the same category
        for pending in pending_tasks:
            pending_category = pending.get("category", "")
            if step_category != pending_category:
                return False

        # Same category tasks can usually be parallelized
        return True

    def _estimate_duration(self, sequence: List[Dict[str, Any]]) -> str:
        """
        Estimate execution duration for the sequence.

        Args:
            sequence: Execution sequence

        Returns:
            Estimated duration string
        """
        total_steps = 0
        parallel_groups = 0

        for step in sequence:
            if "task" in step:
                total_steps += 1
            elif "parallel" in step:
                parallel_groups += 1
                # Parallel tasks count as 1 time unit
                total_steps += 1
            else:
                total_steps += 1

        # Simple heuristic: each step takes ~30 seconds
        estimated_seconds = total_steps * 30

        if estimated_seconds < 60:
            return f"{estimated_seconds} seconds"
        elif estimated_seconds < 3600:
            minutes = estimated_seconds // 60
            return f"{minutes} minutes"
        else:
            hours = estimated_seconds // 3600
            minutes = (estimated_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _count_parallel_steps(self, sequence: List[Dict[str, Any]]) -> int:
        """
        Count the number of parallel execution groups.

        Args:
            sequence: Execution sequence

        Returns:
            Number of parallel groups
        """
        count = 0
        for step in sequence:
            if "parallel" in step:
                count += 1
        return count

    def get_planning_history(self) -> List[Dict[str, Any]]:
        """
        Get history of execution plans.

        Returns:
            List of planning history entries
        """
        history = []
        last_plan = self.get_memory('last_plan')
        if last_plan:
            history.append(last_plan)
        return history

    def analyze_plan_efficiency(self, sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the efficiency of an execution plan.

        Args:
            sequence: Execution sequence to analyze

        Returns:
            Dictionary containing efficiency analysis
        """
        total_tasks = 0
        parallel_tasks = 0
        sequential_steps = 0

        for step in sequence:
            if "task" in step:
                total_tasks += 1
                sequential_steps += 1
            elif "parallel" in step:
                parallel_group = step["parallel"]
                if isinstance(parallel_group, list):
                    total_tasks += len(parallel_group)
                    parallel_tasks += len(parallel_group)
                sequential_steps += 1
            else:
                sequential_steps += 1

        parallelization_ratio = parallel_tasks / total_tasks if total_tasks > 0 else 0
        efficiency_score = min(parallelization_ratio * 100, 100)

        return {
            "total_tasks": total_tasks,
            "parallel_tasks": parallel_tasks,
            "sequential_steps": sequential_steps,
            "parallelization_ratio": parallelization_ratio,
            "efficiency_score": efficiency_score,
            "efficiency_level": "high" if efficiency_score > 70 else "medium" if efficiency_score > 40 else "low"
        }

    async def create_specialized_plan(self, plan_type: str, planning_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create specialized execution plan based on plan type.

        Args:
            plan_type: Type of specialized plan
            planning_data: Planning data and requirements
            context: Execution context

        Returns:
            Specialized plan result
        """
        plan_types = {
            "workflow_optimization": "Optimize workflow for maximum efficiency and parallelization",
            "resource_allocation": "Plan resource allocation and scheduling",
            "dependency_management": "Manage task dependencies and execution order",
            "quality_assurance": "Plan quality control checkpoints and validation",
            "error_recovery": "Plan error handling and recovery strategies"
        }

        if plan_type not in plan_types:
            raise ValueError(f"Unsupported plan type: {plan_type}")

        # Create specialized planning task data
        specialized_task_data = {
            **planning_data,
            "plan_type": plan_type,
            "planning_focus": plan_types[plan_type]
        }

        return await self.execute_task(specialized_task_data, context)

    def generate_dsl_workflow(self, sequence: List[Dict[str, Any]]) -> str:
        """
        Generate DSL workflow representation from execution sequence.

        Args:
            sequence: Execution sequence

        Returns:
            DSL workflow string
        """
        dsl_lines = []
        dsl_lines.append("workflow {")

        for i, step in enumerate(sequence):
            step_dsl = self._step_to_dsl(step, indent=1)
            dsl_lines.extend(step_dsl)

        dsl_lines.append("}")
        return "\n".join(dsl_lines)

    def _step_to_dsl(self, step: Dict[str, Any], indent: int = 0) -> List[str]:
        """Convert a step to DSL representation."""
        indent_str = "  " * indent
        dsl_lines = []

        if "task" in step:
            task_name = step["task"]
            category = step.get("category", "unknown")
            tools = step.get("tools", [])

            dsl_lines.append(f"{indent_str}task(\"{task_name}\") {{")
            dsl_lines.append(f"{indent_str}  category: \"{category}\"")
            if tools:
                dsl_lines.append(f"{indent_str}  tools: {tools}")
            dsl_lines.append(f"{indent_str}}}")

        elif "parallel" in step:
            parallel_tasks = step["parallel"]
            dsl_lines.append(f"{indent_str}parallel {{")

            for task_step in parallel_tasks:
                task_dsl = self._step_to_dsl(task_step, indent + 1)
                dsl_lines.extend(task_dsl)

            dsl_lines.append(f"{indent_str}}}")

        elif "if" in step:
            condition = step["if"]
            then_steps = step.get("then", [])
            else_steps = step.get("else", [])

            dsl_lines.append(f"{indent_str}if (\"{condition}\") {{")

            for then_step in then_steps:
                then_dsl = self._step_to_dsl(then_step, indent + 1)
                dsl_lines.extend(then_dsl)

            if else_steps:
                dsl_lines.append(f"{indent_str}}} else {{")
                for else_step in else_steps:
                    else_dsl = self._step_to_dsl(else_step, indent + 1)
                    dsl_lines.extend(else_dsl)

            dsl_lines.append(f"{indent_str}}}")

        elif "sequence" in step:
            sequence_steps = step["sequence"]
            dsl_lines.append(f"{indent_str}sequence {{")

            for seq_step in sequence_steps:
                seq_dsl = self._step_to_dsl(seq_step, indent + 1)
                dsl_lines.extend(seq_dsl)

            dsl_lines.append(f"{indent_str}}}")

        return dsl_lines

    def validate_workflow_constraints(self, sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate workflow constraints and dependencies.

        Args:
            sequence: Execution sequence to validate

        Returns:
            Validation result
        """
        validation_result = {
            "valid": True,
            "violations": [],
            "warnings": [],
            "suggestions": []
        }

        # Check dependency constraints
        executed_categories = set()

        for step in sequence:
            if "task" in step:
                category = step.get("category", "unknown")

                # Check if dependencies are satisfied
                if category == "process" and "collect" not in executed_categories:
                    validation_result["violations"].append(
                        "Process task scheduled before collect task - dependency violation"
                    )
                    validation_result["valid"] = False

                if category == "analyze" and "process" not in executed_categories:
                    validation_result["warnings"].append(
                        "Analyze task scheduled before process task - may need data processing first"
                    )

                if category == "generate" and "analyze" not in executed_categories:
                    validation_result["warnings"].append(
                        "Generate task scheduled before analyze task - may need analysis results first"
                    )

                executed_categories.add(category)

            elif "parallel" in step:
                parallel_tasks = step["parallel"]
                parallel_categories = set()

                for task_step in parallel_tasks:
                    category = task_step.get("category", "unknown")
                    parallel_categories.add(category)

                # Check if parallel tasks have conflicting dependencies
                if "collect" in parallel_categories and "process" in parallel_categories:
                    validation_result["violations"].append(
                        "Collect and process tasks cannot run in parallel - dependency conflict"
                    )
                    validation_result["valid"] = False

                executed_categories.update(parallel_categories)

        # Add suggestions for optimization
        if validation_result["valid"]:
            validation_result["suggestions"].append("Workflow dependencies are satisfied")

            # Check for optimization opportunities
            total_tasks = sum(1 for step in sequence if "task" in step)
            parallel_tasks = sum(len(step["parallel"]) for step in sequence if "parallel" in step)

            if parallel_tasks / max(total_tasks, 1) < 0.3:
                validation_result["suggestions"].append(
                    "Consider parallelizing more tasks to improve efficiency"
                )

        return validation_result

    def get_planning_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get planning templates for different types of workflows.

        Returns:
            Dictionary of planning templates
        """
        return {
            "data_pipeline": {
                "description": "Data collection, processing, and analysis pipeline",
                "typical_sequence": ["collect", "process", "analyze", "generate"],
                "parallelization": "Within categories only",
                "quality_gates": ["data_validation", "processing_verification", "analysis_review"]
            },
            "research_workflow": {
                "description": "Research and analysis workflow",
                "typical_sequence": ["collect", "analyze", "generate"],
                "parallelization": "High within collect and analyze phases",
                "quality_gates": ["source_verification", "analysis_validation", "content_review"]
            },
            "content_generation": {
                "description": "Content creation and publishing workflow",
                "typical_sequence": ["research", "generate", "review", "publish"],
                "parallelization": "Medium in research and generation phases",
                "quality_gates": ["content_quality", "editorial_review", "final_approval"]
            },
            "batch_processing": {
                "description": "High-volume batch processing workflow",
                "typical_sequence": ["collect", "process", "validate", "output"],
                "parallelization": "High across all phases",
                "quality_gates": ["input_validation", "processing_verification", "output_quality"]
            },
            "interactive_analysis": {
                "description": "Interactive data analysis and exploration",
                "typical_sequence": ["explore", "analyze", "visualize", "interpret"],
                "parallelization": "Low - sequential exploration",
                "quality_gates": ["data_quality", "analysis_accuracy", "interpretation_validity"]
            }
        }
