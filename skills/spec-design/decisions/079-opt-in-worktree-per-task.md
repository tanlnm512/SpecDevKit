# D-079: offer `--isolate worktree` — the emit gives each implementer payload a detached snapshot worktree and names it as the payload's repo

`--emit-spawns` names one repo on every payload: the main tree, where
the developer brief says wave-mates write beside each other and earlier
tasks' landed work sits uncommitted. The engine schedules by `Touches:`
and defers overlaps within a spec (D-039's wave) and across specs
(D-078); it has no way to give one implementer a tree of its own, and a
`Touches:` set the plan got wrong is felt by every wave-mate.

**Decision** (graph.py, the layout and the snapshot are canonical
here; the verbs are spec-build's D-058):

1. **`--isolate worktree` is an opt-in flag of `--emit-spawns` and
   `--run`; the default is unchanged.** Given, every implementer
   payload of the wave works in its own detached git worktree at
   `<repo>/.spec-kit/worktrees/<spec>/<T###>/`. The wave is still the
   one `schedule_wave` picks: isolation changes where a payload works,
   never which tasks run together. The flag needs one of the two
   executor modes (a usage error otherwise).
2. **The worktree is a snapshot of the main working tree, not of HEAD.**
   A later wave depends on earlier tasks' landed-but-uncommitted work,
   which no commit holds. Each worktree is checked out at a snapshot
   commit: a temporary index (`GIT_INDEX_FILE`) takes the tree's
   current state through `git add -A` — tracked edits and deletions,
   untracked files; ignored files excluded — and `git commit-tree`
   commits it, parented on HEAD (a root commit where HEAD is unborn).
3. **The snapshot is an object, not a commit of the user's.** It is on
   no branch and in no reflog; the main tree keeps its HEAD, its refs
   and its index. Its author is the kit and it is never signed, and
   only a worktree checked out at it keeps it alive. `.spec-kit/`
   ignores itself through its own `.gitignore`, so no worktree is ever
   staged or committed.
4. **The payload names the worktree as the repo, under one line that
   makes it the developer's only tree.** The header's `- repo:` line is
   the worktree and every repo-relative path in the payload is read
   under it; `- spec_dir:` stays the main tree's, so the digest file
   is written where `land` reads it. The line says the developer works
   only there and that the brief's ban on stash, reset and checkout
   still binds — the brief's shared-tree sentence is superseded for
   that spawn by the payload.
5. **The emit creates idempotently and prunes.** A missing worktree
   for a payload's task is created. One nothing was ever done in — its
   HEAD still the snapshot it was cut from, no file different — is
   removed and rebuilt from a fresh snapshot, so a task re-emitted
   after a deferral starts from a tree that holds everything landed
   since. One that holds work is kept as it stands, since a fix round
   continues there (spec-build D-058). The worktrees of tasks no longer
   open — ticked, struck, landed with no round open, or gone from the
   task list — are removed first.
6. **Outside a git repository the flag refuses; a worktree git cannot
   build refuses the wave.** Exit 2, the reason named, before any
   payload of the wave is written. `--dry-run` prints the plan
   (`would create`, `would refresh`) and touches nothing. A package
   that ships no developer brief writes no implementer payload: it
   builds no worktree either.
7. **`--explain execute` lists the worktrees on disk.** A claimed
   task's worktree is named with its path — an orphaned claim is
   resumed from there; one whose task is no longer open is reported as
   removable. The report and `--state-json` carry none of it: the
   state stays derived from doc state alone.

**Consequences**: the orchestrator can run implementers in parallel
without their sharing files, and each one sees the tree as it stands.
The costs if this is wrong: every isolated wave passes over the tree
and checks it out once per payload it creates or rebuilds — a task
deferred at the claim pays it again at each emit; a worktree that holds
work is kept as it was cut, so a fix round's tree lacks what landed
meanwhile, and the landing's own check is what refuses the overlap; the
worktrees live inside the
repository, hidden from git by the ignore file but not from a tool
that walks the tree without honoring ignores; and `git worktree add`
runs the repository's post-checkout hook like any other checkout.
