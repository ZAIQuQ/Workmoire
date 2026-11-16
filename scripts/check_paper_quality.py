"""Exercise paper generation and semantic quality checks on public-safe fixtures."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service',default='personal-workspace.service')
    parser.add_argument('--model',help='Explicit model to test before deployment')
    parser.add_argument('--reasoning',help='Explicit reasoning to test before deployment')
    args=parser.parse_args()
    pid=subprocess.check_output(['systemctl','show',args.service,'--property=MainPID','--value'],text=True).strip()
    runtime=dict(entry.split('=',1) for entry in (Path('/proc')/pid/'environ').read_bytes().decode().split('\0') if '=' in entry)
    os.environ.clear();os.environ.update(runtime)
    sys.path.insert(0,str(ROOT))
    import workspace_server as app
    from paper_intake import parse_paper_analysis,check_report_length,paper_reading_markdown,selected_pdf_header
    if args.model:app.PAPER_CODEX_MODEL=args.model
    if args.reasoning:app.PAPER_REASONING_EFFORT=args.reasoning
    fixture=json.loads((ROOT/'prompts/evals/paper-quality.json').read_text())
    original_invoke=app.invoke_codex;reviews=[]
    def capture_synthetic_review(prompt,**kwargs):
        raw=original_invoke(prompt,**kwargs)
        if '---待核验报告---' in prompt:reviews.append(raw)
        return raw
    app.invoke_codex=capture_synthetic_review
    source=fixture['source'];failures=[]
    start=time.monotonic()
    details=app.paper_notes({'title':'Synthetic Sequence Study','authors':[],'url':''},{'scope':'pdf_text','text':source,'truncated':False,'page_count':2,'pages_read':2})
    report=selected_pdf_header({'title':details['title']['name'],'authors':[r['name'] for r in details['authors']]},{'id':'a'*32,'name':'synthetic.pdf'},{},include_pdf=False,compact=True)+paper_reading_markdown(details)
    check_report_length(report)
    print('Synthetic generation and quality check passed in %.1fs (%s / %s)'%(time.monotonic()-start,app.PAPER_CODEX_MODEL,app.PAPER_REASONING_EFFORT),flush=True)
    for case in fixture['cases']:
        report=copy.deepcopy(fixture['report']);report['reading'].update(case['reading_overrides'])
        details=parse_paper_analysis(report,source,require_compact=True)
        approved=True;start=time.monotonic()
        try:app.check_paper_quality(details,source,timeout=90)
        except ValueError:approved=False
        matched=approved==case['approved']
        print('%s: %s (%.1fs)'%(case['id'],'passed' if matched else 'FAILED',time.monotonic()-start),flush=True)
        if not matched:
            failures.append(case['id'])
            try:
                diagnostic=json.loads(reviews[-1])
                print('Synthetic review diagnostic:',json.dumps({key:diagnostic.get(key) for key in ['approved','checks','issues']},ensure_ascii=False),flush=True)
            except (ValueError,IndexError,AttributeError):print('Malformed synthetic quality response',flush=True)
    if failures:raise RuntimeError('Quality evaluation failed: '+', '.join(failures))
    print('All quality cases passed; no personal content used.')

if __name__=='__main__':main()
