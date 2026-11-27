# D-088: the isolated worktree's payload names its two exceptions — the digest file and the fix round's note are written in the main tree's spec dir

D-079 decision 4 keeps `- spec_dir:` on the main tree so the digest
file is written where `land` reads it, under a line making the
worktree the developer's only tree. The payload contradicted itself:
the line said the main tree was not the developer's to touch, the
`## Digest file` section asked for `<spec_dir>/digests/wave-<N>/
implementer-T###.md` under it, and the developer brief allows
`notes/T###.md` there as well. The worktree also carries a copy of the
spec dir, the snapshot holding it — and a digest written into that
copy, by a developer taking the line at its word, is found by nothing:
`mark.py land` refuses "none on file under digests/".

**Decision** (amends D-079 decision 4; `ISOLATED_WORKTREE_LINE` in
graph.py is canonical; the verb's half is spec-build's D-064):

1. **The line states both exceptions and where they live.** After the
   sentence that makes the worktree the only tree: "Two exceptions,
   both under the main tree's spec dir (<spec_dir>): your digest file
   (the `## Digest file` section's path), and on a fix round the note
   `notes/T###.md` the brief lets you append to — written there and
   never in this tree's copy of it, where nothing reads them."
2. **Nothing else moves.** The worktree is still the only tree for the
   task's work, `- spec_dir:` still names the main tree's, and every
   verb still reads the digest and the note from there.

**Consequences**: a developer reading the payload no longer has to
choose between two of its sentences. The costs if this is wrong: the
line is two sentences longer on every isolated payload; the warning is
prose — a note appended to the worktree's copy still travels as part
of the worktree's delta and is refused at the landing when the main
tree's note moved meanwhile, since the engine does not take the spec
dir out of the delta; and a fix round's payload, which embeds the note,
reads the main tree's copy only. Pinned by `tests/test_worktrees.py`
`IsolatedWorktreeTests::test_the_payload_names_the_worktree_as_the_developers_only_tree`.
