"""Public sharing has its own credentials, data surface and revocation boundary."""
import json
import hashlib
from pathlib import Path
import re
import tarfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import test_documents as support
import workspace_server as app
from share_server import ShareHTTPServer, ShareAuth
from share_store import SharePublisher, publication_connection, backup_publications, b64, token_hash


class SharingTests(unittest.TestCase):
    request=support.DocumentHttpTests.request
    fixture_file=support.DocumentHttpTests.fixture_file
    def setUp(self):
        support.DocumentHttpTests.setUp(self)
        self.root=Path(self.temp.name)/'sharing'
        self.share_config=patch.multiple(app,SHARE_DATA_DIR=str(self.root),SHARE_PUBLIC_URL='',SHARE_PORT=5201);self.share_config.start()
        self.publisher=SharePublisher(self.root);self.publisher.initialize()
        self.public=ShareHTTPServer(('127.0.0.1',0),self.root,app.STATIC_DIR,self.root/'auth')
        self.public_thread=threading.Thread(target=self.public.serve_forever,daemon=True);self.public_thread.start()
        self.public_base='http://127.0.0.1:'+str(self.public.server_port)
        self.guest=urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    def tearDown(self):
        self.public.shutdown();self.public.server_close();self.public_thread.join(timeout=3);self.share_config.stop();support.DocumentHttpTests.tearDown(self)
    def public_request(self,path,method='GET',data=None,headers=None,client=None):
        request=urllib.request.Request(self.public_base+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
        try:response=(client or self.guest).open(request,timeout=5)
        except urllib.error.HTTPError as error:response=error
        with response:return response.status,response.read(),dict(response.headers)
    def create(self,title='Shared synthetic note',text='Only this saved text is shared',nodes=None,body_font=None):
        doc={'version':1,'document':{'type':'doc','content':nodes or [{'type':'paragraph','content':[{'type':'text','text':text}]}]}}
        if body_font:doc['document']['attrs']={'bodyFont':body_font}
        status,body,_=self.request('/api/items','POST',{'kind':'note','title':title,'content':text,'rich_content':doc});self.assertEqual(status,201)
        return json.loads(body)['item']
    def publish(self,item,days=7,**extra):
        status,body,_=self.request('/api/items/'+str(item['id'])+'/share','POST',{'days':days,'base_updated_at':item['updated_at'],**extra});self.assertEqual(status,200,body)
        return json.loads(body)['share']
    def unlock(self,share,client=None):return self.public_request(share['path']+'/unlock','POST',{'password':share['password']},client=client)
    def change(self,item,share,action,**extra):
        status,body,_=self.request('/api/items/'+str(item['id'])+'/share/settings','POST',{'share_id':share['id'],'revision':share['revision'],'action':action,**extra});self.assertEqual(status,200,body);return json.loads(body)['share']

    def test_unpredictable_credentials_durations_and_saved_snapshot(self):
        item=self.create(body_font='serif')
        for days in [1,7,30,0]:
            share=self.publish(item,days);token=share['path'].split('/')[-1]
            self.assertTrue(share['password_required'])
            self.assertRegex(token,r'^[A-Za-z0-9_-]{43}$');self.assertNotEqual(token,str(item['id']))
            self.assertRegex(share['password'],r'^[A-Za-z0-9]{16}$')
            for regex in [r'[A-Z]',r'[a-z]',r'[0-9]']:self.assertRegex(share['password'],regex)
            if days:self.assertLess(abs(share['expires_at']-time.time()-days*86400),3)
            else:self.assertIsNone(share['expires_at'])
        with publication_connection(self.root) as con:
            dump='\n'.join(con.iterdump());self.assertNotIn(share['password'],dump);self.assertNotIn(token,dump)
        self.assertEqual((self.root/'publisher.key').stat().st_mode&0o777,0o600)
        self.assertEqual(self.public_request(share['path']+'/document')[0],401)
        status,body,_=self.public_request(share['path']);self.assertEqual(status,200);self.assertNotIn(item['title'].encode(),body)
        self.assertEqual(self.unlock(share)[0],200)
        status,body,_=self.public_request(share['path']+'/document');self.assertEqual(status,200);self.assertIn(item['content'],body.decode());self.assertNotIn('owner_item_id',body.decode());self.assertEqual(json.loads(body)['rich_content']['document']['attrs']['bodyFont'],'serif')
        self.request('/api/items/'+str(item['id']),'PUT',{**item,'content':'New private text','rich_content':None,'base_updated_at':item['updated_at']})
        self.assertNotIn('New private text',self.public_request(share['path']+'/document')[1].decode())
        self.assertEqual(self.request('/api/items/'+str(item['id'])+'/share','POST',{'days':2,'base_updated_at':item['updated_at']})[0],409)

    def test_public_links_allow_anonymous_pdf_reading_and_keep_expiry_revocation_and_backups(self):
        source=self.fixture_file('open.pdf',b'%PDF-1.4 public synthetic bytes','application/pdf')
        item=self.create(nodes=[{'type':'pdf','attrs':{'src':source+'?inline=1','title':'PDF'}}])
        share=self.publish(item,0,password_required=False)
        self.assertFalse(share['password_required']);self.assertIsNone(share['password'])
        self.assertRegex(share['path'],r'^/s/[A-Za-z0-9_-]{43}$')
        status,body,headers=self.public_request(share['path']+'/document')
        self.assertEqual(status,200);self.assertNotIn('Set-Cookie',headers);self.assertIsNone(json.loads(body)['session_expires_at'])
        file=json.loads(body)['rich_content']['document']['content'][0]['attrs']['src']
        self.assertEqual(self.public_request(file,headers={'Range':'bytes=0-4'})[:2],(206,b'%PDF-'))
        self.assertEqual(self.public_request(file,method='HEAD')[0],200)
        self.assertEqual(self.public_request('/api/items')[0],404)
        other=self.publish(self.create('Protected sibling'))
        self.assertEqual(self.public_request(other['path']+'/document')[0],401)
        share=self.change(item,share,'expiry',days=7);self.assertFalse(share['password_required']);self.assertIsNone(share['password'])
        archive=Path(self.temp.name)/'public-shares.tgz';backup_publications(self.root,archive)
        restored=Path(self.temp.name)/'public-restored';restored.mkdir()
        with tarfile.open(archive,'r:gz') as snapshot:snapshot.extractall(restored)
        recovered=SharePublisher(restored).latest(item['id'])
        self.assertFalse(recovered['password_required']);self.assertEqual(recovered['path'],share['path']);self.assertIsNone(recovered['password'])
        with publication_connection(self.root,True) as con:con.execute('UPDATE shares SET expires_at=? WHERE id=?',(int(time.time())-1,share['id']))
        for path in [share['path']+'/document',file]:self.assertEqual(self.public_request(path)[0],404)
        share=self.change(item,share,'expiry',days=0);self.assertEqual(self.public_request(file)[0],200)
        self.change(item,share,'revoke')
        for path in [share['path']+'/document',file]:self.assertEqual(self.public_request(path)[0],404)
        share=self.publish(item,password_required=False)
        self.assertEqual(self.request('/api/items/'+str(item['id']),'DELETE')[0],200)
        self.request('/api/trash/items/'+str(item['id'])+'/restore','POST',{})
        self.assertEqual(self.public_request(share['path']+'/document')[0],404)

    def test_toggling_protection_relocks_content_and_files_with_fresh_credentials(self):
        source=self.fixture_file('toggle.pdf',b'%PDF-1.4 toggle bytes','application/pdf')
        item=self.create(nodes=[{'type':'pdf','attrs':{'src':source+'?inline=1','title':'PDF'}}])
        protected=self.publish(item);self.assertEqual(self.unlock(protected)[0],200)
        file=json.loads(self.public_request(protected['path']+'/document')[1])['rich_content']['document']['content'][0]['attrs']['src']
        opened=self.change(item,protected,'protection',password_required=False)
        self.assertEqual(opened['path'],protected['path']);self.assertFalse(opened['password_required']);self.assertIsNone(opened['password'])
        anonymous=urllib.request.build_opener()
        for path in [opened['path']+'/document',file]:self.assertEqual(self.public_request(path,client=anonymous)[0],200)
        relocked=self.change(item,opened,'protection',password_required=True)
        self.assertEqual(relocked['path'],protected['path']);self.assertTrue(relocked['password_required'])
        self.assertNotEqual(relocked['password'],protected['password']);self.assertRegex(relocked['password'],r'^[A-Za-z0-9]{16}$')
        for client in [self.guest,anonymous]:
            for path in [relocked['path']+'/document',file]:
                self.assertEqual(self.public_request(path,client=client)[0],401)
                self.assertEqual(self.public_request(path,method='HEAD',client=client)[0],401)
        self.assertEqual(self.unlock(protected)[0],401);self.assertEqual(self.unlock(relocked)[0],200)
        self.assertEqual(self.public_request(file)[0],200)
        self.assertEqual(self.change(item,relocked,'protection',password_required=True),relocked)

    def test_protection_changes_require_explicit_boolean_current_revision_and_owner(self):
        item=self.create();share=self.publish(item)
        endpoint='/api/items/'+str(item['id'])+'/share'
        for invalid in [None,0,1,'false',[],{}]:
            self.assertEqual(self.request(endpoint,'POST',{'base_updated_at':item['updated_at'],'password_required':invalid})[0],400)
            self.assertEqual(self.request(endpoint+'/settings','POST',{'share_id':share['id'],'revision':share['revision'],'action':'protection','password_required':invalid})[0],400)
        payload={'share_id':share['id'],'revision':share['revision'],'action':'protection','password_required':False}
        self.assertEqual(self.request(endpoint+'/settings','POST',payload,anonymous=True)[0],401)
        self.assertEqual(self.publisher.latest(item['id']),share)
        opened=self.change(item,share,'protection',password_required=False)
        self.assertEqual(self.request(endpoint+'/settings','POST',{**payload,'password_required':True})[0],400)
        self.assertEqual(self.request(endpoint+'/settings','POST',{**payload,'revision':opened['revision'],'action':'password'})[0],400)
        self.assertFalse(self.publisher.latest(item['id'])['password_required'])

    def test_legacy_schema_migrates_to_protected_without_changing_credentials_or_records(self):
        item=self.create();share=self.publish(item)
        with publication_connection(self.root,True) as con:
            con.execute('ALTER TABLE shares DROP COLUMN password_required')
            original=dict(con.execute('SELECT * FROM shares WHERE id=?',(share['id'],)).fetchone())
        self.assertEqual(self.public_request(share['path']+'/document')[0],401)
        self.publisher.initialize();self.publisher.initialize()
        with publication_connection(self.root) as con:
            migrated=dict(con.execute('SELECT * FROM shares WHERE id=?',(share['id'],)).fetchone())
            self.assertEqual(migrated.pop('password_required'),1);self.assertEqual(migrated,original)
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertEqual(self.publisher.latest(item['id']),share);self.assertEqual(self.unlock(share)[0],200)

    def test_legacy_passwords_and_links_survive_until_explicit_password_reset(self):
        key=bytes(range(32));(self.root/'publisher.key').write_bytes(key)
        row={'key_id':token_hash(b64(key)),'link_nonce':'legacy-test-link','password_nonce':'legacy-test-nonce'}
        token,password=self.publisher.credentials(row)
        self.assertEqual(hashlib.sha256(password.encode()).hexdigest(),'868b98e495dd2291ef379f875d26e3c17641fb109ceffe1d1c444973ea626985')
        self.assertEqual(token_hash(token),'ad962c094de8f6bc924850a4bc55e65b136bb1620a2df769580008c627b2e698')
        item=self.create()
        with patch('share_store.new_password_nonce',return_value='legacy-test-nonce'):
            share=self.publish(item,0)
        self.assertEqual(share['password'],password);self.assertEqual(self.unlock(share)[0],200)
        recovered=SharePublisher(self.root).latest(item['id'])
        self.assertEqual(recovered['password'],password);self.assertEqual(recovered['path'],share['path'])
        changed=self.change(item,recovered,'expiry',days=7)
        self.assertEqual(changed['password'],password);self.assertEqual(self.public_request(share['path']+'/document')[0],200)
        reset=self.change(item,changed,'password')
        self.assertRegex(reset['password'],r'^[A-Za-z0-9]{16}$');self.assertEqual(reset['path'],share['path'])
        self.assertEqual(self.public_request(share['path']+'/document')[0],401)
        self.assertEqual(self.unlock(share)[0],401);self.assertEqual(self.unlock(reset)[0],200)

    def test_new_passwords_are_recoverable_alphanumeric_and_include_all_character_classes(self):
        key=(self.root/'publisher.key').read_bytes();seen=set()
        for index in range(64):
            row={'key_id':token_hash(b64(key)),'link_nonce':'synthetic-link','password_nonce':'v2:synthetic-'+str(index)}
            token,password=self.publisher.credentials(row)
            self.assertRegex(password,r'^[A-Za-z0-9]{16}$')
            for pattern in ['[A-Z]','[a-z]','[0-9]']:self.assertRegex(password,pattern)
            self.assertEqual(self.publisher.credentials(row),(token,password));seen.add(password)
        self.assertEqual(len(seen),64)

    def test_backup_restores_links_passwords_and_media_without_reader_sessions(self):
        source=self.fixture_file('synthetic.pdf',b'%PDF-1.4 backup bytes','application/pdf')
        item=self.create(nodes=[{'type':'pdf','attrs':{'src':source+'?inline=1','title':'PDF'}}])
        share=self.publish(item);self.assertEqual(self.unlock(share)[0],200)
        archive=Path(self.temp.name)/'shares.tgz';backup_publications(self.root,archive)
        restored=Path(self.temp.name)/'restored';restored.mkdir()
        with tarfile.open(archive,'r:gz') as snapshot:
            self.assertFalse(any(name.startswith('auth') for name in snapshot.getnames()))
            snapshot.extractall(restored)
        recovered=SharePublisher(restored).latest(item['id'])
        self.assertEqual(recovered['password'],share['password']);self.assertEqual(recovered['path'],share['path'])
        self.assertEqual(next((restored/'media').iterdir()).read_bytes(),b'%PDF-1.4 backup bytes')
        self.assertEqual(archive.stat().st_mode&0o777,0o600)

    def test_only_referenced_media_and_no_workspace_routes_are_available(self):
        source=self.fixture_file('synthetic.pdf',b'%PDF-1.4 synthetic bytes','application/pdf')
        item=self.create(nodes=[{'type':'paragraph','content':[{'type':'documentLink','attrs':{'id':999,'title':'Related title'}}]},{'type':'pdf','attrs':{'src':source+'?inline=1','title':'PDF'}}])
        share=self.publish(item)
        self.assertEqual(self.request('/api/items/'+str(item['id'])+'/share',anonymous=True)[0],401)
        cookie=app.encode_session('synthetic-reader',1)
        self.assertEqual(self.public_request(share['path']+'/document',headers={'Cookie':'workspace_session='+cookie})[0],401)
        self.assertEqual(self.unlock(share)[0],200)
        body=json.loads(self.public_request(share['path']+'/document')[1]);document=body['rich_content']['document'];self.assertEqual(document['content'][0]['content'][0],{'type':'text','text':'Related title'})
        file=document['content'][1]['attrs']['src'];self.assertNotIn('a'*32,file)
        status,raw,headers=self.public_request(file,headers={'Range':'bytes=0-4'});self.assertEqual((status,raw),(206,b'%PDF-'));self.assertEqual(headers['Referrer-Policy'],'no-referrer')
        self.assertEqual(self.public_request(share['path']+'/files/'+'b'*32)[0],404)
        for path in ['/','/api/items','/api/session','/api/export','/files/'+'a'*32,'/static/app.js','/static/../published.db','/published.db']:
            self.assertEqual(self.public_request(path)[0],404,path)
        self.assertEqual(self.public_request('/api/items','POST',{'title':'Cannot write'})[0],404)
        self.assertEqual(self.public_request(file,client=urllib.request.build_opener())[0],401)
        # A grant for one link never unlocks another link, even for the same content.
        other=self.publish(self.create('Other note'));self.assertEqual(self.public_request(other['path']+'/document')[0],401)

    def test_expiry_password_reset_and_revocation_apply_to_existing_sessions(self):
        item=self.create();share=self.publish(item);self.assertEqual(self.unlock(share)[0],200)
        reset=self.change(item,share,'password');self.assertNotEqual(reset['password'],share['password']);self.assertEqual(reset['path'],share['path']);self.assertEqual(self.public_request(share['path']+'/document')[0],401)
        self.assertEqual(self.unlock(reset)[0],200)
        with publication_connection(self.root,True) as con:con.execute('UPDATE shares SET expires_at=? WHERE id=?',(int(time.time())-1,share['id']))
        self.assertEqual(self.public_request(share['path']+'/document')[0],404)
        refreshed=self.change(item,reset,'expiry',days=30);self.assertTrue(refreshed['active']);self.assertEqual(self.unlock(refreshed)[0],200)
        self.assertIsNone(self.change(item,refreshed,'revoke'));self.assertEqual(self.public_request(share['path']+'/document')[0],404);self.assertEqual(self.unlock(refreshed)[0],404)

    def test_rate_limits_persist_and_cannot_be_evaded_with_forwarded_headers(self):
        share=self.publish(self.create())
        for i in range(5):self.assertEqual(self.public_request(share['path']+'/unlock','POST',{'password':'wrong'},headers={'X-Forwarded-For':'synthetic-'+str(i)})[0],401)
        status,_,headers=self.unlock(share);self.assertEqual(status,429);self.assertGreater(int(headers['Retry-After']),0)
        self.public.auth=ShareAuth(self.root/'auth');self.assertEqual(self.unlock(share)[0],429)

    def test_document_trash_revokes_snapshot_and_origin_checks_prevent_cross_port_changes(self):
        item=self.create();share=self.publish(item);self.assertEqual(self.unlock(share)[0],200)
        self.assertEqual(self.request('/api/items/'+str(item['id'])+'/share','POST',{'days':7,'base_updated_at':item['updated_at']},headers={'Origin':'https://unrelated.example'})[0],403)
        self.assertEqual(self.public_request(share['path']+'/unlock','POST',{'password':share['password']},headers={'Origin':'https://unrelated.example'})[0],403)
        self.assertEqual(self.request('/api/items/'+str(item['id']),'DELETE')[0],200)
        self.assertEqual(self.public_request(share['path']+'/document')[0],404)
        self.request('/api/trash/items/'+str(item['id'])+'/restore','POST',{})
        self.assertEqual(self.public_request(share['path']+'/document')[0],404)
