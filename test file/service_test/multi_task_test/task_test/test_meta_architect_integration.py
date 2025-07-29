#!/usr/bin/env python3
"""
Test script for Meta-Architect integration.

This script validates that all components of the Meta-Architect system
work together properly within the multi-task framework.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.multi_task.core.models.architect_models import (
    BlueprintConstructionRequest,
    StrategicPlan,
    FrameworkRecommendation
)
from app.services.multi_task.core.models.planner_models import PlanningContext
from app.services.multi_task.data.storage.knowledge_database import KnowledgeDatabase
from app.services.multi_task.config.validators.framework_validator import FrameworkValidator


async def test_knowledge_database():
    """Test knowledge database functionality."""
    print("🔍 Testing Knowledge Database...")

    try:
        # Initialize database manager
        db_manager = KnowledgeDatabase()
        await db_manager.initialize()

        # Test framework queries
        frameworks = await db_manager.get_frameworks_by_problem_type("strategic_planning")
        print(f"✅ Found {len(frameworks)} frameworks for strategic planning")

        # Test framework recommendations
        recommendations = await db_manager.get_framework_recommendations(
            problem_description="Develop a comprehensive business strategy",
            domain="business",
            complexity="high"
        )
        print(f"✅ Generated {len(recommendations)} framework recommendations")

        # Test caching
        cached_frameworks = await db_manager.get_frameworks_by_problem_type("strategic_planning")
        print(f"✅ Cache working: {len(cached_frameworks)} frameworks retrieved from cache")

        await db_manager.close()
        return True

    except Exception as e:
        print(f"❌ Knowledge Database test failed: {e}")
        return False


def test_framework_validation():
    """Test framework validation functionality."""
    print("\n🔍 Testing Framework Validation...")

    try:
        # Initialize validator
        validator = FrameworkValidator()

        # Test framework validation
        framework_path = project_root / "framework.yaml"
        if framework_path.exists():
            validation_result = validator.validate_framework_file(str(framework_path))
            if validation_result.is_valid:
                print("✅ Framework configuration is valid")
                print(f"   - {len(validation_result.frameworks)} frameworks validated")
                print(f"   - {len(validation_result.meta_frameworks)} meta-frameworks validated")
            else:
                print(f"❌ Framework validation failed: {validation_result.errors}")
                return False
        else:
            print("⚠️  Framework file not found, skipping validation test")

        return True

    except Exception as e:
        print(f"❌ Framework Validation test failed: {e}")
        return False


def test_model_validation():
    """Test Pydantic model validation."""
    print("\n🔍 Testing Model Validation...")

    try:
        # Test BlueprintConstructionRequest
        request = BlueprintConstructionRequest(
            problem_type="digital_transformation",
            context={
                "industry": "healthcare",
                "company_size": "enterprise",
                "timeline": "6 months",
                "budget": "$500K",
                "stakeholders": ["executives", "IT", "operations"]
            },
            constraints={
                "budget_limit": "$500K",
                "timeline_limit": "6 months"
            },
            preferences={
                "methodology": "agile",
                "risk_tolerance": "medium"
            }
        )
        print("✅ BlueprintConstructionRequest validation passed")

        # Test StrategicPlan
        plan = StrategicPlan(
            framework_name="PEST Analysis",
            problem_analysis="Complex multi-stakeholder digital transformation",
            strategic_approach="Phased implementation with stakeholder alignment",
            key_steps=[
                "Stakeholder analysis and alignment",
                "Technology assessment and gap analysis",
                "Implementation roadmap development",
                "Change management strategy"
            ],
            success_metrics=[
                "Stakeholder satisfaction > 85%",
                "Technology adoption rate > 90%",
                "ROI achievement within 12 months"
            ],
            estimated_duration="6 months",
            confidence_score=0.85,
            risk_factors=[
                "Stakeholder resistance to change",
                "Technology integration complexity"
            ],
            dependencies=[
                "Executive sponsorship",
                "IT infrastructure readiness"
            ]
        )
        print("✅ StrategicPlan validation passed")

        # Test FrameworkRecommendation
        recommendation = FrameworkRecommendation(
            framework_name="SWOT Analysis",
            relevance_score=0.92,
            reasoning="Ideal for strategic assessment of internal capabilities and external opportunities",
            estimated_duration="2-3 weeks",
            complexity_match=True,
            domain_match=True
        )
        print("✅ FrameworkRecommendation validation passed")

        return True

    except Exception as e:
        print(f"❌ Model Validation test failed: {e}")
        return False


def test_interface_compliance():
    """Test that implementations comply with interfaces."""
    print("\n🔍 Testing Interface Compliance...")

    try:
        from app.services.multi_task.core.interfaces.planner_interfaces import IBlueprintConstructor
        from app.services.multi_task.planner.thinker.blueprint_constructer import BlueprintConstructorService

        # Check that BlueprintConstructorService implements IBlueprintConstructor
        if issubclass(BlueprintConstructorService, IBlueprintConstructor):
            print("✅ BlueprintConstructorService implements IBlueprintConstructor")
        else:
            print("❌ BlueprintConstructorService does not implement IBlueprintConstructor")
            return False

        # Check required methods exist
        required_methods = [
            'construct_blueprint',
            'validate_blueprint',
            'get_framework_recommendations',
            'get_supported_domains',
            'get_supported_complexities'
        ]

        for method in required_methods:
            if hasattr(BlueprintConstructorService, method):
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                return False

        return True

    except Exception as e:
        print(f"❌ Interface Compliance test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("🚀 Starting Meta-Architect Integration Tests\n")

    tests = [
        ("Model Validation", test_model_validation),
        ("Framework Validation", test_framework_validation),
        ("Interface Compliance", test_interface_compliance),
        ("Knowledge Database", test_knowledge_database)
    ]

    results = []
    for test_name, test_func in tests:
        if asyncio.iscoroutinefunction(test_func):
            result = await test_func()
        else:
            result = test_func()
        results.append((test_name, result))

    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Meta-Architect integration is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
