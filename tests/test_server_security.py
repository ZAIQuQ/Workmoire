"""Coverage for public bootstrap protection and HTTP connection limits."""
import json
import io
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

import workspace_server as app


class ServerSecurityHttpTests(unittest.TestCase):
    def start_server(self, bind_host: str, setup_token: str = ""):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-server-security-secret",
            SETUP_TOKEN=setup_token,
        )
        self.config.start()
        app.init_db()
        self.server = app.WorkspaceHTTPServer((bind_host, 0), app.WorkspaceHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_port

    def stop_server(self):
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
        if hasattr(self, "thread"):
            self.thread.join(timeout=3)
        if hasattr(self, "config"):
            self.config.stop()
        if hasattr(self, "temp"):
            self.temp.cleanup()

    def tearDown(self):
        self.stop_server()

    def request(self, path, method="GET", payload=None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.base + path,
            method=method,
            data=body,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            response = urllib.request.urlopen(request, timeout=3)
            status = response.status
            raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read()
        return status, json.loads(raw.decode("utf-8"))

    def test_public_bind_without_token_refuses_bootstrap(self):
        self.start_server("0.0.0.0")
        status, session = self.request("/api/session")
        self.assertEqual(status, 200)
        self.assertTrue(session["setup"])
        self.assertTrue(session["setup_token_required"])

        status, body = self.request(
            "/api/setup",
            "POST",
            {"username": "synthetic-racer", "password": "synthetic-password"},
        )
        self.assertEqual(status, 503)
        self.assertIn("WORKSPACE_SETUP_TOKEN", body["error"])
        with app.open_db() as con:
            self.assertIsNone(con.execute("SELECT 1 FROM users WHERE id=1").fetchone())

    def test_local_bind_can_bootstrap_without_token(self):
        self.start_server("127.0.0.1")
        status, session = self.request("/api/session")
        self.assertEqual(status, 200)
        self.assertFalse(session["setup_token_required"])

        status, body = self.request(
            "/api/setup",
            "POST",
            {"username": "local-tester", "password": "synthetic-password"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["username"], "local-tester")

    def test_public_bind_requires_and_validates_token(self):
        self.start_server("0.0.0.0", "synthetic-bootstrap-token")
        status, session = self.request("/api/session")
        self.assertEqual(status, 200)
        self.assertTrue(session["setup_token_required"])

        status, _ = self.request(
            "/api/setup",
            "POST",
            {
                "setup_token": "wrong-token",
                "username": "token-tester",
                "password": "synthetic-password",
            },
        )
        self.assertEqual(status, 400)
        status, body = self.request(
            "/api/setup",
            "POST",
            {
                "setup_token": "synthetic-bootstrap-token",
                "username": "token-tester",
                "password": "synthetic-password",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["username"], "token-tester")

    def test_server_sets_connection_hardening_attributes(self):
        self.assertTrue(app.WorkspaceHTTPServer.daemon_threads)
        self.assertGreaterEqual(app.WorkspaceHTTPServer.request_queue_size, 64)
        self.assertEqual(app.WorkspaceHTTPServer.request_timeout, 30.0)
        server = app.WorkspaceHTTPServer(("127.0.0.1", 0), app.WorkspaceHandler)
        client = socket.create_connection(server.server_address, timeout=3)
        request, _ = server.get_request()
        try:
            self.assertEqual(request.gettimeout(), 30.0)
        finally:
            request.close()
            client.close()
            server.server_close()

    def test_negative_content_length_is_rejected_before_reading_body(self):
        self.start_server("127.0.0.1")
        client = socket.create_connection(self.server.server_address, timeout=3)
        try:
            client.sendall(
                b"POST /api/login HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: -1\r\n"
                b"Connection: close\r\n\r\n"
                b"{}"
            )
            response = client.recv(4096)
            self.assertIn(b"400", response.split(b"\r\n", 1)[0])
        finally:
            client.close()

    def test_request_logging_drops_query_strings(self):
        handler = object.__new__(app.WorkspaceHandler)
        handler.address_string = lambda: "127.0.0.1"
        output = io.StringIO()
        with redirect_stdout(output):
            handler.log_message('"%s" %s %s', 'GET /api/items?q=private-thought HTTP/1.1', 200, '-')
        line = output.getvalue()
        self.assertIn("GET /api/items 200", line)
        self.assertNotIn("private-thought", line)


if __name__ == "__main__":
    unittest.main()
