#!/usr/bin/env bash
# run.sh — invoke the WBS CLI for the ambient project that owns this capability.
#
#   bash wbs.sh next
#   bash wbs.sh init docs/prd.md
#   bash wbs.sh done FEATURE-API
#
# A personalized .aai/skills/wbs-toolkit/run.sh may shadow this file. Its app/
# snapshot is optional; when absent, the pinned vendored app remains the runtime.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$HERE"
while [ ! -d "$PROJECT/.aai" ]; do
  [ "$PROJECT" = "/" ] && {
    echo "no .aai/ above $HERE — install wbs-toolkit into a project first" >&2
    exit 1
  }
  PROJECT="$(dirname "$PROJECT")"
done

APP="$HERE/app/wbs.py"
[ -f "$APP" ] || APP="$PROJECT/.ailib/wbs-toolkit/app/wbs.py"
[ -f "$APP" ] || {
  echo "WBS runtime missing: expected $HERE/app/wbs.py or vendored fallback" >&2
  exit 1
}

cd "$PROJECT"
if command -v uv >/dev/null 2>&1; then
  exec uv run --with pyyaml "$APP" "$@"
fi
exec python3 "$APP" "$@"
