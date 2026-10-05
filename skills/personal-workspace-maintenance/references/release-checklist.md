# Release and deployment checklist

Use this checklist for a source release or a Tencent Cloud deployment.

## Source

- Check git status and review the complete staged file list.
- Confirm data/, databases, uploads, backups, logs, .env, SSH files, server addresses, and personal content are ignored or absent.
- Run make compile (including `bash -n backup.sh`), make test, and node --check workspace/static/app.js.
- Compile tests/browser_smoke.py even when a Chromium binary is unavailable; syntax validation keeps the browser gate executable in CI.
- For browser changes, run tests/browser_smoke.py in an isolated Playwright environment against synthetic temporary data. Syntax checks alone do not prove that navigation or page startup works.
- After restarting, allow a bounded startup interval and retry health probes before deciding that the deployment failed; never treat systemd active state alone as proof of readiness.
- Run an HTTP smoke test for /healthz, /api/session, login/setup, content CRUD, and file upload when applicable.
- When list APIs change, verify total/next-cursor metadata and a browser load-more path beyond the first page; selections and the active editor must remain usable after append.
- When list filters or sorting change, verify status/tag/search filters and every supported sort across multiple cursor pages, reject a cursor reused with a different sort, and confirm the browser preserves the server order.
- When bounded auxiliary views change, verify review and calendar totals, calendar items beyond the compact day view, trash load-more controls, and full-archive parent/tag candidates.
- When hierarchy, related-content, file-association, or tag pickers change, verify server-side search, load-more behavior, current-selection preservation, and rejection of self/descendant parent candidates.
- When file-space listing changes, verify server-side search, total/offset metadata, load-more behavior, and attachment lists after upload or deletion.
- When file association changes, verify linked/unlinked filters, filtered byte totals, authenticated attach/detach, and that a deleted item leaves its file independently manageable.
- Verify first-run protection on synthetic servers: a non-loopback bind without `WORKSPACE_SETUP_TOKEN` must reject setup, a loopback bind may allow local setup, and a configured token must reject incorrect values and accept the correct one. Check the bounded server's request timeout and queue attributes.
- When import/export changes, test a synthetic export with relationships and verify the import is transactional and excludes credentials and file binaries.
- When complete archive export/import changes, inspect the ZIP manifest and attachment bytes, restore a linked file through the archive path, reject traversal/symlink/size/hash tampering, and verify a failed import leaves no database rows or staged files.
- When export or list-scale behavior changes, verify JSON export size/row limits return a clear bounded error, complete archive export remains available, and the workflow SQLite indexes exist after initialization.
- When archive timeline handling changes, verify valid item/file timestamps and mapped activity survive import, while malformed timestamps or unknown attachment IDs leave no partial rows.
- When hierarchy import changes, include a self-parent and a multi-item cycle fixture and verify both are rejected with no partial items.
- When deletion behavior changes, test the full trash lifecycle: active queries hide deleted rows, restore returns them, and permanent deletion removes the row and file bytes.
- When hierarchy deletion changes, restore a parent with active children, verify unchanged links return, explicit parent edits win, and cycle attempts are skipped safely.
- When upload behavior changes, submit an invalid item association and verify no staged orphan file remains after the rejected request.
- When content deletion changes, verify attached file bytes remain independently visible and can be restored or purged through the file-space recycle bin.
- When editor behavior changes, verify local drafts are revision-scoped, restorable or dismissible, and cleared after a successful save or deletion.
- When work-log dates change, verify additive migration on a database copy, strict leap-date validation, title renames, exact server-side date filtering, history/export/import coverage, and browser-local date navigation.
- When session or “today” boundaries change, test that legacy unversioned cookies are rejected after the session-version migration and that stats/review use an explicitly supplied browser civil date.
- If `WORKSPACE_CODEX_BIN` is configured, verify the CLI version and that its help still recognizes the explicit `--ephemeral` and `--sandbox read-only` flags, then run a synthetic assistant smoke test; never use a personal document as the fixture or rely on ignored profile keys for isolation.
- When assistant UI changes, verify that generated text is not persisted until an explicit insert and save action.
- When assistant calls are slow or unavailable, verify the entry is disabled or visibly busy and repeated clicks do not create concurrent calls.
- Update the README when the user-visible behavior or deployment contract changes.
- Update the project skill and maintenance log when the workflow or an operational invariant changes.

## Database and data

- Make a copy or backup of the production data directory before a schema migration.
- When scheduled backups are enabled, run `backup.sh` once, verify both the SQLite snapshot and file archive exist, run `PRAGMA integrity_check` on the snapshot, list the archive contents, and confirm the retention setting is applied.
- Verify migrations are additive or have a tested rollback path.
- Keep production data in the configured data directory, outside the Git checkout.
- Never use a production password or personal document as a test fixture.

## Deployment

- Transfer only the intended source files and static assets.
- For systemd distributions, review the service example's dedicated user, read-only system paths, writable data allowlist, and loopback/HTTPS boundary before enabling it.
- Check the port and existing services before restarting.
- Run systemctl is-active personal-workspace.service.
- Check /healthz, /api/session, ss -lntp, and recent journalctl output.
- If HTTPS is enabled, verify `WORKSPACE_COOKIE_SECURE=true` and inspect the login response for a `Secure` session cookie; keep direct HTTP restricted to a trusted private network.
- Probe `HEAD /healthz` and `HEAD /static/app.js` when the service is behind a monitor or reverse proxy.
- If a backup timer is enabled, check `systemctl list-timers`, the latest successful run, and the backup directory's free space.
- Record the deployed commit and any cloud security-group or HTTPS requirement.

## GitHub

- Use a private-safe commit and a focused message.
- Push only after the remote owner and repository are known.
- Never put credentials in the remote URL or commit history.
- If a repository secret was exposed, rotate it before continuing.
