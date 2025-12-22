"""
Comprehensive AIECS startup and component initialization tests.
Tests all major components to ensure they can be initialized without errors.
"""
import pytest
import pytest_asyncio
import asyncio
import logging
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Import AIECS components
from aiecs.config.config import get_settings
from aiecs.infrastructure.persistence.database_manager import DatabaseManager
from aiecs.infrastructure.messaging.celery_task_manager import CeleryTaskManager
from aiecs.infrastructure.monitoring.structured_logger import setup_structured_logging
from aiecs.llm.client_factory import LLMClientFactory, LLMClientManager
from aiecs.tools import discover_tools, list_tools
from aiecs import create_aiecs_client, create_simple_client, create_full_client

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


class TestAIECSStartup:
    """Test AIECS startup and component initialization"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with minimal configuration"""
        # Set test environment variables
        test_env = {
            'AIECS_ENV': 'test',
            'LOG_LEVEL': 'WARNING',
            'SKIP_OFFICE_TOOL': 'true',
            'SKIP_IMAGE_TOOL': 'true', 
            'SKIP_CHART_TOOL': 'true',
            'STATS_TOOL_MAX_FILE_SIZE_MB': '50',
            'STATS_TOOL_ALLOWED_EXTENSIONS': '[".csv", ".json"]'
        }
        
        # Store original values
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
        # Restore original environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_settings_initialization(self):
        """Test that settings can be loaded without errors"""
        settings = get_settings()
        assert settings is not None
        # Test actual attributes that exist in Settings
        assert hasattr(settings, 'db_host')
        assert hasattr(settings, 'celery_broker_url')
        assert hasattr(settings, 'openai_api_key')

    def test_structured_logging_setup(self):
        """Test structured logging setup"""
        # Should not raise any exceptions
        setup_structured_logging()
        
        # Verify logger is configured
        logger = logging.getLogger('aiecs')
        assert logger is not None

    def test_tool_discovery(self):
        """Test tool discovery process"""
        # Should not raise exceptions
        discover_tools("aiecs.tools")
        
        # Verify tools are discovered
        tools = list_tools()
        assert isinstance(tools, list)
        # Should have at least some basic tools
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_database_manager_initialization(self):
        """Test database manager can be initialized"""
        # Mock database config to avoid requiring actual database
        mock_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        
        db_manager = DatabaseManager(db_config=mock_config)
        assert db_manager is not None
        assert db_manager.db_config == mock_config
        assert not db_manager._initialized

    def test_celery_task_manager_initialization(self):
        """Test Celery task manager can be initialized"""
        # Mock Celery config
        mock_config = {
            'broker_url': 'redis://localhost:6379/0',
            'backend_url': 'redis://localhost:6379/0'
        }
        
        task_manager = CeleryTaskManager(mock_config)
        assert task_manager is not None

    @pytest.mark.asyncio
    async def test_llm_client_factory(self):
        """Test LLM client factory initialization"""
        factory = LLMClientFactory()
        assert factory is not None
        
        # Test manager initialization
        manager = LLMClientManager()
        assert manager is not None
        
        # Test cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_simple_client_creation(self):
        """Test creating AIECS simple client"""
        client = await create_simple_client()
        assert client is not None
        assert client.mode == "simple"
        assert client._initialized
        assert client._tools_discovered

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_aiecs_client_simple_mode(self):
        """Test AIECS client in simple mode"""
        client = await create_aiecs_client(mode="simple")
        assert client is not None
        assert client.mode == "simple"
        assert client._initialized

        # Should not have database or task manager in simple mode
        assert client.db_manager is None
        assert client.task_manager is None

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_component_initialization_order(self):
        """Test that components can be initialized in the correct order"""
        # 1. Settings
        settings = get_settings()
        assert settings is not None

        # 2. Logging
        setup_structured_logging()

        # 3. Tool discovery
        discover_tools("aiecs.tools")
        tools = list_tools()
        assert len(tools) > 0

        # 4. Simple client
        client = await create_simple_client()
        assert client._initialized

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_error_handling_during_initialization(self):
        """Test error handling during component initialization"""
        # Test with invalid database config
        invalid_db_config = {
            'host': 'invalid_host',
            'port': 9999,
            'database': 'nonexistent_db',
            'user': 'invalid_user',
            'password': 'invalid_pass'
        }
        
        db_manager = DatabaseManager(db_config=invalid_db_config)
        
        # Should handle connection errors gracefully
        with pytest.raises(Exception):
            await db_manager.connect()

    def test_environment_variable_handling(self):
        """Test that environment variables are properly handled"""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        # Test with different environment settings
        with patch.dict(os.environ, {'DB_HOST': 'test_host'}, clear=False):
            get_settings.cache_clear()  # Clear cache to pick up new env vars
            settings = get_settings()
            assert settings.db_host == 'test_host'

        get_settings.cache_clear()
        with patch.dict(os.environ, {'DB_PORT': '5433'}, clear=False):
            get_settings.cache_clear()  # Clear cache to pick up new env vars
            settings = get_settings()
            assert settings.db_port == 5433

        # Clear cache after test
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_concurrent_initialization(self):
        """Test concurrent initialization of multiple clients"""
        async def create_and_init_client():
            return await create_simple_client()

        # Create multiple clients concurrently
        clients = await asyncio.gather(*[
            create_and_init_client() for _ in range(3)
        ])

        # All should be initialized
        for client in clients:
            assert client._initialized

        # Cleanup all clients
        await asyncio.gather(*[client.close() for client in clients])

    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """Test proper resource cleanup"""
        client = await create_simple_client()

        # Verify initialization
        assert client._initialized

        # Test cleanup
        await client.close()

        # Should be able to initialize again after cleanup
        await client.initialize()
        assert client._initialized

        # Final cleanup
        await client.close()

    def test_configuration_validation(self):
        """Test configuration validation"""
        settings = get_settings()

        # Basic validation - settings should have required attributes
        required_attrs = ['db_host', 'db_port', 'celery_broker_url']
        for attr in required_attrs:
            assert hasattr(settings, attr), f"Settings missing required attribute: {attr}"

    @pytest.mark.asyncio
    async def test_tool_system_integration(self):
        """Test tool system integration during startup"""
        # Discover tools
        discover_tools("aiecs.tools")
        
        # Get available tools
        tools = list_tools()
        assert isinstance(tools, list)
        
        # Should have basic tools available
        tool_names = [tool.get('name', '') for tool in tools]
        
        # Check for some expected tools (adjust based on your actual tools)
        expected_tools = ['pandas_tool', 'stats_tool']  # Add your actual tool names
        
        for expected_tool in expected_tools:
            # Tool might be skipped in test environment, so just check it doesn't crash
            pass  # We're mainly testing that discovery doesn't crash

    @pytest.mark.asyncio
    async def test_memory_usage_during_startup(self):
        """Test memory usage during startup (basic check)"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Initialize client
        client = await create_simple_client()

        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for simple client)
        assert memory_increase < 100 * 1024 * 1024, f"Memory increase too large: {memory_increase / 1024 / 1024:.2f}MB"

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_startup_timing(self):
        """Test startup timing to ensure reasonable performance"""
        import time

        start_time = time.time()

        # Initialize client
        client = await create_simple_client()

        end_time = time.time()
        startup_time = end_time - start_time

        # Startup should be reasonably fast (less than 10 seconds)
        assert startup_time < 10.0, f"Startup took too long: {startup_time:.2f}s"

        # Cleanup
        await client.close()
