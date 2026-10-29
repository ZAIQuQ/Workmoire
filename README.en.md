# Workmoire

[中文](README.md) · **English**

Self-hosted academic notes and paper reading. Write rich documents, read PDFs in place, and connect your material with tags and document links.

[Quick start](#quick-start) · [User guide](docs/user-guide.md) · [Changelog](CHANGELOG.md) · [Releases](https://github.com/ZAIQuQ/Workmoire/releases)

![Workmoire: a document catalogue, colored tags, and the rich-text editor](docs/images/workmoire.png)

## What it does

- **Write** with rich text, math, images, checklists, and foldable code blocks. A compact single-row toolbar exposes document fonts and selection colors; a right-hand outline tracks headings. Focus mode hides the footer. Insert blocks with `/`, searchable in Chinese, pinyin initials, and English.
- **Work with tables** that fit the document by default. Distribute columns evenly, or turn off fixed width to enable horizontal scrolling.
- **Read papers** by manually uploading a PDF and optionally recording its source link. The server does not download papers. Embed the PDF reader directly in a document. Uploads show measured progress, and one AI analysis organizes publication, authors, labs and research fields, suggests up to two tags, and explains the motivation and contribution with an estimated wait.
- **Organize** with colored catalogue tags, pin-side tag management, and document links. Create either a blank document or paper materials.
- **Share** a read-only snapshot with a strong password and a 1-day, 7-day, 30-day, or permanent lifetime. Reset the password or revoke access at any time.
- **Keep your work** with local drafts, save-conflict detection, version history, recoverable trash, and JSON / full-archive import and export.

Codex assistance is **optional and disabled by default**. When enabled, selected material is passed to the local CLI and its configured model provider. Generated text must be reviewed, inserted, and saved explicitly.

## Quick start

Requires **Python 3.10–3.12**. The server uses the Python standard library; editor assets, fonts, and the PDF reader are bundled. Node.js and a CDN are not required at runtime.

```bash
git clone https://github.com/ZAIQuQ/Workmoire.git
cd Workmoire
cp .env.example .env
chmod 600 .env
```

Edit `.env`:

- Use `WORKSPACE_HOST=127.0.0.1` for a local installation.
- Set `WORKSPACE_DATA_DIR` to a directory outside the source checkout.
- Replace `WORKSPACE_SESSION_SECRET` with a long random value. Set a separate `WORKSPACE_SETUP_TOKEN` before exposing first-run registration publicly.

Generate each secret with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. The setup token is needed only to create the first account; subsequent sign-ins use your username and password.

```bash
python3 workspace_server.py
```

Open [localhost:5200](http://localhost:5200) and create your account.

Use **上报 Bug** at the bottom right to submit screenshots and reproduction steps. The account menu opens an authenticated, read-only report history. See [bug reporting](docs/bug-reports.md).

## Deployment and data

| Service | Default port | Purpose |
| --- | --- | --- |
| Workspace | `5200` | Sign-in, editing, and document management |
| Sharing, enabled separately | `5201` | Password-protected read-only snapshots |

The reader runs under a separate OS identity and reads a dedicated publication store, without access to the private document library. Follow the [sharing deployment guide](docs/document-sharing.md); [systemd examples](deploy/systemd/) cover the workspace and scheduled backups. Alternatively, run the workspace with `docker compose up -d --build`; data uses a named volume. Sharing and Codex are not enabled in the default container setup.

Use HTTPS in production. Back up the database, attachments, and sharing key. Shares contain the saved version at publication time; later edits stay private. Downloaded content cannot be recalled.

```bash
WORKSPACE_DATA_DIR=/path/to/private-data ./backup.sh /path/to/private-backups
```

See the [user guide](docs/user-guide.md), [paper intake guide](docs/paper-intake.md), and [security policy](SECURITY.md) for configuration and behavior.

## Development

Use Node.js 22.13+ or a newer LTS for builds and browser tests.

```bash
npm ci
npm run build
make compile
make test
npx playwright install --with-deps chromium
npm run test:browser
```

Tests use isolated temporary data. After a substantial change, follow the [release workflow](docs/releases.md): update the version and changelog, verify the deployment, then synchronize GitHub.

## License

[MIT](LICENSE). Bundled dependencies, icons, and fonts retain their own [licenses and source notices](workspace/static/THIRD_PARTY_ASSETS.md).
