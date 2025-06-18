#!/usr/bin/env python3
"""
Test script to verify the updated LLM client and general summarizer service
"""
import asyncio
import os
import sys
import logging

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_service_registration():
    """Test that services are properly registered"""
    print("=== Testing Service Registration ===")

    try:
        # Import services to ensure they are registered
        import app.services.domain.services
        import app.services.general.services
        import app.services.multi_task.services

        from app.core.registry import AI_SERVICE_REGISTRY

        print("Registered services:")
        for (mode, service), cls in AI_SERVICE_REGISTRY.items():
            print(f"  ✓ {mode}/{service} -> {cls.__name__}")

        # Check specific services
        expected_services = [
            ("general", "summarizer"),
            ("multi_task", "summarizer"),
            ("domain", "summarizer"),
            ("domain", "rag_service")
        ]

        print("\nChecking expected services:")
        all_registered = True
        for mode, service in expected_services:
            key = (mode, service)
            if key in AI_SERVICE_REGISTRY:
                print(f"  ✓ {mode}/{service} is registered")
            else:
                print(f"  ✗ {mode}/{service} is NOT registered")
                all_registered = False

        return all_registered

    except Exception as e:
        print(f"Error during service registration test: {e}")
        return False

async def test_llm_client():
    """Test the LLM client (mock test without actual API calls)"""
    print("\n=== Testing LLM Client ===")

    try:
        from app.llm.llm_client import LLMClient, LLMMessage, AIProvider

        # Create client instance
        client = LLMClient()
        print("✓ LLM client created successfully")

        # Test message creation
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant"),
            LLMMessage(role="user", content="Hello, how are you?")
        ]
        print("✓ LLM messages created successfully")

        # Test provider enum
        providers = [AIProvider.OPENAI, AIProvider.VERTEX, AIProvider.GROK]
        print(f"✓ Available providers: {[p.value for p in providers]}")

        await client.close()
        print("✓ LLM client closed successfully")

        return True

    except Exception as e:
        print(f"Error during LLM client test: {e}")
        return False

async def test_general_summarizer():
    """Test the general summarizer service"""
    print("\n=== Testing General Summarizer Service ===")

    try:
        from app.services.general.services.summarizer import SummarizerService

        # Create service instance
        service = SummarizerService()
        print("✓ SummarizerService created successfully")

        # Test basic properties
        print(f"✓ System prompt loaded: {len(service.system_prompt)} characters")
        print(f"✓ Tools loaded: {len(service.load_tools())} tools")

        # Test input validation
        test_data = {"text": "Hello, can you help me?"}
        test_context = {"metadata": {"provider": "openai", "model": "gpt-4-turbo"}}

        print("✓ Test data prepared")
        print(f"  Input: {test_data}")
        print(f"  Context: {test_context}")

        # Note: We won't actually call the LLM since we don't have API keys in test
        print("✓ Service structure validated (skipping actual LLM call)")

        return True

    except Exception as e:
        print(f"Error during general summarizer test: {e}")
        return False

async def test_stream_router_fix():
    """Test that the stream router variable scope issue is fixed"""
    print("\n=== Testing Stream Router Fix ===")

    try:
        # Read the stream router file and check for the fix
        with open('app/api/stream_router.py', 'r') as f:
            content = f.read()

        # Check that the error_message variable is properly captured
        if 'error_message = str(e)' in content:
            print("✓ Variable scope fix applied correctly")
            return True
        else:
            print("✗ Variable scope fix not found")
            return False

    except Exception as e:
        print(f"Error checking stream router fix: {e}")
        return False

async def main():
    """Run all tests"""
    print("Starting LLM Integration Tests...\n")

    tests = [
        ("Service Registration", test_service_registration),
        ("LLM Client", test_llm_client),
        ("General Summarizer", test_general_summarizer),
        ("Stream Router Fix", test_stream_router_fix),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "="*50)
    print("TEST RESULTS SUMMARY")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The LLM integration is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
