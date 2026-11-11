# D-051: The engine enforces what the execute prose promised

A review of the execute span found rules that lived only in prose, and
loose ends from D-050:

- SKILL.md required a wave's tasks to share no file, yet
  `--emit-spawns` emitted two tasks that both touch `repo/calc.py`.
- `(implemented) (fix 1/5)` read as landed: execute reported done and
  the delivery reviewer's payload was emitted while a fix was owed.
- A session killed mid-wave left `(in-progress)` claims the engine
  answered with "no payloads to emit" and exit 0.
- Fix payloads named a note path; the builder brief promised the
  failure evidence itself.
- A harness with registered agents received the brief twice (system
  prompt and payload), and the builder read `Long foreground tasks`
  twice (its engineering rules and the shared protocol).
- Tiny tier had no approval record, so a bare Status flip opened
  execute (D-050 decision 1 left it out).
- The survey-staleness WARN still fired on specs-only commits, and
  spec-execute could emit the contract review.

**Decision**:

1. **The engine picks the wave.** Runnable tasks are admitted in
   task-id order only when their files overlap no task already
   admitted and no `(in-progress)` task; a task naming no files runs
   alone. Every other runnable task prints `deferred: T### (<why>)`
   and waits for the next emit.
2. **`(fix n/5)` is an open round.** It voids an `(implemented)`
   beside it: the task is runnable again and execute is not done. A
   landed round is rewritten `(fixed n/5)`, which keeps the count and
   reads as closed. `(fix 5/5)` stays the cap.
3. **A fix payload carries its evidence.** `notes/T###.md` — where
   the orchestrator records each round's failing command and output —
   is embedded verbatim (last 200 lines). Without it the payload tells
   the builder to return blocked and the emit prints `evidence
   missing`.
4. **Held execute is named, never silent.** With execute ready and no
   task spawnable, `--run` and `--emit-spawns` print `AWAITING
   ORCHESTRATOR: execute` and each held task with what it needs; a
   claimed task is flagged as a possible orphan on every emit.
5. **One brief per agent.** `--native-agents` emits payloads that name
   their agent type and omit the brief body; the default stays
   self-contained for harnesses without registered agents. In both
   forms a shared-protocol section whose heading the brief already
   carries is left out of the payload.
6. **Tiny tier is frozen too** (amends D-050 decision 1). A tiny
   `Status: approved|active|done` without `approvals/approval.md`
   fails `check.py` and blocks approve. The freeze hashes spec.md
   without its Status line, § Tasks, and § Evidence — the in-file
   status holder moves freely. No contract-review record is required
   at tiny tier.
7. **The contract review is the authoring package's.** `--repair
   approve`, and the frontier's contract-review payload, are refused
   by a package that does not ship `agents/designer.md`.
8. **Survey staleness reads code, not HEAD.** `check.py`'s WARN and
   the converge loop stay fresh when only the specs tree changed
   since the survey baseline, as the intent gate already did.
9. **Shared protocol rule 5 binds doc authors.** One artifact per doc
   author; an implementer writes its task's `Touches:` set and tests.
10. **`**Lifecycle**: v2` leaves the task template** — no script reads
    it.

**Consequences**: docsets using `(implemented) (fix n/5)` for a landed
fix must rewrite the marker `(fixed n/5)`, or the task re-opens. A
tiny spec approved before this decision needs `freeze.py --record`
once (the delivered example ships its record). The approve node's
done-condition and the execute/tick-commit rows of the contract table
are reworded. spec-execute D-034 records the orchestrator-side
procedure these mechanics serve.
