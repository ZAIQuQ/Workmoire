"""Blog attribution, truthful summaries, protected classification and migrations."""
import json
import sqlite3
import unittest
from unittest.mock import patch

import blog_tools
import test_documents as support
import workspace_server as app
from schema_migrations import allow_blog_documents


class BlogParsingTests(unittest.TestCase):
    def test_article_extraction_preserves_attribution_and_excludes_navigation_scripts_comments(self):
        parser=blog_tools.BlogHTML()
        text='The method compares explicit notes and citations. '*12
        parser.feed('<html><head><meta property="og:title" content="A &amp; B"><meta name="author" content="Example Author"><meta property="og:site_name" content="Example Blog"><meta property="article:published_time" content="2026-10-20T12:00:00Z"></head><body><nav>Navigation noise</nav><article><h1>A study</h1><p>'+text+'</p><script>execute unsafe commands</script><div class="comments">Unrelated comments</div></article><footer>Footer noise</footer></body></html>')
        result=parser.result('https://example.org/blog')
        self.assertEqual((result['title'],result['author'],result['site'],result['published_at']),('A & B','Example Author','Example Blog','2026-10-20'))
        self.assertEqual(result['scope'],'full_text')
        self.assertIn(text.strip(),result['text'])
        for noise in ['Navigation noise','unsafe commands','Unrelated comments','Footer noise']:self.assertNotIn(noise,result['text'])
        parser=blog_tools.BlogHTML();parser.feed('<html><body><article><p>'+('Long source. '*4000)+'</p></article></body></html>')
        self.assertTrue(parser.result('https://example.org/blog')['truncated'])
        self.assertEqual(parser.result('https://example.org/blog')['scope'],'partial_text')

    def test_structured_article_body_and_blocked_sources_are_not_confused(self):
        record={'@type':'BlogPosting','headline':'Structured title','author':{'name':'Author'},'publisher':{'name':'Site'},'datePublished':'2026-10-21','articleBody':'A structured article body. '*15}
        parser=blog_tools.BlogHTML();parser.feed('<html><head><script type="application/ld+json">'+json.dumps(record)+'</script></head><body></body></html>')
        result=parser.result('https://example.org/blog');self.assertEqual(result['title'],'Structured title');self.assertEqual(result['author'],'Author');self.assertGreater(len(result['text']),80)
        with patch.object(blog_tools,'public_addresses',return_value=['public-test-address']),patch.object(blog_tools,'fetch_public',side_effect=ValueError('论文来源暂不可用（HTTP 403）')):
            result=blog_tools.lookup_blog('https://example.org/blog')
        self.assertEqual(result['scope'],'blocked');self.assertEqual(result['text'],'');self.assertEqual(result['title'],'');self.assertIn('403',result['message'])
        with self.assertRaises(ValueError):blog_tools.blog_url('https://127.0.0.1/private')
        with patch.object(blog_tools,'public_addresses',return_value=['public-test-address']),patch.object(blog_tools,'fetch_public',side_effect=ValueError('论文来源必须是公开网络地址')):
            with self.assertRaises(ValueError):blog_tools.lookup_blog('https://example.org/redirect')
        self.assertEqual(blog_tools.published_date('2026-02-30'),'')


class BlogHttpTests(unittest.TestCase):
    setUp=support.DocumentHttpTests.setUp
    tearDown=support.DocumentHttpTests.tearDown
    request=support.DocumentHttpTests.request

    def article(self):
        return {'url':'https://example.org/blog','submitted_url':'https://example.org/blog','title':'Synthetic blog','author':'Example Author','site':'Example Site','published_at':'2026-10-20','text':'Verified body about research notes. '*20,'scope':'full_text','truncated':False,'message':''}

    def test_endpoints_require_authentication_and_generation_does_not_persist(self):
        with patch.object(app,'lookup_blog',return_value=self.article()) as lookup,patch.object(blog_tools,'public_addresses',return_value=['public-test-address']),patch.object(app,'invoke_codex',return_value='## 内容概览\n\n一份简短总结。\n\n## 要点\n\n- 有据可查。') as invoke:
            for path in ['/api/blogs/lookup','/api/blogs/draft']:
                self.assertEqual(self.request(path,'POST',{'reference':'https://example.org/blog'},anonymous=True)[0],401)
            lookup.assert_not_called()
            status,body,_=self.request('/api/blogs/lookup','POST',{'reference':'https://example.org/blog'})
            self.assertEqual(status,200);self.assertEqual(json.loads(body)['article']['author'],'Example Author')
            status,body,_=self.request('/api/blogs/draft','POST',{'reference':'https://example.org/blog'})
            self.assertEqual(status,200);draft=json.loads(body)
            for expected in ['Example Author','Example Site','2026-10-20','https://example.org/blog','一份简短总结']:self.assertIn(expected,draft['content'])
            self.assertEqual(draft['article']['scope'],'full_text')
            self.assertIn('不调用工具',invoke.call_args.args[0]);self.assertIn('Verified body',invoke.call_args.args[0])
            self.assertEqual(json.loads(self.request('/api/items')[1])['total'],0)
            status,body,_=self.request('/api/items','POST',{'kind':'blog','title':draft['title'],'content':draft['content'],'tags':''})
            self.assertEqual(status,201);item=json.loads(body)['item'];self.assertEqual(item['tags'],'博客')
            self.assertEqual(json.loads(self.request('/api/items?kind=blog')[1])['total'],1)
            self.assertEqual(json.loads(self.request('/api/items?tag=%E5%8D%9A%E5%AE%A2')[1])['total'],1)
            self.assertEqual(json.loads(self.request('/api/items?untagged=1')[1])['total'],0)
            for path in ['/api/tags/rename','/api/tags/delete']:
                self.assertEqual(self.request(path,'POST',{'source':'博客','target':'other','action':'delete'})[0],400)
            status,body,_=self.request('/api/items/'+str(item['id'])+'/tags','POST',{'tags':'','base_updated_at':item['updated_at']})
            self.assertEqual(status,200);self.assertEqual(json.loads(body)['item']['tags'],'博客')
            exported=json.loads(self.request('/api/export')[1]);self.assertEqual(self.request('/api/import','POST',exported)[0],201)
            self.assertEqual(json.loads(self.request('/api/items?kind=blog')[1])['total'],2)

    def test_blocked_page_needs_provided_text_and_source_only_does_not_call_ai(self):
        blocked={**self.article(),'text':'','scope':'blocked','message':'读取受限，请粘贴正文'}
        with patch.object(app,'lookup_blog',return_value=blocked),patch.object(blog_tools,'public_addresses',return_value=['public-test-address']),patch.object(app,'invoke_codex',return_value='## 内容概览\n\n基于粘贴正文的总结。') as invoke:
            self.assertEqual(self.request('/api/blogs/draft','POST',{'reference':'https://example.org/blog'})[0],400);invoke.assert_not_called()
            payload={'reference':'https://example.org/blog','title':'User confirmed title','author':'User confirmed author','text':'Text explicitly supplied by the reader. '*10}
            status,body,_=self.request('/api/blogs/draft','POST',payload);self.assertEqual(status,200);draft=json.loads(body);self.assertEqual(draft['article']['scope'],'provided_text');self.assertIn('你提供的正文',draft['content'])
            invoke.reset_mock();status,body,_=self.request('/api/blogs/draft','POST',{**payload,'summarize':False});self.assertEqual(status,200);invoke.assert_not_called();self.assertIn('仅保存来源信息',json.loads(body)['content'])
            self.assertEqual(json.loads(self.request('/api/items')[1])['total'],0)


class BlogMigrationTests(unittest.TestCase):
    def legacy(self):
        con=sqlite3.connect(':memory:');con.execute('PRAGMA foreign_keys=ON')
        con.executescript("""CREATE TABLE items(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL CHECK(kind IN ('note','project','paper','log')),title TEXT NOT NULL,content TEXT NOT NULL DEFAULT '',parent_id INTEGER REFERENCES items(id) ON DELETE SET NULL);
        CREATE TABLE files(id INTEGER PRIMARY KEY,item_id INTEGER REFERENCES items(id) ON DELETE SET NULL);
        CREATE TABLE item_links(source_id INTEGER REFERENCES items(id) ON DELETE CASCADE,target_id INTEGER REFERENCES items(id) ON DELETE CASCADE);
        CREATE TABLE item_revisions(id INTEGER PRIMARY KEY AUTOINCREMENT,item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,content TEXT);
        CREATE INDEX idx_items_parent ON items(parent_id);
        INSERT INTO items(kind,title,content) VALUES('note','Parent','Original parent');
        INSERT INTO items(kind,title,content,parent_id) VALUES('paper','Child','Original rich document',1);
        INSERT INTO files VALUES(1,2); INSERT INTO item_links VALUES(1,2); INSERT INTO item_revisions(item_id,content) VALUES(2,'Earlier body');
        INSERT INTO items(id,kind,title) VALUES(99,'note','Deleted'); DELETE FROM items WHERE id=99;""")
        return con

    def test_constraint_expansion_preserves_rows_links_history_and_autoincrement(self):
        con=self.legacy();tables=['items','files','item_links','item_revisions','sqlite_sequence'];before={table:con.execute('SELECT rowid,* FROM '+table+' ORDER BY rowid').fetchall() for table in tables}
        allow_blog_documents(con);allow_blog_documents(con)
        for table in tables:self.assertEqual(con.execute('SELECT rowid,* FROM '+table+' ORDER BY rowid').fetchall(),before[table])
        self.assertEqual(con.execute('PRAGMA foreign_keys').fetchone()[0],1);self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(con.execute("INSERT INTO items(kind,title) VALUES('blog','A blog')").lastrowid,100)
        self.assertTrue(con.execute("SELECT 1 FROM sqlite_master WHERE name='idx_items_parent'").fetchone());con.close()

    def test_invalid_reference_rolls_back_the_rebuild(self):
        con=self.legacy();con.execute('PRAGMA foreign_keys=OFF');con.execute('INSERT INTO files VALUES(2,999)');con.commit();con.execute('PRAGMA foreign_keys=ON');before=con.execute("SELECT sql FROM sqlite_master WHERE name='items'").fetchone()[0]
        with self.assertRaises(RuntimeError):allow_blog_documents(con)
        self.assertEqual(con.execute("SELECT sql FROM sqlite_master WHERE name='items'").fetchone()[0],before)
        self.assertEqual(con.execute('SELECT COUNT(*) FROM items').fetchone()[0],2);self.assertEqual(con.execute('PRAGMA foreign_keys').fetchone()[0],1);con.close()
