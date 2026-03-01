# Migration Guide: ReAct to Function Calling

HybridAgent no longer supports ReAct text format. Use OpenAI-compatible Function Calling instead.

## Summary of Changes

| Before (ReAct) | After (Function Calling) |
|----------------|-------------------------|
| Parse `TOOL:`, `OPERATION:`, `PARAMETERS:` from text | Native `tool_calls` from LLM API |
| Parse `FINAL RESPONSE: ... finish` from text | No tool_calls → treat as final response |
| `react_format_enabled` config | Removed; Function Calling only when tools configured |
| Step-based prompts in user message | Move to system prompt; first user message = raw task only |

## Supported Providers

Use an LLM client that supports OpenAI-compatible Function Calling:

- **OpenAI** (gpt-4, gpt-4-turbo, etc.)
- **xAI** (Grok)
- **Anthropic** (Claude)
- **Google Vertex AI**

## Migration Steps

### 1. Remove `react_format_enabled`

```python
# Before
config = AgentConfiguration(
    react_format_enabled=True,
    ...
)

# After - remove; no longer exists
config = AgentConfiguration(...)
```

### 2. Use Function Calling with Tools

Ensure your LLM client supports the `tools` parameter. HybridAgent auto-detects support and uses Function Calling when tools are configured.

```python
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=OpenAIClient(),  # or xAI, Anthropic, Vertex
    tools=["search", "calculator"],
    config=config,
)
await agent.initialize()
```

### 3. Remove ReAct Format from Prompts

Do **not** instruct the model to output:

- `TOOL:`, `OPERATION:`, `PARAMETERS:`
- `FINAL RESPONSE: ... finish`
- `<THOUGHT>`, `<OBSERVATION>` tags

The model uses native tool_calls; no text parsing is performed.

### 4. Callers: Do Not Append initial_act_prompt to Task

If you use MasterController or similar callers:

- **Do NOT** append `initial_act_prompt` (Step 1 / Step 2) to the task description passed to HybridAgent
- First user message must contain only the raw request
- Move step instructions to **system prompts** if needed

```python
# Wrong - anchors model to Step 1
task = {"description": f"{user_input}\n\n{initial_act_prompt}"}

# Correct - raw task only
task = {"description": user_input}
# Put Step 1/2 in system_prompt or system_prompts
```

## Tool Schema Requirements

Tools must be registered with proper schemas. HybridAgent uses `ToolSchemaGenerator` to create OpenAI-compatible schemas from `BaseTool` instances. Ensure your tools:

- Extend `BaseTool`
- Implement `run_async(operation, **params)` or `run_async(**params)`
- Have clear docstrings for schema generation

## Text-Only Mode (No Tools)

When `tools=[]`, HybridAgent runs in text-only mode: no Function Calling required. The model generates text; completion is when the response has no tool_calls.

## Error: "does not support tools"

If you see:

```
HybridAgent requires an LLM client with Function Calling support when tools are configured.
Current client (X) does not support tools.
```

- Use OpenAI, xAI, Anthropic, or Vertex
- Or remove tools for text-only tasks
