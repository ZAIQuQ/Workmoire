# Workmoire · 拾序

A quiet, single-user space for academic notes, paper reading, and connected ideas.
The interface has three primary destinations: all documents, paper references,
and document relationships. Planning notes, research ideas, todos, and self-review
checklists are document templates rather than separate applications.

## Writing

- CodeMirror Markdown editor with undo/redo, search, indentation, keyboard shortcuts,
  a compact formatting toolbar, document outline, focus mode, and writing/split/reading views.
- LaTeX inline and display formulas, highlighted code blocks, tables, quotations,
  clickable task lists, symbols, images, and an embedded PDF.js reader with
  selectable text, search, page navigation, and zoom. The reader keeps its place
  while you type beside it.
- Paste or drop images, upload attachments, or explicitly import a public HTTPS PDF.
  Uploads remain authenticated; only byte-verified PDFs and raster images can render
  inline. HTML and SVG remain downloads. PDF byte ranges support browser reading.
- Add document references through the picker and see their relationships in a
  simple neighborhood view. Tags and full-text search help retrieve older work.
- Local drafts, optimistic conflict detection, saved version history, recoverable
  trash, JSON import/export, and a complete archive including attachments.

The warm paper layout uses one consistent Lucide icon set, locally hosted Geist
and Noto Sans SC variable fonts, and two reading illustrations adapted from Open
Doodles. Text hierarchy, independent scrolling panes, a dismissible mobile drawer,
and intrinsic image sizing keep both writing and PDF reading comfortable. Resource
provenance and license details are in
[`workspace/static/THIRD_PARTY_ASSETS.md`](workspace/static/THIRD_PARTY_ASSETS.md).

## Papers and Codex

Enter a title, DOI, arXiv link, or a publisher abstract-page link. Title lookup
combines arXiv and Crossref results. Confirm the paper before generating a dossier.
The service retrieves only public metadata and abstracts, then invokes the explicitly
configured Codex CLI. It preserves the source URL and labels the missing full-text
verification. It does not claim to have read a PDF from metadata alone.

Generated dossiers and assistant suggestions are previews. Inserting them into the
editor does not save them; use the normal save action to persist a document. Paper
lookup and drafting endpoints do not write documents or attachments. PDF downloads
happen only through an explicit import action; publisher access restrictions are
not bypassed. A source can lack metadata, disallow embedding, or be unavailable;
use its DOI/title or upload a locally obtained PDF in those cases.

Codex runs in an empty temporary directory with explicit `--ephemeral` and
`--sandbox read-only` flags. Only the selected document or chosen public paper
metadata is supplied. The CLI may contact its configured model provider. Prompts,
responses, credentials, and personal documents are not written into source or logs.

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
- `WORKSPACE_CODEX_MODEL` / `WORKSPACE_CODEX_REASONING_EFFORT`: optional CLI overrides.
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
relationships, reversible deletion, local visual assets, image proportions, and
responsive editing/PDF layout. Screenshots are written under ignored `artifacts/`.

Rebuild `workspace/static/vendor/` after changing `web/` or library versions.
Keep `package-lock.json` and the bundled third-party notices together.

When generation is enabled, check the actual running service configuration with
`python3 scripts/check_assistant.py --service personal-workspace.service`. This
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
notices in `workspace/static/vendor/THIRD_PARTY_LICENSES.txt`. Illustration notices
and pinned upstream sources live in `workspace/static/illustrations/`.
