# Host migration snippets (Group I / CC-091–095)

These files are **copy targets** for `python-middleware` (`app/services/multi_task/`).
This repo ships aiecs only; host wiring lives in the application repo.

## CC-091 — bump aiecs + enable compression

1. `pyproject.toml` — depend on aiecs `>=2.1.0` (or path to this repo).
2. `config/llm_binding.yaml` — see `llm_binding.snippet.yaml`.
3. Map subagent YAML → `AgentConfiguration.enable_context_compression`.

## CC-092 — ToolArtifactPort (MinIO/S3)

```python
from aiecs.host.compression import S3ToolArtifactPort

artifact_port = S3ToolArtifactPort(
    bucket=os.environ["AIECS_TOOL_ARTIFACT_BUCKET"],
    endpoint_url=os.environ.get("AIECS_TOOL_ARTIFACT_ENDPOINT_URL"),
)
# Pass into HybridAgent tool loop via ToolLoopCompressionContext.artifact_port
# when constructing agent or in multi_task agent factory.
```

## CC-094 — SSE progress bridge

```python
from aiecs.host.compression import compact_progress_event_to_sse_payload
from aiecs.domain.context.compression.progress import CompactProgressEmitter

def on_progress(event):
    payload = compact_progress_event_to_sse_payload(
        event, session_id=session_id, task_id=task_id
    )
    await sse_emit(payload)  # host transport — NOT in aiecs
```

## CC-095 — L2 MC boundary

```python
from aiecs.host.compression import compact_at_mc_recursive_boundary, use_aiecs_compression

if use_aiecs_compression() and at_recursive_boundary and over_threshold:
    history, did = await compact_at_mc_recursive_boundary(
        formatted_history,
        policy=policy,
        llm_client=llm_client,
        session_id=session_id,
        strategy=("microcompact",),  # L2 default: MC-only at boundary
    )
```

See `docs/developer/HOST_MIGRATION_M4.md` for full checklist.
