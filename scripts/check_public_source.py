"""Scan tracked/candidate source paths without printing matched secret values."""
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
patterns=[re.compile(pattern) for pattern in [
    r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    r'\bgh[pousr]_[A-Za-z0-9]{30,}',r'\bgithub_pat_[A-Za-z0-9_]{40,}',
    r'\bsk-[A-Za-z0-9_-]{32,}',r'\bxox[baprs]-[A-Za-z0-9-]{20,}',
]]

def scan():
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    findings=[]
    for name in sorted(set(filter(None,paths))):
        path=ROOT/name
        if not path.is_file():continue
        if any(part in {'data','share-data','backups','node_modules'} for part in path.relative_to(ROOT).parts) or path.suffix in {'.db','.sqlite','.sqlite3','.pem','.key','.log'} or (path.name=='.env' or path.name.startswith('.env.') and path.name!='.env.example'):
            findings.append((name,'runtime/private path'));continue
        if path.suffix in {'.gz','.png','.jpg','.webp','.woff','.woff2','.wasm','.pdf'}:continue
        try:text=path.read_text()
        except UnicodeDecodeError:continue
        for match in re.finditer(r"https?://[^\s/@:]+:[^\s/@]+@[A-Za-z0-9.-]+",text):
            host=urlsplit(match[0]).hostname or ""
            fixture=name.startswith("tests/") and (host in {"example.com","example.org","example.net","localhost"} or host.endswith((".example",".invalid")))
            if not fixture:findings.append((name,"credential-bearing URL"))
        for pattern in patterns:
            if pattern.search(text):findings.append((name,'credential pattern'));break
    return findings

if __name__=='__main__':
    findings=scan()
    for name,kind in findings:print(kind+': '+name)
    print('Public source boundary: '+('FAILED' if findings else 'passed'))
    sys.exit(bool(findings))
