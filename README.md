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
- Global quick capture via the dashboard or Ctrl/⌘ + Shift + N puts a thought directly into the inbox.
- Unsubmitted quick captures can be restored or cleared from browser-local drafts; they are never uploaded automatically.
- The daily log action reopens the current day's log when one already exists, avoiding duplicate daily entries.
- The dashboard activity timeline links back to active content and uploaded files.
- Existing notes, project plans, papers, and logs can be saved as a new inbox copy for reuse as a template.
- A focus mode hides navigation while writing long papers, plans, or logs.
- Separate spaces for notes, projects, papers, and work logs.
- Markdown editing with a safe client-side preview, including headings, task lists, inline code, emphasis, and HTTPS links.
- Status, priority, due date, tags, and server-side search.
- Global search covers content and uploaded files, including a file's associated content title.
- Hierarchical relationships between related notes, projects, papers, and logs.
- Clickable parent and child links make those relationships navigable from the editor.
- Filter and sort each content space by tags, priority, deadlines, or title without leaving the current workspace.
- Recoverable deletion with a private trash area for content and uploaded files.
- Trashed items stay out of search, active statistics, and item exports until restored.
- Pin important papers, projects, or notes so they stay visible in lists and the dashboard.
- Keep unsaved edits as browser-local drafts, with an explicit restore or ignore action.
- Private file storage with a 64 MB per-file limit and optional links from files to notes, projects, papers, or logs.
- Search the file space by filename or the title of its associated note, project, paper, or log.
- One-click JSON export of notes, metadata, and activity history (without passwords).
- Transactional JSON import that rebuilds item relationships without importing credentials or file binaries.
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
When the service is reachable beyond localhost, set `WORKSPACE_SETUP_TOKEN` in
`.env` before the first visit. The token protects the one-time account setup.

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
