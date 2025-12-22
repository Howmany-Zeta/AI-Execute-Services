"""
Unit tests for the service registry module.

Tests cover:
- Service registration via decorator
- Service retrieval
- Error handling for missing services
- list_registered_services() function
- clear_registry() function
- Registry isolation (zero dependencies)
"""

import pytest

# Import directly from the service_registry module to avoid full aiecs package
# initialization which may have dependencies not installed in test environment
from aiecs.core.registry.service_registry import (
    AI_SERVICE_REGISTRY,
    register_ai_service,
    get_ai_service,
    list_registered_services,
    clear_registry,
)


class TestRegisterAIService:
    """Test the register_ai_service decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        clear_registry()

    def teardown_method(self):
        """Clear registry after each test."""
        clear_registry()

    def test_register_service_basic(self):
        """Test basic service registration."""

        @register_ai_service("test_mode", "test_service")
        class TestService:
            pass

        assert ("test_mode", "test_service") in AI_SERVICE_REGISTRY
        assert AI_SERVICE_REGISTRY[("test_mode", "test_service")] is TestService

    def test_register_multiple_services(self):
        """Test registering multiple services."""

        @register_ai_service("mode1", "service1")
        class Service1:
            pass

        @register_ai_service("mode2", "service2")
        class Service2:
            pass

        assert len(AI_SERVICE_REGISTRY) == 2
        assert AI_SERVICE_REGISTRY[("mode1", "service1")] is Service1
        assert AI_SERVICE_REGISTRY[("mode2", "service2")] is Service2

    def test_register_decorator_returns_class(self):
        """Test that decorator returns the original class."""

        @register_ai_service("mode", "service")
        class OriginalClass:
            value = 42

        assert OriginalClass.value == 42

    def test_register_same_key_overwrites(self):
        """Test that registering same key overwrites previous entry."""

        @register_ai_service("mode", "service")
        class FirstClass:
            pass

        @register_ai_service("mode", "service")
        class SecondClass:
            pass

        assert AI_SERVICE_REGISTRY[("mode", "service")] is SecondClass


class TestGetAIService:
    """Test the get_ai_service function."""

    def setup_method(self):
        """Clear registry and register test service before each test."""
        clear_registry()

        @register_ai_service("execute", "openai")
        class OpenAIExecuteService:
            name = "OpenAI"

        self.test_service = OpenAIExecuteService

    def teardown_method(self):
        """Clear registry after each test."""
        clear_registry()

    def test_get_registered_service(self):
        """Test retrieving a registered service."""
        result = get_ai_service("execute", "openai")
        assert result is self.test_service

    def test_get_nonexistent_service_raises_error(self):
        """Test that getting nonexistent service raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            get_ai_service("nonexistent", "service")

        assert "No registered service" in str(excinfo.value)
        assert "nonexistent" in str(excinfo.value)
        assert "service" in str(excinfo.value)

    def test_error_message_includes_available_services(self):
        """Test that error message lists available services."""
        with pytest.raises(ValueError) as excinfo:
            get_ai_service("bad", "key")

        error_msg = str(excinfo.value)
        assert "Available services" in error_msg
        assert "('execute', 'openai')" in error_msg


class TestListRegisteredServices:
    """Test the list_registered_services function."""

    def setup_method(self):
        """Clear registry before each test."""
        clear_registry()

    def teardown_method(self):
        """Clear registry after each test."""
        clear_registry()

    def test_list_empty_registry(self):
        """Test listing services when registry is empty."""
        services = list_registered_services()
        assert services == {}

    def test_list_returns_copy(self):
        """Test that list_registered_services returns a copy."""

        @register_ai_service("mode", "service")
        class TestService:
            pass

        services = list_registered_services()
        services[("new", "key")] = object

        # Original registry should be unchanged
        assert ("new", "key") not in AI_SERVICE_REGISTRY


class TestClearRegistry:
    """Test the clear_registry function."""

    def teardown_method(self):
        """Clear registry after each test."""
        clear_registry()

    def test_clear_removes_all_services(self):
        """Test that clear_registry removes all registered services."""

        @register_ai_service("mode1", "service1")
        class Service1:
            pass

        @register_ai_service("mode2", "service2")
        class Service2:
            pass

        assert len(AI_SERVICE_REGISTRY) == 2

        clear_registry()

        assert len(AI_SERVICE_REGISTRY) == 0

