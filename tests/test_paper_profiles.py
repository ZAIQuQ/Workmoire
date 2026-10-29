"""Grounded paper facts, inferred fields, and explicit tag/save boundaries."""
import json
import unittest
from unittest.mock import patch
from paper_fixtures import analysis_fixture, PROFILE_TEXT
from paper_intake import parse_paper_analysis, paper_field_tags
import paper_tools
import workspace_server as app
import test_documents as support

class PaperProfileTests(unittest.TestCase):
    def test_profile_retains_supported_facts_and_only_two_field_tags(self):
        details=parse_paper_analysis('```json\n'+analysis_fixture(profile=True)+'\n```', PROFILE_TEXT)
        self.assertEqual(details['publication']['status'],'accepted')
        self.assertEqual(details['labs'][0]['lead'],'Example Author Two')
        self.assertEqual(paper_field_tags(details),['机器学习','时间序列预测'])
        raw=json.loads(analysis_fixture(profile=True));raw['fields']['secondary']='机器学习'
        self.assertEqual(paper_field_tags(parse_paper_analysis(raw,PROFILE_TEXT)),['机器学习'])

    def test_unsupported_publication_correspondence_and_lab_claims_are_not_promoted_to_facts(self):
        raw=json.loads(analysis_fixture(profile=True));raw['publication']['status']='published'
        raw['labs'][0]['lead']='Example Author One'
        raw['corresponding_authors']=[{'name':'Example Author One','evidence':'Example Author One and Example Author Two'}]
        raw['fields']['primary']='论文';raw['fields']['secondary']='机器学习,计算机视觉'
        details=parse_paper_analysis(raw,PROFILE_TEXT)
        self.assertEqual(details['publication'],{});self.assertEqual(details['labs'],[])
        self.assertEqual(details['corresponding_authors'],[]);self.assertEqual(paper_field_tags(details),[])
        details=parse_paper_analysis(analysis_fixture(profile=True),'Unrelated paper text without any of the asserted facts.')
        self.assertEqual(details['authors'],[]);self.assertIsNone(details['title']);self.assertEqual(details['fields'],{})

    def test_separate_correspondence_footnotes_need_a_matching_name_and_marker(self):
        source='Example Author One* and Example Author Two†.\n* Corresponding author.\n† Equal contribution.'
        raw={'brief':'Brief', 'authors':[{'name':'Example Author One','evidence':'Example Author One* and Example Author Two†.'}],
             'corresponding_authors':[{'name':'Example Author One','evidence':'Example Author One* and Example Author Two†.', 'marker':'*','designation':'* Corresponding author.'}]}
        details=parse_paper_analysis(raw,source);self.assertEqual(len(details['corresponding_authors']),1)
        self.assertEqual(parse_paper_analysis(details,source),details)
        raw['corresponding_authors'][0]['marker']='†'
        self.assertEqual(parse_paper_analysis(raw,source)['corresponding_authors'],[])

    def test_invalid_model_output_is_actionable_and_never_exposed_as_raw_json(self):
        for raw in ['not json','{}','[]',json.dumps({'brief':'x'*9001})]:
            with self.assertRaisesRegex(ValueError,'论文分析结果'):parse_paper_analysis(raw,PROFILE_TEXT)

class PaperProfileHttpTests(unittest.TestCase):
    setUp=support.DocumentHttpTests.setUp
    tearDown=support.DocumentHttpTests.tearDown
    request=support.DocumentHttpTests.request
    fixture_file=support.DocumentHttpTests.fixture_file

    def test_optional_link_profile_review_and_tags_only_persist_with_normal_save(self):
        self.fixture_file('chosen.pdf',b'%PDF-1.4 synthetic','application/pdf')
        payload={'file_id':'a'*32,'title':'metadata title','author':'metadata author','title_confirmed':False,'author_confirmed':False,'text':PROFILE_TEXT,'page_count':1,'pages_read':1,'generate':True}
        with patch.object(paper_tools,'fetch_public') as fetch,patch.object(app,'invoke_codex',return_value=analysis_fixture(profile=True)) as invoke:
            status,body,_=self.request('/api/papers/draft','POST',payload)
            self.assertEqual(status,200);draft=json.loads(body)
            self.assertEqual(draft['title'],'Synthetic Sequence Study');self.assertEqual(draft['tags'],['机器学习','时间序列预测'])
            for text in ['已录用','Example Conference','Example Author Two','Example Learning Lab','一级领域','二级领域']:self.assertIn(text,draft['content'])
            self.assertNotIn('来源链接',draft['content'])
            with app.open_db() as con:self.assertEqual(con.execute('SELECT count(*) FROM items').fetchone()[0],0)
            reviewed={**payload,'generate':False,'reviewed_analysis':draft['details'],'title':'My corrected title','title_confirmed':True,'reference':'https://example.org/source','selected_tags':['时间序列预测','unrelated injected tag']}
            status,body,_=self.request('/api/papers/draft','POST',reviewed);self.assertEqual(status,200);final=json.loads(body)
            self.assertEqual(final['title'],'My corrected title');self.assertEqual(final['tags'],['时间序列预测'])
            self.assertIn('https://example.org/source',final['content']);self.assertIn('Synthetic brief',final['content'])
            invoke.assert_called_once();fetch.assert_not_called()
        status,body,_=self.request('/api/items','POST',{'kind':'paper','title':final['title'],'content':final['content'],'tags':','.join(final['tags'])})
        self.assertEqual(status,201);self.assertEqual(json.loads(body)['item']['tags'],'论文,时间序列预测')
