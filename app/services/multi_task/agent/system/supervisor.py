"""
Supervisor Agent

Specialized agent for examining outcomes of collect and process tasks.
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


class SupervisorAgent(BaseAgent):
    """
    Agent specialized in supervising and examining task outcomes.

    This agent examines the results of 'collect' and 'process' category tasks
    to ensure quality, credibility, and completeness before proceeding.
    Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the supervisor agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # Quality criteria for different task types - moved from hardcoded to configurable
        self.quality_criteria = {
            "collect": {
                "data_completeness": 0.8,
                "source_credibility": 0.7,
                "data_freshness": 0.6,
                "relevance": 0.8
            },
            "process": {
                "data_integrity": 0.9,
                "transformation_accuracy": 0.8,
                "format_consistency": 0.7,
                "error_handling": 0.8
            }
        }

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the supervisor agent."""
        logger.info(f"Supervisor agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task outcome examination using LangChain-based approach.

        Args:
            task_data: Contains task name, category, and result to examine
            context: Execution context

        Returns:
            Dictionary containing examination results
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            task_name = task_data.get("task_name")
            category = task_data.get("category")
            task_result = task_data.get("task_result")

            if not all([task_name, category, task_result]):
                raise ValueError("Missing required examination parameters")

            if category not in ["collect", "process"]:
                raise ValueError(f"Supervisor only examines collect/process tasks, got: {category}")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Prepare examination input
            examination_context = self._build_examination_context(task_name, category, task_result)
            criteria_description = self._get_criteria_description(category)

            examination_input = {
                "input": f"Examine {category} task outcome for quality and compliance",
                "task_description": f"""
                Task Name: {task_name}
                Category: {category.upper()}
                Task Result: {json.dumps(task_result, indent=2)}

                {examination_context}

                Quality Criteria for {category.upper()} tasks:
                {criteria_description}

                Conduct a thorough examination of this task outcome including:
                1. Quality assessment against established criteria
                2. Data completeness and integrity verification
                3. Source credibility and reliability analysis
                4. Format consistency and structure validation
                5. Error detection and issue identification
                6. Compliance with category-specific requirements
                7. Overall score calculation and pass/fail determination

                Provide response in JSON format:
                {{
                    "task": "{task_name}",
                    "category": "{category}",
                    "passed": boolean,
                    "overall_score": float (0.0-1.0),
                    "criteria_scores": {{
                        "criterion1": float,
                        "criterion2": float
                    }},
                    "issues": ["issue1", "issue2"],
                    "recommendations": ["recommendation1", "recommendation2"],
                    "confidence": float (0.0-1.0),
                    "reasoning": "detailed reasoning for the assessment"
                }}
                """,
                "expected_output": f"Comprehensive quality examination for {category} task with detailed assessment",
                "input_data": task_data
            }

            # Execute the examination task using LangChain agent
            result = await agent_executor.ainvoke(examination_input)

            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))

            # Parse the result
            if isinstance(actual_output, str):
                try:
                    examination_result = json.loads(actual_output)
                except json.JSONDecodeError:
                    # Fallback: create default examination result
                    examination_result = self._create_default_examination(task_name, category, task_result)
            else:
                examination_result = actual_output

            # Validate and enhance the examination result
            validated_result = self._validate_examination_result(examination_result, task_name, category)

            # Store in memory for future reference
            self.add_memory('last_examination', {
                'task_name': task_name,
                'category': category,
                'result': validated_result,
                'timestamp': context.get('timestamp')
            })

            # Update performance metrics
            passed = validated_result.get('passed', False)
            overall_score = validated_result.get('overall_score', 0.0)
            self.update_performance_metrics(
                execution_time=1.0,  # Placeholder
                quality_score=overall_score,
                success=passed
            )

            self.set_available()

            return validated_result

        except Exception as e:
            self.set_available()
            logger.error(f"Task examination failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "outcome_examination",
            "quality_assessment",
            "credibility_analysis",
            "data_validation",
            "process_verification",
            "issue_identification"
        ]

    def _build_examination_context(self, task_name: str, category: str, task_result: Dict[str, Any]) -> str:
        """
        Build context information for examination.

        Args:
            task_name: Name of the task being examined
            category: Category of the task
            task_result: Result to examine

        Returns:
            Formatted context string
        """
        context_lines = [
            "Examination Context:",
            f"Task: {task_name}",
            f"Category: {category}",
            f"Result Type: {type(task_result).__name__}",
            ""
        ]

        # Add category-specific context
        if category == "collect":
            context_lines.extend([
                "Collection Task Focus:",
                "- Data completeness and coverage",
                "- Source reliability and credibility",
                "- Data freshness and timeliness",
                "- Relevance to the original request",
                "- Proper data structure and format"
            ])
        elif category == "process":
            context_lines.extend([
                "Processing Task Focus:",
                "- Data integrity after transformation",
                "- Accuracy of processing operations",
                "- Consistency of output format",
                "- Error handling and edge cases",
                "- Performance and efficiency"
            ])

        return "\n".join(context_lines)

    def _get_criteria_description(self, category: str) -> str:
        """
        Get description of quality criteria for a category.

        Args:
            category: Task category

        Returns:
            Formatted criteria description
        """
        criteria = self.quality_criteria.get(category, {})
        lines = []

        for criterion, threshold in criteria.items():
            lines.append(f"- {criterion.replace('_', ' ').title()}: minimum {threshold}")

        return "\n".join(lines)

    def _create_default_examination(self, task_name: str, category: str, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a default examination result when parsing fails.

        Args:
            task_name: Task name
            category: Task category
            task_result: Task result

        Returns:
            Default examination result
        """
        # Simple heuristic-based examination
        has_data = bool(task_result and task_result.get('result'))
        has_errors = bool(task_result.get('error') or task_result.get('error_message'))

        overall_score = 0.7 if has_data and not has_errors else 0.3
        passed = overall_score >= 0.6

        criteria = self.quality_criteria.get(category, {})
        criteria_scores = {criterion: overall_score for criterion in criteria.keys()}

        return {
            "task": task_name,
            "category": category,
            "passed": passed,
            "overall_score": overall_score,
            "criteria_scores": criteria_scores,
            "issues": ["Automatic examination - manual review recommended"] if not passed else [],
            "recommendations": ["Review task execution and retry if necessary"] if not passed else [],
            "confidence": 0.5,
            "reasoning": f"Automatic examination based on data presence and error status"
        }

    def _validate_examination_result(self, result: Dict[str, Any], task_name: str, category: str) -> Dict[str, Any]:
        """
        Validate and enhance examination result.

        Args:
            result: Examination result to validate
            task_name: Task name
            category: Task category

        Returns:
            Validated examination result
        """
        if not isinstance(result, dict):
            return self._create_default_examination(task_name, category, {})

        # Ensure required fields
        validated = {
            "task": result.get("task", task_name),
            "category": result.get("category", category),
            "passed": bool(result.get("passed", False)),
            "overall_score": max(0.0, min(1.0, float(result.get("overall_score", 0.0)))),
            "criteria_scores": result.get("criteria_scores", {}),
            "issues": result.get("issues", []) if isinstance(result.get("issues"), list) else [],
            "recommendations": result.get("recommendations", []) if isinstance(result.get("recommendations"), list) else [],
            "confidence": max(0.0, min(1.0, float(result.get("confidence", 0.5)))),
            "reasoning": result.get("reasoning", "No reasoning provided")
        }

        # Validate criteria scores
        expected_criteria = self.quality_criteria.get(category, {})
        for criterion in expected_criteria.keys():
            if criterion not in validated["criteria_scores"]:
                validated["criteria_scores"][criterion] = validated["overall_score"]
            else:
                score = validated["criteria_scores"][criterion]
                validated["criteria_scores"][criterion] = max(0.0, min(1.0, float(score)))

        # Ensure pass/fail consistency with scores
        min_threshold = 0.6
        if validated["overall_score"] < min_threshold:
            validated["passed"] = False
            if not validated["issues"]:
                validated["issues"].append(f"Overall score {validated['overall_score']:.2f} below threshold {min_threshold}")

        return validated

    def get_examination_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about examinations performed.

        Returns:
            Dictionary containing examination statistics
        """
        return {
            "total_examinations": self.total_tasks_executed,
            "passed_examinations": self.successful_tasks,
            "failed_examinations": self.failed_tasks,
            "pass_rate": self.successful_tasks / self.total_tasks_executed if self.total_tasks_executed > 0 else 0.0,
            "average_score": self.average_quality_score or 0.0,
            "average_examination_time": self.average_execution_time or 0.0
        }

    def get_examination_history(self) -> List[Dict[str, Any]]:
        """
        Get history of examinations.

        Returns:
            List of examination history entries
        """
        history = []
        last_examination = self.get_memory('last_examination')
        if last_examination:
            history.append(last_examination)
        return history

    def analyze_quality_trends(self) -> Dict[str, Any]:
        """
        Analyze quality trends in examinations.

        Returns:
            Dictionary containing trend analysis
        """
        # This could be expanded to analyze trends across multiple examinations
        last_examination = self.get_memory('last_examination')
        if not last_examination:
            return {"trends": "No examination history available"}

        result = last_examination.get('result', {})
        overall_score = result.get('overall_score', 0.0)

        return {
            "latest_score": overall_score,
            "quality_level": "high" if overall_score > 0.8 else "medium" if overall_score > 0.6 else "low",
            "improvement_needed": overall_score < 0.7,
            "key_issues": result.get('issues', [])
        }

    def suggest_improvements(self, examination_result: Dict[str, Any]) -> List[str]:
        """
        Suggest improvements based on examination results.

        Args:
            examination_result: Examination result to analyze

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        if not examination_result.get('passed', False):
            suggestions.append("Task failed examination - consider retry with improved parameters")

        overall_score = examination_result.get('overall_score', 0.0)
        if overall_score < 0.7:
            suggestions.append("Overall quality below recommended threshold - review task implementation")

        criteria_scores = examination_result.get('criteria_scores', {})
        for criterion, score in criteria_scores.items():
            if score < 0.6:
                suggestions.append(f"Improve {criterion.replace('_', ' ')}: score {score:.2f} is below acceptable level")

        issues = examination_result.get('issues', [])
        if issues:
            suggestions.append("Address identified issues before proceeding to next tasks")

        if examination_result.get('confidence', 1.0) < 0.7:
            suggestions.append("Low examination confidence - consider manual review")

        return suggestions

    async def conduct_specialized_examination(self, examination_type: str, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct specialized examination based on examination type.

        Args:
            examination_type: Type of specialized examination
            task_data: Task data to examine
            context: Execution context

        Returns:
            Specialized examination result
        """
        examination_types = {
            "data_quality": "Comprehensive data quality assessment",
            "source_verification": "Source credibility and reliability verification",
            "format_validation": "Data format and structure validation",
            "completeness_check": "Data completeness and coverage analysis",
            "integrity_audit": "Data integrity and consistency audit"
        }

        if examination_type not in examination_types:
            raise ValueError(f"Unsupported examination type: {examination_type}")

        # Create specialized examination task data
        specialized_task_data = {
            **task_data,
            "examination_type": examination_type,
            "examination_focus": examination_types[examination_type]
        }

        return await self.execute_task(specialized_task_data, context)

    def assess_data_quality(self, task_result: Dict[str, Any], category: str) -> Dict[str, Any]:
        """
        Assess data quality of task result.

        Args:
            task_result: Task result to assess
            category: Task category

        Returns:
            Data quality assessment
        """
        quality_factors = {
            "completeness": 0.0,
            "accuracy": 0.0,
            "consistency": 0.0,
            "timeliness": 0.0,
            "validity": 0.0
        }

        # Assess completeness
        if task_result.get('result'):
            quality_factors["completeness"] = 0.8
            if isinstance(task_result['result'], (dict, list)) and len(task_result['result']) > 0:
                quality_factors["completeness"] = 1.0

        # Assess accuracy (based on error presence)
        if not task_result.get('error') and not task_result.get('error_message'):
            quality_factors["accuracy"] = 0.9

        # Assess consistency (based on data structure)
        if task_result.get('metadata') and task_result.get('result'):
            quality_factors["consistency"] = 0.8

        # Assess timeliness (based on execution time)
        execution_time = task_result.get('execution_time', 0)
        if execution_time > 0 and execution_time < 300:  # Less than 5 minutes
            quality_factors["timeliness"] = 0.9
        elif execution_time < 600:  # Less than 10 minutes
            quality_factors["timeliness"] = 0.7

        # Assess validity (based on category-specific criteria)
        if category == "collect":
            if task_result.get('sources') or task_result.get('source_urls'):
                quality_factors["validity"] = 0.8
        elif category == "process":
            if task_result.get('processed_data') or task_result.get('transformation_log'):
                quality_factors["validity"] = 0.8

        overall_quality = sum(quality_factors.values()) / len(quality_factors)

        return {
            "overall_quality": overall_quality,
            "quality_factors": quality_factors,
            "quality_level": "high" if overall_quality > 0.8 else "medium" if overall_quality > 0.6 else "low",
            "improvement_areas": [factor for factor, score in quality_factors.items() if score < 0.7],
            "strengths": [factor for factor, score in quality_factors.items() if score > 0.8]
        }

    def generate_examination_report(self, examination_result: Dict[str, Any]) -> str:
        """
        Generate a formatted examination report.

        Args:
            examination_result: Examination result to report on

        Returns:
            Formatted examination report
        """
        task_name = examination_result.get('task', 'Unknown')
        category = examination_result.get('category', 'Unknown')
        passed = examination_result.get('passed', False)
        overall_score = examination_result.get('overall_score', 0.0)

        report_lines = [
            f"EXAMINATION REPORT",
            f"==================",
            f"Task: {task_name}",
            f"Category: {category.upper()}",
            f"Status: {'PASSED' if passed else 'FAILED'}",
            f"Overall Score: {overall_score:.2f}",
            f"",
            f"CRITERIA ASSESSMENT:",
        ]

        criteria_scores = examination_result.get('criteria_scores', {})
        for criterion, score in criteria_scores.items():
            status = "✓" if score >= 0.6 else "✗"
            report_lines.append(f"  {status} {criterion.replace('_', ' ').title()}: {score:.2f}")

        issues = examination_result.get('issues', [])
        if issues:
            report_lines.extend([
                f"",
                f"IDENTIFIED ISSUES:"
            ])
            for issue in issues:
                report_lines.append(f"  - {issue}")

        recommendations = examination_result.get('recommendations', [])
        if recommendations:
            report_lines.extend([
                f"",
                f"RECOMMENDATIONS:"
            ])
            for rec in recommendations:
                report_lines.append(f"  • {rec}")

        reasoning = examination_result.get('reasoning', '')
        if reasoning:
            report_lines.extend([
                f"",
                f"REASONING:",
                f"{reasoning}"
            ])

        confidence = examination_result.get('confidence', 0.0)
        report_lines.extend([
            f"",
            f"Examination Confidence: {confidence:.2f}"
        ])

        return "\n".join(report_lines)

    def get_examination_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get examination templates for different types of tasks.

        Returns:
            Dictionary of examination templates
        """
        return {
            "collect_data": {
                "description": "Data collection task examination",
                "criteria": ["data_completeness", "source_credibility", "data_freshness", "relevance"],
                "min_score": 0.7,
                "focus_areas": ["data_quality", "source_verification", "completeness"]
            },
            "collect_web": {
                "description": "Web scraping task examination",
                "criteria": ["data_completeness", "source_credibility", "data_freshness", "relevance"],
                "min_score": 0.6,
                "focus_areas": ["scraping_accuracy", "data_structure", "error_handling"]
            },
            "process_clean": {
                "description": "Data cleaning task examination",
                "criteria": ["data_integrity", "transformation_accuracy", "format_consistency", "error_handling"],
                "min_score": 0.8,
                "focus_areas": ["cleaning_quality", "data_preservation", "format_standardization"]
            },
            "process_transform": {
                "description": "Data transformation task examination",
                "criteria": ["data_integrity", "transformation_accuracy", "format_consistency", "error_handling"],
                "min_score": 0.8,
                "focus_areas": ["transformation_logic", "data_mapping", "output_validation"]
            },
            "process_normalize": {
                "description": "Data normalization task examination",
                "criteria": ["data_integrity", "transformation_accuracy", "format_consistency", "error_handling"],
                "min_score": 0.9,
                "focus_areas": ["normalization_rules", "consistency_checks", "standard_compliance"]
            }
        }
