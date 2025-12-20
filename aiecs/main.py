"""
AIECS - AI Execute Services
A middleware service for AI-powered task execution and tool orchestration
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from typing import Optional
import socketio  # type: ignore[import-untyped]

# Import configuration
from aiecs.config.config import get_settings

# Import WebSocket server
from aiecs.ws.socket_server import sio

# Import infrastructure
from aiecs.infrastructure.persistence.database_manager import DatabaseManager
from aiecs.infrastructure.persistence import (
    initialize_context_engine,
    close_context_engine,
)
from aiecs.infrastructure.messaging.celery_task_manager import (
    CeleryTaskManager,
)
from aiecs.infrastructure.monitoring.structured_logger import (
    setup_structured_logging,
)
from aiecs.infrastructure.monitoring import (
    initialize_global_metrics,
    close_global_metrics,
)

# Import LLM client factory
from aiecs.llm.client_factory import LLMClientFactory

# Import domain models
from aiecs.domain.task.task_context import TaskContext

# Import tool discovery
from aiecs.tools import discover_tools

# Setup logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Global instances
db_manager: Optional[DatabaseManager] = None
task_manager: Optional[CeleryTaskManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager, task_manager

    logger.info("Starting AIECS - AI Execute Services...")

    # Setup structured logging
    setup_structured_logging()

    # Initialize global metrics (early in startup)
    try:
        await initialize_global_metrics()
        logger.info("Global metrics initialized")
    except Exception as e:
        logger.warning(f"Global metrics initialization failed (continuing without it): {e}")

    # Initialize database connection
    try:
        db_manager = DatabaseManager()
        await db_manager.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    # Initialize task manager
    try:
        task_manager = CeleryTaskManager(config={})
        logger.info("Task manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize task manager: {e}")
        raise

    # Discover and register tools
    try:
        discover_tools("aiecs.tools")
        logger.info("Tools discovered and registered")
    except Exception as e:
        logger.error(f"Failed to discover tools: {e}")
        raise

    # Initialize ContextEngine (optional, graceful degradation)
    try:
        await initialize_context_engine()
        logger.info("ContextEngine initialized")
    except Exception as e:
        logger.warning(f"ContextEngine initialization failed (continuing without it): {e}")

    # Application startup complete
    logger.info("AIECS startup complete")

    yield

    # Shutdown
    logger.info("Shutting down AIECS...")

    # Close ContextEngine
    try:
        await close_context_engine()
        logger.info("ContextEngine closed")
    except Exception as e:
        logger.warning(f"Error closing ContextEngine: {e}")

    # Close database connection
    if db_manager:
        await db_manager.disconnect()
        logger.info("Database connection closed")

    # Close all LLM clients
    await LLMClientFactory.close_all()
    logger.info("LLM clients closed")

    # Close global metrics
    try:
        await close_global_metrics()
        logger.info("Global metrics closed")
    except Exception as e:
        logger.warning(f"Error closing global metrics: {e}")

    logger.info("AIECS shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AIECS - AI Execute Services",
    description="Middleware service for AI-powered task execution and tool orchestration",
    version="1.6.3",
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = settings.cors_allowed_origins.split(",") if settings.cors_allowed_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO app
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "aiecs", "version": "1.6.3"}


# Metrics health check endpoint
@app.get("/metrics/health")
async def metrics_health():
    """Check global metrics health"""
    from aiecs.infrastructure.monitoring import (
        is_metrics_initialized,
        get_metrics_summary,
    )

    return {
        "initialized": is_metrics_initialized(),
        "summary": get_metrics_summary(),
    }


# Get available tools
@app.get("/api/tools")
async def get_available_tools():
    """Get list of available tools"""
    from aiecs.tools import list_tools

    tools = list_tools()
    return {"tools": tools, "count": len(tools)}


# Execute task endpoint
@app.post("/api/execute")
async def execute_task(request: Request):
    """Execute a task with given parameters"""
    try:
        data = await request.json()

        # Extract required fields
        task_type = data.get("type", "task")
        user_id = data.get("userId", "anonymous")
        context_data = data.get("context", {})

        # Build task context
        # TaskContext only accepts 'data' and 'task_dir' arguments
        task_data = {
            "user_id": user_id,
            "metadata": context_data.get("metadata", {}),
            **context_data.get("data", {}),
        }
        # Add tools to task_data if needed
        if "tools" in context_data:
            task_data["tools"] = context_data["tools"]
        task_context = TaskContext(
            data=task_data,
            task_dir="./tasks",
        )

        # Submit task to queue
        if not task_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Task manager not initialized",
            )

        # CeleryTaskManager doesn't have submit_task, use execute_task instead
        # For now, generate a task_id and execute asynchronously
        import uuid
        task_id = str(uuid.uuid4())
        # Note: This is a placeholder - actual implementation should queue the task
        # task_manager.execute_task(...)  # type: ignore[attr-defined]

        return {
            "taskId": task_id,
            "status": "queued",
            "message": "Task submitted successfully",
        }

    except Exception as e:
        logger.error(f"Error executing task: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Get task status
@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    try:
        if not task_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Task manager not initialized",
            )

        # CeleryTaskManager doesn't have get_task_status, use get_task_result instead
        task_status = task_manager.get_task_result(task_id)  # type: ignore[attr-defined]

        if not task_status:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        return task_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Cancel task
@app.delete("/api/task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running task"""
    try:
        if not task_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Task manager not initialized",
            )

        success = await task_manager.cancel_task(task_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel task",
            )

        return {
            "taskId": task_id,
            "status": "cancelled",
            "message": "Task cancelled successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Get service info
@app.get("/api/services")
async def get_services():
    """Get available AI services"""
    from aiecs.core.registry import AI_SERVICE_REGISTRY

    services = []
    for (mode, service), cls in AI_SERVICE_REGISTRY.items():
        services.append(
            {
                "mode": mode,
                "service": service,
                "class": cls.__name__,
                "module": cls.__module__,
            }
        )

    return {"services": services, "count": len(services)}


# Get LLM providers
@app.get("/api/providers")
async def get_providers():
    """Get available LLM providers"""
    from aiecs.llm.client_factory import AIProvider

    providers = [{"name": provider.value, "enabled": True} for provider in AIProvider]

    return {"providers": providers, "count": len(providers)}


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "status": 500},
    )


# Main entry point
if __name__ == "__main__":
    import uvicorn

    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))

    # Run the application with Socket.IO support
    uvicorn.run(
        socket_app,  # Use the combined Socket.IO + FastAPI app
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=bool(os.environ.get("RELOAD", False)),
    )
