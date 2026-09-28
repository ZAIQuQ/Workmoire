"""Synthetic HTTP coverage for item revision history and restoration."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class HistoryHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-history-secret",
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
        self.request("/api/setup", "POST", {"username": "history-tester", "password": "synthetic-password"})

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

    def create(self, title, content):
        return self.request(
            "/api/items", "POST", {"kind": "paper", "title": title, "content": content}, status=201
        )["item"]

    def update(self, item, content):
        payload = {
            "kind": item["kind"],
            "title": item["title"],
            "summary": item["summary"],
            "content": content,
            "tags": item["tags"],
            "status": item["status"],
            "priority": item["priority"],
            "due_date": item["due_date"],
            "parent_id": item["parent_id"],
            "pinned": item["pinned"],
        }
        return self.request("/api/items/%d" % item["id"], "PUT", payload)["item"]

    def test_history_is_authenticated_and_restore_keeps_an_undo_version(self):
        item = self.create("Revision paper", "initial outline")
        self.request("/api/items/%d/revisions" % item["id"], anonymous=True, status=401)
        updated = self.update(item, "second outline")
        revisions = self.request("/api/items/%d/revisions" % item["id"])["revisions"]
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0]["content"], "initial outline")
        self.update(updated, "third outline")
        revisions = self.request("/api/items/%d/revisions" % item["id"])["revisions"]
        self.assertEqual([revision["content"] for revision in revisions], ["second outline", "initial outline"])
        restored = self.request(
            "/api/items/%d/revisions/%d/restore" % (item["id"], revisions[-1]["id"]),
            "POST",
        )["item"]
        self.assertEqual(restored["content"], "initial outline")
        newest = self.request("/api/items/%d/revisions" % item["id"])["revisions"][0]
        self.assertEqual(newest["content"], "third outline")
        exported = self.request("/api/export")
        self.assertEqual(len(exported["revisions"]), 3)
        self.assertTrue(all(revision["item_id"] == item["id"] for revision in exported["revisions"]))
        self.request("/api/items/%d/revisions/999999/restore" % item["id"], "POST", status=404)


if __name__ == "__main__":
    unittest.main()
