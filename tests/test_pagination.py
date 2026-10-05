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

    def test_item_list_omits_full_body_but_keeps_task_summary(self):
        content = "- [ ] First task\n- [x] Finished task\n" + ("long body " * 200)
        item = self.request(
            "/api/items", "POST", {"kind": "note", "title": "Long list item", "content": content}, status=201
        )["item"]
        listed = self.request("/api/items?limit=10")["items"]
        summary = next(row for row in listed if row["id"] == item["id"])
        self.assertNotIn("content", summary)
        self.assertEqual(summary["task_total"], 2)
        self.assertEqual(summary["task_done"], 1)
        self.assertTrue(summary["content_preview"].startswith("- [ ] First task"))
        detail = self.request("/api/items/%d" % item["id"])["item"]
        self.assertEqual(detail["content"], content)

    def test_sort_aware_cursors_cover_the_full_archive(self):
        self.request("/api/items", "POST", {"kind": "note", "title": "Zulu", "priority": 1, "due_date": "", "tags": "alpha"}, status=201)
        self.request("/api/items", "POST", {"kind": "note", "title": "Alpha", "priority": 3, "due_date": "2026-01-03"}, status=201)
        self.request("/api/items", "POST", {"kind": "note", "title": "Bravo", "priority": 2, "due_date": "2026-01-01"}, status=201)
        self.request("/api/items", "POST", {"kind": "note", "title": "Charlie", "priority": 3, "due_date": "2026-01-02"}, status=201)
        for sort in ("updated", "priority", "due", "title"):
            first = self.request("/api/items?sort=%s&limit=2" % sort)
            self.assertEqual(first["sort"], sort)
            self.assertEqual(first["total"], 4)
            second = self.request("/api/items?sort=%s&limit=2&cursor=%s" % (sort, first["next_cursor"]))
            ids = [item["id"] for item in first["items"] + second["items"]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(len(ids), 4)
            if sort == "priority":
                self.assertEqual([item["title"] for item in first["items"]], ["Charlie", "Alpha"])
            elif sort == "due":
                self.assertEqual([item["title"] for item in first["items"]], ["Bravo", "Charlie"])
            elif sort == "title":
                self.assertEqual([item["title"] for item in first["items"]], ["Alpha", "Bravo"])
            if sort != "updated":
                self.request("/api/items?sort=updated&cursor=" + first["next_cursor"], status=400)


if __name__ == "__main__":
    unittest.main()
