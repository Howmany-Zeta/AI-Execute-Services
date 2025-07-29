"""
Director Agent

Specialized agent for accepting outcomes of analyze and generate tasks.
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


class DirectorAgent(BaseAgent):
    """
    Agent specialized in directing and accepting task outcomes.

    This agent reviews and accepts the results of 'analyze' and 'generate'
    category tasks to ensure they meet requirements and quality standards.
    Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the director agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # Performance metrics
        self.total_tasks_executed = 0
        self.successful_tasks = 0
        self.failed_tasks = 0

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the director agent."""
        logger.info(f"Director agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task outcome acceptance using LangChain-based approach.

        Args:
            task_data: Contains task name, category, and result to accept
            context: Execution context

        Returns:
            Dictionary containing acceptance results
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            task_name = task_data.get("task_name")
            category = task_data.get("category")
            task_result = task_data.get("task_result")

            if not all([task_name, category, task_result]):
                raise ValueError("Missing required acceptance parameters")

            if category not in ["analyze", "generate"]:
                raise ValueError(f"Director only accepts analyze/generate tasks, got: {category}")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Prepare acceptance input
            acceptance_input = {
                "input": f"Review and accept {category} task outcome",
                "task_description": f"""
                Task Name: {task_name}
                Category: {category}
                Task Result: {json.dumps(task_result, indent=2)}

                Please review this task outcome and provide acceptance assessment including:
                1. Whether the task meets the original requirements
                2. Quality assessment and overall score (0.0-1.0)
                3. Accuracy and reliability evaluation
                4. Check for synthetic or fabricated data
                5. Strengths and areas for improvement
                6. Specific recommendations for enhancement
                7. Confidence level in the assessment
                8. Detailed reasoning for the decision

                Provide response in JSON format with the following structure:
                {{
                    "task": "{task_name}",
                    "category": "{category}",
                    "passed": boolean,
                    "overall_score": float (0.0-1.0),
                    "criteria": {{
                        "meets_request": boolean,
                        "accurate": boolean,
                        "no_synthetic_data": boolean
                    }},
                    "criteria_scores": {{
                        "meets_request": float,
                        "accurate": float,
                        "no_synthetic_data": float
                    }},
                    "strengths": [list of strengths],
                    "weaknesses": [list of weaknesses],
                    "recommendations": [list of recommendations],
                    "confidence": float (0.0-1.0),
                    "reasoning": "detailed reasoning"
                }}
                """,
                "expected_output": f"Comprehensive acceptance assessment for {category} task with detailed evaluation criteria",
                "input_data": task_data
            }

            # Execute the acceptance task using LangChain agent
            result = await agent_executor.ainvoke(acceptance_input)

            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))

            # Parse the result
            if isinstance(actual_output, str):
                try:
                    acceptance_result = json.loads(actual_output)
                except json.JSONDecodeError:
                    # Fallback: create default acceptance result
                    acceptance_result = self._create_default_acceptance(task_name, category, task_result)
            else:
                acceptance_result = actual_output

            # Validate and enhance the acceptance result
            validated_result = self._validate_acceptance_result(acceptance_result, task_name, category)

            # Store in memory for future reference
            self.add_memory('last_acceptance', {
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
            logger.error(f"Task acceptance failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "outcome_acceptance",
            "quality_review",
            "requirement_validation",
            "content_assessment",
            "methodology_evaluation",
            "final_approval"
        ]

    def _create_default_acceptance(self, task_name: str, category: str, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a default acceptance result when parsing fails.

        Args:
            task_name: Task name
            category: Task category
            task_result: Task result

        Returns:
            Default acceptance result
        """
        # Simple heuristic-based acceptance
        has_content = bool(task_result and task_result.get('result'))
        has_errors = bool(task_result.get('error') or task_result.get('error_message'))

        overall_score = 0.7 if has_content and not has_errors else 0.3
        passed = overall_score >= 0.7

        # Basic criteria assessment
        basic_criteria = {
            "meets_request": has_content,
            "accurate": not has_errors,
            "no_synthetic_data": True  # Assume true unless proven otherwise
        }

        return {
            "task": task_name,
            "category": category,
            "passed": passed,
            "overall_score": overall_score,
            "criteria": basic_criteria,
            "criteria_scores": {
                "meets_request": overall_score,
                "accurate": overall_score,
                "no_synthetic_data": overall_score
            },
            "strengths": ["Content present"] if has_content else [],
            "weaknesses": ["Automatic review - manual assessment recommended"] if not passed else [],
            "recommendations": ["Review task execution and retry if necessary"] if not passed else [],
            "confidence": 0.5,
            "reasoning": f"Automatic acceptance based on content presence and error status"
        }

    def _validate_acceptance_result(self, result: Dict[str, Any], task_name: str, category: str) -> Dict[str, Any]:
        """
        Validate and enhance acceptance result.

        Args:
            result: Acceptance result to validate
            task_name: Task name
            category: Task category

        Returns:
            Validated acceptance result
        """
        if not isinstance(result, dict):
            return self._create_default_acceptance(task_name, category, {})

        # Ensure required fields
        validated = {
            "task": result.get("task", task_name),
            "category": result.get("category", category),
            "passed": bool(result.get("passed", False)),
            "overall_score": max(0.0, min(1.0, float(result.get("overall_score", 0.0)))),
            "criteria": result.get("criteria", {}),
            "criteria_scores": result.get("criteria_scores", {}),
            "strengths": result.get("strengths", []) if isinstance(result.get("strengths"), list) else [],
            "weaknesses": result.get("weaknesses", []) if isinstance(result.get("weaknesses"), list) else [],
            "recommendations": result.get("recommendations", []) if isinstance(result.get("recommendations"), list) else [],
            "confidence": max(0.0, min(1.0, float(result.get("confidence", 0.5)))),
            "reasoning": result.get("reasoning", "No reasoning provided")
        }

        # Ensure basic criteria are present
        basic_criteria = ["meets_request", "accurate", "no_synthetic_data"]
        for criterion in basic_criteria:
            if criterion not in validated["criteria"]:
                validated["criteria"][criterion] = validated["passed"]

        # Ensure pass/fail consistency with scores
        min_threshold = 0.7
        if validated["overall_score"] < min_threshold:
            validated["passed"] = False
            if not validated["weaknesses"]:
                validated["weaknesses"].append(f"Overall score {validated['overall_score']:.2f} below acceptance threshold {min_threshold}")

        return validated

    def get_acceptance_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about acceptances performed.

        Returns:
            Dictionary containing acceptance statistics
        """
        return {
            "total_reviews": self.total_tasks_executed,
            "accepted_tasks": self.successful_tasks,
            "rejected_tasks": self.failed_tasks,
            "acceptance_rate": self.successful_tasks / self.total_tasks_executed if self.total_tasks_executed > 0 else 0.0,
            "average_score": self.average_quality_score or 0.0,
            "average_review_time": self.average_execution_time or 0.0
        }

    def get_acceptance_history(self) -> List[Dict[str, Any]]:
        """
        Get history of acceptances.

        Returns:
            List of acceptance history entries
        """
        history = []
        last_acceptance = self.get_memory('last_acceptance')
        if last_acceptance:
            history.append(last_acceptance)
        return history

    def analyze_quality_patterns(self) -> Dict[str, Any]:
        """
        Analyze quality patterns in acceptances.

        Returns:
            Dictionary containing pattern analysis
        """
        # This could be expanded to analyze patterns across multiple acceptances
        last_acceptance = self.get_memory('last_acceptance')
        if not last_acceptance:
            return {"patterns": "No acceptance history available"}

        result = last_acceptance.get('result', {})
        overall_score = result.get('overall_score', 0.0)
        criteria = result.get('criteria', {})

        return {
            "latest_score": overall_score,
            "quality_level": "high" if overall_score > 0.8 else "medium" if overall_score > 0.7 else "low",
            "acceptance_recommended": overall_score >= 0.7,
            "key_strengths": result.get('strengths', []),
            "key_weaknesses": result.get('weaknesses', []),
            "critical_criteria_met": all(criteria.get(c, False) for c in ["meets_request", "accurate", "no_synthetic_data"])
        }

    def provide_improvement_guidance(self, acceptance_result: Dict[str, Any]) -> List[str]:
        """
        Provide improvement guidance based on acceptance results.

        Args:
            acceptance_result: Acceptance result to analyze

        Returns:
            List of improvement guidance points
        """
        guidance = []

        if not acceptance_result.get('passed', False):
            guidance.append("Task did not meet acceptance criteria - significant improvements needed")

        overall_score = acceptance_result.get('overall_score', 0.0)
        if overall_score < 0.8:
            guidance.append("Quality could be improved - aim for higher standards")

        criteria = acceptance_result.get('criteria', {})
        if not criteria.get('meets_request', True):
            guidance.append("Ensure output directly addresses the original request")

        if not criteria.get('accurate', True):
            guidance.append("Verify accuracy of all information and analysis")

        if not criteria.get('no_synthetic_data', True):
            guidance.append("Remove any synthetic or fabricated data - use only real sources")

        criteria_scores = acceptance_result.get('criteria_scores', {})
        for criterion, score in criteria_scores.items():
            if score < 0.7:
                guidance.append(f"Focus on improving {criterion.replace('_', ' ')}: current score {score:.2f}")

        weaknesses = acceptance_result.get('weaknesses', [])
        if weaknesses:
            guidance.append("Address identified weaknesses before resubmission")

        if acceptance_result.get('confidence', 1.0) < 0.7:
            guidance.append("Low review confidence - consider additional quality checks")

        return guidance

    def generate_acceptance_report(self, acceptance_result: Dict[str, Any]) -> str:
        """
        Generate a formatted acceptance report.

        Args:
            acceptance_result: Acceptance result to report on

        Returns:
            Formatted acceptance report
        """
        task_name = acceptance_result.get('task', 'Unknown')
        category = acceptance_result.get('category', 'Unknown')
        passed = acceptance_result.get('passed', False)
        overall_score = acceptance_result.get('overall_score', 0.0)

        report_lines = [
            f"ACCEPTANCE REPORT",
            f"================",
            f"Task: {task_name}",
            f"Category: {category.upper()}",
            f"Status: {'ACCEPTED' if passed else 'REJECTED'}",
            f"Overall Score: {overall_score:.2f}",
            f"",
            f"CRITERIA ASSESSMENT:",
        ]

        criteria = acceptance_result.get('criteria', {})
        for criterion, met in criteria.items():
            status = "✓" if met else "✗"
            report_lines.append(f"  {status} {criterion.replace('_', ' ').title()}")

        criteria_scores = acceptance_result.get('criteria_scores', {})
        if criteria_scores:
            report_lines.extend([
                f"",
                f"DETAILED SCORES:"
            ])
            for criterion, score in criteria_scores.items():
                report_lines.append(f"  {criterion.replace('_', ' ').title()}: {score:.2f}")

        strengths = acceptance_result.get('strengths', [])
        if strengths:
            report_lines.extend([
                f"",
                f"STRENGTHS:"
            ])
            for strength in strengths:
                report_lines.append(f"  + {strength}")

        weaknesses = acceptance_result.get('weaknesses', [])
        if weaknesses:
            report_lines.extend([
                f"",
                f"AREAS FOR IMPROVEMENT:"
            ])
            for weakness in weaknesses:
                report_lines.append(f"  - {weakness}")

        recommendations = acceptance_result.get('recommendations', [])
        if recommendations:
            report_lines.extend([
                f"",
                f"RECOMMENDATIONS:"
            ])
            for rec in recommendations:
                report_lines.append(f"  • {rec}")

        reasoning = acceptance_result.get('reasoning', '')
        if reasoning:
            report_lines.extend([
                f"",
                f"REASONING:",
                f"{reasoning}"
            ])

        return "\n".join(report_lines)

    async def conduct_specialized_review(self, review_type: str, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct specialized review based on review type.

        Args:
            review_type: Type of specialized review
            task_data: Task data to review
            context: Execution context

        Returns:
            Specialized review result
        """
        review_types = {
            "quality_assessment": "Comprehensive quality assessment focusing on accuracy and completeness",
            "requirement_validation": "Validation against original requirements and specifications",
            "content_review": "Content quality, structure, and presentation review",
            "methodology_evaluation": "Evaluation of methodology and approach used",
            "final_approval": "Final approval assessment for task completion"
        }

        if review_type not in review_types:
            raise ValueError(f"Unsupported review type: {review_type}")

        # Create specialized review task data
        specialized_task_data = {
            **task_data,
            "review_type": review_type,
            "review_focus": review_types[review_type]
        }

        return await self.execute_task(specialized_task_data, context)

    def assess_task_completeness(self, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the completeness of a task result.

        Args:
            task_result: Task result to assess

        Returns:
            Completeness assessment
        """
        completeness_score = 0.0
        completeness_factors = []

        # Check for basic result structure
        if task_result.get('result'):
            completeness_score += 0.3
            completeness_factors.append("Has main result content")

        # Check for metadata
        if task_result.get('metadata'):
            completeness_score += 0.1
            completeness_factors.append("Includes metadata")

        # Check for execution details
        if task_result.get('execution_time'):
            completeness_score += 0.1
            completeness_factors.append("Execution time recorded")

        # Check for quality metrics
        if task_result.get('quality_score'):
            completeness_score += 0.1
            completeness_factors.append("Quality metrics available")

        # Check for error handling
        if 'error' not in task_result and 'error_message' not in task_result:
            completeness_score += 0.2
            completeness_factors.append("No errors reported")

        # Check for additional context
        if task_result.get('context') or task_result.get('additional_info'):
            completeness_score += 0.2
            completeness_factors.append("Additional context provided")

        return {
            "completeness_score": min(1.0, completeness_score),
            "completeness_level": "high" if completeness_score > 0.8 else "medium" if completeness_score > 0.6 else "low",
            "factors_present": completeness_factors,
            "missing_elements": self._identify_missing_elements(task_result),
            "improvement_suggestions": self._suggest_completeness_improvements(completeness_score)
        }

    def _identify_missing_elements(self, task_result: Dict[str, Any]) -> List[str]:
        """Identify missing elements in task result."""
        missing = []

        if not task_result.get('result'):
            missing.append("Main result content")

        if not task_result.get('metadata'):
            missing.append("Task metadata")

        if not task_result.get('execution_time'):
            missing.append("Execution timing information")

        if not task_result.get('quality_score'):
            missing.append("Quality assessment metrics")

        if not task_result.get('context') and not task_result.get('additional_info'):
            missing.append("Additional context or supporting information")

        return missing

    def _suggest_completeness_improvements(self, completeness_score: float) -> List[str]:
        """Suggest improvements for task completeness."""
        suggestions = []

        if completeness_score < 0.5:
            suggestions.append("Significant improvements needed - ensure all basic elements are present")

        if completeness_score < 0.8:
            suggestions.append("Add more comprehensive metadata and context information")

        suggestions.append("Include quality metrics and execution details for better traceability")
        suggestions.append("Provide additional context to support the main results")

        return suggestions

    def validate_acceptance_criteria(self, task_result: Dict[str, Any], criteria: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate task result against specific acceptance criteria.

        Args:
            task_result: Task result to validate
            criteria: Acceptance criteria to check

        Returns:
            Dictionary of criteria validation results
        """
        validation_results = {}

        for criterion, requirement in criteria.items():
            if criterion == "min_quality_score":
                current_score = task_result.get('quality_score', 0.0)
                validation_results[criterion] = current_score >= requirement

            elif criterion == "max_execution_time":
                current_time = task_result.get('execution_time', float('inf'))
                validation_results[criterion] = current_time <= requirement

            elif criterion == "required_fields":
                if isinstance(requirement, list):
                    validation_results[criterion] = all(
                        field in task_result for field in requirement
                    )

            elif criterion == "no_errors":
                validation_results[criterion] = (
                    'error' not in task_result and
                    'error_message' not in task_result
                )

            elif criterion == "content_length":
                content = str(task_result.get('result', ''))
                validation_results[criterion] = len(content) >= requirement

            else:
                # Generic boolean check
                validation_results[criterion] = bool(task_result.get(criterion, False))

        return validation_results

    def get_review_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get review templates for different types of acceptance reviews.

        Returns:
            Dictionary of review templates
        """
        return {
            "quality_assessment": {
                "description": "Comprehensive quality assessment review",
                "criteria": ["accuracy", "completeness", "clarity", "relevance"],
                "min_score": 0.7,
                "focus_areas": ["content_quality", "methodology", "presentation"]
            },
            "requirement_validation": {
                "description": "Validation against original requirements",
                "criteria": ["meets_request", "scope_coverage", "deliverable_format"],
                "min_score": 0.8,
                "focus_areas": ["requirement_alignment", "scope_adherence", "format_compliance"]
            },
            "content_review": {
                "description": "Content quality and structure review",
                "criteria": ["structure", "readability", "coherence", "completeness"],
                "min_score": 0.7,
                "focus_areas": ["content_organization", "language_quality", "logical_flow"]
            },
            "methodology_evaluation": {
                "description": "Methodology and approach evaluation",
                "criteria": ["approach_validity", "method_appropriateness", "execution_quality"],
                "min_score": 0.75,
                "focus_areas": ["methodology_soundness", "implementation_quality", "result_validity"]
            },
            "final_approval": {
                "description": "Final approval for task completion",
                "criteria": ["overall_quality", "requirement_fulfillment", "deliverable_readiness"],
                "min_score": 0.8,
                "focus_areas": ["completion_status", "quality_standards", "delivery_readiness"]
            }
        }
