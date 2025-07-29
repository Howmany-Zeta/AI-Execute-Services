"""
Accept Outcome Service

This service integrates the DirectorAgent with QualityProcessor to provide
comprehensive acceptance of analyze and generate task results. It ensures
results meet requirements and quality standards before final approval.

Key responsibilities:
1. Accept results from analyze and generate tasks
2. Validate against original requirements and specifications
3. Assess content quality and accuracy
4. Provide detailed acceptance reports
5. Integrate with LangChain-based director agent
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from ...agent.system.director import DirectorAgent
from ...execution.processors.quality_processor import QualityProcessor
from ...core.models.agent_models import AgentConfig, AgentRole
from ...core.models.quality_models import QualityLevel, TaskCategory, QualityResult
from ...core.models.execution_models import ExecutionResult, ExecutionStatus
from ...core.models.services_models import AcceptanceRequest, AcceptanceResult
from ...core.exceptions.services_exceptions import AcceptanceError
from ...config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager

logger = logging.getLogger(__name__)


class AcceptOutcomeService:
    """
    Service for accepting outcomes of analyze and generate tasks.

    This service combines the capabilities of DirectorAgent (LangChain-based)
    and QualityProcessor to provide comprehensive task result acceptance.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        llm_manager: LLMIntegrationManager,
        quality_processor: QualityProcessor,
        tool_integration_manager=None
    ):
        """
        Initialize the accept outcome service.

        Args:
            config_manager: Configuration manager for agent setup
            llm_manager: LLM integration manager
            quality_processor: Quality processor for detailed checks
            tool_integration_manager: Optional tool integration manager
        """
        self.config_manager = config_manager
        self.llm_manager = llm_manager
        self.quality_processor = quality_processor
        self.tool_integration_manager = tool_integration_manager

        # Initialize director agent
        self.director_agent = self._create_director_agent()

        # Performance tracking
        self.total_acceptances = 0
        self.successful_acceptances = 0
        self.average_acceptance_time = 0.0

        logger.info("AcceptOutcomeService initialized")

    async def accept_task_outcome(self, request: AcceptanceRequest) -> AcceptanceResult:
        """
        Accept a task outcome using both director agent and quality processor.

        Args:
            request: Acceptance request with task details

        Returns:
            Comprehensive acceptance result
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"Accepting outcome for task: {request.task_name} (category: {request.category})")

            # Validate request
            self._validate_acceptance_request(request)

            # Prepare context for acceptance
            acceptance_context = self._prepare_acceptance_context(request)

            # Perform director agent acceptance
            director_result = await self._perform_director_acceptance(request, acceptance_context)

            # Perform quality processor acceptance
            quality_result = await self._perform_quality_acceptance(request, acceptance_context)

            # Combine results
            combined_result = self._combine_acceptance_results(
                request, director_result, quality_result, start_time
            )

            # Update metrics
            acceptance_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_metrics(combined_result.passed, acceptance_time)

            logger.info(f"Acceptance completed for {request.task_name}: passed={combined_result.passed}, score={combined_result.overall_score:.2f}")

            return combined_result

        except Exception as e:
            acceptance_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_metrics(False, acceptance_time)

            logger.error(f"Acceptance failed for {request.task_name}: {e}")

            # Return failure result
            return AcceptanceResult(
                task_name=request.task_name,
                category=request.category,
                passed=False,
                overall_score=0.0,
                criteria={},
                criteria_scores={},
                strengths=[],
                weaknesses=[f"Acceptance failed: {str(e)}"],
                recommendations=["Review task execution and retry"],
                confidence=0.0,
                reasoning=f"Acceptance process failed: {str(e)}",
                acceptance_time=acceptance_time
            )

    async def accept_analyze_task(self, task_name: str, task_result: Dict[str, Any], context: Dict[str, Any] = None) -> AcceptanceResult:
        """
        Convenience method for accepting analyze task outcomes.

        Args:
            task_name: Name of the analyze task
            task_result: Task execution result
            context: Optional execution context

        Returns:
            Acceptance result
        """
        request = AcceptanceRequest(
            task_name=task_name,
            category="analyze",
            task_result=task_result,
            quality_level=QualityLevel.STANDARD,
            context=context
        )

        return await self.accept_task_outcome(request)

    async def accept_generate_task(self, task_name: str, task_result: Dict[str, Any], context: Dict[str, Any] = None) -> AcceptanceResult:
        """
        Convenience method for accepting generate task outcomes.

        Args:
            task_name: Name of the generate task
            task_result: Task execution result
            context: Optional execution context

        Returns:
            Acceptance result
        """
        request = AcceptanceRequest(
            task_name=task_name,
            category="generate",
            task_result=task_result,
            quality_level=QualityLevel.STANDARD,
            context=context
        )

        return await self.accept_task_outcome(request)

    async def accept_with_requirements(
        self,
        task_name: str,
        category: str,
        task_result: Dict[str, Any],
        original_requirements: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AcceptanceResult:
        """
        Accept task outcome with specific requirements validation.

        Args:
            task_name: Name of the task
            category: Task category (analyze/generate)
            task_result: Task execution result
            original_requirements: Original requirements to validate against
            context: Optional execution context

        Returns:
            Acceptance result with requirements validation
        """
        request = AcceptanceRequest(
            task_name=task_name,
            category=category,
            task_result=task_result,
            original_requirements=original_requirements,
            quality_level=QualityLevel.STRICT,  # Use strict quality for requirements validation
            context=context
        )

        return await self.accept_task_outcome(request)

    def _create_director_agent(self) -> DirectorAgent:
        """Create and configure the director agent."""
        agent_config = AgentConfig(
            name="Director Agent",
            role=AgentRole.DIRECTOR,
            goal="Accept and validate analyze and generate task results",
            backstory="A quality control director agent specialized in accepting analyze and generate task results, ensuring they meet requirements and quality standards before final approval.",
            verbose=True,
            allow_delegation=False
        )

        return DirectorAgent(
            config=agent_config,
            config_manager=self.config_manager,
            llm_manager=self.llm_manager,
            tool_integration_manager=self.tool_integration_manager
        )

    def _validate_acceptance_request(self, request: AcceptanceRequest) -> None:
        """Validate acceptance request parameters."""
        if not request.task_name:
            raise ValueError("Task name is required")

        if request.category not in ["analyze", "generate"]:
            raise ValueError(f"Invalid category for acceptance: {request.category}. Must be 'analyze' or 'generate'")

        if not request.task_result:
            raise ValueError("Task result is required")

    def _prepare_acceptance_context(self, request: AcceptanceRequest) -> Dict[str, Any]:
        """Prepare context for acceptance."""
        context = {
            "task_id": request.context.get("task_id", "unknown") if request.context else "unknown",
            "user_id": request.context.get("user_id", "anonymous") if request.context else "anonymous",
            "timestamp": datetime.utcnow().isoformat(),
            "acceptance_type": "outcome_acceptance",
            "quality_level": request.quality_level.value
        }

        # Add original requirements if provided
        if request.original_requirements:
            context["original_requirements"] = request.original_requirements

        return context

    async def _perform_director_acceptance(self, request: AcceptanceRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform acceptance using director agent."""
        task_data = {
            "task_name": request.task_name,
            "category": request.category,
            "task_result": request.task_result
        }

        # Add original requirements if available
        if request.original_requirements:
            task_data["original_requirements"] = request.original_requirements

        return await self.director_agent.execute_task(task_data, context)

    async def _perform_quality_acceptance(self, request: AcceptanceRequest, context: Dict[str, Any]) -> QualityResult:
        """Perform acceptance using quality processor."""
        # Convert task result to ExecutionResult format
        execution_result = ExecutionResult(
            success=request.task_result.get("completed", False),
            result=request.task_result.get("result"),
            error=request.task_result.get("error_message"),
            execution_time=request.task_result.get("execution_time", 0.0),
            status=ExecutionStatus.COMPLETED if request.task_result.get("completed", False) else ExecutionStatus.FAILED
        )

        # Map category to TaskCategory enum
        task_category = TaskCategory.ANALYZE if request.category == "analyze" else TaskCategory.GENERATE

        return await self.quality_processor.accept_task_result(
            execution_result,
            task_category,
            request.quality_level,
            context
        )

    def _combine_acceptance_results(
        self,
        request: AcceptanceRequest,
        director_result: Dict[str, Any],
        quality_result: QualityResult,
        start_time: datetime
    ) -> AcceptanceResult:
        """Combine results from director agent and quality processor."""

        # Extract director results
        director_passed = director_result.get("passed", False)
        director_score = director_result.get("overall_score", 0.0)
        director_confidence = director_result.get("confidence", 0.5)
        director_criteria = director_result.get("criteria", {})
        director_criteria_scores = director_result.get("criteria_scores", {})
        director_strengths = director_result.get("strengths", [])
        director_weaknesses = director_result.get("weaknesses", [])
        director_recommendations = director_result.get("recommendations", [])
        director_reasoning = director_result.get("reasoning", "No reasoning provided")

        # Extract quality processor results
        quality_passed = quality_result.passed
        quality_score = quality_result.score
        quality_issues = quality_result.issues
        quality_recommendations = quality_result.recommendations

        # Combine scores (weighted average: director 70%, quality 30%)
        combined_score = (director_score * 0.7) + (quality_score * 0.3)

        # Combine pass/fail (both must pass)
        combined_passed = director_passed and quality_passed

        # Combine criteria
        combined_criteria = director_criteria.copy()
        combined_criteria_scores = director_criteria_scores.copy()

        # Add quality-based criteria
        if quality_result.score >= 0.7:
            combined_criteria["quality_standards"] = True
            combined_criteria_scores["quality_standards"] = quality_result.score
        else:
            combined_criteria["quality_standards"] = False
            combined_criteria_scores["quality_standards"] = quality_result.score

        # Combine strengths and weaknesses
        combined_strengths = director_strengths.copy()
        combined_weaknesses = director_weaknesses.copy()

        # Add quality issues as weaknesses
        if quality_issues:
            combined_weaknesses.extend([f"Quality issue: {issue}" for issue in quality_issues])

        # Combine recommendations
        combined_recommendations = list(set(director_recommendations + quality_recommendations))

        # Calculate acceptance time
        acceptance_time = (datetime.utcnow() - start_time).total_seconds()

        # Create combined reasoning
        combined_reasoning = f"Director Assessment: {director_reasoning}. Quality Assessment: Combined quality score {quality_score:.2f}."

        return AcceptanceResult(
            task_name=request.task_name,
            category=request.category,
            passed=combined_passed,
            overall_score=combined_score,
            criteria=combined_criteria,
            criteria_scores=combined_criteria_scores,
            strengths=combined_strengths,
            weaknesses=combined_weaknesses,
            recommendations=combined_recommendations,
            confidence=director_confidence,
            reasoning=combined_reasoning,
            quality_result=quality_result,
            acceptance_time=acceptance_time
        )

    def _update_metrics(self, success: bool, acceptance_time: float) -> None:
        """Update service metrics."""
        self.total_acceptances += 1

        if success:
            self.successful_acceptances += 1

        # Update average acceptance time
        self.average_acceptance_time = (
            (self.average_acceptance_time * (self.total_acceptances - 1) + acceptance_time) /
            self.total_acceptances
        )

    def get_acceptance_statistics(self) -> Dict[str, Any]:
        """Get acceptance service statistics."""
        return {
            "total_acceptances": self.total_acceptances,
            "successful_acceptances": self.successful_acceptances,
            "rejected_acceptances": self.total_acceptances - self.successful_acceptances,
            "acceptance_rate": self.successful_acceptances / max(self.total_acceptances, 1),
            "average_acceptance_time": self.average_acceptance_time
        }

    async def get_quality_trends(self) -> Dict[str, Any]:
        """Get quality trends from quality processor."""
        return await self.quality_processor.get_quality_metrics()

    def generate_acceptance_report(self, result: AcceptanceResult) -> str:
        """Generate a formatted acceptance report."""
        report_lines = [
            f"TASK OUTCOME ACCEPTANCE REPORT",
            f"===============================",
            f"Task: {result.task_name}",
            f"Category: {result.category.upper()}",
            f"Status: {'ACCEPTED' if result.passed else 'REJECTED'}",
            f"Overall Score: {result.overall_score:.2f}",
            f"Confidence: {result.confidence:.2f}",
            f"Acceptance Time: {result.acceptance_time:.2f}s",
            f"",
            f"CRITERIA ASSESSMENT:",
        ]

        for criterion, met in result.criteria.items():
            status = "✓" if met else "✗"
            score = result.criteria_scores.get(criterion, 0.0)
            report_lines.append(f"  {status} {criterion.replace('_', ' ').title()}: {score:.2f}")

        if result.strengths:
            report_lines.extend([
                f"",
                f"STRENGTHS:"
            ])
            for strength in result.strengths:
                report_lines.append(f"  + {strength}")

        if result.weaknesses:
            report_lines.extend([
                f"",
                f"AREAS FOR IMPROVEMENT:"
            ])
            for weakness in result.weaknesses:
                report_lines.append(f"  - {weakness}")

        if result.recommendations:
            report_lines.extend([
                f"",
                f"RECOMMENDATIONS:"
            ])
            for rec in result.recommendations:
                report_lines.append(f"  • {rec}")

        report_lines.extend([
            f"",
            f"REASONING:",
            f"{result.reasoning}"
        ])

        return "\n".join(report_lines)

    async def validate_against_requirements(
        self,
        task_result: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate task result against specific requirements.

        Args:
            task_result: Task execution result
            requirements: Requirements to validate against

        Returns:
            Validation result
        """
        validation_criteria = {
            "require_result": True,
            "required_fields": requirements.get("required_fields", []),
            "field_types": requirements.get("field_types", {}),
            "value_ranges": requirements.get("value_ranges", {})
        }

        # Convert to ExecutionResult format
        execution_result = ExecutionResult(
            success=task_result.get("completed", False),
            result=task_result.get("result"),
            error=task_result.get("error_message"),
            execution_time=task_result.get("execution_time", 0.0),
            status=ExecutionStatus.COMPLETED if task_result.get("completed", False) else ExecutionStatus.FAILED
        )

        quality_result = await self.quality_processor.validate_task_result(
            execution_result,
            validation_criteria
        )

        return {
            "is_valid": quality_result.passed,
            "score": quality_result.score,
            "issues": quality_result.issues,
            "recommendations": quality_result.recommendations
        }
