import base64
import json
import secrets
import os
import sqlite3
import subprocess
import tarfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_documents as support
import workspace_server as app
import bug_reports

PIXEL=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII=')

class BugReportTests(unittest.TestCase):
    setUp=support.DocumentHttpTests.setUp
    tearDown=support.DocumentHttpTests.tearDown
    request=support.DocumentHttpTests.request
    def payload(self):return {'title':'Synthetic IME report','description':'Type qwe, remove two letters, then confirm the character.','request_key':secrets.token_hex(16),'images':[{'name':'../../synthetic.png','data':base64.b64encode(PIXEL).decode()}]}
    def test_private_report_submission_is_idempotent_and_immutable(self):
        payload=self.payload();self.assertEqual(self.request('/api/bug-reports','POST',payload,anonymous=True)[0],401)
        status,body,_=self.request('/api/bug-reports','POST',payload);self.assertEqual(status,201,body);report=json.loads(body)['report'];report_id=report['id'];image=report['images'][0]
        self.assertEqual(image['name'],'synthetic.png');self.assertNotIn('stored_name',image)
        self.assertEqual(self.request('/api/bug-reports','POST',payload)[0],200)
        self.assertEqual(json.loads(self.request('/api/bug-reports')[1])['total'],1)
        self.assertEqual(self.request('/api/bug-reports/'+report_id,anonymous=True)[0],401)
        self.assertEqual(self.request(image['url'],anonymous=True)[0],401)
        status,raw,headers=self.request(image['url']);self.assertEqual((status,raw),(200,PIXEL));self.assertEqual(headers['Content-Type'],'image/png');self.assertIn('no-store',headers['Cache-Control'])
        for method in ['POST','PATCH','PUT','DELETE']:self.assertEqual(self.request('/api/bug-reports/'+report_id,method,{'title':'Cannot mutate'})[0],405)
        self.assertEqual(json.loads(self.request('/api/bug-reports/'+report_id)[1])['report']['title'],payload['title'])
        self.assertEqual(json.loads(self.request('/api/files')[1])['total'],0)
        self.assertEqual(self.request('/files/'+image['id'])[0],404)
        with app.open_db() as db:self.assertEqual(db.execute('SELECT count(*) FROM items').fetchone()[0],0)
        screenshot=next((app.FILES_DIR/'bug-reports'/report_id).iterdir());self.assertEqual(screenshot.read_bytes(),PIXEL);self.assertEqual(screenshot.stat().st_mode&0o777,0o600)
    def test_invalid_data_origin_and_limits_leave_no_report_or_image(self):
        payload=self.payload();self.assertEqual(self.request('/api/bug-reports','POST',payload,headers={'Origin':'https://example.org'})[0],403)
        variants=[{**payload,'title':''},{**payload,'description':''},{**payload,'request_key':'../bad'},{**payload,'images':payload['images']*6},{**payload,'images':[{'name':'html.png','data':base64.b64encode(b'<script>alert(1)</script>').decode()}]}]
        for value in variants:self.assertEqual(self.request('/api/bug-reports','POST',value)[0],400)
        with patch.object(bug_reports,'MAX_IMAGE',10):self.assertEqual(self.request('/api/bug-reports','POST',payload)[0],400)
        self.assertEqual(json.loads(self.request('/api/bug-reports')[1])['total'],0);self.assertFalse((app.FILES_DIR/'bug-reports').exists())
    def test_failed_file_write_rolls_back_and_report_images_are_separate(self):
        payload=self.payload()
        with patch.object(Path,'chmod',side_effect=OSError('synthetic write failure')):self.assertEqual(self.request('/api/bug-reports','POST',payload)[0],500)
        self.assertEqual(json.loads(self.request('/api/bug-reports')[1])['total'],0)
        self.assertEqual(list((app.FILES_DIR/'bug-reports').iterdir()),[])
        a=json.loads(self.request('/api/bug-reports','POST',self.payload())[1])['report'];b=json.loads(self.request('/api/bug-reports','POST',self.payload())[1])['report']
        self.assertEqual(self.request('/api/bug-reports/'+a['id']+'/images/'+b['images'][0]['id'])[0],404)

    def test_standard_backup_includes_private_reports_and_screenshots(self):
        report=json.loads(self.request('/api/bug-reports','POST',self.payload())[1])['report']
        out=Path(self.temp.name)/'backups'
        result=subprocess.run([str(Path(app.__file__).parent/'backup.sh'),str(out)],env={**os.environ,'WORKSPACE_DATA_DIR':str(app.DATA_DIR),'WORKSPACE_SHARE_DATA_DIR':''},capture_output=True,text=True,check=True)
        database,files=map(Path,result.stdout.splitlines())
        with sqlite3.connect(database) as con:self.assertEqual(con.execute('SELECT title FROM bug_reports WHERE id=?',(report['id'],)).fetchone()[0],report['title'])
        with tarfile.open(files,'r:gz') as archive:
            names=[name for name in archive.getnames() if name.endswith('.png')]
            self.assertEqual(len(names),1);self.assertTrue(names[0].startswith('files/bug-reports/'+report['id']+'/'));self.assertEqual(archive.extractfile(names[0]).read(),PIXEL)
