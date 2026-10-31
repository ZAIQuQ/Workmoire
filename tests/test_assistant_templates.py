"""Synthetic contract checks for the versioned general assistant templates."""
import json
import unittest
from pathlib import Path

import workspace_server as app


class AssistantTemplateTests(unittest.TestCase):
    def test_public_template_checker_accepts_all_synthetic_cases(self):
        data = json.loads((Path(app.ROOT) / "prompts/evals/document-tasks.json").read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 1)
        self.assertEqual({case["task"] for case in data["cases"]}, set(app.ASSISTANT_TASKS))
        for case in data["cases"]:
            self.assertTrue(case["material"])
            self.assertTrue(case["checks"]["must_include"])
            self.assertTrue(case["checks"]["must_omit"])
            self.assertTrue(case["checks"]["shape"])

    def test_template_loader_uses_the_same_versioned_resources(self):
        for task in app.ASSISTANT_TASKS:
            template = app.document_task_template(task)
            self.assertIn(f"· {task} · v1", template)
            self.assertIn("Markdown", template)


if __name__ == "__main__":
    unittest.main()
