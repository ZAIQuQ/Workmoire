# Two creation choices and selected-PDF intake

New document offers exactly **空白文档** and **论文资料**. The ordinary editor
handles blogs, plans, ideas and checklists through content and editable tags.
Legacy project/blog/log rows remain intact and are presented as ordinary
documents; explicit new writes/imports normalize non-paper kinds to `note`.
Only the `论文` classification is built in and protected.

## Paper sources

| Input | Behavior |
| --- | --- |
| Local PDF | Upload that file, validate it and extract its text. No source download. |
| URL | Resolve available public metadata/PDF links and try downloading a PDF. |
| URL plus local PDF | Use the supplied file. Retain the URL as attribution only. |
| URL download fails | Show the original/download link and request a manual PDF. |
| Replace a downloaded PDF | Invalidate previous extraction/analysis and use the replacement bytes exclusively. |

The user can inspect the chosen file in the embedded PDF reader, correct its
title/author, optionally generate reading notes, then place the dossier in the
editor and save. Existing paper documents remain editable even if created by an
older metadata-only flow.

## File and evidence boundaries

The explicit import action may create a temporary unassociated attachment; it
never creates a document. Uploaded bytes pass a signature check and PDF.js parsing.
Public downloads use the existing pinned-address transport and size/deadline
bounds. A failed public download never falls back to a different unconfirmed file.

PDF.js reads the selected local File during upload, or the authenticated file ID
for a downloaded paper. The preview always points at the final stored file. Extraction is
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

Browser checks cover the exact two options, upload-only, URL-only, supplied-file
priority, PDF replacement, manual fallback and narrow screens. They compare saved
bytes and model-request text to the chosen fixture. Backend checks enforce file
validation, authentication, selected-text analysis, no document writes during
preparation/generation, and ordinary handling of legacy kinds.

## Fast briefs and progress

Paper summaries use the versioned brief template with medium reasoning. Upload
bytes and extracted pages are measured; AI progress and remaining time are
explicit estimates learned from recent durations. See [progress and timing](paper-progress.md).
