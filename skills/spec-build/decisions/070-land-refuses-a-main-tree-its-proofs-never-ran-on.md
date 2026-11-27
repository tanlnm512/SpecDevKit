# D-070: `land` refuses a main tree its proofs never ran on — an uncommitted change made since the worktree was cut, outside what this spec landed

D-058 decision 3 proves the worktree and then merges its delta into
the main tree. Its costs name the hole and live with it: "a developer
that edits the main tree anyway leaves its work in the shared tree and
lands an empty delta — `land` says so when a worktree holds no change".
Said, and landed: with a proof green in a worktree holding no change,
the task went `(implemented)` over edits no acceptance command had ever
run, and the line explained itself with the very fact that should have
stopped it. Any uncommitted edit beside the delta was merged the same
way — the tree the work joined was never the tree that was proven.

**Decision** (amends D-058 decisions 3 and 4 and lifts that cost;
mark.py is canonical for the refusal — the reading and the record are
spec-design's D-090):

1. **With a worktree present, `land` refuses before the proofs while
   the main tree holds an uncommitted change its proofs never saw —
   exit 1, nothing written, the task stays claimed, the worktree
   stays.** The lines name each path and both trees, and the way on:
   move the work into the worktree, or commit or stash what is not the
   task's, and land again. The digest's `implemented` is no evidence
   for a tree the proofs did not run in.
2. **What refuses is read against the cut, not against `git status`.**
   A path refuses when its content in the main tree differs from the
   snapshot the worktree was cut from, is not committed since, and no
   landing of this spec merged it. Three things never refuse: what the
   main tree already held at the cut, since it was in the tree the
   proof runs in (D-058 decision 2); what a landing of this spec
   merged, each proven in its own worktree and uncommitted by D-058
   decision 4; and a change committed since the cut — the owner's
   commit boundary. Run state never counts: the spec's own dir and
   `.spec-kit/`.
3. **Every landing records what it merged, content-exact.** A
   file-disjoint wave lands its tasks one after another, and the
   second's cut predates the first's merge — without the record the
   first landing's own delta would refuse the second. The record is
   spec-design's D-090 (`.spec-kit/landed/<spec>.json`); unreadable,
   it reads as no landings, and the next landing names those paths —
   the refusing side, never a landing over unproven work.
4. **The "nothing to merge" line says only what is true.** A worktree
   holding no change reaches the merge only when the main tree is as
   it was cut; the line no longer explains itself with a developer who
   worked in the main tree.
5. **Nothing else moves.** Without a worktree the landing is D-039's.
   A delta the main tree will not take is still refused by
   `git apply --check` (D-058 decision 5), after this check — a
   conflicting edit that is uncommitted is named here first, as work
   nobody proved. An edit made in the main tree while the proofs run
   is merged: D-058's cost stands for that window, the pre-tick proof
   pass being the first proof of the combination.

**Consequences**: an isolated task lands only over a main tree its
proofs cover or this spec has itself proven. The costs if this is
wrong: an unrelated uncommitted change in the main tree — someone
else's work in progress, a developer's edit in the wrong tree — blocks
every isolated landing until it is committed or stashed; that is the
trade-off, since the proofs must cover the tree the work merges into.
A landing pays two more passes over the tree (the reading before the
proofs, the record after the merge) on top of the cut's; a change
committed since the cut joins the merged tree without the proof having
seen it, as any landing's delta does; the record is local to the
machine, so a wave-mate's landing on a checkout that has none refuses
until the landed paths are committed; and a landing that has already
merged but cannot write its record warns and stands — the next landing
refuses on those paths. Pinned by `tests/test_worktrees.py`
`IsolatedWorktreeTests::test_land_refuses_the_work_left_in_the_main_tree`,
`::test_land_refuses_a_main_tree_edited_since_the_cut`,
`::test_a_wave_mates_landing_does_not_refuse_the_next_one` and
`::test_land_reads_the_digest_written_in_the_main_tree`.
