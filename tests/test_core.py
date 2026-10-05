import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import workspace_server as app


class WorkspaceCoreTests(unittest.TestCase):
    def test_password_hash_round_trip(self):
        encoded = app.password_hash("a sufficiently long password")
        self.assertTrue(app.password_matches("a sufficiently long password", encoded))
        self.assertFalse(app.password_matches("wrong password", encoded))

    def test_session_signature_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.multiple(app, DATA_DIR=root, FILES_DIR=root / "files", DB_PATH=root / "workspace.db", SESSION_SECRET="synthetic-session-secret"):
                app.init_db()
                with app.open_db() as con:
                    con.execute("INSERT INTO users(id,username,password_hash,session_version,created_at) VALUES(1,?,?,1,?)", ("reader", app.password_hash("synthetic-password"), app.utc_now()))
                    con.commit()
                token = app.encode_session("reader", 1)
                self.assertEqual(app.decode_session(token), "reader")
                legacy = app.encode_session("reader")
                self.assertIsNone(app.decode_session(legacy))
        body, signature = token.split(".", 1)
        self.assertIsNone(app.decode_session(body + "." + ("0" * len(signature))))

    def test_tags_are_normalized_and_limited(self):
        tags = app.safe_tags("论文，研究, 论文, " + ",".join("x" + str(i) for i in range(20)))
        self.assertEqual(tags.split(",")[0:2], ["论文", "研究"])
        self.assertLessEqual(len(tags.split(",")), 12)

    def test_assistant_is_disabled_without_explicit_binary(self):
        previous = app.CODEX_BIN
        try:
            app.CODEX_BIN = ""
            status = app.assistant_status()
            self.assertFalse(status["configured"])
            self.assertFalse(status["available"])
            with self.assertRaises(RuntimeError):
                app.run_assistant("summarize", "标题", "note", "正文")
        finally:
            app.CODEX_BIN = previous

    def test_assistant_uses_explicit_local_command(self):
        previous = app.CODEX_BIN
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "fake_codex.py"
            script.write_text("import sys\nsys.stdin.read()\nprint('synthetic assistant result')\n", encoding="utf-8")
            try:
                app.CODEX_BIN = sys.executable + " " + str(script)
                result = app.run_assistant("summarize", "标题", "note", "正文")
                self.assertEqual(result, "synthetic assistant result")
            finally:
                app.CODEX_BIN = previous

    def test_assistant_passes_bounded_reasoning_setting(self):
        previous_bin = app.CODEX_BIN
        previous_effort = app.CODEX_REASONING_EFFORT
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "fake_codex_args.py"
            script.write_text("import sys\nsys.stdin.read()\nprint(' '.join(sys.argv[1:]))\n", encoding="utf-8")
            try:
                app.CODEX_BIN = sys.executable + " " + str(script)
                app.CODEX_REASONING_EFFORT = "low"
                result = app.run_assistant("summarize", "标题", "note", "正文")
                self.assertIn("-c model_reasoning_effort=low", result)
            finally:
                app.CODEX_BIN = previous_bin
                app.CODEX_REASONING_EFFORT = previous_effort

    def test_assistant_receives_item_context_metadata(self):
        previous = app.CODEX_BIN
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "fake_codex_context.py"
            script.write_text("import sys\nprint(sys.stdin.read())\n", encoding="utf-8")
            try:
                app.CODEX_BIN = sys.executable + " " + str(script)
                result = app.run_assistant("summarize", "论文标题", "paper", "正文", "研究摘要", "方法,实验")
                self.assertIn("摘要：研究摘要", result)
                self.assertIn("标签：方法,实验", result)
            finally:
                app.CODEX_BIN = previous

    def test_item_rejects_invalid_due_date(self):
        with self.assertRaises(ValueError):
            app.WorkspaceHandler.normalized_item(None, {
                "kind": "note",
                "title": "date test",
                "due_date": "2026-02-30",
            })

    def test_item_rejects_unbounded_body(self):
        with self.assertRaises(ValueError):
            app.WorkspaceHandler.normalized_item(None, {
                "kind": "paper",
                "title": "large outline",
                "content": "x" * (app.MAX_ITEM_CONTENT + 1),
            })

    def test_item_pin_is_normalized(self):
        item = app.WorkspaceHandler.normalized_item(None, {
            "kind": "note",
            "title": "pinned",
            "pinned": True,
        })
        self.assertEqual(item["pinned"], 1)

    def test_workflow_indexes_are_created(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.multiple(app, DATA_DIR=root, FILES_DIR=root / "files", DB_PATH=root / "workspace.db"):
                app.init_db()
                with app.open_db() as con:
                    indexes = {
                        row["name"] for row in con.execute("PRAGMA index_list(items)")
                    }
                    file_indexes = {
                        row["name"] for row in con.execute("PRAGMA index_list(files)")
                    }
                    activity_indexes = {
                        row["name"] for row in con.execute("PRAGMA index_list(activity)")
                    }
                self.assertIn("idx_items_active_updated", indexes)
                self.assertIn("idx_items_status_due", indexes)
                self.assertIn("idx_items_parent", indexes)
                self.assertIn("idx_files_active_created", file_indexes)
                self.assertIn("idx_activity_created", activity_indexes)

    def test_session_secret_example_is_not_accepted(self):
        self.assertNotEqual(app.SESSION_SECRET, "replace-with-a-long-random-secret")


if __name__ == "__main__":
    unittest.main()
