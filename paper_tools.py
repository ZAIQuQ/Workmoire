"""Bounded public-paper metadata lookup; no access to private network endpoints."""
from __future__ import annotations

import http.client
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
import ipaddress
import json
import os
import re
import socket
import ssl
import time
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote, urlencode, urljoin, urlsplit
from xml.etree import ElementTree

USER_AGENT = "Workmoire/1.0 (personal paper reference manager)"
MAX_METADATA_BYTES = 2 * 1024 * 1024


def public_url(value: str) -> str:
    value = str(value).strip()
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("请提供公开的 HTTPS 论文链接")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("论文链接端口无效") from exc
    if port not in (None, 443):
        raise ValueError("论文链接只支持 HTTPS 默认端口")
    if len(value) > 3000 or any(ord(c) < 32 for c in value):
        raise ValueError("论文链接无效")
    return value


def public_addresses(host: str) -> list[str]:
    try:
        addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
    except OSError as exc:
        raise ValueError("暂时无法解析论文来源，请稍后再试") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("论文来源必须是公开网络地址")
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to an already validated address while verifying the original host."""
    def __init__(self, host: str, address: str):
        super().__init__(host, timeout=14, context=ssl.create_default_context())
        self.public_address = address

    def connect(self) -> None:
        proxy = os.environ.get("WORKSPACE_PAPER_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy", "")
        if proxy:
            endpoint = urlsplit(proxy)
            if endpoint.scheme != "http" or not endpoint.hostname or endpoint.username or endpoint.password:
                raise ValueError("论文网络代理配置无效，需要不含凭证的 HTTP CONNECT 代理")
            self.sock = socket.create_connection((endpoint.hostname, endpoint.port or 80), timeout=self.timeout)
            # Tunnel to the validated public IP, not a second DNS resolution at the proxy.
            self._tunnel_host = self.public_address
            self._tunnel_port = 443
            self._tunnel_headers = {"Host": self.host + ":443"}
            try:
                self._tunnel()
            except Exception:
                self.sock.close()
                raise
            raw = self.sock
        else:
            raw = socket.create_connection((self.public_address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def fetch_public(url: str, max_bytes: int = MAX_METADATA_BYTES) -> tuple[bytes, str, str]:
    """Validate every redirect and pin DNS, with a hard response-size bound."""
    deadline = time.monotonic() + 45
    for _ in range(5):
        if time.monotonic() >= deadline:
            raise ValueError("读取论文来源超时，请稍后再试")
        url = public_url(url)
        parsed = urlsplit(url)
        addresses = public_addresses(parsed.hostname)
        connection = PinnedHTTPSConnection(parsed.hostname, addresses[0])
        path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
        if parsed.query:
            path += "?" + quote(parsed.query, safe="%=&?/:@!$'()*+,;~-._")
        try:
            connection.request("GET", path, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity", "Accept": "application/json,text/html,application/pdf;q=0.9,*/*;q=0.5"})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise ValueError("论文来源返回了无效跳转")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError("论文来源暂不可用（HTTP %d），可尝试 DOI 或论文标题" % response.status)
            if response.getheader("Content-Encoding", "identity").lower() not in ("", "identity"):
                raise ValueError("论文来源的响应格式暂不支持")
            length = response.getheader("Content-Length")
            if length and int(length) > max_bytes:
                raise ValueError("论文来源的文件超过大小限制")
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError("读取论文来源超时，请稍后再试")
                if connection.sock is not None:
                    connection.sock.settimeout(min(14, remaining))
                part = response.read(min(65536, max_bytes + 1 - size))
                if not part:
                    break
                chunks.append(part)
                size += len(part)
                if size > max_bytes:
                    raise ValueError("论文来源的文件超过大小限制")
            return b"".join(chunks), response.getheader("Content-Type", ""), url
        except (OSError, http.client.HTTPException) as exc:
            raise ValueError("读取论文来源超时或连接失败，请稍后再试") from exc
        finally:
            connection.close()
    raise ValueError("论文链接跳转过多")


class PaperHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, list[str]] = {}
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (attrs.get("name") or attrs.get("property") or "").lower()
            value = attrs.get("content", "").strip()
            if key and value:
                self.meta.setdefault(key, []).append(value)
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data

    def first(self, *keys):
        for key in keys:
            if self.meta.get(key):
                return clean_text(self.meta[key][0])
        return ""


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]*>", " ", str(value or "")))).strip()


def doi_metadata(doi: str) -> dict:
    raw, _, _ = fetch_public("https://api.crossref.org/works/" + quote(doi, safe=""))
    return crossref_record(json.loads(raw)["message"])


def crossref_record(record: dict) -> dict:
    title = clean_text((record.get("title") or [""])[0])
    doi = str(record.get("DOI", ""))
    dates = record.get("published", record.get("issued", {})).get("date-parts", [[]])
    year = str(dates[0][0]) if dates and dates[0] else ""
    authors = [clean_text(" ".join([author.get("given", ""), author.get("family", "")])) for author in record.get("author", [])[:30]]
    source = "https://doi.org/" + quote(doi, safe="/") if doi else str(record.get("URL", ""))
    pdf = next((link.get("URL", "") for link in record.get("link", []) if link.get("content-type") == "application/pdf" and str(link.get("URL", "")).startswith("https://")), "")
    return {"title": title, "authors": authors, "year": year, "venue": clean_text((record.get("container-title") or [""])[0]), "doi": doi, "url": source, "pdf_url": pdf, "abstract": clean_text(record.get("abstract", ""))[:16000], "reference": "doi:" + doi, "provider": "Crossref"}


def lookup_papers(reference: str) -> list[dict]:
    reference = str(reference).strip()
    if not reference or len(reference) > 3000:
        raise ValueError("请输入论文标题、DOI 或公开论文链接")
    doi = reference[4:] if reference.startswith("doi:") else reference
    if re.fullmatch(r"10\.\d{4,9}/\S+", doi, re.I):
        return [doi_metadata(doi)]
    if reference.startswith(("http://", "https://")):
        reference = re.sub(r"^http://", "https://", reference)
        parsed = urlsplit(public_url(reference))
        if parsed.hostname in ("doi.org", "dx.doi.org"):
            from urllib.parse import unquote
            return [doi_metadata(unquote(parsed.path.lstrip("/")))]
        # Read the abstract page rather than downloading an arXiv PDF for metadata.
        if parsed.hostname in ("arxiv.org", "www.arxiv.org", "export.arxiv.org"):
            match = re.match(r"/(?:abs|pdf|html)/([\w.\-/]+)", parsed.path)
            if match:
                paper_id = re.sub(r"\.pdf$", "", match.group(1))
                reference = "https://arxiv.org/abs/" + paper_id
        raw, content_type, final_url = fetch_public(reference)
        if "html" not in content_type.lower():
            raise ValueError("请提供论文介绍页或 DOI；PDF 可直接在编辑器中导入")
        page = PaperHTML()
        page.feed(raw.decode("utf-8", errors="replace"))
        title = page.first("citation_title", "dc.title", "og:title")
        if not title:
            raise ValueError("这个页面没有可读取的论文元数据，请改用论文标题或 DOI")
        abstract = page.first("citation_abstract", "dc.description", "og:description", "description")
        pdf = page.first("citation_pdf_url")
        if pdf:
            pdf = urljoin(final_url, pdf)
            if not pdf.startswith("https://"):
                pdf = ""
        return [{"title": title, "authors": [clean_text(author) for author in page.meta.get("citation_author", page.meta.get("dc.creator", []))][:30], "year": page.first("citation_publication_date", "citation_date", "dc.date")[:4], "venue": page.first("citation_journal_title", "citation_conference_title"), "doi": page.first("citation_doi"), "url": final_url, "pdf_url": pdf, "abstract": abstract[:16000], "reference": final_url, "provider": "arXiv" if "arxiv.org" in urlsplit(final_url).netloc else "论文来源页"}]
    if len(reference) < 4 or len(reference) > 600:
        raise ValueError("论文标题应为 4 到 600 个字符")
    def crossref_search():
        query = urlencode({"query.bibliographic": reference, "rows": 5})
        raw, _, _ = fetch_public("https://api.crossref.org/works?" + query)
        return [crossref_record(record) for record in json.loads(raw)["message"].get("items", [])]

    def arxiv_search():
        query = urlencode({"search_query": 'ti:"' + reference.replace('"', '') + '"', "max_results": 8, "sortBy": "relevance"})
        raw, _, _ = fetch_public("https://export.arxiv.org/api/query?" + query)
        return arxiv_atom_records(raw)

    records, failures = [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [pool.submit(arxiv_search), pool.submit(crossref_search)]
        for task in tasks:
            try:
                records.extend(task.result())
            except Exception as exc:
                failures.append(exc)
    if not records and len(failures) == 2:
        raise ValueError("论文检索暂时不可用，可改用 DOI 或原文链接") from failures[0]
    normalized = lambda title: re.sub(r"[^\w]", "", title.casefold())
    needle = normalized(reference)
    unique = {}
    for record in records:
        if record.get("title") and record.get("reference"):
            unique.setdefault(normalized(record["title"]), record)
    return sorted(unique.values(), key=lambda record: SequenceMatcher(None, needle, normalized(record["title"])).ratio(), reverse=True)[:6]


def arxiv_atom_records(raw: bytes) -> list[dict]:
    namespace = {"a": "http://www.w3.org/2005/Atom", "r": "http://arxiv.org/schemas/atom"}
    root = ElementTree.fromstring(raw)
    records = []
    for entry in root.findall("a:entry", namespace):
        source = entry.findtext("a:id", "", namespace).replace("http://", "https://", 1)
        if not source.startswith("https://arxiv.org/abs/"):
            continue
        title = clean_text(entry.findtext("a:title", "", namespace))
        authors = [clean_text(author.findtext("a:name", "", namespace)) for author in entry.findall("a:author", namespace)]
        records.append({"title": title, "authors": authors[:30], "year": entry.findtext("a:published", "", namespace)[:4], "venue": "arXiv", "doi": clean_text(entry.findtext("r:doi", "", namespace)), "url": source, "pdf_url": source.replace("/abs/", "/pdf/"), "abstract": clean_text(entry.findtext("a:summary", "", namespace))[:16000], "reference": source, "provider": "arXiv"})
    return records


def markdown_text(value: object) -> str:
    return re.sub(r"([\\`*_[\]<>])", r"\\\1", clean_text(value))


def dossier_header(paper: dict) -> str:
    lines = ["## 论文信息", "", "- **标题**：" + markdown_text(paper["title"])]
    if paper.get("authors"):
        lines.append("- **作者**：" + markdown_text("; ".join(paper["authors"])))
    if paper.get("year"):
        lines.append("- **年份**：" + markdown_text(paper["year"]))
    if paper.get("venue"):
        lines.append("- **期刊 / 会议**：" + markdown_text(paper["venue"]))
    lines += ["- **来源**：[原文页面](" + paper["url"] + ")", "", "> 根据公开元数据" + ("和摘要" if paper.get("abstract") else "") + "整理；尚未阅读全文，具体结论与实验需对照原文核实。", ""]
    if paper.get("abstract"):
        lines += ["## 原文摘要", "", markdown_text(paper["abstract"]), ""]
    if paper.get("pdf_url"):
        lines += ["## 原文 PDF", "", "@[pdf](" + paper["pdf_url"] + ")", ""]
    return "\n".join(lines)
