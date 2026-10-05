"""Coverage for attachment filtering and reassociation."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class FileHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app, DATA_DIR=root, FILES_DIR=root / "files", DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-files-secret", SETUP_TOKEN="",
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
        self.request("/api/setup", "POST", {"username": "file-tester", "password": "synthetic-password"})

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, path, method="GET", payload=None, body=None, headers=None, status=200):
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request_headers = {"Content-Type": "application/json"} if payload is not None else {}
        request_headers.update(headers or {})
        request = urllib.request.Request(self.base + path, method=method, data=body, headers=request_headers)
        try:
            response = self.client.open(request, timeout=3)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.status, status)
            return json.loads(response.read())

    @staticmethod
    def multipart(filename, content):
        boundary = b"----workmoire-file-boundary"
        body = (
            b"--" + boundary + b"\r\n"
            + b'Content-Disposition: form-data; name="file"; filename="' + filename.encode() + b'"\r\n'
            + b"Content-Type: application/octet-stream\r\n\r\n" + content
            + b"\r\n--" + boundary + b"--\r\n"
        )
        return body, "multipart/form-data; boundary=" + boundary.decode()

    def test_unlinked_file_can_be_filtered_and_reassociated(self):
        item = self.request("/api/items", "POST", {"kind": "project", "title": "File target"}, status=201)["item"]
        body, content_type = self.multipart("notes.txt", b"notes")
        uploaded = self.request("/api/files", "POST", body=body, headers={"Content-Type": content_type}, status=201)
        file_id = uploaded["id"]
        files = self.request("/api/files?linked=no")
        self.assertEqual(files["total"], 1)
        self.assertEqual(files["total_bytes"], 5)
        attached = self.request("/api/files/" + file_id, "PATCH", {"item_id": item["id"]})["file"]
        self.assertEqual(attached["item_id"], item["id"])
        self.assertEqual(attached["item_title"], "File target")
        self.assertEqual(self.request("/api/files?linked=no")["total"], 0)
        self.assertEqual(self.request("/api/files?linked=yes")["total"], 1)
        detached = self.request("/api/files/" + file_id, "PATCH", {"item_id": None})["file"]
        self.assertIsNone(detached["item_id"])


if __name__ == "__main__":
    unittest.main()
