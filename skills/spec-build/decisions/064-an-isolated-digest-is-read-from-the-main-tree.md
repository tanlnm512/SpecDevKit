# D-064: an isolated developer's digest is read from the main tree's spec dir — the payload's two exceptions are stated

D-058 decision 1 says the payload names the worktree "under one line
making it the developer's only working tree". That line and the rest
of the payload disagreed: the `## Digest file` section asks for the
file under the main tree's spec dir, and the brief allows the fix
round's note there. `mark.py land` already read the digest from the
main tree's spec dir, with the worktree present or not; a developer
that followed the line instead wrote into the worktree's copy of the
spec dir, where no verb looks.

**Decision** (adopts spec-design D-088, which amends D-079 decision 4
and whose line is canonical; it amends D-058 decision 1's "one line"):

1. **`land` reads the digest where the payload says to write it** —
   `<spec_dir>/digests/wave-<N>/implementer-T###.md` under the main
   tree — while the task's worktree exists and after it is merged. The
   code is unchanged; this pins it.
2. **The payload's line states the two exceptions**: the digest file
   and, on a fix round, the note `notes/T###.md` — both under the main
   tree's spec dir, never in the worktree's copy of it.
3. **The verbs are unchanged in what they read.** A digest written
   inside the worktree's copy of the spec dir is not found: `land`
   refuses "none on file under digests/", and the task stays claimed.

**Consequences**: the developer's two writes outside the worktree are
named by the payload that forbids the others. The costs if this is
wrong: the exception is prose to the developer — nothing redirects a
digest written into the worktree's copy, so the refusal and a re-spawn
are what meet it; and the note is the same — a note appended in the
worktree's copy reaches the main tree only as part of the delta, and
is refused at the landing when the main tree's note has moved since.
Pinned by `tests/test_worktrees.py`
`IsolatedWorktreeTests::test_land_reads_the_digest_written_in_the_main_tree`.
