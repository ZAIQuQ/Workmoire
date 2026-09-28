#!/usr/bin/env python3
"""Workmoire (拾序), a private single-user workspace server.

The service intentionally uses only Python's standard library so the Tencent Cloud
instance needs no package build step. SQLite is sufficient for one private user,
and the data directory can be backed up as a single unit.
"""
from __future__ import annotations

import base64
import cgi
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import sqlite3
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "workspace" / "static"


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE settings without overriding the process environment."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[key] = value


load_env_file(ROOT / ".env")
DATA_DIR = Path(os.environ.get("WORKSPACE_DATA_DIR", ROOT / "data"))
FILES_DIR = DATA_DIR / "files"
DB_PATH = DATA_DIR / "workspace.db"
HOST = os.environ.get("WORKSPACE_HOST", "0.0.0.0")
PORT = int(os.environ.get("WORKSPACE_PORT", "5200"))
SESSION_SECRET = os.environ.get("WORKSPACE_SESSION_SECRET", "")
if not SESSION_SECRET:
    SESSION_SECRET = secrets.token_urlsafe(48)

SESSION_TTL = 60 * 60 * 24 * 14
MAX_JSON = 2 * 1024 * 1024
MAX_UPLOAD = 64 * 1024 * 1024
KINDS = {"note", "project", "paper", "log"}
STATUSES = {"inbox", "active", "done", "paused"}
ACTIVITY_LABELS = {
    "create": "创建内容",
    "update": "更新内容",
    "delete": "删除内容",
    "upload": "上传文件",
    "delete_file": "删除文件",
}
LOGIN_FAILURES: dict[str, list[float]] = {}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def open_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db() -> None:
    con = open_db()
    con.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY CHECK(id=1),
          username TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS items(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL CHECK(kind IN ('note','project','paper','log')),
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          content TEXT NOT NULL DEFAULT '',
          tags TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'inbox',
          priority INTEGER NOT NULL DEFAULT 2,
          due_date TEXT NOT NULL DEFAULT '',
          parent_id INTEGER,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(parent_id) REFERENCES items(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS files(
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          stored_name TEXT NOT NULL UNIQUE,
          size INTEGER NOT NULL,
          content_type TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS activity(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          action TEXT NOT NULL,
          target_type TEXT NOT NULL,
          target_id TEXT,
          label TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )
    columns = {row["name"] for row in con.execute("PRAGMA table_info(items)")}
    for name, definition in (
        ("priority", "INTEGER NOT NULL DEFAULT 2"),
        ("due_date", "TEXT NOT NULL DEFAULT ''"),
        ("parent_id", "INTEGER"),
    ):
        if name not in columns:
            con.execute("ALTER TABLE items ADD COLUMN %s %s" % (name, definition))
    con.commit()
    con.close()


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt + digest).decode()


def password_matches(password: str, encoded: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(encoded.encode())
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def encode_session(username: str) -> str:
    payload = ("%s|%d" % (username, int(time.time()) + SESSION_TTL)).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + "." + signature


def decode_session(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    body, signature = token.split(".", 1)
    expected = hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        raw = base64.urlsafe_b64decode((body + "==").encode()).decode()
        username, expires = raw.rsplit("|", 1)
        if not username or int(expires) < int(time.time()):
            return None
        return username
    except Exception:
        return None


def safe_tags(value: object) -> str:
    parts: list[str] = []
    for raw in str(value or "").replace("，", ",").split(","):
        tag = " ".join(raw.strip().split())
        if tag and tag not in parts:
            parts.append(tag[:32])
    return ",".join(parts[:12])


def as_item(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["tags_list"] = [x for x in result.get("tags", "").split(",") if x]
    return result


def log_activity(con: sqlite3.Connection, action: str, target_type: str, target_id: object, label: str) -> None:
    con.execute(
        "INSERT INTO activity(action,target_type,target_id,label,created_at) VALUES(?,?,?,?,?)",
        (action, target_type, str(target_id) if target_id is not None else None, label, utc_now()),
    )


def parse_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length > MAX_JSON:
        raise ValueError("请求内容过大")
    raw = handler.rfile.read(length)
    data = json.loads(raw.decode("utf-8") or "{}")
    if not isinstance(data, dict):
        raise ValueError("请求格式无效")
    return data


class WorkspaceHandler(BaseHTTPRequestHandler):
    server_version = "Workmoire/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print("%s %s" % (self.address_string(), fmt % args), flush=True)

    def current_user(self) -> str | None:
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        token = cookies["workspace_session"].value if cookies.get("workspace_session") else None
        return decode_session(token)

    def json_response(self, data: object, status: int = 200, headers: list[tuple[str, str]] | None = None) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in headers or []:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def error(self, message: str, status: int = 400) -> None:
        self.json_response({"error": message}, status)

    def require_user(self) -> str | None:
        user = self.current_user()
        if not user:
            self.error("请先登录", 401)
            return None
        return user

    def set_login_cookie(self, username: str) -> None:
        self.send_header(
            "Set-Cookie",
            "workspace_session=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=%d"
            % (encode_session(username), SESSION_TTL),
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/healthz":
            self.json_response({"ok": True, "service": "workmoire"})
            return
        if path == "/":
            self.serve_static("index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            requested = unquote(path[len("/static/"):])
            if "/" in requested or requested.startswith("."):
                self.send_error(404)
                return
            self.serve_static(requested)
            return
        if path == "/api/session":
            con = open_db()
            user_row = con.execute("SELECT username FROM users WHERE id=1").fetchone()
            con.close()
            user = self.current_user()
            self.json_response({"setup": user_row is None, "authenticated": bool(user), "username": user})
            return
        if path == "/api/stats":
            if not self.require_user():
                return
            con = open_db()
            counts = {row["kind"]: row["count"] for row in con.execute("SELECT kind, COUNT(*) AS count FROM items GROUP BY kind")}
            status_counts = {row["status"]: row["count"] for row in con.execute("SELECT status, COUNT(*) AS count FROM items GROUP BY status")}
            recent = [as_item(row) for row in con.execute("SELECT * FROM items ORDER BY updated_at DESC LIMIT 8")]
            activity = [dict(row) for row in con.execute("SELECT * FROM activity ORDER BY created_at DESC LIMIT 8")]
            file_bytes = con.execute("SELECT COALESCE(SUM(size),0) FROM files").fetchone()[0]
            con.close()
            self.json_response({"counts": counts, "status_counts": status_counts, "recent": recent, "activity": activity, "file_bytes": file_bytes})
            return
        if path == "/api/items":
            if not self.require_user():
                return
            params = parse_qs(parsed.query)
            kind = params.get("kind", [""])[0]
            status = params.get("status", [""])[0]
            search = params.get("q", [""])[0].strip()
            try:
                limit = min(max(int(params.get("limit", ["200"])[0]), 1), 500)
            except ValueError:
                self.error("无效的数量限制", 400)
                return
            clauses, values = [], []
            if kind in KINDS:
                clauses.append("kind=?")
                values.append(kind)
            if status in STATUSES:
                clauses.append("status=?")
                values.append(status)
            if search:
                clauses.append("(title LIKE ? OR summary LIKE ? OR content LIKE ? OR tags LIKE ?)")
                needle = "%" + search + "%"
                values.extend([needle] * 4)
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            con = open_db()
            rows = con.execute("SELECT * FROM items%s ORDER BY updated_at DESC LIMIT ?" % where, values + [limit]).fetchall()
            con.close()
            self.json_response({"items": [as_item(row) for row in rows]})
            return
        if path.startswith("/api/items/"):
            if not self.require_user():
                return
            try:
                item_id = int(path.rsplit("/", 1)[1])
            except ValueError:
                self.error("无效的内容 ID", 400)
                return
            con = open_db()
            row = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
            con.close()
            if not row:
                self.error("内容不存在", 404)
            else:
                self.json_response({"item": as_item(row)})
            return
        if path == "/api/files":
            if not self.require_user():
                return
            con = open_db()
            rows = con.execute("SELECT id,name,size,content_type,created_at FROM files ORDER BY created_at DESC").fetchall()
            con.close()
            self.json_response({"files": [dict(row) for row in rows]})
            return
        if path.startswith("/files/"):
            if not self.require_user():
                return
            file_id = unquote(path.split("/", 2)[2])
            con = open_db()
            row = con.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
            con.close()
            if not row:
                self.send_error(404)
                return
            target = FILES_DIR / row["stored_name"]
            if not target.is_file():
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", row["content_type"] or "application/octet-stream")
            # Uploaded files are untrusted; do not execute HTML/SVG in this origin.
            self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(row["name"]))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(target.stat().st_size))
            self.end_headers()
            with target.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    self.wfile.write(chunk)
            return
        self.send_error(404)

    def serve_static(self, name: str, content_type: str | None = None) -> None:
        target = STATIC_DIR / name
        if not target.is_file():
            self.send_error(404)
            return
        raw = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(name)[0] or "application/octet-stream")
        self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/setup":
            con = open_db()
            try:
                con.execute("BEGIN IMMEDIATE")
                exists = con.execute("SELECT 1 FROM users WHERE id=1").fetchone()
                if exists:
                    con.rollback()
                    con.close()
                    self.error("空间已经初始化", 409)
                    return
                data = parse_json(self)
                username = str(data.get("username", "")).strip()
                password = str(data.get("password", ""))
                if len(username) < 2 or len(username) > 64:
                    raise ValueError("账号长度应为 2 到 64 个字符")
                if len(password) < 10:
                    raise ValueError("密码至少需要 10 个字符")
                con.execute("INSERT INTO users(id,username,password_hash,created_at) VALUES(1,?,?,?)", (username, password_hash(password), utc_now()))
                con.commit()
                con.close()
                payload = json.dumps({"username": username}, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.set_login_cookie(username)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as exc:
                con.close()
                self.error(str(exc), 400)
            return
        if path == "/api/login":
            try:
                data = parse_json(self)
                username = str(data.get("username", "")).strip()
                address = self.client_address[0]
                now = time.time()
                LOGIN_FAILURES[address] = [stamp for stamp in LOGIN_FAILURES.get(address, []) if stamp > now - 600]
                if len(LOGIN_FAILURES[address]) >= 10:
                    self.error("登录尝试过多，请稍后再试", 429)
                    return
                con = open_db()
                row = con.execute("SELECT username,password_hash FROM users WHERE id=1").fetchone()
                con.close()
                if not row or row["username"] != username or not password_matches(str(data.get("password", "")), row["password_hash"]):
                    LOGIN_FAILURES.setdefault(address, []).append(now)
                    self.error("账号或密码错误", 401)
                    return
                payload = json.dumps({"username": row["username"]}, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.set_login_cookie(row["username"])
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as exc:
                self.error(str(exc), 400)
            return
        if path == "/api/logout":
            self.json_response({"ok": True}, 200, [("Set-Cookie", "workspace_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")])
            return
        if path == "/api/items":
            user = self.require_user()
            if not user:
                return
            try:
                data = self.normalized_item(parse_json(self))
                stamp = utc_now()
                con = open_db()
                cursor = con.execute(
                    "INSERT INTO items(kind,title,summary,content,tags,status,priority,due_date,parent_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (data["kind"], data["title"], data["summary"], data["content"], data["tags"], data["status"], data["priority"], data["due_date"], data["parent_id"], stamp, stamp),
                )
                item_id = cursor.lastrowid
                log_activity(con, "create", "item", item_id, data["title"])
                con.commit()
                row = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
                con.close()
                self.json_response({"item": as_item(row)}, 201)
            except Exception as exc:
                self.error(str(exc), 400)
            return
        if path == "/api/files":
            user = self.require_user()
            if not user:
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_UPLOAD:
                    raise ValueError("文件大小必须在 1 到 64 MB 之间")
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", ""), "CONTENT_LENGTH": str(length)},
                )
                field = form["file"] if "file" in form else None
                if field is None or not getattr(field, "filename", None):
                    raise ValueError("没有选择文件")
                original = Path(field.filename).name[:200]
                file_id = uuid.uuid4().hex
                stored_name = file_id + Path(original).suffix.lower()
                target = FILES_DIR / stored_name
                with target.open("wb") as stream:
                    while chunk := field.file.read(1024 * 1024):
                        stream.write(chunk)
                con = open_db()
                con.execute(
                    "INSERT INTO files(id,name,stored_name,size,content_type,created_at) VALUES(?,?,?,?,?,?)",
                    (file_id, original, stored_name, target.stat().st_size, field.type or mimetypes.guess_type(original)[0] or "application/octet-stream", utc_now()),
                )
                log_activity(con, "upload", "file", file_id, original)
                con.commit()
                con.close()
                self.json_response({"ok": True, "id": file_id}, 201)
            except Exception as exc:
                self.error(str(exc), 400)
            return
        if path == "/api/password":
            user = self.require_user()
            if not user:
                return
            try:
                data = parse_json(self)
                old_password = str(data.get("old_password", ""))
                new_password = str(data.get("new_password", ""))
                if len(new_password) < 10:
                    raise ValueError("新密码至少需要 10 个字符")
                con = open_db()
                row = con.execute("SELECT password_hash FROM users WHERE id=1").fetchone()
                if not row or not password_matches(old_password, row["password_hash"]):
                    con.close()
                    self.error("当前密码错误", 401)
                    return
                con.execute("UPDATE users SET password_hash=? WHERE id=1", (password_hash(new_password),))
                con.commit()
                con.close()
                self.json_response({"ok": True})
            except Exception as exc:
                self.error(str(exc), 400)
            return
        self.error("未找到接口", 404)

    def normalized_item(self, data: dict) -> dict:
        kind = str(data.get("kind", "")).strip()
        title = str(data.get("title", "")).strip()
        if kind not in KINDS:
            raise ValueError("内容类型无效")
        if not title:
            raise ValueError("标题不能为空")
        if len(title) > 200:
            raise ValueError("标题不能超过 200 个字符")
        status = str(data.get("status", "inbox"))
        if status not in STATUSES:
            status = "inbox"
        try:
            priority = min(max(int(data.get("priority", 2)), 1), 3)
        except (TypeError, ValueError):
            priority = 2
        due_date = str(data.get("due_date", "")).strip()[:10]
        parent_id = data.get("parent_id")
        if parent_id in ("", None):
            parent_id = None
        else:
            try:
                parent_id = int(parent_id)
            except (TypeError, ValueError):
                parent_id = None
        return {
            "kind": kind,
            "title": title,
            "summary": str(data.get("summary", "")).strip()[:500],
            "content": str(data.get("content", "")),
            "tags": safe_tags(data.get("tags", "")),
            "status": status,
            "priority": priority,
            "due_date": due_date,
            "parent_id": parent_id,
        }

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        user = self.require_user()
        if not user:
            return
        if path.startswith("/api/items/"):
            try:
                item_id = int(path.rsplit("/", 1)[1])
                data = self.normalized_item(parse_json(self))
                stamp = utc_now()
                con = open_db()
                exists = con.execute("SELECT 1 FROM items WHERE id=?", (item_id,)).fetchone()
                if not exists:
                    con.close()
                    self.error("内容不存在", 404)
                    return
                con.execute(
                    "UPDATE items SET kind=?,title=?,summary=?,content=?,tags=?,status=?,priority=?,due_date=?,parent_id=?,updated_at=? WHERE id=?",
                    (data["kind"], data["title"], data["summary"], data["content"], data["tags"], data["status"], data["priority"], data["due_date"], data["parent_id"], stamp, item_id),
                )
                log_activity(con, "update", "item", item_id, data["title"])
                con.commit()
                row = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
                con.close()
                self.json_response({"item": as_item(row)})
            except Exception as exc:
                self.error(str(exc), 400)
            return
        self.error("未找到接口", 404)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        user = self.require_user()
        if not user:
            return
        if path.startswith("/api/items/"):
            try:
                item_id = int(path.rsplit("/", 1)[1])
            except ValueError:
                self.error("无效的内容 ID")
                return
            con = open_db()
            row = con.execute("SELECT title FROM items WHERE id=?", (item_id,)).fetchone()
            if row:
                con.execute("DELETE FROM items WHERE id=?", (item_id,))
                log_activity(con, "delete", "item", item_id, row["title"])
                con.commit()
            con.close()
            self.json_response({"ok": True})
            return
        if path.startswith("/api/files/"):
            file_id = unquote(path.rsplit("/", 1)[1])
            con = open_db()
            row = con.execute("SELECT name,stored_name FROM files WHERE id=?", (file_id,)).fetchone()
            if row:
                con.execute("DELETE FROM files WHERE id=?", (file_id,))
                log_activity(con, "delete_file", "file", file_id, row["name"])
                con.commit()
                (FILES_DIR / row["stored_name"]).unlink(missing_ok=True)
            con.close()
            self.json_response({"ok": True})
            return
        self.error("未找到接口", 404)


def main() -> None:
    init_db()
    print("workmoire listening on %s:%s, data=%s" % (HOST, PORT, DATA_DIR), flush=True)
    ThreadingHTTPServer((HOST, PORT), WorkspaceHandler).serve_forever()


if __name__ == "__main__":
    main()
