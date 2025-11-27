import time
import logging
import json
from typing import Dict, Any, Optional, AsyncGenerator, List
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ContextUpdate:
    """Represents a single update to the context (e.g., message, metadata, or resource)."""

    timestamp: float
    update_type: str  # e.g., "message", "metadata", "resource"
    data: Any  # Content of the update (e.g., message text, metadata dict)
    # Additional metadata (e.g., file paths, model info)
    metadata: Dict[str, Any]


class TaskContext:
    """
    Enhanced context manager for task execution with:
    - Context history tracking and checkpointing
    - Resource acquisition and release
    - Performance tracking
    - File and model tracking
    - Persistent storage
    - Metadata toggles
    - Enhanced error handling
    """

    def __init__(self, data: dict, task_dir: str = "./tasks"):
        self.user_id = data.get("user_id", "anonymous")
        self.chat_id = data.get("chat_id", "none")
        # Ensure metadata includes aiPreference
        self.metadata = data.get("metadata", {})
        if "aiPreference" in data:
            self.metadata["aiPreference"] = data["aiPreference"]
        self.task_dir = Path(task_dir)
        self.start_time: Optional[float] = None
        self.resources: Dict[str, Any] = {}
        self.context_history: List[ContextUpdate] = []
        # Tracks file operations
        self.file_tracker: Dict[str, Dict[str, Any]] = {}
        self.model_tracker: List[Dict[str, Any]] = []  # Tracks model usage
        self.metadata_toggles: Dict[str, bool] = data.get("metadata_toggles", {})
        self._initialize_persistence()

    def _initialize_persistence(self):
        """Initialize persistent storage for context history."""
        try:
            self.task_dir.mkdir(parents=True, exist_ok=True)
            history_file = self.task_dir / f"context_history_{self.chat_id}.json"
            if history_file.exists():
                with open(history_file, "r") as f:
                    raw_history = json.load(f)
                    self.context_history = [
                        ContextUpdate(
                            timestamp=entry["timestamp"],
                            update_type=entry["update_type"],
                            data=entry["data"],
                            metadata=entry["metadata"],
                        )
                        for entry in raw_history
                    ]
                    logger.debug(f"Loaded context history from {history_file}")
        except Exception as e:
            logger.error(f"Failed to initialize context history: {e}")

    async def _save_context_history(self):
        """Save context history to disk."""
        try:
            history_file = self.task_dir / f"context_history_{self.chat_id}.json"
            serialized_history = [
                {
                    "timestamp": update.timestamp,
                    "update_type": update.update_type,
                    "data": update.data,
                    "metadata": update.metadata,
                }
                for update in self.context_history
            ]
            with open(history_file, "w") as f:
                json.dump(serialized_history, f, indent=2)
            logger.debug(f"Saved context history to {history_file}")
        except Exception as e:
            logger.error(f"Failed to save context history: {e}")

    def add_context_update(self, update_type: str, data: Any, metadata: Optional[Dict[str, Any]] = None):
        """Add a context update (e.g., message, metadata change)."""
        update = ContextUpdate(
            timestamp=time.time(),
            update_type=update_type,
            data=data,
            metadata=metadata or {},
        )
        self.context_history.append(update)
        logger.debug(f"Added context update: {update_type}")

    def add_resource(self, name: str, resource: Any) -> None:
        """Add a resource that needs cleanup."""
        self.resources[name] = resource
        self.add_context_update("resource", {"name": name}, {"type": type(resource).__name__})
        logger.debug(f"Added resource: {name}")

    def track_file_operation(self, file_path: str, operation: str, source: str = "task"):
        """Track a file operation (e.g., read, edit)."""
        self.file_tracker[file_path] = {
            "operation": operation,
            "source": source,
            "timestamp": time.time(),
            "state": "active",
        }
        self.add_context_update(
            "file_operation",
            {"path": file_path, "operation": operation},
            {"source": source},
        )
        logger.debug(f"Tracked file operation: {operation} on {file_path}")

    def track_model_usage(self, model_id: str, provider_id: str, mode: str):
        """Track AI model usage."""
        model_entry = {
            "model_id": model_id,
            "provider_id": provider_id,
            "mode": mode,
            "timestamp": time.time(),
        }
        # Avoid duplicates
        if not self.model_tracker or self.model_tracker[-1] != model_entry:
            self.model_tracker.append(model_entry)
            self.add_context_update("model_usage", model_entry)
            logger.debug(f"Tracked model usage: {model_id} ({provider_id}, {mode})")

    def optimize_context(self, max_size: int = 1000) -> bool:
        """Optimize context by removing duplicates and old entries."""
        deduplicated = {}
        optimized_history = []
        total_size = 0

        for update in reversed(self.context_history):
            key = f"{update.update_type}:{json.dumps(update.data, sort_keys=True)}"
            if key not in deduplicated:
                deduplicated[key] = update
                data_size = len(str(update.data))
                if total_size + data_size <= max_size:
                    optimized_history.append(update)
                    total_size += data_size

        self.context_history = list(reversed(optimized_history))
        if len(deduplicated) < len(self.context_history):
            logger.debug(f"Optimized context: removed {len(self.context_history) - len(deduplicated)} duplicates")
            return True
        return False

    async def truncate_context_history(self, timestamp: float):
        """Truncate context history after a given timestamp."""
        original_len = len(self.context_history)
        self.context_history = [update for update in self.context_history if update.timestamp <= timestamp]
        if len(self.context_history) < original_len:
            await self._save_context_history()
            logger.debug(f"Truncated context history at timestamp {timestamp}")

    def get_active_metadata(self) -> Dict[str, Any]:
        """Return metadata filtered by toggles."""
        return {key: value for key, value in self.metadata.items() if key not in self.metadata_toggles or self.metadata_toggles[key] is not False}

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "metadata": self.get_active_metadata(),
            "context_history": [
                {
                    "timestamp": update.timestamp,
                    "update_type": update.update_type,
                    "data": update.data,
                    "metadata": update.metadata,
                }
                for update in self.context_history
            ],
            "file_tracker": self.file_tracker,
            "model_tracker": self.model_tracker,
        }

    def __enter__(self):
        """Synchronous context entry."""
        self.start_time = time.time()
        logger.debug(f"Starting task context for user {self.user_id}, chat {self.chat_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Synchronous context exit with cleanup."""
        duration = time.time() - self.start_time
        logger.debug(f"Completed task context in {duration:.2f}s for user {self.user_id}")
        for resource_name, resource in self.resources.items():
            try:
                if hasattr(resource, "close"):
                    resource.close()
                logger.debug(f"Cleaned up resource: {resource_name}")
            except Exception as e:
                logger.error(f"Error cleaning up resource {resource_name}: {e}")
        if exc_type:
            logger.error(f"Task context exited with error: {exc_val}")
        return False

    async def __aenter__(self):
        """Asynchronous context entry."""
        self.start_time = time.time()
        logger.debug(f"Starting async task context for user {self.user_id}, chat {self.chat_id}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Asynchronous context exit with cleanup."""
        duration = time.time() - self.start_time
        logger.debug(f"Completed async task context in {duration:.2f}s for user {self.user_id}")
        for resource_name, resource in self.resources.items():
            try:
                if hasattr(resource, "close"):
                    if callable(getattr(resource, "close")):
                        if hasattr(resource.close, "__await__"):
                            await resource.close()
                        else:
                            resource.close()
                logger.debug(f"Cleaned up async resource: {resource_name}")
            except Exception as e:
                logger.error(f"Error cleaning up async resource {resource_name}: {e}")
        if exc_type:
            logger.error(f"Async task context exited with error: {exc_val}")
        await self._save_context_history()
        return False


def build_context(data: dict) -> dict:
    """Build a simple context dictionary (for backward compatibility)."""
    context = TaskContext(data)
    return context.to_dict()


@asynccontextmanager
async def task_context(data: dict, task_dir: str = "./tasks") -> AsyncGenerator[TaskContext, None]:
    """
    Async context manager for task execution.

    Usage:
        async with task_context(request_data, task_dir="/path/to/tasks") as context:
            context.add_context_update("message", "User input", {"source": "user"})
            context.track_file_operation("example.py", "read", "tool")
            result = await service_instance.run(data, context)
    """
    context = TaskContext(data, task_dir)
    try:
        await context.__aenter__()
        yield context
    finally:
        await context.__aexit__(None, None, None)
