"""Coverage for self-contained ZIP archive export/import."""
import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch

import workspace_server as app


class ArchiveHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(
            app,
            DATA_DIR=root,
            FILES_DIR=root / "files",
            DB_PATH=root / "workspace.db",
            SESSION_SECRET="synthetic-archive-secret",
            SETUP_TOKEN="",
        )
        self.config.start()
        self.addCleanup(self.config.stop)
        app.init_db()
        self.server = app.WorkspaceHTTPServer(("127.0.0.1", 0), app.WorkspaceHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = "http://127.0.0.1:%d" % self.server.server_port
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self.request("/api/setup", "POST", {"username": "archive-tester", "password": "synthetic-password"})

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
            response = self.client.open(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.status, status)
            return response.read()

    @staticmethod
    def multipart(filename, content, field="file"):
        boundary = b"----workmoire-test-boundary"
        return (
            b"--" + boundary + b"\r\n"
            + (b'Content-Disposition: form-data; name="' + field.encode() + b'"; filename="' + filename.encode() + b'"\r\n')
            + b"Content-Type: application/zip\r\n\r\n"
            + content + b"\r\n--" + boundary + b"--\r\n",
            "multipart/form-data; boundary=" + boundary.decode(),
        )

    def create_item(self):
        return json.loads(self.request("/api/items", "POST", {"kind": "project", "title": "Archive project", "content": "Keep this"}, status=201))[
            "item"
        ]

    def upload_file(self, item_id):
        body, content_type = self.multipart("paper.txt", b"archive bytes")
        result = json.loads(
            self.request(
                "/api/files",
                "POST",
                body=body,
                headers={"Content-Type": content_type},
                status=201,
            )
        )
        with app.open_db() as con:
            con.execute("UPDATE files SET item_id=? WHERE id=?", (item_id, result["id"]))
            con.commit()
        return result["id"]

    def export_archive(self):
        raw = self.request("/api/export-archive")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(archive.testzip(), None)
            manifest = json.loads(archive.read("manifest.json"))
            members = {name: archive.read(name) for name in archive.namelist() if name != "manifest.json"}
        return manifest, members

    def test_json_export_is_bounded(self):
        with patch.object(app, "MAX_JSON_EXPORT", 100):
            self.request("/api/export", status=413)

    def test_archive_round_trip_contains_attachment_bytes(self):
        item = self.create_item()
        file_id = self.upload_file(item["id"])
        manifest, members = self.export_archive()
        self.assertEqual(manifest["format"], "workmoire-archive")
        self.assertEqual(len(manifest["items"]), 1)
        self.assertEqual(len(manifest["files"]), 1)
        entry = manifest["files"][0]
        self.assertEqual(entry["id"], file_id)
        self.assertEqual(members[entry["archive_path"]], b"archive bytes")

        body, content_type = self.multipart("workmoire-archive.zip", self.request("/api/export-archive"))
        result = json.loads(self.request("/api/import-archive", "POST", body=body, headers={"Content-Type": content_type}, status=201))
        self.assertEqual(result["imported_items"], 1)
        self.assertEqual(result["imported_files"], 1)
        with app.open_db() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM items WHERE deleted_at='' ").fetchone()[0], 2)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM files WHERE deleted_at='' ").fetchone()[0], 2)
            imported = con.execute("SELECT stored_name FROM files WHERE id!=?", (file_id,)).fetchone()
        self.assertEqual((app.FILES_DIR / imported["stored_name"]).read_bytes(), b"archive bytes")

    def test_archive_preserves_timestamps_and_history_activity(self):
        item = self.create_item()
        self.upload_file(item["id"])
        manifest, members = self.export_archive()
        old_created = "2024-01-02T03:04:05.000000Z"
        old_updated = "2024-02-03T04:05:06.000000Z"
        manifest["items"][0]["created_at"] = old_created
        manifest["items"][0]["updated_at"] = old_updated
        manifest["activity"].append({
            "id": 999999,
            "action": "note",
            "target_type": "item",
            "target_id": item["id"],
            "label": "历史活动保留",
            "created_at": old_created,
        })
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
            for name, content in members.items():
                archive.writestr(name, content)
        body, content_type = self.multipart("timestamps.zip", archive_bytes.getvalue())
        result = json.loads(self.request("/api/import-archive", "POST", body=body, headers={"Content-Type": content_type}, status=201))
        self.assertGreaterEqual(result["imported_activity"], 1)
        with app.open_db() as con:
            imported = con.execute(
                "SELECT id,created_at,updated_at FROM items WHERE title=? ORDER BY id DESC LIMIT 1",
                ("Archive project",),
            ).fetchone()
            activity = con.execute(
                "SELECT target_id,created_at FROM activity WHERE label=? ORDER BY id DESC LIMIT 1",
                ("历史活动保留",),
            ).fetchone()
        self.assertEqual(imported["created_at"], old_created)
        self.assertEqual(imported["updated_at"], old_updated)
        self.assertEqual(activity["target_id"], str(imported["id"]))
        self.assertEqual(activity["created_at"], old_created)

    def test_archive_rejects_extra_members_and_bad_checksums_transactionally(self):
        item = self.create_item()
        self.upload_file(item["id"])
        body, content_type = self.multipart("not-a-zip.zip", b"not a zip")
        self.request("/api/import-archive", "POST", body=body, headers={"Content-Type": content_type}, status=400)
        manifest, members = self.export_archive()
        base = json.dumps(manifest, ensure_ascii=False).encode("utf-8")

        malicious = io.BytesIO()
        with zipfile.ZipFile(malicious, "w") as archive:
            archive.writestr("manifest.json", base)
            archive.writestr("extra.txt", b"unexpected")
        body, content_type = self.multipart("bad.zip", malicious.getvalue())
        self.request("/api/import-archive", "POST", body=body, headers={"Content-Type": content_type}, status=400)

        invalid_link_manifest = dict(manifest)
        invalid_link_manifest["files"] = [dict(manifest["files"][0], item_id="missing-item")]
        invalid_link = io.BytesIO()
        with zipfile.ZipFile(invalid_link, "w") as archive:
            archive.writestr("manifest.json", json.dumps(invalid_link_manifest).encode("utf-8"))
            for name, content in members.items():
                archive.writestr(name, content)
        body, content_type = self.multipart("bad-file-link.zip", invalid_link.getvalue())
        self.request("/api/import-archive", "POST", body=body, headers={"Content-Type": content_type}, status=400)

        tampered = io.BytesIO()
        with zipfile.ZipFile(tampered, "w") as archive:
            archive.writestr("manifest.json", base)
            for name, content in members.items():
                archive.writestr(name, content + b"tampered")
        body, content_type = self.multipart("bad-checksum.zip", tampered.getvalue())
        self.request("/api/import-archive", "POST", body=body, headers={"Content-Type": content_type}, status=400)

        with app.open_db() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM items WHERE deleted_at='' ").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM files WHERE deleted_at='' ").fetchone()[0], 1)
        self.assertEqual(list(app.DATA_DIR.glob(".workmoire-import-*")), [])


if __name__ == "__main__":
    unittest.main()
