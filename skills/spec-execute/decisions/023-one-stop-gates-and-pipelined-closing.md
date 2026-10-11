# D-023: One pre-execute stop (gates + approval together), a pipelined closing pre-check, and per-wave ticks

The pipeline's wall-clock sat in its seams, not its checks: before-audit
and approve were two back-to-back stops with only a record-write between
them, so a workflow run parked twice for one human conversation; the
closing audit's mechanical modes and its implementation-diff reviewer ran
only AFTER the closing-audit stop, serializing read-only greps behind the
ack; and every tick waited for the closing audit, leaving the post-ack
session a long bookkeeping stretch with stale digests as its evidence.

**Decision**: (1) The mechanical half of the before-audit's six gates is
now `audit.py pre-execute <spec-dir>` (clean tree, branch vs spec.md's
`Branch:` field, the tech-spec's recorded `Verify before implementing`
command — executed only with `--run`, like proofs; chains and
constitution stay in verify/check.py). `graph.py --run` runs it at the
pause and prints it; the stop's contract is ONE session: pre-execute →
judge the three semantic gates → record `Before-audit: passed` → seek
approval → `Status: approved` → freeze. The separate approve pause
survives only for the split case (pass recorded, approval withheld).
(2) When execute lands its last task, the read-only closing modes
(`audit.py scope`, `clean`, `dod --dry-run`, dry `proofs` listing — never
anything that executes test.md) run at the stop (`graph.py --run` prints
them; the spec-run workflow runs them before returning — zcode via
world.run, claude via one marker-split probe), and `--emit-spawns`
prepares `reviewer-diff.md` — the implementation-diff reviewer payload
(base from the recorded Before-audit SHA, the exact diff commands, doc
pointers), which the workflow spawns at the stop; `evidence`, `proofs
--run`, and regression stay the ack session's. (3) Ticks are per-wave
bookkeeping: once a digest plus scoped re-verification prove landing,
tick then (tick.py, the verified output as the done-note) or mark
`(implemented)` and batch — commits still wait for the closing audit,
and the closing audit re-checks every proof either way.

**Why**: the cheapest stop is the one that answers everything its
session was going to do anyway; results-not-claims at every pause
replaces honor-system gate checks (strictly stronger mechanically); and
fresh-evidence ticks beat deferred ticks because the digest and the
acceptance output are in hand at the wave boundary, not sessions later.

**Cost if wrong**: the merged stop could rush approval — mitigated by
the record still gating execute and approve remaining a HUMAN gate that
withholds sign-off on any doubt. The pre-check could be read as the
whole audit — the stop text and gates/before-audit.md name the three
semantic gates as still yours. Per-wave ticks could mask a later
rollback — ticks are doc state, converge re-opens regressed work, and
nothing commits before the closing audit passes. The reviewer payload's
base comes from the recorded Before-audit SHA; a wrong record poisons
the diff anchor — the same poisoning the scope diff always had, now
surfaced one stop earlier.
