import unittest

import workspace_server as app


class WorkspaceCoreTests(unittest.TestCase):
    def test_password_hash_round_trip(self):
        encoded = app.password_hash("a sufficiently long password")
        self.assertTrue(app.password_matches("a sufficiently long password", encoded))
        self.assertFalse(app.password_matches("wrong password", encoded))

    def test_session_signature_round_trip(self):
        token = app.encode_session("reader")
        self.assertEqual(app.decode_session(token), "reader")
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

    def test_item_rejects_invalid_due_date(self):
        with self.assertRaises(ValueError):
            app.WorkspaceHandler.normalized_item(None, {
                "kind": "note",
                "title": "date test",
                "due_date": "2026-02-30",
            })

    def test_item_pin_is_normalized(self):
        item = app.WorkspaceHandler.normalized_item(None, {
            "kind": "note",
            "title": "pinned",
            "pinned": True,
        })
        self.assertEqual(item["pinned"], 1)

    def test_session_secret_example_is_not_accepted(self):
        self.assertNotEqual(app.SESSION_SECRET, "replace-with-a-long-random-secret")


if __name__ == "__main__":
    unittest.main()
