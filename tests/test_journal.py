"""Structured civil dates for work logs."""
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class JournalHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-journal-secret",
            SETUP_TOKEN="",
        )
        self.config.start()
        app.init_db()
        self.server = app.WorkspaceHTTPServer(("127.0.0.1", 0), app.WorkspaceHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.addCleanup(self.config.stop)
        self.base = "http://127.0.0.1:%d" % self.server.server_port
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self.request("/api/setup", "POST", {"username": "journal-tester", "password": "synthetic-password"})

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def request(self, path, method="GET", data=None, status=200):
        request = urllib.request.Request(
            self.base + path,
            method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json"},
        )
        try:
            response = self.client.open(request, timeout=3)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.status, status)
            return json.loads(response.read())

    def test_date_filter_is_strict_and_covers_renamed_logs(self):
        first = self.request(
            "/api/items",
            "POST",
            {"kind": "log", "title": "周一记录", "entry_date": "2026-02-03", "content": "初稿"},
            201,
        )["item"]
        self.request(
            "/api/items",
            "POST",
            {"kind": "log", "title": "周二记录", "entry_date": "2026-02-04", "content": "另一条"},
            201,
        )
        renamed = self.request(
            "/api/items/%d" % first["id"],
            "PUT",
            {"kind": "log", "title": "改过的标题", "content": "继续写", "base_updated_at": first["updated_at"]},
        )["item"]
        self.assertEqual(renamed["entry_date"], "2026-02-03")
        filtered = self.request("/api/items?kind=log&entry_date=2026-02-03")
        self.assertEqual([item["id"] for item in filtered["items"]], [first["id"]])
        self.request("/api/items?entry_date=2026-2-03", status=400)
        self.request(
            "/api/items",
            "POST",
            {"kind": "log", "title": "错误日期", "entry_date": "2026-02-30"},
            400,
        )

    def test_export_import_keeps_entry_date_and_legacy_titles_are_inferred(self):
        item = self.request(
            "/api/items",
            "POST",
            {"kind": "log", "title": "日志标题", "entry_date": "2026-04-05"},
            201,
        )["item"]
        exported = self.request("/api/export")
        self.assertEqual(exported["items"][0]["entry_date"], "2026-04-05")
        legacy = {
            "format": "workmoire-export",
            "version": 1,
            "items": [{"id": 991, "kind": "log", "title": "2026年4月6日"}],
            "links": [],
            "files": [],
            "activity": [],
            "revisions": [],
        }
        self.request("/api/import", "POST", legacy, 201)
        imported = self.request("/api/items?kind=log&entry_date=2026-04-06")
        self.assertEqual(len(imported["items"]), 1)
        self.assertNotEqual(imported["items"][0]["id"], item["id"])

    def test_migration_backfills_only_exact_date_titles(self):
        legacy_path = Path(self.temp.name) / "legacy.db"
        with patch.object(app, "DB_PATH", legacy_path):
            con = sqlite3.connect(legacy_path)
            con.executescript(
                """
                CREATE TABLE items(
                  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, title TEXT NOT NULL,
                  summary TEXT NOT NULL DEFAULT '', content TEXT NOT NULL DEFAULT '', tags TEXT NOT NULL DEFAULT '',
                  status TEXT NOT NULL DEFAULT 'inbox', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                INSERT INTO items(id,kind,title,created_at,updated_at) VALUES
                  (1,'log','2026年4月7日','x','x'), (2,'log','自由标题','x','x');
                CREATE TABLE item_revisions(
                  id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL, kind TEXT NOT NULL,
                  title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', content TEXT NOT NULL DEFAULT '',
                  tags TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'inbox',
                  priority INTEGER NOT NULL DEFAULT 2, due_date TEXT NOT NULL DEFAULT '',
                  parent_id INTEGER, pinned INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
                );
                INSERT INTO item_revisions(item_id,kind,title,created_at) VALUES (1,'log','2026-04-08','x');
                """
            )
            con.commit()
            con.close()
            app.init_db()
            con = sqlite3.connect(legacy_path)
            items = dict(con.execute("SELECT id,entry_date FROM items").fetchall())
            revision_date = con.execute("SELECT entry_date FROM item_revisions").fetchone()[0]
            con.close()
        self.assertEqual(items[1], "2026-04-07")
        self.assertEqual(items[2], "")
        self.assertEqual(revision_date, "2026-04-08")


class JournalValidationTests(unittest.TestCase):
    def test_entry_date_requires_real_iso_date(self):
        item = app.WorkspaceHandler.normalized_item(None, {"kind": "log", "title": "valid", "entry_date": "2024-02-29"})
        self.assertEqual(item["entry_date"], "2024-02-29")
        with self.assertRaises(ValueError):
            app.WorkspaceHandler.normalized_item(None, {"kind": "log", "title": "bad", "entry_date": "2023-02-29"})
        with self.assertRaises(ValueError):
            app.WorkspaceHandler.normalized_item(None, {"kind": "log", "title": "bad", "entry_date": "2024-2-09"})


if __name__ == "__main__":
    unittest.main()
