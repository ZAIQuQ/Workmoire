"""Synthetic HTTP coverage for the authenticated relationship map."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class GraphHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-graph-secret",
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
        self.request("/api/setup", "POST", {"username": "graph-tester", "password": "synthetic-password"})

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

    def create(self, title, kind="note", parent_id=None):
        return self.request(
            "/api/items",
            "POST",
            {"kind": kind, "title": title, "parent_id": parent_id},
            status=201,
        )["item"]

    def test_graph_is_authenticated_and_excludes_trashed_nodes(self):
        parent = self.create("Graph project", kind="project")
        child = self.create("Graph paper", kind="paper", parent_id=parent["id"])
        related = self.create("Graph note")
        self.request("/api/items/%d/links" % parent["id"], "POST", {"target_id": related["id"]}, status=201)
        self.request("/api/graph", anonymous=True, status=401)
        graph = self.request("/api/graph")
        self.assertEqual(graph["total"], 3)
        self.assertEqual({node["id"] for node in graph["nodes"]}, {parent["id"], child["id"], related["id"]})
        self.assertEqual(
            {(edge["source_id"], edge["target_id"], edge["kind"]) for edge in graph["edges"]},
            {(parent["id"], child["id"], "hierarchy"), (parent["id"], related["id"], "related")},
        )
        self.request("/api/items/%d" % related["id"], "DELETE")
        graph = self.request("/api/graph?limit=2")
        self.assertEqual(graph["total"], 2)
        self.assertNotIn(related["id"], {node["id"] for node in graph["nodes"]})
        self.request("/api/graph?limit=bad", status=400)


if __name__ == "__main__":
    unittest.main()
