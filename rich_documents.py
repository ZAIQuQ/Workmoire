"""Validated, versioned rich documents alongside the portable Markdown body."""
from __future__ import annotations

import json
import hashlib
import re
from urllib.parse import urlsplit

MAX_RICH_BYTES = 2 * 1024 * 1024
MAX_RICH_NODES = 30000
BLOCKS = {'paragraph', 'heading', 'blockquote', 'codeBlock', 'bulletList', 'orderedList', 'taskList', 'table', 'horizontalRule', 'image', 'blockMath', 'pdf'}
INLINE = {'text', 'hardBreak', 'inlineMath', 'documentLink'}
CHILDREN = {
    'doc': BLOCKS, 'paragraph': INLINE, 'heading': INLINE, 'blockquote': BLOCKS,
    'codeBlock': {'text'}, 'bulletList': {'listItem'}, 'orderedList': {'listItem'},
    'taskList': {'taskItem'}, 'listItem': BLOCKS, 'taskItem': BLOCKS,
    'table': {'tableRow'}, 'tableRow': {'tableCell', 'tableHeader'},
    'tableCell': BLOCKS, 'tableHeader': BLOCKS,
}
NODES = set(CHILDREN) | INLINE | BLOCKS
MARKS = {'bold', 'italic', 'strike', 'underline', 'code', 'link', 'highlight', 'textStyle', 'subscript', 'superscript'}


def safe_url(value: object, media: bool = False) -> str:
    if not isinstance(value, str) or len(value) > 3000 or re.search(r'[\x00-\x20\x7f]', value):
        raise ValueError('文档链接格式无效')
    if re.fullmatch(r'/files/[a-f0-9]{32}(?:\?inline=1)?', value):
        return value
    if not media and re.fullmatch(r'/files/[a-f0-9]{32}(?:\?inline=1)?#page=([1-9][0-9]{0,4})', value):
        if int(value.rsplit('=',1)[1]) <= 10000:
            return value
    if not media and re.fullmatch(r'#[\w-]+', value):
        return value
    parsed = urlsplit(value)
    if parsed.username or parsed.password:
        raise ValueError('文档链接不能包含凭证')
    if parsed.scheme == 'https' and parsed.hostname:
        return value
    if not media and ((parsed.scheme == 'http' and parsed.hostname) or (parsed.scheme == 'mailto' and '@' in parsed.path)):
        return value
    raise ValueError('文档包含不支持的链接协议')


def normalized_rich_content(value: object, markdown: str | None = None) -> str:
    """Return canonical storage text. Empty text denotes a legacy Markdown item."""
    if value is None or value == '':
        return ''
    if isinstance(value, str):
        if len(value.encode('utf-8')) > MAX_RICH_BYTES:
            raise ValueError('富文本文档超过 2 MB')
        try:
            value = json.loads(value)
        except (ValueError, RecursionError) as exc:
            raise ValueError('富文本文档格式无效') from exc
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        raise ValueError('不支持的富文本文档版本')
    document = value.get('document')
    if not isinstance(document, dict) or document.get('type') != 'doc':
        raise ValueError('富文本文档缺少正文')
    count = 0
    text_length = 0

    def attrs_for(kind: str, raw: object) -> dict:
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ValueError('文档属性格式无效')
        attrs = {}
        if kind == 'doc' and raw.get('bodyFont') is not None:
            if raw['bodyFont'] not in ('sans', 'serif', 'mono'):
                raise ValueError('正文字体无效')
            attrs['bodyFont'] = raw['bodyFont']
        if kind in {'paragraph', 'heading'} and raw.get('textAlign') is not None:
            if not isinstance(raw['textAlign'], str) or raw['textAlign'] not in {'left', 'center', 'right', 'justify'}:
                raise ValueError('段落对齐方式无效')
            attrs['textAlign'] = raw['textAlign']
        if kind in {'paragraph','heading'} and 'blockIndent' in raw:
            if type(raw['blockIndent']) is not int or not 0 <= raw['blockIndent'] <= 8:
                raise ValueError('段落缩进级别无效')
            attrs['blockIndent'] = raw['blockIndent']
        if kind == 'heading':
            if type(raw.get('level')) is not int or not 1 <= raw['level'] <= 6:
                raise ValueError('标题级别无效')
            attrs['level'] = raw['level']
        if kind == 'codeBlock':
            language = raw.get('language')
            if language is not None and (not isinstance(language, str) or not re.fullmatch(r'[\w+#.-]{0,40}', language)):
                raise ValueError('代码语言无效')
            attrs['language'] = language
            if type(raw.get('collapsed', False)) is not bool:
                raise ValueError('代码折叠状态无效')
            attrs['collapsed'] = raw.get('collapsed', False)
        if kind == 'table' and 'fixedWidth' in raw:
            if type(raw['fixedWidth']) is not bool:
                raise ValueError('表格固定宽度设置无效')
            attrs['fixedWidth'] = raw['fixedWidth']
        if kind == 'orderedList':
            start = raw.get('start', 1)
            if type(start) is not int or not 1 <= start <= 100000:
                raise ValueError('列表序号无效')
            attrs['start'] = start
        if kind == 'taskItem':
            if type(raw.get('checked', False)) is not bool:
                raise ValueError('待办状态无效')
            attrs['checked'] = raw.get('checked', False)
        if kind in {'tableCell', 'tableHeader'}:
            for key in ['colspan', 'rowspan']:
                number = raw.get(key, 1)
                if type(number) is not int or not 1 <= number <= 100:
                    raise ValueError('表格尺寸无效')
                attrs[key] = number
            widths = raw.get('colwidth')
            if widths is not None and (not isinstance(widths, list) or len(widths) > 100 or any(type(n) is not int or not (n == 0 or 25 <= n <= 5000) for n in widths)):
                raise ValueError('表格列宽无效')
            attrs['colwidth'] = widths
        if kind in {'image', 'pdf'}:
            attrs['src'] = safe_url(raw.get('src'), media=True)
            for key in ['alt', 'title'] if kind == 'image' else ['title']:
                if raw.get(key) is not None:
                    if not isinstance(raw[key], str) or len(raw[key]) > 500:
                        raise ValueError('附件说明无效')
                    attrs[key] = raw[key]
            if kind == 'image':
                for key in ['width', 'height']:
                    if raw.get(key) is not None:
                        number = raw[key]
                        if type(number) not in {int, float} or not 16 <= number <= 8000:
                            raise ValueError('图片尺寸无效')
                        attrs[key] = number
        if kind in {'inlineMath', 'blockMath'}:
            latex = raw.get('latex', '')
            if not isinstance(latex, str) or len(latex) > 10000:
                raise ValueError('公式过长或格式无效')
            attrs['latex'] = latex
        if kind == 'documentLink':
            if type(raw.get('id')) is not int or raw['id'] < 1:
                raise ValueError('文档引用无效')
            title = raw.get('title', '')
            if not isinstance(title, str) or len(title) > 200:
                raise ValueError('文档引用标题无效')
            attrs.update(id=raw['id'], title=title)
        if kind == 'link':
            attrs['href'] = safe_url(raw.get('href'))
            attrs.update(target='_blank', rel='noopener noreferrer nofollow')
            if raw.get('title') is not None:
                if not isinstance(raw['title'], str) or len(raw['title']) > 500:
                    raise ValueError('链接标题无效')
                attrs['title'] = raw['title']
        if kind in {'highlight', 'textStyle'} and raw.get('color') is not None:
            color = raw['color']
            if not isinstance(color, str) or len(color) > 60:
                raise ValueError('文字颜色无效')
            rgb = re.fullmatch(r'rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)', color)
            if not (re.fullmatch(r'#[a-fA-F0-9]{3}(?:[a-fA-F0-9]{3})?', color) or rgb and all(int(n) <= 255 for n in rgb.groups()) or color in {'black','white','red','green','blue','yellow','gray','grey','orange','purple','pink','brown','teal','navy','maroon','olive'}):
                raise ValueError('文字颜色无效')
            attrs['color'] = color
        return attrs

    def node(raw: object, depth: int = 0) -> dict:
        nonlocal count, text_length
        count += 1
        if depth > 60 or count > MAX_RICH_NODES or not isinstance(raw, dict):
            raise ValueError('文档结构过深或块数量过多')
        kind = raw.get('type')
        if not isinstance(kind, str) or kind not in NODES:
            raise ValueError('文档包含不支持的内容块')
        result = {'type': kind}
        if kind == 'text':
            text = raw.get('text')
            if not isinstance(text, str) or not text:
                raise ValueError('文字节点无效')
            text_length += len(text)
            if text_length > 1024 * 1024:
                raise ValueError('文档文字超过 1 MB')
            result['text'] = text
        attrs = attrs_for(kind, raw.get('attrs'))
        if attrs:
            result['attrs'] = attrs
        children = raw.get('content', [])
        if not isinstance(children, list) or (children and kind not in CHILDREN):
            raise ValueError('内容块结构无效')
        if children:
            result['content'] = []
            for child in children:
                if not isinstance(child, dict) or not isinstance(child.get('type'), str) or child.get('type') not in CHILDREN[kind]:
                    raise ValueError('内容块嵌套无效')
                result['content'].append(node(child, depth + 1))
        if kind == 'doc' and not children:
            result['content'] = [{'type': 'paragraph'}]
        if kind in {'listItem', 'taskItem'} and (not children or children[0].get('type') != 'paragraph'):
            raise ValueError('列表项需要以段落开头')
        if kind in {'table', 'tableRow', 'tableCell', 'tableHeader', 'listItem', 'taskItem'} and not children:
            raise ValueError('表格或列表项不能为空')
        marks = raw.get('marks', [])
        if not isinstance(marks, list) or len(marks) > 16 or (marks and kind not in INLINE):
            raise ValueError('文字样式格式无效')
        if marks:
            result['marks'] = []
            for mark in marks:
                if not isinstance(mark, dict) or not isinstance(mark.get('type'), str) or mark.get('type') not in MARKS:
                    raise ValueError('文档包含不支持的文字样式')
                entry = {'type': mark['type']}
                attributes = attrs_for(mark['type'], mark.get('attrs'))
                if attributes:
                    entry['attrs'] = attributes
                result['marks'].append(entry)
        return result

    try:
        payload = {'version': 1, 'document': node(document)}
        if markdown is not None:
            payload['markdown_hash'] = hashlib.sha256(markdown.encode('utf-8')).hexdigest()
        result = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    except RecursionError as exc:
        raise ValueError('文档结构过深') from exc
    if len(result.encode('utf-8')) > MAX_RICH_BYTES:
        raise ValueError('富文本文档超过 2 MB')
    return result


def remap_references(content: str, rich: str, item_ids: dict, file_ids: dict | None = None) -> tuple[str, str]:
    """Keep imported references local to the newly imported documents and files."""
    file_ids = file_ids or {}
    def files(value: str) -> str:
        return re.sub(r'(/files/)([a-f0-9]{32})(?![a-f0-9])', lambda m: m[1] + file_ids.get(m[2], m[2]), value)
    content = files(re.sub(r'\[\[(\d+)\|', lambda m: '[[' + str(item_ids.get(m[1], m[1])) + '|', content))
    if rich:
        document = json.loads(rich)
        def visit(value):
            if isinstance(value, dict):
                if value.get('type') == 'documentLink':
                    attrs = value.get('attrs', {})
                    attrs['id'] = item_ids.get(str(attrs.get('id')), attrs.get('id'))
                for key, child in value.items():
                    if key in {'src', 'href'} and isinstance(child, str):
                        value[key] = files(child)
                    else:
                        visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(document)
        document['markdown_hash'] = hashlib.sha256(content.encode('utf-8')).hexdigest()
        rich = json.dumps(document, ensure_ascii=False, separators=(',', ':'))
    return content, rich


def read_rich_content(value: str, markdown: str) -> dict | None:
    """An older server may edit Markdown without updating the native document."""
    if not value:
        return None
    try:
        native = json.loads(value)
        if native.get('version') == 1 and native.get('markdown_hash') == hashlib.sha256(markdown.encode('utf-8')).hexdigest():
            return native
    except (ValueError, AttributeError):
        pass
    return None
