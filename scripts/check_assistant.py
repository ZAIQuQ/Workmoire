"""Check Codex with the systemd service's exact environment and synthetic input."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--service',default='personal-workspace.service')
parser.add_argument('--timeout',type=int,default=90)
parser.add_argument('--paper',action='store_true',help='Use the dedicated paper reasoning/model settings')
parser.add_argument('--blog',action='store_true',help='Exercise the blog-summary template with synthetic supplied text')
args=parser.parse_args()
try:
    pid=subprocess.check_output(['systemctl','show',args.service,'--property=MainPID','--value'],text=True).strip()
    if not pid.isdecimal() or int(pid)==0:raise RuntimeError('The workspace service is not running')
    entries=(Path('/proc')/pid/'environ').read_bytes().split(b'\0')
    runtime={key.decode():value.decode() for key,value in (entry.split(b'=',1) for entry in entries if b'=' in entry)}
    # Drop the interactive shell's configuration/proxies, which can otherwise
    # make a broken service appear healthy. Never print the environment.
    os.environ.clear();os.environ.update(runtime)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    import workspace_server as app
    if args.blog:
        app.ASSISTANT_TIMEOUT=args.timeout
        result=app.blog_draft({'reference':'https://example.org/blog','title':'Synthetic blog acceptance fixture','author':'Example Author','text':('This synthetic article describes a note-taking method. Save the original source link, record the publication date, keep the author attribution, and distinguish the author claims from personal comments. It contains no research results or numerical claims. ')*4})
        if result['article']['scope']!='provided_text' or not all(section in result['content'] for section in ['## 来源信息','## 内容概览','## 要点']):
            raise RuntimeError('The synthetic blog summary was unexpected')
        print('Blog assistant check passed with the running service environment; attributed summary generated; no personal data used or saved')
    else:
        result=app.invoke_codex('Reply with only WORKMOIRE_ASSISTANT_OK. This is synthetic input; do not use tools or read files.',timeout=args.timeout,reasoning_effort=app.PAPER_REASONING_EFFORT if args.paper else app.CODEX_REASONING_EFFORT,model=app.PAPER_CODEX_MODEL if args.paper else app.CODEX_MODEL)
        if 'WORKMOIRE_ASSISTANT_OK' not in result:raise RuntimeError('The synthetic assistant reply was unexpected')
        print(('Paper assistant' if args.paper else 'Assistant')+' check passed with the running service environment; reasoning='+str(app.PAPER_REASONING_EFFORT if args.paper else app.CODEX_REASONING_EFFORT)+'; no personal data used')
except Exception as error:
    print('Assistant check failed:',str(error),file=sys.stderr)
    raise SystemExit(1)
