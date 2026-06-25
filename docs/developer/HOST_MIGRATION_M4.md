# Host migration M4 (CC-091–105)

Guide for **python-middleware** integrating aiecs 2.1.x compression after M3 GA.
Host code lives under `app/services/multi_task/`. This aiecs repo ships reference
adapters under `aiecs/host/compression/` and `examples/host_compression/`.

## Prerequisites

- M3 GA complete in aiecs (Groups A–H, `cc_m3_verification.txt`)
- Host repo checked out alongside or depending on aiecs `>=2.1.0`

## Task checklist

### CC-091 — Dependency + subagent config

**Host files:** `pyproject.toml`, `config/llm_binding.yaml`

```toml
# pyproject.toml
aiecs = ">=2.1.0"  # or path = "../python-middleware-dev"
```

```yaml
# llm_binding.yaml (per subagent)
enable_context_compression: true
context_window_limit: 200000
```

Snippet: `examples/host_compression/llm_binding.snippet.yaml`

Wire YAML → `AgentConfiguration` in multi_task agent factory.

### CC-092 — ToolArtifactPort → MinIO/S3 (ADR-012)

```python
from aiecs.host.compression import S3ToolArtifactPort

port = S3ToolArtifactPort()  # AIECS_TOOL_ARTIFACT_BUCKET, optional endpoint
```

Pass `artifact_port=port` into `ToolLoopCompressionContext` when building
HybridAgent (host factory). Requires `boto3` in host env.

### CC-093 — L3 E2E soak

```bash
poetry run python scripts/validate_l3_compression_e2e.py
```

Validates large `read_files`-style output is offloaded and pre-LLM tokens stay
under context window. Add to host CI after CC-091 lands.

### CC-094 — SSE progress bridge

```python
from aiecs.host.compression import compact_progress_event_to_sse_payload
from aiecs.domain.context.compression.progress import CompactProgressEmitter

emitter = CompactProgressEmitter(on_progress=lambda e: sse_send(
    compact_progress_event_to_sse_payload(e, session_id=sid, task_id=tid)
))
```

Host owns Socket.IO/SSE transport; aiecs only emits `CompactProgressEvent`.

### CC-095 — L2 MC recursive boundary

```python
from aiecs.host.compression import compact_at_mc_recursive_boundary, use_aiecs_compression

if use_aiecs_compression() and host_l2_should_compact(...):
    messages, did = await compact_at_mc_recursive_boundary(
        formatted_history,
        policy=policy,
        llm_client=llm_client,
        session_id=session_id,
        strategy=("microcompact",),
    )
```

Env: `USE_AIECS_COMPRESSION=1`. L1 warn-only and *when* to compact stay in host.

### CC-096 — Deprecation plan

See `issue_report/memory/HOST_GENERAL_COMPRESSION_DEPRECATION.md`. Do **not**
delete `general/compression` until CC-097–105 sign-off.

### CC-097–105 — Host acceptance

Track in host repo issue tracker. aiecs provides:

| AC | aiecs artifact |
|----|----------------|
| L3 soak | `scripts/validate_l3_compression_e2e.py` |
| S3 port | `aiecs/host/compression/s3_tool_artifact_port.py` |
| SSE mapping | `aiecs/host/compression/progress_bridge.py` |
| L2 adapter | `aiecs/host/compression/l2_mc_adapter.py` |
| Integration doc | `docs/developer/CONTEXT_COMPRESSION_HOST_INTEGRATION.md` |

## Boundaries (do not violate)

- **L1** warning thresholds + `context_warning` SSE → host only
- **L2** recursive boundary policy → host only; aiecs supplies adapter
- **Config UI / YAML editor** → host only
- **No** aiecs imports from `app/services/general/compression`

## Verification (aiecs repo)

```bash
poetry run pytest test/unit/host/compression -q
poetry run python scripts/validate_l3_compression_e2e.py
poetry run pytest test/integration/context/test_context_compression.py -q 2>&1 | tail -5
```

## Related

- [CONTEXT_COMPRESSION_HOST_INTEGRATION.md](./CONTEXT_COMPRESSION_HOST_INTEGRATION.md)
- [HOST_GENERAL_COMPRESSION_DEPRECATION.md](../../issue_report/memory/HOST_GENERAL_COMPRESSION_DEPRECATION.md)
