"""
Quality Processor

Implements quality control and validation workflows for task execution.
Provides examination and acceptance workflows for different task categories.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
import uuid
from enum import Enum
from dataclasses import dataclass

from ...core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionStatus
)
from ...core.models.quality_models import (
    QualityCheckType, QualityLevel, TaskCategory, QualityCheck, QualityResult
)
from ...core.exceptions.execution_exceptions import ExecutionError, ValidationError
from ...core.interfaces.executor import IExecutor

logger = logging.getLogger(__name__)


class QualityProcessor:
    """
    Quality processor for implementing quality control workflows.

    This processor provides:
    - Task result examination for collect/process tasks
    - Task result acceptance for analyze/generate tasks
    - Configurable quality criteria and thresholds
    - Quality scoring and reporting
    - Quality improvement recommendations
    """

    def __init__(self, executor: IExecutor):
        """
        Initialize the quality processor.

        Args:
            executor: The executor to use for quality checks
        """
        self.executor = executor
        self.logger = logging.getLogger(__name__)
        self._quality_checks = {}
        self._quality_history = {}
        self._quality_criteria = {}
        self._quality_thresholds = {
            QualityLevel.BASIC: 0.6,
            QualityLevel.STANDARD: 0.7,
            QualityLevel.STRICT: 0.9
        }

    async def examine_task_result(
        self,
        task_result: ExecutionResult,
        task_category: TaskCategory,
        quality_level: QualityLevel = QualityLevel.STANDARD,
        context: Optional[ExecutionContext] = None
    ) -> QualityResult:
        """
        Examine a task result for collect/process tasks.

        Args:
            task_result: The task execution result to examine
            task_category: Category of the task (collect/process)
            quality_level: Required quality level
            context: Execution context

        Returns:
            QualityResult: Result of the examination
        """
        if task_category not in [TaskCategory.COLLECT, TaskCategory.PROCESS]:
            raise ValidationError(f"Examination is only for collect/process tasks, got {task_category}")

        check_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Get quality checks for this category and level
            checks = self._get_quality_checks(task_category, QualityCheckType.EXAMINATION, quality_level)

            # Perform examination checks
            check_results = []
            total_score = 0.0
            total_weight = 0.0
            issues = []
            recommendations = []

            for check in checks:
                check_result = await self._perform_quality_check(check, task_result, context)
                check_results.append(check_result)

                total_score += check_result.score * check.weight
                total_weight += check.weight

                if not check_result.passed:
                    issues.extend(check_result.issues)

                recommendations.extend(check_result.recommendations)

            # Calculate overall score
            overall_score = total_score / total_weight if total_weight > 0 else 0.0
            threshold = self._quality_thresholds[quality_level]
            passed = overall_score >= threshold

            # Create quality result
            quality_result = QualityResult(
                check_id=check_id,
                passed=passed,
                score=overall_score,
                details={
                    'task_category': task_category.value,
                    'quality_level': quality_level.value,
                    'threshold': threshold,
                    'check_results': [
                        {
                            'check_id': cr.check_id,
                            'passed': cr.passed,
                            'score': cr.score,
                            'details': cr.details
                        }
                        for cr in check_results
                    ]
                },
                issues=list(set(issues)),  # Remove duplicates
                recommendations=list(set(recommendations)),  # Remove duplicates
                execution_time=datetime.utcnow() - start_time,
                checked_at=start_time
            )

            # Store in history
            self._quality_history[check_id] = quality_result

            self.logger.info(f"Examination completed: {passed}, score: {overall_score:.2f}")
            return quality_result

        except Exception as e:
            self.logger.error(f"Examination failed: {e}")
            return QualityResult(
                check_id=check_id,
                passed=False,
                score=0.0,
                details={'error': str(e)},
                issues=[f"Examination failed: {str(e)}"],
                recommendations=["Review task execution and retry"],
                execution_time=datetime.utcnow() - start_time,
                checked_at=start_time
            )

    async def accept_task_result(
        self,
        task_result: ExecutionResult,
        task_category: TaskCategory,
        quality_level: QualityLevel = QualityLevel.STANDARD,
        context: Optional[ExecutionContext] = None
    ) -> QualityResult:
        """
        Accept a task result for analyze/generate tasks.

        Args:
            task_result: The task execution result to accept
            task_category: Category of the task (analyze/generate)
            quality_level: Required quality level
            context: Execution context

        Returns:
            QualityResult: Result of the acceptance
        """
        if task_category not in [TaskCategory.ANALYZE, TaskCategory.GENERATE]:
            raise ValidationError(f"Acceptance is only for analyze/generate tasks, got {task_category}")

        check_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Get quality checks for this category and level
            checks = self._get_quality_checks(task_category, QualityCheckType.ACCEPTANCE, quality_level)

            # Perform acceptance checks
            check_results = []
            total_score = 0.0
            total_weight = 0.0
            issues = []
            recommendations = []

            for check in checks:
                check_result = await self._perform_quality_check(check, task_result, context)
                check_results.append(check_result)

                total_score += check_result.score * check.weight
                total_weight += check.weight

                if not check_result.passed:
                    issues.extend(check_result.issues)

                recommendations.extend(check_result.recommendations)

            # Calculate overall score
            overall_score = total_score / total_weight if total_weight > 0 else 0.0
            threshold = self._quality_thresholds[quality_level]
            passed = overall_score >= threshold

            # Create quality result
            quality_result = QualityResult(
                check_id=check_id,
                passed=passed,
                score=overall_score,
                details={
                    'task_category': task_category.value,
                    'quality_level': quality_level.value,
                    'threshold': threshold,
                    'check_results': [
                        {
                            'check_id': cr.check_id,
                            'passed': cr.passed,
                            'score': cr.score,
                            'details': cr.details
                        }
                        for cr in check_results
                    ]
                },
                issues=list(set(issues)),  # Remove duplicates
                recommendations=list(set(recommendations)),  # Remove duplicates
                execution_time=datetime.utcnow() - start_time,
                checked_at=start_time
            )

            # Store in history
            self._quality_history[check_id] = quality_result

            self.logger.info(f"Acceptance completed: {passed}, score: {overall_score:.2f}")
            return quality_result

        except Exception as e:
            self.logger.error(f"Acceptance failed: {e}")
            return QualityResult(
                check_id=check_id,
                passed=False,
                score=0.0,
                details={'error': str(e)},
                issues=[f"Acceptance failed: {str(e)}"],
                recommendations=["Review task execution and retry"],
                execution_time=datetime.utcnow() - start_time,
                checked_at=start_time
            )

    async def validate_task_result(
        self,
        task_result: ExecutionResult,
        validation_criteria: Dict[str, Any],
        context: Optional[ExecutionContext] = None
    ) -> QualityResult:
        """
        Validate a task result against custom criteria.

        Args:
            task_result: The task execution result to validate
            validation_criteria: Custom validation criteria
            context: Execution context

        Returns:
            QualityResult: Result of the validation
        """
        check_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Perform validation checks
            issues = []
            recommendations = []
            score = 1.0

            # Check basic success
            if not task_result.success:
                issues.append("Task execution was not successful")
                score -= 0.5

            # Check result structure
            if validation_criteria.get('require_result', True) and not task_result.result:
                issues.append("Task result is empty")
                score -= 0.3

            # Check required fields
            required_fields = validation_criteria.get('required_fields', [])
            if required_fields and isinstance(task_result.result, dict):
                for field in required_fields:
                    if field not in task_result.result:
                        issues.append(f"Required field '{field}' missing from result")
                        score -= 0.1

            # Check data types
            field_types = validation_criteria.get('field_types', {})
            if field_types and isinstance(task_result.result, dict):
                for field, expected_type in field_types.items():
                    if field in task_result.result:
                        actual_value = task_result.result[field]
                        if not isinstance(actual_value, expected_type):
                            issues.append(f"Field '{field}' has wrong type: expected {expected_type.__name__}, got {type(actual_value).__name__}")
                            score -= 0.1

            # Check value ranges
            value_ranges = validation_criteria.get('value_ranges', {})
            if value_ranges and isinstance(task_result.result, dict):
                for field, (min_val, max_val) in value_ranges.items():
                    if field in task_result.result:
                        value = task_result.result[field]
                        if isinstance(value, (int, float)):
                            if value < min_val or value > max_val:
                                issues.append(f"Field '{field}' value {value} is outside range [{min_val}, {max_val}]")
                                score -= 0.1

            # Ensure score is not negative
            score = max(0.0, score)

            # Generate recommendations
            if issues:
                recommendations.append("Review task implementation to address validation issues")
                if score < 0.5:
                    recommendations.append("Consider redesigning task logic")

            passed = score >= 0.7  # Default threshold for validation

            quality_result = QualityResult(
                check_id=check_id,
                passed=passed,
                score=score,
                details={
                    'validation_criteria': validation_criteria,
                    'checks_performed': len(required_fields) + len(field_types) + len(value_ranges) + 2
                },
                issues=issues,
                recommendations=recommendations,
                execution_time=datetime.utcnow() - start_time,
                checked_at=start_time
            )

            # Store in history
            self._quality_history[check_id] = quality_result

            return quality_result

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return QualityResult(
                check_id=check_id,
                passed=False,
                score=0.0,
                details={'error': str(e)},
                issues=[f"Validation failed: {str(e)}"],
                recommendations=["Review validation criteria and retry"],
                execution_time=datetime.utcnow() - start_time,
                checked_at=start_time
            )

    def register_quality_check(
        self,
        check: QualityCheck,
        check_function: Callable[[QualityCheck, ExecutionResult, Optional[ExecutionContext]], QualityResult]
    ) -> None:
        """
        Register a custom quality check.

        Args:
            check: Quality check configuration
            check_function: Function to perform the quality check
        """
        key = (check.task_category, check.check_type, check.quality_level)
        if key not in self._quality_checks:
            self._quality_checks[key] = []

        self._quality_checks[key].append((check, check_function))
        self.logger.info(f"Registered quality check: {check.check_id}")

    def set_quality_threshold(self, quality_level: QualityLevel, threshold: float) -> None:
        """
        Set the quality threshold for a quality level.

        Args:
            quality_level: Quality level to set threshold for
            threshold: Threshold value (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        self._quality_thresholds[quality_level] = threshold
        self.logger.info(f"Set quality threshold for {quality_level.value}: {threshold}")

    async def get_quality_history(
        self,
        task_category: Optional[TaskCategory] = None,
        quality_level: Optional[QualityLevel] = None,
        limit: int = 100
    ) -> List[QualityResult]:
        """
        Get quality check history.

        Args:
            task_category: Filter by task category
            quality_level: Filter by quality level
            limit: Maximum number of results

        Returns:
            List[QualityResult]: Quality check history
        """
        results = list(self._quality_history.values())

        # Apply filters
        if task_category:
            results = [r for r in results if r.details.get('task_category') == task_category.value]

        if quality_level:
            results = [r for r in results if r.details.get('quality_level') == quality_level.value]

        # Sort by checked_at descending and limit
        results.sort(key=lambda r: r.checked_at, reverse=True)
        return results[:limit]

    async def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics and statistics."""
        if not self._quality_history:
            return {
                'total_checks': 0,
                'pass_rate': 0.0,
                'average_score': 0.0,
                'by_category': {},
                'by_level': {}
            }

        results = list(self._quality_history.values())
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.passed)
        total_score = sum(r.score for r in results)

        # Calculate metrics by category
        by_category = {}
        for category in TaskCategory:
            category_results = [r for r in results if r.details.get('task_category') == category.value]
            if category_results:
                by_category[category.value] = {
                    'total': len(category_results),
                    'passed': sum(1 for r in category_results if r.passed),
                    'pass_rate': sum(1 for r in category_results if r.passed) / len(category_results),
                    'average_score': sum(r.score for r in category_results) / len(category_results)
                }

        # Calculate metrics by level
        by_level = {}
        for level in QualityLevel:
            level_results = [r for r in results if r.details.get('quality_level') == level.value]
            if level_results:
                by_level[level.value] = {
                    'total': len(level_results),
                    'passed': sum(1 for r in level_results if r.passed),
                    'pass_rate': sum(1 for r in level_results if r.passed) / len(level_results),
                    'average_score': sum(r.score for r in level_results) / len(level_results)
                }

        return {
            'total_checks': total_checks,
            'pass_rate': passed_checks / total_checks,
            'average_score': total_score / total_checks,
            'by_category': by_category,
            'by_level': by_level
        }

    def _get_quality_checks(
        self,
        task_category: TaskCategory,
        check_type: QualityCheckType,
        quality_level: QualityLevel
    ) -> List[QualityCheck]:
        """Get quality checks for the specified criteria."""
        key = (task_category, check_type, quality_level)

        if key in self._quality_checks:
            return [check for check, _ in self._quality_checks[key]]

        # Return default checks if none registered
        return self._get_default_quality_checks(task_category, check_type, quality_level)

    def _get_default_quality_checks(
        self,
        task_category: TaskCategory,
        check_type: QualityCheckType,
        quality_level: QualityLevel
    ) -> List[QualityCheck]:
        """Get default quality checks for the specified criteria."""
        checks = []

        # Basic success check
        checks.append(QualityCheck(
            check_id=f"basic_success_{task_category.value}_{check_type.value}",
            check_type=check_type,
            task_category=task_category,
            quality_level=quality_level,
            criteria={'check_success': True},
            weight=0.3,
            required=True
        ))

        # Result presence check
        checks.append(QualityCheck(
            check_id=f"result_presence_{task_category.value}_{check_type.value}",
            check_type=check_type,
            task_category=task_category,
            quality_level=quality_level,
            criteria={'check_result_presence': True},
            weight=0.2,
            required=True
        ))

        # Execution time check
        checks.append(QualityCheck(
            check_id=f"execution_time_{task_category.value}_{check_type.value}",
            check_type=check_type,
            task_category=task_category,
            quality_level=quality_level,
            criteria={'max_execution_time': 300},  # 5 minutes
            weight=0.1,
            required=False
        ))

        # Category-specific checks
        if task_category == TaskCategory.COLLECT:
            checks.append(QualityCheck(
                check_id=f"data_completeness_{check_type.value}",
                check_type=check_type,
                task_category=task_category,
                quality_level=quality_level,
                criteria={'check_data_completeness': True},
                weight=0.4,
                required=True
            ))
        elif task_category == TaskCategory.PROCESS:
            checks.append(QualityCheck(
                check_id=f"processing_accuracy_{check_type.value}",
                check_type=check_type,
                task_category=task_category,
                quality_level=quality_level,
                criteria={'check_processing_accuracy': True},
                weight=0.4,
                required=True
            ))
        elif task_category == TaskCategory.ANALYZE:
            checks.append(QualityCheck(
                check_id=f"analysis_depth_{check_type.value}",
                check_type=check_type,
                task_category=task_category,
                quality_level=quality_level,
                criteria={'check_analysis_depth': True},
                weight=0.4,
                required=True
            ))
        elif task_category == TaskCategory.GENERATE:
            checks.append(QualityCheck(
                check_id=f"generation_quality_{check_type.value}",
                check_type=check_type,
                task_category=task_category,
                quality_level=quality_level,
                criteria={'check_generation_quality': True},
                weight=0.4,
                required=True
            ))

        return checks

    async def _perform_quality_check(
        self,
        check: QualityCheck,
        task_result: ExecutionResult,
        context: Optional[ExecutionContext]
    ) -> QualityResult:
        """Perform a single quality check."""
        start_time = datetime.utcnow()

        try:
            # Check if custom function is registered
            key = (check.task_category, check.check_type, check.quality_level)
            if key in self._quality_checks:
                for registered_check, check_function in self._quality_checks[key]:
                    if registered_check.check_id == check.check_id:
                        return await check_function(check, task_result, context)

            # Perform default quality check
            return await self._perform_default_quality_check(check, task_result, context)

        except Exception as e:
            return QualityResult(
                check_id=check.check_id,
                passed=False,
                score=0.0,
                details={'error': str(e)},
                issues=[f"Quality check failed: {str(e)}"],
                recommendations=["Review quality check implementation"],
                execution_time=datetime.utcnow() - start_time,
                checked_at=start_time
            )

    async def _perform_default_quality_check(
        self,
        check: QualityCheck,
        task_result: ExecutionResult,
        context: Optional[ExecutionContext]
    ) -> QualityResult:
        """Perform default quality check implementation."""
        start_time = datetime.utcnow()
        issues = []
        recommendations = []
        score = 1.0

        # Check basic success
        if check.criteria.get('check_success', False):
            if not task_result.success:
                issues.append("Task execution was not successful")
                score -= 0.5

        # Check result presence
        if check.criteria.get('check_result_presence', False):
            if not task_result.result:
                issues.append("Task result is empty")
                score -= 0.3

        # Check execution time
        max_time = check.criteria.get('max_execution_time')
        if max_time and task_result.completed_at and task_result.started_at:
            execution_time = (task_result.completed_at - task_result.started_at).total_seconds()
            if execution_time > max_time:
                issues.append(f"Execution time {execution_time}s exceeded maximum {max_time}s")
                score -= 0.2

        # Category-specific checks (simplified)
        if check.criteria.get('check_data_completeness', False):
            if isinstance(task_result.result, dict) and not task_result.result.get('data'):
                issues.append("Data completeness check failed")
                score -= 0.3

        if check.criteria.get('check_processing_accuracy', False):
            if isinstance(task_result.result, dict) and not task_result.result.get('processed'):
                issues.append("Processing accuracy check failed")
                score -= 0.3

        if check.criteria.get('check_analysis_depth', False):
            if isinstance(task_result.result, dict) and not task_result.result.get('analysis'):
                issues.append("Analysis depth check failed")
                score -= 0.3

        if check.criteria.get('check_generation_quality', False):
            if isinstance(task_result.result, dict) and not task_result.result.get('generated'):
                issues.append("Generation quality check failed")
                score -= 0.3

        # Ensure score is not negative
        score = max(0.0, score)

        # Generate recommendations
        if issues:
            recommendations.append("Address identified quality issues")
            if score < 0.5:
                recommendations.append("Consider task redesign or implementation review")

        return QualityResult(
            check_id=check.check_id,
            passed=score >= 0.7,  # Default passing threshold
            score=score,
            details={
                'criteria_checked': list(check.criteria.keys()),
                'weight': check.weight,
                'required': check.required
            },
            issues=issues,
            recommendations=recommendations,
            execution_time=datetime.utcnow() - start_time,
            checked_at=start_time
        )
