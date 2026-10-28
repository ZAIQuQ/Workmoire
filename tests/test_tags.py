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
        status, body, _ = self.request('/api/tags?'+urlencode({'title':'Evaluation plan', 'context':'Attention'}))
        self.assertEqual(status, 200)
        data=json.loads(body)
        self.assertEqual(data['tags'][0]['tag'], 'Evaluation')
        self.assertEqual(data['tags'][0]['title_match'], 1)
        self.assertEqual(data['tags'][0]['related'], 1)
        self.assertEqual(data['untagged'], 1)
        self.assertEqual(json.loads(self.request('/api/tags?kind=paper')[1])['tags'], [])
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
