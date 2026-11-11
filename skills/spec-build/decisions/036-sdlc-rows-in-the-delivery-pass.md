# D-036: The delivery pass runs the regression gate and records docs, rollback, work type, and parked work

A gap review of the build and verify phases against a full SDLC found
the delivery pass leaving real work to memory:

- dod gate 3 (REGRESSION) was MANUAL, although spec-review's gate.sh
  already detects and runs a repo's own checks.
- A new dependency, or a configured dependency audit, never surfaced
  at the commit gate.
- Nothing asked whether the README, API docs, CHANGELOG, or migration
  notes still matched the change.
- tech-spec.md's rollback table and plan.md § Rollout were written at
  design time and never checked against a proof.
- A bugfix did not have to show a failing test before its fix, and a
  refactor did not have to show behavior preserved.
- WARN/NIT findings ruled "later", spec-review residual risks, and
  deviations were stated once in the delivery summary and lost.
- Archive moved the spec and kept no retrospective. The spec's D-###
  decisions left the active tree with it.
- `audit.py scope` diffed from `Approved-at`, so another spec's commits
  landed in the meantime listed as UNMENTIONED.

**Decision**:

1. **The regression gate is automatic.** spec-build ships spec-review's
   `gate.sh` and `gate_helpers.py` as byte-identical copies, pinned by
   `tools/tests/test_parity.py` (spec-review's are the master).
   `audit.py regression` runs them against the approved base. dod gate
   3 reads PASS or FAIL from the result, or NONE when no repo checks
   are detected. NONE is never a pass: the orchestrator runs the repo's
   documented check command and records its output. The gate's
   dependency-manifest row prints as `deps:` lines in both commands.
2. **The delivery note.** `specs/<name>/notes/delivery.md` holds the
   delivery pass's own facts. Each one may honestly say `none —
   <reason>`. dod adds three gates that read it:
   - gate 11, DOCS IMPACT: a `Docs impact:` line must exist, and every
     file it lists must be in the diff.
   - gate 12, ROLLBACK: every tech-spec rollback row and every filled
     plan § Rollout item must cite an existing TC or carry a `Rollback:
     <key> — <ruling>` line. Tiny tier reads N/A.
   - gate 13, WORK TYPE: spec.md `**Type**: bugfix | hotfix` needs a
     notes/T###.md `## Regression test (red before fix)` record, and
     `refactor | upgrade` needs a `Behavior preserved:` line, proven by
     running the proofs against a worktree of the approved base. Other
     types read N/A.
   notes/ already rides C2 and sits outside the approval freeze.
3. **The developer brief.** For a bugfix or hotfix, the developer
   writes the reproducing test first and appends its red run to its own
   notes/T###.md. This widens the existing fix-round exception to
   specs/. The developer also updates the user-facing docs its behavior
   change makes wrong, the one documented exception to the `Touches:`
   bound.
4. **The hotfix path** is a `Tier: tiny`, `Type: hotfix` spec: failing
   test first, then the fix. The delivery pass is unchanged.
5. **Parked work goes to `specs/BACKLOG.md`.** `tick.py --park '<item>
   :: <source>'` appends one date-free line, `- <spec> — <item>
   (source: <source>)`, and does not repeat a line already there. Every
   tick or park run lists the spec's parked lines. scope treats
   BACKLOG.md as a kit-owned surface, like INDEX.md.
6. **Archive writes `retro.md`.** `archive.sh` calls `retro.py`, which
   assembles the archived dir's retro.md from the spec's records: task
   states and fix rounds, D-### decisions (those past the frozen
   tech-spec prefix are marked as deviations), the delivery note, the
   spec's BACKLOG.md lines, and local telemetry counts. It writes no
   prose of its own. It then appends each D-### title to
   `specs/context/decisions.md`. A retro failure after the move is
   reported, never rolled back, and the rerun command is printed.
7. **Scope is per spec.** Once commits have landed since the base, only
   this spec's files are judged: its tasks' `Touches:`, the working
   tree, and commits whose message names `(<spec-name>)` or that touch
   its spec dir. A file that only other commits changed lists as
   OUTSIDE and is not judged. C1 carries the `(<spec-name>)` scope so
   it stays attributable.

**Consequences**: dod grows from ten gates to thirteen and its title
counts them. "manual gates remain" is computed from the gate states.
The `deps:` line and the delivery note are new delivery-summary
inputs. graph.py, check.py, and the templates are unchanged.
Commit-message attribution is a heuristic, so a hand-made commit with
no `(<spec-name>)` scope that never touched the spec dir reads as
foreign. That is acceptable: before delivery the spec's work is
uncommitted and counts in full.
