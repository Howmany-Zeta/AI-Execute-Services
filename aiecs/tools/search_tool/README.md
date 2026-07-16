# SearchTool (M-D.5 grounding)

Production web-search layer for aiecs: **Google Search Grounding (Gemini)**, **Grok web search**, and **Google Custom Search (CSE)**, with fail-open routing, M-D.1 partition, and routing-aware cache keys.

**Status:** SearchTool is a **supported core tool**. The earlier MCP-migration deprecation notice for `search_tool` has been **revoked** (M-D.5 §12). `task_tools` deprecation is unchanged.

Long-form field tables: [`docs/user/TOOLS_USED_INSTRUCTION/SEARCH_TOOL_CONFIGURATION_REFERENCE.md`](../../../docs/user/TOOLS_USED_INSTRUCTION/SEARCH_TOOL_CONFIGURATION_REFERENCE.md).

---

## Quick start

```python
from aiecs.tools.search_tool import SearchTool

tool = SearchTool(config={
    "grounding_provider": "auto",
    "grounding_provider_chain": "gemini,grok,google_cse",
})

out = tool.search_web(
    "Why is Tesla popular among young people?",
    auto_enhance=True,
    # Domain steering (§3.6) — Grok native; Gemini blocked_domains; CSE post-filter
    # allowed_domains=["yougov.com", "pewresearch.org"],
    # blocked_domains=["facebook.com"],
)
print(out["_search_metadata"]["backend_used"])   # gemini | grok | google_cse
print(out["_search_metadata"]["partition_profile"])  # grounding | cse
```

CSE-only deployments (no grounding keys) continue to work: the chain fails open to `google_cse` when that backend is configured.

---

## Environment variables (`SEARCH_TOOL_*`)

Env prefix is always `SEARCH_TOOL_`. Prefer dedicated search keys — do **not** share LLM client billing by default.

| Env | Config key | Purpose |
|-----|------------|---------|
| `SEARCH_TOOL_GEMINI_API_KEY` | `gemini_api_key` | Gemini grounding (Google AI) |
| `SEARCH_TOOL_GOOGLEAI_API_KEY` | `googleai_api_key` | Alias for Gemini googleai |
| `SEARCH_TOOL_VERTEX_PROJECT_ID` | `vertex_project_id` | Gemini Vertex project |
| `SEARCH_TOOL_VERTEX_LOCATION` | `vertex_location` | Default `global` |
| `SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS_VERTEX_GEMINI` | `google_application_credentials_vertex_gemini` | Gemini Vertex SA |
| `SEARCH_TOOL_GEMINI_GROUNDING_AUTH` | `gemini_grounding_auth` | `auto` \| `googleai` \| `vertex` |
| `SEARCH_TOOL_GROK_API_KEY` | `grok_api_key` | Grok (xAI direct) |
| `SEARCH_TOOL_XAI_API_KEY` | `xai_api_key` | Alias for Grok xAI |
| `SEARCH_TOOL_VERTEX_PROJECT_ID_MAAS` | `vertex_project_id_maas` | Grok Vertex MaaS |
| `SEARCH_TOOL_VERTEX_LOCATION_MAAS` | `vertex_location_maas` | Default `global` |
| `SEARCH_TOOL_GOOGLE_APPLICATION_CREDENTIALS_VERTEX_MAAS` | `google_application_credentials_vertex_maas` | MaaS SA |
| `SEARCH_TOOL_GROK_GROUNDING_AUTH` | `grok_grounding_auth` | `auto` \| `xai` \| `vertex_maas` |
| `SEARCH_TOOL_GOOGLE_API_KEY` | `google_api_key` | CSE API key |
| `SEARCH_TOOL_GOOGLE_CSE_ID` | `google_cse_id` | CSE engine ID |
| `SEARCH_TOOL_GROUNDING_PROVIDER` | `grounding_provider` | `auto` or forced backend |
| `SEARCH_TOOL_GROUNDING_PROVIDER_CHAIN` | `grounding_provider_chain` | Fail-open order |
| `SEARCH_TOOL_ALLOW_LLM_CREDENTIAL_FALLBACK` | `allow_llm_credential_fallback` | Dev-only LLM Settings borrow |
| `SEARCH_TOOL_BATCH_ROUTING_MODE` | `batch_routing_mode` | See [batch pin](#batch-routing-and-p95) |
| `SEARCH_TOOL_BATCH_P95_BUDGET_SECONDS` | `batch_p95_budget_seconds` | Default **15** |
| `SEARCH_TOOL_SEARCH_ERROR_MODE` | `search_error_mode` | `auto` \| `return_dict` \| `raise` |
| `SEARCH_TOOL_GROUNDING_RATE_LIMIT_REQUESTS` | `grounding_rate_limit_requests` | Default **60** (gemini/grok/custom) |
| `SEARCH_TOOL_GROUNDING_RATE_LIMIT_WINDOW` | `grounding_rate_limit_window` | Default **3600** |
| `SEARCH_TOOL_GROUNDING_CIRCUIT_BREAKER_THRESHOLD` | `grounding_circuit_breaker_threshold` | Default **5** |
| `SEARCH_TOOL_GROUNDING_CIRCUIT_BREAKER_TIMEOUT` | `grounding_circuit_breaker_timeout` | Default **60** |
| `SEARCH_TOOL_GROK_MAAS_WEB_SEARCH_ENABLED` | `grok_maas_web_search_enabled` | MaaS spike gate (default `false`) |
| `SEARCH_TOOL_GROK_MAAS_CAPABILITY_PROBE` | `grok_maas_capability_probe` | Optional MaaS probe |

CSE quota fields remain `SEARCH_TOOL_RATE_LIMIT_*` / `SEARCH_TOOL_CIRCUIT_BREAKER_*` (defaults 100 / 86400). Optional per-backend overrides: `SEARCH_TOOL_GEMINI_RATE_LIMIT_REQUESTS`, `SEARCH_TOOL_GROK_CIRCUIT_BREAKER_THRESHOLD`, etc.

`google-api-python-client` is required when CSE is configured or when using `search_news` / `search_images` / `search_videos` (CSE-only methods).

---

## Auth modes

### Gemini (`gemini_grounding_auth`)

| Mode | When | Credentials |
|------|------|-------------|
| `auto` (default) | Prefer googleai key, else Vertex | `SEARCH_TOOL_GEMINI_API_KEY` or Vertex project + SA |
| `googleai` | Force API key | `SEARCH_TOOL_GEMINI_API_KEY` / `SEARCH_TOOL_GOOGLEAI_API_KEY` |
| `vertex` | Force Vertex | `SEARCH_TOOL_VERTEX_PROJECT_ID` + SA / ADC |

Uses **sync** `google.genai` `Client.models.generate_content` (not `client.aio`).

### Grok (`grok_grounding_auth`)

| Mode | When | Credentials |
|------|------|-------------|
| `auto` (default) | Prefer xAI key; MaaS only if spike flag on | `SEARCH_TOOL_GROK_API_KEY` / `SEARCH_TOOL_XAI_API_KEY` |
| `xai` | Force xAI OpenAI-compatible client | API key |
| `vertex_maas` | Force MaaS (ignores spike flag) | MaaS project + SA |

Sync `openai.OpenAI` only — no `asyncio` inside built-in backends.

### Google CSE

Uses `SEARCH_TOOL_GOOGLE_API_KEY` + `SEARCH_TOOL_GOOGLE_CSE_ID`. There is **no** silent fallback to global `GOOGLE_API_KEY` / `GOOGLE_CSE_ID`.

### `allow_llm_credential_fallback` — **dev-only**

| Setting | Behavior |
|---------|----------|
| `false` (**default**, production) | Gemini/Grok use only `SEARCH_TOOL_*`. Unconfigured backends are skipped. |
| `true` | May borrow LLM `Settings` keys (`GOOGLEAI_API_KEY`, `XAI_API_KEY`, etc.) with a one-time WARNING and `credential_source=llm_fallback`. |

**Never enable in production.** Use dedicated `SEARCH_TOOL_*` keys for billing isolation.

---

## Provider chain, aliases, and routing

| Field | Default | Notes |
|-------|---------|-------|
| `grounding_provider` | `auto` | Walk chain, or force one backend |
| `grounding_provider_chain` | `gemini,grok,google_cse` | Fail-open order for `auto` |

**Built-in name aliases** (normalized before routing and cache fingerprint):

| Input | Canonical |
|-------|-----------|
| `google`, `cse`, `google_cse` | `google_cse` |
| `gemini` | `gemini` |
| `grok` | `grok` |
| `auto` | `auto` |
| custom (e.g. `exa`) | exact registered `name` (case-sensitive after trim) |

Unconfigured or circuit-open backends are skipped; the next chain entry is tried.

### Custom backends

```python
tool = SearchTool(
    config={
        "grounding_provider": "auto",
        "grounding_provider_chain": "exa,gemini,grok,google_cse",
    },
    custom_grounding_backends=[ExaGroundingBackend(...)],
)
```

Custom names appear in the routing cache fingerprint. Async-only consumer backends may use `aiecs.tools.search_tool.backends.async_bridge.run_async_from_sync` — **built-ins must not**.

---

## Batch routing and P95

| Field | Default | Description |
|-------|---------|-------------|
| `batch_routing_mode` | `pin_on_first_success` | One chain walk; pin backend after first success |
| `batch_p95_budget_seconds` | **`15.0`** | Total wall-clock budget for the batch |
| `batch_repin_on_sibling_failure` | `false` | Keep pin on Q2+ failure (fail-open tail) |

With `pin_on_first_success`, Q2+ use the pinned backend only (no re-walk of chain head). Per-query timeout is `min(grounding_timeout_seconds, remaining_budget / remaining_queries)`.

Mode `per_query` re-walks the chain each query (higher latency; not the production default).

Batch metadata includes `batch_pinned_backend`, `per_query_backend_used`, `batch_p95_budget_seconds`, `batch_elapsed_ms`.

---

## Error modes (`search_error_mode`)

| Mode | Behavior |
|------|----------|
| `auto` (default) | Tier A (validation) raises; CSE-only API failures raise; auto-chain exhaustion returns `success: false` + `_error` (no raise) |
| `return_dict` | Prefer structured failure dicts for Tier C |
| `raise` | Raise on Tier C failures |

Batch partial failure: successful query buckets keep results; failed buckets carry `_error`.

---

## Partition profiles (`cse` vs `grounding`)

After normalize, results are partitioned with a backend-aware profile:

| Profile | When | Behavior |
|---------|------|----------|
| `grounding` | Gemini/Grok (and citation-shaped customs) | Citation trust floor, relaxed relevance, social demotion; demographic/causal `grounding_min_must_scrape` |
| `cse` | Google CSE | Legacy CSE thresholds (e.g. relevance 0.7) |

See `_search_metadata.partition_profile`, `must_scrape_urls`, `low_signal`.

Tunables: `grounding_trust_citations`, `grounding_relevance_threshold`, `grounding_sparse_snippet_max_len`, `grounding_citation_trust_top_k`, `grounding_min_must_scrape`.

---

## Routing-aware cache fingerprint

Decorator cache keys for `search_web` / `search_batch` include a JSON fingerprint (`cache_schema_version` default **`m-d.5`**) covering:

- `grounding_provider`, `grounding_provider_chain` (normalized)
- `gemini_grounding_auth`, `grok_grounding_auth`, `grok_maas_web_search_enabled`
- `custom_backend_names` (sorted registered non-built-ins)
- `rewrite_before_grounding`, `batch_routing_mode`, `search_error_mode`
- Partition tunables: `grounding_trust_citations`, `grounding_relevance_threshold`, `grounding_sparse_snippet_max_len`, `grounding_citation_trust_top_k`, `grounding_min_must_scrape`

API keys and credential **paths** are never fingerprinted. Changing chain/auth/custom registration or partition knobs → cache **miss** without a schema bump.

**Staged rollout purge:**

1. `tool.clear_search_cache()` — in-process decorator LRU
2. Redis (if used): `SCAN`/`DEL` `tool_executor:*` and `search_tool:*`
3. Keep or bump `cache_schema_version` on envelope breaks

---

## Grok MaaS spike gate

| Field | Default | Notes |
|-------|---------|-------|
| `grok_maas_web_search_enabled` | **`false`** | MaaS-only creds do **not** enable Grok in `auto` until this is `true`. Auto MaaS then **always** TTL-probes `web_search`. |
| `grok_maas_capability_probe` | `false` | Also probe when `grok_grounding_auth=vertex_maas` (forced). Auto ignores this for “whether to probe”. |

**Spike status:** Target model `xai/grok-4.5`. MaaS `web_search` support is **unconfirmed** until ops validate the openapi endpoint — leave enable `false`. Forced `grok_grounding_auth=vertex_maas` still attempts regardless of enable; set `grok_maas_capability_probe=true` to fast-fail unsupported models. Details: `backends/grok_grounding.py` module docstring.

---

## Gemini Search Suggestions TOS (consumer)

aiecs **passthrough only**. When Gemini returns Search Suggestions HTML:

```json
"_search_metadata": {
  "backend_used": "gemini",
  "gemini_grounding": {
    "search_entry_point": { "rendered_content": "<!-- Google HTML -->" },
    "requires_search_suggestions_ui": true
  }
}
```

`grounding_answer` is synthesized text — **not** evidence. Before user-facing display, consumers must pick one path ([Google grounding TOS](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/grounding/grounding-with-google-search)):

| Path | Config (consumer) | Requirement |
|------|-------------------|-------------|
| **A (default)** | `surface_grounding_answer_to_user=false` | Hide `grounding_answer` from end users; citations/URLs OK |
| **B** | `surface_grounding_answer_to_user=true` | Render `rendered_content` **verbatim** adjacent to any shown `grounding_answer` when `requires_search_suggestions_ui=true` |

Prod user-visible grounding is a **Gate P6** consumer checklist — outside aiecs package CI.

---

## Consumer integration (python-middleware)

### `WebSearch.yaml` sketch

```yaml
# Illustrative — field names follow SearchTool.Config / SEARCH_TOOL_* env
tool: web_search
config:
  grounding_provider: auto
  grounding_provider_chain: gemini,grok,google_cse   # or: exa,gemini,grok,google_cse
  batch_routing_mode: pin_on_first_success
  batch_p95_budget_seconds: 15
  search_error_mode: auto
  allow_llm_credential_fallback: false
  grok_maas_web_search_enabled: false
  # surface_grounding_answer_to_user: false   # consumer TOS Path A (default)
```

Wire `SEARCH_TOOL_GEMINI_*`, `SEARCH_TOOL_GROK_*`, and/or `SEARCH_TOOL_GOOGLE_*` in the deployment env.

### Adapter checklist

1. Pass `grounding_provider` / `grounding_provider_chain` into `SearchTool` init/config merge.
2. Preserve `_search_metadata.gemini_grounding.search_entry_point` — do not strip.
3. Implement TOS Path A or B before showing `grounding_answer` to users.
4. On first grounding enable: purge decorator/Redis cache (or rely on `cache_schema_version=m-d.5`).
5. Optional: register `custom_grounding_backends` (e.g. Exa) and put their names in the chain.
6. If middleware also rewrites queries, skip duplicate rewrite when `_search_metadata.rewrite_applied` is true.

```python
tool = SearchTool(
    config=merge_search_tool_init_config(yaml_config),
    custom_grounding_backends=optional_exa_list,
)
```

---

## Package layout (grounding)

```
aiecs/tools/search_tool/
├── core.py                 # SearchTool, search_web / search_batch
├── normalizer.py           # Unified citations / CSE items
├── partition.py            # cse vs grounding profiles
├── cache_fingerprint.py    # Routing fingerprint
├── backends/
│   ├── protocol.py
│   ├── registry.py         # Aliases + custom names
│   ├── credentials.py
│   ├── gemini_grounding.py
│   ├── grok_grounding.py
│   ├── google_cse.py
│   └── async_bridge.py     # Custom async backends only
└── ...
```

---

## Testing

```bash
# M-D.5 phase gates
poetry run pytest test/unit/tools/search_tool/ -v -m "gate_p1 or gate_p2 or gate_p3 or gate_p4 or gate_p5"

# Broader SearchTool suite
poetry run pytest test/unit/tools/test_search_tool.py \
  test/unit/tools/test_search_tool_enhanced.py \
  test/unit/tools/test_search_tool_integration.py -v
```

---

## Enhanced features (unchanged APIs)

Quality scoring, intent analysis, deduplication, context tracking, Redis intelligent cache, and metrics remain available via the existing `enable_*` config flags. `search_news` / `search_images` / `search_videos` remain **CSE-only**.
