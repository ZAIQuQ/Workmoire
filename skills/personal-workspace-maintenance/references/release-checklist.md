# Release and deployment checklist

Use this checklist for a source release or a Tencent Cloud deployment.

## Source

- Check git status and review the complete staged file list.
- Confirm data/, databases, uploads, backups, logs, .env, SSH files, server addresses, and personal content are ignored or absent.
- Run make compile and make test.
- For browser changes, run tests/browser_smoke.py in an isolated Playwright environment against synthetic temporary data. Syntax checks alone do not prove that navigation or page startup works.
- After restarting, allow a bounded startup interval and retry health probes before deciding that the deployment failed; never treat systemd active state alone as proof of readiness.
- Run an HTTP smoke test for /healthz, /api/session, login/setup, content CRUD, and file upload when applicable.
- When import/export changes, test a synthetic export with relationships and verify the import is transactional and excludes credentials and file binaries.
- When deletion behavior changes, test the full trash lifecycle: active queries hide deleted rows, restore returns them, and permanent deletion removes the row and file bytes.
- When editor behavior changes, verify local drafts are revision-scoped, restorable or dismissible, and cleared after a successful save or deletion.
- If `WORKSPACE_CODEX_BIN` is configured, run a synthetic assistant smoke test and verify the CLI version; never use a personal document as the fixture.
- When assistant UI changes, verify that generated text is not persisted until an explicit insert and save action.
- Update the README when the user-visible behavior or deployment contract changes.
- Update the project skill and maintenance log when the workflow or an operational invariant changes.

## Database and data

- Make a copy or backup of the production data directory before a schema migration.
- When scheduled backups are enabled, run `backup.sh` once, verify both the SQLite snapshot and file archive exist, and confirm the retention setting is applied.
- Verify migrations are additive or have a tested rollback path.
- Keep production data in the configured data directory, outside the Git checkout.
- Never use a production password or personal document as a test fixture.

## Deployment

- Transfer only the intended source files and static assets.
- Check the port and existing services before restarting.
- Run systemctl is-active personal-workspace.service.
- Check /healthz, /api/session, ss -lntp, and recent journalctl output.
- Probe `HEAD /healthz` and `HEAD /static/app.js` when the service is behind a monitor or reverse proxy.
- If a backup timer is enabled, check `systemctl list-timers`, the latest successful run, and the backup directory's free space.
- Record the deployed commit and any cloud security-group or HTTPS requirement.

## GitHub

- Use a private-safe commit and a focused message.
- Push only after the remote owner and repository are known.
- Never put credentials in the remote URL or commit history.
- If a repository secret was exposed, rotate it before continuing.
