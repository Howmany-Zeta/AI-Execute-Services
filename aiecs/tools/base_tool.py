import inspect
import logging
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError
import re

from aiecs.tools.tool_executor import (
    InputValidationError,
    SecurityError,
    get_executor,
    ExecutorConfig,
)
from aiecs.config.tool_config import get_tool_config_loader

logger = logging.getLogger(__name__)


class BaseTool:
    """
    Base class for all tools, providing common functionality:
    - Input validation with Pydantic schemas
    - Caching with TTL and content-based keys
    - Concurrency with async/sync execution
    - Error handling with retries and context
    - Performance optimization with metrics
    - Logging with structured output

    Tools inheriting from this class focus on business logic, leveraging
    the executor's cross-cutting concerns.

    Example:
        class MyTool(BaseTool):
            class ReadSchema(BaseModel):
                path: str

            @validate_input(ReadSchema)
            @cache_result(ttl=300)
            @run_in_executor
            @measure_execution_time
            @sanitize_input
            def read(self, path: str):
                # Implementation
                pass
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, tool_name: Optional[str] = None):
        """
        Initialize the tool with optional configuration.

        Configuration is automatically loaded from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/{tool_name}.yaml or config/tools.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Args:
            config (Dict[str, Any], optional): Tool-specific configuration that overrides
                all other sources. If None, configuration is loaded automatically.
            tool_name (str, optional): Registered tool name. If None, uses class name.

        Raises:
            ValueError: If config is invalid.
            ValidationError: If config validation fails (when Config class exists).
        """
        # Detect Config class if it exists
        config_class = self._detect_config_class()
        
        # Determine tool name (for config file discovery)
        if tool_name is None:
            tool_name = self.__class__.__name__
        
        # Load configuration using ToolConfigLoader
        if config_class:
            # Tool has Config class - use loader to load and validate config
            loader = get_tool_config_loader()
            try:
                loaded_config = loader.load_tool_config(
                    tool_name=tool_name,
                    config_schema=config_class,
                    explicit_config=config,
                )
                # Instantiate Config class with loaded config
                self._config_obj = config_class(**loaded_config)
                self._config = loaded_config
            except ValidationError as e:
                logger.error(f"Configuration validation failed for {tool_name}: {e}")
                raise
            except Exception as e:
                logger.warning(f"Failed to load configuration for {tool_name}: {e}. Using defaults.")
                # Fallback to explicit config or empty dict
                self._config = config or {}
                try:
                    self._config_obj = config_class(**self._config)
                except Exception:
                    # If even defaults fail, create empty config object
                    self._config_obj = None
        else:
            # No Config class - backward compatibility mode
            # Still try to load from YAML/env if config provided, otherwise use as-is
            if config:
                # Use explicit config as-is
                self._config = config
            else:
                # Try to load from YAML/env even without Config class
                loader = get_tool_config_loader()
                try:
                    self._config = loader.load_tool_config(
                        tool_name=tool_name,
                        config_schema=None,
                        explicit_config=None,
                    )
                except Exception as e:
                    logger.debug(f"Could not load config for {tool_name}: {e}. Using empty config.")
                    self._config = {}
            self._config_obj = None
        
        # Extract only executor-related config fields to avoid passing tool-specific
        # fields (e.g., user_agent, temp_dir) to ExecutorConfig
        executor_config = self._extract_executor_config(self._config)
        self._executor = get_executor(executor_config)
        self._schemas: Dict[str, Type[BaseModel]] = {}
        self._async_methods: List[str] = []
        self._register_schemas()
        self._register_async_methods()

    def _extract_executor_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only executor-related configuration fields from the full config.
        
        This prevents tool-specific fields (e.g., user_agent, temp_dir) from being
        passed to ExecutorConfig, which would cause validation issues or be silently
        ignored.
        
        Args:
            config (Dict[str, Any]): Full configuration dictionary.
            
        Returns:
            Dict[str, Any]: Filtered configuration containing only ExecutorConfig fields.
        """
        if not config:
            return {}
        
        # Get all valid field names from ExecutorConfig
        executor_fields = set(ExecutorConfig.model_fields.keys())
        
        # Filter config to only include executor-related fields
        executor_config = {
            key: value
            for key, value in config.items()
            if key in executor_fields
        }
        
        return executor_config

    def _detect_config_class(self) -> Optional[Type[BaseModel]]:
        """
        Detect Config class in tool class hierarchy via introspection.

        Looks for a class named 'Config' that inherits from BaseModel or BaseSettings.

        Returns:
            Config class if found, None otherwise
        """
        # Check current class and all base classes
        for cls in [self.__class__] + list(self.__class__.__mro__):
            if hasattr(cls, "Config"):
                config_attr = getattr(cls, "Config")
                # Check if Config is a class and inherits from BaseModel
                if isinstance(config_attr, type):
                    # Import BaseSettings here to avoid circular imports
                    try:
                        from pydantic_settings import BaseSettings
                        if issubclass(config_attr, (BaseModel, BaseSettings)):
                            return config_attr
                    except ImportError:
                        # Fallback if pydantic_settings not available
                        if issubclass(config_attr, BaseModel):
                            return config_attr
        return None

    def _register_schemas(self) -> None:
        """
        Register Pydantic schemas for operations by inspecting inner Schema classes.

        Example:
            class MyTool(BaseTool):
                class ReadSchema(BaseModel):
                    path: str
                def read(self, path: str):
                    pass
            # Registers 'read' -> ReadSchema
        """
        for attr_name in dir(self.__class__):
            attr = getattr(self.__class__, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseModel) and attr.__name__.endswith("Schema"):
                op_name = attr.__name__.replace("Schema", "").lower()
                self._schemas[op_name] = attr

    def _register_async_methods(self) -> None:
        """
        Register async methods for proper execution handling.
        """
        for attr_name in dir(self.__class__):
            attr = getattr(self.__class__, attr_name)
            if inspect.iscoroutinefunction(attr) and not attr_name.startswith("_"):
                self._async_methods.append(attr_name)

    def _sanitize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize keyword arguments to prevent injection attacks.

        Args:
            kwargs (Dict[str, Any]): Input keyword arguments.

        Returns:
            Dict[str, Any]: Sanitized keyword arguments.

        Raises:
            SecurityError: If kwargs contain malicious content.
        """
        sanitized = {}
        for k, v in kwargs.items():
            if isinstance(v, str) and re.search(r"(\bSELECT\b|\bINSERT\b|--|;|/\*)", v, re.IGNORECASE):
                raise SecurityError(f"Input parameter '{k}' contains potentially malicious content")
            sanitized[k] = v
        return sanitized

    def run(self, op: str, **kwargs) -> Any:
        """
        Execute a synchronous operation with parameters.

        Args:
            op (str): The name of the operation to execute.
            **kwargs: The parameters to pass to the operation.

        Returns:
            Any: The result of the operation.

        Raises:
            ToolExecutionError: If the operation fails.
            InputValidationError: If input parameters are invalid.
            SecurityError: If inputs contain malicious content.
        """
        schema_class = self._schemas.get(op)
        if schema_class:
            try:
                schema = schema_class(**kwargs)
                kwargs = schema.model_dump(exclude_unset=True)
            except ValidationError as e:
                raise InputValidationError(f"Invalid input parameters: {e}")
        kwargs = self._sanitize_kwargs(kwargs)
        return self._executor.execute(self, op, **kwargs)

    async def run_async(self, op: str, **kwargs) -> Any:
        """
        Execute an asynchronous operation with parameters.

        Args:
            op (str): The name of the operation to execute.
            **kwargs: The parameters to pass to the operation.

        Returns:
            Any: The result of the operation.

        Raises:
            ToolExecutionError: If the operation fails.
            InputValidationError: If input parameters are invalid.
            SecurityError: If inputs contain malicious content.
        """
        schema_class = self._schemas.get(op)
        if schema_class:
            try:
                schema = schema_class(**kwargs)
                kwargs = schema.model_dump(exclude_unset=True)
            except ValidationError as e:
                raise InputValidationError(f"Invalid input parameters: {e}")
        kwargs = self._sanitize_kwargs(kwargs)
        return await self._executor.execute_async(self, op, **kwargs)

    async def run_batch(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute multiple operations in parallel.

        Args:
            operations (List[Dict[str, Any]]): List of operation dictionaries with 'op' and 'kwargs'.

        Returns:
            List[Any]: List of operation results.

        Raises:
            ToolExecutionError: If any operation fails.
            InputValidationError: If input parameters are invalid.
        """
        return await self._executor.execute_batch(self, operations)

    def _get_method_schema(self, method_name: str) -> Optional[Type[BaseModel]]:
        """
        Get the schema for a method if it exists.

        Args:
            method_name (str): The name of the method.

        Returns:
            Optional[Type[BaseModel]]: The schema class or None.
        """
        if method_name in self._schemas:
            return self._schemas[method_name]
        schema_name = method_name[0].upper() + method_name[1:] + "Schema"
        for attr_name in dir(self.__class__):
            if attr_name == schema_name:
                attr = getattr(self.__class__, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseModel):
                    return attr
        return None
