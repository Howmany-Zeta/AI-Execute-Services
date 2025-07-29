"""
Monitoring Models

Data models for monitoring and performance tracking in the multi-task service.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field


class EventType(Enum):
    """Execution event types."""
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    EXECUTION_PAUSED = "execution_paused"
    EXECUTION_RESUMED = "execution_resumed"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_SKIPPED = "task_skipped"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    PROGRESS_UPDATE = "progress_update"
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    RESOURCE_ALLOCATED = "resource_allocated"
    RESOURCE_RELEASED = "resource_released"


class EventSeverity(Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ExecutionEvent:
    """Execution event data structure."""
    event_id: str
    event_type: EventType
    severity: EventSeverity
    execution_id: str
    timestamp: datetime
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ExecutionMetrics:
    """Execution metrics data structure."""
    execution_id: str
    started_at: datetime
    last_updated: datetime
    status: 'ExecutionStatus'
    progress: float = 0.0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    current_task: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    performance_stats: Dict[str, Any] = field(default_factory=dict)


class MetricType(Enum):
    """Performance metric types."""
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    LATENCY = "latency"


class AlertLevel(Enum):
    """Performance alert levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    metric_id: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    execution_id: Optional[str] = None
    component: Optional[str] = None
    tags: Dict[str, str] = None


@dataclass
class PerformanceAlert:
    """Performance alert data structure."""
    alert_id: str
    metric_type: MetricType
    level: AlertLevel
    threshold_value: float
    actual_value: float
    message: str
    timestamp: datetime
    execution_id: Optional[str] = None
    component: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    comparison: str = "greater_than"  # greater_than, less_than, equal_to
    window_size: int = 10  # Number of measurements to consider
    enabled: bool = True


@dataclass
class ResourceUsage:
    """System resource usage data structure."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_io_bytes: int
    process_count: int
    thread_count: int


class MonitoringStatus(Enum):
    """Monitoring system status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class MonitoringConfig(BaseModel):
    """Monitoring configuration model."""
    # Collection settings
    collection_interval_seconds: int = Field(default=5, description="Metric collection interval")
    event_retention_days: int = Field(default=30, description="Event retention period")
    metric_retention_days: int = Field(default=90, description="Metric retention period")

    # Alert settings
    alert_enabled: bool = Field(default=True, description="Whether alerts are enabled")
    alert_cooldown_seconds: int = Field(default=300, description="Alert cooldown period")

    # Performance thresholds
    execution_time_warning_seconds: float = Field(default=300.0, description="Execution time warning threshold")
    execution_time_critical_seconds: float = Field(default=600.0, description="Execution time critical threshold")
    memory_usage_warning_percent: float = Field(default=85.0, description="Memory usage warning threshold")
    memory_usage_critical_percent: float = Field(default=95.0, description="Memory usage critical threshold")
    cpu_usage_warning_percent: float = Field(default=80.0, description="CPU usage warning threshold")
    cpu_usage_critical_percent: float = Field(default=95.0, description="CPU usage critical threshold")
    error_rate_warning_percent: float = Field(default=5.0, description="Error rate warning threshold")
    error_rate_critical_percent: float = Field(default=10.0, description="Error rate critical threshold")

    # Storage settings
    max_events_in_memory: int = Field(default=10000, description="Maximum events to keep in memory")
    max_metrics_in_memory: int = Field(default=50000, description="Maximum metrics to keep in memory")

    class Config:
        use_enum_values = True


class MonitoringSummary(BaseModel):
    """Monitoring system summary."""
    status: MonitoringStatus = Field(..., description="Current monitoring status")
    uptime_seconds: float = Field(..., description="Monitoring system uptime")
    total_events: int = Field(..., description="Total events collected")
    total_metrics: int = Field(..., description="Total metrics collected")
    active_executions: int = Field(..., description="Number of active executions")
    active_alerts: int = Field(..., description="Number of active alerts")
    last_collection_time: Optional[datetime] = Field(None, description="Last metric collection time")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
