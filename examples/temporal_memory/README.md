# Temporal memory example (L1)

Minimal **HybridAgent** wiring for `temporal_memory@builtin`. This sample is **not** part of AIECS CI (ADR-003).

## Prerequisites

| Mode | Install | Environment |
|------|---------|-------------|
| **Wiring only (NoOp)** | `pip install aiecs` | `TM_ENABLED=false` or `TM_BACKEND=none` — plugin registers but disables on init |
| **Graphiti backend** | `pip install "aiecs[temporal-graphiti]"` + FalkorDB | `TM_ENABLED=true`, `TM_BACKEND=graphiti`, `TM_FALKORDB_URL=...`, `OPENAI_API_KEY=...` |

AIECS core does **not** ship `graphiti-core` in the default wheel. Install Graphiti on the customer side (optional extra or direct `graphiti-core[falkordb]`).

## Run

```bash
cd "$(git rev-parse --show-toplevel)"

# NoOp / wiring demo (no FalkorDB)
TM_BACKEND=none poetry run python examples/temporal_memory/minimal_agent.py

# Graphiti (requires FalkorDB + API key)
TM_ENABLED=true TM_BACKEND=graphiti TM_FALKORDB_URL=redis://localhost:6379 \
  OPENAI_API_KEY=sk-... \
  poetry run python examples/temporal_memory/minimal_agent.py
```

## What the script does

1. Builds `HybridAgent` with `temporal_memory_enabled=True` and explicit `PluginConfig(name="temporal_memory")`.
2. Uses a mock LLM client (no external API for the demo turn).
3. Runs one `execute_task` and prints whether temporal memory stayed active (NoOp vs Graphiti).

For production, use real `BaseLLMClient` credentials and a running graph backend per [DOMAIN_TEMPORAL_MEMORY.md](../../docs/developer/DOMAIN_TEMPORAL_MEMORY.md).
