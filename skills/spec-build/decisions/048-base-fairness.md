# D-048: a red repository check is charged to the change only when the base passes

A repository whose approved base is itself red had no honest path
through the delivery pass: `audit.py regression` read FAIL on any
non-zero check, so every delivery in that repository was red on a
failure the change may never have touched, and dod gate 3 could not
pass. Charging an inherited red to the change is unfair twice over —
the change is blocked on work that is not its own, and the record
gains a failure claim nothing tied to what landed.

**Decision**:

1. **The head runs first; the base is consulted only for a red.**
   When the head's repository checks are green, nothing else runs and
   the result is PASS as before. Only a red repo check sends
   `regression` to a detached temporary worktree of the approved base
   (`git worktree add --detach <tmp> <Approved-at>`, then
   `scripts/gate.sh --repo <tmp>` — the pattern the delivery-pass
   contract names for a behavior-preserved run). The worktree is
   removed on success, on failure and on interruption; the main
   working tree and index are never touched; nothing is installed for
   the base run.
2. **Four outcomes per failing check, each from evidence.** PASS —
   the head is green. FAIL, charged to the change — the base is green
   at it, or the head fails where the base did not. PREEXISTING, not
   charged but listed — the head and the base are red on the same
   failures. UNKNOWN, neither passed nor charged — the base could not
   be checked: no checkout could be made, the base gate produced no
   report, or the check cannot run there.
3. **Failures compare, not exit codes.** The runners the gate already
   detects give failure signatures (pytest `FAILED` lines, unittest
   `FAIL:`/`ERROR:`, go `--- FAIL`, jest and vitest failing markers,
   the `[ERROR]` test lines of maven and gradle, cargo `... FAILED`,
   a TAP `not ok` line). Any failure the base did not have charges
   the check FAIL whatever else is true; failures that all stand at
   the base are PREEXISTING. When neither output yields a signature,
   the whole outputs compare with timings, dates, absolute paths and
   line numbers stripped: equality is PREEXISTING, difference is
   charged. Where exactly one output carries a readable failure, the
   comparison cannot decide and UNKNOWN is said instead of guessed.
4. **What is not charged takes a ruling** — the pattern D-037 set for
   hygiene suspects: `audit.py block` drafts one
   `- Regression: <check> — <ruling>` line per PREEXISTING or UNKNOWN
   check; the owner's ruling turns the row RULED and lets dod gate 3
   pass with the base's failures in view. A FAIL is never rulable
   this way. So a repository red on its base can deliver only by the
   owner's explicit, recorded yes.
5. **A builtin row stays charged without a base run.** The secrets
   and shell-syntax families scan the change itself, which does not
   exist at the base — there is no base verdict to ask for, and the
   change that added the line owns it.

**Consequences**: the delivery block gains an optional seventh line.
The honest limit sits in the open: in a repository whose checks need
an untracked environment (a virtualenv, `node_modules`), the base
reads UNKNOWN until that environment is reproducible — which is the
same red as today, with the reason now said. Signatures are read from
the gate's captured output tails; a runner whose failure lines fall
outside them falls to the stripped-output compare, which requires the
runs to agree beyond the failure lines to spare the change a charge.
Detection is unchanged by a ruling: fix the base, or make the
environment reproducible, and the check is judged on its own exit
again.
