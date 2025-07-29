"""
Execution Monitor

Tracks execution progress, status, and events for tasks and workflows.
Provides real-time monitoring and event logging capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from datetime import datetime, timedelta
import uuid
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque

from ...core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionStatus
)
from ...core.models.monitoring_models import (
    EventType, EventSeverity, ExecutionEvent, ExecutionMetrics
)

logger = logging.getLogger(__name__)


class ExecutionMonitor:
    """
    Execution monitor for tracking execution progress and events.

    This monitor provides:
    - Real-time execution tracking
    - Event logging and notification
    - Progress monitoring
    - Status reporting
    - Performance metrics collection
    - Alert and notification system
    """

    def __init__(self, max_events: int = 10000, max_metrics_history: int = 1000):
        """
        Initialize the execution monitor.

        Args:
            max_events: Maximum number of events to keep in memory
            max_metrics_history: Maximum number of metrics snapshots to keep
        """
        self.max_events = max_events
        self.max_metrics_history = max_metrics_history
        self.logger = logging.getLogger(__name__)

        # Event storage
        self._events = deque(maxlen=max_events)
        self._events_by_execution = defaultdict(list)
        self._events_by_type = defaultdict(list)

        # Metrics storage
        self._active_executions = {}
        self._metrics_history = deque(maxlen=max_metrics_history)

        # Event handlers
        self._event_handlers = defaultdict(list)
        self._global_handlers = []

        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task = None

    async def start_monitoring(self) -> None:
        """Start the execution monitoring."""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Execution monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the execution monitoring."""
        if not self._monitoring_active:
            return

        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Execution monitoring stopped")

    async def track_execution_start(
        self,
        execution_id: str,
        context: ExecutionContext,
        total_tasks: int = 1,
        source: Optional[str] = None
    ) -> None:
        """
        Track the start of an execution.

        Args:
            execution_id: Unique execution identifier
            context: Execution context
            total_tasks: Total number of tasks in the execution
            source: Source component that started the execution
        """
        now = datetime.utcnow()

        # Create execution metrics
        metrics = ExecutionMetrics(
            execution_id=execution_id,
            started_at=now,
            last_updated=now,
            status=ExecutionStatus.RUNNING,
            total_tasks=total_tasks
        )

        self._active_executions[execution_id] = metrics

        # Log event
        await self._log_event(
            event_type=EventType.EXECUTION_STARTED,
            severity=EventSeverity.INFO,
            execution_id=execution_id,
            message=f"Execution started with {total_tasks} tasks",
            details={
                'context': {
                    'input_data_size': len(str(context.input_data)) if context.input_data else 0,
                    'timeout_seconds': context.timeout_seconds,
                    'shared_data_keys': list(context.shared_data.keys()) if context.shared_data else []
                },
                'total_tasks': total_tasks
            },
            source=source
        )

    async def track_execution_progress(
        self,
        execution_id: str,
        progress: float,
        current_task: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track execution progress.

        Args:
            execution_id: Execution identifier
            progress: Progress value (0.0 to 1.0)
            current_task: Currently executing task
            details: Additional progress details
        """
        if execution_id not in self._active_executions:
            return

        metrics = self._active_executions[execution_id]
        metrics.progress = progress
        metrics.last_updated = datetime.utcnow()

        if current_task:
            metrics.current_task = current_task

        # Estimate completion time
        if progress > 0:
            elapsed = metrics.last_updated - metrics.started_at
            estimated_total = elapsed / progress
            metrics.estimated_completion = metrics.started_at + estimated_total

        # Log progress event
        await self._log_event(
            event_type=EventType.PROGRESS_UPDATE,
            severity=EventSeverity.DEBUG,
            execution_id=execution_id,
            message=f"Progress: {progress:.1%}",
            details={
                'progress': progress,
                'current_task': current_task,
                'estimated_completion': metrics.estimated_completion.isoformat() if metrics.estimated_completion else None,
                **(details or {})
            }
        )

    async def track_task_completion(
        self,
        execution_id: str,
        task_result: ExecutionResult,
        task_name: Optional[str] = None
    ) -> None:
        """
        Track task completion.

        Args:
            execution_id: Execution identifier
            task_result: Task execution result
            task_name: Name of the completed task
        """
        if execution_id not in self._active_executions:
            return

        metrics = self._active_executions[execution_id]
        metrics.last_updated = datetime.utcnow()

        if task_result.success:
            metrics.completed_tasks += 1
            event_type = EventType.TASK_COMPLETED
            severity = EventSeverity.INFO
            message = f"Task completed successfully"
        else:
            if task_result.status == ExecutionStatus.CANCELLED:
                metrics.cancelled_tasks += 1
                event_type = EventType.TASK_FAILED
                severity = EventSeverity.WARNING
                message = f"Task was cancelled"
            else:
                metrics.failed_tasks += 1
                event_type = EventType.TASK_FAILED
                severity = EventSeverity.ERROR
                message = f"Task failed: {task_result.error_message or 'Unknown error'}"

        # Update progress
        total_processed = metrics.completed_tasks + metrics.failed_tasks + metrics.cancelled_tasks
        if metrics.total_tasks > 0:
            metrics.progress = total_processed / metrics.total_tasks

        # Log event
        await self._log_event(
            event_type=event_type,
            severity=severity,
            execution_id=execution_id,
            message=message,
            details={
                'task_name': task_name,
                'task_success': task_result.success,
                'task_status': task_result.status.value if hasattr(task_result.status, 'value') else task_result.status,
                'execution_time': (task_result.completed_at - task_result.started_at).total_seconds() if task_result.completed_at and task_result.started_at else None,
                'error_code': task_result.error_code,
                'progress': metrics.progress
            }
        )

    async def track_execution_completion(
        self,
        execution_id: str,
        final_result: ExecutionResult,
        source: Optional[str] = None
    ) -> None:
        """
        Track execution completion.

        Args:
            execution_id: Execution identifier
            final_result: Final execution result
            source: Source component that completed the execution
        """
        if execution_id not in self._active_executions:
            return

        metrics = self._active_executions[execution_id]
        metrics.status = final_result.status
        metrics.last_updated = datetime.utcnow()
        metrics.progress = 1.0

        # Determine event type and severity
        if final_result.success:
            event_type = EventType.EXECUTION_COMPLETED
            severity = EventSeverity.INFO
            message = "Execution completed successfully"
        elif final_result.status == ExecutionStatus.CANCELLED:
            event_type = EventType.EXECUTION_CANCELLED
            severity = EventSeverity.WARNING
            message = "Execution was cancelled"
        else:
            event_type = EventType.EXECUTION_FAILED
            severity = EventSeverity.ERROR
            message = f"Execution failed: {final_result.error_message or 'Unknown error'}"

        # Calculate execution statistics
        total_time = metrics.last_updated - metrics.started_at

        # Log event
        await self._log_event(
            event_type=event_type,
            severity=severity,
            execution_id=execution_id,
            message=message,
            details={
                'total_execution_time': total_time.total_seconds(),
                'completed_tasks': metrics.completed_tasks,
                'failed_tasks': metrics.failed_tasks,
                'cancelled_tasks': metrics.cancelled_tasks,
                'total_tasks': metrics.total_tasks,
                'success_rate': metrics.completed_tasks / max(metrics.total_tasks, 1),
                'error_code': final_result.error_code
            },
            source=source
        )

        # Move to history
        self._metrics_history.append(metrics)
        del self._active_executions[execution_id]

    async def track_error(
        self,
        execution_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> None:
        """
        Track an error occurrence.

        Args:
            execution_id: Execution identifier
            error: The error that occurred
            context: Additional error context
            source: Source component where error occurred
        """
        await self._log_event(
            event_type=EventType.ERROR_OCCURRED,
            severity=EventSeverity.ERROR,
            execution_id=execution_id,
            message=f"Error occurred: {str(error)}",
            details={
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context or {}
            },
            source=source
        )

    async def track_warning(
        self,
        execution_id: str,
        warning_message: str,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> None:
        """
        Track a warning.

        Args:
            execution_id: Execution identifier
            warning_message: Warning message
            details: Additional warning details
            source: Source component that issued the warning
        """
        await self._log_event(
            event_type=EventType.WARNING_ISSUED,
            severity=EventSeverity.WARNING,
            execution_id=execution_id,
            message=warning_message,
            details=details or {},
            source=source
        )

    def register_event_handler(
        self,
        event_type: EventType,
        handler: Callable[[ExecutionEvent], None]
    ) -> None:
        """
        Register an event handler for specific event types.

        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        self._event_handlers[event_type].append(handler)
        self.logger.info(f"Registered event handler for {event_type.value}")

    def register_global_handler(
        self,
        handler: Callable[[ExecutionEvent], None]
    ) -> None:
        """
        Register a global event handler for all events.

        Args:
            handler: Handler function
        """
        self._global_handlers.append(handler)
        self.logger.info("Registered global event handler")

    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionMetrics]:
        """
        Get current execution status.

        Args:
            execution_id: Execution identifier

        Returns:
            Optional[ExecutionMetrics]: Current execution metrics or None if not found
        """
        return self._active_executions.get(execution_id)

    async def get_active_executions(self) -> Dict[str, ExecutionMetrics]:
        """Get all active executions."""
        return self._active_executions.copy()

    async def get_events(
        self,
        execution_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        severity: Optional[EventSeverity] = None,
        limit: int = 100
    ) -> List[ExecutionEvent]:
        """
        Get execution events with optional filtering.

        Args:
            execution_id: Filter by execution ID
            event_type: Filter by event type
            severity: Filter by severity
            limit: Maximum number of events to return

        Returns:
            List[ExecutionEvent]: Filtered events
        """
        events = list(self._events)

        # Apply filters
        if execution_id:
            events = [e for e in events if e.execution_id == execution_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if severity:
            events = [e for e in events if e.severity == severity]

        # Sort by timestamp descending and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    async def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution monitoring summary."""
        active_count = len(self._active_executions)
        total_events = len(self._events)

        # Count events by type
        event_counts = defaultdict(int)
        for event in self._events:
            event_counts[event.event_type.value] += 1

        # Count events by severity
        severity_counts = defaultdict(int)
        for event in self._events:
            severity_counts[event.severity.value] += 1

        # Calculate average execution time from history
        avg_execution_time = 0.0
        if self._metrics_history:
            total_time = sum(
                (m.last_updated - m.started_at).total_seconds()
                for m in self._metrics_history
            )
            avg_execution_time = total_time / len(self._metrics_history)

        return {
            'active_executions': active_count,
            'total_events': total_events,
            'events_by_type': dict(event_counts),
            'events_by_severity': dict(severity_counts),
            'completed_executions': len(self._metrics_history),
            'average_execution_time': avg_execution_time,
            'monitoring_active': self._monitoring_active
        }

    async def _log_event(
        self,
        event_type: EventType,
        severity: EventSeverity,
        execution_id: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """Log an execution event."""
        event = ExecutionEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            execution_id=execution_id,
            timestamp=datetime.utcnow(),
            message=message,
            details=details or {},
            source=source,
            tags=tags or []
        )

        # Store event
        self._events.append(event)
        self._events_by_execution[execution_id].append(event)
        self._events_by_type[event_type].append(event)

        # Call event handlers
        for handler in self._event_handlers[event_type]:
            try:
                await asyncio.get_event_loop().run_in_executor(None, handler, event)
            except Exception as e:
                self.logger.error(f"Event handler failed: {e}")

        for handler in self._global_handlers:
            try:
                await asyncio.get_event_loop().run_in_executor(None, handler, event)
            except Exception as e:
                self.logger.error(f"Global event handler failed: {e}")

        # Log to standard logger
        log_level = {
            EventSeverity.DEBUG: logging.DEBUG,
            EventSeverity.INFO: logging.INFO,
            EventSeverity.WARNING: logging.WARNING,
            EventSeverity.ERROR: logging.ERROR,
            EventSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.INFO)

        self.logger.log(log_level, f"[{execution_id}] {message}")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for periodic tasks."""
        while self._monitoring_active:
            try:
                # Perform periodic monitoring tasks
                await self._cleanup_old_events()
                await self._update_resource_usage()
                await self._check_execution_timeouts()

                # Sleep for monitoring interval
                await asyncio.sleep(10)  # 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Short sleep on error

    async def _cleanup_old_events(self) -> None:
        """Clean up old events from execution-specific storage."""
        # Clean up events older than 1 hour from execution-specific storage
        cutoff_time = datetime.utcnow() - timedelta(hours=1)

        for execution_id in list(self._events_by_execution.keys()):
            events = self._events_by_execution[execution_id]
            self._events_by_execution[execution_id] = [
                e for e in events if e.timestamp > cutoff_time
            ]

            # Remove empty lists
            if not self._events_by_execution[execution_id]:
                del self._events_by_execution[execution_id]

    async def _update_resource_usage(self) -> None:
        """Update resource usage metrics for active executions."""
        # This would integrate with system monitoring to get actual resource usage
        # For now, we'll just update the timestamp
        for metrics in self._active_executions.values():
            metrics.resource_usage['last_updated'] = datetime.utcnow().isoformat()

    async def _check_execution_timeouts(self) -> None:
        """Check for execution timeouts and log warnings."""
        now = datetime.utcnow()

        for execution_id, metrics in self._active_executions.items():
            # Check if execution has been running for more than 1 hour
            if (now - metrics.started_at).total_seconds() > 3600:
                await self.track_warning(
                    execution_id=execution_id,
                    warning_message="Execution has been running for more than 1 hour",
                    details={
                        'runtime_seconds': (now - metrics.started_at).total_seconds(),
                        'progress': metrics.progress
                    },
                    source="execution_monitor"
                )
