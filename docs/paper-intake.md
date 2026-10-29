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

## Fast briefs and progress

Paper summaries use the versioned brief template with medium reasoning. Upload
bytes and extracted pages are measured; AI progress and remaining time are
explicit estimates learned from recent durations. See [progress and timing](paper-progress.md).

## Profiles and field labels

One medium-reasoning call returns structured publication, author, affiliation,
correspondence, lab and field information together with the concise brief. Facts
retain supporting excerpts found in the selected PDF text; correspondence can
use an explicit matching footnote marker. Unsupported facts become unknown. An
arXiv URL alone does not prove publication status, and a famous author or their
university alone does not identify a lab. No source page is fetched. Publication
information describes the supplied version, not a verified latest status.

Research fields are explicitly classified from the paper's subject, with a short
reason and supporting excerpt. Primary and secondary field names become at most
two distinct tags, in addition to the protected `论文` tag. The preview selects
them by default; the user may deselect either. They enter the unsaved document
on insertion and the catalogue only on normal save. No tag or document is
created during analysis. Replacing the PDF clears its facts and suggestions.

The model can correct PDF metadata titles/authors unless the user edited those
fields. Subsequent title/author/source changes keep the result; insertion
revalidates the reviewed analysis and composes the document without another AI
call. Malformed structured output gives an explicit retry error. Raw model JSON
is not rendered as the final document.
