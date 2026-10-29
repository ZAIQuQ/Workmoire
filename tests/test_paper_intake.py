"""Two creation kinds and selected-PDF precedence with recoverable attachments."""
from paper_fixtures import analysis_fixture
import json
import unittest
from unittest.mock import patch

import paper_intake
import paper_tools
import test_documents as support
import workspace_server as app


class PaperSourceTests(unittest.TestCase):
    def test_source_links_are_attribution_without_network_access(self):
        with patch.object(paper_tools.socket, 'getaddrinfo') as dns, patch.object(paper_tools, 'fetch_public') as fetch:
            self.assertEqual(paper_intake.paper_source(' https://example.org/source.pdf '), 'https://example.org/source.pdf')
            self.assertEqual(paper_intake.paper_source(''), '')
            for invalid in ['http://example.org/paper', 'https://user:password@example.org/paper', 'javascript:alert(1)']:
                with self.assertRaises(ValueError):paper_intake.paper_source(invalid)
            dns.assert_not_called();fetch.assert_not_called()


class PaperIntakeHttpTests(unittest.TestCase):
    setUp=support.DocumentHttpTests.setUp
    tearDown=support.DocumentHttpTests.tearDown
    request=support.DocumentHttpTests.request
    fixture_file=support.DocumentHttpTests.fixture_file

    def test_uploaded_pdf_has_priority_over_url_for_import_and_analysis(self):
        self.fixture_file('chosen.pdf',b'%PDF-1.4 chosen bytes','application/pdf')
        payload={'reference':'https://example.org/other-paper','file_id':'a'*32}
        with patch.object(paper_tools,'fetch_public') as download,patch.object(paper_tools,'lookup_papers') as lookup,patch.object(paper_tools,'reading_material') as html:
            self.assertEqual(self.request('/api/papers/prepare','POST',payload,anonymous=True)[0],401)
            status,body,_=self.request('/api/papers/prepare','POST',payload)
            self.assertEqual(status,200);prepared=json.loads(body);self.assertEqual(prepared['pdf_origin'],'uploaded');self.assertEqual(prepared['file']['id'],'a'*32)
            evidence='UPLOADED_PDF_SELECTED: this is the only text used in the paper analysis. '*5
            with patch.object(app,'invoke_codex',return_value=analysis_fixture('## 核心问题\n\n从指定 PDF 提取。')) as invoke:
                status,body,_=self.request('/api/papers/draft','POST',{**payload,'title':'Chosen paper','author':'PDF Author','text':evidence,'pages_read':1,'page_count':1,'truncated':False})
                self.assertEqual(status,200);draft=json.loads(body);self.assertEqual(draft['evidence']['file_id'],'a'*32);self.assertIn(evidence,invoke.call_args.args[0]);self.assertEqual(invoke.call_args.kwargs['reasoning_effort'],app.PAPER_REASONING_EFFORT)
                self.assertIn('/files/'+'a'*32,draft['content']);self.assertLess(draft['content'].index('## 核心问题'),draft['content'].index('## 原文 PDF'));self.assertIn('## 核心问题',draft['analysis']);self.assertNotIn('other-paper.pdf',draft['content'])
            download.assert_not_called();lookup.assert_not_called();html.assert_not_called()
        with app.open_db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM items').fetchone()[0],0)

    def test_url_only_requests_cannot_download_or_generate_even_from_older_clients(self):
        with patch.object(paper_tools,'fetch_public') as fetch, patch.object(paper_tools,'lookup_papers') as lookup, patch.object(app,'invoke_codex') as invoke:
            for reference in ['https://example.org/paper.pdf', 'https://arxiv.org/abs/0000.00000', 'Synthetic paper title']:
                for path,status_code in [('/api/papers/prepare',400),('/api/papers/draft',400),('/api/papers/pdf',410),('/api/papers/lookup',410)]:
                    status,body,_=self.request(path,'POST',{'reference':reference,'url':reference,'background':True})
                    self.assertEqual(status,status_code);self.assertIn('上传 PDF',json.loads(body)['error'])
            fetch.assert_not_called();lookup.assert_not_called();invoke.assert_not_called()
        with app.open_db() as con:
            for table in ['items','files','item_revisions']:
                self.assertEqual(con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        self.assertEqual(list(app.FILES_DIR.iterdir()),[])

    def test_no_text_can_be_archived_but_never_analyzed_as_if_it_were_a_readable_pdf(self):
        self.fixture_file('scan.pdf',b'%PDF-1.4 synthetic scan','application/pdf')
        payload={'file_id':'a'*32,'title':'Scan','text':'\n[第 1 页]\n','page_count':1,'pages_read':1,'truncated':False}
        with patch.object(app,'invoke_codex') as invoke:
            self.assertEqual(self.request('/api/papers/draft','POST',payload)[0],400)
            status,body,_=self.request('/api/papers/draft','POST',{**payload,'generate':False})
            self.assertEqual(status,200);self.assertIn('## 原文 PDF',json.loads(body)['content']);self.assertNotIn('尚未取得',json.loads(body)['content']);invoke.assert_not_called()
        (app.FILES_DIR/('a'*32+'.pdf')).write_bytes(b'<html>not PDF</html>')
        self.assertEqual(self.request('/api/papers/prepare','POST',{'file_id':'a'*32})[0],400)

    def test_legacy_specialized_kinds_write_as_ordinary_notes_and_blog_is_not_builtin(self):
        for kind in ['project','blog','log']:
            status,body,_=self.request('/api/items','POST',{'kind':kind,'title':'Legacy content','tags':'博客','content':'Preserved text'})
            self.assertEqual(status,201);item=json.loads(body)['item'];self.assertEqual(item['kind'],'note');self.assertEqual(item['content'],'Preserved text')
        tags=json.loads(self.request('/api/tags')[1])['tags'];blog=next(row for row in tags if row['tag']=='博客');self.assertFalse(blog['built_in'])
        self.assertEqual(self.request('/api/tags/preview','POST',{'source':'博客','target':'阅读'})[0],200)
