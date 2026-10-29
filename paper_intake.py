"""Prepare an explicit paper PDF and attribute the selected reading material."""
from urllib.parse import quote
import json
import re
import unicodedata

from paper_tools import public_url, markdown_text


def _text(value, limit=200):
    return ' '.join(value.split())[:limit] if isinstance(value, str) else ''


def _key(value):
    return ''.join(unicodedata.normalize('NFKC', value).casefold().split())


def parse_paper_analysis(value, source_text):
    """Validate model/reviewed output and retain only facts with supplied evidence."""
    if isinstance(value, str):
        raw = value.strip()
        if raw.startswith('```') and raw.endswith('```'):
            raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.I)[:-3].strip()
        try:value = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise ValueError('论文分析结果格式不完整，请重试分析') from exc
    if not isinstance(value, dict) or not isinstance(value.get('brief'), str) or not value['brief'].strip() or len(value['brief']) > 9000:
        raise ValueError('论文分析结果缺少有效摘要，请重试分析')
    source = _key(source_text)

    def evidence(row):
        excerpt = _text(row.get('evidence'), 600) if isinstance(row, dict) else ''
        return excerpt if len(_key(excerpt)) >= 6 and _key(excerpt) in source else ''

    def fact(row):
        if not isinstance(row, dict):return None
        name, excerpt = _text(row.get('name')), evidence(row)
        return {'name':name, 'evidence':excerpt} if name and excerpt and _key(name) in _key(excerpt) else None

    def facts(rows, limit=12):
        found=[];seen=set()
        for row in rows[:limit] if isinstance(rows, list) else []:
            result=fact(row)
            if result and _key(result['name']) not in seen:
                found.append(result);seen.add(_key(result['name']))
        return found

    result={'brief':value['brief'].strip(), 'abstract':None, 'title':fact(value.get('title')),
            'authors':facts(value.get('authors')), 'affiliations':facts(value.get('affiliations'),6),
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
    return result


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


def selected_pdf_header(paper: dict, file: dict, material: dict, include_pdf: bool = True) -> str:
    lines=['## 论文信息','', '- **标题**：'+markdown_text(paper['title'])]
    if paper.get('authors'):lines.append('- **作者**：'+markdown_text('; '.join(paper['authors'])))
    if paper.get('year'):lines.append('- **年份**：'+markdown_text(paper['year']))
    if paper.get('venue'):lines.append('- **期刊 / 会议**：'+markdown_text(paper['venue']))
    if paper.get('url'):lines.append('- **来源链接**：[打开原文]('+quote(paper['url'],safe=':/?&=%#@+~')+')')
    lines.append('- **使用的 PDF**：'+markdown_text(file['name']))
    if include_pdf:lines+=['','## 原文 PDF','', '@[pdf](/files/'+file['id']+'?inline=1)','']
    return '\n'.join(lines)+'\n'
