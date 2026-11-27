# D-090: the cut is the baseline the main tree is read against at landing — `specstate` names the unproven changes and records what a landing merged

D-079 decision 2 cuts each worktree from a snapshot of the main
working tree, taken through a temporary index, and decision 3 hides
`.spec-kit/` from git; spec-build's D-058 lands the worktree's delta
into the main tree as uncommitted changes. Nothing read the main tree
at landing: the proof ran in the worktree, and the merge applied on
whatever the main tree had become since the cut.

**Decision** (amends D-079 decisions 2 and 5; the worktree module of
specstate is canonical here — the refusal is spec-build's D-070):

1. **The main tree is read against the cut.**
   `worktree_unproven(repo, worktree, spec_dir)` names the paths whose
   content in the main tree differs from the worktree's snapshot, is
   not committed since, and no landing of the spec merged — the work
   the worktree's proofs never ran on. The reading takes the main
   working tree's tree the way the snapshot does, through a temporary
   index: tracked edits, deletions and untracked files, ignored files
   excluded, the index untouched. The spec's own dir and `.spec-kit/`
   are run state and never count.
2. **Every merge records what it left, content-exact.**
   `worktree_merge` writes `<repo>/.spec-kit/landed/<spec>.json`:
   `{<T###>: {<path>: "<mode> <blob sha>"}}`, null where the merge
   deleted the path — the main tree's content at the delta's paths
   right after the apply. It is local run state, hidden by
   `.spec-kit/`'s own `.gitignore`, never committed and never status:
   the docs alone say a task landed, and the record only says which
   bytes this spec's proofs covered, so the next landing can tell a
   wave-mate's delta from an edit nobody proved. A file that is
   missing or cannot be parsed reads as no landings.
3. **The snapshot's tree is one function.** `_working_tree` takes the
   main working tree's tree; `worktree_snapshot` commits it and a
   landing reads through it.
4. **Nothing moves in the emit.** The cut, the refresh, the pruning
   and the payload are D-079's: the record is written by a landing and
   read by the next one, and no emit looks at it.

**Consequences**: a landing can refuse a main tree its proofs never
saw without refusing the two things D-079 and D-058 built — work that
was uncommitted when the tree was cut, and a wave-mate's landed delta.
The costs if this is wrong: each isolated landing passes over the
tree twice more, once to read it and once to record it, on top of the
cut's pass; the record is per machine and per spec — nothing prunes
it, it grows with the spec's landings and dies with the checkout — so
a landing on a checkout without it refuses until the landed paths are
committed; a record damaged by hand turns every landed path into a
refusal, never into a landing; and the reading is content-exact
against the cut, so a path whose content the main tree regains is no
refusal even when `git status` shows it. Pinned by spec-build's `tests/test_worktrees.py`
`IsolatedWorktreeTests::test_land_refuses_the_work_left_in_the_main_tree`,
`::test_land_refuses_a_main_tree_edited_since_the_cut` and
`::test_a_wave_mates_landing_does_not_refuse_the_next_one`.
