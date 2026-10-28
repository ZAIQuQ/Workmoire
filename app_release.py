"""Public release metadata; update checks never include workspace content."""
from __future__ import annotations
import json
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import quote

ROOT=Path(__file__).resolve().parent
REPOSITORY='ZAIQuQ/Workmoire'
PROJECT_URL='https://github.com/'+REPOSITORY
VERSION_RE=re.compile(r'^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')
_cache=None
_cache_until=0.0
_lock=threading.Lock()


def version_tuple(value):
    match=VERSION_RE.fullmatch(value or '')
    return tuple(map(int,match.groups())) if match else None


def local_release():
    version=json.loads((ROOT/'package.json').read_text())['version']
    if not version_tuple(version):raise ValueError('Invalid application version')
    revision=(ROOT/'REVISION').read_text().strip() if (ROOT/'REVISION').is_file() else ''
    if not re.fullmatch(r'[a-f0-9]{40}',revision):revision=''
    log=(ROOT/'CHANGELOG.md').read_text()
    notes=re.search(r'^## \['+re.escape(version)+r'\][^\n]*\n(.*?)(?=^## |\Z)',log,re.M|re.S)
    return {'version':version,'revision':revision,'repository_url':PROJECT_URL,
            'releases_url':PROJECT_URL+'/releases','latest_url':PROJECT_URL+'/releases/latest',
            'changelog_url':PROJECT_URL+'/blob/main/CHANGELOG.md','commits_url':PROJECT_URL+'/commits/main',
            'notes':notes[1].strip() if notes else ''}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def fetch_latest():
    request=urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+'/releases/latest',headers={
        'Accept':'application/vnd.github+json','User-Agent':'Workmoire-release-check','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=4) as response:
        raw=response.read(262145)
        if len(raw)>262144:raise ValueError('Release response too large')
        return json.loads(raw)


def latest_release():
    global _cache,_cache_until
    with _lock:
        if _cache is not None and time.monotonic()<_cache_until:return dict(_cache)
        ttl=900
        try:
            data=fetch_latest()
            if not isinstance(data,dict) or data.get('draft') or data.get('prerelease') or not version_tuple(data.get('tag_name')):
                raise ValueError('No stable version metadata')
            tag=data['tag_name']
            result={'status':'available','version':tag.lstrip('v'),'url':PROJECT_URL+'/releases/tag/'+quote(tag,safe=''),
                    'notes':str(data.get('body') or '')[:32768],'published_at':str(data.get('published_at') or '')[:40]}
        except urllib.error.HTTPError as error:
            result={'status':'unpublished' if error.code==404 else 'unavailable'};ttl=60
        except Exception:
            result={'status':'unavailable'};ttl=60
        _cache={**result,'checked_at':int(time.time())};_cache_until=time.monotonic()+ttl
        return dict(_cache)


def release_info(check=False):
    result=local_release()
    if check:
        latest=latest_release()
        if latest['status']=='available':
            comparison=(version_tuple(latest['version'])>version_tuple(result['version']))-(version_tuple(latest['version'])<version_tuple(result['version']))
            latest['comparison']='newer' if comparison>0 else 'older' if comparison<0 else 'current'
        result['latest']=latest
    return result
