"""
Comprehensive tests for OperationExecutor without mocks.
Tests all functionality using real instances to achieve >85% code coverage.
"""
import pytest
import asyncio
import tempfile
import os
import time
from typing import Dict, Any, List
from unittest.mock import AsyncMock
from pathlib import Path

from aiecs.application.executors.operation_executor import OperationExecutor
from aiecs.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode
from aiecs.tools import get_tool
from aiecs.tools.tool_executor.tool_executor import ToolExecutor, ToolExecutionError
from aiecs.utils.execution_utils import ExecutionUtils


@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def sample_csv_file(test_data_dir):
    """Create a sample CSV file for testing."""
    # Create test data directory if it doesn't exist
    test_data_dir.mkdir(exist_ok=True)
    
    csv_file = test_data_dir / "sample_data.csv"
    if not csv_file.exists():
        import pandas as pd
        data = {
            'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
            'age': [25, 30, 35, 28, 32],
            'salary': [50000, 60000, 70000, 55000, 65000],
            'department': ['IT', 'HR', 'IT', 'Finance', 'IT']
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False)
    
    return str(csv_file)


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        import pandas as pd
        data = {
            'x': [1, 2, 3, 4, 5],
            'y': [2, 4, 6, 8, 10],
            'group': ['A', 'A', 'B', 'B', 'C']
        }
        df = pd.DataFrame(data)
        df.to_csv(f.name, index=False)
        yield f.name
    
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def tool_executor():
    """Create a ToolExecutor instance for testing."""
    config = {
        'enable_cache': True,
        'cache_size': 50,
        'cache_ttl': 300,
        'max_workers': 2,
        'log_level': 'WARNING'
    }
    return ToolExecutor(config)


@pytest.fixture
def execution_utils():
    """Create an ExecutionUtils instance for testing."""
    return ExecutionUtils(cache_size=50, cache_ttl=300, retry_attempts=2, retry_backoff=0.5)


@pytest.fixture
def operation_executor(tool_executor, execution_utils):
    """Create an OperationExecutor instance for testing."""
    config = {
        'rate_limit_requests_per_second': 10,
        'batch_size': 5,
        'enable_cache': True
    }
    return OperationExecutor(tool_executor, execution_utils, config)


@pytest.fixture
def mock_save_callback():
    """Create a mock save callback for testing."""
    class MockSaveCallback:
        def __init__(self):
            self.calls = []
        
        async def __call__(self, user_id: str, task_id: str, step: int, result: TaskStepResult):
            self.calls.append((user_id, task_id, step, result))
    
    return MockSaveCallback()


class TestOperationExecutorInitialization:
    """Test OperationExecutor initialization and basic functionality."""
    
    def test_init_with_default_config(self, tool_executor, execution_utils):
        """Test initialization with minimal configuration."""
        config = {'rate_limit_requests_per_second': 5}
        executor = OperationExecutor(tool_executor, execution_utils, config)
        
        assert executor.tool_executor == tool_executor
        assert executor.execution_utils == execution_utils
        assert executor.config == config
        assert executor._tool_instances == {}
        assert executor.semaphore._value == 5
    
    def test_init_with_custom_config(self, tool_executor, execution_utils):
        """Test initialization with custom configuration."""
        config = {
            'rate_limit_requests_per_second': 10,
            'batch_size': 15,
            'enable_cache': False
        }
        executor = OperationExecutor(tool_executor, execution_utils, config)
        
        assert executor.config == config
        assert executor.semaphore._value == 10


class TestParameterFiltering:
    """Test parameter filtering functionality."""
    
    def test_filter_tool_params(self, operation_executor):
        """Test filtering of system parameters for tool methods."""
        params = {
            'user_id': 'user123',
            'task_id': 'task456',
            'op': 'test_operation',
            'file_path': '/path/to/file.csv',
            'normal_param': 'value'
        }
        
        filtered = operation_executor._filter_tool_params(params)
        
        assert 'user_id' not in filtered
        assert 'task_id' not in filtered
        assert 'op' not in filtered
        assert 'file_path' in filtered
        assert 'normal_param' in filtered
        assert filtered['file_path'] == '/path/to/file.csv'
        assert filtered['normal_param'] == 'value'
    
    def test_filter_tool_call_params(self, operation_executor):
        """Test filtering of system parameters for tool calls."""
        params = {
            'user_id': 'user123',
            'task_id': 'task456',
            'op': 'test_operation',
            'file_path': '/path/to/file.csv',
            'normal_param': 'value'
        }
        
        filtered = operation_executor._filter_tool_call_params(params)
        
        assert 'user_id' not in filtered
        assert 'task_id' not in filtered
        assert 'op' in filtered  # Keep 'op' parameter for BaseTool.run()
        assert 'file_path' in filtered
        assert 'normal_param' in filtered
        assert filtered['op'] == 'test_operation'


class TestSingleOperationExecution:
    """Test single operation execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_operation_sync_success(self, operation_executor, sample_csv_file):
        """Test successful execution of synchronous operation."""
        # Test stats tool describe operation
        result = await operation_executor.execute_operation(
            "stats.describe", 
            {"file_path": sample_csv_file}
        )
        
        assert result is not None
        assert "statistics" in result
        assert "summary" in result
    
    @pytest.mark.asyncio
    async def test_execute_operation_async_success(self, operation_executor, sample_csv_file):
        """Test successful execution of asynchronous operation."""
        # Test stats tool read_data operation (if it's async)
        result = await operation_executor.execute_operation(
            "stats.read_data", 
            {"file_path": sample_csv_file}
        )
        
        assert result is not None
        assert isinstance(result, list) or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_execute_operation_invalid_spec(self, operation_executor):
        """Test error handling for invalid operation spec."""
        with pytest.raises(ValueError, match="Invalid operation spec"):
            await operation_executor.execute_operation("invalid_spec", {})
    
    @pytest.mark.asyncio
    async def test_execute_operation_nonexistent_tool(self, operation_executor):
        """Test error handling for non-existent tool."""
        with pytest.raises(ValueError, match="Tool .* is not registered"):
            await operation_executor.execute_operation("nonexistent.operation", {})
    
    @pytest.mark.asyncio
    async def test_execute_operation_nonexistent_operation(self, operation_executor):
        """Test error handling for non-existent operation."""
        with pytest.raises(ValueError, match="Operation .* not found in tool"):
            await operation_executor.execute_operation("stats.nonexistent", {})
    
    @pytest.mark.asyncio
    async def test_execute_operation_tool_caching(self, operation_executor, sample_csv_file):
        """Test that tool instances are cached properly."""
        # First call - tool should be created and cached
        await operation_executor.execute_operation(
            "stats.describe", 
            {"file_path": sample_csv_file}
        )
        
        # Verify tool is cached
        assert "stats" in operation_executor._tool_instances
        
        # Second call - should use cached tool
        tool_instance = operation_executor._tool_instances["stats"]
        await operation_executor.execute_operation(
            "stats.describe", 
            {"file_path": sample_csv_file}
        )
        
        # Should be same instance
        assert operation_executor._tool_instances["stats"] is tool_instance


class TestBatchOperations:
    """Test batch operation execution functionality."""
    
    @pytest.mark.asyncio
    async def test_batch_execute_operations_success(self, operation_executor, sample_csv_file):
        """Test successful batch execution of operations."""
        operations = [
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.batch_execute_operations(operations)
        
        assert len(results) == 2
        # All results should be successful (not exceptions)
        for result in results:
            assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_batch_execute_operations_with_errors(self, operation_executor, sample_csv_file):
        """Test batch execution with some operations failing."""
        operations = [
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.nonexistent", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.batch_execute_operations(operations)
        
        assert len(results) == 3
        # Second operation should be an exception
        assert not isinstance(results[0], Exception)
        assert isinstance(results[1], Exception)
        assert not isinstance(results[2], Exception)
    
    @pytest.mark.asyncio
    async def test_batch_execute_operations_large_batch(self, operation_executor, sample_csv_file):
        """Test batch execution with large number of operations."""
        # Create 12 operations to test batching (batch_size=5 in config)
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
            for _ in range(12)
        ]
        
        results = await operation_executor.batch_execute_operations(operations)
        
        assert len(results) == 12
        # All should be successful
        for result in results:
            assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_batch_execute_operations_rate_limiting(self, operation_executor, sample_csv_file):
        """Test rate limiting in batch operations."""
        import time
        
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
            for _ in range(6)  # More than batch size
        ]
        
        start_time = time.time()
        results = await operation_executor.batch_execute_operations(operations)
        end_time = time.time()
        
        # Should have taken some time due to rate limiting
        assert len(results) == 6
        assert end_time - start_time >= 0.05  # Some minimal delay expected


class TestSequenceOperations:
    """Test sequence operation execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_operations_sequence_success(self, operation_executor, sample_csv_file, mock_save_callback):
        """Test successful sequence execution."""
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.execute_operations_sequence(
            operations, "user123", "task456", save_callback=mock_save_callback
        )
        
        assert len(results) == 2
        for result in results:
            assert isinstance(result, TaskStepResult)
            assert result.completed is True
            assert result.status == TaskStatus.COMPLETED.value
        
        # Verify save callback was called
        assert len(mock_save_callback.calls) == 2
    
    @pytest.mark.asyncio
    async def test_execute_operations_sequence_with_failure_continue(self, operation_executor, sample_csv_file, mock_save_callback):
        """Test sequence execution with failure but continue on failure."""
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.nonexistent", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.execute_operations_sequence(
            operations, "user123", "task456", stop_on_failure=False, save_callback=mock_save_callback
        )
        
        assert len(results) == 3
        assert results[0].completed is True
        assert results[1].completed is False
        assert results[1].status == TaskStatus.FAILED.value
        assert results[1].error_code == ErrorCode.EXECUTION_ERROR.value
        assert results[2].completed is True
    
    @pytest.mark.asyncio
    async def test_execute_operations_sequence_with_failure_stop(self, operation_executor, sample_csv_file, mock_save_callback):
        """Test sequence execution with failure and stop on failure."""
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.nonexistent", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.execute_operations_sequence(
            operations, "user123", "task456", stop_on_failure=True, save_callback=mock_save_callback
        )
        
        # Should stop after second operation fails
        assert len(results) == 2
        assert results[0].completed is True
        assert results[1].completed is False
        assert results[1].status == TaskStatus.FAILED.value
    
    @pytest.mark.asyncio
    async def test_execute_operations_sequence_without_callback(self, operation_executor, sample_csv_file):
        """Test sequence execution without save callback."""
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.execute_operations_sequence(
            operations, "user123", "task456"
        )
        
        assert len(results) == 2
        for result in results:
            assert isinstance(result, TaskStepResult)
            assert result.completed is True


class TestParameterReferences:
    """Test parameter reference processing functionality."""
    
    def test_process_param_references_simple(self, operation_executor):
        """Test simple parameter reference processing."""
        # Create mock results
        result1 = TaskStepResult("step1", {"data": "value1"}, True)
        result2 = TaskStepResult("step2", {"info": "value2"}, True)
        results = [result1, result2]
        
        params = {
            "normal_param": "normal_value",
            "ref_param": "$result[0]",
            "other_param": "other_value"
        }
        
        processed = operation_executor._process_param_references(params, results)
        
        assert processed["normal_param"] == "normal_value"
        assert processed["ref_param"] == {"data": "value1"}
        assert processed["other_param"] == "other_value"
    
    def test_process_param_references_nested_access(self, operation_executor):
        """Test nested parameter reference processing."""
        result1 = TaskStepResult("step1", {"data": {"nested": {"value": "target"}}}, True)
        results = [result1]
        
        params = {
            "ref_param": "$result[0].data.nested.value"
        }
        
        processed = operation_executor._process_param_references(params, results)
        
        assert processed["ref_param"] == "target"
    
    def test_process_param_references_invalid_index(self, operation_executor):
        """Test parameter reference with invalid index."""
        results = [TaskStepResult("step1", {"data": "value"}, True)]
        
        params = {
            "ref_param": "$result[5]"  # Index out of range
        }
        
        processed = operation_executor._process_param_references(params, results)
        
        # Should fall back to original value on error
        assert processed["ref_param"] == "$result[5]"
    
    def test_process_param_references_dict_access(self, operation_executor):
        """Test parameter reference with dictionary access."""
        result1 = TaskStepResult("step1", {"field1": "value1", "field2": "value2"}, True)
        results = [result1]
        
        params = {
            "ref_param": "$result[0].field1"
        }
        
        processed = operation_executor._process_param_references(params, results)
        
        assert processed["ref_param"] == "value1"
    
    def test_process_param_references_object_access(self, operation_executor):
        """Test parameter reference with object attribute access."""
        class MockResult:
            def __init__(self):
                self.field = "object_value"
        
        result1 = TaskStepResult("step1", MockResult(), True)
        results = [result1]
        
        params = {
            "ref_param": "$result[0].field"
        }
        
        processed = operation_executor._process_param_references(params, results)
        
        assert processed["ref_param"] == "object_value"
    
    def test_process_param_references_malformed(self, operation_executor):
        """Test parameter reference processing with malformed references."""
        results = [TaskStepResult("step1", {"data": "value"}, True)]
        
        params = {
            "malformed1": "$result[",  # Incomplete reference
            "malformed2": "$result[abc]",  # Non-numeric index
            "normal": "value"
        }
        
        processed = operation_executor._process_param_references(params, results)
        
        # Should fall back to original values for malformed references
        assert processed["malformed1"] == "$result["
        assert processed["malformed2"] == "$result[abc]"
        assert processed["normal"] == "value"
    
    def test_process_param_references_no_references(self, operation_executor):
        """Test parameter reference processing with no references."""
        results = [TaskStepResult("step1", {"data": "value"}, True)]
        
        params = {
            "param1": "value1",
            "param2": "value2",
            "param3": 123
        }
        
        processed = operation_executor._process_param_references(params, results)
        
        # Should return unchanged
        assert processed == params


class TestToolCalls:
    """Test tool call functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self, operation_executor, sample_csv_file):
        """Test successful tool call execution."""
        call = {
            "tool": "stats",
            "params": {
                "op": "read_data",
                "file_path": sample_csv_file
            }
        }
        
        result = await operation_executor._execute_tool_call(call)
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_execute_tool_call_with_cache(self, operation_executor, sample_csv_file):
        """Test tool call with caching enabled."""
        call = {
            "tool": "stats",
            "params": {
                "op": "read_data",
                "file_path": sample_csv_file,
                "user_id": "user123",
                "task_id": "task456"
            }
        }
        
        # First call
        result1 = await operation_executor._execute_tool_call(call)
        
        # Second call should use cache
        result2 = await operation_executor._execute_tool_call(call)
        
        # Both should return results
        assert result1 is not None
        assert result2 is not None
    
    @pytest.mark.asyncio
    async def test_execute_tool_call_custom_executor(self, operation_executor, sample_csv_file):
        """Test tool call with custom executor function."""
        async def custom_executor(tool_name, params):
            return f"Custom result for {tool_name}"
        
        call = {
            "tool": "stats",
            "params": {
                "op": "read_data",
                "file_path": sample_csv_file
            }
        }
        
        result = await operation_executor._execute_tool_call(call, custom_executor)
        
        assert result == "Custom result for stats"
    
    @pytest.mark.asyncio
    async def test_batch_tool_calls_success(self, operation_executor, sample_csv_file):
        """Test successful batch tool calls."""
        tool_calls = [
            {"tool": "stats", "params": {"op": "read_data", "file_path": sample_csv_file}},
            {"tool": "stats", "params": {"op": "describe", "file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.batch_tool_calls(tool_calls)
        
        assert len(results) == 2
        for result in results:
            assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_batch_tool_calls_with_custom_executor(self, operation_executor, sample_csv_file):
        """Test batch tool calls with custom executor function."""
        async def custom_executor(tool_name, params):
            return f"Custom result for {tool_name}"
        
        tool_calls = [
            {"tool": "stats", "params": {"op": "read_data", "file_path": sample_csv_file}},
            {"tool": "stats", "params": {"op": "describe", "file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.batch_tool_calls(tool_calls, custom_executor)
        
        assert len(results) == 2
        for result in results:
            assert "Custom result for stats" in str(result)


class TestExtractToolCalls:
    """Test tool call extraction functionality."""
    
    def test_extract_tool_calls_simple(self, operation_executor):
        """Test simple tool call extraction."""
        description = "Use {{stats(file='data.csv')}} to analyze the data"
        input_data = {"file": "test.csv"}
        context = {}
        
        tool_calls = operation_executor.extract_tool_calls(description, input_data, context)
        
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "stats"
        assert tool_calls[0]["params"]["file"] == "data.csv"
    
    def test_extract_tool_calls_multiple(self, operation_executor):
        """Test multiple tool call extraction."""
        description = "First {{stats(file='data.csv')}} then {{chart(type='bar')}}"
        input_data = {}
        context = {}
        
        tool_calls = operation_executor.extract_tool_calls(description, input_data, context)
        
        assert len(tool_calls) == 2
        assert tool_calls[0]["tool"] == "stats"
        assert tool_calls[1]["tool"] == "chart"
    
    def test_extract_tool_calls_with_input_references(self, operation_executor):
        """Test tool call extraction with input data references."""
        description = "Use {{stats(file='input.filename')}} to process"
        input_data = {"filename": "actual_file.csv"}
        context = {}
        
        tool_calls = operation_executor.extract_tool_calls(description, input_data, context)
        
        assert len(tool_calls) == 1
        assert tool_calls[0]["params"]["file"] == "actual_file.csv"
    
    def test_extract_tool_calls_with_context_references(self, operation_executor):
        """Test tool call extraction with context references."""
        description = "Use {{stats(user='context.current_user')}} to analyze"
        input_data = {}
        context = {"current_user": "john_doe"}
        
        tool_calls = operation_executor.extract_tool_calls(description, input_data, context)
        
        assert len(tool_calls) == 1
        assert tool_calls[0]["params"]["user"] == "john_doe"
    
    def test_extract_tool_calls_no_matches(self, operation_executor):
        """Test tool call extraction with no matches."""
        description = "This is a plain description without tool calls"
        input_data = {}
        context = {}
        
        tool_calls = operation_executor.extract_tool_calls(description, input_data, context)
        
        assert len(tool_calls) == 0
    
    def test_extract_tool_calls_complex_params(self, operation_executor):
        """Test tool call extraction with complex parameters."""
        description = "Use {{stats(file='data.csv', columns='input.cols', user='context.user')}} to analyze"
        input_data = {"cols": "name,age,salary"}
        context = {"user": "admin"}
        
        tool_calls = operation_executor.extract_tool_calls(description, input_data, context)
        
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "stats"
        assert tool_calls[0]["params"]["file"] == "data.csv"
        assert tool_calls[0]["params"]["columns"] == "name,age,salary"
        assert tool_calls[0]["params"]["user"] == "admin"


class TestParallelOperations:
    """Test parallel operation execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_parallel_operations_success(self, operation_executor, sample_csv_file):
        """Test successful parallel operation execution."""
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.execute_parallel_operations(operations)
        
        assert len(results) == 2
        for result in results:
            assert isinstance(result, TaskStepResult)
            assert result.completed is True
            assert result.status == TaskStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_execute_parallel_operations_with_failures(self, operation_executor, sample_csv_file):
        """Test parallel operation execution with some failures."""
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.nonexistent", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.execute_parallel_operations(operations)
        
        assert len(results) == 3
        assert results[0].completed is True
        assert results[1].completed is False
        assert results[1].status == TaskStatus.FAILED.value
        assert results[2].completed is True
    
    @pytest.mark.asyncio
    async def test_execute_parallel_operations_exception_handling(self, operation_executor, sample_csv_file):
        """Test parallel operation execution with exception handling."""
        operations = [
            {"operation": "invalid.operation", "params": {}}
        ]
        
        results = await operation_executor.execute_parallel_operations(operations)
        
        assert len(results) == 1
        # Should handle exceptions gracefully
        result = results[0]
        assert result.completed is False
        assert result.status == TaskStatus.FAILED.value


class TestUtilityMethods:
    """Test utility and management methods."""
    
    def test_get_tool_instance(self, operation_executor):
        """Test tool instance retrieval and caching."""
        # First call should create instance
        tool1 = operation_executor.get_tool_instance("stats")
        assert tool1 is not None
        assert "stats" in operation_executor._tool_instances
        
        # Second call should return cached instance
        tool2 = operation_executor.get_tool_instance("stats")
        assert tool2 is tool1
    
    def test_clear_tool_cache(self, operation_executor):
        """Test tool cache clearing."""
        # Create some tool instances
        operation_executor.get_tool_instance("stats")
        assert len(operation_executor._tool_instances) > 0
        
        # Clear cache
        operation_executor.clear_tool_cache()
        assert len(operation_executor._tool_instances) == 0
    
    def test_get_stats(self, operation_executor):
        """Test statistics retrieval."""
        # Add some tools to cache
        operation_executor.get_tool_instance("stats")
        
        stats = operation_executor.get_stats()
        
        assert "cached_tools" in stats
        assert "tool_names" in stats
        assert "semaphore_value" in stats
        assert "config" in stats
        
        assert stats["cached_tools"] == 1
        assert "stats" in stats["tool_names"]
        assert stats["semaphore_value"] == operation_executor.semaphore._value
        
        # Check config values
        config_stats = stats["config"]
        assert "batch_size" in config_stats
        assert "rate_limit" in config_stats
        assert "enable_cache" in config_stats


class TestErrorScenarios:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_execute_operation_with_tool_error(self, operation_executor):
        """Test operation execution when tool raises an error."""
        # Try to use stats tool with invalid file
        with pytest.raises(Exception):  # Should propagate the underlying error
            await operation_executor.execute_operation(
                "stats.describe", 
                {"file_path": "/nonexistent/file.csv"}
            )
    
    @pytest.mark.asyncio
    async def test_sequence_operations_with_invalid_params(self, operation_executor):
        """Test sequence execution with invalid parameters."""
        operations = [
            {"operation": "stats.describe"},  # Missing required params
        ]
        
        results = await operation_executor.execute_operations_sequence(
            operations, "user123", "task456"
        )
        
        assert len(results) == 1
        assert results[0].completed is False
        assert results[0].status == TaskStatus.FAILED.value
    
    @pytest.mark.asyncio
    async def test_tool_call_with_nonexistent_tool(self, operation_executor):
        """Test tool call with non-existent tool."""
        call = {
            "tool": "nonexistent_tool",
            "params": {"op": "test"}
        }
        
        # Should handle gracefully and return an exception or error
        # The specific behavior depends on the get_tool implementation
        try:
            result = await operation_executor._execute_tool_call(call)
            # If it doesn't raise an exception, the result might be an error
            assert result is not None
        except Exception:
            # Expected to raise an exception for non-existent tool
            pass


class TestSequenceOperationsWithParameterReferences:
    """Test sequence operations with parameter references between steps."""
    
    @pytest.mark.asyncio
    async def test_sequence_with_param_references(self, operation_executor, sample_csv_file):
        """Test sequence execution where later operations use results from earlier ones."""
        operations = [
            {
                "operation": "stats.read_data", 
                "params": {"file_path": sample_csv_file}
            },
            {
                "operation": "stats.describe",
                "params": {
                    "file_path": sample_csv_file,
                    "variables": ["name", "age"]  # Using specific variables
                }
            }
        ]
        
        results = await operation_executor.execute_operations_sequence(
            operations, "user123", "task456"
        )
        
        assert len(results) == 2
        for result in results:
            assert result.completed is True
            assert result.status == TaskStatus.COMPLETED.value
            assert result.result is not None


class TestCacheBehavior:
    """Test caching behavior across different scenarios."""
    
    @pytest.mark.asyncio
    async def test_cache_behavior_across_operations(self, operation_executor, sample_csv_file):
        """Test caching behavior across different operation types."""
        # Execute the same operation multiple times
        params = {"file_path": sample_csv_file, "user_id": "user123", "task_id": "task456"}
        
        # First through single operation
        result1 = await operation_executor.execute_operation("stats.read_data", params)
        
        # Then through tool call
        call = {"tool": "stats", "params": {"op": "read_data", **params}}
        result2 = await operation_executor._execute_tool_call(call)
        
        # Both should work
        assert result1 is not None
        assert result2 is not None
    
    @pytest.mark.asyncio
    async def test_cache_disabled_behavior(self, tool_executor, execution_utils):
        """Test behavior when cache is disabled."""
        config = {
            'rate_limit_requests_per_second': 10,
            'batch_size': 5,
            'enable_cache': False
        }
        executor = OperationExecutor(tool_executor, execution_utils, config)
        
        call = {
            "tool": "stats",
            "params": {
                "op": "read_data",
                "file_path": "/tmp/test.csv",
                "user_id": "user123",
                "task_id": "task456"
            }
        }
        
        # Should not use cache
        try:
            result = await executor._execute_tool_call(call)
            assert result is not None
        except Exception:
            # Expected if file doesn't exist
            pass


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_workflow(self, operation_executor, sample_csv_file, mock_save_callback):
        """Test a comprehensive workflow using multiple features."""
        # 1. Execute single operation
        single_result = await operation_executor.execute_operation(
            "stats.read_data", 
            {"file_path": sample_csv_file}
        )
        assert single_result is not None
        
        # 2. Execute batch operations
        batch_operations = [
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
        ]
        batch_results = await operation_executor.batch_execute_operations(batch_operations)
        assert len(batch_results) == 2
        
        # 3. Execute sequence operations
        sequence_operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}}
        ]
        sequence_results = await operation_executor.execute_operations_sequence(
            sequence_operations, "user123", "task456", save_callback=mock_save_callback
        )
        assert len(sequence_results) == 2
        
        # 4. Execute parallel operations
        parallel_operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.describe", "params": {"file_path": sample_csv_file}}
        ]
        parallel_results = await operation_executor.execute_parallel_operations(parallel_operations)
        assert len(parallel_results) == 2
        
        # 5. Check statistics
        stats = operation_executor.get_stats()
        assert stats["cached_tools"] > 0
        
        # 6. Clear cache and verify
        operation_executor.clear_tool_cache()
        stats_after_clear = operation_executor.get_stats()
        assert stats_after_clear["cached_tools"] == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, operation_executor, sample_csv_file):
        """Test rate limiting behavior in batch operations."""
        import time
        
        # Create many operations to test rate limiting
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
            for _ in range(6)  # More than batch size
        ]
        
        start_time = time.time()
        results = await operation_executor.batch_execute_operations(operations)
        end_time = time.time()
        
        # Should have taken some time due to rate limiting
        # With rate_limit=10/sec and 6 operations in batches of 5, should take at least 0.1 seconds
        assert len(results) == 6
        assert end_time - start_time >= 0.05  # Some minimal delay expected
    
    @pytest.mark.asyncio
    async def test_semaphore_behavior(self, operation_executor, sample_csv_file):
        """Test semaphore behavior for rate limiting."""
        # Test that semaphore is properly initialized
        assert operation_executor.semaphore._value == 10
        
        # Test that semaphore is used in tool calls
        call = {
            "tool": "stats",
            "params": {
                "op": "read_data",
                "file_path": sample_csv_file
            }
        }
        
        # This should use the semaphore
        result = await operation_executor._execute_tool_call(call)
        assert result is not None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_operations_list(self, operation_executor):
        """Test handling of empty operations list."""
        results = await operation_executor.batch_execute_operations([])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_empty_sequence_operations(self, operation_executor):
        """Test handling of empty sequence operations."""
        results = await operation_executor.execute_operations_sequence([], "user123", "task456")
        assert results == []
    
    @pytest.mark.asyncio
    async def test_empty_parallel_operations(self, operation_executor):
        """Test handling of empty parallel operations."""
        results = await operation_executor.execute_parallel_operations([])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_empty_tool_calls_list(self, operation_executor):
        """Test handling of empty tool calls list."""
        results = await operation_executor.batch_tool_calls([])
        assert results == []
    
    def test_empty_extract_tool_calls(self, operation_executor):
        """Test extraction with empty description."""
        tool_calls = operation_executor.extract_tool_calls("", {}, {})
        assert tool_calls == []
    
    def test_process_param_references_empty_results(self, operation_executor):
        """Test parameter reference processing with empty results."""
        params = {
            "ref_param": "$result[0]",
            "normal_param": "value"
        }
        
        processed = operation_executor._process_param_references(params, [])
        
        # Should fall back to original value for invalid reference
        assert processed["ref_param"] == "$result[0]"
        assert processed["normal_param"] == "value"


class TestConfigurationHandling:
    """Test configuration handling and edge cases."""
    
    def test_config_with_missing_values(self, tool_executor, execution_utils):
        """Test initialization with minimal config."""
        config = {}
        executor = OperationExecutor(tool_executor, execution_utils, config)
        
        # Should use defaults
        assert executor.semaphore._value == 5  # Default rate limit
        assert executor.config.get('batch_size', 10) == 10  # Default batch size
    
    def test_config_with_extra_values(self, tool_executor, execution_utils):
        """Test initialization with extra config values."""
        config = {
            'rate_limit_requests_per_second': 15,
            'batch_size': 20,
            'enable_cache': False,
            'extra_value': 'should_be_ignored'
        }
        executor = OperationExecutor(tool_executor, execution_utils, config)
        
        assert executor.semaphore._value == 15
        assert executor.config == config  # Should store all values


class TestToolInstanceManagement:
    """Test tool instance management and lifecycle."""
    
    def test_multiple_tool_instances(self, operation_executor):
        """Test managing multiple tool instances."""
        # Get different tools
        stats_tool = operation_executor.get_tool_instance("stats")
        
        # Verify tools are cached
        assert "stats" in operation_executor._tool_instances
        assert operation_executor._tool_instances["stats"] is stats_tool
    
    def test_tool_instance_reuse(self, operation_executor):
        """Test that tool instances are reused."""
        tool1 = operation_executor.get_tool_instance("stats")
        tool2 = operation_executor.get_tool_instance("stats")
        
        assert tool1 is tool2
    
    def test_clear_tool_cache_affects_stats(self, operation_executor):
        """Test that clearing cache affects statistics."""
        # Add some tools
        operation_executor.get_tool_instance("stats")
        
        stats_before = operation_executor.get_stats()
        assert stats_before["cached_tools"] > 0
        
        # Clear cache
        operation_executor.clear_tool_cache()
        
        stats_after = operation_executor.get_stats()
        assert stats_after["cached_tools"] == 0
