# Blog dossiers

The internal document kind is `blog`; the visible type and required bookmark
are `博客`. The bookmark exists at zero usage, has a fixed copper palette, and is
protected from global deletion/renaming and removal from blog documents. The
main navigation remains documents, papers and relationships.

## User flow

New document → Blog dossier opens the source dialog. Read a public HTTPS link,
check the extracted title/author/site/date, generate a brief summary, insert it
into the native editor, then save normally. Source metadata and the original
link are included in the body, so Markdown and JSON/ZIP exports retain attribution.
The archive also includes an editable notes section.

The summary template is `prompts/blog-summary.md`: a short overview and a few
specific points, usually 300–600 Chinese characters. It uses the existing
general Codex budget, independently of the deeper paper settings. Full AI
template refinement remains in TODO.md for later user review.

Blocked/login-only sources do not yield a fabricated title or summary. The
dialog exposes manual metadata and a pasted-body field. Summaries identify
provided text as their evidence. A source-only archive requires a user-confirmed
title and clearly states that no body summary was generated. Changing the URL
or metadata invalidates an older preview.

## Reading and persistence boundaries

- Blog reads reuse the public-address validation, pinned DNS, redirect checks,
  deadline and response-size limits from the paper transport. Credential-bearing,
  private-network and non-HTTPS destinations are rejected.
- The HTML parser reads metadata and bounded article/main/content containers,
  ignoring navigation, forms, scripts, comments and footer chrome. JSON-LD is
  parsed as data. Candidate count, nesting and extracted text are bounded.
- At most 30,000 characters reach the summary prompt; truncation and broad
  fallback extraction are labeled. Missing authors/dates remain missing.
- Lookup and draft endpoints require authentication and create no documents,
  revisions or files. Model prompts treat source text as untrusted material and
  use the existing ephemeral read-only Codex process.
- Submitted pasted text is limited to 60,000 characters. Summary generation
  requires sufficient body text, and source-only archives do not invoke Codex.
- No login challenge, access restriction or paywall is bypassed. Some platforms
  reject automated or unauthenticated reads; the manual path is the supported
  fallback.

## Database compatibility

SQLite's existing document-kind CHECK constraint requires a transactional table
replacement to accept `blog`. `schema_migrations.allow_blog_documents` copies
the existing columns and rows, preserves indexes, triggers, foreign-key targets
and the original autoincrement sequence position, and verifies references before
commit. Foreign-key enforcement is restored on both success and failure. The
migration is repeatable and must be rehearsed on a private production copy.

Deployment backs up source, SQLite and attachments before the migration, compares
existing record digests and checks database integrity. A source rollback retains
the expanded constraint and user records; older versions may not edit the new
blog kind, so a failed release should be corrected without deleting those records.

## Validation

Tests cover source extraction, structured metadata, truncation, blocked/private
sources, preview-only generation, pasted evidence, source-only archives, built-in
protection, native save/import, narrow layouts and migration rollback. Actual
public-page checks verified ordinary blog extraction and a platform's explicit
403 response. Run `scripts/check_assistant.py --blog --service SERVICE` to verify
the actual service environment and summary template using synthetic text only.
