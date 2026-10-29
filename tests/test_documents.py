"""Media previews and explicit, source-grounded paper drafting boundaries."""
import io
import json
import os
import signal
import sys
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import paper_tools
import workspace_server as app


class DocumentHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = patch.multiple(app, DATA_DIR=root, FILES_DIR=root/'files', DB_PATH=root/'workspace.db', SESSION_SECRET='synthetic-documents-secret', SETUP_TOKEN='')
        self.config.start()
        app.init_db()
        self.server = app.WorkspaceHTTPServer(('127.0.0.1', 0), app.WorkspaceHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:%s' % self.server.server_port
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self.request('/api/setup', 'POST', {'username':'synthetic-reader','password':'synthetic-password'})

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.config.stop()
        self.temp.cleanup()

    def request(self, path, method='GET', data=None, headers=None, anonymous=False):
        request = urllib.request.Request(self.base+path, method=method, data=json.dumps(data).encode() if data is not None else None, headers={'Content-Type':'application/json', **(headers or {})})
        client = urllib.request.build_opener() if anonymous else self.client
        try:
            response = client.open(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), dict(response.headers)

    def fixture_file(self, name, raw, content_type):
        file_id = 'a' * 32
        target = app.FILES_DIR / (file_id + Path(name).suffix)
        target.write_bytes(raw)
        with app.open_db() as con:
            con.execute('INSERT INTO files(id,name,stored_name,size,content_type,created_at) VALUES(?,?,?,?,?,?)', (file_id,name,target.name,len(raw),content_type,app.utc_now()))
        return '/files/' + file_id

    def test_pdf_is_authenticated_inline_and_supports_ranges(self):
        raw=b'%PDF-1.4\nsynthetic-pdf-content'
        path=self.fixture_file('paper.pdf',raw,'text/html')
        status,_,_=self.request(path+'?inline=1', anonymous=True)
        self.assertEqual(status,401)
        status,body,headers=self.request(path+'?inline=1')
        self.assertEqual((status,body),(200,raw))
        self.assertEqual(headers['Content-Type'],'application/pdf')
        self.assertTrue(headers['Content-Disposition'].startswith('inline;'))
        self.assertIn("frame-ancestors 'self'",headers['Content-Security-Policy'])
        status,body,headers=self.request(path+'?inline=1',headers={'Range':'bytes=0-4'})
        self.assertEqual((status,body),(206,b'%PDF-'))
        self.assertEqual(headers['Content-Range'],'bytes 0-4/%s'%len(raw))
        status,body,_=self.request(path,headers={'Range':'bytes=-7'})
        self.assertEqual((status,body),(206,raw[-7:]))
        status,_,headers=self.request(path,headers={'Range':'bytes=900-901'})
        self.assertEqual(status,416)
        self.assertEqual(headers['Content-Range'],'bytes */%s'%len(raw))

    def test_untrusted_html_or_svg_cannot_be_rendered_inline(self):
        path=self.fixture_file('pretend.png',b'<svg onload="alert(1)"></svg>','image/png')
        status,_,headers=self.request(path+'?inline=1')
        self.assertEqual(status,200)
        self.assertEqual(headers['Content-Type'],'application/octet-stream')
        self.assertTrue(headers['Content-Disposition'].startswith('attachment;'))
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])

    def test_vendor_assets_and_path_traversal(self):
        status,_,headers=self.request('/static/vendor/katex.min.css')
        self.assertEqual(status,200)
        status,_,_=self.request('/static/vendor/fonts/KaTeX_Main-Regular.woff2')
        self.assertEqual(status,200)
        status,_,_=self.request('/static/%2e%2e%2fworkspace_server.py')
        self.assertEqual(status,404)
        status,_,headers=self.request('/')
        self.assertEqual(status,200)
        self.assertEqual(headers['Cache-Control'],'no-cache')
        status,body,headers=self.request('/static/vendor/editor.js',method='HEAD')
        self.assertEqual(status,200)
        self.assertEqual(body,b'')

    def test_paper_endpoints_require_authentication_before_network_or_generation(self):
        with patch.object(paper_tools,'lookup_papers') as lookup, patch.object(app,'invoke_codex') as invoke, patch.object(paper_tools,'fetch_public') as fetch:
            for path in ['/api/papers/lookup','/api/papers/draft','/api/papers/pdf','/api/papers/prepare']:
                self.assertEqual(self.request(path,'POST',{'reference':'Synthetic title'},anonymous=True)[0],401)
            lookup.assert_not_called()
            invoke.assert_not_called()
            fetch.assert_not_called()


class PaperNetworkTests(unittest.TestCase):
    def test_rejects_private_addresses_and_non_https_sources(self):
        for url in ['http://example.org','https://user:pass@example.org','https://example.org:8080/']:
            with self.assertRaises(ValueError):paper_tools.public_url(url)
        for address in ['127.0.0.1','10.0.0.1','169.254.0.23','::1','::ffff:127.0.0.1']:
            with patch.object(paper_tools.socket,'getaddrinfo',return_value=[(None,None,None,None,(address,443))]):
                with self.assertRaises(ValueError):paper_tools.public_addresses('untrusted.example')

    def test_redirect_cannot_reach_private_network(self):
        response=SimpleNamespace(status=302,getheader=lambda key,*args:'https://private.example/')
        connection=SimpleNamespace(request=lambda *args,**kwargs:None,getresponse=lambda:response,close=lambda:None)
        def addresses(host,*args,**kwargs):
            return [(None,None,None,None,('127.0.0.1' if host=='private.example' else '93.184.216.34',443))]
        with patch.object(paper_tools.socket,'getaddrinfo',side_effect=addresses),patch.object(paper_tools,'PinnedHTTPSConnection',return_value=connection) as connect:
            with self.assertRaises(ValueError):paper_tools.fetch_public('https://public.example/')
            self.assertEqual(connect.call_count,1)

    def test_transport_failure_tries_only_the_other_validated_addresses(self):
        requested=[]
        def connection(host,address):
            requested.append(address)
            if len(requested)==1:
                def fail(*args,**kwargs):raise OSError('Synthetic connection failure')
                return SimpleNamespace(request=fail,close=lambda:None)
            body=io.BytesIO(b'public fixture')
            headers={'Content-Length':'14','Content-Type':'text/plain','Content-Encoding':'identity'}
            response=SimpleNamespace(status=200,getheader=lambda name,default=None:headers.get(name,default),read=body.read)
            return SimpleNamespace(request=lambda *args,**kwargs:None,getresponse=lambda:response,close=lambda:None,sock=None)
        with patch.object(paper_tools,'public_addresses',return_value=['93.184.216.34','1.1.1.1']),patch.object(paper_tools,'PinnedHTTPSConnection',side_effect=connection):
            body,_,_=paper_tools.fetch_public('https://public.example/paper')
        self.assertEqual(body,b'public fixture')
        self.assertEqual(requested,['93.184.216.34','1.1.1.1'])

    def test_arxiv_atom_preserves_source_abstract_and_normalizes_https(self):
        raw=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/0000.00000v1</id><title>Synthetic paper</title><published>2026-01-01</published><summary>A verifiable abstract.</summary><author><name>Example Author</name></author></entry></feed>'''
        record=paper_tools.arxiv_atom_records(raw)[0]
        self.assertEqual(record['url'],'https://arxiv.org/abs/0000.00000v1')
        self.assertEqual(record['pdf_url'],'https://arxiv.org/pdf/0000.00000v1')
        self.assertEqual(record['abstract'],'A verifiable abstract.')
        self.assertEqual(record['authors'],['Example Author'])

    def test_arxiv_abs_pdf_and_html_urls_use_the_official_id_lookup(self):
        raw=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/0000.00000v1</id><title>Synthetic paper</title><published>2026-01-01</published><summary>Verifiable abstract.</summary><author><name>Example Author</name></author></entry></feed>'''
        for url in ['https://arxiv.org/abs/0000.00000v1','https://arxiv.org/pdf/0000.00000v1.pdf','https://arxiv.org/html/0000.00000v1']:
            with patch.object(paper_tools,'fetch_public',return_value=(raw,'application/atom+xml','')) as fetch:
                self.assertEqual(paper_tools.lookup_papers(url)[0]['title'],'Synthetic paper')
                self.assertIn('https://export.arxiv.org/api/query?id_list=0000.00000v1',fetch.call_args.args[0])
                self.assertEqual(fetch.call_count,1)

    def test_codex_runs_ephemerally_in_empty_directory(self):
        observed={}
        class Process:
            returncode=0
            def __enter__(process):return process
            def __exit__(process,*args):pass
            def communicate(process,prompt,timeout):
                self.assertEqual(prompt,'Synthetic text')
                Path(observed['args'][observed['args'].index('--output-last-message')+1]).write_text('Synthetic suggestion')
                return '', ''
        def launch(args,**kwargs):
            observed.update(args=args,cwd=kwargs['cwd'])
            self.assertEqual(list(Path(kwargs['cwd']).iterdir()),[])
            self.assertEqual(kwargs['start_new_session'],os.name=='posix')
            return Process()
        with patch.object(app,'codex_command',return_value=['synthetic-codex']),patch.object(app.subprocess,'Popen',side_effect=launch):
            self.assertEqual(app.invoke_codex('Synthetic text',reasoning_effort='xhigh',model='gpt-6.1-sol'),'Synthetic suggestion')
        self.assertIn('--ephemeral',observed['args'])
        self.assertIn('model_reasoning_effort=xhigh',observed['args'])
        self.assertEqual(observed['args'][observed['args'].index('--model')+1],'gpt-6.1-sol')
        self.assertEqual(observed['args'][observed['args'].index('--sandbox')+1],'read-only')
        self.assertFalse(Path(observed['cwd']).exists())


    @unittest.skipUnless(os.name=='posix','Process-group cleanup is a POSIX boundary')
    def test_codex_timeout_stops_launcher_and_child_and_releases_slot(self):
        with tempfile.TemporaryDirectory(prefix='workmoire-process-test-') as temporary:
            root=Path(temporary);pids=root/'pids.json';launcher=root/'launcher.py'
            launcher.write_text(
                "import json,os,subprocess,sys,time\n"
                "from pathlib import Path\n"
                "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
                + "Path("+repr(str(pids))+").write_text(json.dumps([os.getpid(),child.pid]))\n"
                + "time.sleep(60)\n"
            )
            try:
                with patch.object(app,'codex_command',return_value=[sys.executable,str(launcher)]):
                    with self.assertRaisesRegex(RuntimeError,'整理超时'):
                        app.invoke_codex('Synthetic timeout fixture',timeout=2)
                self.assertTrue(pids.exists())
                for pid in json.loads(pids.read_text()):
                    status=Path('/proc')/str(pid)/'stat'
                    self.assertTrue(not status.exists() or status.read_text().split()[2]=='Z','Timed-out assistant process remains running')
                self.assertTrue(app.ASSISTANT_SLOT.acquire(blocking=False))
                app.ASSISTANT_SLOT.release()
            finally:
                if pids.exists():
                    for pid in json.loads(pids.read_text()):
                        try:os.kill(pid,signal.SIGKILL)
                        except ProcessLookupError:pass


if __name__=='__main__':unittest.main()
