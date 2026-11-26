# D-006 — The release manager's digest is validated against its grammar before it is read

**Status**: accepted (2026-11-26)

## Context

The release manager's whole reply is one digest — `section:`,
`trace:`, `dropped:`, `watch:` (`agents/release-manager.md`) — and the
session read it by eye: a section without its heading, a trace bullet
that named no source, or a dropped `dropped:` field was as usable as a
good one, and `release.py` validates only the section once it is in
the changelog. spec-design D-074 ships one schema module for every
digest grammar.

## Decision

1. **The digest is a schema.** `scripts/digests.py` carries the
   grammar quoted from the brief — the section opens with its heading,
   and every trace bullet ends in `spec:`, `commit:`, `dep:`,
   `backlog:` or `rollout:` — shipped byte-identical with the other
   digest-grammar skills and pinned by `tools/tests/test_parity.py`.
2. **Every returned digest is validated before anything is read from
   it**: `python3 <skill_dir>/scripts/digests.py validate
   release-manager` — exit 0 valid, exit 1 with the problems. A
   malformed digest is a fix and run again: the problems go back to the
   same brief and it is re-spawned; no section, trace, `dropped:` or
   `watch:` line is read from it, and nothing is replaced in the notes.
3. **The rule is stated once** in `contracts/run.md` § The release
   manager; SKILL.md carries a pointer alone.

## Consequences

The user is never shown a tightened section from a digest the schema
rejected, and no fact's trace is lost to a malformed bullet. Cost if
wrong: a schema stricter than what the release manager writes re-runs a
correct digest — a read-only re-run — and the cure is a schema edit in
the spec-design master, replicated.
