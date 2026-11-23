"""Paper analysis stays unavailable until the matching build passes acceptance."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import paper_acceptance
from scripts.evaluate_paper_release import score
import test_documents as support
import workspace_server as app


class PaperAcceptanceTests(unittest.TestCase):
    def test_threshold_and_profile_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_file = Path(directory) / 'paper-acceptance.json'
            profile = 'a' * 64
            evidence = {'version': 1, 'profile': profile, 'dataset': 'b' * 64, 'total': 50, 'passed': 45}
            with patch.object(app, 'DATA_DIR', Path(directory)), patch.object(
                app, 'PAPER_PROVIDER_PROFILE', 'synthetic-route'
            ), patch.object(app, 'paper_acceptance_profile', return_value=profile), patch.object(
                app, 'codex_command', return_value=['synthetic']
            ), patch.object(app, 'PAPER_ANALYSIS_REQUESTED', True):
                self.assertFalse(app.paper_analysis_enabled())
                evidence_file.write_text('{')
                self.assertFalse(app.paper_analysis_enabled())
                for overrides in ({'passed': 44}, {'total': 49}, {'passed': 51}, {'profile': 'c' * 64}):
                    evidence_file.write_text(json.dumps({**evidence, **overrides}))
                    self.assertFalse(app.paper_analysis_enabled())
                evidence_file.write_text(json.dumps(evidence))
                self.assertTrue(app.paper_analysis_enabled())
                with patch.object(app, 'PAPER_ANALYSIS_REQUESTED', False):
                    self.assertFalse(app.paper_analysis_enabled())

    def test_scoring_keeps_all_attempts_in_denominator_and_requires_every_review(self):
        ids = [f'{index:064x}' for index in range(50)]
        attempts = [
            {'id': case, 'status': 'preview', 'report': 'Synthetic report'} if index < 46
            else {'id': case, 'status': 'analysis_failed'} for index, case in enumerate(ids)
        ]
        reviews = [{'id': case, 'quality': dict.fromkeys(paper_acceptance.QUALITY_CRITERIA, True)}
                   for case in ids[:46]]
        reviews[0]['quality']['grounding'] = False
        run = {'version': 1, 'dataset': 'c'*64, 'profile': 'd'*64, 'ids': ids, 'attempts': attempts}
        review = {'dataset': run['dataset'], 'reviews': reviews}
        self.assertEqual(score(run, review)['passed'], 45)
        self.assertEqual(score(run, review)['total'], 50)
        with self.assertRaises(ValueError):
            score(run, {**review, 'reviews': reviews[:-1]})
        with self.assertRaises(ValueError):
            score({**run, 'attempts': attempts[:-1]}, review)


class PaperPauseHttpTests(unittest.TestCase):
    setUp = support.DocumentHttpTests.setUp
    tearDown = support.DocumentHttpTests.tearDown
    request = support.DocumentHttpTests.request
    fixture_file = support.DocumentHttpTests.fixture_file

    def test_disabled_analysis_blocks_current_and_legacy_clients_but_allows_pdf_archiving(self):
        self.fixture_file('chosen.pdf', b'%PDF-1.4 synthetic', 'application/pdf')
        payload = {'file_id': 'a' * 32, 'title': 'Synthetic paper'}
        with patch.object(app, 'PAPER_ANALYSIS_REQUESTED', False), patch.object(app, 'invoke_codex') as model:
            self.assertFalse(json.loads(self.request('/api/papers/timing')[1])['available'])
            for options in ({}, {'background': True}, {'generate': True}):
                status, body, _ = self.request('/api/papers/draft', 'POST', {**payload, **options})
                self.assertEqual(status, 503)
                self.assertEqual(json.loads(body)['error_code'], 'paper_analysis_paused')
            status, body, _ = self.request('/api/papers/draft', 'POST', {**payload, 'generate': False})
            self.assertEqual(status, 200)
            self.assertIn('## 原文 PDF', json.loads(body)['content'])
            model.assert_not_called()
