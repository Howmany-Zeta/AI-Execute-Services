"""
Google Function Calling Mixin

Provides shared implementation for Google providers (Vertex AI, Google AI)
that use FunctionDeclaration format for Function Calling.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from dataclasses import dataclass
from vertexai.generative_models import (
    FunctionDeclaration,
    Tool,
)
from .base_client import LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

# Import StreamChunk from OpenAI mixin for compatibility
try:
    from .openai_compatible_mixin import StreamChunk
except ImportError:
    # Fallback if not available
    @dataclass
    class StreamChunk:
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
    if hasattr(args, 'items'):
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

    def _convert_openai_to_google_format(
        self, tools: List[Dict[str, Any]]
    ) -> List[Tool]:
        """
        Convert OpenAI tools format to Google FunctionDeclaration format.
        
        Args:
            tools: List of OpenAI-format tool dictionaries
            
        Returns:
            List of Google Tool objects containing FunctionDeclaration
        """
        function_declarations = []
        
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                func_name = func.get("name", "")
                func_description = func.get("description", "")
                func_parameters = func.get("parameters", {})
                
                if not func_name:
                    logger.warning(f"Skipping tool without name: {tool}")
                    continue

                # Create FunctionDeclaration with raw dict parameters
                # Let Vertex SDK handle the schema conversion internally
                function_declaration = FunctionDeclaration(
                    name=func_name,
                    description=func_description,
                    parameters=func_parameters,
                )
                
                function_declarations.append(function_declaration)
            else:
                logger.warning(f"Unsupported tool type: {tool.get('type')}")
        
        # Wrap in Tool objects (Google format requires tools to be wrapped)
        if function_declarations:
            return [Tool(function_declarations=function_declarations)]
        return []

    def _extract_function_calls_from_google_response(
        self, response: Any
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extract function calls from Google Vertex AI response.
        
        Args:
            response: Response object from Google Vertex AI API
            
        Returns:
            List of function call dictionaries in OpenAI-compatible format,
            or None if no function calls found
        """
        function_calls = []
        
        # Check for function calls in response
        # Google Vertex AI returns function calls in different places depending on API version
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            
            # Check for function_call attribute (older API)
            if hasattr(candidate, "function_call") and candidate.function_call:
                func_call = candidate.function_call
                function_calls.append({
                    "id": f"call_{len(function_calls)}",
                    "type": "function",
                    "function": {
                        "name": func_call.name,
                        "arguments": _serialize_function_args(func_call.args) if hasattr(func_call, "args") else "{}",
                    },
                })

            # Check for content.parts with function_call (newer API)
            elif hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        func_call = part.function_call
                        function_calls.append({
                            "id": f"call_{len(function_calls)}",
                            "type": "function",
                            "function": {
                                "name": func_call.name,
                                "arguments": _serialize_function_args(func_call.args) if hasattr(func_call, "args") else "{}",
                            },
                        })
        
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

    def _convert_messages_to_google_format(
        self, messages: List[LLMMessage]
    ) -> List[Dict[str, Any]]:
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
            parts = []
            
            if msg.content:
                parts.append({"text": msg.content})
            
            # Handle tool responses (role="tool")
            if msg.role == "tool" and msg.tool_call_id:
                # Google format uses function_response
                # Note: This may need adjustment based on actual API format
                if msg.content:
                    parts.append({
                        "function_response": {
                            "name": msg.tool_call_id,  # May need mapping
                            "response": {"result": msg.content},
                        }
                    })
            
            if parts:
                google_messages.append({
                    "role": msg.role if msg.role != "tool" else "model",  # Adjust role mapping
                    "parts": parts,
                })
        
        return google_messages

    def _extract_function_calls_from_google_chunk(
        self, chunk: Any
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extract function calls from Google Vertex AI streaming chunk.
        
        Args:
            chunk: Streaming chunk object from Google Vertex AI API
            
        Returns:
            List of function call dictionaries in OpenAI-compatible format,
            or None if no function calls found
        """
        function_calls = []
        
        # Check for function calls in chunk
        if hasattr(chunk, "candidates") and chunk.candidates:
            candidate = chunk.candidates[0]
            
            # Check for content.parts with function_call
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        func_call = part.function_call
                        function_calls.append({
                            "id": f"call_{len(function_calls)}",
                            "type": "function",
                            "function": {
                                "name": func_call.name,
                                "arguments": _serialize_function_args(func_call.args) if hasattr(func_call, "args") else "{}",
                            },
                        })

            # Check for function_call attribute directly on candidate
            elif hasattr(candidate, "function_call") and candidate.function_call:
                func_call = candidate.function_call
                function_calls.append({
                    "id": f"call_{len(function_calls)}",
                    "type": "function",
                    "function": {
                        "name": func_call.name,
                        "arguments": _serialize_function_args(func_call.args) if hasattr(func_call, "args") else "{}",
                    },
                })
        
        return function_calls if function_calls else None

    async def _stream_text_with_function_calling(
        self,
        model_instance: Any,
        contents: Any,
        generation_config: Any,
        safety_settings: List[Any],
        tools: Optional[List[Tool]] = None,
        return_chunks: bool = False,
        **kwargs,
    ) -> AsyncGenerator[Union[str, StreamChunk], None]:
        """
        Stream text with Function Calling support (Google Vertex AI format).

        Args:
            model_instance: GenerativeModel instance (should include system_instruction)
            contents: Input contents (string or list of Content objects)
            generation_config: GenerationConfig object
            safety_settings: List of SafetySetting objects
            tools: List of Tool objects (Google format)
            return_chunks: If True, returns StreamChunk objects; if False, returns str tokens only
            **kwargs: Additional arguments

        Yields:
            str or StreamChunk: Text tokens or StreamChunk objects
        """
        # Build API call parameters
        api_params = {
            "contents": contents,
            "generation_config": generation_config,
            "safety_settings": safety_settings,
            "stream": True,
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
        
        # Add any additional kwargs
        api_params.update(kwargs)
        
        # Get streaming response
        stream_response = model_instance.generate_content(**api_params)
        
        # Accumulator for tool calls
        tool_calls_accumulator: Dict[str, Dict[str, Any]] = {}
        
        # Stream chunks
        import asyncio
        first_chunk_checked = False
        
        for chunk in stream_response:
            # Yield control to event loop
            await asyncio.sleep(0)
            
            # Check for prompt-level safety blocks
            if not first_chunk_checked and hasattr(chunk, "prompt_feedback"):
                pf = chunk.prompt_feedback
                if hasattr(pf, "block_reason") and pf.block_reason:
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
                
                # Check for safety blocks in response
                if hasattr(candidate, "finish_reason"):
                    finish_reason = candidate.finish_reason
                    if finish_reason in ["SAFETY", "RECITATION"]:
                        from .base_client import SafetyBlockError
                        raise SafetyBlockError(
                            "Response blocked by safety filters",
                            block_type="response",
                        )
                
                # Extract text from chunk parts
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
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
                        call_id = func_call["id"]
                        
                        # Initialize accumulator if needed
                        if call_id not in tool_calls_accumulator:
                            tool_calls_accumulator[call_id] = func_call.copy()
                        else:
                            # Update accumulator (merge arguments if needed)
                            existing_call = tool_calls_accumulator[call_id]
                            if func_call["function"]["name"]:
                                existing_call["function"]["name"] = func_call["function"]["name"]
                            if func_call["function"]["arguments"]:
                                # Merge arguments (Google may send partial arguments)
                                existing_args = existing_call["function"].get("arguments", "{}")
                                new_args = func_call["function"]["arguments"]
                                # Simple merge: append new args (may need JSON parsing for proper merge)
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

