"""
E2E Tests for Google AI (Gemini) Integration

Tests real Google AI API calls with minimal token usage.
"""

import pytest
import os
from test.e2e.base import E2ELLMTestBase, log_test_info


@pytest.mark.e2e
@pytest.mark.google
@pytest.mark.requires_api
class TestGoogleAIE2E(E2ELLMTestBase):
    """E2E tests for Google AI (Gemini) API."""
    
    @pytest.fixture(autouse=True)
    def setup(self, google_api_key, cost_tracker):
        """Setup Google AI client."""
        self.api_key = google_api_key
        self.cost_tracker = cost_tracker
        self.model = "gemini-pro"
    
    @pytest.mark.asyncio
    async def test_googleai_basic_generation(self):
        """Test basic Google AI generation with minimal prompt."""
        log_test_info(
            "Google AI Basic Generation",
            model=self.model,
            prompt="Minimal test prompt"
        )
        
        try:
            from aiecs.llm.clients.google_client import GoogleAIClient
            
            client = GoogleAIClient(api_key=self.api_key)
            prompt = self.get_minimal_prompt()
            
            response, latency = await self.measure_latency_async(
                client.agenerate,
                prompt=prompt,
                model=self.model
            )
            
            # Assertions
            self.assert_llm_response_valid(response)
            assert latency < 15.0, f"Response took {latency:.2f}s (should be < 15s)"
            
            # Record usage (approximate)
            prompt_tokens = len(prompt.split()) * 2  # Gemini uses different tokenization
            completion_tokens = len(response.split()) * 2
            self.record_usage(prompt_tokens, completion_tokens, self.model, self.cost_tracker)
            
            print(f"\n✅ Google AI response received in {latency:.2f}s")
            print(f"📝 Response: {response[:100]}...")
            
        except ImportError:
            pytest.skip("Google AI client not available")
        except Exception as e:
            pytest.fail(f"Google AI API call failed: {e}")
    
    @pytest.mark.asyncio
    async def test_googleai_chat(self):
        """Test Google AI chat with minimal messages."""
        log_test_info(
            "Google AI Chat",
            model=self.model,
            message_count=1
        )
        
        try:
            from aiecs.llm.clients.google_client import GoogleAIClient
            
            client = GoogleAIClient(api_key=self.api_key)
            messages = self.get_test_messages()
            
            response, latency = await self.measure_latency_async(
                client.achat,
                messages=messages,
                model=self.model
            )
            
            # Extract response text
            response_text = response if isinstance(response, str) else str(response)
            
            # Assertions
            self.assert_llm_response_valid(response_text)
            assert latency < 15.0, f"Chat took {latency:.2f}s (should be < 15s)"
            
            # Record usage
            prompt_tokens = sum(len(m.get("content", "").split()) for m in messages) * 2
            completion_tokens = len(response_text.split()) * 2
            self.record_usage(prompt_tokens, completion_tokens, self.model, self.cost_tracker)
            
            print(f"\n✅ Google AI chat response in {latency:.2f}s")
            
        except ImportError:
            pytest.skip("Google AI client not available")
        except Exception as e:
            pytest.fail(f"Google AI chat failed: {e}")
