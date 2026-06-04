#!/usr/bin/env bash
# W-006: archive AIECS_SLIMDOWN_EXECUTION_PLAN.md §4.3 verification commands.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

OUT="${ROOT}/issue_report/new_function_request/temporal_kg_memory/artifacts/phase0_verification.txt"
mkdir -p "$(dirname "$OUT")"

_run_rg() {
  local label="$1"
  shift
  echo "## ${label}"
  if command -v rg >/dev/null 2>&1; then
    rg "$@" || true
  else
    echo "# rg not found; grep fallback"
    grep -rE "$1" "${@: -1}" --include='*.py' 2>/dev/null || true
  fi
  echo
}

{
  echo "# Phase 0 verification (execution plan §4.3)"
  echo "# generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "# commit: $(git rev-parse HEAD)"
  echo

  echo "## KG embedded import surface"
  if command -v rg >/dev/null 2>&1; then
    rg 'from aiecs\.(domain|application|infrastructure)\.(knowledge_graph|graph_storage)' aiecs --count || true
  else
    grep -rE 'from aiecs\.(domain|application|infrastructure)\.(knowledge_graph|graph_storage)' aiecs --include='*.py' -c | sort -t: -k2 -nr
  fi
  echo

  echo "## Deprecated tool dirs in tools/__init__.py"
  if command -v rg >/dev/null 2>&1; then
    rg 'apisource|scraper_tool|statistics|knowledge_graph' aiecs/tools/__init__.py || true
  else
    grep -E 'apisource|scraper_tool|statistics|knowledge_graph' aiecs/tools/__init__.py || true
  fi
  echo

  echo "## Agent exports in domain/agent/__init__.py"
  if command -v rg >/dev/null 2>&1; then
    rg 'KnowledgeAwareAgent|GraphAwareAgentMixin' aiecs/domain/agent/__init__.py || true
  else
    grep -E 'KnowledgeAwareAgent|GraphAwareAgentMixin' aiecs/domain/agent/__init__.py || true
  fi
} | tee "${OUT}"
