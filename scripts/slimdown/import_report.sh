#!/usr/bin/env bash
# W-003: repeatable KG/graph_storage import surface report (Phase 0 baseline).
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

PATTERN='from aiecs\.(domain|application|infrastructure)\.(knowledge_graph|graph_storage)'
OUT="${ROOT}/issue_report/new_function_request/temporal_kg_memory/artifacts/import_report.txt"

mkdir -p "$(dirname "$OUT")"

{
  echo "# AIECS slimdown import report"
  echo "# generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "# commit: $(git rev-parse HEAD)"
  echo "# pattern: ${PATTERN}"
  echo
  if command -v rg >/dev/null 2>&1; then
    rg "${PATTERN}" aiecs --count
  else
    echo "# rg not found; using grep -rE (non-zero matches only)"
    grep -rE "${PATTERN}" aiecs --include='*.py' -c | awk -F: '$2+0>0' | sort -t: -k2 -nr
  fi
} | tee "${OUT}"
