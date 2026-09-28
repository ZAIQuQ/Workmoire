#!/usr/bin/env python3
"""Mirror the repository skill into the active Codex skills directory."""
from pathlib import Path
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "personal-workspace-maintenance"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
TARGET = CODEX_HOME / "skills" / SOURCE.name

if not (SOURCE / "SKILL.md").is_file():
    raise SystemExit("repository skill is missing SKILL.md")
TARGET.parent.mkdir(parents=True, exist_ok=True)
if TARGET.exists() or TARGET.is_symlink():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET)
print("synced %s -> %s" % (SOURCE, TARGET))
