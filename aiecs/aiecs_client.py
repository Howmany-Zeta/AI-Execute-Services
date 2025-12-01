"""
AIECS Client - Main API for programmatic usage of AI Execute Services
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

# Import core components
from aiecs.config.config import get_settings, validate_required_settings
from aiecs.domain.task.task_context import TaskContext
from aiecs.tools import discover_tools, list_tools, get_tool
from aiecs.llm.client_factory import (
    LLMClientFactory,
    LLMClientManager,
    AIProvider,
)
from aiecs.llm.clients.base_client import LLMMessage

logger = logging.getLogger(__name__)


class AIECS:
    """
    Main AIECS client for programmatic usage

    This class provides a high-level API for:
    - Executing tasks with AI providers
    - Managing tool orchestration
    - Configuration management

    Two operation modes:
    - Simple mode: Tools and basic AI functionality (no database/Celery)
    - Full mode: Complete infrastructure (requires database/Redis)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, mode: str = "simple"):
        """
        Initialize AIECS client

        Args:
            config: Optional configuration override
            mode: Operation mode - "simple" or "full"
        """
        self.settings = get_settings()
        self.config = config or {}
        self.mode = mode

        # Core components (loaded based on mode)
        self.db_manager = None
        self.task_manager = None
        self.operation_executor = None
        self.llm_manager = None

        # State
        self._initialized = False
        self._tools_discovered = False

    async def initialize(self):
        """Initialize AIECS services based on mode"""
        if self._initialized:
            return

        logger.info(f"Initializing AIECS client in {self.mode} mode...")

        try:
            # Always discover tools
            if not self._tools_discovered:
                discover_tools("aiecs.tools")
                self._tools_discovered = True
                logger.info("Tools discovered and registered")

            # Initialize LLM manager (available in both modes)
            self.llm_manager = LLMClientManager()
            logger.info("LLM manager initialized")

            if self.mode == "simple":
                # Simple mode: only tools, no database/Celery
                logger.info("Simple mode: tools only")

            elif self.mode == "full":
                # Full mode: with database and task queue
                try:
                    # Check configuration first
                    validate_required_settings("database")

                    # Initialize database connection
                    from aiecs.infrastructure.persistence.database_manager import (
                        DatabaseManager,
                    )

                    self.db_manager = DatabaseManager()
                    await self.db_manager.init_connection_pool()
                    logger.info("Database connection pool established")

                    # Initialize task manager
                    from aiecs.infrastructure.messaging.celery_task_manager import (
                        CeleryTaskManager,
                    )

                    celery_config = {
                        "broker_url": self.settings.celery_broker_url,
                        "backend_url": self.settings.celery_broker_url,
                    }
                    self.task_manager = CeleryTaskManager(celery_config)
                    logger.info("Task manager initialized")

                    # Initialize operation executor
                    from aiecs.application.executors.operation_executor import (
                        OperationExecutor,
                    )
                    from aiecs.tools.tool_executor import ToolExecutor
                    from aiecs.utils.execution_utils import ExecutionUtils

                    tool_executor = ToolExecutor()
                    execution_utils = ExecutionUtils()
                    self.operation_executor = OperationExecutor(
                        tool_executor=tool_executor,
                        execution_utils=execution_utils,
                        config=self.config,
                    )

                except Exception as e:
                    logger.warning(f"Full mode initialization failed: {e}")
                    logger.info("Falling back to simple mode")
                    self.mode = "simple"

            self._initialized = True
            logger.info(f"AIECS client initialized successfully in {self.mode} mode")

        except Exception as e:
            logger.error(f"Failed to initialize AIECS: {e}")
            raise

    async def execute(self, context: TaskContext) -> Dict[str, Any]:
        """
        Execute a task with the given context

        Args:
            context: TaskContext with task parameters

        Returns:
            Task execution result
        """
        if not self._initialized:
            await self.initialize()

        if self.mode == "simple":
            # Simple mode: direct execution without queue
            logger.info("Executing task in simple mode (direct execution)")

            # Basic validation
            try:
                validate_required_settings("llm")
            except ValueError as e:
                return {
                    "status": "failed",
                    "error": f"LLM configuration required: {e}",
                    "mode": "simple",
                }

            # TODO: Implement direct task execution without Celery
            # For now, return a placeholder
            return {
                "status": "completed",
                "result": "Simple mode execution (placeholder)",
                "mode": "simple",
                "context_id": context.user_id,
            }

        elif self.mode == "full":
            if not self.task_manager:
                raise RuntimeError("Task manager not initialized in full mode")

            # Submit task to queue and get result
            task_id = await self.task_manager.submit_task(context=context, task_type="task")

            # Wait for task completion
            result = await self._wait_for_task_completion(task_id)
            return result

        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    async def execute_tool(self, tool_name: str, operation: str, params: Dict[str, Any]) -> Any:
        """
        Execute a specific tool operation directly

        Args:
            tool_name: Name of the tool
            operation: Operation to execute
            params: Parameters for the operation

        Returns:
            Operation result
        """
        if not self._initialized:
            await self.initialize()

        # Get tool and execute directly (works in both modes)
        tool = get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Check if tool has execute() method (some tools like KnowledgeGraphBuilderTool)
        if hasattr(tool, "execute") and callable(getattr(tool, "execute")):
            # Tools with execute() method expect kwargs unpacked
            # Some tools use "op", others use "action" - include both for compatibility
            tool_params = {**params, "op": operation, "action": operation}
            return await tool.execute(**tool_params)
        
        # Check if tool has run_async() method (BaseTool-based tools)
        elif hasattr(tool, "run_async") and callable(getattr(tool, "run_async")):
            # BaseTool.run_async expects op as first parameter, then kwargs
            return await tool.run_async(operation, **params)
        
        # Check if tool has run() method (synchronous BaseTool)
        elif hasattr(tool, "run") and callable(getattr(tool, "run")):
            # BaseTool.run expects op as first parameter, then kwargs
            return tool.run(operation, **params)
        
        else:
            raise ValueError(
                f"Tool '{tool_name}' does not have an 'execute()', 'run_async()', or 'run()' method. "
                f"Available methods: {[m for m in dir(tool) if not m.startswith('_')]}"
            )

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools"""
        if not self._tools_discovered:
            discover_tools("aiecs.tools")
            self._tools_discovered = True

        return list_tools()

    async def get_tool(self, tool_name: str):
        """Get a specific tool instance"""
        if not self._tools_discovered:
            discover_tools("aiecs.tools")
            self._tools_discovered = True

        return get_tool(tool_name)

    def process_task(self, task_context: TaskContext) -> Dict[str, Any]:
        """
        Process a task synchronously (for compatibility with synchronous tool calls)

        Args:
            task_context: TaskContext containing the task data

        Returns:
            Task processing result with AI-generated response
        """
        # Run the async method in a new event loop if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If called from async context, create a new thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.process_task_async(task_context))
                    return future.result()
            else:
                # Run in current event loop
                return loop.run_until_complete(self.process_task_async(task_context))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.process_task_async(task_context))

    async def process_task_async(self, task_context: TaskContext) -> Dict[str, Any]:
        """
        Process a task asynchronously using AI providers

        Args:
            task_context: TaskContext containing the task data

        Returns:
            Task processing result with AI-generated response
        """
        if not self._initialized:
            await self.initialize()

        if not self.llm_manager:
            raise RuntimeError("LLM manager not initialized")

        try:
            # Extract data from TaskContext
            context_dict = task_context.to_dict()
            metadata = context_dict.get("metadata", {})

            # Get AI provider preference from metadata
            ai_preference = metadata.get("aiPreference", "default")
            provider = None
            model = None

            # Parse AI preference
            if isinstance(ai_preference, str):
                # Simple string preference
                if ai_preference.lower() != "default":
                    try:
                        provider = AIProvider(ai_preference)
                    except ValueError:
                        logger.warning(f"Unknown AI provider: {ai_preference}, using default")
            elif isinstance(ai_preference, dict):
                # Dictionary with provider and model
                provider_str = ai_preference.get("provider")
                if provider_str:
                    try:
                        provider = AIProvider(provider_str)
                    except ValueError:
                        logger.warning(f"Unknown AI provider: {provider_str}, using default")
                model = ai_preference.get("model")

            # Build prompt from context data
            # The prompt could come from various sources in the context
            prompt = None

            # Check for direct prompt in metadata
            if "prompt" in metadata:
                prompt = metadata["prompt"]
            # Check for input_data (common in document generation)
            elif "input_data" in context_dict:
                input_data = context_dict["input_data"]
                if isinstance(input_data, dict) and "prompt" in input_data:
                    prompt = input_data["prompt"]
                elif isinstance(input_data, str):
                    prompt = input_data

            if not prompt:
                # Fallback: construct a simple prompt from available data
                prompt = f"Task: {context_dict.get('task_type', 'general')}\nData: {context_dict}"

            # Get temperature and other parameters from metadata
            temperature = metadata.get("temperature", 0.7)
            max_tokens = metadata.get("max_tokens", 2000)

            # Generate text using LLM manager
            messages = [LLMMessage(role="user", content=prompt)]

            response = await self.llm_manager.generate_text(
                messages=messages,
                provider=provider,
                model=model,
                context=context_dict,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Track model usage in context
            if hasattr(task_context, "track_model_usage"):
                task_context.track_model_usage(
                    model_id=response.model,
                    provider_id=response.provider,
                    mode="generate",
                )

            # Return result in expected format
            return {
                "status": "completed",
                "response": response.content,
                "provider": response.provider,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "cost_estimate": response.cost_estimate,
                "context_id": context_dict.get("chat_id", "unknown"),
            }

        except Exception as e:
            logger.error(f"Task processing failed: {e}", exc_info=True)

            # For testing/development, provide a mock response when AI provider
            # is unavailable
            error_str = str(e).lower()
            if "api key not configured" in error_str or "providernotavailable" in error_str:
                logger.warning("AI provider unavailable, using mock response for testing")
                mock_content = f"Mock AI-generated content for prompt: {prompt[:100] if len(prompt) > 100 else prompt}..."
                return {
                    "status": "completed",
                    "response": mock_content,
                    "provider": "mock",
                    "model": "mock-model",
                    "tokens_used": len(mock_content.split()),
                    "cost_estimate": 0.0,
                    "context_id": context_dict.get("chat_id", "unknown"),
                    "mock": True,
                }

            return {
                "status": "failed",
                "error": str(e),
                "context_id": (task_context.chat_id if hasattr(task_context, "chat_id") else "unknown"),
            }

    async def _wait_for_task_completion(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for task completion with timeout

        Args:
            task_id: Task ID to wait for
            timeout: Maximum wait time in seconds

        Returns:
            Task result
        """
        if not self.task_manager:
            raise RuntimeError("Task manager not initialized")

        start_time = asyncio.get_event_loop().time()

        while True:
            status = await self.task_manager.get_task_status(task_id)

            if status.get("status") in ["completed", "failed", "cancelled"]:
                return status

            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")

            # Wait before checking again
            await asyncio.sleep(1)

    async def close(self):
        """Close AIECS client and cleanup resources"""
        logger.info("Shutting down AIECS client...")

        if self.mode == "full" and self.db_manager:
            try:
                await self.db_manager.close_connection_pool()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing database: {e}")

        # Close all LLM clients
        try:
            await LLMClientFactory.close_all()
            logger.info("LLM clients closed")
        except Exception as e:
            logger.error(f"Error closing LLM clients: {e}")

        self._initialized = False
        logger.info("AIECS client shutdown complete")

    @asynccontextmanager
    async def session(self):
        """Context manager for AIECS session"""
        await self.initialize()
        try:
            yield self
        finally:
            await self.close()


# Convenience functions for quick usage
async def create_aiecs_client(config: Optional[Dict[str, Any]] = None, mode: str = "simple") -> AIECS:
    """
    Create and initialize an AIECS client

    Args:
        config: Optional configuration override
        mode: Operation mode - "simple" or "full"

    Returns:
        Initialized AIECS client
    """
    client = AIECS(config, mode)
    await client.initialize()
    return client


async def create_simple_client(
    config: Optional[Dict[str, Any]] = None,
) -> AIECS:
    """Create a simple AIECS client (tools only, no database/Celery)"""
    return await create_aiecs_client(config, "simple")


async def create_full_client(config: Optional[Dict[str, Any]] = None) -> AIECS:
    """Create a full AIECS client (with database and Celery)"""
    return await create_aiecs_client(config, "full")
