from enum import Enum
from typing import Any, Dict, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


class ErrorCode(Enum):
    VALIDATION_ERROR = "E001"
    TIMEOUT_ERROR = "E002"
    EXECUTION_ERROR = "E003"
    CANCELLED_ERROR = "E004"
    RETRY_EXHAUSTED = "E005"
    DATABASE_ERROR = "E006"
    DSL_EVALUATION_ERROR = "E007"


class TaskStepResult:
    """Task step result model"""

    def __init__(
        self,
        step: str,
        result: Any,
        completed: bool = False,
        message: str = "",
        status: str = "pending",
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.step = step
        self.result = result
        self.completed = completed
        self.message = message
        self.status = status
        self.error_code = error_code
        self.error_message = error_message

    def dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "result": self.result,
            "completed": self.completed,
            "message": self.message,
            "status": self.status,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }

    def __repr__(self) -> str:
        return f"TaskStepResult(step='{self.step}', status='{self.status}', completed={self.completed})"
