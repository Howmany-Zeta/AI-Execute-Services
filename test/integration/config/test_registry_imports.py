"""
Integration tests for service registry imports.

Tests cover:
- Import from aiecs.core.registry (new location)
- Backward compatibility import from aiecs.config
- No circular import at module level
- Service registration and retrieval workflow
"""

import pytest


class TestCoreRegistryImports:
    """Test imports from the new core.registry location."""

    def test_import_from_core_registry(self):
        """Test importing all registry functions from aiecs.core.registry."""
        from aiecs.core.registry import (
            AI_SERVICE_REGISTRY,
            register_ai_service,
            get_ai_service,
            list_registered_services,
            clear_registry,
        )

        # Verify all imports are callable/usable
        assert AI_SERVICE_REGISTRY is not None
        assert callable(register_ai_service)
        assert callable(get_ai_service)
        assert callable(list_registered_services)
        assert callable(clear_registry)

    def test_import_from_core_module(self):
        """Test importing from aiecs.core module."""
        from aiecs.core import (
            register_ai_service,
            get_ai_service,
            AI_SERVICE_REGISTRY,
        )

        assert callable(register_ai_service)
        assert callable(get_ai_service)
        assert AI_SERVICE_REGISTRY is not None


class TestBackwardCompatibility:
    """Test backward compatibility with old import paths."""

    def test_import_from_config(self):
        """Test importing registry functions from aiecs.config."""
        from aiecs.config import (
            register_ai_service,
            get_ai_service,
            AI_SERVICE_REGISTRY,
        )

        assert callable(register_ai_service)
        assert callable(get_ai_service)
        assert AI_SERVICE_REGISTRY is not None

    def test_import_new_utility_functions_from_config(self):
        """Test that new utility functions are also available from config."""
        from aiecs.config import (
            list_registered_services,
            clear_registry,
        )

        assert callable(list_registered_services)
        assert callable(clear_registry)

    def test_same_registry_from_both_paths(self):
        """Test that both import paths reference the same registry."""
        from aiecs.core.registry import (
            AI_SERVICE_REGISTRY as CORE_REGISTRY,
            clear_registry,
        )
        from aiecs.config import AI_SERVICE_REGISTRY as CONFIG_REGISTRY

        # Both should be the exact same object
        assert CORE_REGISTRY is CONFIG_REGISTRY

        # Clear and verify both are affected
        clear_registry()
        assert len(CORE_REGISTRY) == 0
        assert len(CONFIG_REGISTRY) == 0


class TestRegistryWorkflow:
    """Test full registration and retrieval workflow."""

    def setup_method(self):
        """Clear registry before each test."""
        from aiecs.core.registry import clear_registry

        clear_registry()

    def teardown_method(self):
        """Clear registry after each test."""
        from aiecs.core.registry import clear_registry

        clear_registry()

    def test_register_from_core_retrieve_from_config(self):
        """Test registering via core and retrieving via config."""
        from aiecs.core.registry import register_ai_service
        from aiecs.config import get_ai_service

        @register_ai_service("execute", "test_service")
        class TestService:
            name = "Test"

        # Retrieve from config path
        service_cls = get_ai_service("execute", "test_service")
        assert service_cls is TestService
        assert service_cls.name == "Test"

    def test_register_from_config_retrieve_from_core(self):
        """Test registering via config and retrieving via core."""
        from aiecs.config import register_ai_service
        from aiecs.core.registry import get_ai_service

        @register_ai_service("analyze", "analyzer")
        class AnalyzerService:
            mode = "analyze"

        # Retrieve from core path
        service_cls = get_ai_service("analyze", "analyzer")
        assert service_cls is AnalyzerService
        assert service_cls.mode == "analyze"

    def test_list_services_from_both_paths(self):
        """Test listing services shows same results from both paths."""
        from aiecs.core.registry import (
            register_ai_service,
            list_registered_services as core_list,
        )
        from aiecs.config import list_registered_services as config_list

        @register_ai_service("mode", "service")
        class Service:
            pass

        core_services = core_list()
        config_services = config_list()

        assert core_services == config_services
        assert ("mode", "service") in core_services

