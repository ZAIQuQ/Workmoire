"""Prepare an explicit paper PDF and attribute the selected reading material."""
from urllib.parse import quote
import json
import re
import unicodedata

from paper_tools import public_url, markdown_text
from paper_runtime import PaperFailure


def _text(value, limit=200):
    return ' '.join(value.split())[:limit] if isinstance(value, str) else ''


def _key(value):
    return ''.join(unicodedata.normalize('NFKC', value).casefold().split())


def _name_key(value):
    # PDF producers sometimes emit a spaced accent separately from its letter.
    normalized = unicodedata.normalize('NFKD', value.casefold())
    return ''.join(char for char in normalized
                   if not char.isspace() and not unicodedata.combining(char))


def _arxiv_first_release(source_text):
    """Read an explicit v1 date from the first page's arXiv watermark."""
    first_page = source_text.split('[第 2 页]', 1)[0]
    watermark = re.search(
        r'\barXiv:\s*\d{4}\.\d{4,5}v1\s+\[[a-z][\w.-]*\]\s+'
        r'(?P<date>(?:[1-9]|[12]\d|3[01])\s+'
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?:19|20)\d{2})\b',
        first_page,
        re.I,
    )
    if watermark:
        return {'name': _text(watermark['date']), 'evidence': _text(watermark[0], 600)}
    return None


def _pmlr_publication(source_text):
    """Link an official proceedings masthead to the first-page publication footer."""
    first_page = source_text.split('[第 2 页]', 1)[0]
    header = re.search(
        r'(?m)^Proceedings of Machine Learning Research (?:vol\s+)?'
        r'(?P<volume>\d+|TBD)\s*:\s*\d+\s*[-–—]\s*\d+,?\s*'
        r'(?P<year>(?:19|20)\d{2})[^\S\n]+(?P<venue>[^\n]{8,140})',
        first_page, re.I,
    )
    if not header:
        return None
    footer = re.search(
        r'(?m)^\s*©\s*' + header['year'] + r'[^\n]+\n\s*'
        r'(?P<volume>\d+)\s*:\s*\d+\s*[-–—]\s*\d+\s*,\s*'
        + header['year'] + r'\s*$', first_page,
    )
    if not footer or header['volume'].upper() not in {'TBD', footer['volume']}:
        return None
    return {'status': 'published', 'venue': _text(header['venue']), 'year': header['year'],
            'evidence': _text(header[0], 600), 'publication_footer': _text(footer[0], 350)}


def _official_publication(source_text):
    proceedings = _pmlr_publication(source_text)
    if proceedings:
        return proceedings
    first_page = ' '.join(source_text.split('[第 2 页]', 1)[0].split())
    # PDF.js preserves discretionary line-end hyphens after visual layout.
    first_page = re.sub(r'(?<=[A-Za-z])- (?=[A-Za-z])', '', first_page)
    patterns = (
        r'(?P<venue>Journal of Machine Learning Research) \d+ \((?P<year>20\d{2})\) '
        r'\d+\s*[-–—]\s*\d+.{0,100}?Published \d{1,2}/\d{2}',
        r'Proceedings of the (?P<venue>\d+\s*(?:st|nd|rd|th) International Conference on'
        r' Artificial Intelligence and Statistics \(AISTATS\)) (?P<year>20\d{2}),'
        r' [^.]{2,80}\. PMLR\s*:\s*Volume \d+\. Copyright',
        r'Proceedings of the (?P<venue>[^.]{8,145}Conference on Machine Learning)\s*, [^.]{2,80}\. '
        r'PMLR \d+, (?P<year>20\d{2})\. Copyright',
        r'Proceedings of the (?P<venue>[^,]{8,135}Association for Computational Linguistics'
        r'(?: \([^)]{1,64}\))?)\s*,\s*pages? \d+\s*[-–—]\s*\d+'
        r'.{0,95}?©\s*(?P<year>20\d{2})\s+Association for Computational Linguistics',
    )
    for pattern in patterns:
        hit = re.search(pattern, first_page, re.I)
        if hit:
            return {'status': 'published', 'venue': _text(hit['venue']), 'year': hit['year'],
                    'evidence': _text(hit[0], 600)}
    return None


def parse_paper_analysis(value, source_text, *, require_compact=False):
    """Validate model/reviewed output and retain only facts with supplied evidence."""
    if isinstance(value, str):
        raw = value.strip()
        if raw.startswith('```') and raw.endswith('```'):
            raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.I)[:-3].strip()
        try:value = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise ValueError('论文分析结果格式不完整，请重试分析') from exc
    compact = isinstance(value, dict) and value.get('report_version') == 4
    if require_compact and not compact:
        raise ValueError('论文分析结果未使用阅读报告模板，请重试分析')
    if not isinstance(value, dict) or (not compact and (not isinstance(value.get('brief'), str) or not value['brief'].strip() or len(value['brief']) > 9000)):
        raise ValueError('论文分析结果缺少有效摘要，请重试分析')
    source = _key(source_text)

    def evidence(row):
        excerpt = _text(row.get('evidence'), 600) if isinstance(row, dict) else ''
        return excerpt if len(_key(excerpt)) >= 6 and _key(excerpt) in source else ''

    def fact(row, *, person=False):
        if not isinstance(row, dict):
            return None
        name, excerpt = _text(row.get('name')), evidence(row)
        key = _name_key if person else _key
        if person and not excerpt:
            raw = _text(row.get('evidence'), 600)
            if len(key(raw)) >= 6 and key(raw) in key(source_text):
                excerpt = raw
        return {'name': name, 'evidence': excerpt} if name and excerpt and key(name) in key(excerpt) else None

    def facts(rows, limit=12, *, person=False):
        found=[];seen=set()
        for row in rows[:limit] if isinstance(rows, list) else []:
            result=fact(row, person=person)
            if result and _key(result['name']) not in seen:
                found.append(result);seen.add(_key(result['name']))
        return found

    result={'brief':value.get('brief','').strip() if not compact else '', 'abstract':None, 'title':fact(value.get('title')),
            'authors':facts(value.get('authors'), person=True), 'affiliations':facts(value.get('affiliations'),6),
            'corresponding_authors':[], 'labs':[], 'publication':{}, 'fields':{}}
    author_names={_key(row['name']) for row in result['authors']}
    for raw in value.get('corresponding_authors',[])[:4] if isinstance(value.get('corresponding_authors'),list) else []:
        row=fact(raw)
        if not row or _key(row['name']) not in author_names:continue
        cue=r'correspond|通讯|通信|联系作者'
        named=bool(re.search(cue,row['evidence'],re.I))
        designation=evidence({'evidence':raw.get('designation')});marker=_text(raw.get('marker'),2)
        marked=(marker in {'*','∗','†','‡','✉','1','2','3'} and marker in designation and
                re.search(cue,designation,re.I) and
                (_key(row['name']+marker) in _key(row['evidence']) or _key(marker+row['name']) in _key(row['evidence'])))
        if named or marked:
            row.update(designation=designation,marker=marker);result['corresponding_authors'].append(row)
    leads={_key(row['name']) for row in result['corresponding_authors']}
    for row in value.get('labs',[])[:4] if isinstance(value.get('labs'),list) else []:
        lab=fact(row)
        if not lab:continue
        lead=_text(row.get('lead'))
        # A known author alone is insufficient to attribute a lab to them.
        if lead and (_key(lead) not in leads or _key(lead) not in _key(lab['evidence'])):continue
        lab['lead']=lead;result['labs'].append(lab)
    publication=value.get('publication')
    excerpt=evidence(publication)
    if excerpt:
        status=publication.get('status')
        cues={'published':r'published|proceedings|journal|发表于|正式发表',
              'accepted':r'accepted|to appear|录用|接收', 'submitted':r'submitted|under review|投稿|在审',
              'preprint':r'preprint|arxiv|预印本'}
        if isinstance(status,str) and status in cues and re.search(cues[status],excerpt,re.I):
            venue=_text(publication.get('venue'));year=_text(publication.get('year'),4)
            result['publication']={'status':status, 'venue':venue if _key(venue) in _key(excerpt) else '',
                                   'year':year if re.fullmatch(r'(19|20)\d{2}',year) and year in excerpt else '', 'evidence':excerpt}
    if compact:
        proceedings = _official_publication(source_text)
        if proceedings:
            result['publication'] = proceedings
    fields=value.get('fields')
    if evidence(fields):
        for level in ['primary','secondary']:
            name=_text(fields.get(level),32)
            if name and name not in {'论文','未知','待核实','未确定'} and not re.search(r'[,，;；#<>\[\]{}|/\\]',name):
                result['fields'][level]=name
        result['fields']['evidence']=evidence(fields)
    abstract=value.get('abstract')
    if isinstance(abstract,dict):
        original=abstract.get('original');translation=abstract.get('translation');language=abstract.get('language')
        if (isinstance(language,str) and language in {'en','zh'} and isinstance(original,str) and isinstance(translation,str)
                and 40 <= len(original.strip()) <= 8000 and 20 <= len(translation.strip()) <= 8000
                and _key(original) in source):
            result['abstract']={'language':language,'original':original.strip(),'translation':translation.strip()}
    if compact:
        result['report_version'] = 4
        result['abstract'] = None
        reading = value.get('reading')
        if not isinstance(reading, dict):raise ValueError('论文分析结果缺少阅读笔记，请重试分析')
        def prose(raw, limit, required=False):
            if raw is None:raw = ''
            if not isinstance(raw,str):raise ValueError('论文分析结果字段格式无效，请重试分析')
            text = ' '.join(raw.split())
            if len(text)>limit or (required and not text):raise ValueError('论文分析结果超出模板篇幅或缺少核心内容，请重试分析')
            if re.search(r'依据所提供|材料未明确|待核实|归类依据|关键证据与边界|只读取了|末尾截断|^#{1,6}\s|<[^>]+>|```',text):
                raise ValueError('论文分析结果包含模板外说明，请重试分析')
            return text
        contributions = reading.get('contributions')
        keywords = reading.get('keywords',[])
        if not isinstance(contributions,list) or not 1<=len(contributions)<=3 or not all(isinstance(c,dict) for c in contributions):
            raise ValueError('论文分析结果应包含 1–3 条 Contribution，请重试分析')
        if not isinstance(keywords,list) or len(keywords)>5:raise ValueError('论文分析结果关键词最多 5 个，请重试分析')
        first = fact(reading.get('first_public'))
        # Preserve source spelling; a revision date alone cannot establish first publication.
        if first and not re.search(r'\bv1\b|\barXiv:\s*\d{4}\.\d{4,5}v1\b|first|initial|首次',first['evidence'],re.I):first=None
        if first and len(first['name'])>60:first=None
        result['reading'] = {
            'first_public':first or _arxiv_first_release(source_text), 'direction':prose(reading.get('direction'),48),
            'keywords':list(dict.fromkeys(prose(word,32,True) for word in keywords)),
            'motivation':prose(reading.get('motivation'),150,True),
            'contributions':[{'name':prose(c.get('name'),24,True),'description':prose(c.get('description'),90,True)} for c in contributions],
            'experiments':prose(reading.get('experiments'),100), 'summary':prose(reading.get('summary'),70,True)}
        paper_reading_markdown(result)  # Enforce the complete visible budget as well as each field.
    return result


QUALITY_CHECKS=('grounded','core_insight','mechanism','experiments','concise')

def validate_paper_quality(raw, source_text, *, blocks=()):
    """Fail closed on missing checks, unsupported citations or a rejected review."""
    raw = raw.strip() if isinstance(raw, str) else ''
    if raw.startswith('```') and raw.endswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.I)[:-3].strip()
    try:
        result = json.loads(raw)
    except ValueError:
        result = None
    checks = result.get('checks') if isinstance(result, dict) else None
    if not isinstance(checks, dict) or any(type(checks.get(key)) is not bool for key in QUALITY_CHECKS):
        raise PaperFailure('quality_response', '内容质量校验未返回有效结果，请重试分析。')
    failed = tuple(key for key in QUALITY_CHECKS if not checks[key])
    if result.get('approved') is False and failed:
        issues = result.get('issues')
        feedback = tuple(filter(None, (_text(issue, 160) for issue in issues[:3]))) if isinstance(issues, list) else ()
        raise PaperFailure('quality_rejected', '论文报告未通过内容质量校验，请重试分析。', failed, feedback)
    if result.get('approved') is not True or failed or result.get('issues') != []:
        raise PaperFailure('quality_response', '内容质量校验未返回有效结果，请重试分析。')
    excerpts = result.get('evidence')
    if blocks and isinstance(excerpts, list) and 1 <= len(excerpts) <= 5 and all(
        type(index) is int and 1 <= index <= len(blocks) for index in excerpts
    ):
        return
    source = _key(source_text)
    if not (isinstance(excerpts, list) and 1 <= len(excerpts) <= 5 and all(
        isinstance(e, str) and 12 <= len(e) <= 600 and len(_key(e)) >= 6 and _key(e) in source
        for e in excerpts
    )):
        raise PaperFailure('quality_evidence', '内容质量校验的引文未能与 PDF 文字匹配，请重试分析。')


def paper_reading_markdown(details):
    """Render the owner's compact format; the model cannot add sections."""
    reading=details['reading'];rows=[];visible=[]
    def row(label,text,code=False):
        if not text:return
        visible.append(label+'： '+text)
        safe=markdown_text(text)
        if code:safe='`'+text.replace('`','')+'`'
        rows.append('- **'+label+'：** '+safe)
    if reading['first_public']:row('首次公开',reading['first_public']['name'])
    publication=details['publication']
    if publication.get('status') in {'published','accepted'} and publication.get('venue'):
        row('正式发表','，'.join(filter(None,[publication['venue'],publication.get('year')]))+('（已录用）' if publication['status']=='accepted' else ''))
    row('研究方向',reading['direction'],True)
    if reading['keywords']:
        visible.append('研究关键词： '+'、'.join(reading['keywords']))
        rows.append('- **研究关键词：** '+'、'.join('`'+word.replace('`','')+'`' for word in reading['keywords']))
    row('Motivation',reading['motivation'])
    rows.append('- **Contribution：**');visible.append('Contribution：')
    for c in reading['contributions']:
        visible.append(c['name']+'： '+c['description'])
        rows.append('  - **'+markdown_text(c['name'])+'：** '+markdown_text(c['description']))
    row('实验贡献',reading['experiments']);row('一句话总结',reading['summary'])
    if sum(map(len,visible))>800:raise ValueError('论文分析结果超过阅读笔记 800 字符上限，请重试分析')
    return '## 阅读笔记\n\n'+'\n'.join(rows)


def check_report_length(content):
    # Count visible text conservatively, excluding the PDF URL and source target.
    text=re.sub(r'@\[pdf\]\([^\n]*\)', '', content)
    text=re.sub(r'\[([^\]]*)\]\([^\n]*?\)', r'\1', text)
    text=re.sub(r'(?m)^\s*(?:## |[-] )', '', text)
    text=text.replace('**','').replace('`','').replace('\n','')
    if len(text)>1032:raise ValueError('论文分析结果超过报告总篇幅，请精简标题或重试分析')


def paper_field_tags(details):
    tags=[]
    for level in ['primary','secondary']:
        tag=details.get('fields',{}).get(level,'')
        if tag and _key(tag) not in {_key(t) for t in tags}:tags.append(tag)
    return tags[:2]


def paper_profile_markdown(details):
    publication=details['publication'];fields=details['fields']
    status={'published':'已发表','accepted':'已录用','submitted':'投稿 / 在审','preprint':'预印本版本'}.get(publication.get('status'))
    rows=[];sections=[]
    if status:rows.append('- **发表情况**：'+markdown_text(' · '.join(filter(None,[status,publication.get('venue'),publication.get('year')]))))
    for key,label in [('affiliations','作者单位'),('corresponding_authors','通讯作者')]:
        if details[key]:rows.append('- **'+label+'**：'+'；'.join(markdown_text(row['name']) for row in details[key]))
    if details['labs']:
        rows.append('- **团队 / 实验室**：'+'；'.join(markdown_text(row['name'])+('（通讯作者：'+markdown_text(row['lead'])+'）' if row['lead'] else '') for row in details['labs']))
    if rows:sections.append('## 发表与作者团队\n\n'+'\n'.join(rows))
    rows=['- **'+label+'**：'+markdown_text(fields[key]) for key,label in [('primary','一级领域'),('secondary','二级领域')] if fields.get(key)]
    if rows:sections.append('## 研究领域\n\n'+'\n'.join(rows))
    return '\n\n'.join(sections)


def paper_abstract_markdown(details):
    abstract=details.get('abstract')
    if not abstract:return ''
    chinese=abstract['original'] if abstract['language']=='zh' else abstract['translation']
    english=abstract['original'] if abstract['language']=='en' else abstract['translation']
    return '## 摘要\n\n### 中文摘要\n\n'+markdown_text(chinese)+'\n\n### English Abstract\n\n'+markdown_text(english)


def paper_source(reference: object) -> str:
    value=str(reference or '').strip()
    return public_url(value) if value else ''


def selected_pdf_header(paper: dict, file: dict, material: dict, include_pdf: bool = True, compact: bool = False) -> str:
    title=markdown_text(paper['title'])
    if compact and paper.get('url'):title='['+title+']('+quote(paper['url'],safe=':/?&=%#@+~')+')'
    lines=['## 论文信息','', '- **标题**：'+title]
    if paper.get('authors'):lines.append('- **作者**：'+markdown_text('; '.join(paper['authors'])))
    if not compact and paper.get('year'):lines.append('- **年份**：'+markdown_text(paper['year']))
    if not compact and paper.get('venue'):lines.append('- **期刊 / 会议**：'+markdown_text(paper['venue']))
    if not compact and paper.get('url'):lines.append('- **来源链接**：[打开原文]('+quote(paper['url'],safe=':/?&=%#@+~')+')')
    if not compact:lines.append('- **使用的 PDF**：'+markdown_text(file['name']))
    if include_pdf:lines+=['','## 原文 PDF','', '@[pdf](/files/'+file['id']+'?inline=1)','']
    return '\n'.join(lines)+'\n'
