# Before-audit gate (the plan's only pre-implementation audit)

Runs once, when the execution frontier first becomes eligible: `verify`
done — `check.py <spec-dir>` green — with (for large specs) the reviewer's
report in, and before the execute node ever spawns a task. It is a node in
the workflow graph with one mechanical trigger, not a position in a fixed
sequence: it does not repeat per phase, per wave, or per resumed session,
and it is never re-run just because time passed. The closing audit is its
only counterpart; everything between the two audits is ungated
implementation. In `graph.py --run` this gate surfaces as an
orchestrator-judgment stop: `AWAITING HUMAN: before-audit`. It shares the
pause prefix of the five human gates — clarify, approve, an undetermined
research-gate, the closing-audit judgment, and tick-commit, the set that
is never auto-satisfied — but is not one of them: before-audit is the
orchestrator's six-gate judgment (below), which no script can perform
either, so the auto-trigger pauses it the same way.

## The six gates

1. **Preconditions** — task.md's phase order and dependencies are
   internally consistent. No task depends on a later phase: `check.py`
   fails cross-phase `(after T###)` chains mechanically; the rest —
   whether a declared dependency is *real*, not just phase-ordered — is
   yours to judge.
2. **Fresh baseline** — the tech-spec code guide's "verify before
   implementing" command plus the project's test command, both green
   before any task spawns. Any failure the closing audit finds later is
   then attributable to this plan's implementation, not pre-existing rot.
3. **Clean tree** — `git status --porcelain` shows nothing uncommitted.
   In a non-git repo this gate degrades to an explicit
   `SKIPPED (not a git repo)` note — a skipped note, never a silent pass.
4. **Already-done sweep** — spot-check survey.md for any task that looks
   already satisfied; note it so Execution mode skips spawning it.
5. **Isolated branch/workspace** — cut the branch spec.md's `Branch:`
   field names (or set up a worktree if the harness offers one — prefer
   its native worktree tool, and ask before creating a worktree).
   Implementation never starts on main/master, or on a branch the user is
   actively working in, without explicit consent. The fresh branch also
   anchors the closing audit's scope diff: its starting HEAD is exactly
   the pre-plan state. Where no git exists, the branch/HEAD anchoring is
   unavailable: record the branch as `SKIPPED (not a git repo)` and
   anchor the closing audit's scope expectation on the task files'
   intended-files union instead.
6. **Constitution gate** — read specs/CONSTITUTION.md; the plan and every
   task comply with each article. Semantic, yours to judge — but presence
   and fill-level are mechanical: `check.py <spec-dir> --constitution` (or
   the full check, which folds this in and escalates it from WARN to FAIL
   once a second spec exists in the repo) fails on a missing, empty, or
   still-templated constitution. From here on, every implementer payload
   carries it.

## Pass and failure

Passing all six, record `Before-audit: passed @ <sha>` in task.md's
header block — `passed @ -` where no git sha exists (the accepted non-git
recording form; never an invented sha). Resume, the closing audit, and
graph.py's before-audit node read that line; a later failure attributes to
this plan only from a recorded green baseline. Git-dependent outcomes
above (clean tree, branch, baseline sha) appear in the record as explicit
`SKIPPED (not a git repo)` notes, never as silent passes.

Any gate failing → fix the cause (spec, plan, or re-brief) before
Execution mode spawns anything. The gate is followed by the **user
approval** gate (spec.md `Status: approved`) — see SKILL.md § Verification
(verify → before-audit → approve).
