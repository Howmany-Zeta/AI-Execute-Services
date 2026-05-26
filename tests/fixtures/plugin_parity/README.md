# Plugin parity golden fixtures (§12.1)

Golden snapshots for **plugin-enabled** `HybridAgent` behavior (`BUILD_MESSAGES`, tool schemas, `execute_task` shell, streaming phase order).

Fixtures use in-process `parity_search` (`ParityStubTool`) so tool schema names are stable without the tool registry.

## Scenarios

| File | Purpose |
|------|---------|
| `hybrid_baseline.yaml` | Default derive: `parity_search` tool, `memory_enabled`, no skills |
| `hybrid_context_history.yaml` | `context.history` multi-turn expansion (§7.2) |
| `hybrid_skills_enabled.yaml` | `skills_enabled` + `skill_names` → skill system message (incl. script paths) |
| `hybrid_plugins_empty_regression.yaml` | `plugins: []` ≡ full derive; must match baseline |
| `hybrid_streaming_phases.yaml` | `plugin_phase_started` order: streaming vs sync (§10.3) |

## Refresh baselines

From repository root (updates `expect:` blocks in place):

```bash
poetry run python -m aiecs.domain.agent.plugins.testing.capture
```

Refresh one fixture:

```bash
poetry run python -m aiecs.domain.agent.plugins.testing.capture \
  --fixture tests/fixtures/plugin_parity/hybrid_baseline.yaml
```

## CI gate (Phase 2 merge)

```bash
poetry run pytest test/unit/domain/agent/plugins/ -m plugin_parity -v --tb=short
```

All tests must pass (no xfail). Re-run after changing `HybridAgent`, builtin plugins, or normalize rules.
