# D-009: Sub-repo targets — the `repo` arg, resolved absolute

In a multi-repo workspace whose root is not itself a git repository, a
whole-project review targets a sub-repo via the `repo` arg (absolute,
or relative to the working directory). The scope phase resolves it to
the repo's absolute toplevel (`git -C <dir> rev-parse --show-toplevel`)
before anything else runs; every git call (`git -C`), the gate
(`gate.sh --repo`), and the file paths handed to subagents (absolute)
root there. An arg that resolves to nothing fails loudly with the fix
in the conclusion. Supported for `target: project` only; change, branch
and PR targets refuse it — run those from inside the repository.

**Why**: the masters assumed the workspace root is the git repository.
In a workspace of sibling repos that assumption makes project mode
silently review nothing (`git ls-files` fails, "no tracked source
files matched", clean exit) — the failure mode is a confident empty
report, the worst shape a review tool can produce. Worse, the runtime's
cwd is not guaranteed to be the workspace root (observed live: the cwd
followed the operator's shell), so even a relative `git -C <repo>` can
miss. Resolution must therefore produce an absolute path, and every
seam must use it — one relativized seam silently reviews the wrong
tree. Absolute paths in the asks are deliberate: they resolve in every
subagent's file tools regardless of that agent's own cwd.

**Cost if wrong**: a sub-repo diff/branch/pr review shipped on the same
plumbing but unverified would risk attributing the wrong repo's diff to
the review — so those targets refuse the arg until they are verified
end-to-end the way project mode has been (a 441-file live audit); and
`gh pr checkout` has no `-C`, so pr mode needs a cd-wrapped probe of
its own before it can honor `repo` at all.
