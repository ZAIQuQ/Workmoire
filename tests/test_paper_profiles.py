"""Grounded paper facts, inferred fields, and explicit tag/save boundaries."""
import json
import unittest
from unittest.mock import patch
from paper_fixtures import model_fixture, compact_fixture, analysis_fixture, PROFILE_TEXT, READING_ABSTRACT, READING_TRANSLATION, READING_BRIEF
from paper_intake import parse_paper_analysis, paper_field_tags, paper_profile_markdown, paper_abstract_markdown, paper_reading_markdown, check_report_length, validate_paper_quality
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

    def test_missing_profile_fields_and_classification_explanations_are_omitted(self):
        empty=parse_paper_analysis(analysis_fixture(),PROFILE_TEXT)
        self.assertEqual(paper_profile_markdown(empty),'')
        raw=json.loads(analysis_fixture(profile=True));raw['fields']['reason']='Do not render classification reasoning.'
        details=parse_paper_analysis(raw,PROFILE_TEXT);rendered=paper_profile_markdown(details)
        self.assertNotIn('reason',details['fields'])
        for phrase in ['依据所提供','待核实','未确定','归类依据','Do not render']:self.assertNotIn(phrase,rendered)
        details['affiliations']=[];details['labs']=[];details['corresponding_authors']=[];details['publication']={}
        self.assertNotIn('发表与作者团队',paper_profile_markdown(details))
        self.assertIn('一级领域',paper_profile_markdown(details))

    def test_bilingual_abstract_requires_a_matching_original_and_round_trips_review(self):
        for language,original,translation in [('en',READING_ABSTRACT,READING_TRANSLATION),('zh',READING_TRANSLATION,READING_ABSTRACT)]:
            raw={'brief':READING_BRIEF,'abstract':{'language':language,'original':original,'translation':translation}}
            details=parse_paper_analysis(raw,PROFILE_TEXT+'\nAbstract\n'+original)
            rendered=paper_abstract_markdown(details)
            self.assertIn(READING_ABSTRACT,rendered);self.assertIn(READING_TRANSLATION,rendered)
            self.assertEqual(parse_paper_analysis(details,PROFILE_TEXT+'\nAbstract\n'+original),details)
            self.assertEqual(paper_abstract_markdown(parse_paper_analysis(raw,PROFILE_TEXT)),'')
            raw['abstract']['translation']=''
            self.assertEqual(paper_abstract_markdown(parse_paper_analysis(raw,PROFILE_TEXT+'\n'+original)),'')

    def test_compact_report_structure_evidence_and_roundtrip(self):
        raw=json.loads(compact_fixture(profile=True))
        source=PROFILE_TEXT+' First public release v1: 15 January 2026, arXiv.'
        raw['reading']['first_public']={'name':'15 January 2026, arXiv','evidence':'First public release v1: 15 January 2026, arXiv.'}
        details=parse_paper_analysis(raw,source,require_compact=True)
        report=paper_reading_markdown(details)
        labels=['首次公开','正式发表','研究方向','研究关键词','Motivation','Contribution','一句话总结']
        positions=[report.index('**'+label+'：**') for label in labels]
        self.assertEqual(positions,sorted(positions))
        self.assertEqual(parse_paper_analysis(details,source,require_compact=True),details)
        self.assertNotIn('## 摘要',report);self.assertNotIn('作者单位',report)
        raw['reading']['first_public']['evidence']='Updated v2: 15 January 2026, arXiv.'
        details=parse_paper_analysis(raw,PROFILE_TEXT+' Updated v2: 15 January 2026, arXiv.',require_compact=True)
        self.assertNotIn('首次公开',paper_reading_markdown(details))
        raw['publication']['status']='submitted';raw['publication']['evidence']='Submitted to Example Conference 2026.'
        self.assertNotIn('正式发表',paper_reading_markdown(parse_paper_analysis(raw,source+' Submitted to Example Conference 2026.',require_compact=True)))

    def test_compact_report_accepts_arxiv_v1_watermark_but_not_later_versions(self):
        raw = json.loads(compact_fixture())
        for version in (1, 2, 10):
            with self.subTest(version=version):
                watermark = f'arXiv:2601.00000v{version} [cs.LG] 15 Jan 2026'
                raw['reading']['first_public'] = {'name': '15 Jan 2026', 'evidence': watermark}
                report = paper_reading_markdown(parse_paper_analysis(raw, PROFILE_TEXT + '\n' + watermark, require_compact=True))
                self.assertEqual('首次公开' in report, version == 1)

    def test_compact_report_recovers_missing_first_release_from_the_first_page(self):
        raw = json.loads(compact_fixture())
        watermark = 'arXiv:2601.00000v1 [cs.LG] 15\nJan 2026'
        source = '[第 1 页]\n' + PROFILE_TEXT + watermark + '\n[第 2 页]\nBody'
        details = parse_paper_analysis(raw, source, require_compact=True)
        self.assertEqual(details['reading']['first_public']['name'], '15 Jan 2026')
        self.assertIn('首次公开', paper_reading_markdown(details))
        self.assertEqual(parse_paper_analysis(details, source), details)
        for other in (watermark.replace('v1 ', 'v10 '), '[第 2 页]\n' + watermark):
            self.assertIsNone(parse_paper_analysis(raw, PROFILE_TEXT + other)['reading']['first_public'])

    def test_compact_report_rejects_verbose_or_off_template_results(self):
        with self.assertRaisesRegex(ValueError,'模板'):
            parse_paper_analysis(analysis_fixture(),PROFILE_TEXT,require_compact=True)
        for key,value in [('motivation','字'*151),('summary','字'*71),('experiments','字'*101),('keywords',['term']*6),('contributions',[{'name':'模块','description':'说明'}]*4),('motivation','材料未明确，待核实'),('summary',None)]:
            raw=json.loads(compact_fixture());raw['reading'][key]=value
            with self.assertRaisesRegex(ValueError,'论文分析结果'):parse_paper_analysis(raw,PROFILE_TEXT,require_compact=True)
        raw=json.loads(compact_fixture(profile=True));r=raw['reading']
        r.update(motivation='字'*150,summary='字'*70,experiments='字'*100,direction='字'*48,keywords=[str(i)+'字'*31 for i in range(5)],contributions=[{'name':'字'*24,'description':'字'*90}]*3)
        with self.assertRaisesRegex(ValueError,'800'):parse_paper_analysis(raw,PROFILE_TEXT,require_compact=True)
        with self.assertRaises(ValueError):check_report_length('字'*1033)
        check_report_length('字'*1000+'\n@[pdf](/files/'+'a'*32+'?inline=1)')

    def test_quality_gate_requires_all_checks_and_source_evidence(self):
        from paper_fixtures import quality_fixture
        raw=json.loads(quality_fixture(PROFILE_TEXT))
        validate_paper_quality(json.dumps(raw),PROFILE_TEXT)
        for check in raw['checks']:
            bad=json.loads(json.dumps(raw));bad['checks'][check]=False
            with self.assertRaisesRegex(ValueError,'质量校验'):validate_paper_quality(json.dumps(bad),PROFILE_TEXT)
        for update in [{'approved':False},{'approved':'true'},{'checks':{}},{'issues':['wrong number']},{'evidence':[]},{'evidence':['invented evidence not in the provided paper']}]:
            with self.assertRaisesRegex(ValueError,'质量校验'):validate_paper_quality(json.dumps({**raw,**update}),PROFILE_TEXT)
        for bad in ['not json','[]','null']:
            with self.assertRaisesRegex(ValueError,'质量校验'):validate_paper_quality(bad,PROFILE_TEXT)

    def test_quality_gate_validates_numbered_pdf_evidence(self):
        from paper_fixtures import quality_fixture
        verdict = json.loads(quality_fixture(PROFILE_TEXT))
        blocks = [PROFILE_TEXT[:120], PROFILE_TEXT[120:]]
        validate_paper_quality(json.dumps({**verdict, 'evidence': [1, 2]}), PROFILE_TEXT, blocks=blocks)
        for numbers in ([0], [3], [True], [1, '2']):
            with self.assertRaisesRegex(ValueError, '质量校验'):
                validate_paper_quality(json.dumps({**verdict, 'evidence': numbers}), PROFILE_TEXT, blocks=blocks)

    def test_proceedings_metadata_combines_matching_first_page_masthead_and_footer(self):
        header = 'Proceedings of Machine Learning Research vol TBD:1–24, 2025  5th Example Conference'
        footer = '© 2025 A. Researcher.\n301:42–65, 2025'
        source = '[第 1 页]\n' + header + '\n' + PROFILE_TEXT + footer + '\n[第 2 页]\nFurther material.'
        details = parse_paper_analysis(compact_fixture(), source, require_compact=True)
        publication = details['publication']
        self.assertEqual((publication['status'], publication['venue'], publication['year']),
                         ('published', '5th Example Conference', '2025'))
        self.assertEqual(parse_paper_analysis(details, source), details)
        for invalid in (source.replace('301:42–65, 2025', '301:42–65, 2024'),
                        source.replace(footer, '[第 2 页]\n' + footer)):
            self.assertEqual(parse_paper_analysis(compact_fixture(), invalid)['publication'], {})

    def test_normalizes_spaced_pdf_accents_for_authors(self):
        report = json.loads(compact_fixture())
        report['authors'] = [{'name': 'Mário Cardoso', 'evidence': 'Mário Cardoso'}]
        result = parse_paper_analysis(report, PROFILE_TEXT + '\nM´ ario Cardoso')
        self.assertEqual([row['name'] for row in result['authors']], ['Mário Cardoso'])
        result = parse_paper_analysis(report, PROFILE_TEXT + '\nM´ ario Carvalho')
        self.assertEqual(result['authors'], [])

    def test_official_publication_requires_article_specific_front_page_evidence(self):
        lines = [
            'Proceedings of the 27th International Conference on Artificial Intelligence and Statistics (AISTATS) 2024, Example City. PMLR: Volume 238. Copyright 2024 by the author(s).',
            'Proceedings of the 27 th International Conference on Artifi- cial Intelligence and Statistics (AIS- TATS) 2024, Example City. PMLR: Volume 238. Copy- right 2024 by the author(s).',
            'Proceedings of the 41 st International Conference on Machine Learning , Example City. PMLR 235, 2024. Copyright 2024 by the author(s).',
            'Journal of Machine Learning Research 25 (2024) 1-40 Submitted 7/23; Revised 3/24; Published 6/24',
            'Proceedings of the 41st International Conference on Machine Learning, Example City. PMLR 235, 2024. Copyright 2024 by the author(s).',
            'Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pages 54–73 August 11-16, 2024 ©2024 Association for Computational Linguistics',
        ]
        for line in lines:
            source = '[第 1 页]\n' + line + '\n[第 2 页]\n' + PROFILE_TEXT
            details = parse_paper_analysis(compact_fixture(), source)
            self.assertEqual(details['publication']['status'], 'published')
            self.assertEqual(details['publication']['year'], '2024')
            self.assertEqual(parse_paper_analysis(compact_fixture(), '[第 2 页]\n' + line)['publication'], {})

    def test_invalid_model_output_is_actionable_and_never_exposed_as_raw_json(self):
        for raw in ['not json','{}','[]',json.dumps({'brief':'x'*9001})]:
            with self.assertRaisesRegex(ValueError,'论文分析结果'):parse_paper_analysis(raw,PROFILE_TEXT)

class PaperProfileHttpTests(unittest.TestCase):
    def setUp(self):
        support.DocumentHttpTests.setUp(self)
        gate = patch.object(app, 'paper_analysis_enabled', return_value=True)
        gate.start()
        self.addCleanup(gate.stop)
    tearDown=support.DocumentHttpTests.tearDown
    request=support.DocumentHttpTests.request
    fixture_file=support.DocumentHttpTests.fixture_file

    def test_optional_link_profile_review_and_tags_only_persist_with_normal_save(self):
        self.fixture_file('chosen.pdf',b'%PDF-1.4 synthetic','application/pdf')
        payload={'file_id':'a'*32,'title':'metadata title','author':'metadata author','title_confirmed':False,'author_confirmed':False,'text':PROFILE_TEXT,'page_count':1,'pages_read':1,'generate':True}
        with patch.object(paper_tools,'fetch_public') as fetch,patch.object(app,'invoke_codex',side_effect=model_fixture(compact_fixture(profile=True))) as invoke:
            status,body,_=self.request('/api/papers/draft','POST',payload)
            self.assertEqual(status,200);draft=json.loads(body)
            self.assertEqual(draft['title'],'Synthetic Sequence Study');self.assertEqual(draft['tags'],['机器学习','时间序列预测'])
            for text in ['已录用','Example Conference','Example Author Two','研究方向','Contribution']:self.assertIn(text,draft['content'])
            self.assertNotIn('来源链接',draft['content'])
            with app.open_db() as con:self.assertEqual(con.execute('SELECT count(*) FROM items').fetchone()[0],0)
            reviewed={**payload,'generate':False,'reviewed_analysis':draft['details'],'title':'My corrected title','title_confirmed':True,'reference':'https://example.org/source','selected_tags':['时间序列预测','unrelated injected tag']}
            status,body,_=self.request('/api/papers/draft','POST',reviewed);self.assertEqual(status,200);final=json.loads(body)
            self.assertEqual(final['title'],'My corrected title');self.assertEqual(final['tags'],['时间序列预测'])
            self.assertIn('[My corrected title](https://example.org/source)',final['content']);self.assertNotIn('来源链接',final['content']);self.assertNotIn('使用的 PDF',final['content']);self.assertIn('Synthetic brief',final['content'])
            self.assertEqual(invoke.call_count,2);fetch.assert_not_called()
            reviewed_candidate=invoke.call_args.args[0].split('---待核验报告---\n')[1].split('\n\n---论文原文')[0]
            self.assertEqual(set(json.loads(reviewed_candidate)),{'title','authors','publication','reading'})
        status,body,_=self.request('/api/items','POST',{'kind':'paper','title':final['title'],'content':final['content'],'tags':','.join(final['tags'])})
        self.assertEqual(status,201);self.assertEqual(json.loads(body)['item']['tags'],'论文,时间序列预测')

    def test_compact_report_has_only_template_sections_without_abstract_or_process_copy(self):
        self.fixture_file('chosen.pdf',b'%PDF-1.4 synthetic','application/pdf')
        text=PROFILE_TEXT+'\nAbstract\n'+READING_ABSTRACT+'\n1 Introduction\nA synthetic introduction.'
        payload={'file_id':'a'*32,'title':'Synthetic study','text':text,'page_count':24,'pages_read':15,'truncated':True}
        result=json.loads(compact_fixture())
        result['abstract']={'language':'en','original':READING_ABSTRACT,'translation':READING_TRANSLATION}
        result['brief']='## Extra unwanted section'
        with patch.object(app,'invoke_codex',side_effect=model_fixture(json.dumps(result,ensure_ascii=False))) as invoke:
            status,body,_=self.request('/api/papers/draft','POST',payload);self.assertEqual(status,200);draft=json.loads(body)
            content=draft['content'];self.assertEqual([line for line in content.splitlines() if line.startswith('## ')],['## 论文信息','## 阅读笔记','## 原文 PDF'])
            self.assertIn('**Motivation：**',content);self.assertNotIn('## 摘要',content);self.assertNotIn('Extra unwanted',content)
            for phrase in ['依据所提供','材料未明确','待核实','归类依据','关键证据与边界','阅读依据','部分文字','末尾截断','发表与作者团队','## 研究领域']:self.assertNotIn(phrase,content)
            self.assertTrue(draft['evidence']['truncated']);self.assertEqual(draft['evidence']['pages_read'],15)
            status,body,_=self.request('/api/papers/draft','POST',{**payload,'generate':False,'reviewed_analysis':draft['details']});self.assertEqual(status,200)
            self.assertEqual(json.loads(body)['content'],content);self.assertEqual(invoke.call_count,2)
        with app.open_db() as con:self.assertEqual(con.execute('SELECT count(*) FROM items').fetchone()[0],0)

    def test_quality_failure_does_not_return_or_store_a_draft(self):
        self.fixture_file('chosen.pdf',b'%PDF-1.4 synthetic','application/pdf')
        payload={'file_id':'a'*32,'title':'Synthetic','text':PROFILE_TEXT,'page_count':1,'pages_read':1}
        invalid_review = '{"approved":false,"checks":{},"evidence":[],"issues":["unsupported experiment"]}'
        with patch.object(app,'invoke_codex',side_effect=[compact_fixture(), invalid_review, invalid_review, invalid_review]) as invoke:
            status,body,_=self.request('/api/papers/draft','POST',payload)
            self.assertEqual(status,400);self.assertIn('质量校验',json.loads(body)['error'])
            self.assertNotIn('content',json.loads(body));self.assertEqual(invoke.call_count,4)
            self.assertGreater(invoke.call_args.kwargs['timeout'],0)
            self.assertLessEqual(invoke.call_args.kwargs['timeout'],app.PAPER_ASSISTANT_TIMEOUT)
        with app.open_db() as con:self.assertEqual(con.execute('SELECT count(*) FROM items').fetchone()[0],0)

    def test_unconfirmed_pdf_author_metadata_is_not_kept_when_analysis_cannot_ground_it(self):
        self.fixture_file('chosen.pdf',b'%PDF-1.4 synthetic','application/pdf')
        payload={'file_id':'a'*32,'title':'A paper','author':'Unverified PDF metadata author','author_confirmed':False,'text':'A synthetic paper about prediction methods. '*10,'page_count':1,'pages_read':1}
        with patch.object(app,'invoke_codex',side_effect=model_fixture(compact_fixture())):
            status,body,_=self.request('/api/papers/draft','POST',payload);self.assertEqual(status,200)
            result=json.loads(body);self.assertEqual(result['paper']['authors'],[]);self.assertNotIn(payload['author'],result['content'])
            status,body,_=self.request('/api/papers/draft','POST',{**payload,'author':'Owner-confirmed author','author_confirmed':True})
            self.assertEqual(status,200);self.assertEqual(json.loads(body)['paper']['authors'],['Owner-confirmed author'])
