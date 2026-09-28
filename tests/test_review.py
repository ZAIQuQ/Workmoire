"""Synthetic HTTP coverage for the daily review queue."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class ReviewHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-review-secret",
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
        self.request("/api/setup", "POST", {"username": "review-tester", "password": "synthetic-password"})

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
        fields.update({"kind": fields.get("kind", "project"), "title": title})
        return self.request("/api/items", "POST", fields, status=201)["item"]

    def test_queue_requires_authentication_and_separates_attention_groups(self):
        self.request("/api/review", anonymous=True, status=401)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        today = date.today().isoformat()
        inbox = self.create("Inbox thought", kind="note")
        inbox_due = self.create("Inbox due thought", kind="note", due_date=yesterday)
        overdue = self.create("Overdue project", due_date=yesterday, status="active")
        due_today = self.create("Today's paper", kind="paper", due_date=today, status="active")
        stale = self.create("Stale project", status="active")
        done = self.create("Done project", due_date=yesterday, status="done")
        with app.open_db() as db:
            db.execute("UPDATE items SET updated_at=? WHERE id=?", ("2020-01-01T00:00:00Z", stale["id"]))
            db.commit()

        review = self.request("/api/review")
        self.assertEqual([item["id"] for item in review["inbox"]], [inbox["id"], inbox_due["id"]])
        self.assertEqual([item["id"] for item in review["overdue"]], [overdue["id"]])
        self.assertEqual([item["id"] for item in review["today"]], [due_today["id"]])
        self.assertEqual([item["id"] for item in review["stale"]], [stale["id"]])
        all_review_ids = {item["id"] for key in ("inbox", "overdue", "today", "stale") for item in review[key]}
        self.assertNotIn(done["id"], all_review_ids)

    def test_updated_status_removes_item_from_its_review_group(self):
        inbox = self.create("Promote me", kind="note")
        overdue = self.create(
            "Complete me", due_date=(date.today() - timedelta(days=1)).isoformat(), status="active"
        )
        for item, status in ((inbox, "active"), (overdue, "done")):
            self.request(
                "/api/items/%d" % item["id"],
                "PUT",
                {
                    "kind": item["kind"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "content": item["content"],
                    "tags": item["tags"],
                    "status": status,
                    "priority": item["priority"],
                    "due_date": item["due_date"],
                    "parent_id": item["parent_id"],
                    "pinned": item["pinned"],
                },
            )
        review = self.request("/api/review")
        self.assertEqual(review["inbox"], [])
        self.assertEqual(review["overdue"], [])


if __name__ == "__main__":
    unittest.main()
