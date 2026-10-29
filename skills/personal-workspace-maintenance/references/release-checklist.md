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
- When label organization changes, verify search/pagination, case/full-width reuse, contextual suggestions, keyboard/Chinese composition, read-only controls, and edits during saves. Navigation/filtering must preserve drafts; rename/merge previews must be bounded, reject stale versions and retain original revisions without changing unrelated content.
- For catalogue bookmarks, verify label/pin placement, explicit label-only persistence, matching-draft rebasing, body-save interlocks, cancelled changes and new local drafts. Check built-in zero-count entries, immutable names, legacy paper filters, protected paper membership and preservation of custom labels; compare colors across list/picker/library and phone layouts.
- Exercise visible new-tag creation and immediate Enter before suggestion responses; then rename and delete through the same row entry. Check current-document removal versus shared deletion, preview cancellation, stale or wrong-operation tokens, built-in protection, and consecutive mutations with an unsaved native body.
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
- For sharing, verify both listeners and health endpoints, a dedicated public user/environment, read-only publication access, actual setgid inheritance with the publisher in the sharing group, and denied access to the publisher key/private database. Exercise password gates, all expiry options, reset/revoke/trash invalidation, persistent failure limits, scoped media/ranges and forbidden workspace routes. Test rich/PDF reading and dialogs at phone widths using synthetic documents; never publish private documents for a smoke check.
- Include sharing data in the actual scheduled backup job's environment. Run it after deployment, verify SQLite/archive integrity and a synthetic restore that preserves link/password/media while excluding reader sessions. Document the possibility of old backups reactivating later-revoked links.

## GitHub

- Use a private-safe commit and a focused message.
- Use the standing authorization to synchronize verified deployments to `ZAIQuQ/Workmoire/main`; update version/changelog and both README languages, push the commit and immutable version tag, create its Release, and inspect CI. Do not treat local commits as publication.
- Verify the deployed `REVISION`, package version and release tag agree. If authorization is configured but credentials are missing, prepare all source/deployment work and request a browser login without collecting tokens in chat.
- Never put credentials in the remote URL or commit history.
- If a repository secret was exposed, rotate it before continuing.

## Rich documents and papers

- Rebuild and ship locally vendored editor/math assets, icons, and fonts together; retain license notices and the dependency lockfile. For reused artwork, record the upstream commit and adaptations, verify local asset loading, and check intrinsic proportions and usable controls at phone, tablet, laptop, and desktop widths.
- For typography or shared visual-token changes, inspect the actual Latin/Chinese glyph fonts and weight ranges in a browser; check both main UI and PDF controls, narrow layouts, focus indicators, and local font loading. Keep math/code faces and uploaded PDF typography appropriate to their content.
- Verify inline media magic bytes, authentication, same-origin frame policy, and PDF byte ranges; HTML/SVG must remain downloads.
- Verify that optional source links never trigger network requests and retired online paper lookup/PDF import endpoints reject old clients before retrieval.
- Verify generated paper text preserves the source and uncertainty notice, and creates no records before explicit insertion/save.
- Verify exactly two creation choices and no obsolete template/Blog shortcuts. Exercise manual PDF upload, URL-only gating, optional source attribution, replacement after upload, editor PDF insertion, legacy external blocks, and cancel cleanup. Check original bytes and selected-file text reach the right document/model, no web text replaces a supplied PDF, and legacy notes/tags remain editable.
- Before a document-kind CHECK expansion, rehearse the migration on a private database copy and compare record digests, foreign keys and sequence state. Ensure the deployment ships the new parser/migration modules and prompt resources before restarting.
- Verify concurrent saves keep current typing, stale local drafts require manual merging, and mobile editing has no horizontal page overflow.
- If source retrieval requires an egress proxy, configure it only in the private environment file and test a public source through pinned DNS before deploying.

## Native editor and deeper paper generation

- Verify additive native-document columns on a private copy before production migration; compare existing content and account state without printing either.
- Exercise native marks, list/task nesting, tables and image widths through save/reload, history, conflicts, local drafts and JSON/ZIP import. Check stale mirror hashes and remapped document/file references.
- Verify real keyboard input, Chinese composition, rich HTML paste, slash menus, block drag/undo and long documents. Confirm typing does not serialize all Markdown or recreate PDF frames.
- For code blocks, verify authored folds survive save/history/import while read/search/theme preferences leave content clean; copy/export retain the full script, search reveals matches, and keyboard input/undo never silently target hidden code. Check local fonts, syntax contrast, long-script scrolling and phone-width headers.
- For the right-side outline, verify heading levels/duplicates, live changes and undo, scroll highlighting, code/media reflow and document-switch cleanup. Navigation must preserve native content, selection, save state and PDF nodes in both modes; check narrow-screen keyboard, Escape, outside-click and viewport transitions.
- For document fonts and toolbar changes, verify font/color persistence through undo/redo, drafts, history, native exports and protected sharing. Check actual local font loading, unchanged code/math faces and PDF nodes, partial-selection colors/reset, unique common actions, accessible hover/focus tips and narrow-screen menu stacking.
- For table-width changes, test default fixed layout, long unbroken text, adjacent-column resizing, equal distribution with merged cells, Escape cancellation, undo/redo and save/reload. Check dense tables at phone widths, horizontal scrollbar drag/keyboard behavior in free mode, and layout preservation in native archives and read-only shares.
- For IME work, exercise native Chromium composition shrinking, cancellation and confirmation in paragraphs, headings, lists, tables and code. Verify ordinary Backspace remains functional and no stale prefix reaches saved content.
- For Bug reports, check new-tab draft preservation, upload/paste/remove/retry flows, idempotency, authorization on records/images, immutable APIs and text escaping. Rehearse additive schema changes on a private copy; verify standard backups include report rows and screenshot bytes while public sharing denies access.
- For paper latency/progress changes, verify selected-file byte identity, parallel local extraction, real transfer/page counters, acknowledgement waits, estimated AI overruns and completion gating. Include a synthetic PDF that exceeds the character limit and verify partial extraction still permits preview, analysis and save. Test transient-job ownership, expiry/concurrency, numeric-only timing persistence and safe upload cleanup. Calibrate using public/synthetic input with the deployed model/profile; preserve other private settings when changing paper reasoning.
- Verify draft quota failures stay visible and do not silently discard edits.
- Verify gzip GET/HEAD negotiation, disabled gzip and stale-copy fallback. Retain notices for the bundled runtime dependency graph.
- Run the exact-service assistant check with `--paper` as well as the general mode. Use a public-paper or synthetic evidence fixture, confirm the reasoning budget and truthful source scope, and do not persist acceptance content into personal documents.
