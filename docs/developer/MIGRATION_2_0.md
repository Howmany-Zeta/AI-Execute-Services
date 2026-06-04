# AIECS 2.0 Migration Guide

This guide covers breaking changes in **AIECS 2.0.0** after the core slimdown (ADR-002, ADR-003). See [CHANGELOG.md](../../CHANGELOG.md) and [PLUGIN_SYSTEM.md](./DOMAIN_AGENT/PLUGIN_SYSTEM.md) §7.0 for related detail.

## 1. Agents

### Removed

| Removed | Replacement |
|---------|-------------|
| `KnowledgeAwareAgent` | `HybridAgent` + `knowledge@builtin` |
| `GraphAwareAgentMixin` | `KnowledgePlugin` hooks on `HybridAgent` |
| `GraphMemoryMixin` | Application-owned graph/context integration |

### Recommended setup

```python
from aiecs.domain.agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginConfig

agent = HybridAgent(
    agent_id="agent-001",
    name="Assistant",
    llm_client=llm_client,
    tools=["search"],
    config=AgentConfiguration(
        goal="Answer with optional graph context",
        plugins=[
            PluginConfig(name="knowledge", enabled=True),
        ],
    ),
)
await agent.initialize()
```

- **Without a graph store:** `KnowledgePlugin` stays disabled by default (`derive_default_plugins` uses `NoOpGraphStore`).
- **With an in-process store:** set `agent.graph_store = your_store` before `initialize()` (or rely on L2 factory below).
- **Parity / golden tests:** use `HybridAgent` fixtures under `tests/fixtures/plugin_parity/knowledge_*.yaml`.

## 2. Tools

### Removed from core (2.0.0)

| Package path | Notes |
|--------------|--------|
| `aiecs.tools.apisource` | Fork into your repo or implement `BaseTool` |
| `aiecs.tools.scraper_tool` | Same |
| `aiecs.tools.statistics` | Same |
| `aiecs.tools.knowledge_graph` | Use private L2 + `KnowledgePlugin`, not built-in KG tools |

### Auto-discovery allowlist

Only these tool trees are discovered by default:

- `aiecs.tools.task_tools`
- `aiecs.tools.docs`
- `aiecs.tools.search_tool`

Do not re-add removed directories to `tool_dirs` in application bootstrap code.

### Document parser

`DocumentParserTool` no longer imports `scraper_tool`. URL fetch uses **httpx** only. Ensure `httpx` is available in your environment.

### Scraper-related Python packages (removed from core)

The following packages are **no longer** declared in AIECS core `pyproject.toml` / `poetry.lock` (2.0 slimdown):

| Package | Former use |
|---------|------------|
| `playwright` | Browser automation for `scraper_tool` |
| `playwright-stealth` | Stealth mode for Playwright |
| `curl_cffi` | TLS-fingerprint HTTP client for scraper |
| `scrapy` | Scrapy spider execution |

If you still run scraping in your own application, install and pin these in **your** project—not via `pip install aiecs`. The production Docker image no longer runs `playwright install`. `aiecs-check-deps` / `aiecs-fix-deps` no longer check or install Playwright browsers.

## 3. Private knowledge graph (L2, customer-side)

AIECS **does not** ship, test, or document a proprietary `aiecs-kg` package. Optional L2 is wired only through:

| Setting | Default | Purpose |
|---------|---------|---------|
| `KG_ENABLED` | `false` | When `true`, attempt backend import |
| `KG_BACKEND_MODULE` | `aiecs_kg` | `importlib` module exposing `create_graph_store(settings)` |

### Install steps (customer environment)

1. Install AIECS core: `pip install aiecs` (or editable `pip install -e ".[dev]"` for development).
2. Install **your** private wheel/source for the graph engine (e.g. module `aiecs_kg` on `PYTHONPATH`).
3. Configure environment:

```bash
export KG_ENABLED=true
export KG_BACKEND_MODULE=aiecs_kg   # must match your package module name
```

4. Enable the plugin on the agent (explicit or via non-NoOp store):

```python
from aiecs.infrastructure.knowledge import create_graph_store

store = create_graph_store()  # NoOp if disabled or import fails
agent.graph_store = store
# Plugin derive enables knowledge@builtin when store is not NoOp
```

5. Run your application tests against **your** KG deployment. AIECS CI runs only the **NoOp / factory shell** tests (`test/unit/infrastructure/knowledge/`, `test_knowledge_plugin.py`).

### What AIECS CI does **not** do

- `pip install` paths under `issue_report/.../AI-Execute-Services-KnowledgeGraph`
- `pip install` any `aiecs-kg` or private KG artifact
- Joint integration tests with customer KG backends (ADR-003)

## 4. Configuration summary

| Variable | Phase 3+ core | Notes |
|----------|---------------|--------|
| `KG_ENABLED` | Yes | Only remaining `kg_*` settings in core |
| `KG_BACKEND_MODULE` | Yes | Private factory module name |
| `KG_STORAGE_*`, fusion, tenancy | **Removed** | Configure in private `aiecs-kg` if needed |

## 5. Optional temporal memory (L1, separate track)

**Graphiti** (`graphiti-core`) is an optional **L1** dependency, not part of core slimdown verification. See [TEMPORAL_KG_MEMORY_INDEX.md](../../issue_report/new_function_request/temporal_kg_memory/TEMPORAL_KG_MEMORY_INDEX.md) for `TM_BACKEND` and `pip install graphiti-core` when that extra is published.

## 6. Checklist

- [ ] Replace `KnowledgeAwareAgent` with `HybridAgent` + `PluginConfig(name="knowledge", ...)`
- [ ] Remove imports of deleted tool packages
- [ ] Drop scraper stack deps (`playwright`, `playwright-stealth`, `curl_cffi`, `scrapy`) from deploy manifests if you relied on core shipping them
- [ ] Fork or replace apisource / scraper / statistics / KG tools in your app
- [ ] Set `KG_ENABLED` only when private backend is installed
- [ ] Read [CHANGELOG.md](../../CHANGELOG.md) **2.0.0** section before upgrading production
