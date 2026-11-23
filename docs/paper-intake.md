# Two creation choices and manual PDF intake

New document offers exactly **空白文档** and **论文资料**. The ordinary editor
handles blogs, plans, ideas and checklists through content and editable tags.
Legacy project/blog/log rows remain intact and are presented as ordinary
documents; explicit new writes/imports normalize non-paper kinds to `note`.
Only the `论文` classification is built in and protected.

## Paper sources

| Input | Behavior |
| --- | --- |
| Local PDF | Upload that file, validate it and extract its text. No source download. |
| URL without a file | Record/open the source link; require a manual PDF upload before proceeding. |
| URL plus local PDF | Use only the supplied file. Retain the URL as attribution without fetching it. |
| Replace an uploaded PDF | Invalidate previous extraction/analysis and use the replacement bytes exclusively. |

The user can inspect the chosen file in the embedded PDF reader, correct its
title/author, optionally generate reading notes, then place the dossier in the
editor and save. Existing paper documents remain editable even if created by an
older metadata-only flow.

## File and evidence boundaries

The explicit import action may create a temporary unassociated attachment; it
never creates a document. Uploaded bytes pass a signature check and PDF.js parsing.
Remote PDF retrieval is disabled. `/api/papers/prepare` and `/api/papers/draft`
require an uploaded file, and the retired `/api/papers/pdf` and `/api/papers/lookup`
endpoints return authenticated HTTP 410 responses without any outbound request.
This also prevents older pages from starting source downloads. The editor offers
local PDF upload only; legacy external PDF blocks keep an “Open source” link and a
manual-upload hint without fetching the remote PDF.

PDF.js reads the selected local File during upload. The preview always points at
the final stored file. Extraction is
bounded to 80 pages, 60,000 characters and a 45-second loading task; the worker is
destroyed afterwards. The server verifies the selected attachment and accepts the
browser-extracted text as supplied evidence. Analysis receives only this text
and the confirmed metadata. It does not use a linked page's abstract/HTML instead.
PDF layout, figures and formula details still require checking the original.
Scanned/textless files can be saved with notes, but automatic analysis is disabled
when there is insufficient readable text.

Only the final file is transferred into the editor's pending attachments and
associated on normal document save. Replaced/cancelled temporary imports move
to recoverable file trash. The PDF and document bytes are never silently replaced
by a metadata correction or model response. Revisions, local drafts and normal
conflict checks remain in use.

## Compatibility and verification

Obsolete blog endpoints, parser/prompt resources and dedicated creation controls
are retired. The already-expanded legacy database constraint is retained; there
is no destructive downgrade or startup rewrite of user records. Blog tags become
ordinary tags and may be renamed or removed.

Browser checks cover the exact two options, manual upload, URL-only gating, source
attribution, PDF replacement, editor upload, legacy external blocks and narrow
screens. They compare saved
bytes and model-request text to the chosen fixture. Backend checks enforce file
validation, authentication, selected-text analysis, no document writes during
preparation/generation, and ordinary handling of legacy kinds.

## Compact reading reports

Analysis is disabled until the candidate meets the [release acceptance gate](paper-acceptance.md).

The versioned v4 template uses `gpt-6.1-terra` / `low` by default. A separate fast
model call verifies content quality after generation.
Model names are provider-specific and configurable independently of general
assistant tasks. Generation, verification and one optional recovery attempt share a
150-second total model budget. The workflow uses the uploaded PDF text. Upload bytes and
extracted pages are measured; analysis progress is an estimate. See
[progress and timing](paper-progress.md).

Reports have exactly three sections: **论文信息**, **阅读笔记**, **原文 PDF**.
Paper information contains title and authors; an optional source URL is attached
to the title itself.
Reading notes use these ordered fields:

1. 首次公开 — an evidenced first release or v1 date. Workmoire can recover a missing value from an explicit first-page arXiv v1 watermark.
2. 正式发表 — a venue and year with a paper-specific publication or acceptance statement. A conference template footer leaves this field empty.
3. 研究方向 — one topic, rendered as inline code.
4. 研究关键词 — up to five inline-code terms.
5. Motivation — one paragraph, at most 150 characters.
6. Contribution — one to three named items, each description at most 90 characters.
7. 实验贡献 — one paragraph, at most 100 characters.
8. 一句话总结 — one sentence, at most 70 characters.

The quality template independently checks factual grounding (including experiment
numbers and comparators), the core insight, concrete technical mechanisms,
experimental coverage and non-redundant writing. Approval requires every check
and source-matching citations; rejected or malformed reviews produce an error
and cannot expose a candidate preview. This is a model-assisted gate, not a proof
of correctness. The source PDF remains available for review. Reproduce the live
provider evaluation with `python3 scripts/check_paper_quality.py --service <service>`;
its public-safe cases include wrong numbers/comparators, vague prose, repeated
contributions, a missed core insight and omitted known publication metadata. The UI shows a quality-check stage.

The renderer owns the headings and list structure. Reading notes have an
800-character visible-text budget; the complete text report has a 1,032-character
budget excluding PDF/source URLs. Off-template or overlong AI output returns an
explicit retry error; it is never silently inserted or stored. No abstract
translation, lab biography, review verdict or missing-information filler is added.
Unsupported metadata and optional empty fields are omitted. A revised preprint
date is not treated as the first publication date.

Primary and secondary field classifications retain supporting PDF excerpts
internally and suggest up to two distinct selectable tags, plus the built-in
`论文` tag. Analysis creates no document or tags. Title/author/source corrections
reuse and revalidate the reviewed result without a second model call; replacing
the PDF invalidates it. Extraction coverage stays in the import UI.

Saved documents remain untouched. Previously reviewed v3 drafts can still be
inserted with their prior structure; all new AI calls must produce v4 reports.
