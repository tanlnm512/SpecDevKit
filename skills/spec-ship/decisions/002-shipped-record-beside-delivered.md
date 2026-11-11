# D-002 — `Shipped: PR <url>` is recorded beside the delivery record

**Status**: accepted (2026-11-11)

## Context

The PR's url is evidence the spec should keep: it is how a later
invocation finds the PR once the branch is deleted, and how a reader
of the archived spec finds the review. Two homes were possible — the
status holder, where spec-build writes `Delivered: commit @ <sha>`,
or a ship-owned `notes/ship.md`. The status holder is read by the
shared checker and, at tiny tier, hashed by the approval freeze,
neither of which this skill may edit.

Probed against the shipped fixtures: a `**Shipped**: PR <url>` line
under the delivery record in a full-tier task.md leaves `check.py`
green with identical output, and task.md is outside the freeze. At
tiny tier a `Shipped:` line inside spec.md § Evidence — or a new
§ Evidence appended to the file — leaves both `check.py` and
`freeze.py --verify` green: the freeze drops that whole section. A
line anywhere else in a tiny spec.md, § Tasks included, would break
the freeze.

## Decision

- **Full tier**: task.md's header, the line after the delivery
  record, in the same bold form — `**Shipped**: PR <url>`.
- **Tiny tier**: spec.md § Evidence, created at the end of the file
  when absent — `Shipped: PR <url>`. Never § Tasks, even when the
  delivery record itself sits there.
- `ship.py record` is the only writer, atomic and idempotent; a
  changed url replaces the old one in place.
- The record is evidence, not status. No gate reads it, and state is
  still derived from git and the PR — the url is the selector that
  survives a deleted branch.
- The write is a doc change on the spec's branch: its commit is asked
  first, and pushing that commit is one more previewed push.

## Consequences

No closure change is needed. The cost is one extra commit on the
branch after the PR opens. `notes/ship.md` remains, for evidence no
task covers. If the shared checker ever grows a rule that rejects
unknown header lines, the record moves to `notes/ship.md` under a new
decision.
