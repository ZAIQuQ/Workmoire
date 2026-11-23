import json
from paper_fixtures import model_fixture, compact_fixture, quality_fixture
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

import test_documents as support
import workspace_server as app
from paper_runtime import PaperRuntime

class PaperRecoveryTests(unittest.TestCase):
    def test_semantic_rejection_is_revised_once_and_requires_a_fresh_review(self):
        source = 'The control and treatment use the same fixed test population.'
        report = json.loads(compact_fixture('Synthetic result'))
        revised = json.loads(compact_fixture('Revised synthetic result'))
        approved = json.loads(quality_fixture(source))
        rejected = {**approved, 'approved': False, 'checks': {**approved['checks'], 'experiments': False},
                    'issues': ['PRIVATE_REVIEW_TEXT']}
        material = {'text': source}
        for last_review in (approved, rejected):
            with self.subTest(approved=last_review['approved']), patch.object(
                app, 'invoke_codex', side_effect=map(json.dumps, [report, rejected, revised, last_review])
            ) as invoke:
                if last_review['approved']:
                    details = app.paper_notes({}, material)
                    self.assertEqual(details['reading']['motivation'], revised['reading']['motivation'])
                else:
                    with self.assertRaises(app.PaperFailure) as failure:
                        app.paper_notes({}, material)
                    self.assertEqual(failure.exception.checks, ('experiments',))
                self.assertEqual(invoke.call_count, 4)
                revision = invoke.call_args_list[2].args[0]
                self.assertIn('重新核对主实验', revision)
                self.assertNotIn('PRIVATE_REVIEW_TEXT', revision)
                self.assertIn('Revised synthetic result', invoke.call_args_list[3].args[0])
                self.assertLess(invoke.call_args_list[-1].kwargs['timeout'], app.PAPER_ASSISTANT_TIMEOUT)

    def test_invalid_evidence_rechecks_the_same_candidate_and_insufficient_budget_skips_repair(self):
        source = 'The control and treatment use the same fixed test population.'
        report = compact_fixture('Synthetic result')
        approved = json.loads(quality_fixture(source))
        invalid = json.dumps({**approved, 'evidence': ['This sentence is absent from the PDF.']})
        with patch.object(app, 'invoke_codex', side_effect=[report, invalid, json.dumps(approved)]) as invoke:
            app.paper_notes({}, {'text': source})
            self.assertEqual(invoke.call_count, 3)
            self.assertEqual(invoke.call_args_list[1].args[0], invoke.call_args_list[2].args[0])
        with patch.object(app, 'PAPER_ASSISTANT_TIMEOUT', 10), patch.object(
            app, 'invoke_codex', side_effect=[report, invalid]
        ) as invoke:
            with self.assertRaises(app.PaperFailure) as failure:
                app.paper_notes({}, {'text': source})
            self.assertEqual(failure.exception.code, 'quality_evidence')
            self.assertEqual(invoke.call_count, 2)


class PaperTimingTests(unittest.TestCase):
    def test_duration_samples_persist_without_paper_content_and_excess_is_not_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=PaperRuntime(Path(directory),'synthetic-profile')
            for value in [20,24,28]:runtime.record(22000,value)
            restored=PaperRuntime(Path(directory),'synthetic-profile');estimate=restored.estimate(22000)
            self.assertEqual(estimate['seconds'],24);self.assertGreater(estimate['high'],24)
            payload=json.loads(runtime.path.read_text());self.assertEqual(set(payload),{'profile','samples'});self.assertEqual(set(payload['samples'][0]),{'characters','seconds'});self.assertEqual(runtime.path.stat().st_mode&0o777,0o600)
            self.assertEqual(PaperRuntime(Path(directory),'changed-profile').estimate(22000)['samples'],0)
            release=threading.Event()
            def work(progress):progress('analyzing');release.wait(3);return {'content':'Synthetic result'}
            job=restored.start('owner',{'text':'x'*22000},work)
            try:
                self.assertIsNone(restored.get('someone-else',job['job_id']))
                self.assertEqual(restored.start('owner',{'text':'x'*22000},work)['job_id'],job['job_id'])
                with self.assertRaises(ValueError):restored.start('owner',{'text':'different'},work)
                with restored.lock:restored.jobs[job['job_id']]['started']-=100
                pending=restored.get('owner',job['job_id']);self.assertTrue(pending['over_estimate']);self.assertLess(pending['progress'],100)
            finally:release.set()
            for _ in range(100):
                result=restored.get('owner',job['job_id'])
                if result['status']!='running':break
                time.sleep(.01)
            self.assertEqual(result['progress'],100);self.assertEqual(result['result']['content'],'Synthetic result')
            with restored.lock:restored.jobs[job['job_id']]['finished']-=901
            self.assertIsNone(restored.get('owner',job['job_id']))

    def test_failed_jobs_share_one_trace_and_exclude_private_details(self):
        with tempfile.TemporaryDirectory() as directory, patch('paper_runtime.print') as log:
            runtime = PaperRuntime(Path(directory), 'synthetic-profile')
            def work(progress):
                progress('verifying')
                raise app.PaperFailure('quality_rejected', '固定提示', ('mechanism',))
            job = runtime.start('owner', {'text': 'PRIVATE_SYNTHETIC_PDF'}, work)
            for _ in range(100):
                result = runtime.get('owner', job['job_id'])
                if result['status'] == 'failed' and log.call_count == 3:
                    break
                time.sleep(.01)
            self.assertEqual(result['trace_id'], job['job_id'])
            self.assertEqual(result['stage'], 'verifying')
            self.assertEqual(result['error_code'], 'quality_rejected')
            self.assertEqual(result['failed_checks'], ['mechanism'])
            self.assertNotIn('result', result)
            events = [json.loads(call.args[0].split(' ', 1)[1]) for call in log.call_args_list]
            self.assertEqual([event['event'] for event in events], ['started', 'stage', 'failed'])
            self.assertEqual({event['trace_id'] for event in events}, {job['job_id']})
            self.assertNotIn('PRIVATE_SYNTHETIC_PDF', str(events))
            self.assertNotIn('固定提示', str(events))

class PaperProgressHttpTests(unittest.TestCase):
    setUp=support.DocumentHttpTests.setUp
    tearDown=support.DocumentHttpTests.tearDown
    request=support.DocumentHttpTests.request
    fixture_file=support.DocumentHttpTests.fixture_file
    def test_raw_upload_keeps_exact_bytes_and_rejects_invalid_association(self):
        raw=b'%PDF-1.4\n'+b'synthetic bytes\n'*30
        def upload(anonymous=False,item=''):
            req=urllib.request.Request(self.base+'/api/files/upload',method='POST',data=raw,headers={'Content-Type':'application/pdf','X-File-Name':'chosen.pdf',**({'X-Item-Id':item} if item else {})})
            try:response=(urllib.request.build_opener() if anonymous else self.client).open(req)
            except urllib.error.HTTPError as e:response=e
            with response:return response.status,response.read()
        self.assertEqual(upload(True)[0],401)
        self.assertEqual(upload(item='999999')[0],400)
        self.assertEqual(list(app.FILES_DIR.iterdir()),[])
        status,body=upload();self.assertEqual(status,201);file=json.loads(body);self.assertEqual(file['size'],len(raw));self.assertEqual(self.request('/files/'+file['id'])[1],raw)
        self.assertFalse(any(p.name.startswith('.upload-') for p in app.FILES_DIR.iterdir()))
    def test_analysis_returns_an_authenticated_job_and_does_not_create_a_document(self):
        self.fixture_file('chosen.pdf',b'%PDF-1.4 synthetic','application/pdf')
        payload={'file_id':'a'*32,'title':'Synthetic paper','text':'Evidence from the selected PDF. '*20,'page_count':1,'pages_read':1,'truncated':False,'generate':True,'background':True}
        release=threading.Event()
        def slow(*args,**kwargs):release.wait(3);return model_fixture(compact_fixture('Synthetic brief.'))(args[0])
        with patch.object(app,'invoke_codex',side_effect=slow):
            status,body,_=self.request('/api/papers/draft','POST',payload);self.assertEqual(status,202);job=json.loads(body)
            try:
                self.assertEqual(self.request('/api/papers/jobs/'+job['job_id'],anonymous=True)[0],401)
                self.assertEqual(self.request('/api/papers/timing',anonymous=True)[0],401)
                snapshot=json.loads(self.request('/api/papers/jobs/'+job['job_id'])[1]);self.assertEqual(snapshot['status'],'running');self.assertEqual(snapshot['progress_kind'],'estimated');self.assertLess(snapshot['progress'],100)
            finally:release.set()
            for _ in range(50):
                result=json.loads(self.request('/api/papers/jobs/'+job['job_id'])[1])
                if result['status']!='running':break
                time.sleep(.02)
        self.assertEqual(result['status'],'completed');self.assertIn('Synthetic brief',result['result']['content'])
        with app.open_db() as con:self.assertEqual(con.execute('SELECT count(*) FROM items').fetchone()[0],0)
