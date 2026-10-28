"""Private, immutable bug reports and explicitly supplied screenshots."""
from __future__ import annotations
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
from datetime import datetime,timezone

MAX_IMAGE=5*1024*1024
MAX_TOTAL=20*1024*1024
MAX_REQUEST=29*1024*1024
ID_RE=re.compile(r'^[a-f0-9]{32}$')


def init_schema(con):
    con.executescript('''
    CREATE TABLE IF NOT EXISTS bug_reports(
      id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE, payload_hash TEXT NOT NULL,
      title TEXT NOT NULL, description TEXT NOT NULL, reporter TEXT NOT NULL,
      version TEXT NOT NULL, browser TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS bug_report_images(
      id TEXT PRIMARY KEY, report_id TEXT NOT NULL REFERENCES bug_reports(id),
      name TEXT NOT NULL, stored_name TEXT NOT NULL, content_type TEXT NOT NULL, size INTEGER NOT NULL,
      position INTEGER NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_bug_reports_created ON bug_reports(created_at DESC,id DESC);
    CREATE INDEX IF NOT EXISTS idx_bug_report_images ON bug_report_images(report_id,position);
    ''')


def image_type(raw):
    if len(raw)>=32 and raw.startswith(b'\x89PNG\r\n\x1a\n') and raw[12:16]==b'IHDR' and raw.endswith(b'IEND\xaeB`\x82'):
        width,height=int.from_bytes(raw[16:20],'big'),int.from_bytes(raw[20:24],'big')
        if 0<width<=16000 and 0<height<=16000 and width*height<=64000000:return 'image/png','.png'
    if len(raw)>=32 and raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'):return 'image/jpeg','.jpg'
    if len(raw)>=20 and raw.startswith((b'GIF87a',b'GIF89a')) and raw.endswith(b';'):return 'image/gif','.gif'
    if len(raw)>=20 and raw.startswith(b'RIFF') and raw[8:12]==b'WEBP' and int.from_bytes(raw[4:8],'little')+8==len(raw):return 'image/webp','.webp'
    raise ValueError('截图必须是有效的 PNG、JPEG、GIF 或 WebP 图片')


def validate(payload):
    if not isinstance(payload,dict):raise ValueError('上报内容格式无效')
    title,description=payload.get('title'),payload.get('description')
    if not isinstance(title,str) or not 1<=len(title.strip())<=200:raise ValueError('请填写标题，最多 200 字')
    if not isinstance(description,str) or not 1<=len(description.strip())<=20000:raise ValueError('请填写问题描述和复现步骤，最多 20000 字')
    key=payload.get('request_key','')
    if not isinstance(key,str) or not ID_RE.fullmatch(key):raise ValueError('提交标识无效，请刷新上报页面重试')
    images=payload.get('images',[])
    if not isinstance(images,list) or len(images)>5:raise ValueError('每次最多上传 5 张截图')
    decoded=[];total=0
    for image in images:
        if not isinstance(image,dict) or not isinstance(image.get('data'),str) or len(image['data'])>(MAX_IMAGE+2)//3*4:raise ValueError('每张截图不能超过 5 MB')
        try:raw=base64.b64decode(image['data'],validate=True)
        except (ValueError,binascii.Error):raise ValueError('截图数据无效') from None
        total+=len(raw)
        if not 0<len(raw)<=MAX_IMAGE or total>MAX_TOTAL:raise ValueError('每张截图最多 5 MB，合计最多 20 MB')
        mime,extension=image_type(raw)
        name=str(image.get('name') or '截图').replace('\\','/').rsplit('/',1)[-1][:200]
        decoded.append({'raw':raw,'name':name or '截图','content_type':mime,'extension':extension})
    canonical=[title.strip(),description.strip(),[(image['name'],hashlib.sha256(image['raw']).hexdigest()) for image in decoded]]
    digest=hashlib.sha256(json.dumps(canonical,ensure_ascii=False).encode()).hexdigest()
    return title.strip(),description.strip(),key,digest,decoded


def detail(con,report_id):
    row=con.execute('SELECT id,title,description,version,browser,created_at FROM bug_reports WHERE id=?',(report_id,)).fetchone()
    if not row:return None
    result=dict(row)
    result['images']=[{**dict(image),'url':'/api/bug-reports/'+report_id+'/images/'+image['id']} for image in con.execute('SELECT id,name,content_type,size FROM bug_report_images WHERE report_id=? ORDER BY position',(report_id,))]
    return result


def listing(con,offset=0,limit=20):
    total=con.execute('SELECT count(*) FROM bug_reports').fetchone()[0]
    rows=con.execute('SELECT b.id,b.title,b.version,b.created_at,(SELECT count(*) FROM bug_report_images i WHERE i.report_id=b.id) AS image_count FROM bug_reports b ORDER BY b.created_at DESC,b.id DESC LIMIT ? OFFSET ?',(limit,offset)).fetchall()
    return {'reports':[dict(row) for row in rows],'total':total,'next_offset':offset+len(rows) if offset+len(rows)<total else None}


def create(con,files_dir:Path,payload,reporter,version,browser):
    title,description,key,digest,images=validate(payload)
    report_id=secrets.token_hex(16);folder=files_dir/'bug-reports'/report_id;committed=False;created_folder=False
    try:
        with con:
            con.execute('BEGIN IMMEDIATE')
            existing=con.execute('SELECT id,payload_hash FROM bug_reports WHERE request_key=?',(key,)).fetchone()
            if existing:
                if existing['payload_hash']!=digest:raise ValueError('该提交标识已使用，请重新提交修改后的内容')
                return detail(con,existing['id']),False
            folder.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            folder.mkdir(mode=0o700);created_folder=True
            stamp=datetime.now(timezone.utc).isoformat(timespec='microseconds')
            con.execute('INSERT INTO bug_reports VALUES(?,?,?,?,?,?,?,?,?)',(report_id,key,digest,title,description,reporter,version,str(browser)[:500],stamp))
            for position,image in enumerate(images):
                image_id=secrets.token_hex(16);stored=image_id+image['extension'];path=folder/stored
                with path.open('xb') as stream:stream.write(image['raw'])
                path.chmod(0o600)
                con.execute('INSERT INTO bug_report_images VALUES(?,?,?,?,?,?,?)',(image_id,report_id,image['name'],stored,image['content_type'],len(image['raw']),position))
        committed=True
        return detail(con,report_id),True
    finally:
        if created_folder and not committed and folder.exists():shutil.rmtree(folder)


def image_file(con,files_dir:Path,report_id,image_id):
    row=con.execute('SELECT * FROM bug_report_images WHERE report_id=? AND id=?',(report_id,image_id)).fetchone()
    if not row:return None
    root=(files_dir/'bug-reports'/report_id).resolve();path=(root/row['stored_name']).resolve()
    if path.parent!=root or not path.is_file():return None
    return dict(row),path
