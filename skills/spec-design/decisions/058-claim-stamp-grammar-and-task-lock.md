# D-058: the claim stamp's shared grammar and task_lock

spec-build D-039 makes `mark.py` the one writer of task markers. The
stamp and the lock cross skill boundaries, so the shared copies — the
one grammar every validator and the engine read — carry them here:

1. **`specstate.py`** owns the grammar: the `CLAIM_NOTE` regex
   (`  - claimed <UTC ISO> — run <id>`), the `ClaimStamp` record, and
   the `claim` field on `TaskEntry` (None when unstamped — hand
   written claims and older docsets parse unchanged). It also hosts
   `task_lock`, the marker-writers' lock (build's mark.py and tick.py
   are the callers; the lock file lives in the spec dir, the reader is
   shared so both writers serialize on the same implementation).
2. **`freeze.py`** drops `claimed <ts> — run ` sub-lines from the
   tiny-tier hash alongside the `done`/`fix`/`fixed`/`Delivered`
   status lines. Hard ordering rule: without it, the first claim on a
   frozen tiny spec changes the hash and re-verification breaks — the
   stamp grammar and the freeze alternative shipped in one change.
3. **`check.py`**'s shape gate (the fix-round pairing gate) reads the
   pairing: a stamp without `(in-progress)` fails, and more than one
   stamp on an entry fails — mark.py writes exactly one.
4. **`graph.py`** reads, never writes: claimed tasks show `claimed
   <age> ago by run <id>` in the frontier, `--explain execute` and the
   orphan notices; with `--run-id` passed, only claims from a
   different run are flagged as orphans (this run's own wave reads
   "held by this run's wave"). An execute wave's emit prints the
   exact mark.py claim command after the payload list.

**Consequences**: the stamp is a sub-line, never an inline marker —
`(in-progress)` stays the claim's detection key and the marker regexes
stay byte-stable. mark.py itself is build-only (it imports audit.py);
nothing here adds a harness surface.
