# D-067: a failed task keeps its claim until it leaves — a row is live through the fix round and at the cap

D-057 decision 1 makes a registry row live only while its spec's
status holder shows the task `(in-progress)`, and decision 5 lets `fail`
leave the row on disk as stale. `fail` also replaces the claim with
`(fix n/5)`: between the failure and the round's re-spawn the row sat in
`specs/.claims/registry.json` and held nothing, and the next claim of
any spec swept it. A failed task is not a released one — its half-done
edits of the failed round stay in the tree for the next round to
continue from — so in that window another spec could claim the same
files, and did.

**Decision** (amends D-057 decisions 1 and 5; specstate is canonical,
spec-design's D-078 decision 1 reads the same):

1. **A row is live while its task is open on its spec's status holder:
   `(in-progress)`, or in a fix round — `(fix n/5)`, the cap
   `(fix 5/5)` included.** A round is a claim in waiting: the engine
   re-spawns the task and its edits are already in the tree. The cap
   holds its files for the same reason, for as long as the user takes
   to adjudicate. A ticked or struck entry is never open, whatever
   else its block says.
2. **`fail` writes the registry no more than it did.** The row from the
   claim that failed is what stays live; the round's claim overwrites
   it, as any claim does. `land`, `release`, `drop` and tick remove it
   as before — a released fix round holds nothing, since nothing of
   the task is in flight.
3. **A row whose task is in no round and not claimed is stale** — swept
   by the next claim, deferring nothing, exactly as before.

**Consequences**: a task between a failure and its next round, and a
task at the cap, holds its `Touches:` against every other spec in the
repo. The costs if this is wrong: a spec abandoned with a task in a fix
round holds those files until someone lands, releases or drops the
task — the orphan a resume already names; and the row must still exist
to hold anything, so a registry deleted by hand protects no failed
task until one is re-claimed. Pinned by `tests/test_claim_registry.py`
`ClaimRegistryTests::test_a_failed_task_keeps_its_files_until_it_leaves`.
