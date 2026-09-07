#!/usr/bin/env bash
# post.sh — create the stable project-root WBS launcher after vendoring.
set -euo pipefail

cat > "$TARGET/wbs.sh" <<'SH'
#!/usr/bin/env bash
# wbs.sh — resolve a project-specific WBS fork before the pristine vendored copy.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN="$HERE/.aai/skills/wbs-toolkit/run.sh"
[ -f "$RUN" ] || RUN="$HERE/.ailib/wbs-toolkit/run.sh"
exec bash "$RUN" "$@"
SH
chmod +x "$TARGET/wbs.sh"

command -v uv >/dev/null 2>&1 || \
  echo "  warn  uv not found on PATH — install uv or ensure python3 has PyYAML"
echo "WBS: bash '$TARGET/wbs.sh' --help"
