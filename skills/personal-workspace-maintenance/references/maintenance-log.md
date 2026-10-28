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

## 2026-10-27

- Simplified the interface around documents, paper reading, and neighborhood relationships while retaining the account, existing content model, trash, and exports.
- Added locally bundled CodeMirror, Markdown, LaTeX, and code highlighting with signature-checked authenticated media previews and PDF byte-range handling. The bundled PDF.js reader supports search, selectable text, page navigation, and zoom; incremental preview updates retain its reading position.
- Added public-only pinned-DNS metadata/PDF retrieval with validated redirects and an optional trusted proxy. Paper drafts are source-grounded, explicit, and unsaved until insertion and normal save.
- Moved Codex work to disposable empty directories and read only its final-message file; kept explicit ephemeral/read-only CLI flags and synthetic invocation verification.
- Added HTTP/security checks and an isolated browser suite for rich editing, drafts/conflicts, media, paper drafting, relationships, trash, and mobile layout. The development checkout and test data remain separate from production runtime data.

### Runtime acceptance follow-up

- Added an exact-service-environment assistant check after finding that interactive-shell Codex configuration masked an unconfigured systemd authentication path. Custom `CODEX_HOME` must be explicit in the private service environment.
- Terminate the assistant's whole process group on timeout; killing an npm launcher alone can leave its native child retrying. Added a synthetic launcher/child regression test.
- Verify installed backup permissions by executing the actual systemd backup job as its configured user, rather than relying only on an active timer and earlier snapshot files.
- Resolve arXiv abstract/PDF/HTML URLs through the official identifier API instead of depending on the availability of the public HTML page; preserve the requested version and verify the input forms with synthetic metadata.
- Permit explicit PDF imports a bounded two-minute transfer interval and try up to three already-validated public destination addresses on connection failures; metadata retains its shorter limit and every redirect remains validated.

### Visual resource maintenance

- Reuse pinned, licensed GitHub illustration components and named Lucide icons with locally served Fontsource variable fonts. Record provenance and palette-only adaptations, preserve image proportions, and exercise responsive editor/PDF controls with synthetic browser fixtures. Added the resource inventory, build/font bundling, and browser checks for these boundaries.

- Keep interface copy limited to actions, input formats, feature descriptions, and state. Removed motivational/background text and duplicate English headings from login, empty states, templates, search, and relationship views; retain operational instructions and save boundaries.

- Replaced the rejected green/cream theme, Geist-first typography, and decorative illustration panels with neutral surfaces, Inter/native Chinese type, line-separated document rows, and a single interaction accent. Unified the editor, syntax colors, dialogs, and PDF reader; removed unused illustration assets and stale font subsets from the build.

### Native document editing and paper reasoning

- Replaced the source/preview editor with Tiptap/ProseMirror native editing, lazy Markdown mirrors, stable PDF node views, and meaningful interaction/long-document checks.
- Added versioned native JSON to documents and revisions with additive migration, validation, mirror hashes, conflict/draft preservation, and reference remapping in JSON/ZIP restores.
- Increased paper reasoning separately from general document tasks and added bounded public arXiv HTML extraction with explicit evidence scope; checked the actual CLI service environment and a public-paper generation.
- Added complete runtime license notices and build-time gzip assets with matching GET/HEAD negotiation and stale-copy handling.

## 2026-10-28

- Reduced creation to blank documents and paper materials, retiring specialized templates and the blog workflow without deleting records. Added explicit selected-PDF priority, URL-download/manual fallback, bounded PDF.js text extraction, replacement/cancel cleanup and byte/source-preservation checks.

- Added blog dossiers with protected Chinese classification, attributed short summaries, restricted-source/manual-text fallback and a versioned base prompt. Added a tested atomic CHECK-constraint expansion with private-copy record/reference/sequence verification, plus a synthetic exact-service blog-summary check.

- Unified creation and shared rename/delete in the pin-side label entry. Replaced the hidden two-step creation flow with a named form and immediate association saves; added operation-specific deletion previews and before/after metadata for preserving body drafts across successive tag changes.

- Moved label maintenance into catalogue rows beside pin, added stable bookmark colors, and introduced a revision-checked label-only save that preserves body drafts. Made the paper label a protected built-in, including zero-count and legacy-read behavior; recorded row-control, draft-rebase, palette and backend protection checks.

- Introduced shared visual tokens and consistent moderate rounding across the workspace and PDF controls, based on Notion, Feishu and Yuque references. Prioritized the existing variable Chinese font after a platform-font audit exposed inconsistent intermediate system weights; added actual glyph/font and responsive visual checks to the release guidance.

- Simplified navigation and moved labels to a searchable library and contextual document picker. Added local metadata suggestions and previewed, bounded transactional renames/merges, with checks for stale versions, original revisions, draft preservation during filters/saves and mobile navigation. Recorded the workflow in the release checklist and navigation design note.

- Set the paper generation default to gpt-6.1-sol with xhigh reasoning and a bounded 240-second timeout, independently from general document tasks.
- Added deterministic slash-command aliases for Chinese, pinyin and English, including the requested ddm/yy/cite/todo/db shortcuts. Verified compound queries, exact-match ordering, cancelled queries and Chinese composition through browser input.
- Recorded per-service AI skill/template standardization in TODO.md for user-guided refinement after overall design convergence.
- Added lossless code-folding boundaries and checks: authored state persists through native history/import, reading/search/theme overrides stay outside document history, and caret/search/copy retain complete source. Recorded personal-site typography research and verified licensed local Maple Mono assets, contrast and responsive scrolling.

## 2026-10-29

- Added explicit publication boundaries for a separate password-protected reader: saved snapshots, scoped attachment copies, independent OS identity and environment, opaque credentials, durable attempt limits and per-request revocation checks. Added synthetic browser/security/restore gates and deployment permission verification, including the fact that ports do not isolate cookie domains. Extended the actual backup job contract to preserve the publisher key and consistent publication media while excluding reader sessions; recorded rollback/restoration implications in the sharing guide.

- Verified Linux setgid inheritance across distinct publisher/reader users: the publisher must be a member of the sharing group before chmod and file creation. Rehearse publication with actual OS identities; same-user unit/browser tests cannot prove the deployment permission boundary.

- Reconnected the existing GitHub history with deployed development, restored repository CI/legal/container files and prior regression coverage, and recorded standing authorization for post-deployment pushes/releases. Added version metadata, bounded public release checks, bilingual README maintenance, and an exact-deployment publication helper that rejects divergence and avoids force-push.

- Made the document outline a dedicated navigation view beside the body, with live headings, scroll tracking, content-reflow handling and responsive disclosure. Added selection/save/PDF preservation and lifecycle cleanup to the browser release checks.

- Added validated document-font metadata and a view-preserving font history step: changing ProseMirror root attributes recreates node views, so font history stays separate internally while native saves retain the document setting. Added font/share/export checks, selection-color and tooltip coverage, and updated the supported CI Node runtime.

- Added per-table fixed-width defaults, proportional fixed-mode resizing, merged-cell-aware distribution and explicit accessible scrolling in free mode. Recorded rendering-only viewport changes, strict mode validation, native persistence/share checks and drag/observer cleanup in the release workflow.
