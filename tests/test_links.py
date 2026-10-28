"""Synthetic HTTP coverage for bidirectional links and portable data."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class LinkHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app, DATA_DIR=root, FILES_DIR=root / "files", DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-link-secret", SETUP_TOKEN="",
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
        self.request("/api/setup", "POST", {"username": "link-tester", "password": "synthetic-password"})
        self.a = self.create("Research", "paper")
        self.b = self.create("Implementation", "project")

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, path, method="GET", data=None, status=200, anonymous=False):
        request = urllib.request.Request(
            self.base + path, method=method,
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

    def create(self, title, kind="note"):
        return self.request("/api/items", "POST", {"kind": kind, "title": title}, status=201)["item"]["id"]

    def link(self, source, target, status=201):
        return self.request(f"/api/items/{source}/links", "POST", {"target_id": target}, status=status)

    def test_authentication_and_validation(self):
        for method, suffix, data in (
            ("GET", "", None), ("POST", "", {"target_id": self.b}),
            ("DELETE", f"/{self.b}", None),
        ):
            self.request(f"/api/items/{self.a}/links{suffix}", method, data, status=401, anonymous=True)
        for target in (None, True, [], {}, 1.5, "bad", self.a):
            self.link(self.a, target, status=400)
        self.link(self.a, 999999, status=404)
        self.request("/api/items/999999/links", status=404)

    def test_symmetric_idempotent_link_and_unlink(self):
        self.link(self.a, self.b)
        self.link(self.b, self.a, status=200)
        for source, target in ((self.a, self.b), (self.b, self.a)):
            rows = self.request(f"/api/items/{source}/links")["items"]
            self.assertEqual([row["id"] for row in rows], [target])
        self.request(f"/api/items/{self.b}/links/{self.a}", "DELETE")
        self.assertEqual(self.request(f"/api/items/{self.a}/links")["items"], [])
        self.assertEqual(self.request(f"/api/items/{self.b}/links")["items"], [])

    def test_trash_restore_and_purge(self):
        self.link(self.a, self.b)
        self.request(f"/api/items/{self.b}", "DELETE")
        self.assertEqual(self.request(f"/api/items/{self.a}/links")["items"], [])
        self.assertEqual(self.request("/api/export")["links"], [])
        self.link(self.a, self.b, status=404)
        self.request(f"/api/trash/items/{self.b}/restore", "POST")
        self.assertEqual(self.request(f"/api/items/{self.a}/links")["items"][0]["id"], self.b)
        self.request(f"/api/items/{self.b}", "DELETE")
        self.request(f"/api/trash/items/{self.b}", "DELETE")
        with app.open_db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM item_links").fetchone()[0], 0)

    def test_export_import_remaps_links_and_accepts_legacy_export(self):
        self.link(self.a, self.b)
        exported = self.request("/api/export")
        self.assertEqual(exported["links"], [{"source_id": self.a, "target_id": self.b}])
        self.request("/api/import", "POST", exported, status=201)
        items = self.request("/api/items")["items"]
        imported = {row["title"]: row["id"] for row in items if row["id"] not in (self.a, self.b)}
        rows = self.request(f"/api/items/{imported['Research']}/links")["items"]
        self.assertEqual([row["id"] for row in rows], [imported["Implementation"]])
        legacy = dict(exported)
        del legacy["links"]
        self.request("/api/import", "POST", legacy, status=201)

    def test_invalid_links_cannot_partially_import_items(self):
        exported = self.request("/api/export")
        before = len(exported["items"])
        for links in ({}, [None], [{"source_id": self.a, "target_id": 999999}],
                      [{"source_id": self.a, "target_id": self.a}]):
            self.request("/api/import", "POST", {**exported, "links": links}, status=400)
            self.assertEqual(len(self.request("/api/items")["items"]), before)


if __name__ == "__main__":
    unittest.main()
