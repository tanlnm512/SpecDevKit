# D-067: a stale eval result is removed — never restamped, never kept

A result carries the `surface:` hash of the skill it ran against, and
D-061 reads it `stale` once that hash moves. Nothing said what happens
next. The GLOSSARY row's "append-only" kept the file for good, and a
stamp is never rewritten, so a skill read `stale` until somebody
re-ran its case — and shipped verdicts that no longer described the
code, beside the code. Two of the first seven results removed under
this decision (spec-build E7 and E9) matched no commit on `main`: they
were recorded on a working tree that never landed.

**Decision**:

1. **A stale result is deleted from `evals/results/`.** `evals.py
   list` is the check: a result reading `stale` goes, and `fresh` and
   `unstamped` results stay. Nothing is restamped or re-dated — a
   re-run records a new dated file, as before.
2. **"Append-only" now means a result is never restamped and is
   removed once stale** (the GLOSSARY row): the protection is for a
   record's content, not its existence. An unstamped legacy result is
   not stale (D-061) and stays.
3. **Removal stays out of the gate**, like coverage and freshness
   (D-061).

**Consequences**: history stays in git — `git show <commit>:<path>`
recovers a removed result. grade.py's S4 counts results by existence,
so a skill whose stale results were removed scores lower until its
cases are re-run, and `report`'s coverage and Findings counts fall with
the files: a removed failing result takes its evidence with it, so the
gap it recorded needs an open item of its own. A removal changes no
hashed part, so it never makes a sibling result stale.

First applied 2026-11-25 to spec-build e7, e8, e9 and spec-release
r1–r4.
