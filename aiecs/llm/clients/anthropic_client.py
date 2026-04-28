# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Anthropic on Vertex AI client.

Connects to Claude models hosted on Google Cloud Vertex AI Model Garden via
the official ``anthropic[vertex]`` SDK (``AsyncAnthropicVertex``).  Uses the
same ``vertex_project_id`` / ``vertex_location`` credentials as ``VertexAIClient``,
but speaks the native Anthropic Messages API rather than the Gemini API.

Differences vs the regular ``VertexAIClient`` (Gemini) implementation:

* ``system`` instructions are passed as a separate top-level parameter, not as
  a ``system`` role message.
* Content is composed of typed blocks (``text``, ``image``, ``tool_use``,
  ``tool_result``) instead of Gemini ``Part`` objects.
* Tool schemas use the Anthropic ``input_schema`` shape; tool use is emitted
  as ``tool_use`` blocks and consumed back as ``tool_result`` blocks.
* Prompt caching is per-block via ``cache_control={"type": "ephemeral"}``;
  there is no Vertex CachedContent indirection.
* Extended thinking is enabled with ``thinking={"type": "enabled",
  "budget_tokens": N}`` and reported as ``thinking_tokens`` on the response.
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List, AsyncGenerator, Union, Tuple

from aiecs.llm.utils.image_utils import parse_image_source

logger = logging.getLogger(__name__)

from aiecs.llm.clients.base_client import (  # noqa: E402
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ProviderNotAvailableError,
    RateLimitError,
)
from aiecs.llm.clients.openai_compatible_mixin import StreamChunk  # noqa: E402
from aiecs.config.config import get_settings  # noqa: E402

# The anthropic SDK is an optional dependency (``anthropic[vertex]``).  Import
# defensively so the rest of the LLM package can be imported even when the
# extra has not been installed.
try:
    from anthropic import AsyncAnthropicVertex
    from anthropic import APIStatusError, RateLimitError as AnthropicRateLimitError

    _ANTHROPIC_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when extra is missing
    AsyncAnthropicVertex = None  # type: ignore[assignment,misc]
    APIStatusError = Exception  # type: ignore[assignment,misc]
    AnthropicRateLimitError = Exception  # type: ignore[assignment,misc]
    _ANTHROPIC_AVAILABLE = False


def _serialize_tool_arguments(arguments: Any) -> Dict[str, Any]:
    """Best-effort conversion of an OpenAI-format ``arguments`` value into a dict.

    The OpenAI tool-call shape encodes arguments as a JSON string; Anthropic's
    ``tool_use`` block expects a parsed object.
    """
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, (bytes, bytearray)):
        try:
            arguments = arguments.decode("utf-8")
        except UnicodeDecodeError:
            return {}
    if isinstance(arguments, str):
        if not arguments.strip():
            return {}
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            logger.warning("Failed to JSON-decode tool arguments; passing through as raw string under '_raw'")
            return {"_raw": arguments}
        return parsed if isinstance(parsed, dict) else {"_value": parsed}
    return {"_value": arguments}


def _stringify_tool_result(result: Any) -> str:
    """Coerce a tool-result payload into the string form Anthropic expects."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(result)


def _image_block_from_source(source: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Convert an LLMMessage image source into an Anthropic image content block."""
    img = parse_image_source(source)
    if img.is_url():
        return {
            "type": "image",
            "source": {"type": "url", "url": img.get_url()},
        }
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": img.mime_type,
            "data": img.get_base64_data(),
        },
    }


class AnthropicVertexClient(BaseLLMClient):
    """Anthropic (Claude) on Google Cloud Vertex AI.

    Authenticates via the same Google Cloud credentials used by ``VertexAIClient``
    (``GOOGLE_APPLICATION_CREDENTIALS`` / ADC) and routes all calls through the
    Anthropic SDK's ``AsyncAnthropicVertex`` transport.  Returned data uses the
    same ``LLMResponse`` / ``StreamChunk`` shapes as the other clients so that
    higher-level agents do not need to special-case Anthropic.
    """

    def __init__(self):
        super().__init__("AnthropicVertex")
        self.settings = get_settings()
        self._initialized = False
        self._client: Optional["AsyncAnthropicVertex"] = None

    def _init_client(self) -> "AsyncAnthropicVertex":
        """Lazy initialization of the AsyncAnthropicVertex client."""
        if self._initialized and self._client is not None:
            return self._client

        if not _ANTHROPIC_AVAILABLE:
            raise ProviderNotAvailableError("The 'anthropic' SDK is not installed. Install with: pip install 'anthropic[vertex]'")

        if not self.settings.vertex_project_id:
            raise ProviderNotAvailableError("Vertex AI project ID not configured (VERTEX_PROJECT_ID)")

        # Reuse the same credential resolution logic as VertexAIClient: prefer an
        # explicitly configured key file, fall back to GOOGLE_APPLICATION_CREDENTIALS,
        # otherwise rely on Application Default Credentials.
        if self.settings.google_application_credentials:
            credentials_path = self.settings.google_application_credentials
            if os.path.exists(credentials_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                self.logger.info(f"Using Google Cloud credentials from: {credentials_path}")
            else:
                raise ProviderNotAvailableError(f"Google Cloud credentials file not found: {credentials_path}")
        elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            self.logger.warning("No Google Cloud credentials configured. Falling back to Application Default Credentials.")

        region = getattr(self.settings, "vertex_location", "us-central1")
        try:
            self._client = AsyncAnthropicVertex(
                project_id=self.settings.vertex_project_id,
                region=region,
            )
            self._initialized = True
            self.logger.info(f"AnthropicVertex initialized for project {self.settings.vertex_project_id} region={region}")
        except Exception as e:
            raise ProviderNotAvailableError(f"Failed to initialize AnthropicVertex: {str(e)}")

        return self._client

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _maybe_cache_control(msg: LLMMessage) -> Optional[Dict[str, str]]:
        """Return an Anthropic ``cache_control`` dict if the message asks to be cached."""
        cc = getattr(msg, "cache_control", None)
        if cc is None:
            return None
        cc_type = getattr(cc, "type", "ephemeral") or "ephemeral"
        return {"type": cc_type}

    def _convert_messages(self, messages: List[LLMMessage]) -> Tuple[Optional[Union[str, List[Dict[str, Any]]]], List[Dict[str, Any]]]:
        """Split LLMMessages into Anthropic ``system`` + ``messages`` payload.

        * All ``system`` role messages are merged and returned separately.  When
          any of them carry a ``cache_control`` marker, the system parameter is
          emitted as a list of text blocks so per-block caching is preserved.
        * ``user`` / ``assistant`` messages are converted into block lists.
        * Consecutive ``tool`` messages are merged into a single ``user`` message
          containing ``tool_result`` blocks (Anthropic requires this grouping).
        * Cache markers on a non-system message attach to its last content block.
        """
        system_blocks: List[Dict[str, Any]] = []
        any_system_cached = False
        out: List[Dict[str, Any]] = []
        pending_tool_results: List[Dict[str, Any]] = []

        def _flush_tool_results() -> None:
            if pending_tool_results:
                out.append({"role": "user", "content": list(pending_tool_results)})
                pending_tool_results.clear()

        for msg in messages:
            if msg.role == "system":
                if not msg.content:
                    continue
                block: Dict[str, Any] = {"type": "text", "text": msg.content}
                cc = self._maybe_cache_control(msg)
                if cc:
                    block["cache_control"] = cc
                    any_system_cached = True
                system_blocks.append(block)
                continue

            if msg.role == "tool":
                # OpenAI-style tool response → Anthropic tool_result block.
                pending_tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id or "",
                        "content": _stringify_tool_result(msg.content),
                    }
                )
                continue

            # Any non-tool message terminates the current tool_result run.
            _flush_tool_results()

            blocks: List[Dict[str, Any]] = []
            if msg.content:
                blocks.append({"type": "text", "text": msg.content})

            for image_source in msg.images or []:
                try:
                    blocks.append(_image_block_from_source(image_source))
                except Exception as exc:
                    logger.warning(f"Skipping unparseable image source: {exc}")

            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    func = tc.get("function") or {}
                    name = func.get("name") or ""
                    if not name:
                        continue
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.get("id") or f"toolu_{name}",
                            "name": name,
                            "input": _serialize_tool_arguments(func.get("arguments")),
                        }
                    )

            if not blocks:
                continue

            cc = self._maybe_cache_control(msg)
            if cc:
                blocks[-1]["cache_control"] = cc

            out.append({"role": msg.role, "content": blocks})

        _flush_tool_results()

        if not system_blocks:
            return None, out
        if any_system_cached or len(system_blocks) > 1:
            return system_blocks, out
        # Single uncached system message → use the simple string form.
        return system_blocks[0]["text"], out

    def _convert_tools(self, tools: Optional[List[Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-format tool schemas to Anthropic ``tools`` shape."""
        if not tools:
            return []
        sanitized = self._sanitize_tools(tools)
        anthropic_tools: List[Dict[str, Any]] = []
        for tool in sanitized:
            func = tool.get("function") or {}
            name = func.get("name")
            if not name:
                continue
            anthropic_tools.append(
                {
                    "name": name,
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters") or {"type": "object", "properties": {}},
                }
            )
        return anthropic_tools

    @staticmethod
    def _extract_tool_calls(content_blocks: Any) -> Optional[List[Dict[str, Any]]]:
        """Translate Anthropic ``tool_use`` content blocks to OpenAI-format tool_calls."""
        if not content_blocks:
            return None
        tool_calls: List[Dict[str, Any]] = []
        for block in content_blocks:
            btype = getattr(block, "type", None) if not isinstance(block, dict) else block.get("type")
            if btype != "tool_use":
                continue
            block_id = getattr(block, "id", None) if not isinstance(block, dict) else block.get("id")
            block_name = getattr(block, "name", None) if not isinstance(block, dict) else block.get("name")
            block_input = getattr(block, "input", None) if not isinstance(block, dict) else block.get("input")
            tool_calls.append(
                {
                    "id": block_id or f"call_{len(tool_calls)}",
                    "type": "function",
                    "function": {
                        "name": block_name or "",
                        "arguments": json.dumps(block_input or {}, ensure_ascii=False),
                    },
                }
            )
        return tool_calls or None

    @staticmethod
    def _extract_text(content_blocks: Any) -> str:
        """Concatenate content from all response blocks in order.

        * ``thinking`` blocks are wrapped in ``<thinking>\\n…\\n</thinking>\\n``
          so that the reasoning process is visible in ``LLMResponse.content``,
          matching the format produced by ``VertexAIClient`` for Gemini Thinking
          models.
        * ``text`` blocks are appended as-is.
        * All other block types (e.g. ``tool_use``) are skipped.
        """
        if not content_blocks:
            return ""
        parts: List[str] = []
        for block in content_blocks:
            btype = getattr(block, "type", None) if not isinstance(block, dict) else block.get("type")
            if btype == "thinking":
                thinking_val = getattr(block, "thinking", None) if not isinstance(block, dict) else block.get("thinking")
                if thinking_val:
                    parts.append(f"<thinking>\n{thinking_val}\n</thinking>\n")
            elif btype == "text":
                text_val = getattr(block, "text", None) if not isinstance(block, dict) else block.get("text")
                if text_val:
                    parts.append(text_val)
        return "".join(parts)

    def _build_request(
        self,
        messages: List[LLMMessage],
        model: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assemble the keyword arguments for ``client.messages.create`` / ``stream``."""
        model_name = model or self._get_default_model() or "claude-3-5-sonnet@20240620"

        system, anthropic_messages = self._convert_messages(messages)

        # Anthropic requires max_tokens; choose a sensible upper bound when none given.
        effective_max_tokens = max_tokens or 4096

        request: Dict[str, Any] = {
            "model": model_name,
            "messages": anthropic_messages,
            "max_tokens": effective_max_tokens,
        }
        if system is not None:
            request["system"] = system

        # Forward optional sampling controls when supplied.
        for key in ("top_p", "top_k", "stop_sequences"):
            if key in kwargs and kwargs[key] is not None:
                request[key] = kwargs.pop(key)

        # Tool support: accept OpenAI-format tools and translate them.
        tools = kwargs.pop("tools", None)
        anthropic_tools = self._convert_tools(tools)
        if anthropic_tools:
            request["tools"] = anthropic_tools
            tool_choice = kwargs.pop("tool_choice", None)
            if tool_choice is not None:
                # OpenAI uses "auto" / "none" / {"type": "function", "function": {...}}.
                # Anthropic uses {"type": "auto" | "any" | "tool", "name": "..."}.
                if isinstance(tool_choice, str):
                    if tool_choice in ("auto", "any"):
                        request["tool_choice"] = {"type": tool_choice}
                elif isinstance(tool_choice, dict):
                    if tool_choice.get("type") == "function":
                        fname = (tool_choice.get("function") or {}).get("name")
                        if fname:
                            request["tool_choice"] = {"type": "tool", "name": fname}
                    else:
                        request["tool_choice"] = tool_choice

        # Extended thinking.  Suppress temperature when thinking is enabled because
        # Anthropic rejects non-default sampling settings together with thinking.
        thinking_cfg = kwargs.pop("thinking", None)
        if thinking_cfg is not None:
            request["thinking"] = thinking_cfg
        else:
            request["temperature"] = temperature

        # Optional metadata (e.g. user id) per Anthropic conventions.
        metadata = kwargs.pop("metadata", None)
        if metadata is not None:
            request["metadata"] = metadata

        # Anything left in kwargs that the SDK understands is passed through verbatim.
        # Unknown keys are dropped intentionally to avoid 400 errors from the API.
        for key in ("extra_headers", "extra_query", "extra_body", "timeout"):
            if key in kwargs:
                request[key] = kwargs.pop(key)

        return request

    @staticmethod
    def _extract_usage(usage: Any) -> Dict[str, Optional[int]]:
        """Pull token counts (including cache hits) from an Anthropic ``Usage`` object."""
        if usage is None:
            return {
                "prompt_tokens": None,
                "completion_tokens": None,
                "cache_creation_tokens": None,
                "cache_read_tokens": None,
            }
        return {
            "prompt_tokens": getattr(usage, "input_tokens", None),
            "completion_tokens": getattr(usage, "output_tokens", None),
            "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", None),
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", None),
        }

    # ---------------------------------------------------------------- public API

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a single completion via the Anthropic Messages API.

        Args:
            messages: Conversation messages.
            model: Model name (defaults to config / hardcoded fallback).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            context: Optional metadata dict (user_id, tenant_id, …).
            functions: Legacy OpenAI-format function list. Converted to tools
                automatically when no ``tools`` kwarg is provided.
            system_instruction: Explicit system prompt injected ahead of any
                system-role messages in *messages*.
            **kwargs: Forwarded to ``_build_request`` (tools, tool_choice,
                thinking, top_p, stop_sequences, metadata, …).
        """
        # P2: merge explicit system_instruction into messages
        if system_instruction:
            messages = [LLMMessage(role="system", content=system_instruction)] + list(messages)

        # P1: promote legacy functions= to tools= when tools not already given
        if functions and "tools" not in kwargs:
            kwargs["tools"] = [{"type": "function", "function": f} for f in functions]

        client = self._init_client()
        request = self._build_request(messages, model, temperature, max_tokens, kwargs)

        try:
            response = await client.messages.create(**request)
        except AnthropicRateLimitError as exc:
            raise RateLimitError(f"Anthropic rate limit exceeded: {exc}") from exc
        except APIStatusError as exc:
            raise ProviderNotAvailableError(f"Anthropic API error: {exc}") from exc

        content_text = self._extract_text(response.content)
        tool_calls = self._extract_tool_calls(response.content)
        usage = self._extract_usage(getattr(response, "usage", None))
        prompt_tokens = usage["prompt_tokens"]
        completion_tokens = usage["completion_tokens"]
        cache_read = usage["cache_read_tokens"]
        cache_creation = usage["cache_creation_tokens"]

        cost_estimate: Optional[float] = None
        if prompt_tokens is not None and completion_tokens is not None:
            cost_estimate = self._estimate_cost_from_config(request["model"], prompt_tokens, completion_tokens)

        metadata: Dict[str, Any] = {
            "stop_reason": getattr(response, "stop_reason", None),
            "stop_sequence": getattr(response, "stop_sequence", None),
            "response_id": getattr(response, "id", None),
        }
        if tool_calls:
            metadata["tool_calls"] = tool_calls

        llm_response = LLMResponse(
            content=content_text,
            provider=self.provider_name,
            model=request["model"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_estimate=cost_estimate,
            metadata=metadata,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
            cache_hit=bool(cache_read) if cache_read is not None else None,
            # Anthropic does not currently surface a separate thinking-token count
            # in its Usage object; left as None unless future SDK versions expose it.
            thinking_tokens=None,
        )

        # P0: expose tool_calls as an attribute (mirrors OpenAI/Vertex pattern) so
        # that ToolAgent / HybridAgent can find them via getattr(response, "tool_calls").
        # metadata["tool_calls"] is kept for backward-compatibility with callers that
        # already read the metadata dict.
        if tool_calls:
            setattr(llm_response, "tool_calls", tool_calls)

        return llm_response

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        return_chunks: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[Any, None]:
        """Stream a completion, optionally yielding ``StreamChunk`` objects.

        Mirrors the contract of ``OpenAICompatibleFunctionCallingMixin.stream_text``:
        when ``return_chunks=False`` only text tokens are yielded; when
        ``return_chunks=True`` the stream also surfaces incremental ``tool_call``
        fragments, a final ``tool_calls`` batch, and a terminal ``usage`` event.

        Args:
            messages: Conversation messages.
            model: Model name.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            context: Optional metadata dict (user_id, tenant_id, …).
            return_chunks: Yield ``StreamChunk`` objects when True; plain str tokens when False.
            functions: Legacy OpenAI-format function list. Converted to tools
                automatically when no ``tools`` kwarg is provided.
            system_instruction: Explicit system prompt injected ahead of any
                system-role messages in *messages*.
            **kwargs: Forwarded to ``_build_request`` (tools, tool_choice, thinking, …).
        """
        # P2: merge explicit system_instruction into messages
        if system_instruction:
            messages = [LLMMessage(role="system", content=system_instruction)] + list(messages)

        # P1: promote legacy functions= to tools= when tools not already given
        if functions and "tools" not in kwargs:
            kwargs["tools"] = [{"type": "function", "function": f} for f in functions]

        client = self._init_client()
        request = self._build_request(messages, model, temperature, max_tokens, kwargs)

        # Per-tool-call accumulator keyed by content-block index.  Anthropic
        # streams arguments as ``input_json_delta`` fragments under the same
        # block index that opened the ``tool_use`` block.
        tool_calls_by_index: Dict[int, Dict[str, Any]] = {}
        tool_call_args_buffer: Dict[int, str] = {}
        # Track indices of thinking blocks so we can emit the closing tag at
        # content_block_stop.  Anthropic always streams thinking before text,
        # so the order in the output naturally mirrors the Gemini convention.
        thinking_indices: set = set()
        last_usage: Dict[str, Optional[int]] = {
            "prompt_tokens": None,
            "completion_tokens": None,
            "cache_creation_tokens": None,
            "cache_read_tokens": None,
        }

        try:
            async with client.messages.stream(**request) as stream:
                async for event in stream:
                    etype = getattr(event, "type", None)

                    if etype == "message_start":
                        usage = getattr(getattr(event, "message", None), "usage", None)
                        snapshot = self._extract_usage(usage)
                        for k, v in snapshot.items():
                            if v is not None:
                                last_usage[k] = v
                        continue

                    if etype == "content_block_start":
                        block = getattr(event, "content_block", None)
                        block_type = getattr(block, "type", None)
                        idx = getattr(event, "index", 0)
                        if block_type == "tool_use":
                            tool_calls_by_index[idx] = {
                                "id": getattr(block, "id", None) or f"call_{idx}",
                                "type": "function",
                                "function": {"name": getattr(block, "name", "") or "", "arguments": "{}"},
                            }
                            tool_call_args_buffer[idx] = ""
                        elif block_type == "thinking":
                            # Register index and emit the opening <thinking> tag.
                            thinking_indices.add(idx)
                            if return_chunks:
                                yield StreamChunk(type="token", content="<thinking>\n")
                            else:
                                yield "<thinking>\n"
                        continue

                    if etype == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        dtype = getattr(delta, "type", None)
                        if dtype == "text_delta":
                            text_piece = getattr(delta, "text", "") or ""
                            if not text_piece:
                                continue
                            if return_chunks:
                                yield StreamChunk(type="token", content=text_piece)
                            else:
                                yield text_piece
                        elif dtype == "thinking_delta":
                            # Extended thinking content streamed incrementally.
                            thinking_piece = getattr(delta, "thinking", "") or ""
                            if not thinking_piece:
                                continue
                            if return_chunks:
                                yield StreamChunk(type="token", content=thinking_piece)
                            else:
                                yield thinking_piece
                        elif dtype == "input_json_delta":
                            idx = getattr(event, "index", 0)
                            partial = getattr(delta, "partial_json", "") or ""
                            tool_call_args_buffer[idx] = tool_call_args_buffer.get(idx, "") + partial
                            tc = tool_calls_by_index.get(idx)
                            if tc is not None and return_chunks:
                                tc["function"]["arguments"] = tool_call_args_buffer[idx] or "{}"
                                yield StreamChunk(type="tool_call", tool_call=dict(tc))
                        continue

                    if etype == "content_block_stop":
                        idx = getattr(event, "index", 0)
                        if idx in thinking_indices:
                            # Emit the closing </thinking> tag before text starts.
                            if return_chunks:
                                yield StreamChunk(type="token", content="\n</thinking>\n")
                            else:
                                yield "\n</thinking>\n"
                        elif idx in tool_calls_by_index:
                            buffered = tool_call_args_buffer.get(idx, "")
                            if buffered:
                                tool_calls_by_index[idx]["function"]["arguments"] = buffered
                        continue

                    if etype == "message_delta":
                        usage = getattr(event, "usage", None)
                        if usage is not None:
                            snapshot = self._extract_usage(usage)
                            for k, v in snapshot.items():
                                if v is not None:
                                    last_usage[k] = v
                        continue

        except AnthropicRateLimitError as exc:
            raise RateLimitError(f"Anthropic rate limit exceeded: {exc}") from exc
        except APIStatusError as exc:
            raise ProviderNotAvailableError(f"Anthropic API error: {exc}") from exc

        if return_chunks:
            if tool_calls_by_index:
                ordered_tool_calls = [tool_calls_by_index[i] for i in sorted(tool_calls_by_index.keys())]
                yield StreamChunk(type="tool_calls", tool_calls=ordered_tool_calls)

            if any(v is not None for v in last_usage.values()):
                pt = last_usage["prompt_tokens"] or 0
                ct = last_usage["completion_tokens"] or 0
                usage_payload: Dict[str, Any] = {
                    "prompt_tokens": pt,
                    "completion_tokens": ct,
                    "total_tokens": pt + ct,
                }
                if last_usage["cache_read_tokens"] is not None:
                    usage_payload["cache_read_tokens"] = last_usage["cache_read_tokens"]
                if last_usage["cache_creation_tokens"] is not None:
                    usage_payload["cache_creation_tokens"] = last_usage["cache_creation_tokens"]
                yield StreamChunk(type="usage", usage=usage_payload)

    async def close(self) -> None:
        """Release the underlying httpx client held by AsyncAnthropicVertex."""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception as exc:
                self.logger.debug(f"AnthropicVertex client close raised: {exc}")
            finally:
                self._client = None
                self._initialized = False
