# D-010 — The integrator's tools report is the reply's first line alone, a reported name holds no separator, and a `summary:` counts its own threads

**Status**: accepted (2026-11-26)

## Context

D-008 made the session validate the integrator's digest and D-009 made
its reply open with a tools report. Three things neither checked. The
reader, `tools_report`, took the first `tools:` line anywhere in the
text, so a reply that opened with prose passed on a line found further
down. A reported name was taken as it came, though the kit joins
reported names onto a ` · `-separated provenance line wherever one is
written. And the `threads` digest states a `summary:` — `must-fix <n>
· question <n> · nit <n> · disagree <n>` — that no one counted: a
summary reading `must-fix 0` above a thread classified `must-fix`
validated, and the session, which drafts fix rounds from the counts,
read it. spec-design D-095 and D-096 close them.

## Decision

1. **The report is the line the reply opens with** — blank lines and an
   opening code fence aside. A `tools:` line anywhere else is text,
   never a report, so the digest fails the handshake like one that
   carries none: exit 3 from
   `python3 <skill_dir>/scripts/digests.py validate integrator
   <pr-text | threads> --require-tools`, a failed spawn.
2. **A reported name holding ` · ` refuses the whole digest as
   malformed**: exit 1 with the name — a fix and run again, handed back
   to the same mode, never a failed spawn.
3. **A `summary:` that disagrees with the thread blocks is malformed.**
   Each of its four counts must equal the number of `thread` blocks
   carrying that label; the schema refuses the digest naming the label,
   the count it states and the count it carries, and no classification
   or draft is read from it in the meantime. Zero threads stays
   malformed as before — the digest's `thread` field is required.
4. **The brief and the schema are pinned together.** `tests/test_digests.py`
   reads both digests from the fenced blocks in `agents/integrator.md`
   § Output, fills them, and asserts the schema accepts each — every
   label a thread can take, with its `evidence:` line only on a
   must-fix and its summary counting that thread — and refuses a field
   dropped and a field renamed.

## Consequences

No PR body, classification or draft reply is read from a digest whose
report was found in its own prose, whose report carries a forged name,
or whose summary miscounts its own threads. Cost if wrong: an
integrator that opens with prose before its report is re-spawned as a
failed spawn — a read-only re-run — and one that miscounts is re-run
with the problem.
