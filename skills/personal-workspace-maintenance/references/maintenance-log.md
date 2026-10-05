# Maintenance workflow log

Record only changes to the project's maintenance workflow, security boundary,
deployment invariant, data migration practice, or verification gate. Feature
changes belong in normal commit history.

## 2026-09-28

- Created the maintenance skill as the canonical workflow source.
- Established the public/private boundary: source and generic docs may go to
  GitHub; runtime data, credentials, server identity, and personal content stay
  outside the repository.
- Added release and deployment gates for compilation, tests, HTTP smoke checks,
  staged-file review, sensitive-data scans, health checks, and service logs.

## 2026-09-29

- Added an optional local Codex assistant with a disabled-by-default boundary:
  explicit executable configuration, read-only ephemeral invocation, bounded
  input/output, and no persisted prompts or responses.
- Added the assistant boundary to the source, security guidance, and deployment
  verification workflow.
- Added a private bootstrap token boundary so a fresh public instance cannot be
  initialized by the first unauthenticated visitor.
- Installed the optional Codex CLI as a user-local dependency on the server and
  verified Workmoire's assistant endpoint with synthetic input only; the path
  and CLI authentication remain private service configuration.
- Added a transactional export/import boundary: JSON imports are versioned,
  relationship-aware, and keep credentials and file binaries outside the
  portable content format.
- Added HEAD health/static checks and included them in deployment verification after
  discovering that basic monitors can probe without a response body.
- Added persisted session versions so password changes revoke prior cookies
  immediately while keeping the SQLite migration additive.
- Added a startup guard that refuses the public example session secret, reducing
  the chance of deploying a copy of `.env.example` as production configuration.
- Added a retention-aware SQLite/file backup workflow, generic systemd timer
  examples, and a synthetic backup test so scheduled backups can be enabled on
  a private deployment without putting server paths or data in the repository.
- Added a reversible trash workflow for items and files, with an HTTP lifecycle
  test and explicit permanent-deletion verification to reduce accidental data
  loss during daily organization.
- Added real-browser startup, navigation, and trash lifecycle checks using an
  isolated synthetic workspace after discovering a selector error that passed
  syntax checks. Deployment health probes now allow a bounded startup interval.
- Extended browser-local drafts to existing items with revision matching and
  explicit restore/ignore actions. The boundary keeps drafts out of repository,
  export, and log paths; an explicit local-assistant action may process the
  current selected text without persisting it.
- Added explicit assistant result actions for summary/body insertion; generated
  text remains reviewable and unsaved until the user chooses both insertion and
  the normal save operation.
- Added a disabled assistant entry when the local CLI is unavailable and a
  single-request UI guard so slow local CLI calls cannot be duplicated by
  repeated clicks.

- Made the local assistant explicitly pass a configurable bounded reasoning setting (default `low`) after the private CLI timed out at its profile default; documented model/reasoning overrides and kept the server-only configuration boundary.

- Extended GitHub CI with an explicit Node client syntax check, browser smoke-script compilation, and diff validation so frontend changes receive a reproducible public-repository gate before deployment.
- Added post-write backup validation: SQLite snapshots must pass `PRAGMA integrity_check` and file archives must be listable before retention pruning. Updated `backup.sh`, its synthetic test, the release checklist, and this skill so a successful backup command also proves recoverable artifacts.
- Added `bash -n backup.sh` to the shared compile gate so backup script syntax is checked locally and in GitHub CI before release or deployment. Updated `Makefile`, the release checklist, this skill, and this log.
- Verified the installed local Codex CLI after an upgrade and documented that Workmoire must pass explicit `--ephemeral` and `--sandbox read-only` flags; profile keys that the CLI reports as unrecognized are not treated as security controls.
- Replaced CI's hard-coded deployment IP and institution domain denylist with generic credential patterns and removed the scan exclusion for the legacy source file. The public-boundary gate must not itself publish a private identifier; actual addresses and personal domains remain a manual pre-push check.
- Added authenticated batch triage with a 100-item limit, transactional status updates, revision capture, and reversible batch trash. The UI and API now share the same bounded operation so a failed selection cannot leave a partially changed workspace.
- Kept the “select all” control visible in every content space while leaving batch actions hidden until selection. This makes the shortcut discoverable without weakening the explicit confirmation boundary for changes and trash.
- Added deterministic search relevance ordering that favors title, summary, and tag matches over body-only matches while retaining authenticated, deleted-content-free search.
- Fixed search and activity navigation to load the selected item by authenticated ID, preventing an empty editor when a result falls outside the current client-side list window.

## 2026-10-05

- Made first-run setup fail closed on non-loopback listeners when
  `WORKSPACE_SETUP_TOKEN` is empty, and exposed the same requirement through
  `/api/session`; this prevents an unauthenticated visitor from claiming the
  only account on a fresh public deployment.
- Added a bounded `WorkspaceHTTPServer` with daemon threads, an explicit accept
  queue, and a 30-second socket timeout so incomplete direct HTTP requests
  cannot hold worker threads indefinitely. Added synthetic HTTP and server
  property tests for both boundaries.
- Added optimistic edit conflict protection with microsecond item timestamps,
  a `409` response carrying the current item, and a browser-local draft fallback
  so concurrent tabs cannot silently overwrite a paper, project, or log.
- Added stable cursor pagination and an explicit load-more control for content
  spaces so older material remains discoverable as the archive grows past the
  first client page.
- Added structured civil dates for work logs, with additive migration, strict
  validation, full-archive date filtering, date-preserving edits/history/imports,
  and local-day navigation. Tightened stale browser-draft recovery so an older
  draft remains discoverable but is never applied without an explicit action.
- Made history restore check for unsaved editor changes and state its draft
  clearing effect before the explicit restore confirmation, preventing a
  reversible history action from silently discarding current edits.
- Added version-aware list cursors for priority, due-date, title, and updated
  sorting; status/tag filters now run on the full server archive. Pinning
  advances the item version, legacy unversioned session cookies are rejected,
  imports reject hierarchy cycles, and dashboard/review “today” is supplied
  as an explicit browser civil date. Updated source, tests, README, release
  checklist, and this skill together so these data and deployment invariants
  remain reviewable.
- Extended the same full-archive and bounded-response contract to hierarchy
  candidates, tags, review queues, calendars, and trash; repeated unchanged
  saves now keep timestamps and history stable. Added browser coverage for a
  work-log date move so the active civil-day view follows the saved item.
- Preserved original hierarchy links in a separate trash metadata table,
  validated links during restore, honored explicit parent edits, and advanced
  versions when a trash operation detaches active children. File uploads now
  keep their metadata insert transactional and remove staged bytes after a
  failed association or database write. Updated source, tests, release gates,
  and this skill together.
- Bounded the file-space listing with server-side search pagination, exact
  totals, and a browser load-more control so a large attachment archive remains
  discoverable. Updated the API client, README/release gates, tests, and skill
  together.
