"""
E2E Test Base Classes and Utilities

Provides base classes and helper functions for E2E tests.
"""

import asyncio
import time
from typing import Dict, Any, Optional
import pytest


class E2ETestBase:
    """Base class for E2E tests with common utilities."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.start_time = time.time()
    
    def teardown_method(self):
        """Teardown for each test method."""
        elapsed = time.time() - self.start_time
        print(f"\n⏱️  Test completed in {elapsed:.2f} seconds")
    
    def assert_valid_response(self, response: Any, expected_type: type = str):
        """Assert that a response is valid."""
        assert response is not None, "Response should not be None"
        assert isinstance(response, expected_type), f"Response should be {expected_type}"
        if isinstance(response, str):
            assert len(response) > 0, "Response should not be empty"
    
    def assert_response_contains(self, response: str, *keywords: str):
        """Assert that response contains keywords."""
        response_lower = response.lower()
        for keyword in keywords:
            assert keyword.lower() in response_lower, \
                f"Response should contain '{keyword}'"
    
    def measure_latency(self, func, *args, **kwargs):
        """Measure function execution latency."""
        start = time.time()
        result = func(*args, **kwargs)
        latency = time.time() - start
        return result, latency
    
    async def measure_latency_async(self, func, *args, **kwargs):
        """Measure async function execution latency."""
        start = time.time()
        result = await func(*args, **kwargs)
        latency = time.time() - start
        return result, latency


class LLMTestMixin:
    """Mixin for LLM-specific test utilities."""
    
    def get_minimal_prompt(self) -> str:
        """Get minimal prompt to reduce token usage."""
        return "Say 'OK' if you understand."
    
    def get_test_messages(self) -> list:
        """Get minimal chat messages for testing."""
        return [
            {"role": "user", "content": "Reply with just 'OK'"}
        ]
    
    def assert_llm_response_valid(self, response: str):
        """Assert LLM response is valid."""
        assert response is not None, "LLM response should not be None"
        assert isinstance(response, str), "LLM response should be a string"
        assert len(response) > 0, "LLM response should not be empty"
        # Check for common error patterns
        assert "error" not in response.lower() or "no error" in response.lower(), \
            f"LLM response contains error: {response}"
    
    def calculate_token_cost(self, prompt_tokens: int, completion_tokens: int,
                            model: str) -> float:
        """Calculate approximate cost for API call."""
        # Approximate costs per 1K tokens (as of 2024)
        costs = {
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gemini-pro": {"prompt": 0.000125, "completion": 0.000375},
            "grok-1": {"prompt": 0.001, "completion": 0.002},
        }
        
        model_cost = costs.get(model, {"prompt": 0.001, "completion": 0.002})
        prompt_cost = (prompt_tokens / 1000) * model_cost["prompt"]
        completion_cost = (completion_tokens / 1000) * model_cost["completion"]
        
        return prompt_cost + completion_cost


class ToolTestMixin:
    """Mixin for tool-specific test utilities."""
    
    def assert_tool_result_valid(self, result: Dict[str, Any]):
        """Assert tool result is valid."""
        assert result is not None, "Tool result should not be None"
        assert isinstance(result, dict), "Tool result should be a dictionary"
        assert "error" not in result or result.get("success", False), \
            f"Tool returned error: {result.get('error')}"
    
    def assert_search_results_valid(self, results: list):
        """Assert search results are valid."""
        assert results is not None, "Search results should not be None"
        assert isinstance(results, list), "Search results should be a list"
        assert len(results) > 0, "Search results should not be empty"
        
        # Check first result structure
        if results:
            result = results[0]
            assert isinstance(result, dict), "Each result should be a dictionary"


class E2ELLMTestBase(E2ETestBase, LLMTestMixin):
    """Base class for LLM E2E tests."""
    
    def setup_method(self):
        """Setup for LLM tests."""
        super().setup_method()
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def teardown_method(self):
        """Teardown for LLM tests."""
        print(f"\n💰 Total tokens used: {self.total_tokens}")
        print(f"💵 Estimated cost: ${self.total_cost:.6f}")
        super().teardown_method()
    
    def record_usage(self, prompt_tokens: int, completion_tokens: int,
                    model: str, cost_tracker=None):
        """Record token usage and cost."""
        total = prompt_tokens + completion_tokens
        cost = self.calculate_token_cost(prompt_tokens, completion_tokens, model)
        
        self.total_tokens += total
        self.total_cost += cost
        
        if cost_tracker:
            cost_tracker.record_call(
                provider=model.split('-')[0],
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost
            )


class E2EToolTestBase(E2ETestBase, ToolTestMixin):
    """Base class for tool E2E tests."""
    
    def setup_method(self):
        """Setup for tool tests."""
        super().setup_method()
        self.api_calls = 0
    
    def teardown_method(self):
        """Teardown for tool tests."""
        print(f"\n📞 Total API calls: {self.api_calls}")
        super().teardown_method()
    
    def record_api_call(self):
        """Record an API call."""
        self.api_calls += 1


# Utility functions

def skip_if_no_api_key(key_name: str):
    """Decorator to skip test if API key is missing."""
    def decorator(func):
        return pytest.mark.skipif(
            not os.getenv(key_name),
            reason=f"{key_name} not set in environment"
        )(func)
    return decorator


def requires_api_key(*key_names: str):
    """Decorator to mark test as requiring API keys."""
    def decorator(func):
        # Add requires_api marker
        func = pytest.mark.requires_api(func)
        
        # Add skip conditions for each key
        for key_name in key_names:
            if not os.getenv(key_name):
                func = pytest.mark.skip(
                    reason=f"{key_name} not set in environment"
                )(func)
        
        return func
    return decorator


async def retry_on_rate_limit(func, max_retries: int = 3, backoff: float = 1.0):
    """Retry function on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = backoff * (2 ** attempt)
                    print(f"⏳ Rate limited, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            else:
                raise
    
    raise RuntimeError("Max retries exceeded")


def log_test_info(test_name: str, **kwargs):
    """Log test information."""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    for key, value in kwargs.items():
        print(f"{key}: {value}")
    print('='*60)
