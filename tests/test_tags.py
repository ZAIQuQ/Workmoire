"""Tag discovery, previewed organization and revision/conflict boundaries."""
import json
import unittest
from urllib.parse import urlencode

import test_documents as support
import workspace_server as app


class TagTests(unittest.TestCase):
    setUp = support.DocumentHttpTests.setUp
    tearDown = support.DocumentHttpTests.tearDown
    request = support.DocumentHttpTests.request

    def create(self, title, tags, **extra):
        status, body, _ = self.request('/api/items', 'POST', {'kind': 'note', 'title': title, 'tags': tags, 'content': 'Original body', **extra})
        self.assertEqual(status, 201)
        return json.loads(body)['item']

    def get(self, item):
        return json.loads(self.request('/api/items/'+str(item['id']))[1])['item']

    def test_normalization_and_contextual_suggestions_remain_read_only(self):
        self.assertEqual(app.safe_tags(' #AI，ＡＩ, 方法 ,方法,#C#'), 'AI,方法,C#')
        self.assertEqual(app.safe_tags('x'*33+','+'x'*34), 'x'*32)
        self.create('First', 'Attention,Methods')
        self.create('Second', 'Attention,Evaluation')
        self.create('Third', 'Methods')
        self.create('Fourth', '', kind='paper')
        self.create('Untagged', '')
        status, body, _ = self.request('/api/tags?'+urlencode({'title':'Evaluation plan', 'context':'Attention'}))
        self.assertEqual(status, 200)
        data=json.loads(body)
        self.assertEqual(data['tags'][0]['tag'], 'Evaluation')
        self.assertEqual(data['tags'][0]['title_match'], 1)
        self.assertEqual(data['tags'][0]['related'], 1)
        self.assertEqual(data['untagged'], 1)
        paper_tags=json.loads(self.request('/api/tags?kind=paper')[1])['tags']
        self.assertIn(('论文', 1, 1), [(row['tag'], row['count'], row['built_in']) for row in paper_tags])
        self.assertEqual(json.loads(self.request('/api/items?untagged=1')[1])['total'], 1)
        self.assertEqual(self.request('/api/tags', anonymous=True)[0], 401)
        for path in ['/api/tags/preview', '/api/tags/rename']:
            self.assertEqual(self.request(path, 'POST', {'source':'Methods','target':'Method'}, anonymous=True)[0], 401)
        with app.open_db() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM item_revisions').fetchone()[0], 0)

    def test_preview_merge_and_history_preserve_content_and_exclude_trash(self):
        native={'version':1,'document':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Original body','marks':[{'type':'bold'}]}]}]}}
        first=self.create('First', 'old,keep', rich_content=native)
        second=self.create('Second', 'old,new')
        trashed=self.create('Trashed', 'old')
        self.request('/api/items/'+str(trashed['id']), 'DELETE')
        status, body, _=self.request('/api/tags/preview', 'POST', {'source':'old','target':'new'})
        self.assertEqual(status,200)
        plan=json.loads(body)
        self.assertEqual(plan['count'],2)
        self.assertTrue(plan['merge'])
        self.assertEqual(self.get(first)['tags'],'old,keep')
        with app.open_db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM item_revisions').fetchone()[0],0)
        self.assertEqual(self.request('/api/tags/rename','POST',plan)[0],200)
        changed=self.get(first)
        self.assertEqual(changed['tags'],'new,keep')
        self.assertEqual(changed['rich_content'],first['rich_content'])
        self.assertEqual(changed['content'],first['content'])
        self.assertEqual(self.get(second)['tags'],'new')
        with app.open_db() as con:self.assertEqual(con.execute('SELECT tags FROM items WHERE id=?',(trashed['id'],)).fetchone()[0],'old')
        revisions=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions')[1])['revisions']
        restored=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions/'+str(revisions[0]['id'])+'/restore','POST',{})[1])['item']
        self.assertEqual(restored['tags'],first['tags'])
        self.assertEqual(restored['rich_content'],first['rich_content'])
        # A stale document editor cannot undo a completed tag merge by saving an old base.
        self.assertEqual(self.request('/api/items/'+str(second['id']), 'PUT', {**second, 'base_updated_at':second['updated_at']})[0],409)

    def test_stale_preview_is_atomic_and_requires_refresh(self):
        first=self.create('First','old')
        second=self.create('Second','old')
        plan=json.loads(self.request('/api/tags/preview','POST',{'source':'old','target':'renamed'})[1])
        self.request('/api/items/'+str(second['id']),'PUT',{**second,'title':'Edited elsewhere','base_updated_at':second['updated_at']})
        self.assertEqual(self.request('/api/tags/rename','POST',plan)[0],409)
        self.assertEqual(self.get(first)['tags'],'old')
        self.assertEqual(self.get(second)['tags'],'old')
        self.assertEqual(self.request('/api/tags/rename','POST',{'source':'old','target':'renamed'})[0],409)
        refreshed=json.loads(self.request('/api/tags/preview','POST',{'source':'old','target':'renamed'})[1])
        self.assertEqual(self.request('/api/tags/rename','POST',refreshed)[0],200)

    def test_invalid_or_unbounded_tag_operations_do_not_write(self):
        self.create('First','old')
        for target in ['', 'a,b', 'x'*33, 'old', ['other']]:
            self.assertEqual(self.request('/api/tags/preview','POST',{'source':'old','target':target})[0],400)
        with app.open_db() as con:
            stamp=app.utc_now()
            con.executemany("INSERT INTO items(kind,title,tags,created_at,updated_at) VALUES('note',?,'old',?,?)", [('Synthetic '+str(i),stamp,stamp) for i in range(100)])
        self.assertEqual(self.request('/api/tags/preview','POST',{'source':'old','target':'new'})[0],400)
        with app.open_db() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM item_revisions').fetchone()[0],0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM items WHERE tags='old'").fetchone()[0],101)


    def test_builtin_paper_tag_exists_when_empty_and_cannot_be_renamed(self):
        tags=json.loads(self.request('/api/tags')[1])['tags']
        self.assertEqual({(row['tag'],row['count'],row['built_in']) for row in tags},{('论文',0,1),('博客',0,1)})
        self.assertEqual(json.loads(self.request('/api/tags?q=missing')[1])['tags'],[])
        for path in ['/api/tags/preview','/api/tags/rename']:
            self.assertEqual(self.request(path,'POST',{'source':'论文','target':'Renamed'})[0],400)
        item=self.create('Paper','method',kind='paper')
        self.assertEqual(item['tags'],'论文,method')
        status,body,_=self.request('/api/items/'+str(item['id'])+'/tags','POST',{'tags':'','base_updated_at':item['updated_at']})
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['item']['tags'],'论文')
        updated=self.get(item)
        status,body,_=self.request('/api/items/'+str(item['id']),'PUT',{**updated,'tags':'','base_updated_at':updated['updated_at']})
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['item']['tags'],'论文')

    def test_legacy_papers_are_classified_on_read_without_rewriting_user_records(self):
        custom=','.join('tag'+str(i) for i in range(12))
        item=self.create('Legacy paper',custom,kind='paper')
        with app.open_db() as con:con.execute('UPDATE items SET tags=? WHERE id=?',(custom,item['id']))
        loaded=self.get(item)
        self.assertEqual(loaded['tags'],'论文,'+custom)
        self.assertEqual(len(loaded['tags_list']),13)
        self.assertEqual(json.loads(self.request('/api/items?tag=%E8%AE%BA%E6%96%87')[1])['total'],1)
        self.assertEqual(json.loads(self.request('/api/items?untagged=1')[1])['total'],0)
        with app.open_db() as con:self.assertEqual(con.execute('SELECT tags FROM items WHERE id=?',(item['id'],)).fetchone()[0],custom)
        self.assertEqual(json.loads(self.request('/api/tags?q=%E8%AE%BA%E6%96%87')[1])['tags'][0]['count'],1)
        status,body,_=self.request('/api/items/'+str(item['id'])+'/tags','POST',{'tags':loaded['tags'],'base_updated_at':item['updated_at']})
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['item']['tags_list'],loaded['tags_list'])
        with app.open_db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM item_revisions').fetchone()[0],0)

    def test_single_document_tag_save_is_revision_checked_and_never_writes_the_body(self):
        native={'version':1,'document':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Original body','marks':[{'type':'bold'}]}]}]}}
        first=self.create('Source','old',rich_content=native)
        path='/api/items/'+str(first['id'])+'/tags'
        self.assertEqual(self.request(path,'POST',{'tags':'new','base_updated_at':first['updated_at']},anonymous=True)[0],401)
        self.assertEqual(self.request(path,'POST',{'tags':'new'})[0],400)
        status,body,_=self.request(path,'POST',{'tags':'new','base_updated_at':first['updated_at'],'title':'Unexpected','content':'Must not be saved','rich_content':None})
        self.assertEqual(status,200)
        result=json.loads(body)['item']
        self.assertNotIn('content',result)
        changed=self.get(first)
        for field in ['title','content','rich_content','kind','pinned','summary']:
            self.assertEqual(changed[field],first[field])
        self.assertEqual(changed['tags'],'new')
        self.assertEqual(self.request(path,'POST',{'tags':'stale','base_updated_at':first['updated_at']})[0],409)
        revisions=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions')[1])['revisions']
        self.assertEqual(revisions[0]['tags'],'old')
        self.assertEqual(len(revisions),1)
        self.assertEqual(self.request(path,'POST',{'tags':'new','base_updated_at':changed['updated_at']})[0],200)
        self.assertEqual(len(json.loads(self.request('/api/items/'+str(first['id'])+'/revisions')[1])['revisions']),1)
        self.request('/api/items/'+str(first['id']),'DELETE')
        self.assertEqual(self.request(path,'POST',{'tags':'ignored','base_updated_at':changed['updated_at']})[0],404)

    def test_tag_deletion_is_previewed_versioned_recoverable_and_cannot_delete_builtin(self):
        native={'version':1,'document':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Original body','marks':[{'type':'bold'}]}]}]}}
        first=self.create('First','delete-me,keep',rich_content=native)
        second=self.create('Second','delete-me',kind='paper')
        trashed=self.create('Trashed','delete-me')
        self.request('/api/items/'+str(trashed['id']),'DELETE')
        payload={'source':'delete-me','action':'delete'}
        self.assertEqual(self.request('/api/tags/delete','POST',payload,anonymous=True)[0],401)
        plan=json.loads(self.request('/api/tags/preview','POST',payload)[1])
        self.assertEqual(plan['count'],2)
        self.assertEqual(plan['action'],'delete')
        self.assertEqual(self.get(first)['tags'],'delete-me,keep')
        rename=json.loads(self.request('/api/tags/preview','POST',{'source':'delete-me','target':'changed'})[1])
        self.assertEqual(self.request('/api/tags/delete','POST',rename)[0],409)
        status,body,_=self.request('/api/tags/delete','POST',plan)
        self.assertEqual(status,200)
        result=json.loads(body)
        self.assertEqual(len(result['updates']),2)
        update=result['updates'][0]
        self.assertEqual(update['before']['updated_at'],first['updated_at'])
        self.assertEqual(update['after']['tags'],'keep')
        self.assertNotIn('content',update['before'])
        changed=self.get(first)
        self.assertEqual(changed['content'],first['content'])
        self.assertEqual(changed['rich_content'],first['rich_content'])
        self.assertEqual(self.get(second)['tags'],'论文')
        self.assertEqual(json.loads(self.request('/api/tags?q=delete-me')[1])['tags'],[])
        with app.open_db() as con:self.assertEqual(con.execute('SELECT tags FROM items WHERE id=?',(trashed['id'],)).fetchone()[0],'delete-me')
        revision=json.loads(self.request('/api/items/'+str(first['id'])+'/revisions')[1])['revisions'][0]
        self.assertEqual(self.request('/api/items/'+str(first['id'])+'/revisions/'+str(revision['id'])+'/restore','POST',{})[0],200)
        self.assertEqual(self.get(first)['tags'],first['tags'])
        for path in ['/api/tags/preview','/api/tags/delete']:
            self.assertEqual(self.request(path,'POST',{'source':'论文','action':'delete'})[0],400)

    def test_tag_deletion_rejects_a_stale_preview_without_partial_changes(self):
        first=self.create('First','obsolete')
        plan=json.loads(self.request('/api/tags/preview','POST',{'source':'obsolete','action':'delete'})[1])
        self.create('Added after preview','obsolete')
        self.assertEqual(self.request('/api/tags/delete','POST',plan)[0],409)
        self.assertEqual(self.get(first)['tags'],'obsolete')
        with app.open_db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM item_revisions').fetchone()[0],0)
