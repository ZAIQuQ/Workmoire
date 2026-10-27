"""Mirror the canonical repository skill into the active Codex skill directory."""
import os
import shutil
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=root/'skills'/'personal-workspace-maintenance'
target=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills'/source.name
shutil.copytree(source,target,dirs_exist_ok=True)
print('Maintenance skill synchronized')
