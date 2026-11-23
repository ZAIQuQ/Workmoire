"""Release evidence for the paper analysis pipeline."""

import hashlib
import json
import re
from pathlib import Path


MINIMUM_PAPERS = 50
QUALITY_CRITERIA = ('format_and_length', 'grounding', 'core_insight', 'mechanisms', 'experiments')
PROFILE_FILES = (
    'workspace_server.py', 'paper_intake.py', 'paper_tools.py', 'paper_runtime.py',
    'paper_acceptance.py', 'prompts/paper-brief.md', 'prompts/paper-quality.md',
    'workspace/static/app.js', 'workspace/static/vendor/interface.js',
    'workspace/static/vendor/pdf-extractor.mjs', 'workspace/static/vendor/pdf.worker.min.mjs',
)
SHA256 = re.compile(r'[a-f0-9]{64}')


def profile_digest(root: Path, *, model: str, reasoning: str, timeout: int, provider: str) -> str:
    config = [model, reasoning, timeout, provider]
    state = hashlib.sha256(json.dumps(config, separators=(',', ':')).encode())
    for name in PROFILE_FILES:
        state.update(name.encode())
        state.update(hashlib.sha256((root / name).read_bytes()).digest())
    return state.hexdigest()


def meets_threshold(total, passed):
    return (type(total) is int and type(passed) is int and total >= MINIMUM_PAPERS
            and passed <= total and passed * 10 >= total * 9)


def accepted(path: Path, profile: str) -> bool:
    """Reject missing, stale, malformed or below-threshold results."""
    try:
        with path.open(encoding='utf-8') as stream:
            evidence = json.loads(stream.read(8192))
        return (isinstance(evidence, dict) and type(evidence.get('version')) is int and evidence['version'] == 1
                and evidence.get('profile') == profile
                and isinstance(evidence.get('dataset'), str) and bool(SHA256.fullmatch(evidence['dataset']))
                and meets_threshold(evidence.get('total'), evidence.get('passed')))
    except (OSError, ValueError):
        return False
