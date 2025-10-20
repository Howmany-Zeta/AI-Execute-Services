import asyncio
import logging
import os
import warnings
from typing import Dict, Any, Optional, List, AsyncGenerator
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold, GenerationConfig, SafetySetting
from google.oauth2 import service_account

from aiecs.llm.clients.base_client import BaseLLMClient, LLMMessage, LLMResponse, ProviderNotAvailableError, RateLimitError
from aiecs.config.config import get_settings

# Suppress Vertex AI SDK deprecation warnings (deprecated June 2025, removal June 2026)
# TODO: Migrate to Google Gen AI SDK when official migration guide is available
warnings.filterwarnings('ignore', category=UserWarning, module='vertexai.generative_models._generative_models')

logger = logging.getLogger(__name__)

class VertexAIClient(BaseLLMClient):
    """Vertex AI provider client"""

    def __init__(self):
        super().__init__("Vertex")
        self.settings = get_settings()
        self._initialized = False

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
        
        # Get model name from config if not provided
        model_name = model or self._get_default_model() or "gemini-2.5-pro"
        
        # Get model config for default parameters
        model_config = self._get_model_config(model_name)
        if model_config and max_tokens is None:
            max_tokens = model_config.default_params.max_tokens

        try:
            # Use the stable Vertex AI API
            model_instance = GenerativeModel(model_name)
            self.logger.debug(f"Initialized Vertex AI model: {model_name}")

            # Convert messages to Vertex AI format
            if len(messages) == 1 and messages[0].role == "user":
                prompt = messages[0].content
            else:
                # For multi-turn conversations, combine messages
                prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

            # Use modern GenerationConfig object
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,  # Increased to account for thinking tokens
                top_p=0.95,
                top_k=40,
            )

            # Modern safety settings configuration using SafetySetting objects
            safety_settings = [
                SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_NONE),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_NONE),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_NONE),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_NONE),
            ]

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model_instance.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            )

            # Handle response content safely - improved multi-part response handling
            content = None
            try:
                # First try to get text directly
                content = response.text
                self.logger.debug(f"Vertex AI response received: {content[:100]}...")
            except (ValueError, AttributeError) as ve:
                # Handle multi-part responses and other issues
                self.logger.warning(f"Cannot get response text directly: {str(ve)}")
                
                # Try to extract content from candidates with multi-part support
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    self.logger.debug(f"Candidate finish_reason: {getattr(candidate, 'finish_reason', 'unknown')}")
                    
                    # Handle multi-part content
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        try:
                            # Extract text from all parts
                            text_parts = []
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    text_parts.append(part.text)
                            
                            if text_parts:
                                # Handle multi-part response format
                                if len(text_parts) > 1:
                                    # Multi-part response (typical for Gemini 2.5 with tool calling)
                                    # Check if parts already contain <thinking> tags
                                    first_part = text_parts[0]
                                    has_thinking_tags = '<thinking>' in first_part
                                    
                                    if has_thinking_tags:
                                        # Parts already have <thinking> tags, extract thinking content and actual output
                                        thinking_contents = []
                                        actual_outputs = []
                                        
                                        for part in text_parts:
                                            if '<thinking>' in part and '</thinking>' in part:
                                                # Extract thinking content from this part
                                                import re
                                                thinking_match = re.search(r'<thinking>(.*?)</thinking>', part, re.DOTALL)
                                                if thinking_match:
                                                    thinking_contents.append(thinking_match.group(1).strip())
                                                    
                                                # Extract content after </thinking>
                                                after_thinking = part[thinking_match.end():].strip()
                                                if after_thinking:
                                                    actual_outputs.append(after_thinking)
                                            else:
                                                # This part doesn't have thinking tags, treat as actual output
                                                actual_outputs.append(part)
                                        
                                        # Combine thinking content and actual outputs
                                        if thinking_contents:
                                            combined_thinking = '\n\n'.join(thinking_contents)
                                            content = f"<thinking>\n{combined_thinking}\n</thinking>"
                                            if actual_outputs:
                                                content += "\n" + "\n".join(actual_outputs)
                                        else:
                                            content = "\n".join(text_parts)
                                        
                                        self.logger.info(f"✅ Multi-part response with existing <thinking> tags processed: {len(text_parts)} parts")
                                    else:
                                        # Parts don't have <thinking> tags, wrap first part
                                        thinking_part = text_parts[0]
                                        actual_output_parts = text_parts[1:]
                                        
                                        # Format: <thinking>Part 1</thinking>\nPart 2\nPart 3...
                                        content = f"<thinking>\n{thinking_part}\n</thinking>\n" + "\n".join(actual_output_parts)
                                        self.logger.info(f"✅ Multi-part response wrapped with <thinking> tags: {len(text_parts)} parts")
                                else:
                                    # Single part response - use as is
                                    content = text_parts[0]
                                    self.logger.info("Successfully extracted single-part response")
                            else:
                                self.logger.warning("No text content found in multi-part response")
                        except Exception as part_error:
                            self.logger.error(f"Failed to extract content from multi-part response: {str(part_error)}")
                    
                    # If still no content, check finish reason
                    if not content:
                        if hasattr(candidate, 'finish_reason'):
                            if candidate.finish_reason == 'MAX_TOKENS':
                                content = "[Response truncated due to token limit - consider increasing max_tokens for Gemini 2.5 models]"
                                self.logger.warning("Response truncated due to MAX_TOKENS - Gemini 2.5 uses thinking tokens")
                            elif candidate.finish_reason in ['SAFETY', 'RECITATION']:
                                content = "[Response blocked by safety filters or content policy]"
                                self.logger.warning(f"Response blocked by safety filters: {candidate.finish_reason}")
                            else:
                                content = f"[Response error: Cannot get response text - {candidate.finish_reason}]"
                        else:
                            content = "[Response error: Cannot get the response text]"
                else:
                    content = f"[Response error: No candidates found - {str(ve)}]"
                
                # Final fallback
                if not content:
                    content = "[Response error: Cannot get the response text. Multiple content parts are not supported.]"

            # Vertex AI doesn't provide detailed token usage in the response
            input_tokens = self._count_tokens_estimate(prompt)
            output_tokens = self._count_tokens_estimate(content)
            tokens_used = input_tokens + output_tokens
            
            # Use config-based cost estimation
            cost = self._estimate_cost_from_config(model_name, input_tokens, output_tokens)

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
            if any(keyword in str(e).lower() for keyword in [
                "cannot get the response text",
                "safety filters", 
                "multiple content parts are not supported",
                "cannot get the candidate text"
            ]):
                self.logger.warning(f"Vertex AI response issue: {str(e)}")
                # Return a response indicating the issue
                return LLMResponse(
                    content="[Response unavailable due to content processing issues or safety filters]",
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
