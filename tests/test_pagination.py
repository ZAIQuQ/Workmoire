"""Coverage for stable item-list pagination."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class PaginationHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-pagination-secret",
            SETUP_TOKEN="",
        )
        self.config.start()
        app.init_db()
        self.server = app.WorkspaceHTTPServer(("127.0.0.1", 0), app.WorkspaceHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = "http://127.0.0.1:%d" % self.server.server_port
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self.request("/api/setup", "POST", {"username": "pagination-tester", "password": "synthetic-password"})

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

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
            self.assertEqual(response.code, status)
            return json.loads(response.read())

    def test_cursor_pages_are_stable_and_report_total(self):
        created = [self.request("/api/items", "POST", {"kind": "note", "title": "Entry %d" % index}, status=201)["item"] for index in range(5)]
        first = self.request("/api/items?limit=2")
        self.assertEqual(first["total"], 5)
        self.assertEqual(len(first["items"]), 2)
        self.assertTrue(first["next_cursor"])
        second = self.request("/api/items?limit=2&cursor=" + first["next_cursor"])
        self.assertEqual(second["total"], 5)
        self.assertEqual(len(second["items"]), 2)
        self.assertTrue(set(item["id"] for item in first["items"]).isdisjoint(item["id"] for item in second["items"]))
        third = self.request("/api/items?limit=2&cursor=" + second["next_cursor"])
        self.assertEqual([item["id"] for item in first["items"] + second["items"] + third["items"]], [item["id"] for item in reversed(created)])
        self.assertIsNone(third["next_cursor"])

    def test_invalid_cursor_is_rejected(self):
        self.request("/api/items?cursor=not-a-valid-cursor", status=400)


if __name__ == "__main__":
    unittest.main()
