"""Validate the public synthetic fixtures and versioned document task templates."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = {
    "summarize": ROOT / "prompts/document-summarize.md",
    "outline": ROOT / "prompts/document-outline.md",
    "next_steps": ROOT / "prompts/document-next-steps.md",
    "review": ROOT / "prompts/document-review.md",
}
FIXTURES = ROOT / "prompts/evals/document-tasks.json"


def main() -> None:
    errors: list[str] = []
    for task, path in TASKS.items():
        if not path.is_file():
            errors.append(f"missing template: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if f"· {task} · v1" not in text:
            errors.append(f"template is missing its version header: {path}")
        if not any(phrase in text for phrase in ("不要编造", "不补造", "不虚构", "不进行外部事实核查")):
            errors.append(f"template is missing its grounding boundary: {path}")
        if "Markdown" not in text:
            errors.append(f"template does not define an editable output: {path}")
    try:
        data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"fixture cannot be loaded: {exc}")
        data = {}
    if data.get("version") != 1:
        errors.append("fixture version must be 1")
    cases = data.get("cases")
    if not isinstance(cases, list) or {case.get("task") for case in cases if isinstance(case, dict)} != set(TASKS):
        errors.append("fixtures must cover each document task exactly at least once")
    seen: set[str] = set()
    for case in cases if isinstance(cases, list) else []:
        if not isinstance(case, dict):
            errors.append("fixture case must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            errors.append(f"fixture case id is missing or duplicated: {case_id}")
        seen.add(case_id)
        if not isinstance(case.get("material"), str) or len(case["material"]) < 40:
            errors.append(f"fixture case is too short: {case_id}")
        checks = case.get("checks")
        if not isinstance(checks, dict) or not isinstance(checks.get("must_include"), list) or not isinstance(checks.get("must_omit"), list) or not checks.get("shape"):
            errors.append(f"fixture checks are incomplete: {case_id}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"validated {len(TASKS)} templates and {len(cases)} synthetic evaluation cases")


if __name__ == "__main__":
    main()
