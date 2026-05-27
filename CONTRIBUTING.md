# Contributing to AIECS

Full contributor guide (setup, style, documentation): [docs/developer/contributing.rst](docs/developer/contributing.rst).

Agent plugin system design and API reference: [docs/developer/DOMAIN_AGENT/PLUGIN_SYSTEM.md](docs/developer/DOMAIN_AGENT/PLUGIN_SYSTEM.md).

## Agent plugin system CI

Run this block when changing `aiecs/domain/agent/plugins/`, agent plugin wiring (`hybrid_agent.py`, `llm_agent.py`, `tool_agent.py`, `base_agent.py`), or parity fixtures under `tests/fixtures/plugin_parity/`.

```bash
poetry run pytest test/unit/domain/agent/plugins/ -v --tb=short
poetry run pytest test/unit/domain/agent/plugins/test_plugin_parity.py -m plugin_parity -v --tb=short
poetry run pytest test/unit/domain/agent/test_hybrid_agent*.py test/unit/domain/agent/test_llm_agent*.py test/unit/domain/agent/test_tool_agent*.py -v --tb=short
poetry run mypy aiecs/domain/agent/plugins/ aiecs/domain/agent/hybrid_agent.py aiecs/domain/agent/llm_agent.py aiecs/domain/agent/tool_agent.py aiecs/domain/agent/base_agent.py
```

**Parity gate:** always target `test/unit/domain/agent/plugins/test_plugin_parity.py` explicitly (do not rely on repo-wide `-m plugin_parity` alone).

**Regenerate golden fixtures** after intentional behavior changes:

```bash
poetry run python -m aiecs.domain.agent.plugins.testing.capture
poetry run python -m aiecs.domain.agent.plugins.testing.capture \
    --pattern 'llm_*.yaml' --pattern 'tool_*.yaml'
```
