from typing import Any, Dict, Optional
from datetime import datetime


class TaskContext:
    """Task context model"""

    def __init__(
        self,
        user_id: str,
        task_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.task_id = task_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.variables: Dict[str, Any] = {}  # Variable storage during task execution

    def set_variable(self, key: str, value: Any):
        """Set task variable"""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get task variable"""
        return self.variables.get(key, default)

    def dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "variables": self.variables,
        }


class DSLStep:
    """DSL step model"""

    def __init__(
        self,
        step_type: str,
        condition: Optional[str] = None,
        description: str = "",
        params: Optional[Dict[str, Any]] = None,
    ):
        self.step_type = step_type
        self.condition = condition
        self.description = description
        self.params = params or {}

    def dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type,
            "condition": self.condition,
            "description": self.description,
            "params": self.params,
        }
