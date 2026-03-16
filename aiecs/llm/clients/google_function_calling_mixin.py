"""
Google Function Calling Mixin

Provides shared implementation for Google providers (Vertex AI, Google AI)
that use FunctionDeclaration format for Function Calling.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from dataclasses import dataclass
from google import genai
from google.genai import types
from .base_client import LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

# Finish-reason values that indicate the response was blocked / filtered.
# Mirrors the constant in vertex_client.py and covers all blocking values
# introduced in the google-genai SDK beyond the original {SAFETY, RECITATION}.
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

# Import StreamChunk from OpenAI mixin for compatibility
try:
    from .openai_compatible_mixin import StreamChunk
except ImportError:
    # Fallback if not available
    @dataclass
    class StreamChunk:  # type: ignore[no-redef]
        """Fallback StreamChunk definition"""

        type: str
        content: Optional[str] = None
        tool_call: Optional[Dict[str, Any]] = None
        tool_calls: Optional[List[Dict[str, Any]]] = None


def _serialize_function_args(args) -> str:
    """
    Safely serialize function call arguments to JSON string.

    Handles MapComposite/protobuf objects from Vertex AI by converting
    them to regular dicts before JSON serialization.

    Args:
        args: Function call arguments (may be MapComposite, dict, or other)

    Returns:
        JSON string representation of the arguments
    """
    if args is None:
        return "{}"

    # Handle MapComposite/protobuf objects (they have items() method)
    if hasattr(args, "items"):
        # Convert to regular dict
        args_dict = dict(args)
    elif isinstance(args, dict):
        args_dict = args
    else:
        # Try to convert to dict if possible
        try:
            args_dict = dict(args)
        except (TypeError, ValueError):
            # Last resort: use str() but this should rarely happen
            return str(args)

    return json.dumps(args_dict, ensure_ascii=False)


class GoogleFunctionCallingMixin:
    """
    Mixin class providing Google Function Calling implementation.

    This mixin can be used by Google providers (Vertex AI, Google AI)
    that use FunctionDeclaration format for Function Calling.

    Usage:
        class VertexAIClient(BaseLLMClient, GoogleFunctionCallingMixin):
            async def generate_text(self, messages, tools=None, ...):
                if tools:
                    vertex_tools = self._convert_openai_to_google_format(tools)
                    # Use in API call
    """

    def _sanitize_tools(self, tools: Optional[List[Any]]) -> List[Dict[str, Any]]:
        """Provided by BaseLLMClient; declared here for mypy's benefit."""
        raise NotImplementedError  # pragma: no cover

    def _convert_openai_to_google_format(self, tools: List[Dict[str, Any]]) -> List[types.Tool]:
        """
        Convert OpenAI tools format to Google FunctionDeclaration format.

        Args:
            tools: List of OpenAI-format tool dictionaries

        Returns:
            List of Google Tool objects containing FunctionDeclaration
        """
        function_declarations = []
        sanitized_tools = self._sanitize_tools(tools)

        for tool_dict in sanitized_tools:
            func = tool_dict.get("function") or {}
            func_name = func.get("name", "")
            func_description = func.get("description", "")
            func_parameters = func.get("parameters", {})

            if not func_name:
                logger.warning(f"Skipping tool without name: {tool_dict}")
                continue

            # Create FunctionDeclaration with raw dict parameters
            # The new SDK coerces dict → Schema via pydantic automatically
            function_declaration = types.FunctionDeclaration(
                name=func_name,
                description=func_description,
                parameters=func_parameters,
            )

            function_declarations.append(function_declaration)

        # Wrap in Tool objects (Google format requires tools to be wrapped)
        if function_declarations:
            return [types.Tool(function_declarations=function_declarations)]
        return []

    def _extract_function_calls_from_google_response(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Extract function calls from Google Vertex AI response.

        Args:
            response: Response object from Google Vertex AI API

        Returns:
            List of function call dictionaries in OpenAI-compatible format,
            or None if no function calls found
        """
        function_calls: List[Dict[str, Any]] = []

        # In the google-genai SDK, Candidate no longer exposes a top-level
        # function_call attribute.  Function calls are always inside
        # candidate.content.parts as Part.function_call objects.
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]

            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        func_call = part.function_call
                        # Prefer the SDK-assigned id; fall back to a synthetic one.
                        call_id = func_call.id if hasattr(func_call, "id") and func_call.id else f"call_{len(function_calls)}"
                        function_calls.append(
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": func_call.name,
                                    "arguments": _serialize_function_args(func_call.args) if hasattr(func_call, "args") else "{}",
                                },
                            }
                        )

        return function_calls if function_calls else None

    def _attach_function_calls_to_response(
        self,
        response: LLMResponse,
        function_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Attach function call information to LLMResponse.

        Args:
            response: LLMResponse object
            function_calls: List of function call dictionaries

        Returns:
            LLMResponse with function call info attached
        """
        if function_calls:
            setattr(response, "tool_calls", function_calls)
        return response

    def _convert_messages_to_google_format(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """
        Convert LLMMessage list to Google message format.

        Args:
            messages: List of LLMMessage objects

        Returns:
            List of Google-format message dictionaries
        """
        google_messages = []

        for msg in messages:
            # Google format uses "role" and "parts" structure
            parts: List[Dict[str, Any]] = []

            if msg.content:
                parts.append({"text": msg.content})

            # Handle tool responses (role="tool")
            if msg.role == "tool" and msg.tool_call_id:
                # Google format uses function_response
                # Note: This may need adjustment based on actual API format
                if msg.content:
                    parts.append(
                        {
                            "function_response": {
                                "name": msg.tool_call_id,  # May need mapping
                                "response": {"result": msg.content},
                            }
                        }
                    )

            if parts:
                google_messages.append(
                    {
                        "role": msg.role if msg.role != "tool" else "model",  # Adjust role mapping
                        "parts": parts,
                    }
                )

        return google_messages

    def _extract_function_calls_from_google_chunk(self, chunk: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Extract function calls from Google Vertex AI streaming chunk.

        Args:
            chunk: Streaming chunk object from Google Vertex AI API

        Returns:
            List of function call dictionaries in OpenAI-compatible format,
            or None if no function calls found
        """
        function_calls: List[Dict[str, Any]] = []

        # In the google-genai SDK, Candidate no longer exposes a top-level
        # function_call attribute.  Function calls are always inside
        # candidate.content.parts as Part.function_call objects.
        if hasattr(chunk, "candidates") and chunk.candidates:
            candidate = chunk.candidates[0]

            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        func_call = part.function_call
                        # Prefer the SDK-assigned id; fall back to a synthetic one.
                        call_id = func_call.id if hasattr(func_call, "id") and func_call.id else f"call_{len(function_calls)}"
                        function_calls.append(
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": func_call.name,
                                    "arguments": _serialize_function_args(func_call.args) if hasattr(func_call, "args") else "{}",
                                },
                            }
                        )

        return function_calls if function_calls else None

    async def _stream_text_with_function_calling(
        self,
        client: genai.Client,
        model_name: str,
        contents: Any,
        config: types.GenerateContentConfig,
        return_chunks: bool = False,
        **kwargs,
    ) -> AsyncGenerator[Union[str, StreamChunk], None]:
        """
        Stream text with Function Calling support (Google Vertex AI format).

        Args:
            client: genai.Client instance
            model_name: Model name string
            contents: Input contents (string or list of Content objects)
            config: GenerateContentConfig with all settings (system_instruction,
                    safety_settings, tools, cached_content, etc.) already merged in
            return_chunks: If True, returns StreamChunk objects; if False, returns str tokens only
            **kwargs: Additional arguments (currently unused)

        Yields:
            str or StreamChunk: Text tokens or StreamChunk objects
        """
        # Accumulator for tool calls
        tool_calls_accumulator: Dict[str, Dict[str, Any]] = {}

        first_chunk_checked = False

        async for chunk in await client.aio.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        ):
            # Check for prompt-level safety blocks
            if not first_chunk_checked and hasattr(chunk, "prompt_feedback"):
                pf = chunk.prompt_feedback
                if pf is not None and hasattr(pf, "block_reason") and pf.block_reason:
                    block_reason = str(pf.block_reason)
                    if block_reason not in ["BLOCKED_REASON_UNSPECIFIED", "OTHER"]:
                        from .base_client import SafetyBlockError

                        raise SafetyBlockError(
                            "Prompt blocked by safety filters",
                            block_reason=block_reason,
                            block_type="prompt",
                        )
                first_chunk_checked = True

            # Extract text content and function calls
            if hasattr(chunk, "candidates") and chunk.candidates:
                candidate = chunk.candidates[0]

                # Check for safety/content-policy blocks in response.
                # Uses the full set of blocking FinishReason values from the
                # new google-genai SDK (SAFETY, RECITATION, BLOCKLIST,
                # PROHIBITED_CONTENT, SPII, IMAGE_SAFETY, IMAGE_PROHIBITED_CONTENT).
                if hasattr(candidate, "finish_reason") and candidate.finish_reason:
                    finish_reason = str(candidate.finish_reason)
                    if finish_reason in _SAFETY_BLOCKING_FINISH_REASONS:
                        from .base_client import SafetyBlockError

                        raise SafetyBlockError(
                            f"Response blocked by safety filters ({finish_reason})",
                            block_reason=finish_reason,
                            block_type="response",
                        )

                # Extract text from chunk parts
                if hasattr(candidate, "content") and candidate.content is not None and candidate.content.parts is not None:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            text_content = part.text
                            if return_chunks:
                                yield StreamChunk(type="token", content=text_content)
                            else:
                                yield text_content

                # Also check if text is directly available
                elif hasattr(candidate, "text") and candidate.text:
                    text_content = candidate.text
                    if return_chunks:
                        yield StreamChunk(type="token", content=text_content)
                    else:
                        yield text_content

                # Extract and accumulate function calls
                function_calls = self._extract_function_calls_from_google_chunk(chunk)
                if function_calls:
                    for func_call in function_calls:
                        if not isinstance(func_call, dict):
                            logger.warning(f"Skipping non-dict func_call (type={type(func_call).__name__})")
                            continue
                        call_id = func_call.get("id")
                        if call_id is None:
                            continue
                        _raw_func_data = func_call.get("function")
                        func_data: Dict[str, Any] = _raw_func_data if isinstance(_raw_func_data, dict) else {}
                        # Initialize accumulator if needed
                        if call_id not in tool_calls_accumulator:
                            tool_calls_accumulator[call_id] = {
                                "id": call_id,
                                "type": func_call.get("type", "function"),
                                "function": func_data or {"name": "", "arguments": "{}"},
                            }
                        else:
                            # Update accumulator (merge arguments if needed)
                            existing_call = tool_calls_accumulator[call_id]
                            existing_func = existing_call.get("function")
                            if not isinstance(existing_func, dict):
                                existing_call["function"] = func_data or {
                                    "name": "",
                                    "arguments": "{}",
                                }
                            else:
                                if func_data.get("name"):
                                    existing_call["function"]["name"] = func_data["name"]
                                if func_data.get("arguments"):
                                    new_args = func_data["arguments"]
                                    if new_args and new_args != "{}":
                                        existing_call["function"]["arguments"] = new_args

                        # Yield tool call update if return_chunks=True
                        if return_chunks:
                            yield StreamChunk(
                                type="tool_call",
                                tool_call=tool_calls_accumulator[call_id].copy(),
                            )

        # At the end of stream, yield complete tool_calls if any
        if tool_calls_accumulator and return_chunks:
            complete_tool_calls = list(tool_calls_accumulator.values())
            yield StreamChunk(
                type="tool_calls",
                tool_calls=complete_tool_calls,
            )
