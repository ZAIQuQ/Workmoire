# Password-protected document sharing

Open a document and click **分享** at its upper right. The dialog provides the
link, validity (1, 7, 30 days or permanent), and an automatically generated
28-character password containing uppercase, lowercase, digits and symbols.
The default validity is seven days. Generate the link, then use **复制链接和密码**.
Unsaved or legacy documents are saved through the normal revision-checked flow
first. A stale save prevents publication.

Each link publishes a read-only snapshot of the saved native document and copies
only attachments referenced by its body. Subsequent private edits are not
published. **生成新链接** updates the snapshot and revokes the previous link.
**重置** changes the password and invalidates existing reader sessions;
**停止分享** revokes the link. Moving the original document to trash also revokes
its share; restoring the document does not reactivate the link. Already downloaded
content cannot be recalled. A permanent link remains active until revoked or
replaced. Changing validity counts from the time of the change.

The public page preserves rich text, math, read-only tasks, images, code folding,
and the local PDF reader. References to other private documents become plain text.
Unreferenced attachments and the private document catalogue are never exposed.

## Two services

The owner service normally listens on 5200; the reader listens on 5201. Set
`WORKSPACE_SHARE_DATA_DIR=/var/lib/workmoire-share` and
`WORKSPACE_SHARE_PORT=5201` in the owner's private environment. Leave
`WORKSPACE_SHARE_PUBLIC_URL` empty for direct HTTP on the current hostname, or
set an explicit HTTPS origin in both services when using a reverse proxy.

Use `deploy/systemd/workmoire-share.service.example` and the matching environment
example for the reader. The reader must have its own unprivileged system user,
`workmoire-share`, and a separate environment without owner/Codex credentials.
Copy only `share_server.py`, `share_store.py`, `rich_documents.py` and the static
assets to `/opt/workmoire-share`, with code owned by root and readable but not
writable by the reader. It imports no workspace server or private configuration.
Do not copy private data, keys or backups into the code directory.

Create `/var/lib/workmoire-share` and its `media` child with the owner service user
as owner, `workmoire-share` as group, and mode **2750**. Initialize with
`SharePublisher(Path('/var/lib/workmoire-share')).initialize()` as the owner
service user. The resulting database and media use **0640**; `publisher.key` and
`publisher.lock` use **0600** and belong only to the publisher. Create `auth` with
the reader user as owner and mode **0700**. The setgid publication directories
ensure new snapshots remain readable by the reader despite the owner's umask.
Never add the reader to the owner's private group.

The example systemd unit makes the publication store read-only, allows writes
only to `auth`, hides home directories/private environment files and the publisher
key, and caps memory/tasks. Adjust paths to the real installation. Keep the
publisher key backed up: losing it prevents retrieval of existing link/password
credentials by the owner. Keep main service startup dependent only on its own
configuration; the reader can restart independently.

Validate both health endpoints, listeners and service states. Verify as the
reader user that `published.db` is readable but not writable, while the publisher
key, owner database and private environment cannot be read. Check the cloud
security group if remote clients cannot reach 5201; a local listener alone does
not prove internet reachability.

## Access controls

Public paths use a 43-character token with 256 bits of HMAC output derived from a
private key and a fresh random nonce. No article ID, slug, title or sequential
identifier is used. Only token hashes are stored; the public reader cannot
recover the URL token or password from stored nonces without the publisher key.
Passwords use salted scrypt verifiers and constant-time comparison.

The public service exposes only its password gate, document/file routes, selected
static assets and health endpoint. Title, body and media require password
verification. Workspace login cookies do not authorize a reader request. Reader
cookies are HttpOnly, SameSite=Strict and scoped to one link; server-side sessions
last at most 12 hours, bounded by link expiry. Every document/file request checks
expiry, revocation and credential version. Reader logs omit URL tokens, cookies,
passwords and document contents; configure reverse-proxy access logs the same way.

Persistent limits permit five failed passwords per IP per ten minutes and thirty
per link, plus sixty attempts per IP per minute and 120 total attempts per minute.
IPv6 clients are grouped by /64; untrusted forwarding headers are ignored. A
trusted reverse proxy therefore shares an IP bucket unless explicit trusted-IP
handling is added. Socket/worker counts and concurrent scrypt work are bounded.
The responses disable caching and indexing, suppress referrers, and restrict
framing and resource loading.

Ports are not separate cookie domains. For transport privacy and stronger browser
host separation, terminate HTTPS on a dedicated sharing hostname, set the same
`WORKSPACE_SHARE_PUBLIC_URL` in both services, and enable
`WORKSPACE_SHARE_COOKIE_SECURE=1` in the reader. Plain HTTP on 5201 does not encrypt
the password or content in transit. Do not configure a proxy to forward unknown
public routes to the owner service.

## Backup and restore

When `WORKSPACE_SHARE_DATA_DIR` is set, `backup.sh` also writes
`shares-<timestamp>.tgz`. Under the publisher lock, it uses SQLite backup for the
publication database and archives the publisher key and attachment copies. It
verifies SQLite integrity and archive readability before pruning old backups.
All backup files are private. Reader sessions and rate-limit state are excluded.

Restore only from trusted backups while both services are stopped. Restore the
publication archive to the configured publication directory, restore the owner
database/files from their corresponding backup when needed, then reapply the
owner/group/modes above. Delete stale reader auth state and recreate its private
directory. Start the owner and reader, verify health and synthetic sharing before
use. Restoring an older publication backup can reactivate links revoked since
that backup; revoke or regenerate them before exposing the restored listener.
