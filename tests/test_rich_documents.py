"""Rich-document persistence, migrations, portable references, and paper evidence."""
from paper_fixtures import analysis_fixture
import copy
import gzip
import os
import io
import json
import unittest
import urllib.request
import zipfile
from unittest.mock import patch

import test_documents as support
import workspace_server as app
import paper_tools
from rich_documents import normalized_rich_content


def native(text='Native text'):
    return {'version': 1, 'document': {'type': 'doc', 'content': [
        {'type': 'heading', 'attrs': {'level': 2}, 'content': [{'type': 'text', 'text': 'Section'}]},
        {'type': 'paragraph', 'content': [{'type': 'text', 'text': text, 'marks': [{'type': 'bold'}, {'type': 'underline'}]}, {'type': 'inlineMath', 'attrs': {'latex': 'x^2'}}]},
        {'type': 'table', 'content': [{'type': 'tableRow', 'content': [{'type': 'tableCell', 'attrs': {'colspan': 1, 'rowspan': 1, 'colwidth': [180]}, 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Cell'}]}]}]}]},
    ]}}


class RichDocumentTests(unittest.TestCase):
    setUp = support.DocumentHttpTests.setUp
    tearDown = support.DocumentHttpTests.tearDown
    request = support.DocumentHttpTests.request
    fixture_file = support.DocumentHttpTests.fixture_file

    def create(self, title='Synthetic rich note', content='## Section\n\n**Native text** $x^2$', rich=None):
        status, body, _ = self.request('/api/items', 'POST', {'kind': 'note', 'title': title, 'content': content, 'rich_content': native() if rich is None else rich})
        self.assertEqual(status, 201, body)
        return json.loads(body)['item']

    def test_native_styles_tables_and_history_survive_save_and_restore(self):
        first = self.create()
        self.assertEqual(first['rich_content']['document']['content'][1]['content'][0]['marks'], [{'type': 'bold'}, {'type': 'underline'}])
        self.assertEqual(first['rich_content']['document']['content'][2]['content'][0]['content'][0]['attrs']['colwidth'], [180])
        status, body, _ = self.request('/api/items/'+str(first['id']), 'PUT', {**first, 'content': 'Second text', 'rich_content': native('Second text'), 'base_updated_at': first['updated_at']})
        self.assertEqual(status, 200, body)
        status, body, _ = self.request('/api/items/'+str(first['id'])+'/revisions')
        revision = json.loads(body)['revisions'][0]
        status, body, _ = self.request('/api/items/'+str(first['id'])+'/revisions/'+str(revision['id'])+'/restore', 'POST', {})
        self.assertEqual(status, 200, body)
        restored = json.loads(body)['item']
        self.assertEqual(restored['rich_content'], first['rich_content'])
        self.assertEqual(restored['content'], first['content'])
        listed = json.loads(self.request('/api/items')[1])['items'][0]
        self.assertNotIn('rich_content', listed)
        self.assertNotIn('content', listed)

    def test_whole_document_font_survives_history_and_json_import(self):
        rich=native();rich['document']['attrs']={'bodyFont':'serif'}
        first=self.create(rich=rich)
        changed=copy.deepcopy(first);changed['rich_content']['document']['attrs']['bodyFont']='mono';changed['base_updated_at']=first['updated_at']
        status,body,_=self.request('/api/items/'+str(first['id']),'PUT',changed)
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['item']['rich_content']['document']['attrs']['bodyFont'],'mono')
        revision=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions')[1])['revisions'][0]
        restored=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions/'+str(revision['id'])+'/restore','POST',{})[1])['item']
        self.assertEqual(restored['rich_content']['document']['attrs']['bodyFont'],'serif')
        exported=json.loads(self.request('/api/export')[1])
        self.assertEqual(exported['items'][0]['rich_content']['document']['attrs']['bodyFont'],'serif')
        status,body,_=self.request('/api/import','POST',exported);self.assertEqual(status,201)
        with app.open_db() as db:
            rows=db.execute('SELECT rich_content FROM items ORDER BY id').fetchall()
        self.assertEqual(len(rows),2)
        self.assertTrue(all(json.loads(row[0])['document']['attrs']['bodyFont']=='serif' for row in rows))
        for font in ['untrusted-font; background:url(https://example.org)',False,{},[]]:
            invalid=native();invalid['document']['attrs']={'bodyFont':font}
            with self.assertRaises(ValueError):normalized_rich_content(invalid)

    def test_table_width_mode_survives_history_and_archives_with_strict_boolean_validation(self):
        rich=native();rich['document']['content'][2]['attrs']={'fixedWidth':False}
        first=self.create(rich=rich);table=first['rich_content']['document']['content'][2]
        self.assertIs(table['attrs']['fixedWidth'],False)
        update=copy.deepcopy(first);update['rich_content']['document']['content'][2]['attrs']['fixedWidth']=True;update['base_updated_at']=first['updated_at']
        self.assertEqual(self.request('/api/items/'+str(first['id']),'PUT',update)[0],200)
        revision=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions')[1])['revisions'][0]
        restored=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions/'+str(revision['id'])+'/restore','POST',{})[1])['item']
        self.assertEqual(restored['rich_content'],first['rich_content'])
        with zipfile.ZipFile(io.BytesIO(self.request('/api/export-archive')[1])) as archive:
            manifest=json.loads(archive.read('manifest.json'))
        self.assertIs(manifest['items'][0]['rich_content']['document']['content'][2]['attrs']['fixedWidth'],False)
        self.assertEqual(self.request('/api/import','POST',json.loads(self.request('/api/export')[1]))[0],201)
        with app.open_db() as db:
            rows=db.execute('SELECT rich_content FROM items').fetchall()
        self.assertEqual(len(rows),2);self.assertTrue(all(json.loads(row[0])['document']['content'][2]['attrs']['fixedWidth'] is False for row in rows))
        for flag in ['false',0,1,None,[]]:
            invalid=native();invalid['document']['content'][2]['attrs']={'fixedWidth':flag}
            with self.assertRaises(ValueError):normalized_rich_content(invalid)

    def test_legacy_clients_preserve_formatting_on_metadata_edits_and_clear_stale_native_body(self):
        first = self.create()
        update = {k:v for k,v in first.items() if k != 'rich_content'}
        update.update(title='Renamed', base_updated_at=first['updated_at'])
        status, body, _ = self.request('/api/items/'+str(first['id']), 'PUT', update)
        self.assertEqual(status, 200, body)
        renamed = json.loads(body)['item']
        self.assertEqual(renamed['rich_content'], first['rich_content'])
        update.update(content='Legacy Markdown update', base_updated_at=renamed['updated_at'])
        changed = json.loads(self.request('/api/items/'+str(first['id']), 'PUT', update)[1])['item']
        self.assertIsNone(changed['rich_content'])
        self.assertEqual(changed['content'], 'Legacy Markdown update')

    def test_code_folding_survives_history_and_portable_import_without_losing_source(self):
        source = '\n'.join('print(%d)' % i for i in range(120))
        markdown = '```python\n' + source + '\n```'
        rich = {'version': 1, 'document': {'type': 'doc', 'content': [
            {'type': 'codeBlock', 'attrs': {'language': 'python', 'collapsed': True}, 'content': [{'type': 'text', 'text': source}]},
        ]}}
        first = self.create(title='Folded script', content=markdown, rich=rich)
        changed = copy.deepcopy(first)
        changed['rich_content']['document']['content'][0]['attrs']['collapsed'] = False
        changed['base_updated_at'] = first['updated_at']
        self.assertEqual(self.request('/api/items/'+str(first['id']), 'PUT', changed)[0], 200)
        revisions = json.loads(self.request('/api/items/'+str(first['id'])+'/revisions')[1])['revisions']
        restored = json.loads(self.request('/api/items/'+str(first['id'])+'/revisions/'+str(revisions[0]['id'])+'/restore', 'POST', {})[1])['item']
        self.assertEqual(restored['rich_content'], first['rich_content'])
        self.assertEqual(restored['content'], markdown)
        exported = json.loads(self.request('/api/export')[1])
        self.assertEqual(self.request('/api/import', 'POST', exported)[0], 201)
        rows = json.loads(self.request('/api/items')[1])['items']
        imported = json.loads(self.request('/api/items/'+str(max(row['id'] for row in rows)))[1])['item']
        self.assertEqual(imported['rich_content'], first['rich_content'])
        self.assertEqual(imported['content'], markdown)
        for invalid in ['true', 1, None, [], {}]:
            rich['document']['content'][0]['attrs']['collapsed'] = invalid
            with self.assertRaises(ValueError):
                normalized_rich_content(rich)
        del rich['document']['content'][0]['attrs']['collapsed']
        self.assertFalse(json.loads(normalized_rich_content(rich))['document']['content'][0]['attrs']['collapsed'])

    def test_stale_versions_and_old_server_writes_cannot_resurface_an_older_native_body(self):
        first = self.create()
        second = json.loads(self.request('/api/items/'+str(first['id']), 'PUT', {**first, 'content':'New body', 'rich_content':native('New body'), 'base_updated_at':first['updated_at']})[1])['item']
        status, body, _ = self.request('/api/items/'+str(first['id']), 'PUT', {**first, 'base_updated_at':first['updated_at']})
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(body)['item']['rich_content'], second['rich_content'])
        with app.open_db() as con:
            con.execute('UPDATE items SET content=? WHERE id=?', ('Changed by an older server',first['id']))
        loaded = json.loads(self.request('/api/items/'+str(first['id']))[1])['item']
        self.assertIsNone(loaded['rich_content'])
        self.assertEqual(loaded['content'], 'Changed by an older server')

    def test_json_import_preserves_native_content_and_remaps_document_references(self):
        target = self.create(title='Target')
        document = native()
        document['document']['content'].append({'type':'paragraph','content':[{'type':'documentLink','attrs':{'id':target['id'],'title':'Target'}}]})
        origin = self.create(title='Origin',content='[[%s|Target]]'%target['id'],rich=document)
        exported = json.loads(self.request('/api/export')[1])
        status, body, _ = self.request('/api/import','POST',exported)
        self.assertEqual(status,201,body)
        rows = json.loads(self.request('/api/items')[1])['items']
        new_target = max(row['id'] for row in rows if row['title']=='Target')
        new_origin = max(row['id'] for row in rows if row['title']=='Origin')
        self.assertGreater(new_origin,origin['id'])
        restored = json.loads(self.request('/api/items/'+str(new_origin))[1])['item']
        self.assertEqual(restored['rich_content']['document']['content'][-1]['content'][0]['attrs']['id'],new_target)
        self.assertEqual(restored['content'],'[[%s|Target]]'%new_target)

    def test_complete_archive_remaps_native_and_markdown_attachment_ids(self):
        path = self.fixture_file('synthetic.pdf',b'%PDF-1.4\nsynthetic archive fixture','application/pdf')
        document = {'version':1,'document':{'type':'doc','content':[{'type':'pdf','attrs':{'src':path+'?inline=1','title':'Synthetic PDF'}}, {'type':'codeBlock','attrs':{'language':'python','collapsed':True},'content':[{'type':'text','text':'print(123)'}]}]}}
        first = self.create(content='@[pdf]('+path+'?inline=1)',rich=document)
        with app.open_db() as con:con.execute('UPDATE files SET item_id=?',(first['id'],))
        archive = self.request('/api/export-archive')[1]
        with zipfile.ZipFile(io.BytesIO(archive)) as reader:
            manifest=json.loads(reader.read('manifest.json'))
            self.assertEqual(manifest['items'][0]['rich_content']['document'],document['document'])
        boundary='workmoire-synthetic-archive-boundary'
        raw=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="fixture.zip"\r\nContent-Type: application/zip\r\n\r\n').encode()+archive+('\r\n--'+boundary+'--\r\n').encode()
        request=urllib.request.Request(self.base+'/api/import-archive',data=raw,headers={'Content-Type':'multipart/form-data; boundary='+boundary},method='POST')
        with self.client.open(request,timeout=5) as response:self.assertEqual(response.status,201)
        rows=json.loads(self.request('/api/items')[1])['items'];new_id=max(row['id'] for row in rows)
        restored=json.loads(self.request('/api/items/'+str(new_id))[1])['item']
        files=json.loads(self.request('/api/files?item_id='+str(new_id))[1])['files']
        self.assertEqual(len(files),1)
        self.assertNotEqual(files[0]['id'],'a'*32)
        expected='/files/'+files[0]['id']+'?inline=1'
        self.assertEqual(restored['rich_content']['document']['content'][0]['attrs']['src'],expected)
        self.assertEqual(restored['content'],'@[pdf]('+expected+')')
        self.assertEqual(restored['rich_content']['document']['content'][1], document['document']['content'][1])

    def test_additive_migration_preserves_existing_content_and_is_repeatable(self):
        item=self.create(rich='')
        with app.open_db() as con:
            con.execute('ALTER TABLE items DROP COLUMN rich_content')
            con.execute('ALTER TABLE item_revisions DROP COLUMN rich_content')
        app.init_db();app.init_db()
        loaded=json.loads(self.request('/api/items/'+str(item['id']))[1])['item']
        self.assertEqual(loaded['content'],item['content'])
        self.assertIsNone(loaded['rich_content'])
        with app.open_db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)

    def test_native_task_counts_include_nested_tasks_but_ignore_code_examples(self):
        paragraph = lambda text: {'type':'paragraph','content':[{'type':'text','text':text}]}
        doc = {'version':1,'document':{'type':'doc','content':[
            {'type':'taskList','content':[{'type':'taskItem','attrs':{'checked':False},'content':[paragraph('Parent'),{'type':'taskList','content':[{'type':'taskItem','attrs':{'checked':True},'content':[paragraph('Nested')]}]}]}]},
            {'type':'codeBlock','content':[{'type':'text','text':'- [ ] Not a task'}]},
        ]}}
        self.create(content='- [ ] Parent\n  - [x] Nested\n\n```\n- [ ] Not a task\n```',rich=doc)
        item=json.loads(self.request('/api/items')[1])['items'][0]
        self.assertEqual((item['task_total'],item['task_done']),(2,1))

    def test_static_gzip_negotiation_head_and_stale_fallback(self):
        from pathlib import Path
        assets=Path(self.temp.name)/'assets';assets.mkdir()
        raw=b'window.synthetic = true;';target=assets/'fixture.js';target.write_bytes(raw)
        zipped=gzip.compress(raw);compressed=assets/'fixture.js.gz';compressed.write_bytes(zipped)
        os.utime(target,(10,10));os.utime(compressed,(20,20))
        with patch.object(app,'STATIC_DIR',assets):
            status,body,headers=self.request('/static/fixture.js',headers={'Accept-Encoding':'gzip'})
            self.assertEqual(status,200);self.assertEqual(headers['Content-Encoding'],'gzip');self.assertEqual(gzip.decompress(body),raw)
            self.assertEqual(headers['Vary'],'Accept-Encoding')
            status,body,head=self.request('/static/fixture.js',method='HEAD',headers={'Accept-Encoding':'gzip'})
            self.assertEqual(status,200);self.assertEqual(body,b'');self.assertEqual(head['Content-Length'],str(len(zipped)))
            _,body,headers=self.request('/static/fixture.js',headers={'Accept-Encoding':'gzip;q=0, identity'})
            self.assertNotIn('Content-Encoding',headers);self.assertEqual(body,raw)
            target.write_bytes(b'window.synthetic = false;')
            _,body,headers=self.request('/static/fixture.js',headers={'Accept-Encoding':'gzip'})
            self.assertNotIn('Content-Encoding',headers);self.assertEqual(body,target.read_bytes())

    def test_invalid_native_documents_are_rejected_before_writes(self):
        invalid=[{'version':9,'document':{'type':'doc'}}, {'version':1,'document':{'type':'script'}}, {'version':1,'document':{'type':'doc','content':[{'type':'image','attrs':{'src':'javascript:alert(1)'}}]}}]
        linked=native();linked['document']['content'][1]['content'][0]['marks']=[{'type':'link','attrs':{'href':'javascript:alert(1)'}}];invalid.append(linked)
        malformed=native();malformed['document']['content'][0]['attrs']['level']=99;invalid.append(malformed)
        for rich in invalid:
            status,_,_=self.request('/api/items','POST',{'kind':'note','title':'Invalid','content':'Text','rich_content':rich})
            self.assertEqual(status,400)
        with app.open_db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM items').fetchone()[0],0)


class ReadingMaterialTests(unittest.TestCase):
    def test_public_article_text_keeps_sections_math_and_evidence_scope(self):
        raw=('<html><nav>Navigation noise</nav><article class="ltx_document"><h2>Method</h2><p>'+('Evidence from a synthetic method. '*80)+'</p><math alttext="x^2"><annotation>duplicate math</annotation></math><script>unsafe instructions</script></article><footer>Footer noise</footer></html>').encode()
        paper={'url':'https://arxiv.org/abs/2601.12345v2','abstract':'Synthetic abstract'}
        with patch.object(paper_tools,'fetch_public',return_value=(raw,'text/html','https://arxiv.org/html/2601.12345v2')):
            material=paper_tools.reading_material(paper)
        self.assertEqual(material['scope'],'full_text')
        self.assertIn('Method',material['text']);self.assertIn('$x^2$',material['text'])
        for noise in ['Navigation noise','duplicate math','unsafe instructions','Footer noise']:self.assertNotIn(noise,material['text'])
        short=paper_tools.ArticleText(limit=100);short.feed(raw.decode());self.assertTrue(short.truncated)

    def test_missing_html_falls_back_explicitly_without_fetching_arbitrary_publisher_pages(self):
        with patch.object(paper_tools,'fetch_public',side_effect=ValueError('unavailable')):
            self.assertEqual(paper_tools.reading_material({'url':'https://arxiv.org/abs/2601.12345','abstract':'Abstract'})['scope'],'abstract')
        with patch.object(paper_tools,'fetch_public') as fetch:
            self.assertEqual(paper_tools.reading_material({'url':'https://example.org/paper'})['scope'],'metadata');fetch.assert_not_called()

    def test_paper_dossiers_use_the_brief_template_and_preserve_source_limitations(self):
        paper={'title':'Synthetic paper','url':'https://example.org/paper','abstract':'Abstract'}
        material={'scope':'partial_pdf_text','url':'/files/'+'a'*32,'text':'Bounded PDF text','truncated':True}
        with patch.object(app,'invoke_codex',return_value=analysis_fixture('## 研究问题\n\nSynthetic')) as invoke:
            result=app.paper_notes(paper,material)
        self.assertEqual(invoke.call_args.kwargs['reasoning_effort'],app.PAPER_REASONING_EFFORT)
        self.assertEqual(app.PAPER_REASONING_EFFORT,'medium')
        self.assertEqual(invoke.call_args.kwargs['model'],'gpt-6.1-sol')
        self.assertEqual(invoke.call_args.kwargs['timeout'],150)
        self.assertIn('partial_pdf_text',invoke.call_args.args[0]);self.assertIn('一句话看懂',invoke.call_args.args[0]);self.assertIn('400–700',invoke.call_args.args[0])
        self.assertEqual(result['brief'],'## 研究问题\n\nSynthetic')


if __name__=='__main__':unittest.main()
