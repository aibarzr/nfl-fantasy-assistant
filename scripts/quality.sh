#!/usr/bin/env bash
set -euo pipefail

workspace_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$workspace_root"

run_check() {
  local component="$1"
  shift
  printf '[%s] %s\n' "$component" "$*"
  if ! "$@"; then
    printf '[%s] failed: %s\n' "$component" "$*" >&2
    return 1
  fi
}

backend_checks() {
  run_check "backend format" uv --directory backend run ruff format --check .
  run_check "backend lint" uv --directory backend run ruff check .
  run_check "backend typecheck" uv --directory backend run mypy src tests
  run_check "backend test" uv --directory backend run pytest
  run_check "OpenAPI contract" ./scripts/check-openapi-contract.sh
  run_check "backend build" uv --directory backend build
}

extension_checks() {
  run_check "extension format" npm --prefix extension run format:check
  run_check "extension lint" npm --prefix extension run lint
  run_check "extension typecheck" npm --prefix extension run typecheck
  run_check "extension test" npm --prefix extension test
  run_check "extension build" npm --prefix extension run build
}

documentation_checks() {
  run_check "documentation links" node scripts/check-doc-links.mjs
  run_check "ESPN fixture sanitization" node scripts/check_espn_spike_fixtures.mjs
}

drift_check() {
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    run_check "tracked-file drift" git diff --exit-code
    run_check "staged-file drift" git diff --cached --exit-code
  else
    printf '[tracked-file drift] skipped: this source snapshot has no Git metadata. CI always runs this check.\n'
  fi
}

usage() {
  printf 'Usage: %s {all|backend|extension|docs|drift}\n' "$0" >&2
}

case "${1:-all}" in
  all)
    backend_checks
    extension_checks
    documentation_checks
    drift_check
    ;;
  backend) backend_checks ;;
  extension) extension_checks ;;
  docs) documentation_checks ;;
  drift) drift_check ;;
  *)
    usage
    exit 2
    ;;
esac
