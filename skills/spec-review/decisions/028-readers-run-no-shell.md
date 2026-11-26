# D-028: drop the shell from every review reader, and hand it the diff as files

Five `spec-review-*` readers carried `tools: Read, Grep, Glob, Bash`:
the scout, the three lens reviewers and the confirmer — D-027 kept the
confirmer's shell for exactly the reason below. "Read-only" was prose
against a shell: a brief can ask a spawn not to run a test or touch the
tree, but nothing stops it, and every generated dialect that reads
`tools:` granted `bash` on opencode and Kilo and `Execute` on droid.
The shell had one job in each reader's ask — `git diff <base>` for a
lens reviewer, `git diff <base> -- <path>` for a confirmer, a look
around the tree for the scout — and the same asks seat roles with no
shell at all: `spec-review-quality` runs the triage editor, the final
assessor and the fix-loop assessment, and a read-only lens type runs the
fresh-eyes fix reviewer — asks that named a git command, three as an
instruction, for a type that cannot run one
(`plans/kit-hardening.md` § 2.2).

**Decision** (what the shell fetched becomes a file the oracle writes
and the ask names — the readers lose the shell together, never one
ahead of its supply):

1. **Five briefs drop the shell: `tools: Read, Grep, Glob`.**
   `spec-review-scout`, `spec-review-correctness`,
   `spec-review-security`, `spec-review-quality` and
   `spec-review-confirmer` each deny Bash beside Write and Edit. The
   fixer is the author and keeps its tools; the fix verifier was
   already shell-less (D-027). spec-review ships six readers and one
   author and nothing else — pinned, with the list closed, by
   `test_reader_briefs_grant_files_only`.
2. **The oracle writes what the shell used to fetch into the run
   folder (D-020), and the ask names the file.** Under
   `<run_dir>/reader-files/`: `diff.patch` — the change against the
   base, under the gate's pinned diff options so user config cannot
   reshape or execute it; `hunk-<path>-<digest>.patch` — the change to
   one path, one per finding at confirm and one per path at
   fix-review; `inventory.txt` — the scout's target file list and the
   repository's tracked tree; `part-<i>-of-<n>.txt` — a project shard's
   file list; `diff-with-fixes.patch` — the change as it stands after
   the fix loop. Untracked files stay in the ask: no diff carries them.
3. **Every ask but the fixer's names a file, never a git command.**
   The five that held a shell, and — because their types hold none —
   triage, cross-lens, the final assessment, the fix verification and
   the fix-loop assessment. The fixer's ask keeps its git sentence. The
   `ask` result stays `{status, ask}`: the paths are in the text.
4. **A reader ask carries `run_dir`, the path `run-init` returned.**
   Without a run folder — missing, or holding no `run.json` — the ask
   is `status: error` naming stage `ask`: never a bare ask a shell-less
   reader could answer only with an empty list that reads as a clean
   diff. A diff that cannot be produced — the repository is gone, a
   base that does not resolve — is a named absence in the ask
   (`…: ABSENT — <why>`) with the answer it forces: `not run: <why>`,
   never a finding and never `verified`. An empty hunk is ruled the
   same way: the change does not touch the path, so the finding
   predates it. A wave is refused whole, naming the bare ask.
5. **Read-only is mechanical on every dialect through the existing
   generators.** The Claude frontmatter `tools:` line; opencode and
   Kilo deny `edit` and `bash`; droid collapses the set to
   `read-only`; omp's registry derives `read, grep, glob` from the same
   line. Pinned per target for all six readers by the reader tables in
   `tools/tests/test_agent_defs.py` — `READER_BASH` denies the shell
   for every reader, and `SHELL_READER_ROLES` is pinned empty.
6. **The records follow.** `contracts/run-sequence.md` carries
   `run_dir` in the reader ctx keys; `contracts/panel.md`, SKILL.md and
   `protocol/panel-protocol.md` say in one sentence each that a reader
   reads the diff file; `GLOSSARY.md` gains `diff file`;
   `HARNESS-FACTS.md` gains the verified row; the rule ledger's
   "reviewers never re-run the repo's suites" moves from prose to
   machinery; the root `agents/` personas are regenerated.

**Consequences**: a reader can no longer look at anything the oracle
did not hand it — an ask that under-supplies is a worse review, not a
blocked one. A diff too large for one read is paged through the file
(the `over_cap` sentence says so); a tree the oracle could not list is
the scout's named gap; a reader told nothing about a path reports
`not run`, never a guess. The run folder gains `reader-files/`, which
its own `.gitignore` already covers and the run's gc removes with it.
Every session now passes `run_dir` in each reader ctx — the ctx keys
say which — and one forgotten key stops the run at `O ask` instead of
producing a review that read nothing. The cost if wrong is a reader
denied something the oracle does not write: it surfaces as a `not run`
in a report and is fixed by adding a file to the ask, never by handing
a reader its shell back. D-027 point 5's "it holds that shell until the
plan item" is closed here.
