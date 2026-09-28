#!/usr/bin/env bash
set -euo pipefail
base="$(cd "$(dirname "$0")" && pwd)"
data="${WORKSPACE_DATA_DIR:-$base/data}"
out="${1:-$base/backups}"
retention_days="${WORKSPACE_BACKUP_RETENTION_DAYS:-14}"

case "$retention_days" in
  ''|*[!0-9]*)
    echo "WORKSPACE_BACKUP_RETENTION_DAYS must be a non-negative integer" >&2
    exit 2
    ;;
esac

if [ ! -f "$data/workspace.db" ]; then
  echo "database not found: $data/workspace.db" >&2
  exit 1
fi

stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out"
db_snapshot="$out/workspace-$stamp.db"
files_snapshot="$out/files-$stamp.tgz"
cleanup_failed() {
  rm -f "$db_snapshot" "$files_snapshot"
}
trap cleanup_failed ERR
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$data/workspace.db" ".backup '$db_snapshot'"
else
  python3 - "$data/workspace.db" "$db_snapshot" <<'PY'
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

python3 - "$db_snapshot" <<'PY'
import sqlite3
import sys

with sqlite3.connect(sys.argv[1]) as db:
    result = db.execute("PRAGMA integrity_check").fetchone()[0]
if result != "ok":
    raise SystemExit("backup integrity check failed: %s" % result)
PY

if [ -d "$data/files" ]; then
  tar -C "$data" -czf "$files_snapshot" files
else
  # Keep the backup format stable for a new installation with no uploads yet.
  tar -czf "$files_snapshot" --files-from /dev/null
fi
tar -tzf "$files_snapshot" >/dev/null
trap - ERR

# Prune only the two files produced by this script, and only after both new
# snapshots have been written successfully. mtime is intentionally used here:
# it also makes retention predictable when an operator restores old backups.
find "$out" -maxdepth 1 -type f -name 'workspace-*.db' -mtime "+$retention_days" -delete
find "$out" -maxdepth 1 -type f -name 'files-*.tgz' -mtime "+$retention_days" -delete

printf '%s\n' "$db_snapshot" "$files_snapshot"
