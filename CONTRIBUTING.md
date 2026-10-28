# Contributing

Use the current document-first product scope: blank notes and paper materials,
with optional Codex assistance and a separate sharing service.

Run `npm ci`, `npm run build`, `make compile`, `make test`, and
`npm run test:browser` before submitting editor or navigation changes. Install
Chromium with `npx playwright install --with-deps chromium` when needed. Tests
start disposable servers on loopback and must never use real documents or
production credentials.

Keep server dependencies in the Python standard library where practical. Frontend
libraries and fonts are bundled locally with pinned versions and license notices.
Document the user-visible behavior, relevant validation, and any migration or
operational impact. Keep both README languages in sync.

Never commit runtime data, credentials, private server details, logs, or backups.
Run `python3 scripts/check_public_source.py` before staging and before publishing.
The canonical maintenance skill is in `skills/personal-workspace-maintenance/`;
use [the release workflow](docs/releases.md) for a deployment and GitHub update.
