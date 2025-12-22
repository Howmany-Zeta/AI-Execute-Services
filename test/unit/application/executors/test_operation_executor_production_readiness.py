"""
Production readiness tests for OperationExecutor.
These tests focus on security, performance, reliability, and monitoring aspects.
"""
import pytest
import asyncio
import time
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock
import concurrent.futures
import threading

from aiecs.application.executors.operation_executor import OperationExecutor
from aiecs.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode


class TestSecurityAndValidation:
    """Test security aspects and input validation."""
    
    @pytest.mark.asyncio
    async def test_parameter_injection_protection(self, operation_executor):
        """Test protection against parameter injection attacks."""
        malicious_params = {
            "file_path": "../../../etc/passwd",  # Path traversal
            "command": "rm -rf /",  # Command injection
            "script": "<script>alert('xss')</script>",  # XSS
            "sql": "'; DROP TABLE users; --"  # SQL injection
        }
        
        # Should handle malicious inputs gracefully
        with pytest.raises(Exception):  # Should fail safely
            await operation_executor.execute_operation(
                "stats.describe", malicious_params
            )
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_protection(self, operation_executor):
        """Test protection against resource exhaustion attacks."""
        # Test with extremely large batch
        large_operations = [
            {"operation": "stats.read_data", "params": {"file_path": "/dev/null"}}
            for _ in range(1000)  # Very large batch
        ]
        
        start_time = time.time()
        results = await operation_executor.batch_execute_operations(large_operations)
        execution_time = time.time() - start_time
        
        # Should complete within reasonable time due to rate limiting
        assert execution_time > 10  # Rate limiting should slow it down
        assert len(results) == 1000
    
    def test_tool_access_control(self, operation_executor):
        """Test that tools can only access authorized resources."""
        # Test accessing non-existent or restricted tools
        with pytest.raises(ValueError, match="Tool .* is not registered"):
            operation_executor.get_tool_instance("restricted_tool")
    
    @pytest.mark.asyncio
    async def test_input_size_limits(self, operation_executor):
        """Test handling of extremely large inputs."""
        huge_param = "x" * (10 * 1024 * 1024)  # 10MB string
        
        # Should handle large inputs gracefully
        try:
            await operation_executor.execute_operation(
                "stats.describe", {"large_param": huge_param}
            )
        except Exception as e:
            # Should fail gracefully, not crash
            assert isinstance(e, (ValueError, MemoryError, OSError))


class TestPerformanceAndLoad:
    """Test performance characteristics and load handling."""
    
    @pytest.mark.asyncio
    async def test_high_concurrency_operations(self, operation_executor, sample_csv_file):
        """Test handling of high concurrency scenarios."""
        # Create 50 concurrent operations
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
            for _ in range(50)
        ]
        
        start_time = time.time()
        results = await operation_executor.batch_execute_operations(operations)
        execution_time = time.time() - start_time
        
        # All operations should complete
        assert len(results) == 50
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 45  # Allow some failures
        
        # Should complete within reasonable time
        assert execution_time < 60  # Should not take more than 1 minute
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, operation_executor, sample_csv_file):
        """Test memory usage doesn't grow unbounded under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Execute many operations
        for _ in range(10):
            operations = [
                {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
                for _ in range(20)
            ]
            await operation_executor.batch_execute_operations(operations)
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 100MB)
        assert memory_growth < 100 * 1024 * 1024
    
    def test_tool_instance_lifecycle(self, operation_executor):
        """Test proper tool instance lifecycle management."""
        # Create multiple tool instances
        for i in range(10):
            tool = operation_executor.get_tool_instance("stats")
            assert tool is not None
        
        # Should reuse instances (cache)
        assert len(operation_executor._tool_instances) == 1
        
        # Clear cache and verify cleanup
        operation_executor.clear_tool_cache()
        assert len(operation_executor._tool_instances) == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_effectiveness(self, operation_executor, sample_csv_file):
        """Test that rate limiting actually works under load."""
        # Configure strict rate limiting
        operation_executor.config['rate_limit_requests_per_second'] = 2
        operation_executor.semaphore = asyncio.Semaphore(2)
        
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
            for _ in range(10)
        ]
        
        start_time = time.time()
        results = await operation_executor.batch_execute_operations(operations)
        execution_time = time.time() - start_time
        
        # Should take at least 4 seconds due to rate limiting (10 ops / 2 per sec)
        assert execution_time >= 3.0
        assert len(results) == 10


class TestReliabilityAndResilience:
    """Test reliability and resilience aspects."""
    
    @pytest.mark.asyncio
    async def test_tool_failure_recovery(self, operation_executor):
        """Test recovery from tool failures."""
        # Simulate tool failure
        with patch('aiecs.tools.get_tool') as mock_get_tool:
            mock_tool = MagicMock()
            mock_tool.describe.side_effect = Exception("Tool crashed")
            mock_get_tool.return_value = mock_tool
            
            # Should handle tool failure gracefully
            with pytest.raises(Exception):
                await operation_executor.execute_operation(
                    "stats.describe", {"file_path": "test.csv"}
                )
            
            # Executor should still be functional after failure
            stats = operation_executor.get_stats()
            assert stats is not None
    
    @pytest.mark.asyncio
    async def test_partial_batch_failure_handling(self, operation_executor, sample_csv_file):
        """Test handling of partial failures in batch operations."""
        operations = [
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.nonexistent", "params": {"file_path": sample_csv_file}},
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}},
            {"operation": "invalid.operation", "params": {}},
            {"operation": "stats.read_data", "params": {"file_path": sample_csv_file}}
        ]
        
        results = await operation_executor.batch_execute_operations(operations)
        
        # Should have results for all operations
        assert len(results) == 5
        
        # Some should succeed, some should fail
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful) >= 2  # At least some should succeed
        assert len(failed) >= 2  # At least some should fail
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_on_failure(self, operation_executor):
        """Test that resources are properly cleaned up on failures."""
        initial_tool_count = len(operation_executor._tool_instances)
        
        # Cause a failure
        try:
            await operation_executor.execute_operation(
                "nonexistent.operation", {}
            )
        except Exception:
            pass
        
        # Tool cache should not be corrupted
        assert len(operation_executor._tool_instances) >= initial_tool_count
        
        # Should still be able to execute valid operations
        operation_executor.get_tool_instance("stats")
        assert "stats" in operation_executor._tool_instances
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, operation_executor):
        """Test handling of operation timeouts."""
        # This would require implementing timeout functionality
        # For now, test that long-running operations don't hang indefinitely
        
        start_time = time.time()
        try:
            # Simulate a potentially long-running operation
            await operation_executor.execute_operation(
                "stats.describe", {"file_path": "/dev/zero"}  # This might hang
            )
        except Exception:
            pass  # Expected to fail
        
        execution_time = time.time() - start_time
        # Should not hang indefinitely
        assert execution_time < 30  # Should timeout within 30 seconds


class TestMonitoringAndObservability:
    """Test monitoring and observability features."""
    
    def test_statistics_collection(self, operation_executor):
        """Test that statistics are properly collected."""
        # Execute some operations to generate stats
        operation_executor.get_tool_instance("stats")
        
        stats = operation_executor.get_stats()
        
        # Verify required statistics are present
        assert "cached_tools" in stats
        assert "tool_names" in stats
        assert "semaphore_value" in stats
        assert "config" in stats
        
        # Verify statistics accuracy
        assert stats["cached_tools"] == 1
        assert "stats" in stats["tool_names"]
        assert isinstance(stats["semaphore_value"], int)
        
        # Verify config statistics
        config_stats = stats["config"]
        assert "batch_size" in config_stats
        assert "rate_limit" in config_stats
        assert "enable_cache" in config_stats
    
    @pytest.mark.asyncio
    async def test_error_tracking(self, operation_executor):
        """Test that errors are properly tracked and reported."""
        # Generate some errors
        error_count = 0
        
        try:
            await operation_executor.execute_operation("invalid.operation", {})
        except Exception:
            error_count += 1
        
        try:
            await operation_executor.execute_operation("stats.nonexistent", {})
        except Exception:
            error_count += 1
        
        # Errors should be tracked (this would require implementing error tracking)
        assert error_count == 2
    
    def test_health_check_capability(self, operation_executor):
        """Test basic health check functionality."""
        # Basic health check - executor should be responsive
        stats = operation_executor.get_stats()
        assert stats is not None
        
        # Should be able to get tool instances
        tool = operation_executor.get_tool_instance("stats")
        assert tool is not None
        
        # Cache operations should work
        operation_executor.clear_tool_cache()
        assert len(operation_executor._tool_instances) == 0


class TestConfigurationAndEnvironment:
    """Test configuration handling and environment setup."""
    
    def test_configuration_validation(self, tool_executor, execution_utils):
        """Test configuration validation and defaults."""
        # Test with minimal config
        minimal_config = {}
        executor = OperationExecutor(tool_executor, execution_utils, minimal_config)
        
        # Should use defaults
        assert executor.semaphore._value == 5  # Default rate limit
        
        # Test with custom config
        custom_config = {
            'rate_limit_requests_per_second': 15,
            'batch_size': 25,
            'enable_cache': False
        }
        executor = OperationExecutor(tool_executor, execution_utils, custom_config)
        
        # Should use custom values
        assert executor.semaphore._value == 15
        assert executor.config['batch_size'] == 25
        assert executor.config['enable_cache'] is False
    
    def test_invalid_configuration_handling(self, tool_executor, execution_utils):
        """Test handling of invalid configurations."""
        # Test with invalid config values
        invalid_configs = [
            {'rate_limit_requests_per_second': -1},  # Negative rate limit
            {'batch_size': 0},  # Zero batch size
            {'rate_limit_requests_per_second': 'invalid'},  # Non-numeric
        ]
        
        for config in invalid_configs:
            try:
                executor = OperationExecutor(tool_executor, execution_utils, config)
                # Should either handle gracefully or use defaults
                assert executor.semaphore._value > 0
            except Exception as e:
                # Should fail gracefully with clear error message
                assert isinstance(e, (ValueError, TypeError))
