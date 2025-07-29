import asyncio
import pytest
import unittest.mock as mock
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from typing import Dict, Any, List
import json

# Import the classes to test
from app.services.service_executor import (
    ServiceExecutor,
    ExecutorConfig,
    get_executor,
    initialize_executor
)
from app.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode
from app.infrastructure.messaging.websocket_manager import UserConfirmation


class TestExecutorConfig:
    """Test ExecutorConfig class"""

    def test_executor_config_default_values(self):
        """Test ExecutorConfig with default values"""
        config = ExecutorConfig()

        assert config.broker_url == "redis://redis:6379/0"
        assert config.backend_url == "redis://redis:6379/0"
        assert config.task_serializer == "json"
        assert config.accept_content == ["json"]
        assert config.result_serializer == "json"
        assert config.timezone == "UTC"
        assert config.enable_utc is True
        assert config.task_timeout_seconds == 300
        assert config.call_timeout_seconds == 600
        assert config.rate_limit_requests_per_second == 5
        assert config.batch_size == 10
        assert config.retry_max_attempts == 3
        assert config.retry_min_wait == 4
        assert config.retry_max_wait == 60
        assert config.enable_metrics is True
        assert config.enable_tracing is True
        assert config.enable_cache is True
        assert config.cache_ttl == 3600

    def test_executor_config_custom_values(self):
        """Test ExecutorConfig with custom values"""
        custom_config = {
            "broker_url": "redis://localhost:6379/1",
            "task_timeout_seconds": 600,
            "rate_limit_requests_per_second": 10,
            "enable_metrics": False
        }
        config = ExecutorConfig(**custom_config)

        assert config.broker_url == "redis://localhost:6379/1"
        assert config.task_timeout_seconds == 600
        assert config.rate_limit_requests_per_second == 10
        assert config.enable_metrics is False


class TestServiceExecutor:
    """Test ServiceExecutor class"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch.multiple(
            'app.services.service_executor',
            ExecutorMetrics=MagicMock(),
            DatabaseManager=MagicMock(),
            WebSocketManager=MagicMock(),
            CeleryTaskManager=MagicMock(),
            TracingManager=MagicMock(),
            ExecutionUtils=MagicMock(),
            ToolExecutor=MagicMock(),
            OperationExecutor=MagicMock(),
            DSLProcessor=MagicMock(),
            ThreadPoolExecutor=MagicMock()
        ) as mocks:
            yield mocks

    @pytest.fixture
    def service_executor(self, mock_dependencies):
        """Create ServiceExecutor instance with mocked dependencies"""
        config = {"enable_metrics": True, "enable_tracing": True}
        executor = ServiceExecutor(config)
        return executor

    def test_service_executor_initialization(self, mock_dependencies):
        """Test ServiceExecutor initialization"""
        config = {"enable_metrics": True, "enable_tracing": True}
        executor = ServiceExecutor(config)

        assert executor.config.enable_metrics is True
        assert executor.config.enable_tracing is True
        assert hasattr(executor, 'metrics_manager')
        assert hasattr(executor, 'database_manager')
        assert hasattr(executor, 'websocket_manager')
        assert hasattr(executor, 'celery_manager')
        assert hasattr(executor, 'tracing_manager')
        assert hasattr(executor, 'execution_utils')
        assert hasattr(executor, 'tool_executor')
        assert hasattr(executor, 'operation_executor')
        assert hasattr(executor, 'dsl_processor')

    def test_service_executor_initialization_no_config(self, mock_dependencies):
        """Test ServiceExecutor initialization without config"""
        executor = ServiceExecutor()

        assert isinstance(executor.config, ExecutorConfig)
        assert executor.config.enable_metrics is True

    @pytest.mark.asyncio
    async def test_initialize_success(self, service_executor):
        """Test successful initialization"""
        # Mock the manager methods
        service_executor.database_manager.init_connection_pool = AsyncMock(return_value=True)
        service_executor.database_manager.init_database_schema = AsyncMock(return_value=True)
        service_executor.websocket_manager.start_server = AsyncMock(return_value=True)

        result = await service_executor.initialize()

        assert result is True
        service_executor.database_manager.init_connection_pool.assert_called_once()
        service_executor.database_manager.init_database_schema.assert_called_once()
        service_executor.websocket_manager.start_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service_executor):
        """Test initialization failure"""
        # Mock database initialization to fail
        service_executor.database_manager.init_connection_pool = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        result = await service_executor.initialize()

        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_success(self, service_executor):
        """Test successful shutdown"""
        service_executor.websocket_manager.stop_server = AsyncMock()
        service_executor.database_manager.close = AsyncMock()
        service_executor.tracing_manager.close_tracer = MagicMock()
        service_executor.thread_pool.shutdown = MagicMock()

        await service_executor.shutdown()

        service_executor.websocket_manager.stop_server.assert_called_once()
        service_executor.database_manager.close.assert_called_once()
        service_executor.tracing_manager.close_tracer.assert_called_once()
        service_executor.thread_pool.shutdown.assert_called_once_with(wait=True)

    @pytest.mark.asyncio
    async def test_shutdown_with_exception(self, service_executor):
        """Test shutdown with exception"""
        service_executor.websocket_manager.stop_server = AsyncMock(
            side_effect=Exception("Shutdown error")
        )
        service_executor.database_manager.close = AsyncMock()
        service_executor.tracing_manager.close_tracer = MagicMock()
        service_executor.thread_pool.shutdown = MagicMock()

        # Should not raise exception
        await service_executor.shutdown()

    @pytest.mark.asyncio
    async def test_execute_operation(self, service_executor):
        """Test execute_operation delegation"""
        operation_spec = "test_operation"
        params = {"param1": "value1"}
        expected_result = {"result": "success"}

        service_executor.operation_executor.execute_operation = AsyncMock(
            return_value=expected_result
        )

        result = await service_executor.execute_operation(operation_spec, params)

        assert result == expected_result
        service_executor.operation_executor.execute_operation.assert_called_once_with(
            operation_spec, params
        )

    @pytest.mark.asyncio
    async def test_execute_task(self, service_executor):
        """Test execute_task delegation"""
        task_name = "test_task"
        input_data = {"input": "data"}
        context = {"context": "value"}
        expected_result = {"task_result": "completed"}

        service_executor.celery_manager.execute_task = AsyncMock(
            return_value=expected_result
        )

        result = await service_executor.execute_task(task_name, input_data, context)

        assert result == expected_result
        service_executor.celery_manager.execute_task.assert_called_once_with(
            task_name, input_data, context
        )

    @pytest.mark.asyncio
    async def test_batch_execute_operations(self, service_executor):
        """Test batch_execute_operations delegation"""
        operations = [{"op1": "data1"}, {"op2": "data2"}]
        expected_result = [{"result1": "success"}, {"result2": "success"}]

        service_executor.operation_executor.batch_execute_operations = AsyncMock(
            return_value=expected_result
        )

        result = await service_executor.batch_execute_operations(operations)

        assert result == expected_result
        service_executor.operation_executor.batch_execute_operations.assert_called_once_with(
            operations
        )

    @pytest.mark.asyncio
    async def test_batch_execute_tasks(self, service_executor):
        """Test batch_execute_tasks delegation"""
        tasks = [{"task1": "data1"}, {"task2": "data2"}]
        expected_result = [{"result1": "completed"}, {"result2": "completed"}]

        service_executor.celery_manager.batch_execute_tasks = AsyncMock(
            return_value=expected_result
        )

        result = await service_executor.batch_execute_tasks(tasks)

        assert result == expected_result
        service_executor.celery_manager.batch_execute_tasks.assert_called_once_with(tasks)

    @pytest.mark.asyncio
    async def test_save_task_history(self, service_executor):
        """Test save_task_history delegation"""
        user_id = "user123"
        task_id = "task456"
        step = 1
        step_result = TaskStepResult(
            step="test_step",
            result={"data": "value"},
            completed=True,
            message="Success"
        )

        service_executor.database_manager.save_task_history = AsyncMock(return_value=True)

        result = await service_executor.save_task_history(user_id, task_id, step, step_result)

        assert result is True
        service_executor.database_manager.save_task_history.assert_called_once_with(
            user_id, task_id, step, step_result
        )

    @pytest.mark.asyncio
    async def test_load_task_history(self, service_executor):
        """Test load_task_history delegation"""
        user_id = "user123"
        task_id = "task456"
        expected_history = [{"step": 1, "result": "data"}]

        service_executor.database_manager.load_task_history = AsyncMock(
            return_value=expected_history
        )

        result = await service_executor.load_task_history(user_id, task_id)

        assert result == expected_history
        service_executor.database_manager.load_task_history.assert_called_once_with(
            user_id, task_id
        )

    @pytest.mark.asyncio
    async def test_check_task_status(self, service_executor):
        """Test check_task_status delegation"""
        user_id = "user123"
        task_id = "task456"
        expected_status = TaskStatus.COMPLETED

        service_executor.database_manager.check_task_status = AsyncMock(
            return_value=expected_status
        )

        result = await service_executor.check_task_status(user_id, task_id)

        assert result == expected_status
        service_executor.database_manager.check_task_status.assert_called_once_with(
            user_id, task_id
        )

    @pytest.mark.asyncio
    async def test_notify_user(self, service_executor):
        """Test notify_user delegation"""
        step_result = TaskStepResult(
            step="test_step",
            result={"data": "value"},
            completed=True,
            message="Success"
        )
        user_id = "user123"
        task_id = "task456"
        step = 1
        expected_confirmation = UserConfirmation(confirmed=True, message="OK", proceed=True)

        service_executor.websocket_manager.notify_user = AsyncMock(
            return_value=expected_confirmation
        )

        result = await service_executor.notify_user(step_result, user_id, task_id, step)

        assert result == expected_confirmation
        service_executor.websocket_manager.notify_user.assert_called_once_with(
            step_result, user_id, task_id, step
        )

    @pytest.mark.asyncio
    async def test_send_heartbeat(self, service_executor):
        """Test send_heartbeat delegation"""
        user_id = "user123"
        task_id = "task456"
        interval = 30

        service_executor.websocket_manager.send_heartbeat = AsyncMock(return_value=True)

        result = await service_executor.send_heartbeat(user_id, task_id, interval)

        assert result is True
        service_executor.websocket_manager.send_heartbeat.assert_called_once_with(
            user_id, task_id, interval
        )

    @pytest.mark.asyncio
    async def test_execute_dsl_step(self, service_executor):
        """Test execute_dsl_step delegation"""
        step = {"action": "test"}
        intent_categories = ["category1"]
        input_data = {"input": "data"}
        context = {"context": "value"}
        execute_single_task = AsyncMock()
        execute_batch_task = AsyncMock()
        expected_result = TaskStepResult(
            step="dsl_step",
            result={"data": "value"},
            completed=True,
            message="DSL executed"
        )

        service_executor.dsl_processor.execute_dsl_step = AsyncMock(
            return_value=expected_result
        )

        result = await service_executor.execute_dsl_step(
            step, intent_categories, input_data, context,
            execute_single_task, execute_batch_task
        )

        assert result == expected_result
        service_executor.dsl_processor.execute_dsl_step.assert_called_once_with(
            step, intent_categories, input_data, context,
            execute_single_task, execute_batch_task
        )

    def test_evaluate_condition(self, service_executor):
        """Test evaluate_condition delegation"""
        condition = "test_condition"
        intent_categories = ["category1", "category2"]
        expected_result = True

        service_executor.dsl_processor.evaluate_condition = MagicMock(
            return_value=expected_result
        )

        result = service_executor.evaluate_condition(condition, intent_categories)

        assert result == expected_result
        service_executor.dsl_processor.evaluate_condition.assert_called_once_with(
            condition, intent_categories
        )

    @pytest.mark.asyncio
    async def test_execute_operations_sequence(self, service_executor):
        """Test execute_operations_sequence delegation"""
        operations = [{"op1": "data1"}, {"op2": "data2"}]
        user_id = "user123"
        task_id = "task456"
        stop_on_failure = True
        expected_result = [
            TaskStepResult(step="op1", result={"data": "value1"}, completed=True, message="Success"),
            TaskStepResult(step="op2", result={"data": "value2"}, completed=True, message="Success")
        ]

        service_executor.operation_executor.execute_operations_sequence = AsyncMock(
            return_value=expected_result
        )

        result = await service_executor.execute_operations_sequence(
            operations, user_id, task_id, stop_on_failure
        )

        assert result == expected_result
        service_executor.operation_executor.execute_operations_sequence.assert_called_once_with(
            operations, user_id, task_id, stop_on_failure,
            save_callback=service_executor.save_task_history
        )

    @pytest.mark.asyncio
    async def test_execute_parallel_operations(self, service_executor):
        """Test execute_parallel_operations delegation"""
        operations = [{"op1": "data1"}, {"op2": "data2"}]
        expected_result = [
            TaskStepResult(step="op1", result={"data": "value1"}, completed=True, message="Success"),
            TaskStepResult(step="op2", result={"data": "value2"}, completed=True, message="Success")
        ]

        service_executor.operation_executor.execute_parallel_operations = AsyncMock(
            return_value=expected_result
        )

        result = await service_executor.execute_parallel_operations(operations)

        assert result == expected_result
        service_executor.operation_executor.execute_parallel_operations.assert_called_once_with(
            operations
        )

    @pytest.mark.asyncio
    async def test_batch_tool_calls(self, service_executor):
        """Test batch_tool_calls delegation"""
        tool_calls = [{"tool": "tool1", "params": {}}, {"tool": "tool2", "params": {}}]
        tool_executor = MagicMock()
        expected_result = [{"result1": "success"}, {"result2": "success"}]

        service_executor.operation_executor.batch_tool_calls = AsyncMock(
            return_value=expected_result
        )

        result = await service_executor.batch_tool_calls(tool_calls, tool_executor)

        assert result == expected_result
        service_executor.operation_executor.batch_tool_calls.assert_called_once_with(
            tool_calls, tool_executor
        )

    def test_extract_tool_calls(self, service_executor):
        """Test extract_tool_calls delegation"""
        description = "test description"
        input_data = {"input": "data"}
        context = {"context": "value"}
        expected_result = [{"tool": "extracted_tool", "params": {}}]

        service_executor.operation_executor.extract_tool_calls = MagicMock(
            return_value=expected_result
        )

        result = service_executor.extract_tool_calls(description, input_data, context)

        assert result == expected_result
        service_executor.operation_executor.extract_tool_calls.assert_called_once_with(
            description, input_data, context
        )

    def test_create_retry_strategy(self, service_executor):
        """Test create_retry_strategy"""
        metric_name = "test_metric"

        retry_strategy = service_executor.create_retry_strategy(metric_name)

        # Check that it returns a tenacity retry decorator
        assert hasattr(retry_strategy, '__call__')

    def test_create_retry_strategy_no_metric(self, service_executor):
        """Test create_retry_strategy without metric name"""
        retry_strategy = service_executor.create_retry_strategy()

        # Check that it returns a tenacity retry decorator
        assert hasattr(retry_strategy, '__call__')

    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self, service_executor):
        """Test execute_with_timeout with successful execution"""
        async def test_func(arg1, arg2, kwarg1=None):
            return {"result": f"{arg1}_{arg2}_{kwarg1}"}

        result = await service_executor.execute_with_timeout(
            test_func, "value1", "value2", timeout=5, kwarg1="kwvalue"
        )

        assert result == {"result": "value1_value2_kwvalue"}

    @pytest.mark.asyncio
    async def test_execute_with_timeout_timeout_error(self, service_executor):
        """Test execute_with_timeout with timeout"""
        async def slow_func():
            await asyncio.sleep(10)
            return {"result": "success"}

        result = await service_executor.execute_with_timeout(slow_func, timeout=0.1)

        assert result["step"] == "slow_func"
        assert result["completed"] is False
        assert result["status"] == TaskStatus.TIMED_OUT.value
        assert result["error_code"] == ErrorCode.TIMEOUT_ERROR.value

    def test_with_metrics(self, service_executor):
        """Test with_metrics decorator"""
        metric_name = "test_metric"
        labels = {"label1": "value1"}

        service_executor.metrics_manager.with_metrics = MagicMock(return_value="decorator")

        result = service_executor.with_metrics(metric_name, labels)

        assert result == "decorator"
        service_executor.metrics_manager.with_metrics.assert_called_once_with(
            metric_name, labels
        )

    def test_with_tracing(self, service_executor):
        """Test with_tracing decorator"""
        operation_name = "test_operation"

        service_executor.tracing_manager.with_tracing = MagicMock(return_value="tracer_decorator")

        result = service_executor.with_tracing(operation_name)

        assert result == "tracer_decorator"
        service_executor.tracing_manager.with_tracing.assert_called_once_with(operation_name)

    def test_get_status(self, service_executor):
        """Test get_status method"""
        # Mock the manager methods
        service_executor.metrics_manager.get_metrics_summary = MagicMock(
            return_value={"metrics": "summary"}
        )
        service_executor.websocket_manager.get_status = MagicMock(
            return_value={"websocket": "status"}
        )
        service_executor.tracing_manager.get_tracer_info = MagicMock(
            return_value={"tracer": "info"}
        )
        service_executor.operation_executor.get_stats = MagicMock(
            return_value={"operation": "stats"}
        )
        service_executor.celery_manager.get_queue_info = MagicMock(
            return_value={"queue": "info"}
        )

        status = service_executor.get_status()

        assert "service_executor" in status
        assert status["service_executor"]["initialized"] is True
        assert "config" in status["service_executor"]
        assert status["metrics"] == {"metrics": "summary"}
        assert status["websocket"] == {"websocket": "status"}
        assert status["tracing"] == {"tracer": "info"}
        assert status["operation_executor"] == {"operation": "stats"}
        assert status["celery"] == {"queue": "info"}

    def test_get_health_check_healthy(self, service_executor):
        """Test get_health_check when all components are healthy"""
        service_executor.websocket_manager.get_connection_count = MagicMock(return_value=5)

        health = service_executor.get_health_check()

        assert health["status"] == "healthy"
        assert "timestamp" in health
        assert health["components"]["database"] == "healthy"
        assert health["components"]["websocket"] == "healthy"
        assert health["components"]["metrics"] == "healthy"
        assert health["components"]["tracing"] == "healthy"

    def test_get_health_check_unhealthy_websocket(self, service_executor):
        """Test get_health_check when websocket is unhealthy"""
        service_executor.websocket_manager.get_connection_count = MagicMock(return_value=-1)

        health = service_executor.get_health_check()

        assert health["status"] == "healthy"  # Overall status is still healthy
        assert health["components"]["websocket"] == "unhealthy"

    def test_get_health_check_disabled_components(self, service_executor):
        """Test get_health_check with disabled components"""
        service_executor.config.enable_metrics = False
        service_executor.config.enable_tracing = False
        service_executor.websocket_manager.get_connection_count = MagicMock(return_value=0)

        health = service_executor.get_health_check()

        assert health["status"] == "healthy"
        assert health["components"]["metrics"] == "disabled"
        assert health["components"]["tracing"] == "disabled"

    def test_get_health_check_exception(self, service_executor):
        """Test get_health_check when exception occurs"""
        service_executor.websocket_manager.get_connection_count = MagicMock(
            side_effect=Exception("Connection error")
        )

        health = service_executor.get_health_check()

        assert health["status"] == "unhealthy"
        assert "error" in health
        assert "timestamp" in health


class TestSingletonFunctions:
    """Test singleton functions"""

    def test_get_executor_singleton(self):
        """Test get_executor returns singleton"""
        # Reset the global variable
        import app.services.service_executor as module
        module._default_executor = None

        with patch('app.services.service_executor.ServiceExecutor') as mock_executor:
            mock_instance = MagicMock()
            mock_executor.return_value = mock_instance

            # First call should create instance
            executor1 = get_executor()
            assert executor1 == mock_instance
            mock_executor.assert_called_once_with(None)

            # Second call should return same instance
            executor2 = get_executor()
            assert executor2 == mock_instance
            assert executor1 is executor2
            # Should not create new instance
            mock_executor.assert_called_once()

    def test_get_executor_with_config(self):
        """Test get_executor with custom config"""
        # Reset the global variable
        import app.services.service_executor as module
        module._default_executor = None

        config = {"enable_metrics": False}

        with patch('app.services.service_executor.ServiceExecutor') as mock_executor:
            mock_instance = MagicMock()
            mock_executor.return_value = mock_instance

            executor = get_executor(config)

            assert executor == mock_instance
            mock_executor.assert_called_once_with(config)

    @pytest.mark.asyncio
    async def test_initialize_executor(self):
        """Test initialize_executor function"""
        # Reset the global variable
        import app.services.service_executor as module
        module._default_executor = None

        config = {"enable_metrics": True}

        with patch('app.services.service_executor.ServiceExecutor') as mock_executor:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_executor.return_value = mock_instance

            executor = await initialize_executor(config)

            assert executor == mock_instance
            mock_executor.assert_called_once_with(config)
            mock_instance.initialize.assert_called_once()


class TestIntegrationScenarios:
    """Integration test scenarios"""

    @pytest.fixture
    def mock_all_dependencies(self):
        """Mock all dependencies for integration tests"""
        with patch.multiple(
            'app.services.service_executor',
            ExecutorMetrics=MagicMock(),
            DatabaseManager=MagicMock(),
            WebSocketManager=MagicMock(),
            CeleryTaskManager=MagicMock(),
            TracingManager=MagicMock(),
            ExecutionUtils=MagicMock(),
            ToolExecutor=MagicMock(),
            OperationExecutor=MagicMock(),
            DSLProcessor=MagicMock(),
            ThreadPoolExecutor=MagicMock()
        ) as mocks:
            yield mocks

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, mock_all_dependencies):
        """Test full lifecycle: init -> execute -> shutdown"""
        executor = ServiceExecutor()

        # Mock initialization
        executor.database_manager.init_connection_pool = AsyncMock(return_value=True)
        executor.database_manager.init_database_schema = AsyncMock(return_value=True)
        executor.websocket_manager.start_server = AsyncMock(return_value=True)

        # Mock execution
        executor.operation_executor.execute_operation = AsyncMock(
            return_value={"result": "success"}
        )

        # Mock shutdown
        executor.websocket_manager.stop_server = AsyncMock()
        executor.database_manager.close = AsyncMock()
        executor.tracing_manager.close_tracer = MagicMock()
        executor.thread_pool.shutdown = MagicMock()

        # Test lifecycle
        init_result = await executor.initialize()
        assert init_result is True

        exec_result = await executor.execute_operation("test_op", {"param": "value"})
        assert exec_result == {"result": "success"}

        await executor.shutdown()

        # Verify all calls were made
        executor.database_manager.init_connection_pool.assert_called_once()
        executor.websocket_manager.start_server.assert_called_once()
        executor.operation_executor.execute_operation.assert_called_once()
        executor.websocket_manager.stop_server.assert_called_once()
        executor.database_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_during_execution(self, mock_all_dependencies):
        """Test error handling during operation execution"""
        executor = ServiceExecutor()

        # Mock operation to raise exception
        executor.operation_executor.execute_operation = AsyncMock(
            side_effect=Exception("Operation failed")
        )

        # Should propagate the exception
        with pytest.raises(Exception, match="Operation failed"):
            await executor.execute_operation("failing_op", {})

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_all_dependencies):
        """Test timeout handling in execute_with_timeout"""
        executor = ServiceExecutor()

        async def slow_operation():
            await asyncio.sleep(1)
            return {"result": "slow"}

        # Test with very short timeout
        result = await executor.execute_with_timeout(slow_operation, timeout=0.01)

        assert result["completed"] is False
        assert result["status"] == TaskStatus.TIMED_OUT.value
        assert "Timed out" in result["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
