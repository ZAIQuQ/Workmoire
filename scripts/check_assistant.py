"""Check Codex with the systemd service's exact environment and synthetic input."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--service',default='personal-workspace.service')
parser.add_argument('--timeout',type=int,default=45)
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
    result=app.invoke_codex('Reply with only WORKMOIRE_ASSISTANT_OK. This is synthetic input; do not use tools or read files.',timeout=args.timeout)
    if 'WORKMOIRE_ASSISTANT_OK' not in result:raise RuntimeError('The synthetic assistant reply was unexpected')
    print('Assistant check passed with the running service environment; no personal data used')
except Exception as error:
    print('Assistant check failed:',str(error),file=sys.stderr)
    raise SystemExit(1)
