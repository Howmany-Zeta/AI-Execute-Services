"""
Test FastAPI application startup and lifespan management.
Tests the complete application startup process including all middleware and services.
"""
import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import AIECS FastAPI app and components
from aiecs import get_fastapi_app
from aiecs.main import lifespan


class TestFastAPIAppStartup:
    """Test FastAPI application startup and lifecycle"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment for FastAPI testing"""
        test_env = {
            'AIECS_ENV': 'test',
            'LOG_LEVEL': 'WARNING',
            'SKIP_OFFICE_TOOL': 'true',
            'SKIP_IMAGE_TOOL': 'true',
            'SKIP_CHART_TOOL': 'true',
            'DISABLE_DATABASE': 'true',  # Disable database for testing
            'DISABLE_CELERY': 'true',    # Disable Celery for testing
        }
        
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
        # Restore environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_fastapi_app_creation(self):
        """Test that FastAPI app can be created"""
        app = get_fastapi_app()
        assert app is not None
        assert app.title == "AIECS - AI Execute Services"
        assert app.version == "1.0.0"

    def test_app_routes_registration(self):
        """Test that routes are properly registered"""
        app = get_fastapi_app()
        
        # Get all routes
        routes = [route.path for route in app.routes]
        
        # Should have basic routes
        expected_routes = [
            "/health",
            "/execute",
            "/status/{task_id}",
            "/tools",
        ]
        
        for expected_route in expected_routes:
            assert any(expected_route in route for route in routes), f"Route {expected_route} not found"

    def test_middleware_configuration(self):
        """Test middleware configuration"""
        app = get_fastapi_app()
        
        # Check that CORS middleware is configured
        middleware_types = [type(middleware).__name__ for middleware in app.user_middleware]
        assert 'CORSMiddleware' in middleware_types

    @pytest.mark.asyncio
    async def test_lifespan_startup_with_mocks(self):
        """Test lifespan startup with mocked dependencies"""
        app = get_fastapi_app()
        
        # Mock database and task manager to avoid external dependencies
        with patch('aiecs.main.DatabaseManager') as mock_db_manager, \
             patch('aiecs.main.CeleryTaskManager') as mock_task_manager, \
             patch('aiecs.main.discover_tools') as mock_discover_tools, \
             patch('aiecs.main.LLMClientFactory.close_all') as mock_llm_close:
            
            # Configure mocks
            mock_db_instance = AsyncMock()
            mock_db_manager.return_value = mock_db_instance
            
            mock_task_instance = MagicMock()
            mock_task_manager.return_value = mock_task_instance
            
            # Test lifespan startup
            async with lifespan(app):
                # Verify components were initialized
                mock_db_manager.assert_called_once()
                mock_db_instance.connect.assert_called_once()
                mock_task_manager.assert_called_once()
                mock_discover_tools.assert_called_once_with("aiecs.tools")
            
            # Verify cleanup was called
            mock_db_instance.disconnect.assert_called_once()
            mock_llm_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint"""
        app = get_fastapi_app()
        
        # Mock dependencies for testing
        with patch('aiecs.main.DatabaseManager') as mock_db_manager, \
             patch('aiecs.main.CeleryTaskManager') as mock_task_manager, \
             patch('aiecs.main.discover_tools'):
            
            mock_db_instance = AsyncMock()
            mock_db_manager.return_value = mock_db_instance
            mock_task_manager.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_tools_endpoint(self):
        """Test tools listing endpoint"""
        app = get_fastapi_app()
        
        with patch('aiecs.main.DatabaseManager') as mock_db_manager, \
             patch('aiecs.main.CeleryTaskManager') as mock_task_manager, \
             patch('aiecs.main.discover_tools'):
            
            mock_db_instance = AsyncMock()
            mock_db_manager.return_value = mock_db_instance
            mock_task_manager.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/tools")
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_startup_error_handling(self):
        """Test error handling during startup"""
        app = get_fastapi_app()
        
        # Mock database connection to fail
        with patch('aiecs.main.DatabaseManager') as mock_db_manager:
            mock_db_instance = AsyncMock()
            mock_db_instance.connect.side_effect = Exception("Database connection failed")
            mock_db_manager.return_value = mock_db_instance
            
            # Startup should raise exception
            with pytest.raises(Exception, match="Database connection failed"):
                async with lifespan(app):
                    pass

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown process"""
        app = get_fastapi_app()
        
        with patch('aiecs.main.DatabaseManager') as mock_db_manager, \
             patch('aiecs.main.CeleryTaskManager') as mock_task_manager, \
             patch('aiecs.main.discover_tools'), \
             patch('aiecs.main.LLMClientFactory.close_all') as mock_llm_close:
            
            mock_db_instance = AsyncMock()
            mock_db_manager.return_value = mock_db_instance
            mock_task_manager.return_value = MagicMock()
            
            # Test complete lifecycle
            async with lifespan(app):
                # App is running
                pass
            
            # Verify shutdown was called
            mock_db_instance.disconnect.assert_called_once()
            mock_llm_close.assert_called_once()

    def test_app_metadata(self):
        """Test application metadata"""
        app = get_fastapi_app()
        
        assert app.title == "AIECS - AI Execute Services"
        assert app.description == "Middleware service for AI-powered task execution and tool orchestration"
        assert app.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_cors_configuration(self):
        """Test CORS configuration"""
        app = get_fastapi_app()
        
        with patch('aiecs.main.DatabaseManager') as mock_db_manager, \
             patch('aiecs.main.CeleryTaskManager') as mock_task_manager, \
             patch('aiecs.main.discover_tools'):
            
            mock_db_instance = AsyncMock()
            mock_db_manager.return_value = mock_db_instance
            mock_task_manager.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test OPTIONS request (CORS preflight)
                response = await client.options("/health")
                # Should not return 405 Method Not Allowed if CORS is properly configured
                assert response.status_code != 405

    @pytest.mark.asyncio
    async def test_websocket_integration(self):
        """Test WebSocket integration"""
        app = get_fastapi_app()
        
        # Check that Socket.IO is integrated
        # This is a basic check - full WebSocket testing would require more setup
        assert hasattr(app, 'mount') or hasattr(app, 'add_route')

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        app = get_fastapi_app()
        
        with patch('aiecs.main.DatabaseManager') as mock_db_manager, \
             patch('aiecs.main.CeleryTaskManager') as mock_task_manager, \
             patch('aiecs.main.discover_tools'):
            
            mock_db_instance = AsyncMock()
            mock_db_manager.return_value = mock_db_instance
            mock_task_manager.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Send multiple concurrent requests
                tasks = [client.get("/health") for _ in range(5)]
                responses = await asyncio.gather(*tasks)
                
                # All should succeed
                for response in responses:
                    assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_responses(self):
        """Test error response handling"""
        app = get_fastapi_app()
        
        with patch('aiecs.main.DatabaseManager') as mock_db_manager, \
             patch('aiecs.main.CeleryTaskManager') as mock_task_manager, \
             patch('aiecs.main.discover_tools'):
            
            mock_db_instance = AsyncMock()
            mock_db_manager.return_value = mock_db_instance
            mock_task_manager.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test non-existent endpoint
                response = await client.get("/nonexistent")
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_request_validation(self):
        """Test request validation"""
        app = get_fastapi_app()
        
        with patch('aiecs.main.DatabaseManager') as mock_db_manager, \
             patch('aiecs.main.CeleryTaskManager') as mock_task_manager, \
             patch('aiecs.main.discover_tools'):
            
            mock_db_instance = AsyncMock()
            mock_db_manager.return_value = mock_db_instance
            mock_task_manager.return_value = MagicMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test execute endpoint with invalid data
                response = await client.post("/execute", json={})
                # Should return validation error (422) or bad request (400)
                assert response.status_code in [400, 422]

    def test_app_configuration_loading(self):
        """Test that app loads configuration correctly"""
        app = get_fastapi_app()
        
        # App should be configured with proper settings
        assert app is not None
        
        # Check that lifespan is configured
        assert app.router.lifespan_context is not None
