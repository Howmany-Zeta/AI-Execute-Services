#!/usr/bin/env python3
"""
Test script to verify service registration
"""

# Import services to ensure they are registered
import app.services.scholar.services
import app.services.general.services
import app.services.multi_task.services

from app.config.registry import AI_SERVICE_REGISTRY

def test_service_registration():
    """Test that all expected services are registered"""
    print("Registered services:")
    for (mode, service), cls in AI_SERVICE_REGISTRY.items():
        print(f"  {mode}/{service} -> {cls.__name__}")

    # Check specific services
    expected_services = [
        ("general", "summarizer"),
        ("multi_task", "summarizer"),
        ("domain", "summarizer"),
        ("domain", "rag_service")
    ]

    print("\nChecking expected services:")
    for mode, service in expected_services:
        key = (mode, service)
        if key in AI_SERVICE_REGISTRY:
            print(f"  ✓ {mode}/{service} is registered")
        else:
            print(f"  ✗ {mode}/{service} is NOT registered")

if __name__ == "__main__":
    test_service_registration()
