import os
import sqlite3
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackupScriptTests(unittest.TestCase):
    def test_creates_snapshot_and_prunes_expired_snapshots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            out = root / "backups"
            (data / "files").mkdir(parents=True)
            (data / "files" / "example.txt").write_text("synthetic", encoding="utf-8")
            with sqlite3.connect(data / "workspace.db") as db:
                db.execute("create table marker (value text)")
                db.execute("insert into marker values ('synthetic')")
                db.commit()

            old_db = out / "workspace-20000101-000000.db"
            old_files = out / "files-20000101-000000.tgz"
            out.mkdir()
            old_db.write_bytes(b"old")
            old_files.write_bytes(b"old")
            old_db.touch()
            old_files.touch()
            old_time = 946684800  # 2000-01-01 UTC
            os.utime(old_db, (old_time, old_time))
            os.utime(old_files, (old_time, old_time))

            env = os.environ.copy()
            env["WORKSPACE_DATA_DIR"] = str(data)
            env["WORKSPACE_BACKUP_RETENTION_DAYS"] = "14"
            result = subprocess.run(
                [str(ROOT / "backup.sh"), str(out)],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            lines = result.stdout.splitlines()
            self.assertEqual(len(lines), 2)
            self.assertFalse(old_db.exists())
            self.assertFalse(old_files.exists())
            snapshot_db, snapshot_files = map(Path, lines)
            self.assertTrue(snapshot_db.exists())
            self.assertTrue(snapshot_files.exists())
            with sqlite3.connect(snapshot_db) as db:
                self.assertEqual(db.execute("select value from marker").fetchone()[0], "synthetic")
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            with tarfile.open(snapshot_files, "r:gz") as archive:
                self.assertIn("files/example.txt", archive.getnames())


if __name__ == "__main__":
    unittest.main()
