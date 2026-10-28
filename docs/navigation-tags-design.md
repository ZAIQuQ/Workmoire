# Navigation and tag organization

Reviewed primary product documentation on 2026-10-28:

| Reference | Documented behavior | Workmoire decision |
| --- | --- | --- |
| [Notion: navigate with the sidebar](https://www.notion.com/help/navigate-with-the-sidebar) | Sidebar sections can collapse or hide; favorites appear when used; a library provides access beyond the visible sidebar | Keep primary destinations visible, collapse the desktop sidebar, move the tag catalogue to an on-demand library |
| [Bear: how to use tags](https://bear.app/faq/how-to-use-tags-in-bear/) | Tags organize notes, can be renamed, and can be managed separately from the note text; nested and pinned tags are available | Make labels direct, searchable document controls; provide explicit rename/merge operations with document history |

The research focused on navigation and tag workflows. Notion's multi-user
teamspaces and Bear's arbitrary tag nesting would add unnecessary structure to
this single-user academic notebook, so they are not part of this change. No new
framework or third-party artwork was introduced; the existing licensed Lucide
icons are reused.

## Information hierarchy

- The sidebar has three destinations: documents, papers and relationships. One
  secondary entry opens tag management. The previous seven-label list,
  duplicated document counters and always-visible shortcut link are removed.
  Shortcuts remain in the account menu. Desktop navigation can collapse without
  destroying the editor or its draft; phones retain a drawer.
- Document rows prioritize the title and a one-line preview. Repeated type
  labels and tag summaries are omitted; icons distinguish document types, and
  task progress appears when relevant. Selection and pinning remain available.
- Document labels appear below the title. Three compact chips are visible by
  default; the picker exposes the complete set without a long label row.
- Filtering changes the document list and preserves the editor. On phones it
  reveals the list, and reopening the current document retains unsaved edits.
  The tag library searches and paginates the full catalogue.

## Suggestions and organization

Suggestions use existing local metadata: title substring matches first, then
co-occurrence with the last selected tag, then usage count. The picker explains
the first two reasons. It supports keyboard selection, Chinese composition,
case-insensitive reuse and normalized full-width names. Suggestions are not
automatic assignments; label edits stay unsaved until explicit document save.
No additional AI service is involved.

Renaming to an existing name merges it. A preview lists the impact count and up
to five example titles; the operation applies across the workspace, including
when opened from a paper filter. A fingerprint of affected versions protects
against stale previews. Writes are authenticated and transactional, update only
labels and document timestamps, and record the original revisions. Trash is
excluded. One operation is bounded to 100 active documents; larger changes
require a smaller affected set. No bulk label or document deletion is added.

## Verification

Backend checks cover local ranking, normalization, authentication, previews,
atomic merge/history, stale editors/previews, untagged filtering and operation
bounds. Browser checks cover keyboard additions, read-only labels, save/reload,
large catalogues, draft preservation while filtering, merge previews, changes
during a save, stale suggestions, sidebar persistence and phone widths. Visual
reviews use synthetic documents at desktop and mobile sizes.
