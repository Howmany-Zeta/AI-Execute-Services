"""
Examine Outcome Service

This service integrates the SupervisorAgent with QualityProcessor to provide
comprehensive examination of collect and process task results. It ensures
quality, credibility, and completeness before proceeding with workflow execution.

Key responsibilities:
1. Examine results from collect and process tasks
2. Assess data quality, credibility, and completeness
3. Provide detailed examination reports
4. Integrate with LangChain-based supervisor agent
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from ...agent.system.supervisor import SupervisorAgent
from ...execution.processors.quality_processor import QualityProcessor
from ...core.models.agent_models import AgentConfig, AgentRole
from ...core.models.quality_models import QualityLevel, TaskCategory, QualityResult
from ...core.models.execution_models import ExecutionResult, ExecutionStatus
from ...core.models.services_models import ExaminationRequest, ExaminationResult
from ...core.exceptions.services_exceptions import ExaminationError
from ...config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager

logger = logging.getLogger(__name__)


class ExamineOutcomeService:
    """
    Service for examining outcomes of collect and process tasks.

    This service combines the capabilities of SupervisorAgent (LangChain-based)
    and QualityProcessor to provide comprehensive task result examination.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        llm_manager: LLMIntegrationManager,
        quality_processor: QualityProcessor,
        tool_integration_manager=None
    ):
        """
        Initialize the examine outcome service.

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

        # Initialize supervisor agent
        self.supervisor_agent = self._create_supervisor_agent()

        # Performance tracking
        self.total_examinations = 0
        self.successful_examinations = 0
        self.average_examination_time = 0.0

        logger.info("ExamineOutcomeService initialized")

    async def examine_task_outcome(self, request: ExaminationRequest) -> ExaminationResult:
        """
        Examine a task outcome using both supervisor agent and quality processor.

        Args:
            request: Examination request with task details

        Returns:
            Comprehensive examination result
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"Examining outcome for task: {request.task_name} (category: {request.category})")

            # Validate request
            self._validate_examination_request(request)

            # Prepare context for examination
            examination_context = self._prepare_examination_context(request)

            # Perform supervisor agent examination
            supervisor_result = await self._perform_supervisor_examination(request, examination_context)

            # Perform quality processor examination
            quality_result = await self._perform_quality_examination(request, examination_context)

            # Combine results
            combined_result = self._combine_examination_results(
                request, supervisor_result, quality_result, start_time
            )

            # Update metrics
            examination_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_metrics(combined_result.passed, examination_time)

            logger.info(f"Examination completed for {request.task_name}: passed={combined_result.passed}, score={combined_result.overall_score:.2f}")

            return combined_result

        except Exception as e:
            examination_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_metrics(False, examination_time)

            logger.error(f"Examination failed for {request.task_name}: {e}")

            # Return failure result
            return ExaminationResult(
                task_name=request.task_name,
                category=request.category,
                passed=False,
                overall_score=0.0,
                criteria_scores={},
                issues=[f"Examination failed: {str(e)}"],
                recommendations=["Review task execution and retry"],
                confidence=0.0,
                reasoning=f"Examination process failed: {str(e)}",
                examination_time=examination_time
            )

    async def examine_collect_task(self, task_name: str, task_result: Dict[str, Any], context: Dict[str, Any] = None) -> ExaminationResult:
        """
        Convenience method for examining collect task outcomes.

        Args:
            task_name: Name of the collect task
            task_result: Task execution result
            context: Optional execution context

        Returns:
            Examination result
        """
        request = ExaminationRequest(
            task_name=task_name,
            category="collect",
            task_result=task_result,
            quality_level=QualityLevel.STANDARD,
            context=context
        )

        return await self.examine_task_outcome(request)

    async def examine_process_task(self, task_name: str, task_result: Dict[str, Any], context: Dict[str, Any] = None) -> ExaminationResult:
        """
        Convenience method for examining process task outcomes.

        Args:
            task_name: Name of the process task
            task_result: Task execution result
            context: Optional execution context

        Returns:
            Examination result
        """
        request = ExaminationRequest(
            task_name=task_name,
            category="process",
            task_result=task_result,
            quality_level=QualityLevel.STANDARD,
            context=context
        )

        return await self.examine_task_outcome(request)

    def _create_supervisor_agent(self) -> SupervisorAgent:
        """Create and configure the supervisor agent."""
        agent_config = AgentConfig(
            name="Supervisor Agent",
            role=AgentRole.SUPERVISOR,
            goal="Examine and validate task outcomes for quality assurance",
            backstory="A quality control supervisor agent specialized in examining collect and process task results, ensuring data quality, credibility, and completeness.",
            verbose=True,
            allow_delegation=False
        )

        return SupervisorAgent(
            config=agent_config,
            config_manager=self.config_manager,
            llm_manager=self.llm_manager,
            tool_integration_manager=self.tool_integration_manager
        )

    def _validate_examination_request(self, request: ExaminationRequest) -> None:
        """Validate examination request parameters."""
        if not request.task_name:
            raise ValueError("Task name is required")

        if request.category not in ["collect", "process"]:
            raise ValueError(f"Invalid category for examination: {request.category}. Must be 'collect' or 'process'")

        if not request.task_result:
            raise ValueError("Task result is required")

    def _prepare_examination_context(self, request: ExaminationRequest) -> Dict[str, Any]:
        """Prepare context for examination."""
        return {
            "task_id": request.context.get("task_id", "unknown") if request.context else "unknown",
            "user_id": request.context.get("user_id", "anonymous") if request.context else "anonymous",
            "timestamp": datetime.utcnow().isoformat(),
            "examination_type": "outcome_examination",
            "quality_level": request.quality_level.value
        }

    async def _perform_supervisor_examination(self, request: ExaminationRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform examination using supervisor agent."""
        task_data = {
            "task_name": request.task_name,
            "category": request.category,
            "task_result": request.task_result
        }

        return await self.supervisor_agent.execute_task(task_data, context)

    async def _perform_quality_examination(self, request: ExaminationRequest, context: Dict[str, Any]) -> QualityResult:
        """Perform examination using quality processor."""
        # Convert task result to ExecutionResult format
        execution_result = ExecutionResult(
            success=request.task_result.get("completed", False),
            result=request.task_result.get("result"),
            error=request.task_result.get("error_message"),
            execution_time=request.task_result.get("execution_time", 0.0),
            status=ExecutionStatus.COMPLETED if request.task_result.get("completed", False) else ExecutionStatus.FAILED
        )

        # Map category to TaskCategory enum
        task_category = TaskCategory.COLLECT if request.category == "collect" else TaskCategory.PROCESS

        return await self.quality_processor.examine_task_result(
            execution_result,
            task_category,
            request.quality_level,
            context
        )

    def _combine_examination_results(
        self,
        request: ExaminationRequest,
        supervisor_result: Dict[str, Any],
        quality_result: QualityResult,
        start_time: datetime
    ) -> ExaminationResult:
        """Combine results from supervisor agent and quality processor."""

        # Extract supervisor results
        supervisor_passed = supervisor_result.get("passed", False)
        supervisor_score = supervisor_result.get("overall_score", 0.0)
        supervisor_confidence = supervisor_result.get("confidence", 0.5)
        supervisor_issues = supervisor_result.get("issues", [])
        supervisor_recommendations = supervisor_result.get("recommendations", [])
        supervisor_reasoning = supervisor_result.get("reasoning", "No reasoning provided")
        supervisor_criteria = supervisor_result.get("criteria_scores", {})

        # Extract quality processor results
        quality_passed = quality_result.passed
        quality_score = quality_result.score
        quality_issues = quality_result.issues
        quality_recommendations = quality_result.recommendations

        # Combine scores (weighted average: supervisor 60%, quality 40%)
        combined_score = (supervisor_score * 0.6) + (quality_score * 0.4)

        # Combine pass/fail (both must pass)
        combined_passed = supervisor_passed and quality_passed

        # Combine issues and recommendations
        combined_issues = list(set(supervisor_issues + quality_issues))
        combined_recommendations = list(set(supervisor_recommendations + quality_recommendations))

        # Combine criteria scores
        combined_criteria = supervisor_criteria.copy()
        if hasattr(quality_result, 'details') and quality_result.details:
            quality_criteria = quality_result.details.get('criteria_scores', {})
            combined_criteria.update(quality_criteria)

        # Calculate examination time
        examination_time = (datetime.utcnow() - start_time).total_seconds()

        # Create combined reasoning
        combined_reasoning = f"Supervisor Assessment: {supervisor_reasoning}. Quality Assessment: Combined quality score {quality_score:.2f}."

        return ExaminationResult(
            task_name=request.task_name,
            category=request.category,
            passed=combined_passed,
            overall_score=combined_score,
            criteria_scores=combined_criteria,
            issues=combined_issues,
            recommendations=combined_recommendations,
            confidence=supervisor_confidence,
            reasoning=combined_reasoning,
            quality_result=quality_result,
            examination_time=examination_time
        )

    def _update_metrics(self, success: bool, examination_time: float) -> None:
        """Update service metrics."""
        self.total_examinations += 1

        if success:
            self.successful_examinations += 1

        # Update average examination time
        self.average_examination_time = (
            (self.average_examination_time * (self.total_examinations - 1) + examination_time) /
            self.total_examinations
        )

    def get_examination_statistics(self) -> Dict[str, Any]:
        """Get examination service statistics."""
        return {
            "total_examinations": self.total_examinations,
            "successful_examinations": self.successful_examinations,
            "failed_examinations": self.total_examinations - self.successful_examinations,
            "success_rate": self.successful_examinations / max(self.total_examinations, 1),
            "average_examination_time": self.average_examination_time
        }

    async def get_quality_trends(self) -> Dict[str, Any]:
        """Get quality trends from quality processor."""
        return await self.quality_processor.get_quality_metrics()

    def generate_examination_report(self, result: ExaminationResult) -> str:
        """Generate a formatted examination report."""
        report_lines = [
            f"TASK OUTCOME EXAMINATION REPORT",
            f"================================",
            f"Task: {result.task_name}",
            f"Category: {result.category.upper()}",
            f"Status: {'PASSED' if result.passed else 'FAILED'}",
            f"Overall Score: {result.overall_score:.2f}",
            f"Confidence: {result.confidence:.2f}",
            f"Examination Time: {result.examination_time:.2f}s",
            f"",
            f"CRITERIA SCORES:",
        ]

        for criterion, score in result.criteria_scores.items():
            report_lines.append(f"  {criterion.replace('_', ' ').title()}: {score:.2f}")

        if result.issues:
            report_lines.extend([
                f"",
                f"ISSUES IDENTIFIED:"
            ])
            for issue in result.issues:
                report_lines.append(f"  - {issue}")

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
