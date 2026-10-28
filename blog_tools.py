"""Read public blog HTML and prepare attributed, bounded summary material."""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import json
import re
from urllib.parse import quote, urlsplit

from paper_tools import clean_text, fetch_public, markdown_text, public_addresses, public_url

MAX_BLOG_TEXT = 30000
MIN_BLOG_TEXT = 80


def blog_url(value: object) -> str:
    try:
        url = public_url(str(value))
        public_addresses(urlsplit(url).hostname)
        return url
    except ValueError as error:
        raise ValueError(str(error).replace('论文', '博客')) from error


def published_date(value: object) -> str:
    match = re.search(r'\b(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', str(value or ''))
    if match:
        try:
            return date(*map(int, match.groups())).isoformat()
        except ValueError:
            pass
    return ''


def source_name(url: str) -> str:
    host = urlsplit(url).hostname or ''
    if host == 'zhihu.com' or host.endswith('.zhihu.com'):
        return '知乎'
    return host.removeprefix('www.')


class BlogHTML(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    BREAKS = {'p','div','section','h1','h2','h3','h4','h5','h6','li','pre','blockquote','br','tr'}
    SKIP = {'script','style','nav','header','footer','aside','form','button','noscript','svg'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.meta = {}
        self.title = []
        self.h1 = []
        self.author = []
        self.candidates = []
        self.ld = []
        self.serial = 0

    def add(self, text):
        active = {frame['id'] for frame in self.stack}
        for candidate in self.candidates:
            if candidate['id'] in active:
                remaining = MAX_BLOG_TEXT - candidate['length']
                if len(text) > remaining:
                    candidate['truncated'] = True
                if remaining > 0:
                    candidate['parts'].append(text[:remaining])
                    candidate['length'] += len(text[:remaining])

    def handle_starttag(self, tag, attrs):
        if self.serial >= 40000 or len(self.stack) >= 200:
            raise ValueError('文章结构过于复杂，请粘贴正文后整理')
        attrs = dict(attrs)
        marker = (attrs.get('class','') + ' ' + attrs.get('id','')).lower()
        parent_skip = any(frame['skip'] for frame in self.stack)
        ignored = tag in self.SKIP or bool(re.search(r'(?:^|[\s_-])(comments?|related|recommend|advert|cookie|navigation|sidebar)(?:[\s_-]|$)', marker))
        self.serial += 1
        frame = {'tag':tag,'id':self.serial,'skip':parent_skip or ignored,'json':None,
                 'author':attrs.get('rel')=='author' or 'authorinfo-name' in marker}
        if tag == 'meta':
            name = (attrs.get('name') or attrs.get('property') or '').lower()
            self.meta.setdefault(name, attrs.get('content',''))
        if tag == 'time' and attrs.get('datetime') and any(frame['tag']=='article' for frame in self.stack):
            self.meta.setdefault('article:published_time', attrs['datetime'])
        if tag == 'script' and attrs.get('type','').lower()=='application/ld+json' and len(self.ld)<8:
            frame['json'] = []
        if tag not in self.VOID:
            self.stack.append(frame)
        if not frame['skip']:
            priority = 6 if attrs.get('itemprop')=='articleBody' or 'post-richtext' in marker else 5 if any(key in marker for key in ['entry-content','post-content','article-content','markdown-body','js_content']) else 4 if tag=='article' else 2 if tag=='main' else 0 if tag=='body' else -1
            if priority>=0 and len(self.candidates)<16:
                self.candidates.append({'id':frame['id'],'priority':priority,'parts':[],'length':0,'truncated':False})
            if tag in self.BREAKS:
                self.add('\n')

    def handle_endtag(self, tag):
        index = next((index for index in range(len(self.stack)-1,-1,-1) if self.stack[index]['tag']==tag), None)
        if index is None:
            return
        frame = self.stack[index]
        if not frame['skip'] and tag in self.BREAKS:
            self.add('\n')
        if frame['json'] is not None:
            try:
                self.ld.append(json.loads(''.join(frame['json'])))
            except (ValueError, RecursionError):
                pass
        del self.stack[index:]

    def handle_data(self, text):
        if any(frame['tag']=='title' for frame in self.stack) and sum(map(len,self.title))<1000:
            self.title.append(text[:1000])
        if self.stack and self.stack[-1]['json'] is not None:
            parts=self.stack[-1]['json']
            if sum(map(len,parts))<200000:
                parts.append(text[:200000])
            return
        if any(frame['skip'] for frame in self.stack):
            return
        if any(frame['tag']=='h1' for frame in self.stack) and sum(map(len,self.h1))<1000:
            self.h1.append(text[:1000])
        if any(frame['author'] for frame in self.stack) and sum(map(len,self.author))<300:
            self.author.append(text[:300])
        self.add(text)

    def result(self, url: str) -> dict:
        records = []
        pending = [(value,0) for value in self.ld]
        while pending and len(records)<20:
            value,depth = pending.pop()
            if depth>12:
                continue
            if isinstance(value,list):
                pending.extend((item,depth+1) for item in value[:50])
            elif isinstance(value,dict):
                types=value.get('@type',[])
                if isinstance(types,str): types=[types]
                if any(t in ['Article','BlogPosting','NewsArticle','TechArticle'] for t in types): records.append(value)
                if '@graph' in value: pending.append((value['@graph'],depth+1))
        record=records[0] if records else {}
        author=record.get('author',{})
        authors=author if isinstance(author,list) else [author]
        author_text='、'.join(clean_text(value.get('name','') if isinstance(value,dict) else value) for value in authors[:10])
        publisher=record.get('publisher',{})
        title=clean_text(self.meta.get('og:title') or record.get('headline') or ''.join(self.h1) or ''.join(self.title))[:200]
        result={'url':url,'title':title,'author':clean_text(self.meta.get('author') or self.meta.get('article:author') or author_text or ''.join(self.author))[:200],
                'site':clean_text(self.meta.get('og:site_name') or (publisher.get('name') if isinstance(publisher,dict) else '') or source_name(url))[:100],
                'published_at':published_date(self.meta.get('article:published_time') or record.get('datePublished')),
                'description':clean_text(self.meta.get('description') or self.meta.get('og:description') or record.get('description',''))[:1000],
                'text':'','scope':'metadata','truncated':False,'message':''}
        for candidate in self.candidates:
            candidate['text']='\n'.join(line for line in (re.sub(r'[ \t\r\f\v]+',' ',line).strip() for line in ''.join(candidate['parts']).split('\n')) if line)
        choices=[candidate for candidate in self.candidates if len(candidate['text'])>=MIN_BLOG_TEXT]
        if record.get('articleBody') and isinstance(record['articleBody'],str):
            body=clean_text(record['articleBody'])
            if len(body)>=MIN_BLOG_TEXT:choices.append({'priority':5,'text':body[:MAX_BLOG_TEXT],'truncated':len(body)>MAX_BLOG_TEXT})
        if choices:
            chosen=max(choices,key=lambda candidate:(candidate['priority'],len(candidate['text'])))
            result.update(text=chosen['text'],truncated=chosen['truncated'],scope='partial_text' if chosen['truncated'] or chosen['priority']==0 else 'full_text')
        if re.search(r'just a moment|access denied|安全验证|验证中心|登录知乎|captcha',title,re.I):
            result.update(title='',text='',scope='blocked',message='来源需要登录或验证，请粘贴正文后整理。')
        elif len(result['text'])<1500 and not any(candidate['priority']>=4 for candidate in choices) and re.search(r'扫码登录|输入验证码|登录后查看|enable javascript|verify you are human',result['text'],re.I):
            result.update(text='',scope='blocked',message='来源需要登录或验证，请粘贴正文后整理。')
        elif not result['text']:
            result['message']='未读取到可总结的正文，可粘贴正文，或仅建立来源档案。'
        return result


def lookup_blog(reference: object) -> dict:
    url=blog_url(reference)
    try:
        raw,content_type,final_url=fetch_public(url)
    except ValueError as error:
        message=str(error).replace('论文','博客')
        if any(term in message for term in ['公开网络地址','HTTPS','端口','超过大小','跳转过多']):
            raise ValueError(message) from error
        code=re.search(r'HTTP (\d{3})',message)
        reason='来源拒绝读取（HTTP '+code[1]+'）' if code else '暂时无法读取来源'
        return {'url':url,'submitted_url':url,'title':'','author':'','site':source_name(url),'published_at':'','description':'','text':'','scope':'blocked','truncated':False,'message':reason+'，可补充标题并粘贴正文，或仅建立来源档案。'}
    if not any(kind in content_type.lower() for kind in ['text/html','application/xhtml+xml']):
        raise ValueError('博客链接需要指向 HTML 文章页面')
    parser=BlogHTML()
    parser.feed(raw.decode('utf-8',errors='replace'))
    result=parser.result(final_url)
    result['submitted_url']=url
    return result


def provided_blog(data: dict) -> dict:
    url=blog_url(data.get('reference',''))
    text=str(data.get('text','')).strip()
    if len(text)>60000:
        raise ValueError('粘贴的正文不能超过 60000 个字符')
    return {'url':url,'submitted_url':url,'title':clean_text(data.get('title',''))[:200],
            'author':clean_text(data.get('author',''))[:200],'site':clean_text(data.get('site','') or source_name(url))[:100],
            'published_at':published_date(data.get('published_at','')),'description':'',
            'text':text[:MAX_BLOG_TEXT],'scope':'provided_text' if text else 'metadata','truncated':len(text)>MAX_BLOG_TEXT,'message':''}


def blog_header(article: dict) -> str:
    link=quote(article['url'],safe=':/?&=%#@+~')
    lines=['## 来源信息','', '- **标题**：'+markdown_text(article['title']),
           '- **作者**：'+markdown_text(article.get('author') or '未提供'),
           '- **平台**：'+markdown_text(article.get('site') or source_name(article['url']))]
    if article.get('published_at'):lines.append('- **发布日期**：'+markdown_text(article['published_at']))
    lines += ['- **原文**：[打开来源链接]('+link+')','']
    scope=article['scope']
    note={'full_text':'摘要依据：已读取的网页正文。','partial_text':'摘要依据：已读取的部分网页正文。','provided_text':'摘要依据：你提供的正文。','metadata':'仅保存来源信息，尚未读取正文。','blocked':'来源暂不可读取，尚未生成内容摘要。'}[scope]
    if article.get('truncated'):note+=' 正文较长，本次采用前 '+str(MAX_BLOG_TEXT)+' 个字符。'
    return '\n'.join(lines+['> '+note,''])+'\n'
