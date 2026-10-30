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
from rich_documents import normalized_rich_content, safe_url, remap_references, pdf_fragment


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

    def test_pdf_page_citations_survive_save_history_and_reference_remapping(self):
        source=self.fixture_file('citation.pdf',b'%PDF-1.4 synthetic quotation source','application/pdf')
        href=source+'?inline=1#page=3';content='> A source quotation\n\n[Source p. 3]('+href+')'
        rich={'version':1,'document':{'type':'doc','content':[{'type':'blockquote','content':[{'type':'paragraph','content':[{'type':'text','text':'A source quotation'}]}]},{'type':'paragraph','content':[{'type':'text','text':'Source p. 3','marks':[{'type':'link','attrs':{'href':href}}]}]}]}}
        item=self.create(content=content,rich=rich);stored=item['rich_content']['document']['content'][1]['content'][0]['marks'][0]['attrs']['href'];self.assertEqual(stored,href)
        changed={**item,'content':content+'\n\nMy interpretation','base_updated_at':item['updated_at']}
        self.assertEqual(self.request('/api/items/'+str(item['id']),'PUT',changed)[0],200)
        revision=json.loads(self.request('/api/items/'+str(item['id'])+'/revisions')[1])['revisions'][0]
        restored=json.loads(self.request('/api/items/'+str(item['id'])+'/revisions/'+str(revision['id'])+'/restore','POST',{})[1])['item']
        self.assertEqual(restored['rich_content']['document'],item['rich_content']['document'])
        exported=json.loads(self.request('/api/export')[1]);self.assertEqual(exported['items'][0]['content'],content)
        remapped,remapped_rich=remap_references(content,normalized_rich_content(rich,content),{}, {source.rsplit('/',1)[1]:'d'*32})
        self.assertIn('/files/'+'d'*32+'?inline=1#page=3',remapped);self.assertIn('/files/'+'d'*32+'?inline=1#page=3',remapped_rich)
        for invalid in ['#page=0','#page=-1','#page=10001','#page=1&url=https://example.org','#other=3']:
            with self.assertRaises(ValueError):safe_url(source+'?inline=1'+invalid)
        with self.assertRaises(ValueError):safe_url(href,media=True)

    def test_precise_pdf_anchors_validate_bounds_and_survive_native_archives(self):
        fragment='page=3&rect=100,200,3000,400;100,700,2000,400&fp='+'a'*32
        source=self.fixture_file('anchored.pdf',b'%PDF-1.4 source anchor','application/pdf')
        href=source+'?inline=1#'+fragment
        self.assertEqual(pdf_fragment(fragment),fragment);self.assertEqual(safe_url(href),href)
        rich={'version':1,'document':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Precise source','marks':[{'type':'link','attrs':{'href':href}}]}]}]}}
        item=self.create(content='[Source]('+href+')',rich=rich)
        with zipfile.ZipFile(io.BytesIO(self.request('/api/export-archive')[1])) as archive:
            manifest=json.loads(archive.read('manifest.json'));self.assertIn(fragment,manifest['items'][0]['content']);self.assertIn(fragment,json.dumps(manifest['items'][0]['rich_content']))
        _,mapped=remap_references(item['content'],normalized_rich_content(rich),{}, {source.rsplit('/',1)[1]:'b'*32})
        self.assertIn('/files/'+'b'*32+'?inline=1#'+fragment,mapped)
        for rect in ['1,2,0,4','9990,1,20,1','1,9999,1,2','1,,2,3','1,2,3','1,2,3,4,5','1,2,3,4;'*33,'-1,2,3,4','0,0,10001,1']:
            invalid='page=1&rect='+rect+'&fp='+'a'*32
            self.assertIsNone(pdf_fragment(invalid))
            with self.assertRaises(ValueError):safe_url(source+'#'+invalid)
        for fragment in ['page=3&rect=1,2,3,4','page=3&fp='+'a'*32,'page=3&rect=1,2,3,4&fp=wrong']:
            self.assertIsNone(pdf_fragment(fragment))

    def test_autosave_coalesces_checkpoints_but_preserves_manual_and_concurrent_versions(self):
        item=self.create(content='Original',rich=native('Original'));original=item.copy()
        def update(text,automatic=True):
            nonlocal item
            status,body,_=self.request('/api/items/'+str(item['id']),'PUT',{**item,'content':text,'rich_content':native(text),'base_updated_at':item['updated_at'],'autosave':automatic})
            self.assertEqual(status,200,body);item=json.loads(body)['item']
        def revisions():return json.loads(self.request('/api/items/'+str(item['id'])+'/revisions')[1])['revisions']
        update('Auto one');update('Auto two');self.assertEqual(len(revisions()),1)
        update('Manual checkpoint',False);self.assertEqual(len(revisions()),2)
        update('New autosave cluster');self.assertEqual(len(revisions()),3)
        with patch.object(app,'AUTOSAVE_HISTORY_SECONDS',0):update('Later checkpoint')
        self.assertEqual(len(revisions()),4)
        status,_,_=self.request('/api/items/'+str(item['id']),'PUT',{**original,'base_updated_at':original['updated_at'],'autosave':True})
        self.assertEqual(status,409);self.assertEqual(len(revisions()),4)
        for flag in [None,0,1,'true',{}]:self.assertEqual(self.request('/api/items/'+str(item['id']),'PUT',{**item,'base_updated_at':item['updated_at'],'autosave':flag})[0],400)
        self.assertEqual(self.request('/api/items/'+str(item['id']),'PUT',{**item,'base_updated_at':'','autosave':True})[0],400)
        self.assertEqual(json.loads(self.request('/api/items/'+str(item['id']))[1])['item']['content'],'Later checkpoint')

    def test_new_document_creation_retries_are_idempotent_and_do_not_overwrite_newer_versions(self):
        payload={'kind':'note','title':'Synthetic automatic note','content':'First text','rich_content':native('First text'),'creation_key':'c'*32,'autosave':True}
        status,body,_=self.request('/api/items','POST',payload);self.assertEqual(status,201,body);item=json.loads(body)['item']
        status,body,_=self.request('/api/items','POST',{**payload,'content':'Unacknowledged newer text','rich_content':native('Unacknowledged newer text')})
        self.assertEqual(status,200,body);retry=json.loads(body);self.assertTrue(retry['replayed']);self.assertEqual(retry['item']['id'],item['id']);self.assertEqual(retry['item']['content'],'First text')
        changed={**item,'content':'Other tab text','rich_content':native('Other tab text'),'base_updated_at':item['updated_at']}
        self.assertEqual(self.request('/api/items/'+str(item['id']),'PUT',changed)[0],200)
        status,body,_=self.request('/api/items','POST',payload);self.assertEqual(status,409);self.assertEqual(json.loads(body)['creation_revision'],item['updated_at'])
        self.assertEqual(json.loads(body)['item']['content'],'Other tab text')
        with app.open_db() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM items').fetchone()[0],1)
            key_hash=con.execute('SELECT key_hash FROM document_creations').fetchone()[0];self.assertNotEqual(key_hash,payload['creation_key'])
        self.assertNotIn('document_creations',self.request('/api/export')[1].decode())
        self.assertEqual(self.request('/api/items','POST',payload,anonymous=True)[0],401)
        self.assertEqual(self.request('/api/items/'+str(item['id']),'DELETE')[0],200)
        self.assertEqual(self.request('/api/items','POST',payload)[0],410)

    def test_creation_keys_validate_before_writes_and_migration_is_additive(self):
        original=self.create()
        with app.open_db() as con:
            con.execute('DROP TABLE document_creations');before=[tuple(row) for row in con.execute('SELECT * FROM items')]
            app.init_document_creations(con);app.init_document_creations(con)
            self.assertEqual([tuple(row) for row in con.execute('SELECT * FROM items')],before)
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        for value in ['',True,1,[],{},'invalid','a'*31,'A'*32]:
            self.assertEqual(self.request('/api/items','POST',{'kind':'note','title':'Invalid creation key','creation_key':value})[0],400)
        self.assertEqual(self.request('/api/items','POST',{'kind':'note','title':'Missing key','autosave':True})[0],400)
        self.assertEqual(json.loads(self.request('/api/items/'+str(original['id']))[1])['item']['title'],original['title'])

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

    def test_paragraph_indent_survives_history_and_exports_with_bounded_validation(self):
        rich=native();rich['document']['content'][0]['attrs']['blockIndent']=2
        rich['document']['content'][1]['attrs']={'blockIndent':1}
        first=self.create(rich=rich)
        changed=copy.deepcopy(first);changed['rich_content']['document']['content'][0]['attrs']['blockIndent']=3;changed['base_updated_at']=first['updated_at']
        self.assertEqual(self.request('/api/items/'+str(first['id']),'PUT',changed)[0],200)
        revision=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions')[1])['revisions'][0]
        restored=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions/'+str(revision['id'])+'/restore','POST',{})[1])['item']
        self.assertEqual(restored['rich_content']['document']['content'][0]['attrs']['blockIndent'],2)
        exported=json.loads(self.request('/api/export')[1]);self.assertEqual(self.request('/api/import','POST',exported)[0],201)
        with app.open_db() as con:
            rows=con.execute('SELECT rich_content FROM items').fetchall()
            self.assertEqual(len(rows),2)
            for row in rows:self.assertEqual(json.loads(row[0])['document']['content'][1]['attrs']['blockIndent'],1)
        with zipfile.ZipFile(io.BytesIO(self.request('/api/export-archive')[1])) as archive:
            manifest=json.loads(archive.read('manifest.json'));self.assertEqual(manifest['items'][0]['rich_content']['document']['content'][0]['attrs']['blockIndent'],2)
        for value in [-1,9,True,1.5,'2',None]:
            invalid=native();invalid['document']['content'][1]['attrs']={'blockIndent':value}
            self.assertEqual(self.request('/api/items','POST',{'kind':'note','title':'Invalid indent','rich_content':invalid})[0],400)

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
        fragment='#page=1&rect=100,200,3000,500&fp='+'b'*32
        document = {'version':1,'document':{'type':'doc','content':[{'type':'pdf','attrs':{'src':path+'?inline=1','title':'Synthetic PDF'}}, {'type':'codeBlock','attrs':{'language':'python','collapsed':True},'content':[{'type':'text','text':'print(123)'}]}]}}
        document['document']['content'].append({'type':'paragraph','content':[{'type':'text','text':'Source','marks':[{'type':'link','attrs':{'href':path+'?inline=1'+fragment,'target':'_blank','rel':'noopener noreferrer nofollow'}}]}]})
        first = self.create(content='@[pdf]('+path+'?inline=1)\n\n[Source]('+path+'?inline=1'+fragment+')',rich=document)
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
        self.assertEqual(restored['content'],'@[pdf]('+expected+')\n\n[Source]('+expected+fragment+')')
        self.assertEqual(restored['rich_content']['document']['content'][1], document['document']['content'][1])
        self.assertEqual(restored['rich_content']['document']['content'][2]['content'][0]['marks'][0]['attrs']['href'],expected+fragment)

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
