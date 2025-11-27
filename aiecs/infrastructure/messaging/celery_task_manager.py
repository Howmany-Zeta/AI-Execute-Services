import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional
from celery import Celery  # type: ignore[import-untyped]
from celery.exceptions import TimeoutError as CeleryTimeoutError  # type: ignore[import-untyped]
from asyncio import TimeoutError as AsyncioTimeoutError

# Removed direct import to avoid circular dependency
# Tasks are referenced by string names instead
from aiecs.domain.execution.model import TaskStatus, ErrorCode

logger = logging.getLogger(__name__)


class CeleryTaskManager:
    """
    Specialized handler for Celery distributed task scheduling and execution
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.celery_app: Optional[Celery] = None
        self._init_celery()

    def _init_celery(self):
        """Initialize Celery application"""
        try:
            self.celery_app = Celery(
                "service_executor",
                broker=self.config.get("broker_url", "redis://redis:6379/0"),
                backend=self.config.get("backend_url", "redis://redis:6379/0"),
            )

            # Configure Celery
            self.celery_app.conf.update(
                task_serializer=self.config.get("task_serializer", "json"),
                accept_content=self.config.get("accept_content", ["json"]),
                result_serializer=self.config.get("result_serializer", "json"),
                timezone=self.config.get("timezone", "UTC"),
                enable_utc=self.config.get("enable_utc", True),
                task_queues=self.config.get(
                    "task_queues",
                    {
                        "fast_tasks": {
                            "exchange": "fast_tasks",
                            "routing_key": "fast_tasks",
                        },
                        "heavy_tasks": {
                            "exchange": "heavy_tasks",
                            "routing_key": "heavy_tasks",
                        },
                    },
                ),
                worker_concurrency=self.config.get(
                    "worker_concurrency",
                    {"fast_worker": 10, "heavy_worker": 2},
                ),
            )

            logger.info("Celery application initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Celery: {e}")
            raise

    def execute_celery_task(
        self,
        task_name: str,
        queue: str,
        user_id: str,
        task_id: str,
        step: int,
        mode: str,
        service: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ):
        """
        Execute Celery task

        Args:
            task_name: Task name
            queue: Queue name ('fast_tasks' or 'heavy_tasks')
            user_id: User ID
            task_id: Task ID
            step: Step number
            mode: Service mode
            service: Service name
            input_data: Input data
            context: Context information

        Returns:
            Celery AsyncResult object
        """
        logger.info(f"Queueing task {task_name} to {queue} for user {user_id}, task {task_id}, step {step}")

        # Determine Celery task to use based on queue
        celery_task_name = "aiecs.tasks.worker.execute_task"
        if queue == "heavy_tasks":
            celery_task_name = "aiecs.tasks.worker.execute_heavy_task"

        # Send task to Celery
        if self.celery_app is None:
            raise RuntimeError("Celery app not initialized")
        return self.celery_app.send_task(
            celery_task_name,
            kwargs={
                "task_name": task_name,
                "user_id": user_id,
                "task_id": task_id,
                "step": step,
                "mode": mode,
                "service": service,
                "input_data": input_data,
                "context": context,
            },
            queue=queue,
        )

    async def execute_task(
        self,
        task_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Execute a single task using Celery for asynchronous processing
        """
        user_id = context.get("user_id", "anonymous")
        task_id = input_data.get("task_id", str(uuid.uuid4()))
        step = input_data.get("step", 0)
        mode = input_data.get("mode", "default")
        service = input_data.get("service", "default")
        queue = input_data.get("queue", "fast_tasks")
        timeout = self.config.get("task_timeout_seconds", 300)

        try:
            # Use string-based task names to avoid circular imports
            celery_task_name = "aiecs.tasks.worker.execute_task"
            if queue == "heavy_tasks":
                celery_task_name = "aiecs.tasks.worker.execute_heavy_task"

            if self.celery_app is None:
                raise RuntimeError("Celery app not initialized")
            result = self.celery_app.send_task(
                celery_task_name,
                kwargs={
                    "task_name": task_name,
                    "user_id": user_id,
                    "task_id": task_id,
                    "step": step,
                    "mode": mode,
                    "service": service,
                    "input_data": input_data,
                    "context": context,
                },
                queue=queue,
            )

            return result.get(timeout=timeout)

        except CeleryTimeoutError as e:
            logger.error(f"Timeout executing Celery task {task_name}: {e}")
            return {
                "status": TaskStatus.TIMED_OUT,
                "error_code": ErrorCode.TIMEOUT_ERROR,
                "error_message": str(e),
            }
        except Exception as e:
            logger.error(f"Error executing Celery task {task_name}: {e}", exc_info=True)
            return {
                "status": TaskStatus.FAILED,
                "error_code": ErrorCode.EXECUTION_ERROR,
                "error_message": str(e),
            }

    async def execute_heavy_task(self, task_name: str, input_data: Dict, context: Dict) -> Any:
        """
        Execute heavy task
        """
        input_data["queue"] = "heavy_tasks"
        return await self.execute_task(task_name, input_data, context)

    async def execute_dsl_task_step(self, step: Dict, input_data: Dict, context: Dict) -> Dict[str, Any]:
        """
        Execute DSL task step
        """
        task_name = step.get("task")
        category = "process"

        if not task_name:
            return {
                "step": "unknown",
                "result": None,
                "completed": False,
                "message": "Invalid DSL step: missing task name",
                "status": TaskStatus.FAILED,
                "error_code": ErrorCode.VALIDATION_ERROR,
                "error_message": "Task name is required",
            }

        # Determine task type
        task_type = "fast"
        try:
            task_type_result = await self.execute_task(task_name, {"get_task_type": True}, context)
            if isinstance(task_type_result, dict) and "task_type" in task_type_result:
                task_type = task_type_result["task_type"]
        except Exception:
            logger.warning(f"Could not determine task type for {task_name}, defaulting to 'fast'")

        queue = "heavy_tasks" if task_type == "heavy" else "fast_tasks"
        celery_task_name = "aiecs.tasks.worker.execute_heavy_task" if task_type == "heavy" else "aiecs.tasks.worker.execute_task"

        user_id = context.get("user_id", str(uuid.uuid4()))
        task_id = context.get("task_id", str(uuid.uuid4()))
        step_num = context.get("step", 0)

        # Send task to Celery
        if self.celery_app is None:
            raise RuntimeError("Celery app not initialized")
        celery_task = self.celery_app.send_task(
            celery_task_name,
            kwargs={
                "task_name": task_name,
                "user_id": user_id,
                "task_id": task_id,
                "step": step_num,
                "mode": context.get("mode", "multi_task"),
                "service": context.get("service", "summarizer"),
                "input_data": input_data,
                "context": context,
            },
            queue=queue,
        )

        try:
            timeout_seconds = self.config.get("task_timeout_seconds", 300)
            start_time = time.time()

            # Wait for task completion
            while not celery_task.ready():
                if time.time() - start_time > timeout_seconds:
                    raise AsyncioTimeoutError(f"Task {task_name} timed out after {timeout_seconds} seconds")
                await asyncio.sleep(0.5)

            if celery_task.successful():
                result = celery_task.get()
                if isinstance(result, dict) and "step" in result:
                    return result
                else:
                    return {
                        "step": f"{category}/{task_name}",
                        "result": result,
                        "completed": True,
                        "message": f"Completed task {task_name}",
                        "status": TaskStatus.COMPLETED,
                    }
            else:
                error = celery_task.get(propagate=False)
                status = TaskStatus.TIMED_OUT if isinstance(error, CeleryTimeoutError) else TaskStatus.FAILED
                error_code = ErrorCode.TIMEOUT_ERROR if isinstance(error, CeleryTimeoutError) else ErrorCode.EXECUTION_ERROR

                return {
                    "step": f"{category}/{task_name}",
                    "result": None,
                    "completed": False,
                    "message": f"Failed to execute task: {error}",
                    "status": status,
                    "error_code": error_code,
                    "error_message": str(error),
                }

        except AsyncioTimeoutError as e:
            return {
                "step": f"{category}/{task_name}",
                "result": None,
                "completed": False,
                "message": "Task execution timed out",
                "status": TaskStatus.TIMED_OUT,
                "error_code": ErrorCode.TIMEOUT_ERROR,
                "error_message": str(e),
            }
        except Exception as e:
            return {
                "step": f"{category}/{task_name}",
                "result": None,
                "completed": False,
                "message": f"Failed to execute {category}/{task_name}",
                "status": TaskStatus.FAILED,
                "error_code": ErrorCode.EXECUTION_ERROR,
                "error_message": str(e),
            }

    def get_task_result(self, task_id: str):
        """Get task result"""
        try:
            if self.celery_app is None:
                raise RuntimeError("Celery app not initialized")
            result = self.celery_app.AsyncResult(task_id)
            return {
                "task_id": task_id,
                "status": result.status,
                "result": result.result if result.ready() else None,
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
            }
        except Exception as e:
            logger.error(f"Error getting task result for {task_id}: {e}")
            return {"task_id": task_id, "status": "ERROR", "error": str(e)}

    def cancel_task(self, task_id: str):
        """Cancel task"""
        try:
            if self.celery_app is None:
                raise RuntimeError("Celery app not initialized")
            self.celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Task {task_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False

    async def batch_execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[Any]:
        """
        Batch execute tasks
        """
        results = []
        batch_size = self.config.get("batch_size", 10)
        rate_limit = self.config.get("rate_limit_requests_per_second", 5)

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[
                    self.execute_task(
                        task["task_name"],
                        task.get("input_data", {}),
                        task.get("context", {}),
                    )
                    for task in batch
                ],
                return_exceptions=True,
            )
            results.extend(batch_results)
            await asyncio.sleep(1.0 / rate_limit)

        return results

    def get_queue_info(self) -> Dict[str, Any]:
        """Get queue information"""
        try:
            if self.celery_app is None:
                raise RuntimeError("Celery app not initialized")
            inspect = self.celery_app.control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()

            return {
                "active_tasks": active_tasks,
                "scheduled_tasks": scheduled_tasks,
                "reserved_tasks": reserved_tasks,
            }
        except Exception as e:
            logger.error(f"Error getting queue info: {e}")
            return {"error": str(e)}

    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        try:
            if self.celery_app is None:
                raise RuntimeError("Celery app not initialized")
            inspect = self.celery_app.control.inspect()
            stats = inspect.stats()
            return stats or {}
        except Exception as e:
            logger.error(f"Error getting worker stats: {e}")
            return {"error": str(e)}
