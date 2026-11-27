# D-008 — The integrator's digest is validated against its mode's grammar before it is read

**Status**: accepted (2026-11-26)

## Context

The integrator returns one digest in its mode's grammar — `title:`,
`body:`, `changed:`, `flags:` for `pr-text`; `thread` blocks, then
`summary:` and `injection:` for `threads` (`agents/integrator.md`).
No script read either: the orchestrator took the rewritten body, the
classifications and the draft replies from whatever came back, so a
digest with a field missing, a `task:` that was not a task id, or an
`evidence:` line on a thread that was not a must-fix was as usable as
a good one. spec-design D-074 ships one schema module for every digest
grammar.

## Decision

1. **The two grammars are schemas.** `scripts/digests.py` carries them
   quoted from the integrator's brief — shipped byte-identical with the
   other digest-grammar skills and pinned by
   `tools/tests/test_parity.py`. A thread's fields are ordered and
   typed; `evidence:` belongs to a `must-fix` and to nothing else.
2. **Every returned digest is validated before anything is read from
   it**: `python3 <skill_dir>/scripts/digests.py validate integrator
   <pr-text | threads>` — exit 0 valid, exit 1 with the problems. A
   malformed digest is a fix and run again: the problems go back to the
   same mode and it is re-spawned; no body, classification, or draft is
   read from it in the meantime.
3. **The rule is stated once** in `contracts/run.md` § Digests and what
   the orchestrator checks; SKILL.md carries a pointer alone.

## Consequences

No PR body and no draft reply reaches the user from a digest the
schema rejected. Cost if wrong: a schema stricter than what the
integrator writes re-runs a correct digest — a read-only re-run — and
the cure is a schema edit in the spec-design master, replicated.
