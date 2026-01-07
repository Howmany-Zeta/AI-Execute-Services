import asyncio
import json
import logging
import os
import warnings
import hashlib
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    HarmCategory,
    HarmBlockThreshold,
    GenerationConfig,
    SafetySetting,
    Content,
    Part,
)

logger = logging.getLogger(__name__)

# Try to import CachedContent for prompt caching support
try:
    from vertexai.preview import caching
    CACHED_CONTENT_AVAILABLE = True
except ImportError:
    try:
        # Alternative import path for different SDK versions
        from vertexai import caching
        CACHED_CONTENT_AVAILABLE = True
    except ImportError:
        CACHED_CONTENT_AVAILABLE = False
        # Note: logger may not be initialized yet, so we'll log later

from aiecs.llm.clients.base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ProviderNotAvailableError,
    RateLimitError,
    SafetyBlockError,
)
from aiecs.llm.clients.google_function_calling_mixin import GoogleFunctionCallingMixin
from aiecs.config.config import get_settings

# Suppress Vertex AI SDK deprecation warnings (deprecated June 2025, removal June 2026)
# TODO: Migrate to Google Gen AI SDK when official migration guide is available
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="vertexai.generative_models._generative_models",
)

logger = logging.getLogger(__name__)


def _extract_safety_ratings(safety_ratings: Any) -> List[Dict[str, Any]]:
    """
    Extract safety ratings information from Vertex AI response.
    
    Args:
        safety_ratings: Safety ratings object from Vertex AI response
        
    Returns:
        List of dictionaries containing safety rating details
    """
    ratings_list = []
    if not safety_ratings:
        return ratings_list
    
    # Handle both list and single object
    ratings_iter = safety_ratings if isinstance(safety_ratings, list) else [safety_ratings]
    
    for rating in ratings_iter:
        rating_dict = {}
        
        # Extract category
        if hasattr(rating, "category"):
            rating_dict["category"] = str(rating.category)
        elif hasattr(rating, "get"):
            rating_dict["category"] = rating.get("category", "UNKNOWN")
        
        # Extract blocked status
        if hasattr(rating, "blocked"):
            rating_dict["blocked"] = bool(rating.blocked)
        elif hasattr(rating, "get"):
            rating_dict["blocked"] = rating.get("blocked", False)
        
        # Extract severity (for HarmBlockMethod.SEVERITY)
        if hasattr(rating, "severity"):
            rating_dict["severity"] = str(rating.severity)
        elif hasattr(rating, "get"):
            rating_dict["severity"] = rating.get("severity")
        
        if hasattr(rating, "severity_score"):
            rating_dict["severity_score"] = float(rating.severity_score)
        elif hasattr(rating, "get"):
            rating_dict["severity_score"] = rating.get("severity_score")
        
        # Extract probability (for HarmBlockMethod.PROBABILITY)
        if hasattr(rating, "probability"):
            rating_dict["probability"] = str(rating.probability)
        elif hasattr(rating, "get"):
            rating_dict["probability"] = rating.get("probability")
        
        if hasattr(rating, "probability_score"):
            rating_dict["probability_score"] = float(rating.probability_score)
        elif hasattr(rating, "get"):
            rating_dict["probability_score"] = rating.get("probability_score")
        
        ratings_list.append(rating_dict)
    
    return ratings_list


def _build_safety_block_error(
    response: Any,
    block_type: str,
    default_message: str,
) -> SafetyBlockError:
    """
    Build a detailed SafetyBlockError from Vertex AI response.
    
    Args:
        response: Vertex AI response object
        block_type: "prompt" or "response"
        default_message: Default error message
        
    Returns:
        SafetyBlockError with detailed information
    """
    block_reason = None
    safety_ratings = []
    
    if block_type == "prompt":
        # Check prompt_feedback for prompt blocks
        if hasattr(response, "prompt_feedback"):
            pf = response.prompt_feedback
            if hasattr(pf, "block_reason"):
                block_reason = str(pf.block_reason)
            elif hasattr(pf, "get"):
                block_reason = pf.get("block_reason")
            
            if hasattr(pf, "safety_ratings"):
                safety_ratings = _extract_safety_ratings(pf.safety_ratings)
            elif hasattr(pf, "get"):
                safety_ratings = _extract_safety_ratings(pf.get("safety_ratings", []))
    
    elif block_type == "response":
        # Check candidates for response blocks
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "safety_ratings"):
                safety_ratings = _extract_safety_ratings(candidate.safety_ratings)
            elif hasattr(candidate, "get"):
                safety_ratings = _extract_safety_ratings(candidate.get("safety_ratings", []))
            
            # Check finish_reason
            if hasattr(candidate, "finish_reason"):
                finish_reason = str(candidate.finish_reason)
                if finish_reason in ["SAFETY", "RECITATION"]:
                    block_reason = finish_reason
    
    # Build detailed error message
    error_parts = [default_message]
    if block_reason:
        error_parts.append(f"Block reason: {block_reason}")

    # Safely extract blocked categories, handling potential non-dict elements
    blocked_categories = []
    for r in safety_ratings:
        if isinstance(r, dict) and r.get("blocked", False):
            blocked_categories.append(r.get("category", "UNKNOWN"))
    if blocked_categories:
        error_parts.append(f"Blocked categories: {', '.join(blocked_categories)}")

    # Add severity/probability information
    for rating in safety_ratings:
        # Skip non-dict elements
        if not isinstance(rating, dict):
            continue
        if rating.get("blocked"):
            if "severity" in rating:
                error_parts.append(
                    f"{rating.get('category', 'UNKNOWN')}: severity={rating.get('severity')}, "
                    f"score={rating.get('severity_score', 'N/A')}"
                )
            elif "probability" in rating:
                error_parts.append(
                    f"{rating.get('category', 'UNKNOWN')}: probability={rating.get('probability')}, "
                    f"score={rating.get('probability_score', 'N/A')}"
                )
    
    error_message = " | ".join(error_parts)
    
    return SafetyBlockError(
        message=error_message,
        block_reason=block_reason,
        block_type=block_type,
        safety_ratings=safety_ratings,
    )


class VertexAIClient(BaseLLMClient, GoogleFunctionCallingMixin):
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
        # Cache for CachedContent objects (key: content hash, value: cached_content_id)
        self._cached_content_cache: Dict[str, str] = {}

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

    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash for content to use as cache key."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    async def _create_or_get_cached_content(
        self,
        content: str,
        model_name: str,
        ttl_seconds: Optional[int] = None,
    ) -> Optional[str]:
        """
        Create or get a CachedContent for the given content.
        
        This method implements Gemini's CachedContent API for prompt caching.
        It preserves the existing cache_control mechanism for developer convenience.
        
        The method supports multiple Vertex AI SDK versions and gracefully falls back
        to regular system_instruction if CachedContent API is unavailable.
        
        Args:
            content: Content to cache (typically system instruction)
            model_name: Model name to use for caching
            ttl_seconds: Time to live in seconds (optional, defaults to 3600)
            
        Returns:
            CachedContent resource name (e.g., "projects/.../cachedContents/...") or None if caching unavailable
        """
        if not CACHED_CONTENT_AVAILABLE:
            self.logger.debug("CachedContent API not available, skipping cache creation")
            return None
        
        if not content or not content.strip():
            return None
        
        # Generate cache key
        cache_key = self._generate_content_hash(content)
        
        # Check if we already have this cached
        if cache_key in self._cached_content_cache:
            cached_content_id = self._cached_content_cache[cache_key]
            self.logger.debug(f"Using existing CachedContent: {cached_content_id}")
            return cached_content_id
        
        try:
            self._init_vertex_ai()
            
            # Build the content to cache (system instruction as Content)
            # For CachedContent, we typically cache the system instruction
            cached_content_obj = Content(
                role="user",
                parts=[Part.from_text(content)]
            )
            
            # Try different API patterns based on SDK version
            cached_content_id = None
            
            # Pattern 1: caching.CachedContent.create() (most common)
            if hasattr(caching, 'CachedContent'):
                try:
                    cached_content = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: caching.CachedContent.create(
                            model=model_name,
                            contents=[cached_content_obj],
                            ttl_seconds=ttl_seconds or 3600,  # Default 1 hour
                        )
                    )
                    
                    # Extract the resource name
                    if hasattr(cached_content, 'name'):
                        cached_content_id = cached_content.name
                    elif hasattr(cached_content, 'resource_name'):
                        cached_content_id = cached_content.resource_name
                    else:
                        cached_content_id = str(cached_content)
                    
                    if cached_content_id:
                        # Store in cache
                        self._cached_content_cache[cache_key] = cached_content_id
                        self.logger.info(f"Created CachedContent for prompt caching: {cached_content_id}")
                        return cached_content_id
                        
                except AttributeError as e:
                    self.logger.debug(f"CachedContent.create() signature may differ: {str(e)}")
                except Exception as e:
                    self.logger.debug(f"Failed to create CachedContent using pattern 1: {str(e)}")
            
            # Pattern 2: Try alternative API patterns if Pattern 1 fails
            # Note: Different SDK versions may have different APIs
            # This is a fallback that allows graceful degradation
            self.logger.warning(
                "CachedContent API not available or incompatible with current SDK version. "
                "Falling back to system_instruction (prompt caching disabled). "
                "To enable prompt caching, ensure you're using a compatible Vertex AI SDK version."
            )
            return None
                
        except Exception as e:
            self.logger.warning(
                f"Failed to create CachedContent (prompt caching disabled, using system_instruction): {str(e)}"
            )
            # Don't raise - allow fallback to regular generation without caching
            return None

    def _convert_messages_to_contents(
        self, messages: List[LLMMessage]
    ) -> List[Content]:
        """
        Convert LLMMessage list to Vertex AI Content objects.

        This properly handles multi-turn conversations including
        function/tool responses for Vertex AI Function Calling.

        Args:
            messages: List of LLMMessage objects (system messages should be filtered out)

        Returns:
            List of Content objects for Vertex AI API
        """
        contents = []

        for msg in messages:
            # Handle tool/function responses (role="tool")
            if msg.role == "tool":
                # Vertex AI expects function responses as user messages with FunctionResponse parts
                # The tool_call_id maps to the function name
                func_name = msg.tool_call_id or "unknown_function"

                # Parse content as the function response
                try:
                    # Try to parse as JSON if it looks like JSON
                    if msg.content and msg.content.strip().startswith('{'):
                        response_data = json.loads(msg.content)
                    else:
                        response_data = {"result": msg.content}
                except json.JSONDecodeError:
                    response_data = {"result": msg.content}

                # Create FunctionResponse part using Part.from_function_response
                func_response_part = Part.from_function_response(
                    name=func_name,
                    response=response_data
                )

                contents.append(Content(
                    role="user",  # Function responses are sent as "user" role in Vertex AI
                    parts=[func_response_part]
                ))

            # Handle assistant messages with tool calls
            elif msg.role == "assistant" and msg.tool_calls:
                parts = []
                if msg.content:
                    parts.append(Part.from_text(msg.content))

                for tool_call in msg.tool_calls:
                    func = tool_call.get("function", {})
                    func_name = func.get("name", "")
                    func_args = func.get("arguments", "{}")

                    # Parse arguments
                    try:
                        args_dict = json.loads(func_args) if isinstance(func_args, str) else func_args
                    except json.JSONDecodeError:
                        args_dict = {}

                    # Create FunctionCall part using Part.from_dict
                    # Note: Part.from_function_call() does NOT exist in Vertex AI SDK
                    # Must use from_dict with function_call structure
                    function_call_part = Part.from_dict({
                        "function_call": {
                            "name": func_name,
                            "args": args_dict
                        }
                    })
                    parts.append(function_call_part)

                contents.append(Content(
                    role="model",
                    parts=parts
                ))

            # Handle regular messages (user, assistant without tool_calls)
            else:
                role = "model" if msg.role == "assistant" else msg.role
                if msg.content:
                    contents.append(Content(
                        role=role,
                        parts=[Part.from_text(msg.content)]
                    ))

        return contents

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        system_instruction: Optional[str] = None,
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
            # Extract system message from messages if present
            system_msg = None
            system_cache_control = None
            user_messages = []
            for msg in messages:
                if msg.role == "system":
                    system_msg = msg.content
                    system_cache_control = msg.cache_control
                else:
                    user_messages.append(msg)

            # Use explicit system_instruction parameter if provided, else use extracted system message
            final_system_instruction = system_instruction or system_msg

            # Check if we should use CachedContent API for prompt caching
            cached_content_id = None
            if final_system_instruction and system_cache_control:
                # Create or get CachedContent for the system instruction
                # Extract TTL from cache_control if available (defaults to 3600 seconds)
                ttl_seconds = getattr(system_cache_control, 'ttl_seconds', None) or 3600
                cached_content_id = await self._create_or_get_cached_content(
                    content=final_system_instruction,
                    model_name=model_name,
                    ttl_seconds=ttl_seconds,
                )
                if cached_content_id:
                    self.logger.debug(f"Using CachedContent for prompt caching: {cached_content_id}")
                    # When using CachedContent, we don't pass system_instruction to GenerativeModel
                    # Instead, we'll pass cached_content_id to generate_content
                    final_system_instruction = None

            # Initialize model WITH system instruction for prompt caching support
            # Note: If using CachedContent, system_instruction will be None
            model_instance = GenerativeModel(
                model_name,
                system_instruction=final_system_instruction
            )
            self.logger.debug(f"Initialized Vertex AI model: {model_name}")

            # Convert messages to Vertex AI format
            if len(user_messages) == 1 and user_messages[0].role == "user":
                contents = user_messages[0].content
            else:
                # For multi-turn conversations, use proper Content objects
                contents = self._convert_messages_to_contents(user_messages)

            # Use modern GenerationConfig object
            generation_config = GenerationConfig(
                temperature=temperature,
                # Increased to account for thinking tokens
                max_output_tokens=max_tokens or 8192,
                top_p=0.95,
                top_k=40,
            )

            # Modern safety settings configuration using SafetySetting objects
            # Allow override via kwargs, otherwise use defaults (BLOCK_NONE for all categories)
            if "safety_settings" in kwargs:
                safety_settings = kwargs["safety_settings"]
                if not isinstance(safety_settings, list):
                    raise ValueError("safety_settings must be a list of SafetySetting objects")
            else:
                # Default safety settings - can be configured via environment or config
                # Default to BLOCK_NONE to allow all content (can be overridden)
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

            # Prepare tools for Function Calling if provided
            tools_for_api = None
            if tools or functions:
                # Convert OpenAI format to Google format
                tools_list = tools or []
                if functions:
                    # Convert legacy functions format to tools format
                    tools_list = [{"type": "function", "function": func} for func in functions]
                
                google_tools = self._convert_openai_to_google_format(tools_list)
                if google_tools:
                    tools_for_api = google_tools
            
            # Build API call parameters
            api_params = {
                "contents": contents,
                "generation_config": generation_config,
                "safety_settings": safety_settings,
            }
            
            # Add cached_content if using CachedContent API for prompt caching
            if cached_content_id:
                api_params["cached_content"] = cached_content_id
                self.logger.debug(f"Added cached_content to API params: {cached_content_id}")
            
            # Add tools if available
            if tools_for_api:
                api_params["tools"] = tools_for_api
            
            # Add any additional kwargs (but exclude tools/safety_settings/cached_content to avoid conflicts)
            for key, value in kwargs.items():
                if key not in ["tools", "safety_settings", "cached_content"]:
                    api_params[key] = value
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model_instance.generate_content(**api_params),
            )

            # Check for prompt-level safety blocks first
            if hasattr(response, "prompt_feedback"):
                pf = response.prompt_feedback
                # Check if prompt was blocked
                if hasattr(pf, "block_reason") and pf.block_reason:
                    block_reason = str(pf.block_reason)
                    if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER"]:
                        # Prompt was blocked by safety filters
                        raise _build_safety_block_error(
                            response,
                            block_type="prompt",
                            default_message="Prompt blocked by safety filters",
                        )
                elif hasattr(pf, "get") and pf.get("block_reason"):
                    block_reason = pf.get("block_reason")
                    if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER"]:
                        raise _build_safety_block_error(
                            response,
                            block_type="prompt",
                            default_message="Prompt blocked by safety filters",
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
                                # Response was blocked by safety filters
                                raise _build_safety_block_error(
                                    response,
                                    block_type="response",
                                    default_message="Response blocked by safety filters",
                                )
                            else:
                                content = f"[Response error: Cannot get response text - {candidate.finish_reason}]"
                        else:
                            content = "[Response error: Cannot get the response text]"
                else:
                    # No candidates found - check if this is due to safety filters
                    # Check prompt_feedback for block reason
                    if hasattr(response, "prompt_feedback"):
                        pf = response.prompt_feedback
                        if hasattr(pf, "block_reason") and pf.block_reason:
                            block_reason = str(pf.block_reason)
                            if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER"]:
                                raise _build_safety_block_error(
                                    response,
                                    block_type="prompt",
                                    default_message="No candidates found - prompt blocked by safety filters",
                                )
                        elif hasattr(pf, "get") and pf.get("block_reason"):
                            block_reason = pf.get("block_reason")
                            if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER"]:
                                raise _build_safety_block_error(
                                    response,
                                    block_type="prompt",
                                    default_message="No candidates found - prompt blocked by safety filters",
                                )
                    
                    # If not a safety block, raise generic error with details
                    error_msg = f"Response error: No candidates found - Response has no candidates (and thus no text)."
                    if hasattr(response, "prompt_feedback"):
                        error_msg += " Check prompt_feedback for details."
                    raise ValueError(error_msg)

                # Final fallback
                if not content:
                    content = "[Response error: Cannot get the response text. Multiple content parts are not supported.]"

            # Vertex AI doesn't provide detailed token usage in the response
            # Use estimation method as fallback
            # Estimate input tokens from messages content
            prompt_text = " ".join(msg.content for msg in messages if msg.content)
            input_tokens = self._count_tokens_estimate(prompt_text)
            output_tokens = self._count_tokens_estimate(content)
            tokens_used = input_tokens + output_tokens

            # Extract cache metadata from Vertex AI response if available
            cache_read_tokens = None
            cache_hit = None
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                if hasattr(usage, "cached_content_token_count"):
                    cache_read_tokens = usage.cached_content_token_count
                    cache_hit = cache_read_tokens is not None and cache_read_tokens > 0

            # Use config-based cost estimation
            cost = self._estimate_cost_from_config(model_name, input_tokens, output_tokens)

            # Extract function calls from response if present
            function_calls = self._extract_function_calls_from_google_response(response)

            llm_response = LLMResponse(
                content=content,
                provider=self.provider_name,
                model=model_name,
                tokens_used=tokens_used,
                prompt_tokens=input_tokens,  # Estimated value since Vertex AI doesn't provide detailed usage
                completion_tokens=output_tokens,  # Estimated value since Vertex AI doesn't provide detailed usage
                cost_estimate=cost,
                cache_read_tokens=cache_read_tokens,
                cache_hit=cache_hit,
            )

            # Attach function call info if present
            if function_calls:
                self._attach_function_calls_to_response(llm_response, function_calls)

            return llm_response

        except SafetyBlockError:
            # Re-raise safety block errors as-is (they already contain detailed information)
            raise
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
                # Estimate prompt tokens from messages content
                prompt_text = " ".join(msg.content for msg in messages if msg.content)
                estimated_prompt_tokens = self._count_tokens_estimate(prompt_text)
                return LLMResponse(
                    content="[Response unavailable due to content processing issues or safety filters]",
                    provider=self.provider_name,
                    model=model_name,
                    tokens_used=estimated_prompt_tokens,
                    prompt_tokens=estimated_prompt_tokens,
                    completion_tokens=0,
                    cost_estimate=0.0,
                )
            raise

    async def stream_text(  # type: ignore[override]
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        return_chunks: bool = False,
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[Any, None]:
        """
        Stream text using Vertex AI real streaming API with Function Calling support.

        Args:
            messages: List of LLM messages
            model: Model name (optional)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format)
            tool_choice: Tool choice strategy (not used for Google Vertex AI)
            return_chunks: If True, returns GoogleStreamChunk objects; if False, returns str tokens only
            system_instruction: System instruction for prompt caching support
            **kwargs: Additional arguments

        Yields:
            str or GoogleStreamChunk: Text tokens or StreamChunk objects
        """
        self._init_vertex_ai()

        # Get model name from config if not provided
        model_name = model or self._get_default_model() or "gemini-2.5-pro"

        # Get model config for default parameters
        model_config = self._get_model_config(model_name)
        if model_config and max_tokens is None:
            max_tokens = model_config.default_params.max_tokens

        try:
            # Extract system message from messages if present
            system_msg = None
            system_cache_control = None
            user_messages = []
            for msg in messages:
                if msg.role == "system":
                    system_msg = msg.content
                    system_cache_control = msg.cache_control
                else:
                    user_messages.append(msg)

            # Use explicit system_instruction parameter if provided, else use extracted system message
            final_system_instruction = system_instruction or system_msg

            # Check if we should use CachedContent API for prompt caching
            cached_content_id = None
            if final_system_instruction and system_cache_control:
                # Create or get CachedContent for the system instruction
                # Extract TTL from cache_control if available (defaults to 3600 seconds)
                ttl_seconds = getattr(system_cache_control, 'ttl_seconds', None) or 3600
                cached_content_id = await self._create_or_get_cached_content(
                    content=final_system_instruction,
                    model_name=model_name,
                    ttl_seconds=ttl_seconds,
                )
                if cached_content_id:
                    self.logger.debug(f"Using CachedContent for prompt caching in streaming: {cached_content_id}")
                    # When using CachedContent, we don't pass system_instruction to GenerativeModel
                    # Instead, we'll pass cached_content_id to generate_content
                    final_system_instruction = None

            # Initialize model WITH system instruction for prompt caching support
            # Note: If using CachedContent, system_instruction will be None
            model_instance = GenerativeModel(
                model_name,
                system_instruction=final_system_instruction
            )
            self.logger.debug(f"Initialized Vertex AI model for streaming: {model_name}")

            # Convert messages to Vertex AI format
            if len(user_messages) == 1 and user_messages[0].role == "user":
                contents = user_messages[0].content
            else:
                # For multi-turn conversations, use proper Content objects
                contents = self._convert_messages_to_contents(user_messages)

            # Use modern GenerationConfig object
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                top_p=0.95,
                top_k=40,
            )

            # Get safety settings from kwargs or use defaults
            if "safety_settings" in kwargs:
                safety_settings = kwargs["safety_settings"]
                if not isinstance(safety_settings, list):
                    raise ValueError("safety_settings must be a list of SafetySetting objects")
            else:
                # Default safety settings
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

            # Prepare tools for Function Calling if provided
            tools_for_api = None
            if tools or functions:
                # Convert OpenAI format to Google format
                tools_list = tools or []
                if functions:
                    # Convert legacy functions format to tools format
                    tools_list = [{"type": "function", "function": func} for func in functions]
                
                google_tools = self._convert_openai_to_google_format(tools_list)
                if google_tools:
                    tools_for_api = google_tools
            
            # Use mixin method for Function Calling support
            from aiecs.llm.clients.openai_compatible_mixin import StreamChunk
            
            # Add cached_content to kwargs if using CachedContent API
            stream_kwargs = kwargs.copy()
            if cached_content_id:
                stream_kwargs["cached_content"] = cached_content_id
                self.logger.debug(f"Added cached_content to streaming API params: {cached_content_id}")
            
            async for chunk in self._stream_text_with_function_calling(
                model_instance=model_instance,
                contents=contents,
                generation_config=generation_config,
                safety_settings=safety_settings,
                tools=tools_for_api,
                return_chunks=return_chunks,
                **stream_kwargs,
            ):
                # Yield chunk (can be str or StreamChunk)
                yield chunk

        except SafetyBlockError:
            # Re-raise safety block errors as-is
            raise
        except Exception as e:
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                raise RateLimitError(f"Vertex AI quota exceeded: {str(e)}")
            self.logger.error(f"Error in Vertex AI streaming: {str(e)}")
            raise

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
