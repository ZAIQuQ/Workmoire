"""Run and score a private, independently reviewed paper release benchmark."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paper_acceptance import MINIMUM_PAPERS, QUALITY_CRITERIA, SHA256, meets_threshold


def private_path(value):
    path = Path(value).resolve()
    if path.is_relative_to(ROOT):
        raise ValueError('Keep benchmark inputs and results outside the source checkout')
    return path


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_new(path, value):
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def load_cases(manifest):
    cases = []
    ids = set()
    for row in read_json(manifest)['cases']:
        pdf = private_path(manifest.parent / row['pdf'])
        if not pdf.is_file() or pdf.suffix.lower() != '.pdf':
            raise ValueError('Every case needs a local PDF')
        with pdf.open('rb') as stream:
            digest = hashlib.sha256()
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        case_id = digest.hexdigest()
        if case_id in ids:
            raise ValueError('A PDF can appear only once per benchmark')
        ids.add(case_id)
        cases.append({'id': case_id, 'pdf': str(pdf), 'reference': row.get('reference', '')})
    if len(cases) < MINIMUM_PAPERS:
        raise ValueError(f'Freeze at least {MINIMUM_PAPERS} distinct PDF inputs before running')
    return cases


def run_benchmark(args):
    cases = load_cases(args.manifest)
    if args.output.exists():
        raise ValueError('Use a new path for each benchmark run')
    pid = subprocess.check_output(['systemctl', 'show', args.service, '-p', 'MainPID', '--value'], text=True).strip()
    if not pid.isdecimal() or int(pid) == 0:
        raise ValueError('The service must be running to load its provider settings')
    environment = (Path('/proc') / pid / 'environ').read_bytes().decode().split('\0')
    os.environ.clear()
    os.environ.update(dict(entry.split('=', 1) for entry in environment if '=' in entry))
    with tempfile.TemporaryDirectory(prefix='workmoire-paper-eval-') as scratch:
        os.environ.update(WORKSPACE_HOST='127.0.0.1', WORKSPACE_PORT='0',
                          WORKSPACE_DATA_DIR=scratch, WORKSPACE_SHARE_DATA_DIR='',
                          WORKSPACE_SETUP_TOKEN='', WORKSPACE_COOKIE_SECURE='0',
                          WORKSPACE_SESSION_SECRET=secrets.token_hex(32))
        if args.provider:
            os.environ['WORKSPACE_PAPER_PROVIDER_PROFILE'] = args.provider
        import workspace_server as app
        if not app.PAPER_PROVIDER_PROFILE or app.codex_command() is None:
            raise ValueError('The benchmark requires the configured Codex binary and a provider profile label')
        profile = app.paper_acceptance_profile()
        app.init_db()
        app.paper_analysis_enabled = lambda: True  # Only this loopback process uses the candidate build before acceptance.
        with app.WorkspaceHTTPServer(('127.0.0.1', 0), app.WorkspaceHandler) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                options = {'origin': 'http://127.0.0.1:' + str(server.server_port),
                           'password': secrets.token_urlsafe(32), 'timeout': app.PAPER_ASSISTANT_TIMEOUT,
                           'cases': cases}
                child = subprocess.run(['node', 'scripts/evaluate_papers.cjs'], cwd=ROOT,
                                       input=json.dumps(options), text=True, stdout=subprocess.PIPE, check=True)
            finally:
                server.shutdown()
                worker.join()
        app.paper_acceptance_profile.cache_clear()
        if profile != app.paper_acceptance_profile() or cases != load_cases(args.manifest):
            raise ValueError('The candidate profile or PDF inputs changed during evaluation')
        rows = json.loads(child.stdout)
        dataset = hashlib.sha256(json.dumps([(row['id'], row['reference']) for row in cases]).encode()).hexdigest()
        write_new(args.output, {'version': 1, 'profile': profile,
                                'dataset': dataset, 'ids': [row['id'] for row in cases], 'attempts': rows})


def score(run, review):
    ids = run['ids']
    attempts = run['attempts']
    reviews = review['reviews']
    if (run.get('version') != 1 or run['dataset'] != review['dataset']
            or not all(isinstance(x, str) and SHA256.fullmatch(x)
                       for x in [run['dataset'], run['profile'], *ids])
            or len(set(ids)) != len(ids) or len(ids) < MINIMUM_PAPERS
            or [row['id'] for row in attempts] != ids):
        raise ValueError('The benchmark must contain one attempt for every frozen input')
    if any(row['status'] not in {'preview', 'prepare_failed', 'analysis_failed'} for row in attempts):
        raise ValueError('Unknown attempt status')
    if any(not isinstance(row.get('report'), str) or not row['report'].strip()
           for row in attempts if row['status'] == 'preview'):
        raise ValueError('Every successful attempt must include the report shown for review')
    expected = {row['id'] for row in attempts if row['status'] == 'preview'}
    if len(reviews) != len(expected) or {row['id'] for row in reviews} != expected:
        raise ValueError('Review every preview exactly once')
    passed = 0
    for row in reviews:
        ratings = row['quality']
        if set(ratings) != set(QUALITY_CRITERIA) or any(type(value) is not bool for value in ratings.values()):
            raise ValueError('A qualified reviewer must record a boolean for every quality criterion')
        passed += all(ratings.values())
    return {'version': 1, 'profile': run['profile'], 'dataset': run['dataset'],
            'total': len(ids), 'passed': passed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    run = commands.add_parser('run')
    run.add_argument('manifest', type=private_path)
    run.add_argument('output', type=private_path)
    run.add_argument('--service', default='personal-workspace.service')
    run.add_argument('--provider', help='Non-secret label for the provider route and CLI profile')
    review = commands.add_parser('score')
    review.add_argument('run', type=private_path)
    review.add_argument('review', type=private_path)
    review.add_argument('output', type=private_path)
    args = parser.parse_args()
    if args.action == 'run':
        run_benchmark(args)
    else:
        evidence = score(read_json(args.run), read_json(args.review))
        passed, total = evidence['passed'], evidence['total']
        print(f'{passed}/{total} passed ({passed / total:.1%})')
        if not meets_threshold(total, passed):
            sys.exit('Below the 90% release threshold')
        write_new(args.output, evidence)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        sys.exit(f'Paper acceptance could not complete ({type(error).__name__})'
                 if not isinstance(error, ValueError) else str(error))
