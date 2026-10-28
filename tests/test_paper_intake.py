"""Two creation kinds and selected-PDF precedence with recoverable attachments."""
import json
import unittest
from unittest.mock import patch

import paper_intake
import test_documents as support
import workspace_server as app


class PaperSourceTests(unittest.TestCase):
    def test_direct_pdf_and_landing_page_resolve_without_persisting(self):
        with patch.object(paper_intake,'fetch_public',return_value=(b'%PDF-1.7 synthetic','application/pdf','https://example.org/final.pdf')) as fetch:
            result=paper_intake.download_paper('https://example.org/source.pdf',1000)
            self.assertEqual(result['raw'],b'%PDF-1.7 synthetic')
            self.assertEqual(result['status'],'ready')
            fetch.assert_called_once_with('https://example.org/source.pdf',1000)
        paper={'title':'Verified paper','authors':['Author'],'url':'https://example.org/article','pdf_url':'https://example.org/file.pdf'}
        with patch.object(paper_intake,'lookup_papers',return_value=[paper]),patch.object(paper_intake,'fetch_public',return_value=(b'%PDF-1.7 synthetic','application/pdf',paper['pdf_url'])):
            result=paper_intake.download_paper(paper['url'],1000)
            self.assertEqual(result['name'],'Verified paper.pdf')
            self.assertEqual(result['source_url'],paper['url'])

    def test_arxiv_pdf_download_does_not_depend_on_metadata_api_availability(self):
        with patch.object(paper_intake,'lookup_papers',side_effect=ValueError('Metadata unavailable')),patch.object(paper_intake,'fetch_public',return_value=(b'%PDF-1.7 synthetic','application/pdf','https://arxiv.org/pdf/1706.03762v2')) as fetch:
            result=paper_intake.download_paper('https://arxiv.org/abs/1706.03762v2',1000)
            self.assertEqual(result['status'],'ready')
            fetch.assert_called_once_with('https://arxiv.org/pdf/1706.03762v2',1000)

    def test_blocked_or_non_pdf_sources_require_manual_upload(self):
        for failure in [ValueError('论文来源暂不可用（HTTP 403）'),ValueError('Connection timed out')]:
            with patch.object(paper_intake,'fetch_public',side_effect=failure):
                result=paper_intake.download_paper('https://example.org/source.pdf',1000)
                self.assertEqual(result['status'],'needs_pdf');self.assertIn('上传',result['message']);self.assertNotIn('raw',result)
        with patch.object(paper_intake,'fetch_public',return_value=(b'<html>Login</html>','text/html','https://example.org/source.pdf')):
            self.assertEqual(paper_intake.download_paper('https://example.org/source.pdf',1000)['status'],'needs_pdf')
        with patch.object(paper_intake,'fetch_public',side_effect=ValueError('论文来源必须是公开网络地址')):
            with self.assertRaises(ValueError):paper_intake.download_paper('https://example.org/source.pdf',1000)


class PaperIntakeHttpTests(unittest.TestCase):
    setUp=support.DocumentHttpTests.setUp
    tearDown=support.DocumentHttpTests.tearDown
    request=support.DocumentHttpTests.request
    fixture_file=support.DocumentHttpTests.fixture_file

    def test_uploaded_pdf_has_priority_over_url_for_import_and_analysis(self):
        self.fixture_file('chosen.pdf',b'%PDF-1.4 chosen bytes','application/pdf')
        payload={'reference':'https://example.org/other-paper','file_id':'a'*32}
        with patch.object(app,'download_paper') as download,patch.object(app,'lookup_papers') as lookup,patch.object(app,'reading_material') as html:
            self.assertEqual(self.request('/api/papers/prepare','POST',payload,anonymous=True)[0],401)
            status,body,_=self.request('/api/papers/prepare','POST',payload)
            self.assertEqual(status,200);prepared=json.loads(body);self.assertEqual(prepared['pdf_origin'],'uploaded');self.assertEqual(prepared['file']['id'],'a'*32)
            evidence='UPLOADED_PDF_SELECTED: this is the only text used in the paper analysis. '*5
            with patch.object(app,'invoke_codex',return_value='## 核心问题\n\n从指定 PDF 提取。') as invoke:
                status,body,_=self.request('/api/papers/draft','POST',{**payload,'title':'Chosen paper','author':'PDF Author','text':evidence,'pages_read':1,'page_count':1,'truncated':False})
                self.assertEqual(status,200);draft=json.loads(body);self.assertEqual(draft['evidence']['file_id'],'a'*32);self.assertIn(evidence,invoke.call_args.args[0]);self.assertEqual(invoke.call_args.kwargs['reasoning_effort'],app.PAPER_REASONING_EFFORT)
                self.assertIn('/files/'+'a'*32,draft['content']);self.assertLess(draft['content'].index('## 核心问题'),draft['content'].index('## 原文 PDF'));self.assertIn('## 核心问题',draft['analysis']);self.assertNotIn('other-paper.pdf',draft['content'])
            download.assert_not_called();lookup.assert_not_called();html.assert_not_called()
        with app.open_db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM items').fetchone()[0],0)

    def test_url_import_creates_only_an_unassociated_pdf_and_failed_download_creates_nothing(self):
        ready={'status':'ready','paper':{'title':'Source paper'},'source_url':'https://example.org/paper','download_url':'https://example.org/paper.pdf','name':'paper.pdf','raw':b'%PDF-1.4 downloaded'}
        with patch.object(app,'download_paper',return_value=ready):
            status,body,_=self.request('/api/papers/prepare','POST',{'reference':'https://example.org/paper'})
        self.assertEqual(status,200);file=json.loads(body)['file']
        with app.open_db() as con:
            row=con.execute('SELECT * FROM files WHERE id=?',(file['id'],)).fetchone();self.assertIsNone(row['item_id']);self.assertEqual((app.FILES_DIR/row['stored_name']).read_bytes(),b'%PDF-1.4 downloaded');self.assertEqual(con.execute('SELECT COUNT(*) FROM items').fetchone()[0],0)
        with patch.object(app,'download_paper',return_value={'status':'needs_pdf','source_url':'https://example.org/blocked','message':'请上传'}):
            status,body,_=self.request('/api/papers/prepare','POST',{'reference':'https://example.org/blocked'})
        self.assertEqual(json.loads(body)['status'],'needs_pdf')
        with app.open_db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM files').fetchone()[0],1)

    def test_no_text_can_be_archived_but_never_analyzed_as_if_it_were_a_readable_pdf(self):
        self.fixture_file('scan.pdf',b'%PDF-1.4 synthetic scan','application/pdf')
        payload={'file_id':'a'*32,'title':'Scan','text':'\n[第 1 页]\n','page_count':1,'pages_read':1,'truncated':False}
        with patch.object(app,'invoke_codex') as invoke:
            self.assertEqual(self.request('/api/papers/draft','POST',payload)[0],400)
            status,body,_=self.request('/api/papers/draft','POST',{**payload,'generate':False})
            self.assertEqual(status,200);self.assertIn('尚未取得',json.loads(body)['content']);invoke.assert_not_called()
        (app.FILES_DIR/('a'*32+'.pdf')).write_bytes(b'<html>not PDF</html>')
        self.assertEqual(self.request('/api/papers/prepare','POST',{'file_id':'a'*32})[0],400)

    def test_legacy_specialized_kinds_write_as_ordinary_notes_and_blog_is_not_builtin(self):
        for kind in ['project','blog','log']:
            status,body,_=self.request('/api/items','POST',{'kind':kind,'title':'Legacy content','tags':'博客','content':'Preserved text'})
            self.assertEqual(status,201);item=json.loads(body)['item'];self.assertEqual(item['kind'],'note');self.assertEqual(item['content'],'Preserved text')
        tags=json.loads(self.request('/api/tags')[1])['tags'];blog=next(row for row in tags if row['tag']=='博客');self.assertFalse(blog['built_in'])
        self.assertEqual(self.request('/api/tags/preview','POST',{'source':'博客','target':'阅读'})[0],200)
