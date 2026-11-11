# D-002 — Where `Released:` is recorded, and when

**Status**: accepted (2026-11-11)

## Context

D-014 named "a `Released:` marker in spec.md". At full tier spec.md is
frozen whole except its Status line (freeze.py): any added line fails
check.py's approval-freeze check. At tiny tier spec.md is frozen
except § Evidence and the status tokens in § Tasks; a `Released:`
line after the `Delivered:` record inside § Tasks failed the freeze in
a scratch run, the same line under `## Evidence` passed. task.md is not
frozen, and check.py passed it with an extra header line.

The record also cannot name its own commit: the tag points at the
release commit, so a line inside that commit cannot carry its sha.

## Decision

- The record lives in the spec's status holder, beside `Delivered:`:
  `**Released**: <tag> @ <sha12>` below task.md's `**Delivered**:`
  header at full tier; `Released: <tag> @ <sha12>` in spec.md
  § Evidence at tiny tier, the section appended when absent. Archived
  specs take it in their archived dir.
- `<sha12>` is the release commit the tag points to.
- The records ride a second commit, `chore(release): record <tag> on
  delivered specs`, made right after the tag under the same yes — the
  shape of spec-build's C1/C2.
- The post-release outcome (`Post-release check: <tag> pass|fail
  <date> — <note>`) follows the same placement.
- No project-level release ledger: the tag and the changelog are the
  project's record; a `specs/RELEASES.md` would restate both.

## Consequences

No change to check.py, freeze.py, or the docset templates. check.py
does not verify the record's sha the way it verifies `Delivered:`
(observations item 2). A user-typed note never carries angle brackets
into a tiny spec — check.py would read them as a placeholder — so
`verify` strips them.
