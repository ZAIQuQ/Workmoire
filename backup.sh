#!/usr/bin/env bash
set -euo pipefail
base="$(cd "$(dirname "$0")" && pwd)"
data="${WORKSPACE_DATA_DIR:-$base/data}"
out="${1:-$base/backups}"
stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out"
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$data/workspace.db" ".backup '$out/workspace-$stamp.db'"
else
  python3 - "$data/workspace.db" "$out/workspace-$stamp.db" <<'PY'
import sqlite3
import sys

source, target = sys.argv[1:]
src = sqlite3.connect(source)
dst = sqlite3.connect(target)
with dst:
    src.backup(dst)
dst.close()
src.close()
PY
fi
tar -C "$data" -czf "$out/files-$stamp.tgz" files
printf '%s\n' "$out/workspace-$stamp.db" "$out/files-$stamp.tgz"
