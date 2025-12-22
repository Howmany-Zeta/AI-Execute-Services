"""
Integration tests for AIECS complete startup process.
Tests the full application stack including all components working together.
"""
import pytest
import asyncio
import os
import tempfile
import time
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Import AIECS components
import aiecs
from aiecs.config.config import get_settings
from aiecs.infrastructure.monitoring.structured_logger import setup_structured_logging


class TestIntegrationStartup:
    """Integration tests for complete AIECS startup"""

    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Setup environment for integration testing"""
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        
        test_env = {
            'AIECS_ENV': 'test',
            'LOG_LEVEL': 'INFO',  # Use INFO for integration tests
            'TEMP_DIR': self.temp_dir,
            'SKIP_OFFICE_TOOL': 'true',
            'SKIP_IMAGE_TOOL': 'true',
            'SKIP_CHART_TOOL': 'true',
            'STATS_TOOL_MAX_FILE_SIZE_MB': '100',
            'STATS_TOOL_ALLOWED_EXTENSIONS': '[".csv", ".json", ".xlsx"]',
            # Mock external services
            'MOCK_DATABASE': 'true',
            'MOCK_CELERY': 'true',
            'MOCK_REDIS': 'true'
        }
        
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    @pytest.mark.asyncio
    async def test_complete_startup_sequence(self):
        """Test complete startup sequence with all components"""
        startup_steps = []
        
        try:
            # Step 1: Configuration loading
            startup_steps.append("config_loading")
            settings = get_settings()
            assert settings is not None
            
            # Step 2: Logging setup
            startup_steps.append("logging_setup")
            setup_structured_logging()
            
            # Step 3: Tool discovery
            startup_steps.append("tool_discovery")
            from aiecs.tools import discover_tools
            discover_tools("aiecs.tools")
            
            # Step 4: Client creation and initialization
            startup_steps.append("client_creation")
            client = aiecs.create_simple_client()
            
            startup_steps.append("client_initialization")
            await client.initialize()
            
            # Step 5: Verify client is functional
            startup_steps.append("client_verification")
            assert client._initialized
            assert client._tools_discovered
            
            # Step 6: Test basic functionality
            startup_steps.append("functionality_test")
            from aiecs.tools import list_tools
            tools = list_tools()
            assert isinstance(tools, list)
            
            # Step 7: Cleanup
            startup_steps.append("cleanup")
            await client.close()
            
            startup_steps.append("complete")
            
        except Exception as e:
            pytest.fail(f"Startup failed at step {startup_steps[-1] if startup_steps else 'unknown'}: {e}")

    @pytest.mark.asyncio
    async def test_startup_with_error_recovery(self):
        """Test startup with error recovery mechanisms"""
        # Test that startup can recover from non-critical errors
        
        with patch('aiecs.tools.discover_tools') as mock_discover:
            # First call fails, second succeeds
            mock_discover.side_effect = [Exception("Tool discovery failed"), None]
            
            client = aiecs.create_simple_client()
            
            # Should handle the error and continue
            await client.initialize()
            assert client._initialized

    @pytest.mark.asyncio
    async def test_multiple_client_initialization(self):
        """Test multiple clients can be initialized simultaneously"""
        clients = []
        
        try:
            # Create multiple clients
            for i in range(3):
                client = aiecs.create_simple_client()
                clients.append(client)
            
            # Initialize all clients concurrently
            await asyncio.gather(*[client.initialize() for client in clients])
            
            # Verify all are initialized
            for client in clients:
                assert client._initialized
                assert client._tools_discovered
            
        finally:
            # Cleanup all clients
            await asyncio.gather(*[client.close() for client in clients])

    @pytest.mark.asyncio
    async def test_startup_performance_benchmarks(self):
        """Test startup performance meets benchmarks"""
        start_time = time.time()
        
        client = aiecs.create_simple_client()
        await client.initialize()
        
        initialization_time = time.time() - start_time
        
        # Startup should be fast (less than 5 seconds for simple client)
        assert initialization_time < 5.0, f"Initialization too slow: {initialization_time:.2f}s"
        
        await client.close()

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency during startup"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Force garbage collection
        gc.collect()
        
        client = aiecs.create_simple_client()
        await client.initialize()
        
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        
        await client.close()
        
        # Force garbage collection after cleanup
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_after_cleanup = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 50 * 1024 * 1024, f"Memory increase too large: {memory_increase / 1024 / 1024:.2f}MB"
        
        # Memory should be mostly freed after cleanup
        assert memory_after_cleanup < memory_increase * 0.5, "Memory not properly freed after cleanup"

    @pytest.mark.asyncio
    async def test_configuration_validation_integration(self):
        """Test configuration validation in integration context"""
        # Test with various configuration scenarios
        
        # Valid configuration
        client = aiecs.create_simple_client()
        await client.initialize()
        assert client._initialized
        await client.close()
        
        # Configuration with custom settings
        custom_config = {
            'enable_cache': True,
            'cache_size': 100,
            'max_workers': 4
        }
        
        client = aiecs.create_aiecs_client(config=custom_config, mode="simple")
        await client.initialize()
        assert client._initialized
        await client.close()

    @pytest.mark.asyncio
    async def test_tool_system_integration_complete(self):
        """Test complete tool system integration"""
        client = aiecs.create_simple_client()
        await client.initialize()
        
        try:
            # Test tool discovery
            from aiecs.tools import list_tools, get_tool
            tools = list_tools()
            assert isinstance(tools, list)
            
            # Test that we can get tool information
            if tools:
                tool_name = tools[0].get('name')
                if tool_name:
                    tool_info = get_tool(tool_name)
                    assert tool_info is not None
            
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_error_propagation_and_logging(self):
        """Test error propagation and logging during startup"""
        import logging
        
        # Capture log messages
        log_messages = []
        
        class TestLogHandler(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())
        
        handler = TestLogHandler()
        logger = logging.getLogger('aiecs')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        try:
            client = aiecs.create_simple_client()
            await client.initialize()
            await client.close()
            
            # Should have some log messages
            assert len(log_messages) > 0
            
        finally:
            logger.removeHandler(handler)

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation when optional components fail"""
        # Mock some components to fail
        with patch('aiecs.infrastructure.monitoring.structured_logger.setup_structured_logging') as mock_logging:
            mock_logging.side_effect = Exception("Logging setup failed")
            
            # Should still be able to initialize
            client = aiecs.create_simple_client()
            await client.initialize()
            assert client._initialized
            await client.close()

    @pytest.mark.asyncio
    async def test_concurrent_operations_after_startup(self):
        """Test concurrent operations after startup"""
        client = aiecs.create_simple_client()
        await client.initialize()
        
        try:
            # Test concurrent tool operations
            from aiecs.tools import list_tools
            
            async def get_tools():
                return list_tools()
            
            # Run multiple concurrent operations
            results = await asyncio.gather(*[get_tools() for _ in range(5)])
            
            # All should succeed
            for result in results:
                assert isinstance(result, list)
                
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_resource_limits_and_constraints(self):
        """Test behavior under resource constraints"""
        # Test with limited resources
        limited_config = {
            'max_workers': 1,
            'cache_size': 10,
            'timeout': 5
        }
        
        client = aiecs.create_aiecs_client(config=limited_config, mode="simple")
        await client.initialize()
        
        try:
            # Should still work with limited resources
            assert client._initialized
            
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_startup_idempotency(self):
        """Test that startup operations are idempotent"""
        client = aiecs.create_simple_client()
        
        # Initialize multiple times
        await client.initialize()
        await client.initialize()  # Should not cause issues
        await client.initialize()  # Should not cause issues
        
        assert client._initialized
        
        await client.close()

    def test_version_and_metadata_consistency(self):
        """Test version and metadata consistency"""
        # Check that version information is consistent
        assert hasattr(aiecs, '__version__')
        assert isinstance(aiecs.__version__, str)
        assert len(aiecs.__version__) > 0
        
        # Check other metadata
        assert hasattr(aiecs, '__author__')
        assert hasattr(aiecs, '__email__')
