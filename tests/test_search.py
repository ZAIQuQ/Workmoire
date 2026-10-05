"""Synthetic HTTP coverage for global search previews and filters."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class SearchHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-search-secret",
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
        self.request("/api/setup", "POST", {"username": "search-tester", "password": "synthetic-password"})

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

    def test_search_returns_context_and_filters_by_kind_and_status(self):
        note = self.create("Capture a design thought", content="The retrieval workflow needs a useful context preview.", tags="search")
        project = self.create("Project planning", kind="project", content="The retrieval workflow belongs in the active project.", status="active")
        result = self.request("/api/search?q=workflow")
        self.assertEqual({item["id"] for item in result["items"]}, {note["id"], project["id"]})
        self.assertIn("workflow", result["items"][0]["snippet"].lower())
        filtered = self.request("/api/search?q=workflow&kind=project&status=active")
        self.assertEqual([item["kind"] for item in filtered["items"]], ["project"])
        self.request("/api/search?q=workflow&kind=invalid", status=400)

    def test_search_prioritizes_title_and_metadata_matches(self):
        body_match = self.create("Unrelated note", content="workflow appears only in the body")
        pinned_body_match = self.create("Pinned unrelated note", content="workflow appears in this body", pinned=True)
        title_match = self.create("Workflow retrieval plan", content="A short outline")
        tag_match = self.create("Tagged note", tags="workflow")
        result = self.request("/api/search?q=workflow")
        ids = [item["id"] for item in result["items"]]
        self.assertLess(ids.index(title_match["id"]), ids.index(tag_match["id"]))
        self.assertLess(ids.index(tag_match["id"]), ids.index(body_match["id"]))
        self.assertLess(ids.index(title_match["id"]), ids.index(pinned_body_match["id"]))


if __name__ == "__main__":
    unittest.main()
