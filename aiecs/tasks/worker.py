from aiecs.domain.execution.model import TaskStatus
from celery import Celery  # type: ignore[import-untyped]
from aiecs.config.config import get_settings
from aiecs.ws.socket_server import push_progress
from aiecs.core.registry import get_ai_service
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("ai_worker", broker=settings.celery_broker_url)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_queues={
        "fast_tasks": {"exchange": "fast_tasks", "routing_key": "fast_tasks"},
        "heavy_tasks": {
            "exchange": "heavy_tasks",
            "routing_key": "heavy_tasks",
        },
    },
    task_routes={
        "aiecs.tasks.worker.execute_task": {"queue": "fast_tasks"},
        "aiecs.tasks.worker.execute_heavy_task": {"queue": "heavy_tasks"},
    },
)


@celery_app.task(bind=True, name="aiecs.tasks.worker.execute_task")
def execute_task(
    self,
    task_name: str,
    user_id: str,
    task_id: str,
    step: int,
    mode: str,
    service: str,
    input_data: Dict[str, Any],
    context: Dict[str, Any],
):
    """
    Execute a fast task from the service executor queue.
    This task is used for operations that should complete quickly.
    """
    logger.info(f"Executing fast task: {task_name} for user {user_id}, task {task_id}, step {step}")
    return _execute_service_task(
        self,
        task_name,
        user_id,
        task_id,
        step,
        mode,
        service,
        input_data,
        context,
    )


@celery_app.task(bind=True, name="aiecs.tasks.worker.execute_heavy_task")
def execute_heavy_task(
    self,
    task_name: str,
    user_id: str,
    task_id: str,
    step: int,
    mode: str,
    service: str,
    input_data: Dict[str, Any],
    context: Dict[str, Any],
):
    """
    Execute a heavy task from the service executor queue.
    This task is used for operations that may take longer to complete.
    """
    logger.info(f"Executing heavy task: {task_name} for user {user_id}, task {task_id}, step {step}")
    return _execute_service_task(
        self,
        task_name,
        user_id,
        task_id,
        step,
        mode,
        service,
        input_data,
        context,
    )


def _execute_service_task(
    self,
    task_name: str,
    user_id: str,
    task_id: str,
    step: int,
    mode: str,
    service: str,
    input_data: Dict[str, Any],
    context: Dict[str, Any],
):
    """
    Common implementation for executing both fast and heavy tasks.
    This function handles the actual task execution logic.
    """
    try:
        # 1. Push started status
        asyncio.run(
            push_progress(
                user_id,
                {
                    "status": TaskStatus.RUNNING.value,
                    "step": step,
                    "task": task_name,
                    "message": f"Executing task: {task_name}",
                },
            )
        )

        # 2. Get the service instance
        # Note: get_ai_service is imported at module level from aiecs.core.registry
        # The registry is now in the core layer to prevent circular imports
        service_cls = get_ai_service(mode, service)
        service_instance = service_cls()

        # 3. Execute the task
        if hasattr(service_instance, task_name) and callable(getattr(service_instance, task_name)):
            method = getattr(service_instance, task_name)
            result = method(input_data, context)
        else:
            # Fallback to a generic execution method if the specific task
            # method doesn't exist
            result = service_instance.execute_task(task_name, input_data, context)

        # 4. Push completed status
        asyncio.run(
            push_progress(
                user_id,
                {
                    "status": TaskStatus.COMPLETED.value,
                    "step": step,
                    "task": task_name,
                    "result": result,
                    "message": f"Completed task: {task_name}",
                },
            )
        )

        return {
            "status": TaskStatus.COMPLETED.value,
            "task": task_name,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Error executing task {task_name}: {str(e)}", exc_info=True)
        # Push error status
        asyncio.run(
            push_progress(
                user_id,
                {
                    "status": TaskStatus.FAILED.value,
                    "step": step,
                    "task": task_name,
                    "error": str(e),
                    "message": f"Failed to execute task: {task_name}",
                },
            )
        )

        return {
            "status": TaskStatus.FAILED.value,
            "task": task_name,
            "error": str(e),
        }
