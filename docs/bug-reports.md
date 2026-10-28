# Private Bug reports

Click **上报 Bug** at the bottom right of the workspace. A separate page accepts
a title, description/reproduction steps and optional screenshots. You can select,
drag or paste PNG, JPEG, GIF and WebP files: at most five images, five MB each,
and twenty MB combined. The form retains its inputs after a failed submission.
Repeated submissions of the same request are idempotent.

The account menu's **Bug 记录** opens the report list. Records and images require
the existing workspace login. This remains a single-account application: the
signed-in owner is the maintainer; no additional public reporter or administrator
account is created. Submitted records are immutable through the UI/API. Add a
new report if you need to provide additional information.

Only the explicitly typed title/description and selected images are uploaded.
The server adds the application version, timestamp and browser User-Agent.
Documents, their URLs, cookies, console logs and assistant material are not
captured automatically. These reports are not sent to GitHub or an AI service.

Reports use the additive `bug_reports` and `bug_report_images` tables in the
configured workspace database. Screenshots use opaque file names underneath
`WORKSPACE_DATA_DIR/files/bug-reports/`. They do not appear in the document
attachment catalogue or document JSON/ZIP exports. The existing `backup.sh`
SQLite snapshot and complete `files` archive include both records and images.
Restore both from the same backup set. The independent sharing process has no
access to this database or screenshot directory.

Report creation validates a bounded JSON request, image signatures and lengths,
requires the existing login and a same-origin JSON request, and commits records
with their screenshot metadata together. Failed writes roll back the transaction
and remove only the directory created for that attempt. Record and screenshot
reads disable caching. The viewer inserts text as text, never as report-authored
HTML. PUT, PATCH, DELETE and detail POST requests are rejected.

## IME regression coverage

The reported sequence `q'we → q'w → q` reproduced the duplicate-prefix bug in
Chromium via `Input.imeSetComposition`. A DOM deletion was interpreted as a
Backspace shortcut query; Tiptap list/core keymaps dispatched empty transactions
even when they returned false. Repainting stale state replaced the active text
node and terminated the browser's composition range.

The editor now guards shortcut plugins while composition is active. Native
browser input and ProseMirror DOM parsing remain enabled; no replacement input
buffer or character rewriting is introduced. Tests cover shrinking candidates,
confirmation, cancellation, normal Backspace and persistence in several block
types. User screenshots and actual private report contents must never be added
to the public repository as fixtures.
