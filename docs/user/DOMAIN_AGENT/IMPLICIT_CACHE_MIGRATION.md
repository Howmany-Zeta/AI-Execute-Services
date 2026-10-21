# Migration: explicit prompt cache → implicit cache

Audience: code that calls `LLMAgent`, `ToolAgent`, `HybridAgent`, or `VertexAIClient` / `OpenAIClient` directly.

Vertex no longer creates a Google `CachedContent` resource. Each model request sends the same system text, tools, and full message list, and Vertex’s default implicit cache matches that prefix. The hit or miss is on the response for that call. There is no cache id and no separate callback.

Method signatures are unchanged. Read the new fields below if you need to know whether this call hit.

## What to change

1. Delete host code that calls Vertex `caches.create`, stores a `cached_content` name, or reads Redis keys `vertex_ai:cached_content:*`. The client no longer reads or writes those keys. Leaving old keys in Redis is harmless.
2. Keep `enable_prompt_caching` and per-message `cache_control` as they are. They still choose where system text is placed. They no longer create a CachedContent object.
3. Keep Anthropic `cache_control` as it is. That marker is Anthropic’s own prefix hint, not Google CachedContent.
4. Read `cache_hit` and `cache_read_tokens` from `execute_task`, or a `cache_status` event from `execute_task_streaming`.
5. For OpenAI, pass a stable non-empty `context["session_id"]` when calls in one conversation should share a prompt cache.

## What the client sends now

`VertexAIClient.generate_text` and `stream_text`:

- Always send `system_instruction`, `tools`, and the full contents.
- Do not call `caches.create`.
- Do not set `cached_content` on the request.
- Do not look up Redis before the model call.

`cache_control` on a system message still decides placement:

| `cache_control` set (`enable_prompt_caching` defaults to true) | System text goes in `system_instruction` |
| `cache_control` absent or false | System text is prepended as a user message: `[System Context]\n...` |

Leave the flag where it is. Turning `enable_prompt_caching` off moves the system text from `system_instruction` into that user prefix and changes the bytes implicit cache compares.

The Google AI client never created CachedContent. It still sends the full request.

## How to tell a hit

A hit is `cache_read_tokens > 0`. `0` is a miss.

| Provider | Field on that response |
|----------|------------------------|
| Vertex / Gemini | `usage_metadata.cached_content_token_count` |
| OpenAI | `usage.prompt_tokens_details.cached_tokens` |
| Anthropic | `usage.cache_read_input_tokens` (unchanged) |

Implicit cache can drop a prefix within 24 hours when the service is under load. A miss after a quiet period is normal. There is nothing to refresh.

### Non-streaming

`execute_task` adds both fields on the LLM path (`LLMAgent`, `ToolAgent` when the task has a description, `HybridAgent` tool loop):

```python
result = await agent.execute_task(
    {"description": "Summarize the notes"},
    {"session_id": "sess-1"},
)

if result["cache_hit"]:
    billed_from_cache = result["cache_read_tokens"]
```

`HybridAgent` reports the **last** model call in that task. Earlier calls in the same tool loop are counted in agent metrics (`cache_hits`, `cache_misses`, `cache_hit_rate`, `total_cache_read_tokens`).

`process_message` does not copy these fields. It still returns `response` (and, for `LLMAgent`, `tokens_used`). Use `execute_task` when the caller needs the hint.

A direct client call already exposes the same numbers:

```python
response = await client.generate_text(messages, model="gemini-2.5-pro", tools=tools)
response.cache_hit           # True when cache_read_tokens > 0
response.cache_read_tokens
```

If the provider omits cache usage on a non-streaming response, the agent result is `cache_hit=False` and `cache_read_tokens=0`, and that call is not added to the hit/miss counters.

### Streaming

`execute_task_streaming` on `LLMAgent`, `ToolAgent`, and `HybridAgent` yields one event per model call, then repeats the last call on the final `result`:

```python
async for event in agent.execute_task_streaming(task, {"session_id": "sess-1"}):
    if event["type"] == "cache_status":
        # this model call
        # event["cache_hit"] is False when event["cache_read_tokens"] == 0
        record(event["cache_hit"], event["cache_read_tokens"])
    elif event["type"] == "result":
        # last model call of the task
        record(event["cache_hit"], event["cache_read_tokens"])
```

`cache_status` shape:

```python
{
    "type": "cache_status",
    "cache_hit": False,
    "cache_read_tokens": 0,
    "timestamp": "2026-10-21T05:33:00.000000",
}
```

`process_message_streaming` still yields only text tokens. It drops `cache_status`. Use `execute_task_streaming` to observe hits.

If you iterate `stream_text` yourself, keep `return_chunks=True` and read the terminal chunk. Agents already turn that chunk into `cache_status`; do not look for `type=="usage"` on the agent stream.

```python
# raw client only
# StreamChunk(type="usage", usage={"cache_read_tokens": 120, ...})
```

A usage chunk with `cache_read_tokens` 0 is recorded as a miss.

## Keeping the prefix stable

Implicit cache matches only a leading run of identical tokens. The tool loop already appends new messages at the end. The prefix stays hit-able when the head of the request does not change.

- Send the same system text on every turn of a conversation.
- Leave tool order as `_tool_schemas`. Do not sort or filter tools differently on each call unless the tool set itself changed.
- For OpenAI, set `context["session_id"]` to a non-empty string that stays constant for the conversation. `OpenAIClient` copies that value to `prompt_cache_key`. It does not use `agent_id`. An empty or missing `session_id` omits the parameter. If the API rejects `prompt_cache_key`, the client drops it and retries that request once.
- `xAI` and other OpenAI-compatible clients do not set `prompt_cache_key`.

Context compression may rewrite history before a call. That turn’s prefix changes, so the implicit cache misses. That miss is expected. The next turn hits again once the prefix is stable.

## Checklist

- [ ] Remove Vertex `caches.create` / `cached_content` handling and any read of `vertex_ai:cached_content:*`
- [ ] Leave `enable_prompt_caching` and Anthropic `cache_control` unchanged
- [ ] Read `cache_hit` and `cache_read_tokens` from `execute_task`, or `cache_status` from `execute_task_streaming`
- [ ] Pass a stable `session_id` for OpenAI conversations that should share a prefix
- [ ] Keep system text and tool order stable across turns
