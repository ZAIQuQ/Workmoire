import json
from paper_fixtures import analysis_fixture
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
        def slow(*args,**kwargs):release.wait(3);return analysis_fixture('## 一句话看懂\n\nSynthetic brief.')
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
