# D-008 — The release manager's tools report is the reply's first line alone, and a reported name holds no separator

**Status**: accepted (2026-11-26)

## Context

D-007 made the release manager open its reply with a tools report and
refuse a digest without Read. The reader, `tools_report`, took the
first `tools:` line anywhere in the text — a reply that opened with
prose passed on a line found further down, inside the digest — and a
reported name was taken as it came, though the kit joins reported names
onto a ` · `-separated provenance line wherever one is written.
spec-design D-095 closes both.

## Decision

1. **The report is the line the reply opens with** — blank lines and
   an opening code fence aside. A `tools:` line anywhere else is text,
   never a report, so the digest fails the handshake like one that
   carries none: exit 3 from
   `python3 <skill_dir>/scripts/digests.py validate release-manager
   --require-tools`, a failed spawn.
2. **A reported name holding ` · ` refuses the whole digest as
   malformed**: exit 1 with the name — a fix and run again, handed back
   to the same brief, never a failed spawn. A line break cannot reach a
   name: the report is read from one line.
3. **The brief and the schema are pinned together.** `tests/test_digests.py`
   reads the digest from the fenced block in `agents/release-manager.md`
   § Digest, fills it, and asserts the schema accepts it — each trace
   source the block lists — and refuses a field dropped, a field
   renamed, and a section that does not open with its heading.

## Consequences

No tightened section is read from a digest whose report was found in
its own prose, and no release manager's report can shape an
orchestrator's line. Cost if wrong: a release manager that opens with
prose before its report is re-spawned as a failed spawn — a read-only
re-run — and one that reports a name holding the separator is re-run
with the problem.
