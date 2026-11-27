# D-065: `drop` discards the task's worktree, as `release` does — a worktree git will not remove never undoes the drop

D-058 decision 6 names `release` as the verb that discards the
worktree with the claim and `fail` as the one that keeps it. `drop`
was unnamed: a dropped task's worktree stayed on disk with the dropped
work in it until some later emit under isolation happened to write a
wave.

**Decision** (amends D-058 decision 6; mark.py):

1. **`drop` removes the task's worktree once the entry is struck**,
   with the work in it, and says so on its line: `dropped T001 (D-###)
   — struck in task.md, the decision stays visible; its worktree
   <path> is removed with the work in it`. A task with no worktree
   prints the line it always did.
2. **An unremovable worktree never blocks the drop, and never fails
   silently.** The ruling is the user's decision, so the marker write
   stands and the exit is 0; the warning on stderr names git's reason
   and the by-hand command — `warning: the worktree was NOT removed —
   <git's reason>; remove it by hand: git worktree remove --force
   <path>` — and the line on stdout says `its worktree <path> is NOT
   removed`.
3. **One wording and one removal for the verbs that discard.**
   `release` and `drop` share the removal, and `land`, `release` and
   `drop` share the warning.

**Consequences**: a dropped task leaves no tree behind in the ordinary
case, and the three verbs say the same thing when git refuses. The
costs if this is wrong: a leftover is not retried until an emit under
isolation writes a wave — the pruning runs inside the wave's write, so
an empty wave prunes nothing — which is why the by-hand command is
named; `--force` once does not override a locked worktree (git asks
for `-f -f` or an unlock first), and git's own reason in the warning
is what says so; and a drop refused for its ruling — a `D-###`
tech-spec.md does not define, or any drop at `Tier: tiny` — removes
nothing, as before. Pinned by `tests/test_worktrees.py`
`IsolatedWorktreeTests::test_drop_discards_the_worktree_with_the_task`
and
`::test_a_worktree_git_will_not_remove_does_not_undo_the_drop`.
