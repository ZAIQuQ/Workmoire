#!/usr/bin/env python3
"""Independent read-only HTTP surface for optionally protected snapshots."""
from __future__ import annotations

from contextlib import closing
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import quote, urlsplit, unquote

from share_store import active_share, password_matches, publication_connection, shared_document, token_hash, requires_password

SESSION_SECONDS = 12 * 3600
STATIC_EXACT = {'share.html','share.css','design-tokens.css','app.css','rich-editor.css','code-block.css','pdf-viewer.css','favicon.svg',
                'vendor/share-reader.js','vendor/share-icons.js','vendor/editor.js','vendor/type.css','vendor/katex.min.css','vendor/pdf-reader.mjs','vendor/pdf.worker.min.mjs','vendor/pdf-viewer.css'}
STATIC_FONTS = ('vendor/type/','vendor/fonts/','fonts/maple-mono/','vendor/pdf-cmaps/','vendor/pdf-fonts/','vendor/pdf-wasm/','vendor/images/')


class ShareAuth:
    def __init__(self, root: Path):
        root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path=root/'auth.db';self.lock=threading.Lock();self.kdf=threading.BoundedSemaphore(2)
        with closing(self.connect()) as con,con:
            con.executescript('''CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY,started INTEGER NOT NULL,count INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,share_id TEXT NOT NULL,version INTEGER NOT NULL,expires_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_share_session_expiry ON sessions(expires_at);''')
        os.chmod(self.path,0o600)

    def connect(self):
        con=sqlite3.connect(self.path,timeout=5);con.row_factory=sqlite3.Row;return con

    def reserve(self, ip: str, token: str):
        address=ipaddress.ip_address(ip)
        if address.version==6:ip=str(ipaddress.ip_network(str(address)+'/64',strict=False))
        keys=[('ip:'+token_hash(ip),5,600,True),('link:'+token_hash(token),30,600,True),('traffic:'+token_hash(ip),60,60,False),('global',120,60,False)]
        now=int(time.time());reservation=[]
        with self.lock,closing(self.connect()) as con,con:
            con.execute('BEGIN IMMEDIATE');con.execute('DELETE FROM attempts WHERE started<?',(now-1200,));con.execute('DELETE FROM sessions WHERE expires_at<=?',(now,))
            for key,limit,window,releasable in keys:
                row=con.execute('SELECT * FROM attempts WHERE key=?',(key,)).fetchone()
                if row and row['started']+window>now and row['count']>=limit:
                    return None,max(1,row['started']+window-now)
            for key,limit,window,releasable in keys:
                row=con.execute('SELECT * FROM attempts WHERE key=?',(key,)).fetchone()
                started=row['started'] if row and row['started']+window>now else now
                count=row['count']+1 if row and started==row['started'] else 1
                con.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)',(key,started,count));reservation.append((key,started,releasable))
        return reservation,0

    def success(self, reservation, share):
        session=secrets.token_urlsafe(32);expires=min(int(time.time())+SESSION_SECONDS,share['expires_at'] or 2**62)
        with self.lock,closing(self.connect()) as con,con:
            for key,started,releasable in reservation:
                if not releasable: continue
                con.execute('UPDATE attempts SET count=max(0,count-1) WHERE key=? AND started=?',(key,started))
            con.execute('INSERT INTO sessions VALUES(?,?,?,?)',(token_hash(session),share['id'],share['version'],expires))
        return session,expires

    def access(self, session: str, share):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',session or ''):return None
        with closing(self.connect()) as con:
            row=con.execute('SELECT expires_at FROM sessions WHERE hash=? AND share_id=? AND version=? AND expires_at>?',(token_hash(session),share['id'],share['version'],int(time.time()))).fetchone()
        return row['expires_at'] if row else None


class ShareHTTPServer(ThreadingHTTPServer):
    daemon_threads=True;request_queue_size=32
    def __init__(self,address,root:Path,static:Path,auth_dir:Path,secure=False,public_origin=''):
        self.share_root=root.resolve();self.static_root=static.resolve();self.auth=ShareAuth(auth_dir);self.secure=secure;self.public_origin=public_origin.rstrip('/');self.slots=threading.BoundedSemaphore(16)
        super().__init__(address,ShareHandler)
    def get_request(self):
        request,address=super().get_request();request.settimeout(15);return request,address
    def process_request(self,request,client_address):
        if not self.slots.acquire(blocking=False):
            try:request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n')
            except OSError:pass
            self.shutdown_request(request);return
        try:super().process_request(request,client_address)
        except Exception:self.slots.release();raise
    def process_request_thread(self,request,client_address):
        try:super().process_request_thread(request,client_address)
        finally:self.slots.release()
    def handle_error(self,request,client_address):
        # Never emit a URL token, cookie, document body or password in logs.
        print('share connection error',flush=True)


class ShareHandler(BaseHTTPRequestHandler):
    server_version='WorkmoireShare/1.0'
    def log_message(self,fmt,*args):
        status=str(args[1]) if len(args)>1 else '-';print('share request '+self.command+' '+status,flush=True)
    def respond(self,body,status=200,content_type='application/json; charset=utf-8',extra=(),frame=False,head=False):
        if isinstance(body,dict):body=json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)))
        self.security_headers(frame)
        for key,value in extra:self.send_header(key,value)
        self.end_headers()
        if not head:self.wfile.write(body)
    def security_headers(self,frame=False):
        for key,value in [('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer'),('X-Robots-Tag','noindex, nofollow, noarchive'),('X-Frame-Options','SAMEORIGIN' if frame else 'DENY'),('Cross-Origin-Resource-Policy','same-origin'),('Permissions-Policy','camera=(), microphone=(), geolocation=()'),('Content-Security-Policy',"default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: https:; connect-src 'self'; worker-src 'self'; frame-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors "+("'self'" if frame else "'none'"))]:self.send_header(key,value)
    def fail(self,status=404,message='分享不存在、已到期或已停止',extra=(),head=False):
        self.respond({'error':message},status,extra=extra,head=head)
    def grant(self,share):
        cookies=SimpleCookie()
        try:cookies.load(self.headers.get('Cookie',''))
        except Exception:return None
        return self.server.auth.access(cookies['workmoire_share'].value if cookies.get('workmoire_share') else '',share)
    def do_GET(self):self.get(False)
    def do_HEAD(self):self.get(True)
    def get(self,head):
        try:
            path=urlsplit(self.path).path
            if path=='/healthz':
                with closing(publication_connection(self.server.share_root)) as con:con.execute('SELECT 1 FROM shares LIMIT 1').fetchone()
                self.respond({'ok':True,'service':'sharing'},head=head);return
            if path.startswith('/static/'):
                self.static(unquote(path[8:]),head);return
            match=re.fullmatch(r'/s/([A-Za-z0-9_-]{43})(?:/(document|files/([a-f0-9]{32})))?/?',path)
            if not match:self.fail(head=head);return
            token,action,alias=match.groups()
            if not action:self.static('share.html',head);return
            share=active_share(self.server.share_root,token)
            if not share:self.fail(head=head);return
            protected=requires_password(share)
            session_expiry=self.grant(share) if protected else None
            if protected and not session_expiry:self.fail(401,'请输入分享密码',head=head);return
            if action=='document':
                self.respond({**shared_document(share,token),'session_expires_at':session_expiry},head=head);return
            self.file(share,alias,head)
        except (BrokenPipeError,ConnectionResetError):return
        except Exception:
            print('share read failed',flush=True);self.fail(503,'分享暂时不可用，请稍后重试',head=head)
    def do_POST(self):
        try:
            path=urlsplit(self.path).path;match=re.fullmatch(r'/s/([A-Za-z0-9_-]{43})/unlock',path)
            if not match:self.fail();return
            origin=self.headers.get('Origin')
            expected=self.server.public_origin or ('http://'+self.headers.get('Host',''))
            if origin and origin!=expected:self.fail(403,'请求来源无效');return
            if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':self.fail(415,'请求格式无效');return
            token=match[1];reservation,retry=self.server.auth.reserve(self.client_address[0],token)
            if reservation is None:self.fail(429,'尝试过多，请稍后再试',extra=[('Retry-After',str(retry))]);return
            try:length=int(self.headers.get('Content-Length','0'))
            except ValueError:length=0
            if not 0<length<=2048:self.fail(400,'请求格式无效');return
            data=json.loads(self.rfile.read(length));password=data.get('password') if isinstance(data,dict) else None
            if not isinstance(password,str) or len(password)>128:self.fail(400,'请求格式无效');return
            share=active_share(self.server.share_root,token)
            if not share:self.fail();return
            if not requires_password(share):self.respond({'ok':True});return
            if not self.server.auth.kdf.acquire(blocking=False):self.fail(429,'验证繁忙，请稍后重试',extra=[('Retry-After','2')]);return
            try:valid=password_matches(password,share['password_hash'])
            finally:self.server.auth.kdf.release()
            if not valid:self.fail(401,'密码不正确，请重试');return
            # Recheck after the KDF: expiry/reset/revocation can happen concurrently.
            latest=active_share(self.server.share_root,token)
            if not latest or latest['version']!=share['version']:self.fail();return
            session,expires=self.server.auth.success(reservation,latest)
            cookie='workmoire_share='+session+'; Path=/s/'+token+'/; HttpOnly; SameSite=Strict; Max-Age='+str(max(1,expires-int(time.time())))+('; Secure' if self.server.secure else '')
            self.respond({'ok':True},extra=[('Set-Cookie',cookie)])
        except (ValueError,json.JSONDecodeError):self.fail(400,'请求格式无效')
        except (BrokenPipeError,ConnectionResetError):return
        except Exception:
            print('share unlock failed',flush=True);self.fail(503,'验证暂时不可用，请稍后重试')
    def do_PUT(self):self.fail()
    def do_PATCH(self):self.fail()
    def do_DELETE(self):self.fail()
    def static(self,name,head):
        if name=='pdf-viewer.html':name='share-pdf-viewer.html'
        allowed=name in STATIC_EXACT or name=='share-pdf-viewer.html' or any(name.startswith(prefix) for prefix in STATIC_FONTS)
        if not allowed or any(part.startswith('.') for part in Path(name).parts) or '\\' in name:self.fail(head=head);return
        target=(self.server.static_root/name).resolve()
        try:target.relative_to(self.server.static_root)
        except ValueError:self.fail(head=head);return
        if not target.is_file():self.fail(head=head);return
        mime=mimetypes.guess_type(target.name)[0] or 'application/octet-stream';extra=[]
        qualities={}
        for part in self.headers.get('Accept-Encoding','').split(','):
            fields=part.strip().split(';');quality=1.0
            for field in fields[1:]:
                if field.strip().startswith('q='):
                    try:quality=float(field.strip()[2:])
                    except ValueError:quality=0
            qualities[fields[0]]=quality
        zipped=Path(str(target)+'.gz')
        if qualities.get('gzip',qualities.get('*',0))>0 and zipped.exists() and zipped.stat().st_mtime_ns>=target.stat().st_mtime_ns:
            target=zipped;extra.append(('Content-Encoding','gzip'))
        extra.append(('Vary','Accept-Encoding'))
        self.respond(target.read_bytes(),content_type=mime,extra=extra,frame=(name=='share-pdf-viewer.html'),head=head)
    def file(self,share,alias,head):
        with closing(publication_connection(self.server.share_root)) as con:
            file=con.execute('SELECT * FROM share_files WHERE share_id=? AND alias=?',(share['id'],alias)).fetchone()
        if not file or not re.fullmatch(r'[a-f0-9]{64}',file['blob']):self.fail(head=head);return
        target=self.server.share_root/'media'/file['blob']
        if not target.is_file():self.fail(head=head);return
        size=target.stat().st_size;start,end=0,size-1;status=200
        if self.headers.get('Range'):
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',self.headers['Range'])
            if not match or not any(match.groups()):self.fail(416,'范围无效',extra=[('Content-Range','bytes */'+str(size))],head=head);return
            first,last=match.groups()
            if first:start=int(first);end=min(int(last) if last else size-1,size-1)
            else:start=max(0,size-int(last));end=size-1
            if start>=size or start>end:self.fail(416,'范围无效',extra=[('Content-Range','bytes */'+str(size))],head=head);return
            status=206
        inline=file['content_type']=='application/pdf' or file['content_type'].startswith('image/')
        self.send_response(status);self.send_header('Content-Type',file['content_type']);self.send_header('Content-Length',str(max(0,end-start+1)));self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Disposition',('inline' if inline else 'attachment')+"; filename*=UTF-8''"+quote(file['name'],safe=''))
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.security_headers(frame=inline);self.end_headers()
        if not head:
            with target.open('rb') as stream:
                stream.seek(start);remaining=end-start+1
                while remaining>0:
                    chunk=stream.read(min(65536,remaining))
                    if not chunk:break
                    self.wfile.write(chunk);remaining-=len(chunk)


def main():
    root=Path(os.environ['WORKSPACE_SHARE_DATA_DIR']).resolve()
    static=Path(os.environ.get('WORKSPACE_SHARE_STATIC_DIR',Path(__file__).parent/'workspace/static'))
    auth=Path(os.environ.get('WORKSPACE_SHARE_AUTH_DIR',root/'auth'))
    server=ShareHTTPServer((os.environ.get('WORKSPACE_SHARE_HOST','127.0.0.1'),int(os.environ.get('WORKSPACE_SHARE_PORT','5201'))),root,static,auth,secure=os.environ.get('WORKSPACE_SHARE_COOKIE_SECURE','')=='1',public_origin=os.environ.get('WORKSPACE_SHARE_PUBLIC_URL',''))
    print('Workmoire sharing service ready',flush=True)
    try:server.serve_forever()
    finally:server.server_close()

if __name__=='__main__':main()
