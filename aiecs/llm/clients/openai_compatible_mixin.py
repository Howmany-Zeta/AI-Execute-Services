"""
OpenAI-Compatible Function Calling Mixin

Provides shared implementation for OpenAI-compatible providers (OpenAI, xAI, etc.)
that use the same API format for Function Calling.
"""

import logging
from typing import Dict, Any, Optional, List, AsyncGenerator, cast, Union
from dataclasses import dataclass
from openai import AsyncOpenAI

from .base_client import LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    """
    Represents a chunk in streaming response.
    
    Can contain either a text token or tool call information.
    """
    type: str  # "token" or "tool_call"
    content: Optional[str] = None  # Text token content
    tool_call: Optional[Dict[str, Any]] = None  # Tool call information
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Complete tool calls (when stream ends)


class OpenAICompatibleFunctionCallingMixin:
    """
    Mixin class providing OpenAI-compatible Function Calling implementation.
    
    This mixin can be used by any provider that uses OpenAI-compatible API format.
    Examples: OpenAI, xAI (Grok), and other OpenAI-compatible providers.
    
    Usage:
        class MyClient(BaseLLMClient, OpenAICompatibleFunctionCallingMixin):
            def _get_openai_client(self) -> AsyncOpenAI:
                # Return OpenAI-compatible client
                pass
            
            async def generate_text(self, messages, **kwargs):
                return await self._generate_text_with_function_calling(
                    messages, **kwargs
                )
    """

    def _convert_messages_to_openai_format(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """
        Convert LLMMessage list to OpenAI message format (support tool calls).
        
        Args:
            messages: List of LLMMessage objects
            
        Returns:
            List of OpenAI-format message dictionaries
        """
        openai_messages = []
        for msg in messages:
            msg_dict: Dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                msg_dict["content"] = msg.content
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            openai_messages.append(msg_dict)
        return openai_messages

    def _prepare_function_calling_params(
        self,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Prepare function calling parameters for OpenAI-compatible API.
        
        Args:
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format, recommended)
            tool_choice: Tool choice strategy ("auto", "none", or specific tool)
            
        Returns:
            Dictionary with function calling parameters
        """
        params: Dict[str, Any] = {}
        
        # Prefer 'tools' parameter (new format) over 'functions' (legacy)
        if tools:
            params["tools"] = tools
            if tool_choice is not None:
                params["tool_choice"] = tool_choice
        elif functions:
            # Legacy format - convert to tools format for consistency
            params["tools"] = [{"type": "function", "function": func} for func in functions]
            if tool_choice is not None:
                params["tool_choice"] = tool_choice
        
        return params

    def _extract_function_calls_from_response(self, message: Any) -> tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
        """
        Extract function calls from OpenAI-compatible response message.
        
        Args:
            message: Response message object from OpenAI SDK
            
        Returns:
            Tuple of (function_call, tool_calls)
            - function_call: Legacy format function call (if present)
            - tool_calls: New format tool calls (if present)
        """
        function_call = None
        tool_calls = None
        
        # Check for legacy function_call format
        if hasattr(message, "function_call") and message.function_call:
            function_call = {
                "name": message.function_call.name,
                "arguments": message.function_call.arguments,
            }
        
        # Check for new tool_calls format
        elif hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        
        return function_call, tool_calls

    def _attach_function_calls_to_response(
        self,
        response: LLMResponse,
        function_call: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Attach function call information to LLMResponse.
        
        Args:
            response: LLMResponse object
            function_call: Legacy format function call
            tool_calls: New format tool calls
            
        Returns:
            LLMResponse with function call info attached
        """
        if function_call:
            setattr(response, "function_call", function_call)
        if tool_calls:
            setattr(response, "tool_calls", tool_calls)
        return response

    async def _generate_text_with_function_calling(
        self,
        client: AsyncOpenAI,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text with Function Calling support (OpenAI-compatible).
        
        This is a helper method that can be called by subclasses to implement
        generate_text() with Function Calling support.
        
        Args:
            client: AsyncOpenAI client instance
            messages: List of LLM messages
            model: Model name
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format)
            tool_choice: Tool choice strategy
            **kwargs: Additional arguments
            
        Returns:
            LLMResponse with optional function_call information
        """
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages)
        
        # Prepare API call parameters
        api_params: Dict[str, Any] = {
            "model": model,
            "messages": cast(Any, openai_messages),  # type: ignore[arg-type]
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Add function calling support
        fc_params = self._prepare_function_calling_params(functions, tools, tool_choice)
        api_params.update(fc_params)
        
        # Add any additional kwargs
        api_params.update(kwargs)
        
        # Make API call
        response = await client.chat.completions.create(**api_params)
        
        # Extract response content
        message = response.choices[0].message
        content = message.content or ""
        
        # Extract function calls
        function_call, tool_calls = self._extract_function_calls_from_response(message)
        
        # Extract token usage
        tokens_used = response.usage.total_tokens if response.usage else None
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        # Extract cache metadata from OpenAI response
        # OpenAI returns cached_tokens in prompt_tokens_details for supported models
        cache_read_tokens = None
        cache_hit = None
        if response.usage and hasattr(response.usage, "prompt_tokens_details"):
            details = response.usage.prompt_tokens_details
            if details and hasattr(details, "cached_tokens"):
                cache_read_tokens = details.cached_tokens
                cache_hit = cache_read_tokens is not None and cache_read_tokens > 0

        # Create response
        llm_response = LLMResponse(
            content=content,
            provider=self.provider_name,  # type: ignore[attr-defined]
            model=model,
            tokens_used=tokens_used,
            prompt_tokens=input_tokens if response.usage else None,
            completion_tokens=output_tokens if response.usage else None,
            cost_estimate=self._estimate_cost_from_config(model, input_tokens, output_tokens)  # type: ignore[attr-defined]
            if hasattr(self, "_estimate_cost_from_config") else None,
            cache_read_tokens=cache_read_tokens,
            cache_hit=cache_hit,
        )

        # Attach function call info
        return self._attach_function_calls_to_response(llm_response, function_call, tool_calls)

    async def _stream_text_with_function_calling(
        self,
        client: AsyncOpenAI,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        return_chunks: bool = False,
        **kwargs,
    ) -> AsyncGenerator[Union[str, StreamChunk], None]:
        """
        Stream text with Function Calling support (OpenAI-compatible).
        
        This is a helper method that can be called by subclasses to implement
        stream_text() with Function Calling support.
        
        Args:
            client: AsyncOpenAI client instance
            messages: List of LLM messages
            model: Model name
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format)
            tool_choice: Tool choice strategy
            return_chunks: If True, returns StreamChunk objects; if False, returns str tokens only
            **kwargs: Additional arguments
            
        Yields:
            str or StreamChunk: Text tokens as they are generated, or StreamChunk objects if return_chunks=True
            
        Note:
            When return_chunks=True, yields StreamChunk objects that can contain:
            - type="token": Text token content
            - type="tool_call": Tool call information (accumulated)
            - type="tool_calls": Complete tool calls list (at end of stream)
        """
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages)
        
        # Prepare API call parameters
        api_params: Dict[str, Any] = {
            "model": model,
            "messages": cast(Any, openai_messages),  # type: ignore[arg-type]
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        # Add function calling support
        fc_params = self._prepare_function_calling_params(functions, tools, tool_choice)
        api_params.update(fc_params)
        
        # Add any additional kwargs
        api_params.update(kwargs)
        
        # Stream response
        stream = await client.chat.completions.create(**api_params)
        
        # Accumulator for tool calls
        tool_calls_accumulator: Dict[str, Dict[str, Any]] = {}
        
        if hasattr(stream, "__aiter__"):
            async for chunk in stream:
                delta = chunk.choices[0].delta
                
                # Yield text tokens
                if delta.content:
                    if return_chunks:
                        yield StreamChunk(type="token", content=delta.content)
                    else:
                        yield delta.content
                
                # Accumulate tool calls
                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        call_id = tool_call_delta.id
                        
                        # Initialize accumulator for this call if needed
                        if call_id not in tool_calls_accumulator:
                            tool_calls_accumulator[call_id] = {
                                "id": call_id,
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        
                        # Accumulate function name and arguments
                        if tool_call_delta.function:
                            if tool_call_delta.function.name:
                                tool_calls_accumulator[call_id]["function"]["name"] = tool_call_delta.function.name
                            if tool_call_delta.function.arguments:
                                tool_calls_accumulator[call_id]["function"]["arguments"] += tool_call_delta.function.arguments
                        
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

