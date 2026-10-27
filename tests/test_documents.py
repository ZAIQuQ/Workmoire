"""Media previews and explicit, source-grounded paper drafting boundaries."""
import io
import json
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
        with patch.object(app,'lookup_papers') as lookup, patch.object(app,'invoke_codex') as invoke, patch.object(app,'fetch_public') as fetch:
            for path in ['/api/papers/lookup','/api/papers/draft','/api/papers/pdf']:
                self.assertEqual(self.request(path,'POST',{'reference':'Synthetic title'},anonymous=True)[0],401)
            lookup.assert_not_called()
            invoke.assert_not_called()
            fetch.assert_not_called()

    def test_paper_draft_is_source_grounded_and_not_persisted(self):
        paper={'title':'Synthetic paper','authors':['Example Author'],'year':'2026','venue':'Example Journal','url':'https://example.org/paper','doi':'10.0000/example','pdf_url':'https://example.org/paper.pdf','abstract':'A synthetic abstract.','reference':'doi:10.0000/example','provider':'Synthetic'}
        with patch.object(app,'lookup_papers',return_value=[paper]),patch.object(app,'invoke_codex',return_value='## 研究问题\n\n待全文核实。') as invoke:
            status,body,_=self.request('/api/papers/draft','POST',{'reference':paper['reference']})
            self.assertEqual(status,200)
            draft=json.loads(body)
            self.assertIn('https://example.org/paper',draft['content'])
            self.assertIn('尚未阅读全文',draft['content'])
            self.assertIn('待全文核实',invoke.call_args.args[0])
        with app.open_db() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)
            for table in ['items','files','item_revisions']:
                self.assertEqual(con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)

    def test_pdf_import_validates_bytes_before_saving(self):
        with patch.object(app,'fetch_public',return_value=(b'<html>not PDF</html>','application/pdf','https://example.org/a.pdf')):
            status,_,_=self.request('/api/papers/pdf','POST',{'url':'https://example.org/a.pdf'})
            self.assertEqual(status,400)
        with app.open_db() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM files').fetchone()[0],0)
        with patch.object(app,'fetch_public',return_value=(b'%PDF-1.4\nfixture','application/pdf','https://example.org/a.pdf')):
            status,body,_=self.request('/api/papers/pdf','POST',{'url':'https://example.org/a.pdf','name':'test.pdf'})
            self.assertEqual(status,201)
            file_id=json.loads(body)['id']
        self.assertEqual(self.request('/files/'+file_id+'?inline=1')[0],200)


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

    def test_arxiv_atom_preserves_source_abstract_and_normalizes_https(self):
        raw=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/0000.00000v1</id><title>Synthetic paper</title><published>2026-01-01</published><summary>A verifiable abstract.</summary><author><name>Example Author</name></author></entry></feed>'''
        record=paper_tools.arxiv_atom_records(raw)[0]
        self.assertEqual(record['url'],'https://arxiv.org/abs/0000.00000v1')
        self.assertEqual(record['pdf_url'],'https://arxiv.org/pdf/0000.00000v1')
        self.assertEqual(record['abstract'],'A verifiable abstract.')
        self.assertEqual(record['authors'],['Example Author'])

    def test_codex_runs_ephemerally_in_empty_directory(self):
        observed={}
        def run(args,**kwargs):
            observed.update(args=args,cwd=kwargs['cwd'])
            self.assertEqual(list(Path(kwargs['cwd']).iterdir()),[])
            Path(args[args.index('--output-last-message')+1]).write_text('Synthetic suggestion')
            return SimpleNamespace(returncode=0)
        with patch.object(app,'codex_command',return_value=['synthetic-codex']),patch.object(app.subprocess,'run',side_effect=run):
            self.assertEqual(app.invoke_codex('Synthetic text'),'Synthetic suggestion')
        self.assertIn('--ephemeral',observed['args'])
        self.assertEqual(observed['args'][observed['args'].index('--sandbox')+1],'read-only')
        self.assertFalse(Path(observed['cwd']).exists())


if __name__=='__main__':unittest.main()
