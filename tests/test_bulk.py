"""Synthetic HTTP coverage for authenticated, transactional bulk triage."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class BulkHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-bulk-secret",
            SETUP_TOKEN="",
        )
        self.config.start()
        self.addCleanup(self.config.stop)
        app.init_db()
        self.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.WorkspaceHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = "http://127.0.0.1:%d" % self.server.server_port
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self.request("/api/setup", "POST", {"username": "bulk-tester", "password": "synthetic-password"})

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, path, method="GET", data=None, status=200, anonymous=False):
        request = urllib.request.Request(
            self.base + path,
            method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json"},
        )
        client = urllib.request.build_opener() if anonymous else self.client
        try:
            response = client.open(request, timeout=3)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.code, status)
            return json.loads(response.read())

    def create(self, title, **fields):
        fields.update({"kind": fields.get("kind", "note"), "title": title})
        return self.request("/api/items", "POST", fields, status=201)["item"]

    def test_bulk_status_is_authenticated_and_creates_revisions(self):
        first = self.create("First inbox")
        second = self.create("Second inbox")
        self.request("/api/items/bulk", "POST", {"ids": [first["id"], second["id"]], "action": "status", "status": "active"})
        items = {item["id"]: item for item in self.request("/api/items")['items']}
        self.assertEqual(items[first["id"]]["status"], "active")
        self.assertEqual(items[second["id"]]["status"], "active")
        self.assertEqual(len(self.request("/api/items/%d/revisions" % first["id"])["revisions"]), 1)
        unchanged = self.request(
            "/api/items/bulk", "POST", {"ids": [first["id"]], "action": "status", "status": "active"}
        )
        self.assertEqual(unchanged["updated"], 0)
        self.request("/api/items/bulk", "POST", {"ids": [first["id"]]}, status=400)
        self.request(
            "/api/items/bulk", "POST", {"ids": [first["id"]], "action": "status", "status": "done"}, anonymous=True, status=401
        )

    def test_bulk_trash_detaches_children_and_rolls_back_invalid_selection(self):
        parent = self.create("Parent", kind="project")
        child = self.create("Child", parent_id=parent["id"])
        survivor = self.create("Survivor")
        self.request("/api/items/bulk", "POST", {"ids": [parent["id"], child["id"]], "action": "trash"})
        active = {item["id"]: item for item in self.request("/api/items")['items']}
        self.assertEqual(set(active), {survivor["id"]})
        trash = {item["id"]: item for item in self.request("/api/trash")["items"]}
        self.assertEqual(set(trash), {parent["id"], child["id"]})
        self.request("/api/trash/items/%d/restore" % child["id"], "POST")
        restored = self.request("/api/items/%d" % child["id"])["item"]
        self.assertIsNone(restored["parent_id"])
        self.request("/api/items/bulk", "POST", {"ids": [survivor["id"], 999999], "action": "trash"}, status=400)
        self.assertEqual(self.request("/api/items/%d" % survivor["id"])["item"]["deleted_at"], "")
        self.request("/api/items/bulk", "POST", {"ids": list(range(1, 102)), "action": "trash"}, status=400)


if __name__ == "__main__":
    unittest.main()
