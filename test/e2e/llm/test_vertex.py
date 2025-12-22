"""
E2E Tests for Vertex AI Integration

Tests real Vertex AI API calls with minimal token usage.
"""

import pytest
import os
from test.e2e.base import E2ELLMTestBase, log_test_info


@pytest.mark.e2e
@pytest.mark.vertex
@pytest.mark.requires_api
class TestVertexAIE2E(E2ELLMTestBase):
    """E2E tests for Vertex AI API."""
    
    @pytest.fixture(autouse=True)
    def setup(self, vertex_config, cost_tracker):
        """Setup Vertex AI client."""
        self.project_id = vertex_config["project_id"]
        self.location = vertex_config["location"]
        self.cost_tracker = cost_tracker
        self.model = "gemini-pro"
    
    @pytest.mark.asyncio
    async def test_vertex_basic_generation(self):
        """Test basic Vertex AI generation with minimal prompt."""
        log_test_info(
            "Vertex AI Basic Generation",
            model=self.model,
            project=self.project_id,
            location=self.location
        )
        
        try:
            from aiecs.llm.clients.vertex_client import VertexAIClient
            
            client = VertexAIClient(
                project_id=self.project_id,
                location=self.location
            )
            prompt = self.get_minimal_prompt()
            
            response, latency = await self.measure_latency_async(
                client.agenerate,
                prompt=prompt,
                model=self.model
            )
            
            # Assertions
            self.assert_llm_response_valid(response)
            assert latency < 20.0, f"Response took {latency:.2f}s (should be < 20s)"
            
            # Record usage (approximate)
            prompt_tokens = len(prompt.split()) * 2
            completion_tokens = len(response.split()) * 2
            self.record_usage(prompt_tokens, completion_tokens, self.model, self.cost_tracker)
            
            print(f"\n✅ Vertex AI response received in {latency:.2f}s")
            print(f"📝 Response: {response[:100]}...")
            
        except ImportError:
            pytest.skip("Vertex AI client not available")
        except Exception as e:
            pytest.fail(f"Vertex AI API call failed: {e}")
    
    @pytest.mark.asyncio
    async def test_vertex_chat(self):
        """Test Vertex AI chat with minimal messages."""
        log_test_info(
            "Vertex AI Chat",
            model=self.model,
            project=self.project_id
        )
        
        try:
            from aiecs.llm.clients.vertex_client import VertexAIClient
            
            client = VertexAIClient(
                project_id=self.project_id,
                location=self.location
            )
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
            assert latency < 20.0, f"Chat took {latency:.2f}s (should be < 20s)"
            
            # Record usage
            prompt_tokens = sum(len(m.get("content", "").split()) for m in messages) * 2
            completion_tokens = len(response_text.split()) * 2
            self.record_usage(prompt_tokens, completion_tokens, self.model, self.cost_tracker)
            
            print(f"\n✅ Vertex AI chat response in {latency:.2f}s")
            
        except ImportError:
            pytest.skip("Vertex AI client not available")
        except Exception as e:
            pytest.fail(f"Vertex AI chat failed: {e}")
