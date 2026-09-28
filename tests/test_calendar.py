"""Synthetic HTTP coverage for the month calendar endpoint."""
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


class CalendarHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-calendar-secret",
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
        self.request("/api/setup", "POST", {"username": "calendar-tester", "password": "synthetic-password"})

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

    def test_calendar_requires_authentication_and_filters_by_month(self):
        self.request("/api/calendar", anonymous=True, status=401)
        current = date.today()
        in_month = self.create("Calendar project", due_date=current.isoformat())
        previous = current.replace(day=1) - timedelta(days=1)
        outside = self.create("Previous month", due_date=previous.isoformat())
        deleted = self.create("Deleted calendar item", due_date=current.isoformat())
        self.request("/api/items/%d" % deleted["id"], "DELETE")
        calendar = self.request("/api/calendar?year=%d&month=%d" % (current.year, current.month))
        self.assertEqual(calendar["year"], current.year)
        self.assertEqual(calendar["month"], current.month)
        self.assertEqual([item["id"] for item in calendar["items"]], [in_month["id"]])
        previous_calendar = self.request("/api/calendar?year=%d&month=%d" % (previous.year, previous.month))
        self.assertEqual([item["id"] for item in previous_calendar["items"]], [outside["id"]])
        self.request("/api/calendar?year=2026&month=13", status=400)


if __name__ == "__main__":
    unittest.main()
