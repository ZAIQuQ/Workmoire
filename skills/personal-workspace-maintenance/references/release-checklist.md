# Release and deployment checklist

Use this checklist for a source release or a Tencent Cloud deployment.

## Source

- Check git status and review the complete staged file list.
- Confirm data/, databases, uploads, backups, logs, .env, SSH files, server addresses, and personal content are ignored or absent.
- Run make compile (including `bash -n backup.sh`), make test, and node --check workspace/static/app.js.
- Compile tests/browser_server.py and syntax-check tests/browser.spec.cjs so the browser gate remains executable.
- For browser changes, run npm run test:browser in its isolated Playwright environment against synthetic temporary data. Syntax checks alone do not prove that navigation or page startup works.
- After restarting, allow a bounded startup interval and retry health probes before deciding that the deployment failed; never treat systemd active state alone as proof of readiness.
- Run an HTTP smoke test for /healthz, /api/session, login/setup, content CRUD, and file upload when applicable.
- Verify first-run protection on synthetic servers: a non-loopback bind without `WORKSPACE_SETUP_TOKEN` must reject setup, a loopback bind may allow local setup, and a configured token must reject incorrect values and accept the correct one. Check the bounded server's request timeout and queue attributes.
- When import/export changes, test a synthetic export with relationships and verify the import is transactional and excludes credentials and file binaries.
- When deletion behavior changes, test the full trash lifecycle: active queries hide deleted rows, restore returns them, and permanent deletion removes the row and file bytes.
- When editor behavior changes, verify local drafts are revision-scoped, restorable or dismissible, and cleared after a successful save or deletion.
- If `WORKSPACE_CODEX_BIN` is configured, verify the CLI version and that its help still recognizes the explicit `--ephemeral` and `--sandbox read-only` flags, then run a synthetic assistant smoke test; never use a personal document as the fixture or rely on ignored profile keys for isolation.
- Run `python3 scripts/check_assistant.py --service personal-workspace.service` after deployment so the exact service configuration, not the interactive shell, proves the assistant works. Verify timeout cleanup includes the npm launcher's native child.
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
- Check the port and existing services before restarting.
- Run systemctl is-active personal-workspace.service.
- Check /healthz, /api/session, ss -lntp, and recent journalctl output.
- Probe `HEAD /healthz` and `HEAD /static/app.js` when the service is behind a monitor or reverse proxy.
- Verify the installed backup script is executable by the service user, run the backup systemd job, and inspect its exit status and snapshot artifacts.
- If a backup timer is enabled, check `systemctl list-timers`, the latest successful run, and the backup directory's free space.
- Record the deployed commit and any cloud security-group or HTTPS requirement.

## GitHub

- Use a private-safe commit and a focused message.
- Push only after the remote owner and repository are known.
- Never put credentials in the remote URL or commit history.
- If a repository secret was exposed, rotate it before continuing.

## Rich documents and papers

- Rebuild and ship locally vendored editor/math assets, icons, and fonts together; retain license notices and the dependency lockfile. For reused artwork, record the upstream commit and adaptations, verify local asset loading, and check intrinsic proportions and usable controls at phone, tablet, laptop, and desktop widths.
- Verify inline media magic bytes, authentication, same-origin frame policy, and PDF byte ranges; HTML/SVG must remain downloads.
- Verify title, DOI, and arXiv lookup using public metadata, and test private/redirect destinations using synthetic fixtures.
- Verify generated paper text preserves the source and uncertainty notice, and creates no records before explicit insertion/save.
- Verify concurrent saves keep current typing, stale local drafts require manual merging, and mobile editing has no horizontal page overflow.
- If source retrieval requires an egress proxy, configure it only in the private environment file and test a public source through pinned DNS before deploying.

## Native editor and deeper paper generation

- Verify additive native-document columns on a private copy before production migration; compare existing content and account state without printing either.
- Exercise native marks, list/task nesting, tables and image widths through save/reload, history, conflicts, local drafts and JSON/ZIP import. Check stale mirror hashes and remapped document/file references.
- Verify real keyboard input, Chinese composition, rich HTML paste, slash menus, block drag/undo and long documents. Confirm typing does not serialize all Markdown or recreate PDF frames.
- Verify draft quota failures stay visible and do not silently discard edits.
- Verify gzip GET/HEAD negotiation, disabled gzip and stale-copy fallback. Retain notices for the bundled runtime dependency graph.
- Run the exact-service assistant check with `--paper` as well as the general mode. Use a public-paper or synthetic evidence fixture, confirm the reasoning budget and truthful source scope, and do not persist acceptance content into personal documents.
