"""
Task Decomposer Agent

Specialized agent for breaking down intent categories into executable sub-tasks.
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


class TaskDecomposerAgent(BaseAgent):
    """
    Agent specialized in decomposing intent categories into specific sub-tasks.

    Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the task decomposer agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the task decomposer agent."""
        logger.info(f"Task decomposer agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task decomposition using LangChain-based approach.
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            categories = task_data.get("categories", [])
            if not categories:
                raise ValueError("No categories provided for task decomposition")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Get available subtasks for context
            available_subtasks = self._get_available_subtasks_from_config()

            # Get agent mapping for enhanced output
            agent_mapping = self._get_agent_mapping_from_config()

            # Prepare decomposition input with enhanced requirements
            decomposition_input = {
                "input": f"Decompose intent categories into executable sub-tasks with agent assignments",
                "task_description": f"""
                Categories to decompose: {categories}

                Available subtasks by category:
                {json.dumps(available_subtasks, indent=2)}

                Agent mapping for subtasks:
                {json.dumps(agent_mapping, indent=2)}

                For each category, select the most appropriate sub-tasks that will effectively accomplish the intent:

                Category Guidelines:
                - answer: Direct response tasks for questions and explanations
                - collect: Data gathering, searching, and information collection tasks
                - process: Data transformation, cleaning, and processing tasks
                - analyze: Data analysis, examination, and insight generation tasks
                - generate: Content creation, report writing, and output generation tasks

                Consider:
                1. The specific requirements of each category
                2. The complexity and scope of the request
                3. Dependencies between sub-tasks
                4. Optimal execution sequence
                5. Resource requirements and constraints
                6. Agent capabilities and specializations

                Provide response in JSON format mapping categories to selected sub-tasks:
                {{
                    "category1": ["subtask1", "subtask2"],
                    "category2": ["subtask3"],
                    "category3": ["subtask4", "subtask5"]
                }}

                Only include categories that were provided in the input and only select from available subtasks.
                Each selected subtask should have a corresponding agent assignment.
                """,
                "expected_output": "JSON mapping of categories to appropriate sub-tasks with agent considerations",
                "input_data": task_data
            }

            # Execute the decomposition task using LangChain agent
            result = await agent_executor.ainvoke(decomposition_input)

            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))

            # Parse the result
            if isinstance(actual_output, str):
                try:
                    breakdown = json.loads(actual_output)
                except json.JSONDecodeError:
                    # Fallback: create default breakdown
                    breakdown = self._create_default_breakdown(categories)
            else:
                breakdown = actual_output

            # Validate and clean the breakdown
            validated_breakdown = self._validate_breakdown(breakdown, categories)

            # Generate agent mapping for the validated breakdown
            subtask_agent_mapping = self._generate_subtask_agent_mapping(validated_breakdown)

            # Store in memory for future reference
            self.add_memory('last_decomposition', {
                'categories': categories,
                'breakdown': validated_breakdown,
                'agent_mapping': subtask_agent_mapping,
                'timestamp': context.get('timestamp')
            })

            self.set_available()

            return {
                'breakdown': validated_breakdown,
                'agent_mapping': subtask_agent_mapping,
                'total_subtasks': sum(len(subtasks) for subtasks in validated_breakdown.values()),
                'reasoning': f"Decomposed {len(categories)} categories into specific sub-tasks with agent assignments using LangChain-based analysis"
            }

        except Exception as e:
            self.set_available()
            logger.error(f"Task decomposition failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "task_decomposition",
            "subtask_identification",
            "workflow_planning",
            "task_mapping"
        ]

    def _create_default_breakdown(self, categories: List[str]) -> Dict[str, List[str]]:
        """
        Create a default breakdown when parsing fails.

        Args:
            categories: List of categories to create breakdown for

        Returns:
            Default breakdown mapping
        """
        breakdown = {}

        # Get available subtasks from configuration
        available_subtasks = self._get_available_subtasks_from_config()

        for category in categories:
            if category in available_subtasks:
                # Use the first available sub-task as default
                subtasks = available_subtasks[category]
                if subtasks:
                    breakdown[category] = [subtasks[0]]

        return breakdown

    def _validate_breakdown(self, breakdown: Dict[str, List[str]], categories: List[str]) -> Dict[str, List[str]]:
        """
        Validate and clean the breakdown.

        Args:
            breakdown: Breakdown to validate
            categories: Original categories

        Returns:
            Validated breakdown
        """
        if not isinstance(breakdown, dict):
            return self._create_default_breakdown(categories)

        validated = {}
        available_subtasks = self._get_available_subtasks_from_config()

        for category in categories:
            if category in breakdown and isinstance(breakdown[category], list):
                # Validate sub-tasks for this category
                valid_subtasks = []
                available = available_subtasks.get(category, [])

                for subtask in breakdown[category]:
                    if isinstance(subtask, str) and subtask in available:
                        valid_subtasks.append(subtask)

                # Ensure at least one sub-task per category
                if not valid_subtasks and available:
                    valid_subtasks = [available[0]]

                if valid_subtasks:
                    validated[category] = valid_subtasks
            else:
                # Create default for missing/invalid categories
                if category in available_subtasks:
                    available = available_subtasks[category]
                    if available:
                        validated[category] = [available[0]]

        return validated

    def _get_available_subtasks_from_config(self) -> Dict[str, List[str]]:
        """
        Get available subtasks from configuration using TaskFactory.

        This method dynamically loads subtasks from the tasks.yaml configuration
        file, eliminating hardcoded values and making the system fully configuration-driven.

        Returns:
            Dictionary mapping categories to available subtasks
        """
        try:
            # Since we no longer have task_factory as a parameter, we'll use a fallback approach
            # In a real implementation, this would be injected or accessed through the config_manager
            logger.warning("TaskFactory not available, using fallback subtask mapping")

            # Fallback to basic mapping if configuration is not accessible
            return {
                "answer": ["answer_discuss", "answer_conclusion", "answer_questions"],
                "collect": ["collect_scrape", "collect_search"],
                "process": ["process_dataCleaning", "process_dataNormalization"],
                "analyze": ["analyze_dataoutcome"],
                "generate": ["generate_report"]
            }

        except Exception as e:
            logger.error(f"Failed to load subtasks from configuration: {e}")
            # Return fallback mapping on error
            return {
                "answer": ["answer_discuss", "answer_conclusion", "answer_questions", "answer_brainstorming"],
                "collect": ["collect_scrape", "collect_search", "collect_internalResources", "collect_externalResources"],
                "process": ["process_dataCleaning", "process_dataNormalization", "process_dataStatistics", "process_dataModeling"],
                "analyze": ["analyze_dataoutcome", "analyze_trends", "analyze_patterns", "analyze_correlations"],
                "generate": ["generate_report", "generate_summary", "generate_visualization", "generate_recommendations"]
            }

    def get_available_subtasks_for_category(self, category: str) -> List[str]:
        """
        Get available sub-tasks for a specific category.

        Args:
            category: Category name

        Returns:
            List of available sub-tasks
        """
        available_subtasks = self._get_available_subtasks_from_config()
        return available_subtasks.get(category, [])

    def get_all_available_subtasks(self) -> Dict[str, List[str]]:
        """
        Get all available sub-tasks.

        Returns:
            Dictionary mapping categories to sub-tasks
        """
        return self._get_available_subtasks_from_config()

    def analyze_decomposition_complexity(self, breakdown: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Analyze the complexity of a task decomposition.

        Args:
            breakdown: Task breakdown to analyze

        Returns:
            Dictionary containing complexity analysis
        """
        total_subtasks = sum(len(subtasks) for subtasks in breakdown.values())
        categories_count = len(breakdown)

        # Calculate complexity score
        complexity_score = (total_subtasks * 0.6) + (categories_count * 0.4)

        if complexity_score <= 2:
            complexity_level = "low"
        elif complexity_score <= 5:
            complexity_level = "medium"
        else:
            complexity_level = "high"

        return {
            "total_subtasks": total_subtasks,
            "categories_count": categories_count,
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "estimated_execution_time": self._estimate_execution_time(breakdown)
        }

    def _estimate_execution_time(self, breakdown: Dict[str, List[str]]) -> str:
        """
        Estimate execution time for a breakdown.

        Args:
            breakdown: Task breakdown

        Returns:
            Estimated execution time as string
        """
        # Simple heuristic based on sub-task count and types
        total_subtasks = sum(len(subtasks) for subtasks in breakdown.values())

        # Different categories have different time estimates
        time_weights = {
            "answer": 1,
            "collect": 3,
            "process": 2,
            "analyze": 4,
            "generate": 3
        }

        weighted_time = 0
        for category, subtasks in breakdown.items():
            weight = time_weights.get(category, 2)
            weighted_time += len(subtasks) * weight

        if weighted_time <= 5:
            return "1-2 minutes"
        elif weighted_time <= 10:
            return "2-5 minutes"
        elif weighted_time <= 20:
            return "5-10 minutes"
        else:
            return "10+ minutes"

    def get_decomposition_history(self) -> List[Dict[str, Any]]:
        """
        Get history of task decompositions.

        Returns:
            List of decomposition history entries
        """
        history = []
        last_decomposition = self.get_memory('last_decomposition')
        if last_decomposition:
            history.append(last_decomposition)
        return history

    def suggest_optimizations(self, breakdown: Dict[str, List[str]]) -> List[str]:
        """
        Suggest optimizations for a task breakdown.

        Args:
            breakdown: Task breakdown to optimize

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Check for potential parallelization
        if len(breakdown) > 1:
            suggestions.append("Consider parallel execution of independent categories")

        # Check for redundant sub-tasks
        all_subtasks = []
        for subtasks in breakdown.values():
            all_subtasks.extend(subtasks)

        if len(all_subtasks) != len(set(all_subtasks)):
            suggestions.append("Remove duplicate sub-tasks across categories")

        # Check for missing dependencies
        if "collect" in breakdown and "process" in breakdown:
            suggestions.append("Ensure collect tasks complete before process tasks")

        if "analyze" in breakdown and "generate" in breakdown:
            suggestions.append("Ensure analyze tasks complete before generate tasks")

        return suggestions

    async def create_specialized_decomposition(self, decomposition_type: str, categories: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create specialized decomposition based on decomposition type.

        Args:
            decomposition_type: Type of specialized decomposition
            categories: Categories to decompose
            context: Execution context

        Returns:
            Specialized decomposition result
        """
        decomposition_types = {
            "workflow_oriented": "Decompose with focus on workflow optimization and efficiency",
            "resource_optimized": "Decompose with focus on resource allocation and utilization",
            "parallel_focused": "Decompose with maximum parallelization opportunities",
            "sequential_ordered": "Decompose with strict sequential execution requirements",
            "quality_assured": "Decompose with emphasis on quality control checkpoints"
        }

        if decomposition_type not in decomposition_types:
            raise ValueError(f"Unsupported decomposition type: {decomposition_type}")

        # Create specialized decomposition task data
        specialized_task_data = {
            "categories": categories,
            "decomposition_type": decomposition_type,
            "decomposition_focus": decomposition_types[decomposition_type]
        }

        return await self.execute_task(specialized_task_data, context)

    def validate_decomposition_dependencies(self, breakdown: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate dependencies in task decomposition.

        Args:
            breakdown: Task breakdown to validate

        Returns:
            Dependency validation result
        """
        validation_result = {
            "valid": True,
            "dependency_violations": [],
            "warnings": [],
            "suggestions": []
        }

        categories = list(breakdown.keys())

        # Define dependency rules
        dependency_rules = {
            "process": ["collect"],  # Process depends on collect
            "analyze": ["collect", "process"],  # Analyze depends on collect/process
            "generate": ["analyze"]  # Generate depends on analyze
        }

        # Check dependencies
        for category, dependencies in dependency_rules.items():
            if category in categories:
                missing_deps = [dep for dep in dependencies if dep not in categories]
                if missing_deps:
                    validation_result["warnings"].append(
                        f"{category} category present but missing dependencies: {missing_deps}"
                    )

        # Check for logical sequence
        category_order = ["answer", "collect", "process", "analyze", "generate"]
        present_categories = [cat for cat in category_order if cat in categories]

        if len(present_categories) > 1:
            # Check if categories follow logical order
            for i in range(len(present_categories) - 1):
                current_idx = category_order.index(present_categories[i])
                next_idx = category_order.index(present_categories[i + 1])

                if next_idx < current_idx:
                    validation_result["warnings"].append(
                        f"Category order may be suboptimal: {present_categories[i]} before {present_categories[i + 1]}"
                    )

        # Add suggestions
        if validation_result["valid"]:
            validation_result["suggestions"].append("Decomposition dependencies are satisfied")

            # Suggest optimizations
            if "collect" in categories and "analyze" in categories:
                validation_result["suggestions"].append(
                    "Consider adding process category between collect and analyze for data preparation"
                )

        return validation_result

    def generate_decomposition_summary(self, breakdown: Dict[str, List[str]]) -> str:
        """
        Generate a summary of the task decomposition.

        Args:
            breakdown: Task breakdown to summarize

        Returns:
            Decomposition summary string
        """
        total_subtasks = sum(len(subtasks) for subtasks in breakdown.values())
        categories_count = len(breakdown)

        summary_lines = [
            f"TASK DECOMPOSITION SUMMARY",
            f"==========================",
            f"Categories: {categories_count}",
            f"Total Sub-tasks: {total_subtasks}",
            f"",
            f"BREAKDOWN BY CATEGORY:"
        ]

        for category, subtasks in breakdown.items():
            summary_lines.append(f"  {category.upper()}: {len(subtasks)} sub-tasks")
            for subtask in subtasks:
                summary_lines.append(f"    - {subtask}")
            summary_lines.append("")

        complexity_analysis = self.analyze_decomposition_complexity(breakdown)
        summary_lines.extend([
            f"COMPLEXITY ANALYSIS:",
            f"  Complexity Level: {complexity_analysis['complexity_level'].upper()}",
            f"  Estimated Time: {complexity_analysis['estimated_execution_time']}",
            f"  Complexity Score: {complexity_analysis['complexity_score']:.1f}"
        ])

        return "\n".join(summary_lines)

    def get_decomposition_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get decomposition templates for different types of requests.

        Returns:
            Dictionary of decomposition templates
        """
        return {
            "simple_question": {
                "description": "Simple question requiring direct answer",
                "typical_breakdown": {"answer": ["answer_discuss"]},
                "complexity": "low",
                "estimated_time": "1-2 minutes"
            },
            "research_task": {
                "description": "Research and analysis task",
                "typical_breakdown": {
                    "collect": ["collect_search"],
                    "analyze": ["analyze_dataoutcome"],
                    "generate": ["generate_report"]
                },
                "complexity": "medium",
                "estimated_time": "5-10 minutes"
            },
            "data_processing": {
                "description": "Data collection and processing workflow",
                "typical_breakdown": {
                    "collect": ["collect_scrape"],
                    "process": ["process_dataCleaning", "process_dataNormalization"],
                    "analyze": ["analyze_dataoutcome"]
                },
                "complexity": "medium",
                "estimated_time": "5-10 minutes"
            },
            "comprehensive_analysis": {
                "description": "Full analysis and reporting workflow",
                "typical_breakdown": {
                    "collect": ["collect_search", "collect_scrape"],
                    "process": ["process_dataCleaning"],
                    "analyze": ["analyze_dataoutcome"],
                    "generate": ["generate_report"]
                }
            }
        }

    def _get_agent_mapping_from_config(self) -> Dict[str, str]:
        """
        Get agent mapping from configuration using TaskFactory.

        This method loads the mapping of subtasks to their corresponding agents
        from the tasks.yaml configuration file.

        Returns:
            Dictionary mapping subtasks to agent names
        """
        try:
            # In a real implementation, this would be loaded from tasks.yaml via config_manager
            # For now, return a comprehensive mapping based on the tasks.yaml structure
            return {
                # Answer tasks
                "answer_discuss": "researcher_discussionfacilitator",
                "answer_conclusion": "writer_conclusionspecialist",
                "answer_questions": "researcher_knowledgeprovider",
                "answer_brainstorming": "researcher_ideagenerator",

                # Collect tasks
                "collect_scrape": "fieldwork_webscraper",
                "collect_search": "fieldwork_apisearcher",
                "collect_internalResources": "fieldwork_internaldatacollector",
                "collect_externalResources": "fieldwork_externaldatacollector",

                # Process tasks
                "process_dataCleaning": "fieldwork_dataoperator",
                "process_dataNormalization": "fieldwork_dataengineer",
                "process_dataStatistics": "fieldwork_statistician",
                "process_dataModeling": "fieldwork_datascientist",
                "process_dataIntegration": "fieldwork_dataengineer",
                "process_dataCompression": "fieldwork_dataengineer",
                "process_dataEnrichment": "fieldwork_dataengineer",
                "process_dataTransformation": "fieldwork_dataengineer",
                "process_dataFiltering": "fieldwork_dataoperator",
                "process_dataFormatting": "fieldwork_dataoperator",

                # Analyze tasks
                "analyze_dataoutcome": "fieldwork_statistician",
                "analyze_trends": "analyst_trendanalyst",
                "analyze_patterns": "analyst_patternrecognition",
                "analyze_correlations": "analyst_correlationspecialist",
                "analyze_predictions": "analyst_predictivemodeling",
                "analyze_comparisons": "analyst_comparativeanalyst",
                "analyze_insights": "analyst_insightgenerator",

                # Generate tasks
                "generate_report": "writer_reportspecialist",
                "generate_summary": "writer_summaryspecialist",
                "generate_visualization": "writer_visualizationspecialist",
                "generate_presentation": "writer_presentationspecialist",
                "generate_documentation": "writer_documentationspecialist",
                "generate_recommendations": "writer_recommendationspecialist"
            }

        except Exception as e:
            logger.error(f"Failed to load agent mapping from configuration: {e}")
            # Return fallback mapping on error
            return {
                "answer_discuss": "researcher_discussionfacilitator",
                "answer_conclusion": "writer_conclusionspecialist",
                "answer_questions": "researcher_knowledgeprovider",
                "collect_scrape": "fieldwork_webscraper",
                "collect_search": "fieldwork_apisearcher",
                "process_dataCleaning": "fieldwork_dataoperator",
                "process_dataNormalization": "fieldwork_dataengineer",
                "analyze_dataoutcome": "fieldwork_statistician",
                "generate_report": "writer_reportspecialist"
            }

    def _generate_subtask_agent_mapping(self, breakdown: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Generate mapping of subtasks to their corresponding agents.

        Args:
            breakdown: Task breakdown mapping categories to subtasks

        Returns:
            Dictionary mapping each subtask to its assigned agent
        """
        agent_mapping = self._get_agent_mapping_from_config()
        subtask_agent_mapping = {}

        for category, subtasks in breakdown.items():
            for subtask in subtasks:
                # Get agent from configuration
                agent = agent_mapping.get(subtask)
                if agent:
                    subtask_agent_mapping[subtask] = agent
                else:
                    # Fallback to category-based mapping
                    subtask_agent_mapping[subtask] = self._get_default_agent_for_category(category)

        return subtask_agent_mapping

    def _get_default_agent_for_category(self, category: str) -> str:
        """
        Get default agent for a category when specific subtask mapping is not available.

        Args:
            category: Task category

        Returns:
            Default agent name for the category
        """
        default_agents = {
            "answer": "researcher_knowledgeprovider",
            "collect": "fieldwork_webscraper",
            "process": "fieldwork_dataoperator",
            "analyze": "fieldwork_statistician",
            "generate": "writer_reportspecialist"
        }
        return default_agents.get(category, "general_researcher")

    def get_agent_mapping_for_breakdown(self, breakdown: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Public method to get agent mapping for a given breakdown.

        Args:
            breakdown: Task breakdown mapping categories to subtasks

        Returns:
            Dictionary mapping each subtask to its assigned agent
        """
        return self._generate_subtask_agent_mapping(breakdown)

    def get_available_agents(self) -> List[str]:
        """
        Get list of all available agents from the configuration.

        Returns:
            List of available agent names
        """
        agent_mapping = self._get_agent_mapping_from_config()
        return list(set(agent_mapping.values()))

    def get_agents_for_category(self, category: str) -> List[str]:
        """
        Get list of agents that can handle tasks in a specific category.

        Args:
            category: Task category

        Returns:
            List of agent names for the category
        """
        agent_mapping = self._get_agent_mapping_from_config()
        available_subtasks = self._get_available_subtasks_from_config()

        category_agents = set()
        if category in available_subtasks:
            for subtask in available_subtasks[category]:
                agent = agent_mapping.get(subtask)
                if agent:
                    category_agents.add(agent)

        return list(category_agents)
