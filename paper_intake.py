"""Prepare an explicit paper PDF and attribute the selected reading material."""
from urllib.parse import quote

from paper_tools import public_url, markdown_text


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
    if material['text']:
        scope='所选 PDF 提取的文字'
        if material['truncated']:scope+='（部分内容）'
        lines+=['','> 阅读依据：'+scope+'。图表、公式和排版细节请对照下方 PDF。']
    else:lines+=['','> 已保留所选 PDF；尚未取得可用于自动分析的文字。']
    if include_pdf:lines+=['','## 原文 PDF','', '@[pdf](/files/'+file['id']+'?inline=1)','']
    return '\n'.join(lines)+'\n'
