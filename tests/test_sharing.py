"""Public sharing has its own credentials, data surface and revocation boundary."""
import json
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
from share_store import SharePublisher, publication_connection, backup_publications


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
    def publish(self,item,days=7):
        status,body,_=self.request('/api/items/'+str(item['id'])+'/share','POST',{'days':days,'base_updated_at':item['updated_at']});self.assertEqual(status,200,body)
        return json.loads(body)['share']
    def unlock(self,share,client=None):return self.public_request(share['path']+'/unlock','POST',{'password':share['password']},client=client)
    def change(self,item,share,action,**extra):
        status,body,_=self.request('/api/items/'+str(item['id'])+'/share/settings','POST',{'share_id':share['id'],'revision':share['revision'],'action':action,**extra});self.assertEqual(status,200,body);return json.loads(body)['share']

    def test_unpredictable_credentials_durations_and_saved_snapshot(self):
        item=self.create(body_font='serif')
        for days in [1,7,30,0]:
            share=self.publish(item,days);token=share['path'].split('/')[-1]
            self.assertRegex(token,r'^[A-Za-z0-9_-]{43}$');self.assertNotEqual(token,str(item['id']))
            self.assertGreaterEqual(len(share['password']),24)
            for regex in [r'[A-Z]',r'[a-z]',r'[0-9]',r'[^A-Za-z0-9]']:self.assertRegex(share['password'],regex)
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
