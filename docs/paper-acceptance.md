# Paper analysis release acceptance

Paper analysis starts disabled. A candidate can be enabled after at least **90%**
of a preselected set of **50 or more distinct papers** produces a usable report.
For 50 papers, at least 45 must pass. Manual PDF upload and paper filing are
available while analysis is paused.

## Run the benchmark

Prepare a held-out set of public papers with extractable text. Select it before
running the candidate and cover the papers people actually submit, including
preprints, proceedings papers, different research areas, long PDFs and
multi-column or table-heavy layouts. Keep the reviewed facts, PDF files and
outputs outside the checkout. Each entry in the private manifest has a local
`pdf` path relative to the manifest, with an optional `reference`:

```json
{"cases":[{"pdf":"corpus/paper-01.pdf","reference":"https://example.org/paper-01"}]}
```

Use the candidate checkout and its installed Playwright Chromium. The runner
uses the configured model provider from the running service and an isolated
loopback instance with a disposable account and database. For a candidate run,
pass its settings with `--model`, `--reasoning`, `--review-model`,
`--review-reasoning`, `--final-review-model`, and `--timeout`. Use the same generation and review models,
reasoning effort, timeout, provider route and CLI configuration intended for
production. The provider label is a non-secret identifier. Change it when the
provider route or CLI version/profile changes.

```sh
python3 scripts/evaluate_paper_release.py run \
  /path/to/manifest.json /path/to/run.json --provider candidate-route-v1 \
  --model gpt-6.2-sol --reasoning medium \
  --review-model gpt-6.1-sol --review-reasoning medium \
  --final-review-model gpt-6.1-terra --timeout 300 --workers 3
```

Count one submission per paper. Recovery already built into a submitted job is
part of the same attempt. Upload or extraction failures, timeouts, provider
errors, terminal rejections and missing previews all count as failures. Include
the full run in the denominator. Fixes informed by results should be measured
on a fresh held-out set.

## Review the reports

An assessor independent of the generation and production verification calls
compares each preview with the source. Record all five decisions for every
preview:

- `format_and_length` follows the agreed template and length limits.
- `grounding` checks names, publication status, dates, numbers and factual
  claims against the PDF.
- `core_insight` captures the actual research problem and main contribution.
- `mechanisms` explains how the main method works in concrete terms.
- `experiments` covers the main result and comparators where the paper supports them.

A report counts as one success when all five decisions pass. Use
`{"dataset":"<dataset from run.json>","reviews":[...]}` with one
`{"id":"<case id>","quality":{...}}` per preview. Run the scorer:

```sh
python3 scripts/evaluate_paper_release.py score \
  /path/to/run.json /path/to/review.json /path/to/paper-acceptance.json
```

The scorer creates an acceptance record only when the threshold is met. Keep
the detailed results private. Install the record as `paper-acceptance.json` in
the private workspace data directory. Set `WORKSPACE_PAPER_ANALYSIS_ENABLED=1`
and `WORKSPACE_PAPER_PROVIDER_PROFILE` to the evaluated provider label. The
server checks the benchmark threshold and the fingerprint of the analysis code,
prompts, browser bundle, PDF extractor and model settings before accepting a
generation request. A changed profile requires a fresh acceptance record.

The normal CI suite and small synthetic model checks are regression tests. Use
the held-out results above for a decision to enable analysis.

## v1.16.4 acceptance result

The frozen sample included 50 distinct public papers, with 10 each from arXiv,
ACL, CVPR, ICML, and AISTATS. The browser workflow produced 49 previews. An
independent GPT-6 Astra review compared the reports with extracted PDF text and
passed 47. One job was rejected before preview. The independent review rejected
one report for omitting an earlier public version and one for omitting the
paper’s dataset construction contribution. The 49 previews had a median
end-to-end latency of 48 seconds, a P90 of 77 seconds and a maximum of 91 seconds.
