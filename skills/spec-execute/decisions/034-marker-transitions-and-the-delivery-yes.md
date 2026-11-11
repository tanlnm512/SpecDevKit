# D-034: Marker transitions, fix rounds, and the delivery yes

A review of this skill found its run procedure underspecified or
contradictory where it mattered most:

- Nothing said who writes which task marker, or what a resumed session
  does with `(in-progress)` claims a dead wave left behind.
- `blocked:why` counted as a fix round, and rounds 1–3 demanded "the
  SAME builder", which most harnesses cannot continue.
- graph.py called tick-commit a HUMAN GATE while the delivery pass
  read as autonomous through both commits; `ship` claimed to refuse
  "unless test and review are green", a result nothing records.
- The builder was told to "revert your WIP" in a tree its wave-mates
  share and where no earlier task is committed yet.
- A spec named `build`, `test`, `review`, or `ship` collided with the
  router's verbs; the trigger "build" matched any build request;
  `audit.py dod` cited `gates/dod.md`, which does not ship.

**Decision**:

1. **One transition table** (SKILL.md § Task markers). The
   orchestrator writes every marker; builders return digests. The
   engine mechanics behind it are spec-author D-051: an open
   `(fix n/5)` re-opens the task, `(fixed n/5)` closes the round.
2. **Resume settles orphans first.** For each claimed task: read the
   diff of its files, re-run its acceptance commands, then write
   `(implemented)` or clear the claim. The tree is never reset.
3. **Only failed implementation opens a fix round.** `blocked:why`
   gets a ruling or a route to `/spec-author` and costs no round. The
   orchestrator records each round's failure evidence in
   `notes/T###.md`; the round continues the same agent where the
   harness allows and is otherwise a fresh spawn carrying that file.
   `n` counts failures, so `(fix 5/5)` is the cap and at most four
   rounds run before adjudication; round 4 goes one tier up.
4. **The tick-commit gate is the user's.** The delivery pass ends in
   a summary; ticks and both commits follow only the user's explicit
   yes to it.
5. **`ship` is the whole pass.** It re-runs the proofs, the regression
   gate, and the review instruments, then presents the summary — no
   persisted proof record was added to make a refusal checkable.
6. **The builder undoes only its own edits, by path** — it deletes
   the files it created and reverses its own changes; `git stash`,
   `reset`, `checkout`, `restore`, and `clean` are forbidden. An
   acceptance command red only in a file outside its `Touches:` is
   reported in the digest's `note`, not fixed.
7. **Verbs win the first word.** `build|test|review|ship|continue|
   resume` are always verbs; a spec so named is addressed as `spec
   <name>`.
8. **`tick.py` refuses a task whose fix round is open.**

**Consequences**: the builder digest gains a `note` field. The
builder may append to `notes/T###.md` on any fix round (it was "from
round 2"). `test` and `review` remain rehearsals of delivery-pass
steps; passing them earlier saves nothing at `ship`.
