# Document sharing with optional password protection

Open a document and click **分享** at its upper right. The dialog provides the
link, validity (1, 7, 30 days or permanent), and a **密码保护** switch. Protection
is on by default. When enabled, it uses an automatically generated 16-character
password containing uppercase, lowercase and digits, without symbols. Turn it
off to let anyone with the link read the snapshot and its included attachments.
The default validity is seven days. **复制链接和密码** copies exactly two lines
when protected; **复制链接** copies only the URL when protection is off. Neither
adds expiry commentary.
Unsaved or legacy documents are saved through the normal revision-checked flow
first. A stale save prevents publication.

Each link publishes the saved native document as a read-only public version and
copies only attachments referenced by its body. Later **saved** edits refresh the
same link, password and expiry in place; unsaved drafts never become public.
**生成新链接** remains available when you want to replace the URL or credentials.
**重置** changes the password and invalidates existing reader sessions;
**停止分享** revokes the link. Moving the original document to trash also revokes
its share; restoring the document does not reactivate the link. Already downloaded
content cannot be recalled. A permanent link remains active until revoked or
replaced. Changing validity counts from the time of the change. A reader reloads
the link to receive the latest saved version; an already open reader may need to
reload after a publication update.

When the document is saved, an existing link is refreshed in place with the new正文 and referenced attachment set; its URL, password, expiry and protection mode stay unchanged.

Changing **密码保护** on an existing share saves immediately and keeps the link
and snapshot. Re-enabling protection generates a fresh password and invalidates
earlier reader sessions. The owner API hides passwords while protection is off;
password reset is available only while protection is enabled. Concurrent stale
settings are rejected rather than silently overriding a newer choice.

The public page preserves rich text, math, read-only tasks, images, code folding,
LaTeX previews, a sticky right-hand outline and the local PDF reader. References to other private documents become plain text.
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
Add the owner service user to the `workmoire-share` supplementary group and
restart its service so it can maintain the setgid directories. Never add the
reader to the owner's private group. Verify the database and newly copied media
actually inherit `workmoire-share`; chmod by an owner outside that group can
clear the setgid bit on Linux.

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
Passwords use salted scrypt verifiers and constant-time comparison. New password
nonces carry a `v2:` prefix. HMAC output supplies an unbiased alphanumeric sample,
with rejection until the 16-character password contains all three character
classes. Unprefixed nonces retain the original 28-character derivation, so an
upgrade or expiry change does not change a live password. Explicit resets use
the new format and invalidate old reader sessions. Publisher software must
support the nonce version to recover passwords after a restore.

The public service exposes only its access page, document/file routes, selected
static assets and health endpoint. Protected shares require password verification
for title, body and media. Explicitly unprotected shares allow these requests
without a login, password or reader session. Workspace login cookies do not authorize a reader request. Reader
cookies are HttpOnly, SameSite=Strict and scoped to one link; server-side sessions
last at most 12 hours, bounded by link expiry. Every document/file request checks
expiry, revocation, the saved protection setting and, when protected, credential version. Reader logs omit URL tokens, cookies,
passwords and document contents; configure reverse-proxy access logs the same way.

The additive `password_required` column defaults to `1`: all existing shares
remain protected after an upgrade, with unchanged passwords and links. Only an
explicit boolean `false` from the authenticated owner disables protection. A
reader encountering the old schema treats it as protected. Include the setting
in publication backups; restoring a previous snapshot also restores its access mode.

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
