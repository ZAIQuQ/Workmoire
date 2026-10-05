# Workmoire · 拾序

A private, single-user web workspace for collecting research notes, paper
outlines, project plans, work logs, and related files.

The first release is deliberately small and self-hostable. It uses Python's
standard library, SQLite, and a browser client with no build step. The
application is suitable for a personal server and can be extended without
introducing a large runtime dependency stack.

## Features

- One account with password setup and password changes.
- Dashboard with recent work, content counts, quick capture actions, an inbox queue with one-click promotion, and deadline cards that can be marked complete in place.
- A dedicated daily review queue groups inbox items, overdue work, today's deadlines, and stale active content with direct open, promote, and complete actions.
- A month calendar brings project, paper, and work-log deadlines into one navigable planning view.
- A read-only relationship map shows hierarchy and cross-links together; nodes open the original content without exposing bodies through the graph endpoint.
- Global quick capture via the dashboard or Ctrl/⌘ + Shift + N puts a thought directly into the inbox.
- Unsubmitted quick captures can be restored or cleared from browser-local drafts; they are never uploaded automatically.
- Work logs keep a separate civil date from their title, so renaming a log does not lose its day; the daily action reopens the first log for that date and a day may contain multiple logs.
- The dashboard activity timeline links back to active content and uploaded files.
- Existing notes, project plans, papers, and logs can be saved as a new inbox copy for reuse as a template.
- A focus mode hides navigation while writing long papers, plans, or logs.
- Separate spaces for notes, projects, papers, and work logs.
- Change an item's content type in the editor so a captured note can become a project, paper, or work log without re-entering it.
- Markdown editing with a safe client-side preview, including headings, task lists, inline code, emphasis, and HTTPS links. Task-list checkboxes can be toggled in preview and remain an unsaved editor change until you explicitly save.
- Task-list progress appears in content lists and the editor, so project and paper checklists remain scannable without opening each item.
- Status, priority, due date, tags, and server-side search. Status/tag filters
  and all list sorts are evaluated across the full archive before cursor
  pagination, so “highest priority”, “earliest due”, and title order do not
  silently stop at the first page.
- Global search covers content and uploaded files, including a file's associated content title.
- Global search shows a matching context preview and can be narrowed by content type or status.
- Search ranks title matches ahead of summaries, tags, and body-only matches so a precise idea is easier to recover.
- Hierarchical relationships between related notes, projects, papers, and logs.
- Clickable parent and child links make those relationships navigable from the editor.
- Add reversible many-to-many links between any active notes, projects, papers, and logs to connect ideas across the hierarchy.
- Filter and sort each content space by tags, priority, deadlines, or title without leaving the current workspace.
- Content spaces use stable cursor pagination with an explicit load-more affordance, so a growing archive remains discoverable beyond the first page.
- Work-log spaces can filter by an exact \`YYYY-MM-DD\` date and move between days without relying on UTC timestamps. Dashboard due dates and daily review use the browser's local civil date explicitly, avoiding a server-timezone mismatch.
- Select several items in a content space to change their status in one transaction or move them to the recoverable trash; bulk actions are authenticated and limited to 100 items.
- Recoverable deletion with a private trash area for content and uploaded files; safe restores retain unchanged hierarchy links when the original parent is available.
- File space uses server-side search and load-more pagination, so large attachment archives remain navigable without loading every row at once.
- Trashed items stay out of search, active statistics, and item exports until restored.
- Pin important papers, projects, or notes so they stay visible in lists and the dashboard.
- Keep unsaved edits as browser-local drafts, with an explicit restore or ignore action.
- Detect stale saves from another tab or device and preserve the unsaved version as a local draft before loading the newer server copy.
- Keep up to 100 saved pre-edit versions per item, with an explicit review and restore path.
- Private file storage with a 64 MB per-file limit and optional links from files to notes, projects, papers, or logs.
- Search the file space by filename or the title of its associated note, project, paper, or log.
- One-click JSON export of notes, metadata, saved revisions, activity history, and cross-links (without passwords).
- Transactional JSON import that rebuilds hierarchy and cross-links without importing credentials or file binaries.
- Signed, expiring login cookies and basic login rate limiting.
- SQLite WAL mode and a small activity trail.
- Optional local Codex整理助手，默认关闭，不上传内容到外部服务。
- When explicitly enabled, the assistant receives the selected item's title, summary, tags, and body through the local read-only CLI context.
- Assistant results can be explicitly inserted into the summary or appended to the body; generation never saves automatically.
- Docker and systemd friendly deployment.

## Run locally

Copy .env.example to .env, set a long random session secret, and run:

    python3 workspace_server.py

Open http://127.0.0.1:5200. The first visit asks you to create the only
account. The optional `.env` file is loaded automatically and must stay private.
When the service is reachable beyond localhost, set a strong
`WORKSPACE_SETUP_TOKEN` in `.env` before the first visit. The server refuses
first-run setup on a non-loopback bind without that token, so an unauthenticated
visitor cannot claim the only account. Generate one with
`python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`; keep it outside
the repository. If a reverse proxy exposes a loopback-bound service, configure
the token too because the application cannot infer the proxy's public reach.

## Docker

Copy .env.example to .env and run:

    docker compose up -d --build

The named volume stores the database and uploaded files. Back up that volume
before upgrading or moving the service.
The JSON export contains file metadata; use `backup.sh` when the uploaded file
contents themselves must be migrated.

`backup.sh` writes a SQLite-consistent database snapshot and a compressed file
archive. It retains the last 14 days by default; set
`WORKSPACE_BACKUP_RETENTION_DAYS` to change that policy. A generic systemd
service and timer are provided in `deploy/systemd/*.example`. Copy them into
your systemd configuration, replace the example user and paths, then enable
the timer. Keep the backup directory outside the Git checkout.

## Project maintenance

The repository includes a Codex maintenance skill at `skills/personal-workspace-maintenance`. It defines the public/private data boundary, testing gates, deployment checks, and GitHub release workflow. When a maintenance rule changes, update the skill and its maintenance log in the same commit, then run `make skill-sync`.

## Production notes

The service binds to the configured host and port. If it is reachable from
the public internet, put it behind HTTPS or a private network and restrict
the inbound security-group rule to trusted addresses. Do not commit your
production .env, data/, database, uploads, logs, or backups.

The first-run account setup fails closed without `WORKSPACE_SETUP_TOKEN` on
non-loopback binds. Keep the token configured even when a reverse proxy makes
a loopback-bound process publicly reachable. The built-in threaded server uses
a 30-second request socket timeout and an explicit accept queue; keep a
production HTTPS reverse proxy or private network in front of it for stronger
connection and TLS controls.

The project is intentionally independent of any existing service on the
machine. Choose a free port and data directory when deploying beside another
application.

### Optional local Codex assistant

The editor can ask a locally installed Codex CLI to summarize, outline, review,
or suggest next steps. It is disabled unless `WORKSPACE_CODEX_BIN` points to an
installed executable. Workmoire invokes only `codex exec` in an ephemeral,
read-only mode, passes the selected document through standard input, and does
not save the response. The server must have its own Codex authentication if
this option is enabled; the public repository contains no credentials.

On a Linux server without root package access, install it for the service user:

    npm install --prefix "$HOME/.local" @openai/codex@alpha
    export WORKSPACE_CODEX_BIN="$HOME/.local/node_modules/.bin/codex"
    export WORKSPACE_CODEX_REASONING_EFFORT=low

Workmoire defaults to the low reasoning setting so a browser request remains
responsive; set `WORKSPACE_CODEX_MODEL` or choose `medium`, `high`, or `xhigh`
when a private deployment has a longer assistant timeout. Keep the CLI's own
authentication files in that user's home directory and outside the repository.

## License

MIT. See LICENSE.
