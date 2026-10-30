"""Publish immutable share snapshots; the public reader needs no workspace access."""
from __future__ import annotations

import base64
from contextlib import contextmanager, closing
import copy
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import tarfile
import tempfile
import threading
import time
from urllib.parse import urlsplit

from rich_documents import read_rich_content, pdf_fragment

DURATIONS = {1, 7, 30, 0}
TOKEN_RE = re.compile(r'^[A-Za-z0-9_-]{43}$')
FILE_RE = re.compile(r'^/files/([a-f0-9]{32})(?:\?inline=1)?$')
PUBLISH_LOCK = threading.RLock()
MAX_MEDIA = 256
MAX_MEDIA_BYTES = 64 * 1024 * 1024
PASSWORD_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'


def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def requires_password(row) -> bool:
    # Old databases and unknown values remain protected during rolling upgrades.
    return 'password_required' not in row.keys() or row['password_required'] != 0


def new_password_nonce() -> str:
    # Existing unprefixed nonces retain their original password derivation.
    return 'v2:' + secrets.token_urlsafe(32)


def alphanumeric_password(key: bytes, nonce: str) -> str:
    counter = 0
    while True:
        digest = hmac.new(key, f'password-v2:{nonce}:{counter}'.encode(), hashlib.sha256).digest()
        # Reject the eight excess byte values instead of biasing modulo 62.
        candidate = ''.join(PASSWORD_ALPHABET[byte % 62] for byte in digest if byte < 248)[:16]
        if len(candidate) == 16 and all(any(check(char) for char in candidate) for check in (str.isupper, str.islower, str.isdigit)):
            return candidate
        counter += 1


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, dklen=32, maxmem=64*1024*1024)
    return b64(salt) + '.' + b64(digest)


def password_matches(password: str, encoded: str) -> bool:
    if not isinstance(password, str) or not 1 <= len(password) <= 128:
        return False
    try:
        salt, expected = [base64.urlsafe_b64decode(part + '='*(-len(part)%4)) for part in encoded.split('.')]
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, dklen=32, maxmem=64*1024*1024)
        return hmac.compare_digest(expected, actual)
    except (ValueError, TypeError):
        return False


def media_type(header: bytes) -> str:
    if header.startswith(b'%PDF-'): return 'application/pdf'
    if header.startswith(b'\x89PNG\r\n\x1a\n'): return 'image/png'
    if header.startswith(b'\xff\xd8\xff'): return 'image/jpeg'
    if header.startswith((b'GIF87a', b'GIF89a')): return 'image/gif'
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP': return 'image/webp'
    return 'application/octet-stream'


def publication_connection(root: Path, writable=False):
    path = root/'published.db'
    con = sqlite3.connect(path if writable else path.as_uri()+'?mode=ro', uri=not writable, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con


class SharePublisher:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o2750)
        os.chmod(self.root, 0o2750)
        with PUBLISH_LOCK, (self.root/'publisher.lock').open('a+b') as lock:
            os.chmod(self.root/'publisher.lock', 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def initialize(self):
        with self.locked():
            (self.root/'media').mkdir(exist_ok=True, mode=0o2750)
            os.chmod(self.root/'media', 0o2750)
            key = self.root/'publisher.key'
            if not key.exists():
                fd = os.open(key, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as stream: stream.write(secrets.token_bytes(32))
            if len(key.read_bytes()) != 32: raise RuntimeError('分享服务密钥无效')
            os.chmod(key, 0o600)
            with closing(publication_connection(self.root, True)) as con, con:
                con.execute('PRAGMA journal_mode=DELETE')
                con.executescript('''
                CREATE TABLE IF NOT EXISTS shares(
                    id TEXT PRIMARY KEY, owner_item_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE, link_nonce TEXT NOT NULL,
                    password_nonce TEXT NOT NULL, password_hash TEXT NOT NULL,
                    key_id TEXT NOT NULL, title TEXT NOT NULL, document TEXT NOT NULL,
                    source_updated_at TEXT NOT NULL, created_at INTEGER NOT NULL,
                    days INTEGER NOT NULL, expires_at INTEGER, revoked_at INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL DEFAULT 1,
                    password_required INTEGER NOT NULL DEFAULT 1 CHECK(password_required IN (0,1))
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_live_share ON shares(owner_item_id) WHERE revoked_at=0;
                CREATE TABLE IF NOT EXISTS share_files(
                    share_id TEXT NOT NULL REFERENCES shares(id) ON DELETE CASCADE,
                    alias TEXT NOT NULL, blob TEXT NOT NULL, name TEXT NOT NULL,
                    content_type TEXT NOT NULL, size INTEGER NOT NULL,
                    PRIMARY KEY(share_id,alias)
                );
                CREATE INDEX IF NOT EXISTS idx_share_blob ON share_files(blob);
                ''')
                if 'password_required' not in {row['name'] for row in con.execute('PRAGMA table_info(shares)')}:
                    con.execute('ALTER TABLE shares ADD COLUMN password_required INTEGER NOT NULL DEFAULT 1 CHECK(password_required IN (0,1))')
            os.chmod(self.root/'published.db', 0o640)

    def credentials(self, row) -> tuple[str, str]:
        key = (self.root/'publisher.key').read_bytes()
        if token_hash(b64(key)) != row['key_id']:
            raise ValueError('分享密钥已变化，请重新生成分享链接')
        token = b64(hmac.new(key, ('link-v1:'+row['link_nonce']).encode(), hashlib.sha256).digest())
        if row['password_nonce'].startswith('v2:'):
            return token, alphanumeric_password(key, row['password_nonce'])
        if ':' in row['password_nonce']:
            raise ValueError('分享密码格式不受此版本支持')
        digest = hmac.new(key, ('password-v1:'+row['password_nonce']).encode(), hashlib.sha256).digest()
        password = ('ABCDEFGHJKLMNPQRSTUVWXYZ'[digest[0]%24] + 'abcdefghjkmnpqrstuvwxyz'[digest[1]%22]
                    + '23456789'[digest[2]%8] + '!@#$%&*_-+'[digest[3]%10] + b64(digest[4:])[:24])
        return token, password

    def owner_view(self, row) -> dict:
        token, password = self.credentials(row)
        protected = requires_password(row)
        return {'id':row['id'], 'path':'/s/'+token, 'password':password if protected else None, 'password_required':protected,
                'title':row['title'], 'created_at':row['created_at'], 'source_updated_at':row['source_updated_at'],
                'days':row['days'], 'expires_at':row['expires_at'], 'revision':row['revision'],
                'active':not row['revoked_at'] and (row['expires_at'] is None or row['expires_at'] > time.time())}

    def latest(self, item_id: int):
        self.initialize()
        with closing(publication_connection(self.root)) as con:
            row = con.execute('SELECT * FROM shares WHERE owner_item_id=? AND revoked_at=0', (item_id,)).fetchone()
        return self.owner_view(row) if row else None

    def _copy_file(self, file: dict, files_dir: Path) -> dict:
        source = (files_dir/file['stored_name']).resolve()
        source.relative_to(files_dir.resolve())
        if not source.is_file() or source.stat().st_size > MAX_MEDIA_BYTES:
            raise ValueError('分享中的附件不可用或超过大小限制')
        digest = hashlib.sha256(); size = 0; header = b''
        fd, temporary = tempfile.mkstemp(prefix='.copy-', dir=self.root/'media')
        try:
            with os.fdopen(fd, 'wb') as target, source.open('rb') as stream:
                while part := stream.read(65536):
                    if not header: header = part[:32]
                    size += len(part)
                    if size > MAX_MEDIA_BYTES: raise ValueError('分享中的附件超过大小限制')
                    digest.update(part); target.write(part)
            blob = digest.hexdigest(); destination = self.root/'media'/blob
            os.chmod(temporary, 0o640); os.replace(temporary, destination)
            return {'blob':blob, 'name':file['name'], 'content_type':media_type(header), 'size':size}
        finally:
            Path(temporary).unlink(missing_ok=True)

    def _collect_blobs(self, con):
        used = {row[0] for row in con.execute('SELECT DISTINCT blob FROM share_files')}
        for path in (self.root/'media').iterdir():
            if re.fullmatch(r'[a-f0-9]{64}', path.name) and path.name not in used: path.unlink(missing_ok=True)

    def publish(self, item: dict, file_rows: dict, files_dir: Path, days: int, owner_origin: str='', password_required: bool=True) -> dict:
        if type(days) is not int or days not in DURATIONS: raise ValueError('请选择 1 天、7 天、30 天或永久')
        if type(password_required) is not bool: raise ValueError('密码保护设置无效')
        rich = read_rich_content(item.get('rich_content'), item['content'])
        if not rich: raise ValueError('请先在编辑器保存文档，再生成分享链接')
        self.initialize()
        with self.locked(), closing(publication_connection(self.root, True)) as con:
            now = int(time.time()); key = (self.root/'publisher.key').read_bytes()
            record = {'id':secrets.token_hex(16), 'owner_item_id':item['id'], 'link_nonce':secrets.token_urlsafe(32),
                      'password_nonce':new_password_nonce(), 'key_id':token_hash(b64(key))}
            token, password = self.credentials(record)
            assets = {}; copied = {}
            def local_id(value):
                parsed = urlsplit(str(value or ''))
                if parsed.netloc and parsed.netloc != urlsplit(owner_origin).netloc: return None
                match = re.fullmatch(r'/files/([a-f0-9]{32})', parsed.path)
                return match[1] if match else None
            def link(value, media=False):
                file_id = local_id(value)
                if file_id:
                    if file_id not in file_rows: return None
                    if file_id not in assets:
                        if len(assets) >= MAX_MEDIA: raise ValueError('单个分享最多包含 256 个附件')
                        assets[file_id] = secrets.token_hex(16)
                        copied[file_id] = self._copy_file(file_rows[file_id], files_dir)
                    fragment=urlsplit(str(value)).fragment
                    page='#'+fragment if not media and pdf_fragment(fragment) else ''
                    return 'share-file:'+assets[file_id]+page
                parsed = urlsplit(str(value or ''))
                if parsed.netloc and parsed.netloc == urlsplit(owner_origin).netloc: return None
                if parsed.scheme in ({'https'} if media else {'https','http','mailto'}) and not parsed.username and not parsed.password:
                    return value
                if not media and str(value).startswith('#'): return value
                return None
            def sanitize(node):
                if node['type'] == 'documentLink': return {'type':'text','text':node.get('attrs',{}).get('title') or '关联文档'}
                if node['type'] in {'image','pdf'}:
                    src = link(node.get('attrs',{}).get('src'), True)
                    if not src: return {'type':'paragraph','content':[{'type':'text','text':'附件未包含在此分享中'}]}
                    if node['type']=='pdf' and not src.startswith('share-file:'):
                        return {'type':'paragraph','content':[{'type':'text','text':'打开 PDF 来源','marks':[{'type':'link','attrs':{'href':src,'target':'_blank','rel':'noopener noreferrer'}}]}]}
                    node['attrs']['src'] = src
                marks=[]
                for mark in node.get('marks',[]):
                    if mark['type']=='link':
                        href=link(mark.get('attrs',{}).get('href'))
                        if not href: continue
                        mark['attrs']={'href':href,'target':'_blank','rel':'noopener noreferrer'}
                    marks.append(mark)
                if 'marks' in node: node['marks']=marks
                if node['type']=='codeBlock':
                    for child in node.get('content',[]): child.pop('marks',None)
                elif 'content' in node: node['content']=[sanitize(child) for child in node['content']]
                return node
            try:
                document = json.dumps(sanitize(copy.deepcopy(rich['document'])), ensure_ascii=False, separators=(',',':'))
                with con:
                    old = [row[0] for row in con.execute('SELECT id FROM shares WHERE owner_item_id=? AND revoked_at=0',(item['id'],))]
                    for share_id in old:
                        con.execute("UPDATE shares SET revoked_at=?,document='',version=version+1,revision=revision+1 WHERE id=?",(now,share_id))
                        con.execute('DELETE FROM share_files WHERE share_id=?',(share_id,))
                    con.execute('INSERT INTO shares(id,owner_item_id,token_hash,link_nonce,password_nonce,password_hash,key_id,title,document,source_updated_at,created_at,days,expires_at,password_required) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                (record['id'],item['id'],token_hash(token),record['link_nonce'],record['password_nonce'],password_hash(password),record['key_id'],item['title'],document,item['updated_at'],now,days,now+days*86400 if days else None,password_required))
                    for file_id,alias in assets.items():
                        f=copied[file_id];con.execute('INSERT INTO share_files VALUES(?,?,?,?,?,?)',(record['id'],alias,f['blob'],f['name'],f['content_type'],f['size']))
                self._collect_blobs(con)
                return self.owner_view(con.execute('SELECT * FROM shares WHERE id=?',(record['id'],)).fetchone())
            except Exception:
                con.rollback();self._collect_blobs(con);raise

    def change(self, item_id: int, share_id: str, revision: int, action: str, days=None, password_required=None):
        self.initialize()
        with self.locked(), closing(publication_connection(self.root, True)) as con, con:
            row=con.execute('SELECT * FROM shares WHERE id=? AND owner_item_id=? AND revoked_at=0',(share_id,item_id)).fetchone()
            if not row or row['revision'] != revision: raise ValueError('分享状态已变化，请重新打开分享面板')
            if action=='expiry':
                if type(days) is not int or days not in DURATIONS: raise ValueError('分享有效期无效')
                con.execute('UPDATE shares SET days=?,expires_at=?,revision=revision+1 WHERE id=?',(days,int(time.time())+days*86400 if days else None,share_id))
            elif action=='password':
                if not requires_password(row): raise ValueError('请先开启密码保护')
                updated=dict(row);updated['password_nonce']=new_password_nonce()
                _,password=self.credentials(updated)
                con.execute('UPDATE shares SET password_nonce=?,password_hash=?,version=version+1,revision=revision+1 WHERE id=?',(updated['password_nonce'],password_hash(password),share_id))
            elif action=='protection':
                if type(password_required) is not bool: raise ValueError('密码保护设置无效')
                if password_required != requires_password(row):
                    updated=dict(row)
                    if password_required:
                        updated['password_nonce']=new_password_nonce()
                        _,password=self.credentials(updated)
                        updated['password_hash']=password_hash(password)
                    con.execute('UPDATE shares SET password_required=?,password_nonce=?,password_hash=?,version=version+1,revision=revision+1 WHERE id=?',
                                (password_required,updated['password_nonce'],updated['password_hash'],share_id))
            elif action=='revoke':
                con.execute("UPDATE shares SET revoked_at=?,document='',version=version+1,revision=revision+1 WHERE id=?",(int(time.time()),share_id))
                con.execute('DELETE FROM share_files WHERE share_id=?',(share_id,));con.commit();self._collect_blobs(con);return None
            else: raise ValueError('分享操作无效')
            return self.owner_view(con.execute('SELECT * FROM shares WHERE id=?',(share_id,)).fetchone())

    def revoke_items(self, item_ids):
        if not (self.root/'published.db').exists(): return
        with self.locked(), closing(publication_connection(self.root, True)) as con, con:
            for item_id in item_ids:
                for row in con.execute('SELECT id FROM shares WHERE owner_item_id=? AND revoked_at=0',(item_id,)).fetchall():
                    con.execute("UPDATE shares SET revoked_at=?,document='',version=version+1,revision=revision+1 WHERE id=?",(int(time.time()),row['id']))
                    con.execute('DELETE FROM share_files WHERE share_id=?',(row['id'],))
            con.commit();self._collect_blobs(con)


def active_share(root: Path, token: str):
    if not TOKEN_RE.fullmatch(token): return None
    with closing(publication_connection(root)) as con:
        row=con.execute('SELECT * FROM shares WHERE token_hash=? AND revoked_at=0 AND (expires_at IS NULL OR expires_at>?)',(token_hash(token),int(time.time()))).fetchone()
    return row


def backup_publications(root: Path, target: Path):
    """Archive a consistent publication set and key, excluding reader sessions."""
    publisher=SharePublisher(root)
    if not (publisher.root/'published.db').is_file():
        raise ValueError('Sharing database is not initialized')
    with publisher.locked(), tempfile.TemporaryDirectory(prefix='workmoire-share-backup-') as temporary:
        snapshot=Path(temporary)/'published.db'
        with closing(publication_connection(publisher.root)) as source, closing(sqlite3.connect(snapshot)) as destination:
            source.backup(destination)
            if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('Sharing snapshot integrity check failed')
        with tarfile.open(target,'w:gz') as archive:
            archive.add(snapshot,arcname='published.db')
            archive.add(publisher.root/'publisher.key',arcname='publisher.key')
            archive.add(publisher.root/'media',arcname='media')
        os.chmod(target,0o600)
        with tarfile.open(target,'r:gz') as archive:
            for entry in archive:
                if entry.isfile():
                    with archive.extractfile(entry) as stream:
                        while stream.read(1024*1024): pass


def shared_document(row, token: str) -> dict:
    document=json.loads(row['document'])
    def rewrite(value):
        if isinstance(value,dict):
            result={}
            for key,child in value.items():
                match=re.fullmatch(r'share-file:([a-f0-9]{32})(?:#(.+))?',child) if key in {'src','href'} and isinstance(child,str) else None
                result[key]='/s/'+token+'/files/'+match[1]+'?inline=1'+('#'+match[2] if match[2] and pdf_fragment(match[2]) else '') if match else rewrite(child)
            return result
        if isinstance(value,list): return [rewrite(child) for child in value]
        return value
    return {'title':row['title'],'rich_content':{'version':1,'document':rewrite(document)},'created_at':row['created_at'],'expires_at':row['expires_at']}
