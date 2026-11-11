# D-052: The tiny freeze covers the task list; intake's gate fails alone

A review of D-050/D-051 found three places where the recorded
contract let through what it meant to stop, or stopped what it meant
to let through:

- D-051 decision 6 left § Tasks out of the tiny freeze, so a new
  requirement and task appended under § Tasks of an approved tiny
  spec passed `check.py` and `freeze.py --verify`.
- D-050 decision 8's unresolvable-baseline FAIL ran in the full check
  too. A squash, rebase, or shallow clone loses the baseline commit
  under a docset whose intake passed long ago; the survey's equivalent
  is SKIPPED.
- A filled-but-red intent.md left the spec node READY, so
  `--run --span intent` asked for a spec draft over open questions.

**Decision**:

1. **The tiny freeze hashes § Tasks less its status tokens** (amends
   D-051 decision 6). Checkbox state, `(in-progress)`,
   `(implemented)`, `(fix n/5)`, `(fixed n/5)`, `done <date> —
   <proof>` sub-lines, a `Delivered:` record, and blank lines at the
   section's tail are normalized away; everything else in § Tasks is
   contract. § Evidence stays out of the hash. Adding, editing, or
   striking a task or requirement needs a fresh approval
   (`freeze.py --record --force`).
2. **Only `--intent-only` fails a baseline sha the repo cannot
   resolve** (amends D-050 decision 8). The full check notes it
   `intent staleness: SKIPPED`. A resolvable stale baseline still
   fails both.
3. **spec.md is drafted only from a green intent.** With spec.md
   missing, the spec node is READY when the intent node is DONE and
   BLOCKED on a red one; a red intent stops its own span with
   `AWAITING: intent: <the gate's reason>`.

**Consequences**: a tiny spec frozen under D-051 fails verification
until it is re-recorded (`freeze.py --record --force`; the delivered
example ships a re-recorded freeze). A dropped tiny-tier task is a
re-approval, not a status edit. The graph's intent node still probes
`--intent-only`, so a lost baseline keeps the intent node BLOCKED
until intent.md records a commit the repo holds.
