"""
E2E Tests for OpenAI LLM Integration

Tests real OpenAI API calls with minimal token usage.
"""

import pytest
import os
from test.e2e.base import E2ELLMTestBase, log_test_info


@pytest.mark.e2e
@pytest.mark.openai
@pytest.mark.requires_api
class TestOpenAIE2E(E2ELLMTestBase):
    """E2E tests for OpenAI API."""
    
    @pytest.fixture(autouse=True)
    def setup(self, openai_api_key, cost_tracker):
        """Setup OpenAI client."""
        self.api_key = openai_api_key
        self.cost_tracker = cost_tracker
        self.model = "gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_openai_basic_completion(self):
        """Test basic OpenAI completion with minimal prompt."""
        log_test_info(
            "OpenAI Basic Completion",
            model=self.model,
            prompt="Minimal test prompt"
        )
        
        try:
            from aiecs.llm.clients.openai_client import OpenAIClient
            
            client = OpenAIClient(api_key=self.api_key)
            prompt = self.get_minimal_prompt()
            
            response, latency = await self.measure_latency_async(
                client.agenerate,
                prompt=prompt,
                model=self.model,
                max_tokens=10  # Minimal tokens
            )
            
            # Assertions
            self.assert_llm_response_valid(response)
            assert latency < 10.0, f"Response took {latency:.2f}s (should be < 10s)"
            
            # Record usage (approximate)
            prompt_tokens = len(prompt.split())
            completion_tokens = len(response.split())
            self.record_usage(prompt_tokens, completion_tokens, self.model, self.cost_tracker)
            
            print(f"\n✅ OpenAI response received in {latency:.2f}s")
            print(f"📝 Response: {response[:100]}...")
            
        except ImportError:
            pytest.skip("OpenAI client not available")
        except Exception as e:
            pytest.fail(f"OpenAI API call failed: {e}")
    
    @pytest.mark.asyncio
    async def test_openai_chat_completion(self):
        """Test OpenAI chat completion with minimal messages."""
        log_test_info(
            "OpenAI Chat Completion",
            model=self.model,
            message_count=1
        )
        
        try:
            from aiecs.llm.clients.openai_client import OpenAIClient
            
            client = OpenAIClient(api_key=self.api_key)
            messages = self.get_test_messages()
            
            response, latency = await self.measure_latency_async(
                client.achat,
                messages=messages,
                model=self.model,
                max_tokens=5  # Minimal tokens
            )
            
            # Extract response text
            response_text = response if isinstance(response, str) else str(response)
            
            # Assertions
            self.assert_llm_response_valid(response_text)
            assert latency < 10.0, f"Chat took {latency:.2f}s (should be < 10s)"
            
            # Record usage
            prompt_tokens = sum(len(m.get("content", "").split()) for m in messages)
            completion_tokens = len(response_text.split())
            self.record_usage(prompt_tokens, completion_tokens, self.model, self.cost_tracker)
            
            print(f"\n✅ OpenAI chat response in {latency:.2f}s")
            
        except ImportError:
            pytest.skip("OpenAI client not available")
        except Exception as e:
            pytest.fail(f"OpenAI chat failed: {e}")
    
    def test_openai_error_handling(self):
        """Test OpenAI error handling with invalid request."""
        log_test_info(
            "OpenAI Error Handling",
            test="Invalid API key handling"
        )
        
        try:
            from aiecs.llm.clients.openai_client import OpenAIClient
            
            # Use invalid API key
            client = OpenAIClient(api_key="invalid_key_test_12345")
            
            with pytest.raises(Exception) as exc_info:
                # Sync call for error testing
                client.generate(prompt="test", model=self.model)
            
            # Verify error is meaningful
            error_msg = str(exc_info.value).lower()
            assert any(keyword in error_msg for keyword in ["api", "auth", "key", "invalid"]), \
                "Error message should indicate authentication issue"
            
            print(f"\n✅ Error handling works correctly")
            
        except ImportError:
            pytest.skip("OpenAI client not available")
