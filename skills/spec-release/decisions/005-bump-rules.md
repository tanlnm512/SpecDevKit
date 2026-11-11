# D-005 — The version bump follows the work types

**Status**: accepted (2026-11-11)

## Context

The kit already classifies every spec by `**Type**` (spec-design
D-056). Commits outside the spec flow usually follow Conventional
Commits or nothing at all. Projects keep their version in different
files, sometimes several at once.

## Decision

- breaking → major; feature → minor; bugfix, hotfix, refactor,
  upgrade → patch; the highest level wins. A breaking marker is a
  spec's `**Breaking**:` line, a `**Compatibility**:` bullet that names
  a break, a `!:` commit type, or a `BREAKING CHANGE:` footer. Outside
  commits count: `feat` → minor, anything else → patch.
- Before 1.0.0 a breaking change bumps minor (SemVer §4); leaving 0.x
  is the user's call, never proposed.
- The proposal always shows its reasons and every version source
  found. Disagreeing sources are reported and ruled by the user
  (`--only`); the script never picks one.
- The tag family in use (`v1.2.3`, `1.2.3`, `pkg-v1.2.3`) is detected
  from the tags reachable from HEAD; several families are reported and
  the most recent is used until the user names one.

## Consequences

The proposal is only as good as the type headers and commit subjects;
a mislabelled spec yields a wrong bump, which the user's confirmation
catches. Monorepos with one version per package are out of scope for
now (observations item 4).
