# Workmoire · 拾序

A self-hosted, single-user workspace for academic notes and paper reading.
The interface has three primary destinations: all documents, paper references,
and document relationships. Creation has exactly two choices: **Blank document**
and **Paper materials**. Blogs, plans, ideas and checklists use ordinary documents
and tags, rather than separate creation types.

## Bug reports

Use the bottom-right **上报 Bug** link to open a separate page. Add a title,
reproduction steps and optional screenshots. File selection, drag/drop and
clipboard images are supported. The form uploads only when submitted; failed
submissions retain their input and may be retried. The current editor stays open.

Open **Bug 记录** from the account menu to read submitted reports. In this
single-account installation, the signed-in workspace owner is the maintainer.
Reports cannot be edited or deleted through the interface/API. See
[storage, access and backup details](bug-reports.md).

## Writing

Click in a table to reveal **每列等宽** (equal columns) and **固定宽度** (fixed
width) in the table toolbar. Fixed width is on by default, including for older
tables without a mode setting: the table fits the body, text wraps inside cells,
and dragging a column boundary redistributes space between adjacent columns.
The table adapts to viewport changes without editing the document. Existing
stored widths are retained as proportions until you explicitly change them.

Turn off fixed width to allow wider columns. When the table exceeds the body,
a visible scrollbar below it supports dragging and keyboard navigation. The
page itself stays within the viewport. Equal columns respects merged cells and
row spans; in free-width mode it distributes the current table width. Layout
changes use normal undo, save, history and native export/share boundaries.
Press Escape during a column drag to cancel. Markdown export keeps the table
text; use JSON/full archives to preserve widths and the fixed/free mode.

Choose **字体** in the toolbar to use sans, serif or monospaced text throughout
one document. The default sans face is unchanged. Serif uses locally bundled
Noto Serif SC; mono uses Maple Mono with the existing Chinese fallback. The
choice applies in editing, reading and shared snapshots and supports undo/redo.
It is stored with the native document, including local drafts, saved history and
JSON/full archives; Markdown export does not carry document fonts. Code, formula
faces and interface typography retain their own styles.

Select text, then use the toolbar's **A** color button for a preset or custom
color. **默认颜色** removes only the selected text's explicit color. Bold,
italic, underline, strike, inline code, highlighting, lists, quotes, alignment,
links and clearing text formatting are directly available. **更多** contains
only subscript, superscript and list indentation. Hover or keyboard-focus a
control to see its function and any shortcut.

The document body has an independent outline on its right in editing, reading,
and focus modes. Headings 1–6 appear with their hierarchy; selecting an entry
scrolls only the document, while the current section follows scrolling. Heading
edits, undo and content reflow update the outline automatically. On narrow
screens use the outline button beside the reading/editing controls, choose a
section to close the panel, or press Escape. Navigation does not change the
document, editor selection or save state. Plain text styled to look large is
not a heading: choose a heading style to include a paragraph in the outline.

- Tiptap/ProseMirror block editor with direct rich-text input, a selection toolbar,
  slash insertion menu, draggable blocks, and separate undo steps for block actions.
  Bold, italic, underline, strike, color, highlight, alignment, nested lists and
  checklists use native editor transactions.
- Editable tables with row/column operations and resizable columns; inline/display
  LaTeX formulas with live editing; syntax-highlighted code blocks with a language
  picker; resizable images; and a persistent embedded PDF.js reader.
- Paste formatted HTML or Markdown, paste/drop images, search across styled text,
  navigate the outline, and switch between editing, reading and focus modes.
  The editor updates changed blocks only. Markdown serialization is deferred to
  saves, idle drafts, explicit assistant requests and export.
- Uploads remain authenticated; only byte-verified PDFs and raster images render
  inline. HTML and SVG uploads remain downloads. PDF insertion requires a
  manual upload; source-link downloads are disabled. PDF text selection, search, pages and zoom remain available
  while writing around the same reader node.
- Native documents are stored as versioned JSON alongside a Markdown mirror.
  Existing Markdown documents open without rewriting stored content. Native
  formatting, table widths and media attributes survive drafts, saved history,
  JSON/ZIP export and import. A checksum prevents an older server's Markdown edit
  from accidentally resurfacing stale native content.
- Local drafts, conflict detection, recoverable trash and explicit saves remain
  part of the workflow. A failed local draft write is reported and prevents
  navigation until the document is saved. Imports remap both document references
  and attachment references when allocating new IDs.

Slash commands accept Chinese labels, pinyin initials/full pinyin, and English
aliases. Examples: `/ddm` or `/dmk` for a code block; `/yy`, `/cite` or `/quote`
for a blockquote; `/todo` or `/db` for a checklist; `/bg` for a table; `/gs` for
a formula; `/tp` for an image; and `/bt1`–`/bt3` for headings. Queries can combine
terms such as `/code block`, `/yy cite` or `/待办 checkbox`. Exact labels and
aliases rank first; matching ignores case and normalizes full-width input.
Choose with the arrow keys and Enter, or click a result. Unmatched/cancelled
queries remain ordinary document text.

Code blocks use locally bundled Maple Mono NL with distinct light/dark palettes.
Use the chevron to fold a block; its language, line count and first nonempty line
remain visible. Editing-mode folds save with the document and support undo;
reading-mode folds are temporary. The sun/moon button remembers the code theme
in this browser. Search reveals folded matches, and copying or Markdown export
always includes the full source. Native JSON/ZIP exports retain folding.
Long expanded scripts scroll within the block. See the
[code-block design research](code-block-design.md) for references and choices.

The interface uses white and gray surfaces, dark text, one blue interaction
accent, and a consistent Lucide icon set. Locally bundled Inter and variable
Noto Sans SC provide consistent Latin/Chinese type and intermediate weights;
platform sans-serif fonts remain fallbacks. Shared visual tokens give controls,
menus and panels a moderate corner-radius scale. The desktop editor sits on a
white document surface, while phone editing uses the available width.
Independent scrolling panes, a dismissible mobile drawer, and intrinsic image
sizing support both writing and PDF reading. Resource provenance and licenses
are documented in
[`workspace/static/THIRD_PARTY_ASSETS.md`](../workspace/static/THIRD_PARTY_ASSETS.md).

The sidebar keeps three main destinations and one tag-management entry. Its
desktop collapse control remembers your preference without remounting the
editor. Document rows show a title, a short preview, colored bookmarks and
relevant task status. The bookmark control sits immediately left of pin. Each
row shows two tags and an overflow count; clicking a tag filters the catalogue.
The same normalized label always receives the same color across rows, pickers
and the tag library. Labels remain readable without relying on color alone.

Manage a document's tags from the bookmark control beside pin, without opening
the document. Its **Document tags** tab has an explicit **New tag** form; creating
and adding a tag saves the association immediately. Enter also works directly
in the search field while suggestions are loading. Existing labels can be
selected, or removed from this document with their × control. These actions
update only tags, with a version check and history revision; unsaved body text
remains local. Matching local drafts advance to the new metadata revision. New
documents keep tags local until document save. The current document remains
accessible even if it is outside the filtered page.

The same entry's **Manage tags** tab supports renaming, merging and deleting
shared labels. Deletion previews the affected documents and removes only the
label association from active documents; it preserves document content and
history. Removing a tag from one document and deleting it across documents are
separate, explicitly named actions. Existing-body drafts survive these changes.

`论文` is the only built-in classification. It exists at zero usage, cannot be
deleted or renamed, and stays attached to paper materials. Blogs and other topics
are ordinary editable/removable tags. Older specialized records remain readable
as ordinary documents; explicit new writes/imports normalize non-paper kinds to
notes without erasing existing content or history.

The list's tag filter and searchable, paginated tag library include an untagged
view. Filtering preserves the open draft. Rename, merge or delete a tag through
the same management controls: preview the affected documents, then apply. Each
affected document retains a history revision; stale previews are rejected, and
each operation is limited to 100 active documents. Trash is excluded. See the
[navigation and tag design research](navigation-tags-design.md).

The [product-style research](product-style-design.md) records the Notion,
Feishu and Yuque references, typography audit and visual verification.

## Papers and Codex

Choose **New document → Paper materials** and manually upload a PDF. An optional
HTTPS source link is saved as attribution only; the server does not visit it or
download a PDF. A source URL alone cannot start import or analysis. The editor's
**Insert PDF** action also accepts local uploads only. Existing attachments and
external source links remain available.

The selected file is previewed before use. It can be replaced at any point before
insertion; replacing it invalidates the earlier extracted text and generated
notes. Browser-side PDF.js extraction reads the supplied local file in parallel with
upload,
up to 80 pages / 60,000 characters, with a bounded loading task. Optional Codex
analysis uses those extracted words, never a substitute HTML article or another
PDF. Textless/scanned PDFs can be archived and read without invented analysis.

Optionally run **AI 分析论文** to organize publication, authors, affiliations,
correspondence, labs and two research-field levels along with the concise brief.
Unsupported facts are marked for verification. The preview suggests one or two
field tags, selected by default; deselect any you do not want. Confirm the
title/author, insert into the editor, then save. Tags appear in the catalogue
after saving. Editing the title/author or optional source link retains the
analysis; replacing the PDF invalidates it. Only the final selected file is associated with the saved
document. Abandoned/replaced temporary imports move to recoverable attachment
trash. See [paper intake behavior](paper-intake.md).

Paper briefs default to `gpt-6.1-sol` with `medium` reasoning and a 150-second model timeout.
General document tasks default to `medium` with a 90-second timeout. Optional
private settings can override the paper model and budget independently. The
[brief template](../prompts/paper-brief.md) requests a one-sentence takeaway,
motivation, the method/differentiator, and evidence/limitations in about 400–700
Chinese characters. [Progress tracking](paper-progress.md) separates measured
upload/extraction from AI estimates calibrated with recent task durations.

Generated dossiers and assistant suggestions are previews. Importing a chosen
PDF creates an unassociated attachment; inserting a dossier creates unsaved
editor state. Normal save persists the document and links its selected PDF.
Lookup and analysis endpoints do not create document records. Publisher access
restrictions are not bypassed; manual upload is the fallback.

Codex runs in an empty temporary directory with explicit `--ephemeral` and
`--sandbox read-only` flags. Only the selected document or chosen public paper
material is supplied. The CLI may contact its configured model provider. Prompts,
responses, credentials, and personal documents are not written into source or logs.

AI skill/template standardization and later user-guided refinement are tracked in
[`TODO.md`](../TODO.md), after the overall interface and workflow design settles.

## Run

Runtime: Python 3.10–3.12 and its standard library. Browser assets and fonts are
vendored locally; the deployed application does not need Node.js or a CDN.

Copy `.env.example` to a private `.env` and configure:

- `WORKSPACE_DATA_DIR`: directory for the SQLite database and uploads, outside the source checkout.
- `WORKSPACE_SESSION_SECRET`: a long random secret.
- `WORKSPACE_HOST` / `WORKSPACE_PORT`: bind address and port (default port 5200).
- `WORKSPACE_SETUP_TOKEN`: a private random token required for first-run creation on a public listener.
- `WORKSPACE_COOKIE_SECURE`: enable when serving through HTTPS.
- `WORKSPACE_CODEX_BIN`: an optional installed Codex executable; leave empty to disable generation.
- `CODEX_HOME`: set this explicitly in the private service environment when Codex uses
  a custom configuration directory; the service does not inherit your interactive shell.
- `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`: configure these in the same private
  service environment when the selected model provider requires an egress proxy.
- `WORKSPACE_CODEX_MODEL` / `WORKSPACE_CODEX_REASONING_EFFORT`: optional general CLI overrides.
- `WORKSPACE_PAPER_CODEX_MODEL` / `WORKSPACE_PAPER_REASONING_EFFORT`: independent paper overrides, defaulting to `gpt-6.1-sol` and `medium`.
- `WORKSPACE_PAPER_ASSISTANT_TIMEOUT`: paper model timeout in seconds (default 150; bounded to 60–600).
- `WORKSPACE_PAPER_PROXY`: optional trusted HTTP CONNECT proxy for paper retrieval.
  The paper fetcher also recognizes `HTTPS_PROXY`; target DNS is validated and the
  tunnel uses a pinned public destination IP. Credentials in proxy URLs are unsupported.

Run `python3 workspace_server.py` and open `http://127.0.0.1:5200`.
The first-run form creates the only account. Passwords are chosen in the browser,
are salted and hashed, and are never included in configuration or source. Existing
accounts, cookies, documents, and backups are compatible with the document-focused UI.

Use the example service in `deploy/systemd/` for systemd. Keep its environment
file private, back up data before deploying, copy only source/static assets, and
verify `/healthz` and `/api/session` after a restart.

## Development and checks

The source checkout is separate from the live application's data. Install the
locked frontend dependencies and build the vendored assets:

```sh
npm ci
npm run build
make compile
make test
npx playwright install chromium
npm run test:browser
```

Browser tests start their own loopback server with disposable synthetic data.
They cover login, editor tools, math/code/tables, draft recovery and conflicts,
image/PDF attachment handling, paper drafting without automatic persistence,
native formatting and migration, table editing/resizing, block movement, Chinese
composition, draft/storage failures, concurrent saves, media proportions, and
responsive editing/PDF layout. A synthetic document with over 900 blocks checks
that typing avoids full-document Markdown serialization and retains PDF nodes. Screenshots are written under ignored `artifacts/`.

Rebuild `workspace/static/vendor/` after changing `web/` or library versions.
Keep `package-lock.json` and the bundled runtime dependency notices together.
The build also emits gzip copies of public text assets. The server negotiates
compression for GET/HEAD and falls back to the original if a compressed copy is stale.

When generation is enabled, check the actual running service configuration with
`python3 scripts/check_assistant.py --service personal-workspace.service` and
repeat with `--paper` to verify the paper settings. This
uses synthetic input and does not print credentials or process personal documents.
Timed-out assistant calls terminate the launcher and its child processes together.

`skills/personal-workspace-maintenance/SKILL.md` is the canonical maintenance
workflow. Run `make skill-sync` after changing it.

## Backups

`WORKSPACE_DATA_DIR=/path/to/private-data ./backup.sh /path/to/private-backups`
creates a SQLite-consistent snapshot and an archive of uploaded files. Both are
validated before retention pruning; the default retention is 14 days. Backup and
systemd timer examples are in `deploy/systemd/`. JSON exports omit credentials
and attachment binaries; complete archives include attachment bytes but never
account credentials.

## License

MIT. Bundled editor/rendering libraries, icons, and fonts retain their respective
notices in `workspace/static/vendor/THIRD_PARTY_LICENSES.txt`. Pinned resource
sources are listed in `workspace/static/THIRD_PARTY_ASSETS.md`.

## Document sharing

Use **分享** at the upper right of a document to generate a password-protected,
read-only snapshot on the independent sharing service (default port 5201).
Choose 1, 7, 30 days or permanent; every link gets a strong generated password
and an unpredictable URL identifier. Reset passwords, replace links or stop
sharing from the same dialog. Later private edits are not published automatically.
See [sharing setup, access controls and backup/restore](document-sharing.md).

## Compact editing space

The main formatting toolbar stays on one row. At narrow widths, scroll it
horizontally or tab to the next control; color, insertion and More menus remain
inside the visible editor area. Hover/focus descriptions still identify controls.
The title area uses less vertical space. The footer contains only **链接文档**
and **上报 Bug**, using the same size and alignment. Focus mode hides the footer;
exit focus to restore it. Opening a Bug report still uses a separate tab and
preserves the current draft. On phone layouts, returning to the document list
keeps the reporting entry available.

## Tab and indentation

While the text caret is in the editor, **Tab** indents and **Shift+Tab** outdents.
Paragraphs and headings use native block formatting (up to eight levels); selected
paragraphs change together. Lists nest under the previous item or move up a level.
Code uses four spaces and adjusts the complete selected lines without replacing
source text. Table cells keep next/previous-cell navigation, including adding a
row at the end. An unavailable indent/outdent at a boundary keeps editor focus.

Composition events are left to the input method. **Esc** returns focus from the
text surface to the paragraph-style selector, where Tab resumes normal toolbar
navigation. Other fields and read-only views keep their normal keyboard behavior.
The More menu uses the same indentation commands. Native JSON, archives, history
and shares preserve paragraph indentation. Markdown keeps the text; use a native
export to retain paragraph layout. Lists and code retain their structural/text
indentation in Markdown.
