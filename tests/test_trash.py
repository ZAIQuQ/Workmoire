import json
import sqlite3
import tempfile
import threading
import unittest
from datetime import date, timedelta
import urllib.error
import urllib.request
from pathlib import Path

import workspace_server as app


class TrashHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.saved = {
            "DATA_DIR": app.DATA_DIR,
            "FILES_DIR": app.FILES_DIR,
            "DB_PATH": app.DB_PATH,
            "SETUP_TOKEN": app.SETUP_TOKEN,
            "SESSION_SECRET": app.SESSION_SECRET,
        }
        app.DATA_DIR = root / "data"
        app.FILES_DIR = app.DATA_DIR / "files"
        app.DB_PATH = app.DATA_DIR / "workspace.db"
        app.SETUP_TOKEN = ""
        app.SESSION_SECRET = "synthetic-trash-test-secret"
        app.LOGIN_FAILURES.clear()
        app.init_db()
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.WorkspaceHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        cls.base = "http://127.0.0.1:%d" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        app.DATA_DIR = cls.saved["DATA_DIR"]
        app.FILES_DIR = cls.saved["FILES_DIR"]
        app.DB_PATH = cls.saved["DB_PATH"]
        app.SETUP_TOKEN = cls.saved["SETUP_TOKEN"]
        app.SESSION_SECRET = cls.saved["SESSION_SECRET"]
        cls.temp.cleanup()

    def request(self, path, method="GET", payload=None, expected=200):
        body = None
        headers = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=body, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=3)
            status = response.status
            raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read()
        self.assertEqual(status, expected)
        return json.loads(raw.decode("utf-8"))

    def upload_file(self, item_id, name="linked.txt", payload=b"linked file", expected=201):
        boundary = "----workmoire-test-boundary"
        body = (
            ("--%s\r\n" % boundary).encode()
            + b'Content-Disposition: form-data; name="item_id"\r\n\r\n'
            + str(item_id).encode()
            + b"\r\n"
            + ("--%s\r\n" % boundary).encode()
            + ('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % name).encode()
            + b"Content-Type: text/plain\r\n\r\n"
            + payload
            + b"\r\n--"
            + boundary.encode()
            + b"--\r\n"
        )
        request = urllib.request.Request(
            self.base + "/api/files",
            data=body,
            headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
            method="POST",
        )
        try:
            response = self.opener.open(request, timeout=3)
            status = response.status
            raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read()
        self.assertEqual(status, expected)
        return json.loads(raw.decode("utf-8"))

    def test_z_dashboard_splits_overdue_and_upcoming_open_items(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        captured = self.request(
            "/api/items", "POST", {"kind": "note", "title": "Quick capture synthetic", "content": "remember this", "status": "inbox"}, expected=201
        )["item"]
        self.assertEqual(captured["status"], "inbox")
        self.assertEqual(captured["content"], "remember this")
        overdue = self.request(
            "/api/items", "POST", {"kind": "project", "title": "Overdue synthetic", "due_date": yesterday}, expected=201
        )["item"]
        upcoming = self.request(
            "/api/items", "POST", {"kind": "paper", "title": "Upcoming synthetic", "due_date": tomorrow}, expected=201
        )["item"]
        completed = self.request(
            "/api/items", "POST", {"kind": "log", "title": "Completed synthetic", "due_date": yesterday, "status": "done"}, expected=201
        )["item"]
        stats = self.request("/api/stats")
        self.assertEqual([item["id"] for item in stats["overdue"]], [overdue["id"]])
        self.assertEqual([item["id"] for item in stats["upcoming"]], [upcoming["id"]])
        self.assertIn(overdue["id"], [item["id"] for item in stats["inbox"]])
        self.assertNotIn(completed["id"], [item["id"] for item in stats["overdue"] + stats["upcoming"]])
        promoted = self.request(
            "/api/items/%d" % overdue["id"],
            "PUT",
            {"kind": overdue["kind"], "title": overdue["title"], "summary": overdue["summary"], "content": overdue["content"], "tags": overdue["tags"], "status": "active", "priority": overdue["priority"], "due_date": overdue["due_date"], "parent_id": overdue["parent_id"], "pinned": overdue["pinned"]},
        )["item"]
        self.assertEqual(promoted["status"], "active")
        after_promote = self.request("/api/stats")
        self.assertNotIn(overdue["id"], [item["id"] for item in after_promote["inbox"]])
        completed_from_dashboard = self.request(
            "/api/items/%d" % overdue["id"],
            "PUT",
            {"kind": overdue["kind"], "title": overdue["title"], "summary": overdue["summary"], "content": overdue["content"], "tags": overdue["tags"], "status": "done", "priority": overdue["priority"], "due_date": overdue["due_date"], "parent_id": overdue["parent_id"], "pinned": overdue["pinned"]},
        )["item"]
        self.assertEqual(completed_from_dashboard["status"], "done")
        after_complete = self.request("/api/stats")
        self.assertNotIn(overdue["id"], [item["id"] for item in after_complete["overdue"] + after_complete["upcoming"]])
        for item in (captured, overdue, upcoming, completed):
            self.request("/api/items/%d" % item["id"], "DELETE")
            self.request("/api/trash/items/%d" % item["id"], "DELETE")

    def test_items_can_be_restored_and_permanently_removed(self):
        self.request("/api/setup", "POST", {"username": "tester", "password": "a-long-test-password"})
        parent = self.request("/api/items", "POST", {"kind": "project", "title": "Parent"}, expected=201)["item"]
        pinned = self.request("/api/items/" + str(parent["id"]) + "/pin", "POST", {"pinned": True})["item"]
        self.assertEqual(pinned["pinned"], 1)
        self.assertEqual(self.request("/api/stats")["pinned"][0]["id"], parent["id"])
        child = self.request(
            "/api/items",
            "POST",
            {"kind": "note", "title": "Child", "parent_id": parent["id"]},
            expected=201,
        )["item"]
        before_orphan_check = {path.name for path in app.FILES_DIR.iterdir()}
        self.upload_file(999999, name="rejected.txt", expected=400)
        self.assertEqual(before_orphan_check, {path.name for path in app.FILES_DIR.iterdir()})
        linked_items = self.request(
            "/api/items/%d/links" % parent["id"],
            "POST",
            {"target_id": child["id"]},
            expected=201,
        )["items"]
        self.assertEqual([item["id"] for item in linked_items], [child["id"]])
        self.request(
            "/api/items/%d/links" % parent["id"],
            "POST",
            {"target_id": parent["id"]},
            expected=400,
        )
        self.request(
            "/api/items/%d/links" % parent["id"],
            "POST",
            {"target_id": 999999},
            expected=404,
        )
        self.assertEqual(
            [item["id"] for item in self.request("/api/items/%d/links" % child["id"])["items"]],
            [parent["id"]],
        )
        self.assertEqual(
            [item["id"] for item in self.request("/api/items/%d/links" % parent["id"], "POST", {"target_id": child["id"]})["items"]],
            [child["id"]],
        )
        linked = self.upload_file(parent["id"])
        self.assertEqual(linked["item_id"], parent["id"])
        page = self.request("/api/files?item_id=%d&limit=1&offset=0" % parent["id"])
        self.assertEqual(page["total"], 1)
        self.assertIsNone(page["next_offset"])
        self.request("/api/files?limit=bad", expected=400)
        linked_files = self.request("/api/files?item_id=%d" % parent["id"])["files"]
        self.assertEqual([file["id"] for file in linked_files], [linked["id"]])
        self.assertEqual([file["id"] for file in self.request("/api/files?q=linked")["files"]], [linked["id"]])
        self.assertEqual([file["id"] for file in self.request("/api/files?q=Parent")["files"]], [linked["id"]])
        global_search = self.request("/api/search?q=Parent")
        self.assertIn(parent["id"], [item["id"] for item in global_search["items"]])
        self.assertIn(linked["id"], [file["id"] for file in global_search["files"]])
        self.request("/api/files/%s" % linked["id"], "DELETE")
        self.request("/api/trash/files/%s" % linked["id"], "DELETE")

        child_before_detach = self.request("/api/items/%d" % child["id"])["item"]
        self.request("/api/items/%d" % parent["id"], "DELETE")
        active = self.request("/api/items?limit=20")["items"]
        self.assertEqual([item["id"] for item in active], [child["id"]])
        self.assertIsNone(active[0]["parent_id"])
        self.assertNotEqual(active[0]["updated_at"], child_before_detach["updated_at"])
        self.assertEqual(self.request("/api/items/%d/links" % child["id"])["items"], [])
        trash = self.request("/api/trash")
        self.assertEqual([item["id"] for item in trash["items"]], [parent["id"]])
        self.assertEqual([item["id"] for item in self.request("/api/export")["items"]], [child["id"]])
        self.assertNotIn("project", self.request("/api/stats")["counts"])
        self.assertEqual(self.request("/api/items?q=Parent")["items"], [])

        file_id = "synthetic-file"
        stored_name = "synthetic-file.txt"
        target = app.FILES_DIR / stored_name
        target.write_text("keep me", encoding="utf-8")
        with app.open_db() as db:
            db.execute(
                "INSERT INTO files(id,name,stored_name,size,content_type,created_at) VALUES(?,?,?,?,?,?)",
                (file_id, "notes.txt", stored_name, target.stat().st_size, "text/plain", app.utc_now()),
            )
            db.commit()
        self.request("/api/files/%s" % file_id, "DELETE")
        self.assertFalse(any(file["id"] == file_id for file in self.request("/api/files")["files"]))
        self.assertTrue(any(file["id"] == file_id for file in self.request("/api/trash")["files"]))
        self.assertEqual(self.request("/api/export")["files"], [])
        self.request("/api/trash/files/%s/restore" % file_id, "POST")
        self.assertTrue(any(file["id"] == file_id for file in self.request("/api/files")["files"]))
        self.request("/api/files/%s" % file_id, "DELETE")
        self.request("/api/trash/files/%s" % file_id, "DELETE")
        self.assertFalse(target.exists())

        restored = self.request("/api/trash/items/%d/restore" % parent["id"], "POST")["item"]
        self.assertEqual(restored["title"], "Parent")
        self.assertEqual(self.request("/api/items/%d" % child["id"])["item"]["parent_id"], parent["id"])
        pending_parent = self.request("/api/items", "POST", {"kind": "project", "title": "Pending parent"}, expected=201)["item"]
        pending_child = self.request("/api/items", "POST", {"kind": "note", "title": "Pending child", "parent_id": pending_parent["id"]}, expected=201)["item"]
        self.request("/api/items/%d" % pending_parent["id"], "DELETE")
        detached = self.request("/api/items/%d" % pending_child["id"])["item"]
        self.request(
            "/api/items/%d" % pending_child["id"],
            "PUT",
            {field: detached[field] for field in ("kind", "title", "summary", "content", "tags", "status", "priority", "due_date", "entry_date", "parent_id", "pinned")},
        )
        self.request("/api/trash/items/%d/restore" % pending_parent["id"], "POST")
        self.assertIsNone(self.request("/api/items/%d" % pending_child["id"])["item"]["parent_id"])
        current_child = self.request("/api/items/%d" % child["id"])["item"]
        self.request(
            "/api/items/%d" % child["id"],
            "PUT",
            {field: current_child[field] for field in ("kind", "title", "summary", "content", "tags", "status", "priority", "due_date", "entry_date", "pinned")} | {"parent_id": None},
        )
        self.request("/api/items/%d" % parent["id"], "DELETE")
        self.request("/api/trash/items/%d/restore" % parent["id"], "POST")
        self.assertIsNone(self.request("/api/items/%d" % child["id"])["item"]["parent_id"])
        cycle_root = self.request("/api/items", "POST", {"kind": "project", "title": "Cycle root"}, expected=201)["item"]
        cycle_parent = self.request("/api/items", "POST", {"kind": "project", "title": "Cycle parent", "parent_id": cycle_root["id"]}, expected=201)["item"]
        cycle_child = self.request("/api/items", "POST", {"kind": "note", "title": "Cycle child", "parent_id": cycle_parent["id"]}, expected=201)["item"]
        self.request("/api/items/%d" % cycle_parent["id"], "DELETE")
        root_now = self.request("/api/items/%d" % cycle_root["id"])["item"]
        self.request(
            "/api/items/%d" % cycle_root["id"],
            "PUT",
            {field: root_now[field] for field in ("kind", "title", "summary", "content", "tags", "status", "priority", "due_date", "entry_date", "pinned")} | {"parent_id": cycle_child["id"]},
        )
        restored_cycle = self.request("/api/trash/items/%d/restore" % cycle_parent["id"], "POST")
        self.assertGreaterEqual(restored_cycle["skipped_relationships"], 1)
        self.assertIsNone(self.request("/api/items/%d" % cycle_child["id"])["item"]["parent_id"])
        self.assertEqual(
            [item["id"] for item in self.request("/api/items/%d/links" % parent["id"])["items"]],
            [child["id"]],
        )
        self.request("/api/items/%d/links/%d" % (parent["id"], child["id"]), "DELETE")
        self.assertEqual(self.request("/api/items/%d/links" % parent["id"])["items"], [])
        self.request("/api/items/%d" % parent["id"], "DELETE")
        self.request("/api/trash/items/%d" % parent["id"], "DELETE")
        self.request("/api/items/%d" % parent["id"], expected=404)

class TrashMigrationTests(unittest.TestCase):
    def test_legacy_schema_gets_reversible_delete_columns(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            saved = (app.DATA_DIR, app.FILES_DIR, app.DB_PATH)
            app.DATA_DIR = root / "data"
            app.FILES_DIR = app.DATA_DIR / "files"
            app.DB_PATH = app.DATA_DIR / "workspace.db"
            app.DATA_DIR.mkdir(parents=True)
            with sqlite3.connect(app.DB_PATH) as db:
                db.executescript(
                    """
                    CREATE TABLE users(id INTEGER PRIMARY KEY CHECK(id=1), username TEXT NOT NULL UNIQUE,
                      password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
                    CREATE TABLE items(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
                      title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', content TEXT NOT NULL DEFAULT '',
                      tags TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'inbox',
                      priority INTEGER NOT NULL DEFAULT 2, due_date TEXT NOT NULL DEFAULT '',
                      parent_id INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                    CREATE TABLE files(id TEXT PRIMARY KEY, name TEXT NOT NULL, stored_name TEXT NOT NULL UNIQUE,
                      size INTEGER NOT NULL, content_type TEXT NOT NULL, created_at TEXT NOT NULL);
                    CREATE TABLE activity(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL,
                      target_type TEXT NOT NULL, target_id TEXT, label TEXT NOT NULL, created_at TEXT NOT NULL);
                    """
                )
            try:
                app.init_db()
                with sqlite3.connect(app.DB_PATH) as db:
                    item_columns = {row[1] for row in db.execute("PRAGMA table_info(items)")}
                    file_columns = {row[1] for row in db.execute("PRAGMA table_info(files)")}
                    user_columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
                    link_tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn("deleted_at", item_columns)
                self.assertIn("pinned", item_columns)
                self.assertIn("deleted_at", file_columns)
                self.assertIn("session_version", user_columns)
                self.assertIn("item_links", link_tables)
                self.assertIn("item_trash_meta", link_tables)
            finally:
                app.DATA_DIR, app.FILES_DIR, app.DB_PATH = saved


if __name__ == "__main__":
    unittest.main()
