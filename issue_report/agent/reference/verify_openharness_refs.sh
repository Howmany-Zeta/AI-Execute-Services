#!/usr/bin/env bash
# Verify vendored OpenHarness paths cited in §13 / OPENHARNESS_HOOKS_REFERENCE.md exist at recorded HEAD.
# Usage (from python-middleware-dev root):
#   bash issue_report/agent/reference/verify_openharness_refs.sh
# CI: run on docs/agent-hook changes; fail if tree missing, HEAD drift, or anchor strings absent.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${SCRIPT_DIR}/openharness_refs.manifest"

# Resolve repo root (reference/ is issue_report/agent/reference/)
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "ERROR: manifest not found: ${MANIFEST}" >&2
  exit 1
fi

RECORDED_HEAD=""
ROOT=""
declare -a PATHS=()
declare -a ANCHORS=()

while IFS= read -r line || [[ -n "${line}" ]]; do
  line="${line%%#*}"
  line="$(echo "${line}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "${line}" ]] && continue
  case "${line}" in
    HEAD=*) RECORDED_HEAD="${line#HEAD=}" ;;
    ROOT=*) ROOT="${line#ROOT=}" ;;
    PATH=*) PATHS+=("${line#PATH=}") ;;
    ANCHOR=*) ANCHORS+=("${line#ANCHOR=}") ;;
    *) echo "WARN: unknown manifest line: ${line}" >&2 ;;
  esac
done < "${MANIFEST}"

if [[ -z "${ROOT}" || -z "${RECORDED_HEAD}" ]]; then
  echo "ERROR: manifest must define HEAD= and ROOT=" >&2
  exit 1
fi

OH="${REPO_ROOT}/${ROOT}"
if [[ ! -d "${OH}" ]]; then
  echo "ERROR: OpenHarness tree missing: ${OH}" >&2
  echo "  Clone or submodule to ${ROOT} (see reference/README.md)." >&2
  exit 1
fi

if ! git -C "${OH}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: ${OH} is not a git checkout (cannot verify HEAD)." >&2
  exit 1
fi

ACTUAL_HEAD="$(git -C "${OH}" rev-parse HEAD)"
if [[ "${ACTUAL_HEAD}" != "${RECORDED_HEAD}" ]]; then
  echo "ERROR: OpenHarness HEAD drift." >&2
  echo "  Recorded: ${RECORDED_HEAD}" >&2
  echo "  Actual:   ${ACTUAL_HEAD}" >&2
  echo "  Update openharness_refs.manifest, OPENHARNESS_HOOKS_REFERENCE.md §0, plan §13; refresh excerpts." >&2
  exit 1
fi

missing=0
for rel in "${PATHS[@]}"; do
  if [[ ! -f "${OH}/${rel}" ]]; then
    echo "ERROR: missing cited path: ${ROOT}/${rel}" >&2
    missing=1
  else
    echo "OK path ${rel}"
  fi
done

anchor_fail=0
for entry in "${ANCHORS[@]}"; do
  rel="${entry%%:*}"
  pattern="${entry#*:}"
  if [[ ! -f "${OH}/${rel}" ]]; then
    echo "ERROR: anchor file missing: ${ROOT}/${rel}" >&2
    anchor_fail=1
    continue
  fi
  if ! grep -Fq "${pattern}" "${OH}/${rel}"; then
    echo "ERROR: anchor not found in ${ROOT}/${rel}: ${pattern}" >&2
    anchor_fail=1
  else
    echo "OK anchor ${rel}"
  fi
done

if [[ "${missing}" -ne 0 || "${anchor_fail}" -ne 0 ]]; then
  exit 1
fi

echo "OpenHarness reference check passed (HEAD=${RECORDED_HEAD}, paths=${#PATHS[@]}, anchors=${#ANCHORS[@]})."
