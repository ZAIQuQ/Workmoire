---
name: personal-workspace-maintenance
description: Maintain this private single-user workspace as a public, reproducible open-source project.
---

# Workmoire Maintenance

Use this skill for changes to the Workmoire source, tests, deployment, GitHub synchronization, runtime data boundaries, or the project's own maintenance workflow. It applies when a request mentions this project, its Tencent Cloud service, its public repository, or an optimization to the workflow.

## Core invariants

- The Git repository is public-safe source. Never commit personal notes, papers, work logs, uploaded files, SQLite databases, backups, production .env files, server addresses, usernames, SSH material, access tokens, cookies, logs, or generated runtime state.
- Runtime data stays outside the checkout in the configured WORKSPACE_DATA_DIR. Treat the database and file directory as user data and back them up before schema changes or destructive operations.
- Unsaved editor drafts are browser-local convenience data. Matching drafts may be restored directly; stale drafts remain visible with an explicit warning and require a deliberate restore action, never automatic application. They stay local by default; only an explicit assistant action may send the current selected text to the configured local Codex, and that text must never enter repository files, server logs, or exports automatically.
- Keep normal content and file deletion reversible through the authenticated trash area. Permanent deletion must be a separate, explicit operation and must remove the corresponding file bytes.
- Keep batch organization actions authenticated, bounded to a small explicit selection, and transactional. Batch status changes must leave item history; batch trash must remain reversible and detach affected hierarchy links without exposing partial results.
- Keep the batch-selection affordance visible before any item is selected; reveal destructive or state-changing actions only after selection so the fast path stays discoverable without making accidental changes easy.
- Keep the application single-user unless the user explicitly changes that product decision. Passwords are set through the first-run page and are never placed in source, documentation, chat, or deployment commands.
- Protect first-run setup with `WORKSPACE_SETUP_TOKEN` whenever the service is reachable beyond localhost. Keep the token in the private environment file and never commit or print it in deployment logs.
- Enforce the first-run boundary in code: a non-loopback listener without `WORKSPACE_SETUP_TOKEN` must return an error before creating the account, and `/api/session` must expose that token requirement so the setup form cannot silently omit it. A reverse proxy can make a loopback bind public, so configure the token there too.
- Keep direct HTTP connection handling bounded: the custom server must use daemon worker threads, an explicit request queue, and a finite socket read timeout. Prefer HTTPS termination and stronger rate/connection controls at a production reverse proxy.
- Protect edits against silent multi-tab overwrites: clients send the last `updated_at` they loaded, and the server returns the current item with `409` on a stale base. Preserve the user's unsaved changes as a local draft before offering to load the newer server version.
- Treat every authenticated session cookie as versioned state: reject legacy cookies without a `session_version`, and compare the version with SQLite so password changes revoke all prior sessions. Mutations that affect list order, including pinning, must advance `updated_at` and participate in stale-edit protection.
- Keep the service independent of other applications on the server. Discover a free port before changing it, preserve existing services, and verify the service health after every deployment.
- Keep the project reproducible from a clean checkout. Prefer Python standard-library code and documented Docker/systemd paths unless a dependency has a clear user-facing benefit.
- Keep the local Codex assistant disabled unless `WORKSPACE_CODEX_BIN` is explicitly configured on the private server. It may receive only the selected document through standard input, must run in ephemeral read-only mode, and must never expose arbitrary command execution or persist prompts and responses. Use a bounded reasoning setting by default so a web request remains responsive; make model and reasoning overrides explicit private configuration.
- Treat the assistant CLI flags as the security boundary: pass `--ephemeral` and `--sandbox read-only` explicitly on every invocation, and do not rely on profile keys that the installed CLI may ignore. When the CLI is upgraded, verify its version, help output, and a synthetic invocation before enabling it for personal content.
- Treat assistant output as a user-reviewed suggestion: display it without mutation first, require an explicit insert action, keep the result in the unsaved editor state, and send it to persistent storage only through the normal save path.
- Treat imports as user-data migrations: accept only the versioned Workmoire export format, run them in one transaction, rebuild relationships through an ID map, and never import credentials or file binaries.
- Validate imported hierarchy graphs before insertion; reject self-parenting and cycles without leaving partial rows. Keep cursor pagination's sort key in the cursor, and apply status, tag, search, and sort filters on the server before returning a page so a growing archive is never represented by a first-page approximation.
- Back up the configured data directory before schema or deployment changes. Use `backup.sh` (or an equivalent SQLite backup API) for the database and archive uploaded files; keep backups outside the checkout and apply an explicit retention policy.
- Treat a backup as valid only after the SQLite snapshot passes `PRAGMA integrity_check` and the uploaded-file archive can be listed successfully; perform those checks before retention pruning.
- Keep automated public-boundary checks generic: never embed a real deployment address, personal domain, or other private identifier as a denylist fixture. Use synthetic patterns in CI and review actual addresses, emails, and paths before publishing.
- Keep search ranking deterministic and privacy-preserving: rank metadata matches ahead of body-only matches without exposing deleted content or adding an external indexing service.
- Open search and activity results through an authenticated item lookup rather than assuming the current client list contains the result; navigation must remain correct when list views are bounded or filtered.
- Keep growing content spaces discoverable with stable cursor pagination and an explicit load-more control; bounded list responses must report their total and never silently imply that only the first page exists.
- Apply the same visibility rule to review queues, calendars, trash, hierarchy candidates, and tag filters: expose totals or a load-more path when a response is bounded, and do not let the browser's first-page cache hide valid parents, links, or recoverable data.
- Treat a save with no changed revision fields as a no-op: preserve `updated_at`, activity history, and the revision list instead of creating a fake edit.
- Store work-log dates as validated civil \`YYYY-MM-DD\` fields independent of editable titles and UTC timestamps. Migrations may recover only exact legacy date titles, must preserve ambiguous titles as undated, and date filters must operate on the full server-side archive.
- When a browser-facing summary or review queue needs “today,” pass the browser's validated civil date explicitly to the API; do not let server timezone defaults silently disagree with local-day navigation.

## Working workflow

1. Read the repository instructions and inspect the current branch, service unit, data path, port, and resource headroom before editing.
2. Work in the Git checkout. Keep production data in a separate ignored directory. Make schema changes backward-compatible and test them against a copy of the database before touching production. Verify that deleted content is hidden from active queries and can be restored.
3. Treat the repository skill at skills/personal-workspace-maintenance/SKILL.md as the source of truth for this workflow. If a workflow invariant or repeatable operational lesson changes, update this skill and its relevant reference in the same change.
4. Run the project's checks before deployment: make compile (including `bash -n backup.sh`), make test, node --check workspace/static/app.js, and an HTTP smoke test covering health, first-run session state, authentication, content CRUD, file upload, and assistant-disabled behavior when those paths changed.
5. Run a public-repository scan before staging and again before pushing. Check for IP addresses, personal email addresses, private paths, credentials, private keys, tokens, cookies, database files, uploads, logs, and non-placeholder production settings. Review the staged file list manually.
6. Deploy only source files and static assets to the configured application directory. Do not copy .env, data/, backups, or a whole working directory. Restart the systemd service only after the new files are in place, then verify systemctl is-active, /healthz, /api/session, the listening port, and recent journal output. If backups are enabled, verify the timer, one completed snapshot, SQLite integrity, archive readability, and retention behavior without exposing backup contents.
7. Commit with a focused message that describes the user-facing behavior. Push only to the intended GitHub repository and branch. If the remote is absent or the authenticated account is unclear, stop before creating a new remote or publishing.
8. Report what changed, what was tested, the public repository state, the deployment state, and any remaining setup such as a cloud security-group rule or HTTPS.

## Updating this skill

Update the skill when a workflow rule, security boundary, deployment invariant, data migration practice, or verification gate changes. Keep feature-specific implementation details in the source or focused references instead of expanding this file with a changelog. Add a short dated entry to references/maintenance-log.md for each such workflow improvement, including the reason and the files changed.

After editing the repository copy, run python3 scripts/sync_skill.py to mirror it into the active Codex skill directory. Validate it with the skill creator's quick_validate.py before reporting completion. The mirror is a generated local convenience; the repository copy remains canonical and must be committed.

## References

- Read references/release-checklist.md before a GitHub release or production deployment.
- Read references/maintenance-log.md when deciding whether a new workflow lesson is already recorded.
