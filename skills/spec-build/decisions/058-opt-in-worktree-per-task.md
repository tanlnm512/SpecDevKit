# D-058: land each task from its own worktree on request — `--isolate worktree` merges the tree's delta into the main tree, `release` discards it

The developer brief describes one shared tree: wave-mates write beside
each other, earlier tasks' landed work sits uncommitted in the same
files, and a developer undoes only its own edits by path. That is safe
while every developer honors its `Touches:` — nothing isolates one
implementer's half-written edit from a wave-mate's acceptance command,
or from a `Touches:` set the plan got wrong. D-057 keeps two specs off
one file; it gives one task no tree of its own.

**Decision** (the flag, the worktree's layout, its snapshot and the
emit are canonical in spec-design's D-079; adopted here in the same
words — this skill's half is the verbs):

1. **`--isolate worktree` is opt-in, and without it nothing changes.**
   On `graph.py --emit-spawns` or `--run`, each runnable implementer
   payload works in its own detached git worktree at
   `<repo>/.spec-kit/worktrees/<spec>/<T###>/`, and the payload's
   `- repo:` line names that worktree under one line making it the
   developer's only working tree — the brief's ban on stash, reset and
   checkout still binds. The default stays the shared tree, byte for
   byte.
2. **The worktree is a snapshot of the main working tree, not of HEAD.**
   A later wave depends on earlier tasks' landed-but-uncommitted work.
   The emit builds the snapshot through a temporary index
   (`GIT_INDEX_FILE`) and `git commit-tree`: an unreferenced commit on
   no branch — no ref, no reflog entry, no index change in the main
   tree. Not a git repository: the flag refuses, exit 2, naming the
   reason. The emit creates a missing worktree, rebuilds one nothing
   was ever done in from the current tree, keeps one that holds work as
   it is, and removes the worktrees of tasks no longer open.
3. **`land` proves the worktree, then merges it.** With a worktree
   present, the task's acceptance commands run with the worktree as
   the repository. Then `land` builds the worktree's whole delta
   against the snapshot it was cut from — tracked and untracked files
   alike, binary content included, through a temporary index in the
   worktree — and `git apply --check`s it in the main repository.
4. **A clean delta lands in the working tree alone.** `git apply`
   writes the files and nothing else: nothing staged, nothing
   committed, HEAD and every branch as they were, the index
   byte-identical — the work sits in the main tree as uncommitted
   changes, where a shared-tree task's would. The worktree is removed
   and the task lands as usual.
5. **A delta the main tree will not take clean is refused — exit 1,
   nothing written.** The message names both trees and the conflicting
   paths; the worktree stays and the task stays claimed: settle by
   hand, then land again or release. The apply is all-or-nothing —
   never a merge commit, never a conflict marker in either tree.
6. **`release` discards the worktree with the claim; `fail` keeps it.**
   A release means the work is not wanted: the next emit re-spawns the
   task in a fresh worktree. A failed round's work is where the next
   round continues, so its payload reuses that worktree as it stands.
7. **A delta is measured from the snapshot, not from the worktree's
   HEAD.** The snapshot's sha is recorded in the worktree's own git
   dir, so a commit made inside the worktree — which the brief
   forbids — loses no work.

**Consequences**: parallel implementers stop sharing files, and a
landing is still one uncommitted change in the main tree, with no
commit and no index write. The costs if this is wrong: every isolated
task pays one pass over the tree and one full checkout — disk and time
proportional to the repository, paid again at every emit that finds its
worktree untouched; ignored files are not in a snapshot,
so a worktree lacks what the tree ignores (dependencies, build output)
and a proof needing them runs ENV-BLOCKED or red there; the delta was
proven in its worktree, never in the main tree it joins — the first
proof of the combination is the next proof pass; a developer that
edits the main tree anyway leaves its work in the shared tree and
lands an empty delta — `land` says so when a worktree holds no
change; the proofs run from the worktree's root, wherever the spec
dir's grandparent sits in the repository, so a tree whose specs are not
at its root runs them from another directory than the shared tree does;
and a conflict costs a hand-settled tree, the task waiting claimed
until someone settles it.
