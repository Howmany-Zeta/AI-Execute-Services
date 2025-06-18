import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from vertexai.generative_models import GenerativeModel
import vertexai

from .base_client import BaseLLMClient, LLMMessage, LLMResponse, ProviderNotAvailableError, RateLimitError
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class VertexAIClient(BaseLLMClient):
    """Vertex AI provider client"""

    def __init__(self):
        super().__init__("vertex")
        self.settings = get_settings()
        self._initialized = False

        # Token cost estimates (USD per 1K tokens)
        self.token_costs = {
            "gemini-pro": {"input": 0.00025, "output": 0.0005},
            "gemini-1.5-pro": {"input": 0.00125, "output": 0.00375},
            "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        }

    def _init_vertex_ai(self):
        """Lazy initialization of Vertex AI"""
        if not self._initialized:
            if not self.settings.vertex_project_id:
                raise ProviderNotAvailableError("Vertex AI project ID not configured")
            try:
                vertexai.init(
                    project=self.settings.vertex_project_id,
                    location=getattr(self.settings, 'vertex_location', 'us-central1')
                )
                self._initialized = True
                self.logger.info(f"Vertex AI initialized for project {self.settings.vertex_project_id}")
            except Exception as e:
                raise ProviderNotAvailableError(f"Failed to initialize Vertex AI: {str(e)}")

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text using Vertex AI"""
        self._init_vertex_ai()
        model_name = model or "gemini-1.5-pro"

        try:
            # Use the stable Vertex AI API
            model_instance = GenerativeModel(model_name)

            # Convert messages to Vertex AI format
            if len(messages) == 1 and messages[0].role == "user":
                prompt = messages[0].content
            else:
                # For multi-turn conversations, combine messages
                prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model_instance.generate_content(
                    prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens or 1024,
                    }
                )
            )

            content = response.text
            # Vertex AI doesn't provide detailed token usage in the response
            tokens_used = self._count_tokens_estimate(prompt + content)
            cost = self._estimate_cost(
                model_name,
                self._count_tokens_estimate(prompt),
                self._count_tokens_estimate(content),
                self.token_costs
            )

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=model_name,
                tokens_used=tokens_used,
                cost_estimate=cost
            )

        except Exception as e:
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                raise RateLimitError(f"Vertex AI quota exceeded: {str(e)}")
            raise

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text using Vertex AI (simulated streaming)"""
        # Vertex AI streaming is more complex, for now fall back to non-streaming
        response = await self.generate_text(messages, model, temperature, max_tokens, **kwargs)

        # Simulate streaming by yielding words
        words = response.content.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)  # Small delay to simulate streaming

    async def close(self):
        """Clean up resources"""
        # Vertex AI doesn't require explicit cleanup
        self._initialized = False
