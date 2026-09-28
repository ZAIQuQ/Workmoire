---
name: personal-workspace-maintenance
description: Maintain this private single-user workspace as a public, reproducible open-source project.
---

# Workmoire Maintenance

Use this skill for changes to the Workmoire source, tests, deployment, GitHub synchronization, runtime data boundaries, or the project's own maintenance workflow. It applies when a request mentions this project, its Tencent Cloud service, its public repository, or an optimization to the workflow.

## Core invariants

- The Git repository is public-safe source. Never commit personal notes, papers, work logs, uploaded files, SQLite databases, backups, production .env files, server addresses, usernames, SSH material, access tokens, cookies, logs, or generated runtime state.
- Runtime data stays outside the checkout in the configured WORKSPACE_DATA_DIR. Treat the database and file directory as user data and back them up before schema changes or destructive operations.
- Keep the application single-user unless the user explicitly changes that product decision. Passwords are set through the first-run page and are never placed in source, documentation, chat, or deployment commands.
- Keep the service independent of other applications on the server. Discover a free port before changing it, preserve existing services, and verify the service health after every deployment.
- Keep the project reproducible from a clean checkout. Prefer Python standard-library code and documented Docker/systemd paths unless a dependency has a clear user-facing benefit.

## Working workflow

1. Read the repository instructions and inspect the current branch, service unit, data path, port, and resource headroom before editing.
2. Work in the Git checkout. Keep production data in a separate ignored directory. Make schema changes backward-compatible and test them against a copy of the database before touching production.
3. Treat the repository skill at skills/personal-workspace-maintenance/SKILL.md as the source of truth for this workflow. If a workflow invariant or repeatable operational lesson changes, update this skill and its relevant reference in the same change.
4. Run the project's checks before deployment: make compile, make test, and an HTTP smoke test covering health, first-run session state, authentication, content CRUD, and file upload when those paths changed.
5. Run a public-repository scan before staging and again before pushing. Check for IP addresses, personal email addresses, private paths, credentials, private keys, tokens, cookies, database files, uploads, logs, and non-placeholder production settings. Review the staged file list manually.
6. Deploy only source files and static assets to the configured application directory. Do not copy .env, data/, backups, or a whole working directory. Restart the systemd service only after the new files are in place, then verify systemctl is-active, /healthz, /api/session, the listening port, and recent journal output.
7. Commit with a focused message that describes the user-facing behavior. Push only to the intended GitHub repository and branch. If the remote is absent or the authenticated account is unclear, stop before creating a new remote or publishing.
8. Report what changed, what was tested, the public repository state, the deployment state, and any remaining setup such as a cloud security-group rule or HTTPS.

## Updating this skill

Update the skill when a workflow rule, security boundary, deployment invariant, data migration practice, or verification gate changes. Keep feature-specific implementation details in the source or focused references instead of expanding this file with a changelog. Add a short dated entry to references/maintenance-log.md for each such workflow improvement, including the reason and the files changed.

After editing the repository copy, run python3 scripts/sync_skill.py to mirror it into the active Codex skill directory. Validate it with the skill creator's quick_validate.py before reporting completion. The mirror is a generated local convenience; the repository copy remains canonical and must be committed.

## References

- Read references/release-checklist.md before a GitHub release or production deployment.
- Read references/maintenance-log.md when deciding whether a new workflow lesson is already recorded.
