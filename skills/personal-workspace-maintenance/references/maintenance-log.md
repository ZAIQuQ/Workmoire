# Maintenance workflow log

Record only changes to the project's maintenance workflow, security boundary,
deployment invariant, data migration practice, or verification gate. Feature
changes belong in normal commit history.

## 2026-09-28

- Created the maintenance skill as the canonical workflow source.
- Established the public/private boundary: source and generic docs may go to
  GitHub; runtime data, credentials, server identity, and personal content stay
  outside the repository.
- Added release and deployment gates for compilation, tests, HTTP smoke checks,
  staged-file review, sensitive-data scans, health checks, and service logs.
