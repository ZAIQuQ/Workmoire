"""Coverage for optimistic edit conflict protection."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class ConflictHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-conflict-secret",
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
        self.request("/api/setup", "POST", {"username": "conflict-tester", "password": "synthetic-password"})

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

    def test_stale_update_is_rejected_without_overwriting_server_content(self):
        original = self.request("/api/items", "POST", {"kind": "note", "title": "原始内容"}, status=201)["item"]
        fresh = self.request(
            "/api/items/%d" % original["id"],
            "PUT",
            {"kind": "note", "title": "其他窗口的更新", "base_updated_at": original["updated_at"]},
        )["item"]
        self.assertNotEqual(original["updated_at"], fresh["updated_at"])
        conflict = self.request(
            "/api/items/%d" % original["id"],
            "PUT",
            {"kind": "note", "title": "过期窗口的覆盖", "base_updated_at": original["updated_at"]},
            status=409,
        )
        self.assertEqual(conflict["item"]["title"], "其他窗口的更新")
        current = self.request("/api/items/%d" % original["id"])["item"]
        self.assertEqual(current["title"], "其他窗口的更新")

    def test_simultaneous_same_base_updates_have_one_winner(self):
        original = self.request("/api/items", "POST", {"kind": "note", "title": "并发原始内容"}, status=201)["item"]
        clients = []
        for _ in range(2):
            client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
            login = urllib.request.Request(
                self.base + "/api/login",
                method="POST",
                data=json.dumps({"username": "conflict-tester", "password": "synthetic-password"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with client.open(login, timeout=3):
                pass
            clients.append(client)
        barrier = threading.Barrier(2)
        outcomes = []

        def update(client, title):
            request = urllib.request.Request(
                self.base + "/api/items/%d" % original["id"],
                method="PUT",
                data=json.dumps({"kind": "note", "title": title, "base_updated_at": original["updated_at"]}).encode(),
                headers={"Content-Type": "application/json"},
            )
            barrier.wait()
            try:
                with client.open(request, timeout=3) as response:
                    outcomes.append(response.status)
            except urllib.error.HTTPError as error:
                outcomes.append(error.code)

        threads = [
            threading.Thread(target=update, args=(clients[0], "并发窗口 A")),
            threading.Thread(target=update, args=(clients[1], "并发窗口 B")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(sorted(outcomes), [200, 409])


if __name__ == "__main__":
    unittest.main()
