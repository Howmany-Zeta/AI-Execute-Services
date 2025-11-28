import asyncio
import logging
import os
import warnings
from typing import Dict, Any, Optional, List, AsyncGenerator
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    HarmCategory,
    HarmBlockThreshold,
    GenerationConfig,
    SafetySetting,
)

from aiecs.llm.clients.base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ProviderNotAvailableError,
    RateLimitError,
)
from aiecs.config.config import get_settings

# Suppress Vertex AI SDK deprecation warnings (deprecated June 2025, removal June 2026)
# TODO: Migrate to Google Gen AI SDK when official migration guide is available
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="vertexai.generative_models._generative_models",
)

logger = logging.getLogger(__name__)


class VertexAIClient(BaseLLMClient):
    """Vertex AI provider client"""

    def __init__(self):
        super().__init__("Vertex")
        self.settings = get_settings()
        self._initialized = False
        # Track part count statistics for monitoring
        self._part_count_stats = {
            "total_responses": 0,
            "part_counts": {},  # {part_count: frequency}
            "last_part_count": None,
        }

    def _init_vertex_ai(self):
        """Lazy initialization of Vertex AI with proper authentication"""
        if not self._initialized:
            if not self.settings.vertex_project_id:
                raise ProviderNotAvailableError("Vertex AI project ID not configured")

            try:
                # Set up Google Cloud authentication
                pass

                # Check if GOOGLE_APPLICATION_CREDENTIALS is configured
                if self.settings.google_application_credentials:
                    credentials_path = self.settings.google_application_credentials
                    if os.path.exists(credentials_path):
                        # Set the environment variable for Google Cloud SDK
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                        self.logger.info(f"Using Google Cloud credentials from: {credentials_path}")
                    else:
                        self.logger.warning(f"Google Cloud credentials file not found: {credentials_path}")
                        raise ProviderNotAvailableError(f"Google Cloud credentials file not found: {credentials_path}")
                elif "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                    self.logger.info("Using Google Cloud credentials from environment variable")
                else:
                    self.logger.warning("No Google Cloud credentials configured. Using default authentication.")

                # Initialize Vertex AI
                vertexai.init(
                    project=self.settings.vertex_project_id,
                    location=getattr(self.settings, "vertex_location", "us-central1"),
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
        **kwargs,
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
                # Increased to account for thinking tokens
                max_output_tokens=max_tokens or 8192,
                top_p=0.95,
                top_k=40,
            )

            # Modern safety settings configuration using SafetySetting objects
            safety_settings = [
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.BLOCK_NONE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.BLOCK_NONE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.BLOCK_NONE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.BLOCK_NONE,
                ),
            ]

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model_instance.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                ),
            )

            # Handle response content safely - improved multi-part response
            # handling
            content = None
            try:
                # First try to get text directly
                content = response.text
                self.logger.debug(f"Vertex AI response received: {content[:100]}...")
            except (ValueError, AttributeError) as ve:
                # Handle multi-part responses and other issues
                self.logger.warning(f"Cannot get response text directly: {str(ve)}")

                # Try to extract content from candidates with multi-part
                # support
                if hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    self.logger.debug(f"Candidate finish_reason: {getattr(candidate, 'finish_reason', 'unknown')}")

                    # Handle multi-part content
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        try:
                            # Extract text from all parts
                            text_parts: List[str] = []
                            for part in candidate.content.parts:
                                if hasattr(part, "text") and part.text:
                                    text_parts.append(str(part.text))

                            if text_parts:
                                # Log part count for monitoring
                                part_count = len(text_parts)
                                self.logger.info(f"📊 Vertex AI response: {part_count} parts detected")

                                # Update statistics
                                self._part_count_stats["total_responses"] += 1
                                self._part_count_stats["part_counts"][part_count] = self._part_count_stats["part_counts"].get(part_count, 0) + 1
                                self._part_count_stats["last_part_count"] = part_count

                                # Log statistics if significant variation
                                # detected
                                if part_count != self._part_count_stats.get("last_part_count", part_count):
                                    self.logger.warning(f"⚠️ Part count variation detected: {part_count} parts (previous: {self._part_count_stats.get('last_part_count', 'unknown')})")

                                # Handle multi-part response format
                                if len(text_parts) > 1:
                                    # Multi-part response
                                    # Minimal fix: only fix incomplete <thinking> tags, preserve original order
                                    # Do NOT reorganize content - let
                                    # downstream code handle semantics

                                    processed_parts = []
                                    fixed_count = 0

                                    for i, part_raw in enumerate(text_parts):
                                        # Check for thinking content that needs
                                        # formatting
                                        needs_thinking_format = False
                                        # Ensure part is a string (use different name to avoid redefinition)
                                        part_str: str = str(part_raw) if not isinstance(part_raw, str) else part_raw

                                        if "<thinking>" in part_str and "</thinking>" not in part_str:  # type: ignore[operator]
                                            # Incomplete <thinking> tag: add
                                            # closing tag
                                            part_str = part_str + "\n</thinking>"  # type: ignore[operator]
                                            needs_thinking_format = True
                                            self.logger.debug(f"  Part {i+1}: Incomplete <thinking> tag fixed")
                                        elif isinstance(part_str, str) and part_str.startswith("thinking") and "</thinking>" not in part_str:  # type: ignore[operator]
                                            # thinking\n format: convert to
                                            # <thinking>...</thinking>
                                            if part_str.startswith("thinking\n"):
                                                # thinking\n格式：提取内容并包装
                                                # 跳过 "thinking\n"
                                                content = part_str[8:]
                                            else:
                                                # thinking开头但无换行：提取内容并包装
                                                # 跳过 "thinking"
                                                content = part_str[7:]

                                            part_str = f"<thinking>\n{content}\n</thinking>"
                                            needs_thinking_format = True
                                            self.logger.debug(f"  Part {i+1}: thinking\\n format converted to <thinking> tags")

                                        if needs_thinking_format:
                                            fixed_count += 1

                                        processed_parts.append(part_str)

                                    # Merge in original order
                                    content = "\n".join(processed_parts)

                                    if fixed_count > 0:
                                        self.logger.info(f"✅ Multi-part response merged: {len(text_parts)} parts, {fixed_count} incomplete tags fixed, order preserved")
                                    else:
                                        self.logger.info(f"✅ Multi-part response merged: {len(text_parts)} parts, order preserved")
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
                        if hasattr(candidate, "finish_reason"):
                            if candidate.finish_reason == "MAX_TOKENS":
                                content = "[Response truncated due to token limit - consider increasing max_tokens for Gemini 2.5 models]"
                                self.logger.warning("Response truncated due to MAX_TOKENS - Gemini 2.5 uses thinking tokens")
                            elif candidate.finish_reason in [
                                "SAFETY",
                                "RECITATION",
                            ]:
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
                cost_estimate=cost,
            )

        except Exception as e:
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                raise RateLimitError(f"Vertex AI quota exceeded: {str(e)}")
            # Handle specific Vertex AI response errors
            if any(
                keyword in str(e).lower()
                for keyword in [
                    "cannot get the response text",
                    "safety filters",
                    "multiple content parts are not supported",
                    "cannot get the candidate text",
                ]
            ):
                self.logger.warning(f"Vertex AI response issue: {str(e)}")
                # Return a response indicating the issue
                return LLMResponse(
                    content="[Response unavailable due to content processing issues or safety filters]",
                    provider=self.provider_name,
                    model=model_name,
                    tokens_used=self._count_tokens_estimate(prompt),
                    cost_estimate=0.0,
                )
            raise

    async def stream_text(  # type: ignore[override]
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream text using Vertex AI (simulated streaming)"""
        # Vertex AI streaming is more complex, for now fall back to
        # non-streaming
        response = await self.generate_text(messages, model, temperature, max_tokens, **kwargs)

        # Simulate streaming by yielding words
        words = response.content.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)  # Small delay to simulate streaming

    def get_part_count_stats(self) -> Dict[str, Any]:
        """
        Get statistics about part count variations in Vertex AI responses.

        Returns:
            Dictionary containing part count statistics and analysis
        """
        stats = self._part_count_stats.copy()

        if stats["total_responses"] > 0:
            # Calculate variation metrics
            part_counts = list(stats["part_counts"].keys())
            stats["variation_analysis"] = {
                "unique_part_counts": len(part_counts),
                "most_common_count": (max(stats["part_counts"].items(), key=lambda x: x[1])[0] if stats["part_counts"] else None),
                "part_count_range": (f"{min(part_counts)}-{max(part_counts)}" if part_counts else "N/A"),
                # 0-1, higher is more stable
                "stability_score": 1.0 - (len(part_counts) - 1) / max(stats["total_responses"], 1),
            }

            # Generate recommendations
            if stats["variation_analysis"]["stability_score"] < 0.7:
                stats["recommendations"] = [
                    "High part count variation detected",
                    "Consider optimizing prompt structure",
                    "Monitor input complexity patterns",
                    "Review tool calling configuration",
                ]
            else:
                stats["recommendations"] = [
                    "Part count variation is within acceptable range",
                    "Continue monitoring for patterns",
                ]

        return stats

    def log_part_count_summary(self):
        """Log a summary of part count statistics"""
        stats = self.get_part_count_stats()

        if stats["total_responses"] > 0:
            self.logger.info("📈 Vertex AI Part Count Summary:")
            self.logger.info(f"  Total responses: {stats['total_responses']}")
            self.logger.info(f"  Part count distribution: {stats['part_counts']}")

            if "variation_analysis" in stats:
                analysis = stats["variation_analysis"]
                self.logger.info(f"  Stability score: {analysis['stability_score']:.2f}")
                self.logger.info(f"  Most common count: {analysis['most_common_count']}")
                self.logger.info(f"  Count range: {analysis['part_count_range']}")

                if "recommendations" in stats:
                    self.logger.info("  Recommendations:")
                    for rec in stats["recommendations"]:
                        self.logger.info(f"    • {rec}")

    async def get_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings using Vertex AI embedding model
        
        Args:
            texts: List of texts to embed
            model: Embedding model name (default: gemini-embedding-001)
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        self._init_vertex_ai()
        
        # Use gemini-embedding-001 as default
        embedding_model_name = model or "gemini-embedding-001"
        
        try:
            from google.cloud import aiplatform
            from google.cloud.aiplatform.gapic import PredictionServiceClient
            from google.protobuf import struct_pb2
            
            # Initialize prediction client
            location = getattr(self.settings, "vertex_location", "us-central1")
            endpoint = f"{location}-aiplatform.googleapis.com"
            client = PredictionServiceClient(client_options={"api_endpoint": endpoint})
            
            # Model resource name
            model_resource = f"projects/{self.settings.vertex_project_id}/locations/{location}/publishers/google/models/{embedding_model_name}"
            
            # Generate embeddings for each text
            embeddings = []
            for text in texts:
                # Prepare instance
                instance = struct_pb2.Struct()
                instance.fields["content"].string_value = text
                
                # Make prediction request
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.predict(
                        endpoint=model_resource,
                        instances=[instance]
                    )
                )
                
                # Extract embedding
                if response.predictions and len(response.predictions) > 0:
                    prediction = response.predictions[0]
                    if "embeddings" in prediction and "values" in prediction["embeddings"]:
                        embedding = list(prediction["embeddings"]["values"])
                        embeddings.append(embedding)
                    else:
                        self.logger.warning(f"Unexpected response format for embedding: {prediction}")
                        # Return zero vector as fallback
                        embeddings.append([0.0] * 768)
                else:
                    self.logger.warning("No predictions returned from embedding model")
                    embeddings.append([0.0] * 768)
            
            return embeddings
            
        except ImportError as e:
            self.logger.error(f"Required Vertex AI libraries not available: {e}")
            # Return zero vectors as fallback
            return [[0.0] * 768 for _ in texts]
        except Exception as e:
            self.logger.error(f"Error generating embeddings with Vertex AI: {e}")
            # Return zero vectors as fallback
            return [[0.0] * 768 for _ in texts]

    async def close(self):
        """Clean up resources"""
        # Log final statistics before cleanup
        self.log_part_count_summary()
        # Vertex AI doesn't require explicit cleanup
        self._initialized = False
