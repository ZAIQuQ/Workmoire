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


if __name__ == "__main__":
    unittest.main()
