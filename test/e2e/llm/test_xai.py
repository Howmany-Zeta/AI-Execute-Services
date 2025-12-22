"""
E2E Tests for xAI (Grok) Integration

Tests real xAI API calls with minimal token usage.
"""

import pytest
import os
from test.e2e.base import E2ELLMTestBase, log_test_info


@pytest.mark.e2e
@pytest.mark.xai
@pytest.mark.requires_api
class TestXAIE2E(E2ELLMTestBase):
    """E2E tests for xAI (Grok) API."""
    
    @pytest.fixture(autouse=True)
    def setup(self, xai_api_key, cost_tracker):
        """Setup xAI client."""
        self.api_key = xai_api_key
        self.cost_tracker = cost_tracker
        self.model = "grok-1"
    
    @pytest.mark.asyncio
    async def test_xai_basic_generation(self):
        """Test basic xAI generation with minimal prompt."""
        log_test_info(
            "xAI Basic Generation",
            model=self.model,
            prompt="Minimal test prompt"
        )
        
        try:
            from aiecs.llm.clients.xai_client import XAIClient
            
            client = XAIClient(api_key=self.api_key)
            prompt = self.get_minimal_prompt()
            
            response, latency = await self.measure_latency_async(
                client.agenerate,
                prompt=prompt,
                model=self.model,
                max_tokens=10  # Minimal tokens
            )
            
            # Assertions
            self.assert_llm_response_valid(response)
            assert latency < 15.0, f"Response took {latency:.2f}s (should be < 15s)"
            
            # Record usage (approximate)
            prompt_tokens = len(prompt.split())
            completion_tokens = len(response.split())
            self.record_usage(prompt_tokens, completion_tokens, self.model, self.cost_tracker)
            
            print(f"\n✅ xAI response received in {latency:.2f}s")
            print(f"📝 Response: {response[:100]}...")
            
        except ImportError:
            pytest.skip("xAI client not available")
        except Exception as e:
            pytest.fail(f"xAI API call failed: {e}")
    
    @pytest.mark.asyncio
    async def test_xai_chat(self):
        """Test xAI chat with minimal messages."""
        log_test_info(
            "xAI Chat",
            model=self.model,
            message_count=1
        )
        
        try:
            from aiecs.llm.clients.xai_client import XAIClient
            
            client = XAIClient(api_key=self.api_key)
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
            assert latency < 15.0, f"Chat took {latency:.2f}s (should be < 15s)"
            
            # Record usage
            prompt_tokens = sum(len(m.get("content", "").split()) for m in messages)
            completion_tokens = len(response_text.split())
            self.record_usage(prompt_tokens, completion_tokens, self.model, self.cost_tracker)
            
            print(f"\n✅ xAI chat response in {latency:.2f}s")
            
        except ImportError:
            pytest.skip("xAI client not available")
        except Exception as e:
            pytest.fail(f"xAI chat failed: {e}")
