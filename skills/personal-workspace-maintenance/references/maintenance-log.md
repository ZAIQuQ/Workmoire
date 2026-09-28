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
