import asyncio
import logging
import os
from typing import Dict, Any, Optional, List, AsyncGenerator
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
import vertexai
from google.oauth2 import service_account

from .base_client import BaseLLMClient, LLMMessage, LLMResponse, ProviderNotAvailableError, RateLimitError
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)

class VertexAIClient(BaseLLMClient):
    """Vertex AI provider client"""

    def __init__(self):
        super().__init__("Vertex")
        self.settings = get_settings()
        self._initialized = False

        # Token cost estimates (USD per 1K tokens)
        self.token_costs = {
            "gemini-2.5-pro": {"input": 0.00125, "output": 0.00375},
            "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
        }

    def _init_vertex_ai(self):
        """Lazy initialization of Vertex AI with proper authentication"""
        if not self._initialized:
            if not self.settings.vertex_project_id:
                raise ProviderNotAvailableError("Vertex AI project ID not configured")

            try:
                # Set up Google Cloud authentication
                credentials = None

                # Check if GOOGLE_APPLICATION_CREDENTIALS is configured
                if self.settings.google_application_credentials:
                    credentials_path = self.settings.google_application_credentials
                    if os.path.exists(credentials_path):
                        # Set the environment variable for Google Cloud SDK
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                        self.logger.info(f"Using Google Cloud credentials from: {credentials_path}")
                    else:
                        self.logger.warning(f"Google Cloud credentials file not found: {credentials_path}")
                        raise ProviderNotAvailableError(f"Google Cloud credentials file not found: {credentials_path}")
                elif 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                    self.logger.info("Using Google Cloud credentials from environment variable")
                else:
                    self.logger.warning("No Google Cloud credentials configured. Using default authentication.")

                # Initialize Vertex AI
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
        model_name = model or "gemini-2.5-pro"

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
                        "max_output_tokens": max_tokens or 8192,  # Increased to account for thinking tokens
                        "top_p": 0.95,
                        "top_k": 40,
                    },
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
            )

            # Handle response content safely
            try:
                content = response.text
                self.logger.debug(f"Vertex AI response received: {content[:100]}...")
            except ValueError as ve:
                # Handle cases where response has no content (safety filters, etc.)
                self.logger.warning(f"Vertex AI response error: {str(ve)}")
                self.logger.debug(f"Full response object: {response}")

                # Check if response has candidates but no text
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    self.logger.debug(f"Candidate finish_reason: {getattr(candidate, 'finish_reason', 'unknown')}")

                    # If finish_reason is MAX_TOKENS, it might be due to thinking tokens
                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 'MAX_TOKENS':
                        content = "[Response truncated due to token limit - consider increasing max_tokens for Gemini 2.5 models]"
                        self.logger.warning("Response truncated due to MAX_TOKENS - Gemini 2.5 uses thinking tokens")
                    elif "no parts" in str(ve).lower() or "safety filters" in str(ve).lower():
                        content = "[Response blocked by safety filters or has no content]"
                        self.logger.warning(f"Vertex AI response blocked or empty: {str(ve)}")
                    else:
                        content = f"[Response error: {str(ve)}]"
                else:
                    content = f"[Response error: {str(ve)}]"

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
            # Handle specific Vertex AI response errors
            if "cannot get the response text" in str(e).lower() or "safety filters" in str(e).lower():
                self.logger.warning(f"Vertex AI response issue: {str(e)}")
                # Return a response indicating the issue
                return LLMResponse(
                    content="[Response unavailable due to safety filters or content policy]",
                    provider=self.provider_name,
                    model=model_name,
                    tokens_used=self._count_tokens_estimate(prompt),
                    cost_estimate=0.0
                )
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
