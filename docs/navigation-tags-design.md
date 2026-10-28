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
- Document rows show the title, a one-line preview and colored bookmarks. Icons
  distinguish document types; task progress appears when relevant. Selection
  and pinning remain available.
- The bookmark control sits immediately left of pin, with two visible tag chips
  and a `+N` overflow control. Tag chips filter the list. A bounded, anchored
  picker handles the full set; tag maintenance is removed from the title area.
- Filtering changes the document list and preserves the editor. On phones it
  reveals the list, and reopening the current document retains unsaved edits.
  A draft/current-document row remains accessible outside the filtered page.
  The tag library searches and paginates the full catalogue.

Bookmark colors use a deterministic normalized-name mapping to eight restrained
palettes, shared by list chips, selected labels, suggestions and the library.
`论文` has a fixed blue bookmark. Every color retains a readable text label, and
the text/background pairs meet 4.5:1 contrast. Color is a display preference,
not stored document metadata.

## Suggestions and organization

Suggestions use existing local metadata: title substring matches first, then
co-occurrence with the last selected tag, then usage count. The picker explains
the first two reasons. It supports keyboard selection, Chinese composition,
case-insensitive reuse and normalized full-width names. Suggestions are not
automatic assignments. The picker has explicit apply/cancel controls. Existing
documents use a dedicated metadata save that changes only labels and the
revision timestamp. It records history and rejects stale versions, leaving the
body and native document untouched. Unsaved body edits remain local; a matching
local draft is rebased only over the known tag-only revision. Body saves and
tag saves on the same document cannot race through the client. New documents
keep labels in their local draft until the first document save. No additional
AI service is involved.

The `论文` catalogue entry is built in, including at zero usage. Renaming or
merging it away is rejected by the backend. Paper dossiers always expose it,
including legacy records that did not store it, and tag/body saves retain it.
It is locked in paper pickers and excluded from custom-label limits. Notes may
associate with it without changing their document type. No startup rewrite of
existing documents or their historical revisions is required.

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
bounds. Browser checks cover row-control placement, independent metadata saves,
draft preservation/rebasing, new local documents, built-in protection, keyboard
and Chinese input, palette consistency/contrast, history, stale updates,
pagination, filtering and phone widths. Visual reviews use synthetic documents.
