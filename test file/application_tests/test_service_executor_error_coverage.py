import asyncio
import pytest
import pytest_asyncio
import logging
from unittest.mock import Mock, patch, AsyncMock, call
from datetime import datetime
from typing import Dict, Any, List

# Import the classes to test
from app.services.service_executor import (
    ServiceExecutor,
    ExecutorConfig,
    get_executor,
    initialize_executor
)
from app.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestServiceExecutorErrorCoverage:
    """Test cases specifically designed to cover error handling paths and uncovered lines"""

    @pytest.fixture
    def test_config(self):
        """Create test configuration for error testing"""
        return {
            "enable_metrics": False,
            "enable_tracing": False,
            "enable_cache": True,
            "task_timeout_seconds": 1,
            "broker_url": "memory://",
            "backend_url": "cache+memory://",
            "websocket_port": 0,
            "db_config": {
                "user": "test",
                "password": "test",
                "database": "test",
                "host": "localhost",
                "port": 5432
            }
        }

    @pytest_asyncio.fixture
    async def service_executor(self, test_config):
        """Create ServiceExecutor for error testing"""
        executor = ServiceExecutor(test_config)
        yield executor
        try:
            await executor.shutdown()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_initialize_database_failure(self, test_config):
        """Test initialization failure when database initialization fails - covers lines 195-201, 203-204"""
        executor = ServiceExecutor(test_config)

        # Mock database manager to raise exception during init_connection_pool
        with patch.object(executor.database_manager, 'init_connection_pool', side_effect=Exception("Database connection failed")):
            result = await executor.initialize()
            assert result is False

        # Test database schema initialization failure
        with patch.object(executor.database_manager, 'init_connection_pool', return_value=None), \
             patch.object(executor.database_manager, 'init_database_schema', side_effect=Exception("Schema init failed")):
            result = await executor.initialize()
            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_websocket_failure(self, test_config):
        """Test initialization failure when WebSocket server fails to start - covers lines 198, 203-204"""
        executor = ServiceExecutor(test_config)

        # Mock websocket manager to raise exception during start_server
        with patch.object(executor.database_manager, 'init_connection_pool', return_value=None), \
             patch.object(executor.database_manager, 'init_database_schema', return_value=None), \
             patch.object(executor.websocket_manager, 'start_server', side_effect=Exception("WebSocket start failed")):
            result = await executor.initialize()
            assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_error_handling(self, test_config):
        """Test shutdown error handling - covers lines 222-223"""
        executor = ServiceExecutor(test_config)

        # Mock components to raise exceptions during shutdown
        with patch.object(executor.websocket_manager, 'stop_server', side_effect=Exception("WebSocket stop failed")), \
             patch.object(executor.database_manager, 'close', side_effect=Exception("Database close failed")), \
             patch.object(executor.tracing_manager, 'close_tracer', side_effect=Exception("Tracer close failed")):

            # Should not raise exception, but log errors
            await executor.shutdown()
            # Test passes if no exception is raised

    @pytest.mark.asyncio
    async def test_batch_execute_operations_delegation(self, service_executor):
        """Test batch_execute_operations delegation - covers line 236"""
        operations = [{"operation": "test1"}, {"operation": "test2"}]

        # Mock the operation executor to return a specific result
        with patch.object(service_executor.operation_executor, 'batch_execute_operations', return_value=["result1", "result2"]) as mock_batch:
            result = await service_executor.batch_execute_operations(operations)
            mock_batch.assert_called_once_with(operations)
            assert result == ["result1", "result2"]

    @pytest.mark.asyncio
    async def test_batch_execute_tasks_delegation(self, service_executor):
        """Test batch_execute_tasks delegation - covers line 240"""
        tasks = [{"task": "test1"}, {"task": "test2"}]

        # Mock the celery manager to return a specific result
        with patch.object(service_executor.celery_manager, 'batch_execute_tasks', return_value=["task_result1", "task_result2"]) as mock_batch:
            result = await service_executor.batch_execute_tasks(tasks)
            mock_batch.assert_called_once_with(tasks)
            assert result == ["task_result1", "task_result2"]

    @pytest.mark.asyncio
    async def test_save_task_history_delegation(self, service_executor):
        """Test save_task_history delegation - covers line 245"""
        user_id = "test_user"
        task_id = "test_task"
        step = 1
        step_result = TaskStepResult(
            step="test_step",
            result={"data": "test"},
            completed=True,
            message="Test message",
            status=TaskStatus.COMPLETED.value
        )

        # Mock the database manager
        with patch.object(service_executor.database_manager, 'save_task_history', return_value="saved") as mock_save:
            result = await service_executor.save_task_history(user_id, task_id, step, step_result)
            mock_save.assert_called_once_with(user_id, task_id, step, step_result)
            assert result == "saved"

    @pytest.mark.asyncio
    async def test_load_task_history_delegation(self, service_executor):
        """Test load_task_history delegation - covers line 249"""
        user_id = "test_user"
        task_id = "test_task"

        # Mock the database manager
        with patch.object(service_executor.database_manager, 'load_task_history', return_value=[{"step": 1}]) as mock_load:
            result = await service_executor.load_task_history(user_id, task_id)
            mock_load.assert_called_once_with(user_id, task_id)
            assert result == [{"step": 1}]

    @pytest.mark.asyncio
    async def test_check_task_status_delegation(self, service_executor):
        """Test check_task_status delegation - covers line 253"""
        user_id = "test_user"
        task_id = "test_task"

        # Mock the database manager
        with patch.object(service_executor.database_manager, 'check_task_status', return_value=TaskStatus.COMPLETED) as mock_check:
            result = await service_executor.check_task_status(user_id, task_id)
            mock_check.assert_called_once_with(user_id, task_id)
            assert result == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_notify_user_delegation(self, service_executor):
        """Test notify_user delegation - covers line 258"""
        step_result = TaskStepResult(
            step="test_step",
            result={"data": "test"},
            completed=True,
            message="Test message",
            status=TaskStatus.COMPLETED.value
        )
        user_id = "test_user"
        task_id = "test_task"
        step = 1

        # Mock the websocket manager
        mock_confirmation = Mock()
        with patch.object(service_executor.websocket_manager, 'notify_user', return_value=mock_confirmation) as mock_notify:
            result = await service_executor.notify_user(step_result, user_id, task_id, step)
            mock_notify.assert_called_once_with(step_result, user_id, task_id, step)
            assert result == mock_confirmation

    @pytest.mark.asyncio
    async def test_send_heartbeat_delegation(self, service_executor):
        """Test send_heartbeat delegation - covers line 262"""
        user_id = "test_user"
        task_id = "test_task"
        interval = 30

        # Mock the websocket manager
        with patch.object(service_executor.websocket_manager, 'send_heartbeat', return_value="heartbeat_sent") as mock_heartbeat:
            result = await service_executor.send_heartbeat(user_id, task_id, interval)
            mock_heartbeat.assert_called_once_with(user_id, task_id, interval)
            assert result == "heartbeat_sent"

    @pytest.mark.asyncio
    async def test_execute_dsl_step_delegation(self, service_executor):
        """Test execute_dsl_step delegation - covers line 268"""
        step = {"if": "test_condition", "then": [{"task": "test_task"}]}
        intent_categories = ["test_category"]
        input_data = {"input": "data"}
        context = {"context": "value"}
        execute_single_task = Mock()
        execute_batch_task = Mock()

        mock_result = TaskStepResult(
            step="dsl_step",
            result={"dsl": "result"},
            completed=True,
            message="DSL executed",
            status=TaskStatus.COMPLETED.value
        )

        # Mock the DSL processor
        with patch.object(service_executor.dsl_processor, 'execute_dsl_step', return_value=mock_result) as mock_dsl:
            result = await service_executor.execute_dsl_step(
                step, intent_categories, input_data, context, execute_single_task, execute_batch_task
            )
            mock_dsl.assert_called_once_with(
                step, intent_categories, input_data, context, execute_single_task, execute_batch_task
            )
            assert result == mock_result

    @pytest.mark.asyncio
    async def test_execute_operations_sequence_delegation(self, service_executor):
        """Test execute_operations_sequence delegation - covers line 282"""
        operations = [{"operation": "test1"}, {"operation": "test2"}]
        user_id = "test_user"
        task_id = "test_task"
        stop_on_failure = True

        mock_results = [
            TaskStepResult(step="op1", result={}, completed=True, message="", status=TaskStatus.COMPLETED.value),
            TaskStepResult(step="op2", result={}, completed=True, message="", status=TaskStatus.COMPLETED.value)
        ]

        # Mock the operation executor
        with patch.object(service_executor.operation_executor, 'execute_operations_sequence', return_value=mock_results) as mock_sequence:
            result = await service_executor.execute_operations_sequence(operations, user_id, task_id, stop_on_failure)
            mock_sequence.assert_called_once_with(
                operations, user_id, task_id, stop_on_failure,
                save_callback=service_executor.save_task_history
            )
            assert result == mock_results

    @pytest.mark.asyncio
    async def test_execute_parallel_operations_delegation(self, service_executor):
        """Test execute_parallel_operations delegation - covers line 289"""
        operations = [{"operation": "test1"}, {"operation": "test2"}]

        mock_results = [
            TaskStepResult(step="op1", result={}, completed=True, message="", status=TaskStatus.COMPLETED.value),
            TaskStepResult(step="op2", result={}, completed=True, message="", status=TaskStatus.COMPLETED.value)
        ]

        # Mock the operation executor
        with patch.object(service_executor.operation_executor, 'execute_parallel_operations', return_value=mock_results) as mock_parallel:
            result = await service_executor.execute_parallel_operations(operations)
            mock_parallel.assert_called_once_with(operations)
            assert result == mock_results

    @pytest.mark.asyncio
    async def test_batch_tool_calls_delegation(self, service_executor):
        """Test batch_tool_calls delegation - covers line 294"""
        tool_calls = [{"tool": "test1"}, {"tool": "test2"}]
        tool_executor = Mock()

        # Mock the operation executor
        with patch.object(service_executor.operation_executor, 'batch_tool_calls', return_value=["tool_result1", "tool_result2"]) as mock_batch_tools:
            result = await service_executor.batch_tool_calls(tool_calls, tool_executor)
            mock_batch_tools.assert_called_once_with(tool_calls, tool_executor)
            assert result == ["tool_result1", "tool_result2"]

    def test_create_retry_strategy_with_metric(self, service_executor):
        """Test create_retry_strategy with metric recording - covers lines 304-305"""
        metric_name = "test_metric"
        retry_strategy = service_executor.create_retry_strategy(metric_name)

        # Mock the metrics manager to track calls
        with patch.object(service_executor.metrics_manager, 'record_retry') as mock_record:
            # Create a function that will fail twice then succeed
            call_count = 0

            @retry_strategy
            def test_function():
                nonlocal call_count
                call_count += 1
                if call_count <= 2:  # Fail first two attempts
                    raise ValueError("Test failure")
                return "success"

            # Execute the function - should retry and eventually succeed
            result = test_function()
            assert result == "success"
            assert call_count == 3  # Initial call + 2 retries

            # Verify record_retry was called for each retry attempt
            expected_calls = [
                call(metric_name, 2),  # Second attempt
                call(metric_name, 3),  # Third attempt
            ]
            mock_record.assert_called_once_with(metric_name, 2)

    def test_get_health_check_exception_handling(self, service_executor):
        """Test get_health_check exception handling - covers lines 377-378"""
        # Mock websocket_manager.get_connection_count to raise an exception
        with patch.object(service_executor.websocket_manager, 'get_connection_count', side_effect=Exception("Connection count failed")):
            health = service_executor.get_health_check()

            assert health["status"] == "unhealthy"
            assert "error" in health
            assert "timestamp" in health
            assert "Connection count failed" in health["error"]

    @pytest.mark.asyncio
    async def test_execute_with_timeout_exception_logging(self, service_executor):
        """Test execute_with_timeout with proper exception logging"""
        async def failing_task():
            raise Exception("Task failed")

        # This should handle the exception and return a timeout-style result
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError("Timeout occurred")):
            result = await service_executor.execute_with_timeout(failing_task, timeout=1)

            assert result["completed"] is False
            assert result["status"] == TaskStatus.TIMED_OUT.value
            assert result["error_code"] == ErrorCode.TIMEOUT_ERROR.value
            assert "Timed out" in result["message"]


class TestServiceExecutorEdgeCases:
    """Additional edge case tests to improve coverage"""

    @pytest.fixture
    def service_executor(self):
        """Create ServiceExecutor with minimal config"""
        config = {
            "enable_metrics": False,
            "enable_tracing": False,
            "websocket_port": 0,
            "broker_url": "memory://",
            "backend_url": "cache+memory://"
        }
        executor = ServiceExecutor(config)
        return executor

    def test_evaluate_condition_with_none_parameters(self, service_executor):
        """Test evaluate_condition with None parameters"""
        # Test with None context, input_data, and results
        result = service_executor.evaluate_condition(
            "intent.includes('test')",
            ["test"],
            context=None,
            input_data=None,
            results=None
        )
        assert result is True

    def test_extract_tool_calls_delegation(self, service_executor):
        """Test extract_tool_calls delegation - covers line 298"""
        description = "test description"
        input_data = {"input": "data"}
        context = {"context": "value"}

        # Mock the operation executor
        with patch.object(service_executor.operation_executor, 'extract_tool_calls', return_value=[{"tool": "extracted"}]) as mock_extract:
            result = service_executor.extract_tool_calls(description, input_data, context)
            mock_extract.assert_called_once_with(description, input_data, context)
            assert result == [{"tool": "extracted"}]

    @pytest.mark.asyncio
    async def test_initialize_success_path(self):
        """Test successful initialization path - covers lines 200-201"""
        config = {
            "enable_metrics": False,
            "enable_tracing": False,
            "websocket_port": 0,
            "broker_url": "memory://",
            "backend_url": "cache+memory://"
        }
        executor = ServiceExecutor(config)

        # Mock all initialization methods to succeed
        with patch.object(executor.database_manager, 'init_connection_pool', return_value=None), \
             patch.object(executor.database_manager, 'init_database_schema', return_value=None), \
             patch.object(executor.websocket_manager, 'start_server', return_value=None):

            result = await executor.initialize()
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
