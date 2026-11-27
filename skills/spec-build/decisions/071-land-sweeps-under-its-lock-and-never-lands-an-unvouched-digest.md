# D-071: land sweeps under its lock — a busy lock refuses, and a digest no request row records lands nothing

D-041 made the digest file on disk the primary evidence a landing
reads, and D-055 decision 4 put the provenance sweep before the read.
The sweep ran before land took `.task.lock`, and its own lock wait was
swallowed into a warning: with another writer holding the lock, the
sweep was skipped and land went on to wait in its own right. Two five-
second waits straddle a competitor's release, so a landing could run
its proofs and land on a digest file the sweep never looked at — judged
while a writer held the lock, on a state nobody swept.

**Decision** (amends D-041 decision 2's "the digest file on disk is the
evidence" with the sweep-under-lock ordering, and D-055 decision 4's
placement of the sweep; spec-design's D-091 is canonical for the
classification it reads):

1. **The sweep runs inside land's lock hold.** Every landing sweeps
   after acquiring `.task.lock` and before reading the entry or any
   digest, so the digest state the gate judges is the swept state, and
   no writer can move a digest file or a ledger row between the sweep
   and the judgment. `sweep_digests` grows a locked form for a caller
   already holding the lock; every other caller keeps taking it.
2. **A busy lock refuses the landing.** `land` acquires the lock first:
   a held lock is one wait, then exit 5 with nothing written — the
   entry stays claimed, no digest is given a line, no row is appended.
   The sweep is never skipped to get there.
3. **A digest no ledger row records lands nothing.** The sweep vouches
   a file only where the ledger records the request that produced it —
   the `wave` row of its wave and stem, or the `claim` row that claimed
   the task there. A parse-valid file neither carries — hand-placed, or
   left by a run whose ledger write failed — is `unverified`: no
   provenance line, recorded `digest_malformed` (outcome `unverified`,
   once per content), named. land's digest gate refuses it like a
   malformed one, exit 1, the line naming the file and what is missing;
   the entry stays claimed, `--digest` does not talk over it. The
   override stays for a missing file only.
4. **`fail`, `release`, `drop` and `claim` keep their sweep and lock
   order.** They gate on no digest file; only `land` reads one to
   decide.

**Consequences**: the judged digest is always the swept one, and a
contended spec refuses rather than lands blind. The costs if this is
wrong: a landing behind another writer waits one window and exits 5 —
the orchestrator retries, nothing is lost; a digest whose run's ledger
write failed (the warning path) is now refused where D-055 read it on
its own merits — the remedy is re-emit and re-spawn, and the ledger
warning is the trace; and a hand-placed file can no longer be landed
with `--digest` beside it. Pinned by `tests/test_mark.py`
`LockTests::test_land_with_a_held_lock_refuses_and_writes_nothing` and
`LandProofGateTests::test_a_digest_no_request_row_vouches_refuses_the_landing`.
