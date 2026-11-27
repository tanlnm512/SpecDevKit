# D-092: unverified digests prove nothing — the ledger, not the highest wave directory, names the latest

D-075 vouched any digest that parsed: a file no `wave` row recorded
gained a line of `none` facts and read like a vouched answer. And
`digests_on_file` took the highest `wave-N/` directory as the newest —
a hand-placed file, or a dead run's leftover, outranked everything the
ledger had vouched and was what `land` read and a held node named.
Stage 1's refused-digest hold (D-086) shared that highest-wins
convention.

**Decision** (amends D-075 decisions 3 and 4 — the request-less vouch
and the `none`-facts line are withdrawn; D-055's adopted copy in
spec-build is amended by D-071/D-072 there; extends D-086's hold to the
new refusal, which stays as D-086 wrote it in every other respect):

1. **Vouching needs a request row.** A digest file's content is vouched
   where the ledger records the request that produced it: the `wave`
   row of its wave and stem — or the `claim` row that claimed the task
   there, which records the same request for a hand-claimed wave — and
   a `digest` row or a sweep about to write one carries its sha. A
   parse-valid file with neither is `unverified`: no provenance line is
   ever written for it, it is recorded `digest_malformed` (outcome
   `unverified`, once per content), and it never produces an
   orchestrator line. A file whose `provenance:` line no row vouches
   for stays malformed, as D-075 decision 4 has it.
2. **The ledger names the latest.** For a task, the newest file the
   sweep leaves valid is the digest; a refused file newer than every
   valid one holds in its place (at one wave the valid file outranks
   it). An unverified file holds only while nothing vouches a digest
   beside it — a vouched file at a lower wave wins, and the stray is
   ignored. When the ledger names none, there is no latest: a file
   alone proves nothing, and the newest unverified file is the refusal
   the readers see.
3. **The hold is D-086's.** A node whose named digest is unverified is
   blocked with the same reason line shape, `unverified at <path> — … —
   fix and run again`, and the wave after it is not emitted; the
   approval ends the hold as D-086 decision 4 has it. `land` refuses
   the same classification (spec-build D-072), and the resume view and
   the retro fold read it as refused.

**Consequences**: what a landing cites and what a node holds is what
the orchestrator's ledger vouches, however many files sit in
`digests/`. The costs if this is wrong: a genuine digest whose ledger
write failed is refused — re-emit and re-spawn, the warning is the
trace; an emit of the same wave number after a ledger loss re-joins by
claim row only; and a wave's digest mid-flight (row written, file not
yet swept) reads valid, since the sweep at the next boundary will
vouch it. Pinned by `tests/test_specstate.py` `DigestVouchTests` and by
`tests/test_graph.py`
`RefusedDigestHoldTests::test_a_digest_nobody_asked_for_holds_its_node`.
