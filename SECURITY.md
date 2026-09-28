# Security policy

This project is intended for a single private user. Do not expose the service
without a strong password and a protected network path.

Please do not open a public issue for a suspected vulnerability. Contact the
maintainer privately with a description, reproduction steps, and impact.

Never commit runtime data, uploaded files, database files, production
configuration, credentials, access tokens, or server addresses. The repository
contains only generic source and documentation.

The optional local assistant is disabled by default. If enabled, configure an
explicit Codex executable on the private server and keep the service behind the
same authentication and network boundary as the rest of the workspace.

Deleted content and files are moved to the authenticated trash area first.
Permanent deletion is a separate action; database and file backups remain the
recovery path after permanent deletion.

Set a random `WORKSPACE_SETUP_TOKEN` before exposing a fresh instance. It is
accepted only during the one-time account initialization and must stay outside
the public repository.
