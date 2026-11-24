"""Publish an already-tested and deployed revision to the established GitHub repo."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app_release import REPOSITORY,local_release
from scripts.check_public_source import scan


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def run(*args):subprocess.run(args,cwd=ROOT,check=True)


def quality_run(head, *, wait=False):
    deadline = time.monotonic() + 120
    while True:
        raw = subprocess.check_output(
            ['gh', 'run', 'list', '--repo', REPOSITORY, '--workflow', 'ci.yml',
             '--branch', 'main', '--event', 'push', '--commit', head, '--limit', '1',
             '--json', 'databaseId,conclusion,url'], text=True,
        )
        runs = json.loads(raw)
        if runs:
            result = runs[0]
            if wait and not result['conclusion']:
                run('gh', 'run', 'watch', str(result['databaseId']), '--repo', REPOSITORY,
                    '--interval', '10', '--exit-status')
                wait = False
                continue
            if result['conclusion'] == 'success':
                return result['url']
            raise RuntimeError('GitHub quality checks must pass for this commit: '+result['url'])
        if not wait or time.monotonic() >= deadline:
            raise RuntimeError('No GitHub main quality run found for '+head[:12])
        time.sleep(5)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',help='Push main and verify GitHub quality before deployment')
    parser.add_argument('--deployment-dir',type=Path)
    parser.add_argument('--health-url',default='http://127.0.0.1:5200/healthz')
    parser.add_argument('--share-deployment-dir',type=Path)
    parser.add_argument('--share-health-url',default='http://127.0.0.1:5201/healthz')
    args=parser.parse_args()
    if not args.prepare and args.deployment_dir is None:
        parser.error('--deployment-dir is required when publishing')
    if args.prepare and (args.deployment_dir or args.share_deployment_dir):
        parser.error('--prepare does not take deployment directories')
    if git('status','--porcelain'):raise RuntimeError('Commit the reviewed change before publishing')
    head=git('rev-parse','HEAD');info=local_release();tag='v'+info['version']
    if not info['notes']:raise RuntimeError('Add changelog notes for the version before publishing')
    remote=git('remote','get-url','origin')
    if remote not in {'https://github.com/'+REPOSITORY+'.git','https://github.com/'+REPOSITORY,'git@github.com:'+REPOSITORY+'.git'}:
        raise RuntimeError('origin does not match the established repository')
    if scan():raise RuntimeError('Public source scan failed; inspect locally before publishing')
    run('git','diff','--check')
    auth=subprocess.run(['gh','auth','status','--hostname','github.com'],capture_output=True,text=True)
    if auth.returncode:raise RuntimeError('GitHub login required: gh auth login --hostname github.com --git-protocol https --web --scopes workflow')
    access=subprocess.check_output(['gh','api','repos/'+REPOSITORY,'--jq','.permissions.push'],text=True).strip()
    if access!='true':raise RuntimeError('The authenticated GitHub account has no push permission for this repository')
    run('git','fetch','origin','main')
    if subprocess.run(['git','merge-base','--is-ancestor','origin/main',head],cwd=ROOT).returncode:
        raise RuntimeError('Integrate the new upstream commits and redeploy before publishing')
    if args.prepare:
        run('git','push','origin','HEAD:refs/heads/main')
        print('GitHub quality passed for '+head[:12]+': '+quality_run(head,wait=True))
        return
    if git('rev-parse','origin/main')!=head:
        raise RuntimeError('Run this script with --prepare before deploying and publishing')
    quality_run(head)
    deployments=[(args.deployment_dir,args.health_url)]
    if args.share_deployment_dir:deployments.append((args.share_deployment_dir,args.share_health_url))
    for directory,url in deployments:
        if (directory/'REVISION').read_text().strip()!=head:raise RuntimeError('Deployment revision does not match HEAD')
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=5) as response:
            if not json.load(response).get('ok'):raise RuntimeError('Deployment health check failed')
    existing=subprocess.run(['git','rev-parse','--verify','refs/tags/'+tag],cwd=ROOT,capture_output=True,text=True)
    if existing.returncode==0:
        if git('rev-list','-n','1',tag)!=head:raise RuntimeError('Version tag already points to a different commit')
    else:run('git','tag','-a',tag,'-m','Workmoire '+tag,head)
    run('git','push','origin','refs/tags/'+tag)
    with tempfile.TemporaryDirectory(prefix='workmoire-release-') as temporary:
        notes=Path(temporary)/'notes.md'
        body=re.sub(r'(?<=\]\()((?![a-z][a-z0-9+.-]*:|/|#)[^ )]+)(?=\))',lambda match:'https://github.com/'+REPOSITORY+'/blob/'+tag+'/'+match[0],info['notes'],flags=re.I)
        notes.write_text(body+'\n')
        exists=subprocess.run(['gh','release','view',tag,'--repo',REPOSITORY],capture_output=True)
        if exists.returncode:run('gh','release','create',tag,'--repo',REPOSITORY,'--verify-tag','--title','Workmoire '+tag,'--notes-file',str(notes))
    remote_sha=git('ls-remote','origin','refs/heads/main').split()[0]
    if remote_sha!=head:raise RuntimeError('Remote branch verification failed')
    print('Published '+tag+' from '+head[:7]+' after GitHub quality and deployment checks.')

if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,subprocess.CalledProcessError) as error:
        print(str(error),file=sys.stderr);sys.exit(1)
