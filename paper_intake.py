"""Prepare an explicit paper PDF and attribute the selected reading material."""
from pathlib import PurePosixPath
import re
from urllib.parse import quote, unquote, urlsplit

from paper_tools import fetch_public, lookup_papers, public_url, markdown_text


def paper_source(reference: object) -> str:
    value=str(reference or '').strip()
    return public_url(value) if value else ''


def download_paper(reference: str, max_bytes: int) -> dict:
    """Resolve a public source; return a manual-upload path on download failure."""
    source=paper_source(reference)
    if not source:
        raise ValueError('请上传 PDF 或提供论文链接')
    paper={'title':'','authors':[],'year':'','venue':'','url':source,'pdf_url':''}
    candidate=source if re.search(r'(?:\.pdf$|/pdf(?:/|$))',urlsplit(source).path,re.I) else ''
    parsed=urlsplit(source)
    arxiv=re.fullmatch(r'/(?:abs|html|pdf)/((?:\d{4}\.\d{4,5}|[A-Za-z][A-Za-z.\-]*/\d{7})(?:v\d+)?)(?:\.pdf)?',parsed.path)
    if parsed.hostname in {'arxiv.org','www.arxiv.org','export.arxiv.org'} and arxiv:
        candidate='https://arxiv.org/pdf/'+arxiv[1]
    try:
        if not candidate:
            try:
                matches=lookup_papers(source)
                if len(matches)==1:
                    paper=matches[0];candidate=paper.get('pdf_url','')
            except ValueError:
                # Some download URLs have neither a .pdf suffix nor HTML metadata.
                candidate=source
        if not candidate:
            candidate=source
        raw,_,final=fetch_public(candidate,max_bytes)
        if not raw.startswith(b'%PDF-'):
            raise ValueError('来源没有返回 PDF 文件')
        if not paper.get('title') and urlsplit(source).hostname in {'arxiv.org','www.arxiv.org','export.arxiv.org'}:
            try:
                matches=lookup_papers(source)
                if len(matches)==1:paper=matches[0]
            except (ValueError,OSError):
                pass
        basename=unquote(PurePosixPath(urlsplit(final).path).name)
        name=(paper.get('title') or (basename if basename.lower().endswith('.pdf') else '论文原文'))[:170]
        if not name.lower().endswith('.pdf'):name+='.pdf'
        return {'status':'ready','paper':paper,'source_url':source,'download_url':final,'name':name,'raw':raw}
    except (ValueError,OSError) as error:
        if any(term in str(error) for term in ['公开网络地址','HTTPS','端口']):
            raise ValueError(str(error)) from error
        return {'status':'needs_pdf','paper':paper,'source_url':source,'download_url':candidate,'message':'未能自动取得 PDF。请打开原文下载，然后上传你要使用的文件。','detail':str(error)}


def selected_pdf_header(paper: dict, file: dict, material: dict) -> str:
    lines=['## 论文信息','', '- **标题**：'+markdown_text(paper['title'])]
    if paper.get('authors'):lines.append('- **作者**：'+markdown_text('; '.join(paper['authors'])))
    if paper.get('year'):lines.append('- **年份**：'+markdown_text(paper['year']))
    if paper.get('venue'):lines.append('- **期刊 / 会议**：'+markdown_text(paper['venue']))
    if paper.get('url'):lines.append('- **来源链接**：[打开原文]('+quote(paper['url'],safe=':/?&=%#@+~')+')')
    lines.append('- **使用的 PDF**：'+markdown_text(file['name']))
    if material['text']:
        scope='所选 PDF 提取的文字'
        if material['truncated']:scope+='（部分内容）'
        lines+=['','> 阅读依据：'+scope+'。图表、公式和排版细节请对照下方 PDF。']
    else:lines+=['','> 已保留所选 PDF；尚未取得可用于自动分析的文字。']
    lines+=['','## 原文 PDF','', '@[pdf](/files/'+file['id']+'?inline=1)','']
    return '\n'.join(lines)+'\n'
