import json
import logging
import os
import hashlib
import base64
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from google import genai
from google.genai import types

from aiecs.llm.utils.image_utils import parse_image_source

logger = logging.getLogger(__name__)

from aiecs.llm.clients.base_client import (  # noqa: E402
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ProviderNotAvailableError,
    RateLimitError,
    SafetyBlockError,
)
from aiecs.llm.clients.google_function_calling_mixin import GoogleFunctionCallingMixin  # noqa: E402
from aiecs.config.config import get_settings  # noqa: E402

# Finish-reason values (as returned by str() on FinishReason in Python 3.11+)
# that indicate the response was blocked or filtered by safety / content policies.
# Extends the old-SDK set of {SAFETY, RECITATION} with values introduced in
# the google-genai SDK: BLOCKLIST, PROHIBITED_CONTENT, SPII, IMAGE_SAFETY,
# IMAGE_PROHIBITED_CONTENT.
_SAFETY_BLOCKING_FINISH_REASONS: frozenset[str] = frozenset(
    {
        "SAFETY",
        "RECITATION",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "IMAGE_SAFETY",
        "IMAGE_PROHIBITED_CONTENT",
    }
)


def _extract_safety_ratings(safety_ratings: Any) -> List[Dict[str, Any]]:
    """
    Extract safety ratings information from Vertex AI response.

    Args:
        safety_ratings: Safety ratings object from Vertex AI response

    Returns:
        List of dictionaries containing safety rating details
    """
    ratings_list: List[Dict[str, Any]] = []
    if not safety_ratings:
        return ratings_list

    # Handle both list and single object
    ratings_iter = safety_ratings if isinstance(safety_ratings, list) else [safety_ratings]

    for rating in ratings_iter:
        if not isinstance(rating, dict) and not hasattr(rating, "category"):
            logger.debug(f"Skipping non-dict/non-object rating element: type={type(rating).__name__}")
            continue
        rating_dict: Dict[str, Any] = {}

        # Extract category
        if hasattr(rating, "category"):
            rating_dict["category"] = str(rating.category)
        elif isinstance(rating, dict):
            rating_dict["category"] = rating.get("category", "UNKNOWN")

        # Extract blocked status
        if hasattr(rating, "blocked"):
            rating_dict["blocked"] = bool(rating.blocked)
        elif isinstance(rating, dict):
            rating_dict["blocked"] = rating.get("blocked", False)

        # Extract severity (for HarmBlockMethod.SEVERITY)
        if hasattr(rating, "severity"):
            rating_dict["severity"] = str(rating.severity)
        elif isinstance(rating, dict):
            rating_dict["severity"] = rating.get("severity")

        if hasattr(rating, "severity_score"):
            rating_dict["severity_score"] = float(rating.severity_score)
        elif isinstance(rating, dict):
            rating_dict["severity_score"] = rating.get("severity_score")

        # Extract probability (for HarmBlockMethod.PROBABILITY)
        if hasattr(rating, "probability"):
            rating_dict["probability"] = str(rating.probability)
        elif isinstance(rating, dict):
            rating_dict["probability"] = rating.get("probability")

        if hasattr(rating, "probability_score"):
            rating_dict["probability_score"] = float(rating.probability_score)
        elif isinstance(rating, dict):
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
            elif isinstance(pf, dict):
                block_reason = pf.get("block_reason")

            if hasattr(pf, "safety_ratings"):
                safety_ratings = _extract_safety_ratings(pf.safety_ratings)
            elif isinstance(pf, dict):
                safety_ratings = _extract_safety_ratings(pf.get("safety_ratings", []))

    elif block_type == "response":
        # Check candidates for response blocks
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "safety_ratings"):
                safety_ratings = _extract_safety_ratings(candidate.safety_ratings)
            elif isinstance(candidate, dict):
                safety_ratings = _extract_safety_ratings(candidate.get("safety_ratings", []))

            # Check finish_reason against all blocking values defined by the
            # new google-genai SDK (supersedes old {SAFETY, RECITATION} pair).
            if hasattr(candidate, "finish_reason"):
                finish_reason = str(candidate.finish_reason)
                if finish_reason in _SAFETY_BLOCKING_FINISH_REASONS:
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
                error_parts.append(f"{rating.get('category', 'UNKNOWN')}: severity={rating.get('severity')}, " f"score={rating.get('severity_score', 'N/A')}")
            elif "probability" in rating:
                error_parts.append(f"{rating.get('category', 'UNKNOWN')}: probability={rating.get('probability')}, " f"score={rating.get('probability_score', 'N/A')}")

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
        self._client: Optional[genai.Client] = None
        # Track part count statistics for monitoring
        self._part_count_stats: Dict[str, Any] = {
            "total_responses": 0,
            "part_counts": {},  # {part_count: frequency}
            "last_part_count": None,
        }
        # Cache for CachedContent objects (key: content hash, value: cached_content_id)
        self._cached_content_cache: Dict[str, str] = {}

    def _init_client(self) -> genai.Client:
        """Lazy initialization of Vertex AI genai.Client with proper authentication"""
        if not self._initialized or self._client is None:
            if not self.settings.vertex_project_id:
                raise ProviderNotAvailableError("Vertex AI project ID not configured")

            try:
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

                # Initialize the google-genai client for Vertex AI
                self._client = genai.Client(
                    vertexai=True,
                    project=self.settings.vertex_project_id,
                    location=getattr(self.settings, "vertex_location", "us-central1"),
                )
                self._initialized = True
                self.logger.info(f"Vertex AI (google-genai) initialized for project {self.settings.vertex_project_id}")

            except Exception as e:
                raise ProviderNotAvailableError(f"Failed to initialize Vertex AI: {str(e)}")

        return self._client

    def _generate_content_hash(self, content: str, tools: Optional[List[Any]] = None) -> str:
        """Generate a hash for content and tools to use as cache key."""
        hash_input = content
        if tools:
            # Include tools in the hash so different tool configurations get different cached contents
            import json

            tools_str = json.dumps([str(t) for t in tools], sort_keys=True)
            hash_input = f"{content}|tools:{tools_str}"
        return hashlib.md5(hash_input.encode("utf-8")).hexdigest()

    async def _create_or_get_cached_content(
        self,
        content: str,
        model_name: str,
        ttl_seconds: Optional[int] = None,
        tools: Optional[List[Any]] = None,
    ) -> Optional[str]:
        """
        Create or get a CachedContent for the given system instruction and tools.

        Uses the new google-genai SDK (`self._client.aio.caches.create`) to create
        a server-side cache entry.  The system instruction is stored via the
        `system_instruction` field of `CreateCachedContentConfig`; tools (if any)
        are included in the same cache object so that a single cached_content ID
        covers both.

        Args:
            content: System instruction text to cache
            model_name: Model name to use for caching (e.g. "gemini-2.5-pro")
            ttl_seconds: Time-to-live in seconds (defaults to 3600)
            tools: Optional list of types.Tool objects to include in the cache

        Returns:
            CachedContent resource name string, or None if caching fails
        """
        if not content or not content.strip():
            return None

        # Generate cache key (includes tools so different tool configs get separate caches)
        cache_key = self._generate_content_hash(content, tools)

        # Return existing cache entry if present
        if cache_key in self._cached_content_cache:
            existing_cached_id = self._cached_content_cache[cache_key]
            self.logger.debug(f"Using existing CachedContent: {existing_cached_id}")
            return existing_cached_id

        try:
            client = self._init_client()

            if tools:
                self.logger.debug(f"Including {len(tools)} tools in cached content")

            cache = await client.aio.caches.create(
                model=model_name,
                config=types.CreateCachedContentConfig(
                    system_instruction=content,
                    ttl=f"{ttl_seconds or 3600}s",
                    tools=tools,
                ),
            )

            cached_content_id: Optional[str] = cache.name
            if cached_content_id:
                self._cached_content_cache[cache_key] = cached_content_id
                self.logger.info(f"Created CachedContent for prompt caching: {cached_content_id}")
            return cached_content_id

        except Exception as e:
            self.logger.warning(f"Failed to create CachedContent (prompt caching disabled, " f"falling back to system_instruction): {str(e)}")
            return None

    def _convert_messages_to_contents(self, messages: List[LLMMessage]) -> List[types.Content]:
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

        # Maps tool_call_id -> function declaration name, built from each assistant turn.
        # Used so that FunctionResponse.name matches the function declaration name
        # (e.g. "create_file") instead of the opaque call id (e.g. "call_0").
        tool_call_id_to_name: Dict[str, str] = {}

        # Accumulates FunctionResponse parts belonging to the *current* tool turn.
        # Vertex AI requires that all responses for one model-function-call turn are
        # grouped into a SINGLE user Content with N parts, not N separate Contents.
        pending_tool_parts: List = []

        def _flush_pending_tool_parts() -> None:
            """Emit accumulated FunctionResponse parts as one user Content."""
            if pending_tool_parts:
                contents.append(types.Content(role="user", parts=list(pending_tool_parts)))
                pending_tool_parts.clear()

        for msg in messages:
            # ------------------------------------------------------------------
            # Tool / function response messages
            # ------------------------------------------------------------------
            if msg.role == "tool":
                # Resolve the function *declaration* name from the mapping built
                # when the preceding assistant turn was processed.
                func_name = tool_call_id_to_name.get(msg.tool_call_id or "") or msg.tool_call_id or "unknown_function"

                # Parse content as the function response payload
                try:
                    if msg.content and msg.content.strip().startswith("{"):
                        response_data = json.loads(msg.content)
                    else:
                        response_data = {"result": msg.content}
                except json.JSONDecodeError:
                    response_data = {"result": msg.content}

                func_response_part = types.Part.from_function_response(
                    name=func_name,
                    response=response_data,
                )
                # Accumulate – do NOT append a new Content yet.
                pending_tool_parts.append(func_response_part)

            # ------------------------------------------------------------------
            # Assistant messages that carry tool / function calls
            # ------------------------------------------------------------------
            elif msg.role == "assistant" and msg.tool_calls:
                # A new model turn starts – flush any tool responses from the
                # previous turn first (handles back-to-back function calling rounds).
                _flush_pending_tool_parts()

                sanitized_tool_calls = self._sanitize_tool_calls(msg.tool_calls)

                # Build / update the id→name mapping for the upcoming tool turn.
                if sanitized_tool_calls:
                    for tool_call in sanitized_tool_calls:
                        call_id = tool_call.get("id", "")
                        fname = (tool_call.get("function") or {}).get("name", "")
                        if call_id:
                            tool_call_id_to_name[call_id] = fname

                parts = []
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))

                # Add images if present
                if msg.images:
                    for image_source in msg.images:
                        image_content = parse_image_source(image_source)
                        if image_content.is_url():
                            parts.append(
                                types.Part.from_uri(
                                    file_uri=image_content.get_url(),
                                    mime_type=image_content.mime_type,
                                )
                            )
                        else:
                            base64_data = image_content.get_base64_data()
                            image_bytes = base64.b64decode(base64_data)
                            parts.append(
                                types.Part.from_bytes(
                                    data=image_bytes,
                                    mime_type=image_content.mime_type,
                                )
                            )

                if sanitized_tool_calls:
                    for tool_call in sanitized_tool_calls:
                        func = tool_call.get("function") or {}
                        func_name = func.get("name", "")
                        func_args = func.get("arguments", "{}")
                        try:
                            args_dict = json.loads(func_args) if isinstance(func_args, str) else func_args
                        except json.JSONDecodeError:
                            args_dict = {}
                        # Create FunctionCall part using types.Part + types.FunctionCall
                        # (Part.from_dict is deprecated in the new SDK)
                        function_call_part = types.Part(function_call=types.FunctionCall(name=func_name, args=args_dict))
                        parts.append(function_call_part)

                contents.append(types.Content(role="model", parts=parts))

            # ------------------------------------------------------------------
            # Regular messages (user text, assistant without tool calls, etc.)
            # ------------------------------------------------------------------
            else:
                # Encountering a non-tool message ends the current tool-response
                # accumulation window – flush before processing this message.
                _flush_pending_tool_parts()

                role = "model" if msg.role == "assistant" else msg.role
                parts = []

                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))

                if msg.images:
                    for image_source in msg.images:
                        image_content = parse_image_source(image_source)
                        if image_content.is_url():
                            parts.append(
                                types.Part.from_uri(
                                    file_uri=image_content.get_url(),
                                    mime_type=image_content.mime_type,
                                )
                            )
                        else:
                            base64_data = image_content.get_base64_data()
                            image_bytes = base64.b64decode(base64_data)
                            parts.append(
                                types.Part.from_bytes(
                                    data=image_bytes,
                                    mime_type=image_content.mime_type,
                                )
                            )

                if parts:
                    contents.append(types.Content(role=role, parts=parts))

        # Flush any tool responses that are still pending at the end of the loop
        # (e.g. the conversation ends right after tool execution).
        _flush_pending_tool_parts()

        return contents

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text using Vertex AI.

        Args:
            messages: List of conversation messages
            model: Model name (optional, uses default if not provided)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            context: Optional context dictionary containing metadata such as:
                - user_id: User identifier for tracking/billing
                - tenant_id: Tenant identifier for multi-tenant setups
                - request_id: Request identifier for tracing
                - session_id: Session identifier
                - Any other custom metadata for observability or middleware
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format, recommended)
            tool_choice: Tool choice strategy
            system_instruction: System instruction for the model
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        client = self._init_client()

        # Get model name from config if not provided
        model_name = model or self._get_default_model() or "gemini-2.5-pro"

        # Get model config for default parameters
        model_config = self._get_model_config(model_name)
        if model_config and max_tokens is None:
            max_tokens = model_config.default_params.max_tokens

        try:
            # Extract system messages from messages if present
            # AIECS 1.9.8: Support multiple system messages with selective caching
            # - Messages with cache_control=True → cached as system_instruction
            # - Messages without cache_control or cache_control=False → prepended to user messages
            cached_system_msgs = []
            non_cached_system_msgs = []
            system_cache_control = None
            user_messages = []

            for msg in messages:
                if msg.role == "system":
                    if msg.content:
                        # Check if this message should be cached
                        if msg.cache_control:
                            cached_system_msgs.append(msg.content)
                            if system_cache_control is None:
                                system_cache_control = msg.cache_control
                        else:
                            non_cached_system_msgs.append(msg.content)
                else:
                    user_messages.append(msg)

            # Cached system messages become the system_instruction
            system_msg = "\n\n".join(cached_system_msgs) if cached_system_msgs else None

            # Non-cached system messages are prepended as a user message
            if non_cached_system_msgs:
                non_cached_content = "\n\n".join(non_cached_system_msgs)
                # Create a new LLMMessage and prepend to user_messages
                user_messages.insert(0, LLMMessage(role="user", content=f"[System Context]\n{non_cached_content}"))
                self.logger.debug(f"[AIECS 1.9.8] Prepended {len(non_cached_system_msgs)} non-cached system message(s) to user messages")

            # Use explicit system_instruction parameter if provided, else use extracted system message
            final_system_instruction = system_instruction or system_msg

            # Prepare tools for Function Calling BEFORE cached content creation
            # so tools can be included in the cached content
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

            # Check if we should use CachedContent API for prompt caching
            cached_content_id = None
            if final_system_instruction and system_cache_control:
                # Create or get CachedContent for the system instruction (and tools if provided)
                # Extract TTL from cache_control if available (defaults to 3600 seconds)
                ttl_seconds = getattr(system_cache_control, "ttl_seconds", None) or 3600
                cached_content_id = await self._create_or_get_cached_content(
                    content=final_system_instruction,
                    model_name=model_name,
                    ttl_seconds=ttl_seconds,
                    tools=tools_for_api,
                )

            # Convert messages to Vertex AI format
            contents: Union[str, List[types.Content]]
            if len(user_messages) == 1 and user_messages[0].role == "user":
                contents = user_messages[0].content or ""
            else:
                # For multi-turn conversations, use proper Content objects
                contents = self._convert_messages_to_contents(user_messages)

            # Build safety settings — allow override via kwargs
            if "safety_settings" in kwargs:
                safety_settings = kwargs.pop("safety_settings")
                if not isinstance(safety_settings, list):
                    raise ValueError("safety_settings must be a list of SafetySetting objects")
            else:
                safety_settings = [
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                ]

            # Build unified GenerateContentConfig.
            # When cached_content is set, system_instruction and tools must be omitted
            # because they are already baked into the cached content object.
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                top_p=kwargs.pop("top_p", 0.95),
                top_k=kwargs.pop("top_k", 40),
                system_instruction=final_system_instruction if not cached_content_id else None,
                tools=tools_for_api if not cached_content_id else None,  # type: ignore[arg-type]
                cached_content=cached_content_id,
                safety_settings=safety_settings,
            )

            if cached_content_id:
                self.logger.debug(f"Using CachedContent for prompt caching: {cached_content_id}")

            response = await client.aio.models.generate_content(
                model=model_name,
                contents=contents,  # type: ignore[arg-type]
                config=config,
            )

            # Check for prompt-level safety blocks first
            if hasattr(response, "prompt_feedback"):
                pf = response.prompt_feedback
                # Check if prompt was blocked
                if pf is not None and hasattr(pf, "block_reason") and pf.block_reason:
                    block_reason = str(pf.block_reason)
                    if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER"]:
                        # Prompt was blocked by safety filters
                        raise _build_safety_block_error(
                            response,
                            block_type="prompt",
                            default_message="Prompt blocked by safety filters",
                        )
                elif isinstance(pf, dict) and pf.get("block_reason"):
                    block_reason = str(pf.get("block_reason", ""))
                    if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER", ""]:
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
                content = response.text or ""
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
                    if hasattr(candidate, "content") and candidate.content is not None and hasattr(candidate.content, "parts"):
                        try:
                            # Extract text from all parts
                            text_parts: List[str] = []
                            for part in candidate.content.parts or []:
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

                                        if "<thinking>" in part_str and "</thinking>" not in part_str:
                                            # Incomplete <thinking> tag: add
                                            # closing tag
                                            part_str = part_str + "\n</thinking>"
                                            needs_thinking_format = True
                                            self.logger.debug(f"  Part {i+1}: Incomplete <thinking> tag fixed")
                                        elif isinstance(part_str, str) and part_str.startswith("thinking") and "</thinking>" not in part_str:
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
                        if pf is not None and hasattr(pf, "block_reason") and pf.block_reason:
                            block_reason = str(pf.block_reason)
                            if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER"]:
                                raise _build_safety_block_error(
                                    response,
                                    block_type="prompt",
                                    default_message="No candidates found - prompt blocked by safety filters",
                                )
                        elif isinstance(pf, dict) and pf.get("block_reason"):
                            block_reason = str(pf.get("block_reason", ""))
                            if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER", ""]:
                                raise _build_safety_block_error(
                                    response,
                                    block_type="prompt",
                                    default_message="No candidates found - prompt blocked by safety filters",
                                )

                    # If not a safety block, raise generic error with details
                    error_msg = "Response error: No candidates found - Response has no candidates (and thus no text)."
                    if hasattr(response, "prompt_feedback"):
                        error_msg += " Check prompt_feedback for details."
                    raise ValueError(error_msg)

                # Final fallback
                if not content:
                    content = "[Response error: Cannot get the response text. Multiple content parts are not supported.]"

            # Extract actual token usage from response.usage_metadata
            prompt_tokens = 0
            completion_tokens = 0
            tokens_used = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = response.usage_metadata
                prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
                completion_tokens = getattr(usage, "candidates_token_count", 0) or 0
                tokens_used = getattr(usage, "total_token_count", 0) or (prompt_tokens + completion_tokens)
            else:
                # Fallback estimation if usage_metadata is unavailable
                prompt_text = " ".join(msg.content for msg in messages if msg.content)
                prompt_tokens = self._count_tokens_estimate(prompt_text)
                completion_tokens = self._count_tokens_estimate(content or "")
                tokens_used = prompt_tokens + completion_tokens

            # Extract cache metadata from response
            cache_read_tokens = None
            cache_hit = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = response.usage_metadata
                if hasattr(usage, "cached_content_token_count"):
                    cache_read_tokens = usage.cached_content_token_count
                    cache_hit = cache_read_tokens is not None and cache_read_tokens > 0

            # Use config-based cost estimation
            cost = self._estimate_cost_from_config(model_name, prompt_tokens, completion_tokens)

            # Extract function calls from response if present
            function_calls = self._extract_function_calls_from_google_response(response)

            llm_response = LLMResponse(
                content=content or "",
                provider=self.provider_name,
                model=model_name,
                tokens_used=tokens_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
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
        context: Optional[Dict[str, Any]] = None,
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
            context: Optional context dictionary containing metadata such as:
                - user_id: User identifier for tracking/billing
                - tenant_id: Tenant identifier for multi-tenant setups
                - request_id: Request identifier for tracing
                - session_id: Session identifier
                - Any other custom metadata for observability or middleware
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format)
            tool_choice: Tool choice strategy (not used for Google Vertex AI)
            return_chunks: If True, returns GoogleStreamChunk objects; if False, returns str tokens only
            system_instruction: System instruction for prompt caching support
            **kwargs: Additional arguments

        Yields:
            str or GoogleStreamChunk: Text tokens or StreamChunk objects
        """
        client = self._init_client()

        # Get model name from config if not provided
        model_name = model or self._get_default_model() or "gemini-2.5-pro"

        # Get model config for default parameters
        model_config = self._get_model_config(model_name)
        if model_config and max_tokens is None:
            max_tokens = model_config.default_params.max_tokens

        try:
            # Extract system messages from messages if present
            # AIECS 1.9.8: Support multiple system messages with selective caching
            # - Messages with cache_control=True → cached as system_instruction
            # - Messages without cache_control or cache_control=False → prepended to user messages
            cached_system_msgs = []
            non_cached_system_msgs = []
            system_cache_control = None
            user_messages = []

            for msg in messages:
                if msg.role == "system":
                    if msg.content:
                        # Check if this message should be cached
                        if msg.cache_control:
                            cached_system_msgs.append(msg.content)
                            if system_cache_control is None:
                                system_cache_control = msg.cache_control
                        else:
                            non_cached_system_msgs.append(msg.content)
                else:
                    user_messages.append(msg)

            # Cached system messages become the system_instruction
            system_msg = "\n\n".join(cached_system_msgs) if cached_system_msgs else None

            # Non-cached system messages are prepended as a user message
            if non_cached_system_msgs:
                non_cached_content = "\n\n".join(non_cached_system_msgs)
                # Create a new LLMMessage and prepend to user_messages
                user_messages.insert(0, LLMMessage(role="user", content=f"[System Context]\n{non_cached_content}"))
                self.logger.debug(f"[AIECS 1.9.8] Prepended {len(non_cached_system_msgs)} non-cached system message(s) to user messages")

            # DEBUG: Log system message handling
            self.logger.debug(f"[DEBUG vertex stream_text] Cached system msgs: {len(cached_system_msgs)}, Non-cached: {len(non_cached_system_msgs)}")
            if system_msg:
                self.logger.debug(f"[DEBUG vertex stream_text] Cached system_msg preview: {system_msg[:200]}...")

            # Use explicit system_instruction parameter if provided, else use extracted system message
            final_system_instruction = system_instruction or system_msg

            # Prepare tools for Function Calling BEFORE cached content creation
            # so tools can be included in the cached content
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

            # Check if we should use CachedContent API for prompt caching
            cached_content_id = None
            if final_system_instruction and system_cache_control:
                # Create or get CachedContent for the system instruction (and tools if provided)
                # Extract TTL from cache_control if available (defaults to 3600 seconds)
                ttl_seconds = getattr(system_cache_control, "ttl_seconds", None) or 3600
                cached_content_id = await self._create_or_get_cached_content(
                    content=final_system_instruction,
                    model_name=model_name,
                    ttl_seconds=ttl_seconds,
                    tools=tools_for_api,
                )

            # Convert messages to Vertex AI format
            stream_contents: Union[str, List[types.Content]]
            if len(user_messages) == 1 and user_messages[0].role == "user":
                stream_contents = user_messages[0].content or ""
            else:
                # For multi-turn conversations, use proper Content objects
                stream_contents = self._convert_messages_to_contents(user_messages)

            # Build safety settings — allow override via kwargs
            if "safety_settings" in kwargs:
                safety_settings = kwargs.pop("safety_settings")
                if not isinstance(safety_settings, list):
                    raise ValueError("safety_settings must be a list of SafetySetting objects")
            else:
                safety_settings = [
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                ]

            # Build unified GenerateContentConfig.
            # When cached_content is set, system_instruction and tools must be omitted
            # because they are already baked into the cached content object.
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                top_p=kwargs.pop("top_p", 0.95),
                top_k=kwargs.pop("top_k", 40),
                system_instruction=final_system_instruction if not cached_content_id else None,
                tools=tools_for_api if not cached_content_id else None,  # type: ignore[arg-type]
                cached_content=cached_content_id,
                safety_settings=safety_settings,
            )

            if cached_content_id:
                self.logger.debug(f"Using CachedContent for prompt caching in streaming: {cached_content_id}")

            async for chunk in self._stream_text_with_function_calling(
                client=client,
                model_name=model_name,
                contents=stream_contents,
                config=config,
                return_chunks=return_chunks,
            ):
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
        Generate embeddings using Vertex AI embedding model.

        Passes all texts in a single batched call to
        ``self._client.aio.models.embed_content``, which maps to the
        Vertex AI ``{model}:predict`` endpoint internally.

        Args:
            texts: List of texts to embed
            model: Embedding model name (default: gemini-embedding-001)

        Returns:
            List of embedding vectors (each is a list of floats)
        """
        client = self._init_client()

        embedding_model_name = model or "gemini-embedding-001"

        try:
            result = await client.aio.models.embed_content(
                model=embedding_model_name,
                contents=texts,  # type: ignore[arg-type]
            )

            embeddings = []
            for emb in result.embeddings or []:
                embeddings.append(list(emb.values or []))

            return embeddings

        except Exception as e:
            self.logger.error(f"Error generating embeddings with Vertex AI: {e}")
            # Return zero vectors as fallback so callers don't crash
            return [[0.0] * 768 for _ in texts]

    async def close(self):
        """Clean up resources"""
        # Log final statistics before cleanup
        self.log_part_count_summary()
        self._initialized = False
        self._client = None
